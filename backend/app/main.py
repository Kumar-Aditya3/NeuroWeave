from datetime import datetime, timezone
from hashlib import sha256
from typing import Dict

from fastapi import Depends, FastAPI

from .arcs import build_current_arcs
from .auth import require_api_key
from .db import (
    create_wallpaper_memory,
    create_event,
    create_feedback,
    get_arc_centroids,
    get_latest_vibe,
    get_recent_event_payloads,
    get_recent_events,
    get_user_sources,
    get_wallpaper_memory,
    get_weighted_profile,
    init_db,
    upsert_arc_centroids,
    upsert_device,
    update_profiles,
    utc_now_iso,
)
from .ml import classify_text
from .models import (
    ActivityIngestRequest,
    ContextRecommendation,
    DashboardResponse,
    FeedbackRequest,
    HealthResponse,
    IngestResponse,
    PageIngestRequest,
    PdfIngestRequest,
    RecentEventsResponse,
    SourcesResponse,
)
from .supabase_mirror import mirror_device, mirror_event, mirror_feedback
from .wallpapers import build_wallpaper_payload

TOPIC_KEYWORDS = {
    "tech": ["python", "fastapi", "ml", "ai", "code", "programming", "software"],
    "education": [
        "swayam",
        "course",
        "courses",
        "learn",
        "learning",
        "lecture",
        "exam",
        "study",
        "student",
        "university",
        "college",
        "nptel",
        "mooc",
    ],
    "anime": ["anime", "manga", "otaku", "episode", "studio", "shonen"],
    "fitness": ["fitness", "workout", "gym", "cardio", "strength", "nutrition"],
    "philosophy": ["philosophy", "ethics", "stoic", "stoicism", "meaning", "existence"],
    "self-help": ["habit", "motivation", "focus", "discipline", "self improvement"],
    "news": ["news", "breaking", "update", "world", "politics", "economy"],
    "unknown": [],
}
DEDUPE_BUCKET_SECONDS = 300


def recommendation_map(primary_topic: str, vibe: str) -> Dict[str, object]:
    wallpaper_by_topic = {
        "tech": ["minimal", "dark-ui", "futuristic"],
        "education": ["library", "desk-setup", "warm-focus"],
        "anime": ["cinematic", "neon", "character-art"],
        "fitness": ["dynamic", "high-contrast", "athletic"],
        "philosophy": ["abstract", "statue", "monochrome"],
        "self-help": ["clean", "focus", "morning-light"],
        "news": ["editorial", "world-map", "neutral"],
        "unknown": ["neutral", "minimal", "soft-light"],
    }
    music_by_vibe = {
        "calm": "lofi / ambient",
        "balanced": "indie / instrumental",
        "intense": "synthwave / cinematic",
        "dark": "dark ambient / downtempo",
    }
    quote_by_vibe = {
        "calm": "mindful and reflective",
        "balanced": "practical and focused",
        "intense": "driven and resilient",
        "dark": "grounding and hopeful",
    }
    return {
        "wallpaper_tags": wallpaper_by_topic.get(primary_topic, ["minimal"]),
        "music_mood": music_by_vibe.get(vibe, "indie / instrumental"),
        "quote_style": quote_by_vibe.get(vibe, "practical and focused"),
    }


def normalize_created_at(timestamp: datetime | None) -> str:
    if not timestamp:
        return utc_now_iso()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat()


