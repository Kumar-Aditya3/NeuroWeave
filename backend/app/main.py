from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Dict

from fastapi import Depends, FastAPI

from .auth import require_api_key
from .db import (
    create_event,
    create_feedback,
    get_latest_vibe,
    get_recent_events,
    get_user_sources,
    get_weighted_profile,
    init_db,
    upsert_device,
    update_profiles,
    utc_now_iso,
)
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

POSITIVE_WORDS = {"calm", "happy", "growth", "focus", "hope", "progress", "joy"}
NEGATIVE_WORDS = {"angry", "sad", "dark", "stress", "anxiety", "doom", "rage"}
DEDUPE_BUCKET_SECONDS = 300


def classify_text(text: str) -> Dict[str, object]:
    lowered = text.lower()
    topic_scores: Dict[str, float] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        matches = sum(count_keyword_matches(lowered, word) for word in keywords)
        topic_scores[topic] = float(matches)

    total = sum(topic_scores.values())
    if total > 0:
        topic_scores = {k: round(v / total, 4) for k, v in topic_scores.items()}
    else:
        topic_scores = {k: 0.0 for k in TOPIC_KEYWORDS.keys()}
        topic_scores["unknown"] = 1.0

    positive_hits = sum(lowered.count(word) for word in POSITIVE_WORDS)
    negative_hits = sum(lowered.count(word) for word in NEGATIVE_WORDS)

    if positive_hits > negative_hits:
        sentiment = "positive"
    elif negative_hits > positive_hits:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    if negative_hits >= 2:
        vibe = "dark"
    elif positive_hits >= 2:
        vibe = "calm"
    elif "intense" in lowered or "binge" in lowered:
        vibe = "intense"
    else:
        vibe = "balanced"

    return {"topic_scores": topic_scores, "sentiment": sentiment, "vibe": vibe}


def count_keyword_matches(text: str, keyword: str) -> int:
    escaped = re.escape(keyword.lower())
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return len(re.findall(pattern, text))


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


def build_context_recommendation(user_id: str) -> ContextRecommendation:
    profile = get_weighted_profile(user_id)
    primary_topic = "unknown"
    if profile and max(profile.values()) > 0:
        primary_topic = max(profile, key=profile.get)
    vibe = get_latest_vibe(user_id)
    mapped = recommendation_map(primary_topic, vibe)
    return ContextRecommendation(
        user_id=user_id,
        primary_topic=primary_topic,  # type: ignore[arg-type]
        topic_scores={k: round(v, 4) for k, v in profile.items()},
        wallpaper_tags=mapped["wallpaper_tags"],  # type: ignore[arg-type]
        music_mood=mapped["music_mood"],  # type: ignore[arg-type]
        quote_style=mapped["quote_style"],  # type: ignore[arg-type]
        vibe=vibe,  # type: ignore[arg-type]
    )


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
    analysis = classify_text(text_blob)
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
        selected_text=payload.selected_text,
        content_text=text_blob,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        created_at=created_at,
        dedupe_key=dedupe_key,
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    if not deduped:
        update_profiles(payload.user_id, analysis["topic_scores"])

    return IngestResponse(
        event_id=event_id,
        deduped=deduped,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
    )


@app.post("/ingest/pdf", response_model=IngestResponse)
def ingest_pdf(
    payload: PdfIngestRequest,
    _: str = Depends(require_api_key),
) -> IngestResponse:
    text_blob = f"{payload.filename}\n{payload.text}"
    analysis = classify_text(text_blob)
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
        selected_text=None,
        content_text=payload.text,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        created_at=created_at,
        dedupe_key=dedupe_key,
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    if not deduped:
        update_profiles(payload.user_id, analysis["topic_scores"])
    return IngestResponse(
        event_id=event_id,
        deduped=deduped,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
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
    analysis = classify_text(text_blob)
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
        selected_text=payload.selected_text,
        content_text=text_blob,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        created_at=created_at,
        dedupe_key=dedupe_key,
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    if not deduped:
        update_profiles(payload.user_id, analysis["topic_scores"])
    return IngestResponse(
        event_id=event_id,
        deduped=deduped,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
    )


@app.get("/recommend/context", response_model=ContextRecommendation)
def recommend_context(
    user_id: str = "kumar",
    _: str = Depends(require_api_key),
) -> ContextRecommendation:
    return build_context_recommendation(user_id)


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
    _: str = Depends(require_api_key),
) -> DashboardResponse:
    return DashboardResponse(
        user_id=user_id,
        recommendation=build_context_recommendation(user_id),
        events=get_recent_events(user_id, limit),
        sources=get_user_sources(user_id),
    )