def dedupe_key_for(
    *,
    user_id: str,
    device_id: str,
    event_type: str,
    title: str | None,
    created_at: str,
) -> str:
    parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    bucket = int(parsed.timestamp() // DEDUPE_BUCKET_SECONDS)
    raw = "|".join(
        [
            user_id.strip().lower(),
            device_id.strip().lower(),
            event_type.strip().lower(),
            (title or "").strip().lower(),
            str(bucket),
        ]
    )
    return sha256(raw.encode("utf-8")).hexdigest()


app = FastAPI(title="NeuroWeave API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def build_context_recommendation(
    user_id: str,
    classifier_mode: str = "embedding_primary",
    recommendation_intensity: str = "balanced",
    wallpaper_style: str = "minimal",
    wallpaper_provider: str = "curated_unsplash",
    recent_payloads: list[dict] | None = None,
    current_arcs: list[dict] | None = None,
) -> ContextRecommendation:
    recent_payloads = recent_payloads if recent_payloads is not None else get_recent_event_payloads(user_id, limit=48)
    profile = get_weighted_profile(user_id)
    if current_arcs is None:
        current_arcs = get_adaptive_arcs(user_id, classifier_mode=classifier_mode, recent_payloads=recent_payloads)
    if recent_payloads:
        recency_weighted: Dict[str, float] = {topic: 0.0 for topic in TOPIC_KEYWORDS.keys()}
        vibe_weighted: Dict[str, float] = {"calm": 0.0, "balanced": 0.0, "intense": 0.0, "dark": 0.0}
        reason_parts: list[str] = []
        for index, payload in enumerate(recent_payloads):
            weight = max(0.18, 1.0 - (index * 0.03))
            text_blob = " ".join(
                [
                    payload["title"],
                    payload["url"],
                    payload["selected_text"],
                    payload["content_text"],
                    payload["source"],
                    payload["event_type"],
                ]
            )
            analysis = classify_text(text_blob, classifier_mode=classifier_mode)
            for topic, score in analysis["topic_scores"].items():
                recency_weighted[topic] += float(score) * weight
            vibe_weighted[str(analysis["vibe"])] += weight
            if index < 3:
                top_topic = max(analysis["topic_scores"], key=analysis["topic_scores"].get)
                reason_parts.append(f"{payload['title'][:44]} -> {top_topic}")

        total = sum(recency_weighted.values()) or 1.0
        profile = {topic: round(value / total, 4) for topic, value in recency_weighted.items()}
        vibe = max(vibe_weighted, key=vibe_weighted.get)
        explanation = "Recent signals: " + "; ".join(reason_parts) if reason_parts else "Recent signals are still warming up."
    else:
        vibe = get_latest_vibe(user_id)
        explanation = "Using historical profile because recent events are sparse."

    primary_topic = "unknown"
    if profile and max(profile.values()) > 0:
        primary_topic = max(profile, key=profile.get)
    mapped = recommendation_map(primary_topic, vibe)
    top_arc_name = current_arcs[0]["name"] if current_arcs else None
    wallpaper = build_wallpaper_payload(
        primary_topic,
        vibe,
        recommendation_intensity,
        wallpaper_style,
        provider=wallpaper_provider,
        arc_name=top_arc_name,
        recent_memory=get_wallpaper_memory(user_id, limit=36),
    )
    create_wallpaper_memory(
        user_id=user_id,
        topic=primary_topic,
        vibe=vibe,
        style=wallpaper_style,
        provider=wallpaper["wallpaper_provider"],
        wallpaper_query=wallpaper["wallpaper_query"],
        wallpaper_preview_url=wallpaper.get("wallpaper_preview_url"),
    )
    if top_arc_name:
        explanation = f"{explanation} Active arc: {top_arc_name}."
    return ContextRecommendation(
        user_id=user_id,
        primary_topic=primary_topic,  # type: ignore[arg-type]
        topic_scores={k: round(v, 4) for k, v in profile.items()},
        wallpaper_tags=mapped["wallpaper_tags"],  # type: ignore[arg-type]
        wallpaper_query=wallpaper["wallpaper_query"],
        wallpaper_preview_url=wallpaper["wallpaper_preview_url"],
        wallpaper_palette=wallpaper["wallpaper_palette"],
        wallpaper_source=wallpaper["wallpaper_source"],
        wallpaper_provider=wallpaper["wallpaper_provider"],
        wallpaper_rationale=wallpaper["wallpaper_rationale"],
        wallpaper_cached_path=wallpaper["wallpaper_cached_path"],
        wallpaper_alternates=wallpaper["wallpaper_alternates"],
        music_mood=mapped["music_mood"],  # type: ignore[arg-type]
        quote_style=mapped["quote_style"],  # type: ignore[arg-type]
        vibe=vibe,  # type: ignore[arg-type]
        classifier_mode=classifier_mode,
        explanation=explanation,
    )


def build_source_mix(events: list[dict]) -> dict:
    mix = {
        "browser": 0,
        "app": 0,
        "game": 0,
        "ocr": 0,
        "mobile": 0,
    }
    for event in events:
        event_type = event.get("event_type", "")
        source = event.get("source", "")
        if event_type == "browser_tab":
            mix["browser"] += 1
        elif event_type == "game":
            mix["game"] += 1
        elif event_type == "ocr_text":
            mix["ocr"] += 1
        elif source.startswith("mobile_") or event_type.startswith("mobile_"):
            mix["mobile"] += 1
        else:
            mix["app"] += 1
    return mix


def get_adaptive_arcs(
    user_id: str,
    classifier_mode: str,
    recent_payloads: list[dict] | None = None,
) -> list[dict]:
    payloads = recent_payloads if recent_payloads is not None else get_recent_event_payloads(user_id, limit=48)
    stored_centroids = get_arc_centroids(user_id)
    arcs, centroid_updates = build_current_arcs(
        payloads,
        classifier_mode=classifier_mode,
        prior_centroids=stored_centroids,
    )
    if centroid_updates:
        upsert_arc_centroids(user_id, centroid_updates)
    return arcs


@app.post("/ingest/page", response_model=IngestResponse)
def ingest_page(
    payload: PageIngestRequest,
    _: str = Depends(require_api_key),
) -> IngestResponse:
    text_blob = " ".join(
        [
            payload.title,
            str(payload.url),
            payload.selected_text or "",
        ]
    )
    analysis = classify_text(text_blob, classifier_mode="embedding_primary")
    created_at = normalize_created_at(payload.timestamp)
    dedupe_key = dedupe_key_for(
        user_id=payload.user_id,
        device_id=payload.device_id,
        event_type="browser_tab",
        title=payload.title,
        created_at=created_at,
    )

    event_id, deduped = create_event(
        user_id=payload.user_id,
        device_id=payload.device_id,
        client_name=payload.client_name,
        source="browser_tab",
        event_type="browser_tab",
        url=str(payload.url),
        title=payload.title,
        category="browser",
        selected_text=payload.selected_text,
        content_text=text_blob,
        topic_scores=analysis["topic_scores"],
        embedding_json=str(analysis.get("embedding_preview")),
        classifier_mode=str(analysis.get("classifier_mode", "embedding_primary")),
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        created_at=created_at,
        dedupe_key=dedupe_key,
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    mirror_device(
        {
            "user_id": payload.user_id,
            "device_id": payload.device_id,
            "client_name": payload.client_name,
            "last_seen_at": created_at,
        }
    )
    mirror_event(
        {
            "dedupe_key": dedupe_key,
            "user_id": payload.user_id,
            "device_id": payload.device_id,
            "client_name": payload.client_name,
            "source": "browser_tab",
            "event_type": "browser_tab",
            "url": str(payload.url),
            "title": payload.title,
            "category": "browser",
            "selected_text": payload.selected_text,
            "content_text": text_blob,
            "topic_scores_json": analysis["topic_scores"],
            "embedding_json": analysis.get("embedding_preview"),
            "classifier_mode": str(analysis.get("classifier_mode", "embedding_primary")),
            "sentiment": analysis["sentiment"],
            "vibe": analysis["vibe"],
            "created_at": created_at,
            "received_at": utc_now_iso(),
        }
    )
    if not deduped:
        update_profiles(payload.user_id, analysis["topic_scores"])

    return IngestResponse(
        event_id=event_id,
        deduped=deduped,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        classifier_mode=str(analysis.get("classifier_mode", "embedding_primary")),
    )


@app.post("/ingest/pdf", response_model=IngestResponse)
def ingest_pdf(
    payload: PdfIngestRequest,
    _: str = Depends(require_api_key),
) -> IngestResponse:
    text_blob = f"{payload.filename}\n{payload.text}"
    analysis = classify_text(text_blob, classifier_mode="embedding_primary")
    created_at = normalize_created_at(payload.timestamp)
    dedupe_key = dedupe_key_for(
        user_id=payload.user_id,
        device_id=payload.device_id,
        event_type="pdf",
        title=payload.filename,
        created_at=created_at,
    )
    event_id, deduped = create_event(
        user_id=payload.user_id,
        device_id=payload.device_id,
        client_name=payload.client_name,
        source=payload.source,
        event_type="pdf",
        url=None,
        title=payload.filename,
        category="document",
        selected_text=None,
        content_text=payload.text,
        topic_scores=analysis["topic_scores"],
        embedding_json=str(analysis.get("embedding_preview")),
        classifier_mode=str(analysis.get("classifier_mode", "embedding_primary")),
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        created_at=created_at,
        dedupe_key=dedupe_key,
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    mirror_device(
        {
            "user_id": payload.user_id,
            "device_id": payload.device_id,
            "client_name": payload.client_name,
            "last_seen_at": created_at,
        }
    )
    mirror_event(
        {
            "dedupe_key": dedupe_key,
            "user_id": payload.user_id,
            "device_id": payload.device_id,
            "client_name": payload.client_name,
            "source": payload.source,
            "event_type": "pdf",
            "url": None,
            "title": payload.filename,
            "category": "document",
            "selected_text": None,
            "content_text": payload.text,
            "topic_scores_json": analysis["topic_scores"],
            "embedding_json": analysis.get("embedding_preview"),
            "classifier_mode": str(analysis.get("classifier_mode", "embedding_primary")),
            "sentiment": analysis["sentiment"],
            "vibe": analysis["vibe"],
            "created_at": created_at,
            "received_at": utc_now_iso(),
        }
    )
    if not deduped:
        update_profiles(payload.user_id, analysis["topic_scores"])
    return IngestResponse(
        event_id=event_id,
        deduped=deduped,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        classifier_mode=str(analysis.get("classifier_mode", "embedding_primary")),
    )


@app.post("/ingest/activity", response_model=IngestResponse)
def ingest_activity(
    payload: ActivityIngestRequest,
    _: str = Depends(require_api_key),
) -> IngestResponse:
    text_blob = " ".join(
        [
            payload.title,
            str(payload.url or ""),
            payload.process_name or "",
            payload.category or "",
            payload.selected_text or "",
            payload.content_text or "",
        ]
    )
    analysis = classify_text(text_blob, classifier_mode="embedding_primary")
    created_at = normalize_created_at(payload.timestamp)
    dedupe_key = dedupe_key_for(
        user_id=payload.user_id,
        device_id=payload.device_id,
        event_type=payload.event_type,
        title=payload.title,
        created_at=created_at,
    )
    event_id, deduped = create_event(
        user_id=payload.user_id,
        device_id=payload.device_id,
        client_name=payload.client_name,
        source=payload.source,
        event_type=payload.event_type,
        url=str(payload.url) if payload.url else None,
        title=payload.title,
        category=payload.category,
        selected_text=payload.selected_text,
        content_text=text_blob,
        topic_scores=analysis["topic_scores"],
        embedding_json=str(analysis.get("embedding_preview")),
        classifier_mode=str(analysis.get("classifier_mode", "embedding_primary")),
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        created_at=created_at,
        dedupe_key=dedupe_key,
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    mirror_device(
        {
            "user_id": payload.user_id,
            "device_id": payload.device_id,
            "client_name": payload.client_name,
            "last_seen_at": created_at,
        }
    )
    mirror_event(
        {
            "dedupe_key": dedupe_key,
            "user_id": payload.user_id,
            "device_id": payload.device_id,
            "client_name": payload.client_name,
            "source": payload.source,
            "event_type": payload.event_type,
            "url": str(payload.url) if payload.url else None,
            "title": payload.title,
            "category": payload.category,
            "selected_text": payload.selected_text,
            "content_text": text_blob,
            "process_name": payload.process_name,
            "topic_scores_json": analysis["topic_scores"],
            "embedding_json": analysis.get("embedding_preview"),
            "classifier_mode": str(analysis.get("classifier_mode", "embedding_primary")),
            "sentiment": analysis["sentiment"],
            "vibe": analysis["vibe"],
            "created_at": created_at,
            "received_at": utc_now_iso(),
        }
    )
    if not deduped:
        update_profiles(payload.user_id, analysis["topic_scores"])
    return IngestResponse(
        event_id=event_id,
        deduped=deduped,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        classifier_mode=str(analysis.get("classifier_mode", "embedding_primary")),
    )


@app.get("/recommend/context", response_model=ContextRecommendation)
def recommend_context(
    user_id: str = "kumar",
    classifier_mode: str = "embedding_primary",
    recommendation_intensity: str = "balanced",
    wallpaper_style: str = "minimal",
    wallpaper_provider: str = "curated_unsplash",
    _: str = Depends(require_api_key),
) -> ContextRecommendation:
    return build_context_recommendation(
        user_id,
        classifier_mode=classifier_mode,
        recommendation_intensity=recommendation_intensity,
        wallpaper_style=wallpaper_style,
        wallpaper_provider=wallpaper_provider,
    )


@app.post("/feedback")
def feedback(
    payload: FeedbackRequest,
    _: str = Depends(require_api_key),
) -> dict:
    create_feedback(
        user_id=payload.user_id,
        recommendation_topic=payload.recommendation_topic,
        action=payload.action,
    )
    mirror_feedback(
        {
            "user_id": payload.user_id,
            "recommendation_topic": payload.recommendation_topic,
            "action": payload.action,
            "created_at": utc_now_iso(),
        }
    )
    return {"status": "accepted"}


@app.get("/me/sources", response_model=SourcesResponse)
def me_sources(
    user_id: str = "kumar",
    _: str = Depends(require_api_key),
) -> SourcesResponse:
    sources = get_user_sources(user_id)
    return SourcesResponse(user_id=user_id, sources=sources)


@app.get("/me/recent-events", response_model=RecentEventsResponse)
def me_recent_events(
    user_id: str = "kumar",
    limit: int = 20,
    _: str = Depends(require_api_key),
) -> RecentEventsResponse:
    events = get_recent_events(user_id, limit)
    return RecentEventsResponse(user_id=user_id, events=events)


@app.get("/me/dashboard", response_model=DashboardResponse)
def me_dashboard(
    user_id: str = "kumar",
    limit: int = 24,
    classifier_mode: str = "embedding_primary",
    recommendation_intensity: str = "balanced",
    wallpaper_style: str = "minimal",
    wallpaper_provider: str = "curated_unsplash",
    _: str = Depends(require_api_key),
) -> DashboardResponse:
    recent_events = get_recent_events(user_id, limit)
    recent_payloads = get_recent_event_payloads(user_id, limit=48)
    current_arcs = get_adaptive_arcs(
        user_id,
        classifier_mode=classifier_mode,
        recent_payloads=recent_payloads,
    )
    return DashboardResponse(
        user_id=user_id,
        recommendation=build_context_recommendation(
            user_id,
            classifier_mode=classifier_mode,
            recommendation_intensity=recommendation_intensity,
            wallpaper_style=wallpaper_style,
            wallpaper_provider=wallpaper_provider,
            recent_payloads=recent_payloads,
            current_arcs=current_arcs,
        ),
        events=recent_events,
        sources=get_user_sources(user_id),
        current_arcs=current_arcs,
        source_mix=build_source_mix(recent_events),
    )
