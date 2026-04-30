from datetime import datetime, timezone
import json
from hashlib import sha256
from pathlib import Path
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

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
    get_user_preference_profile,
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
from .supabase_mirror import (
    fetch_arc_centroids as fetch_supabase_arc_centroids,
    fetch_recent_event_payloads as fetch_supabase_recent_event_payloads,
    fetch_recent_events as fetch_supabase_recent_events,
    fetch_user_preferences as fetch_supabase_user_preferences,
    fetch_wallpaper_memory as fetch_supabase_wallpaper_memory,
    mirror_arc_centroids,
    mirror_device,
    mirror_event,
    mirror_feedback,
    mirror_user_preferences,
    mirror_wallpaper_memory,
)
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
WALLPAPER_CACHE_ROOT = Path(__file__).resolve().parents[1] / "wallpaper_cache"
DEFAULT_TOPIC_WEIGHT = 50.0


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


def normalize_recommendation_intensity(value: str) -> str:
    raw = (value or "").strip().lower()
    aliases = {
        "calm": "low",
        "low": "low",
        "balanced": "balanced",
        "strong": "high",
        "high": "high",
    }
    return aliases.get(raw, "balanced")


def apply_feedback_intensity_bias(intensity: str, preference_profile: dict[str, dict[str, float]]) -> str:
    vibe_preferences = preference_profile.get("vibe", {})
    dark_penalty = float(vibe_preferences.get("dark", 0.0))
    intense_penalty = float(vibe_preferences.get("intense", 0.0))
    calm_affinity = float(vibe_preferences.get("calm", 0.0))

    if intensity == "high" and (intense_penalty < -0.45 or dark_penalty < -0.45):
        return "balanced"
    if intensity == "balanced" and calm_affinity > 0.9:
        return "low"
    return intensity


def parse_topic_weights(topic_weights_json: str | None) -> dict[str, float]:
    if not topic_weights_json:
        return {}
    try:
        payload = json.loads(topic_weights_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}

    parsed: dict[str, float] = {}
    for topic in TOPIC_KEYWORDS.keys():
        raw_value = payload.get(topic)
        if raw_value is None:
            continue
        try:
            numeric = float(raw_value)
        except (TypeError, ValueError):
            continue
        parsed[topic] = max(0.0, min(100.0, numeric))
    return parsed


def apply_topic_weight_bias(scores: Dict[str, float], topic_weights: dict[str, float] | None) -> Dict[str, float]:
    if not scores:
        return scores
    topic_weights = topic_weights or {}
    weighted: Dict[str, float] = {}
    for topic, score in scores.items():
        slider_value = topic_weights.get(topic, DEFAULT_TOPIC_WEIGHT)
        multiplier = 0.5 + (slider_value / 100.0)
        weighted[topic] = float(score) * multiplier

    total = sum(weighted.values()) or 1.0
    return {topic: round(value / total, 4) for topic, value in weighted.items()}


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


@app.get("/wallpapers/cache/{filename}")
def wallpaper_cache_file(filename: str):
    safe_name = Path(filename).name
    cache_root = WALLPAPER_CACHE_ROOT.resolve()
    target = (cache_root / safe_name).resolve()
    if target.parent != cache_root or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Wallpaper file not found")
    return FileResponse(target)


def build_context_recommendation(
    user_id: str,
    classifier_mode: str = "embedding_primary",
    recommendation_intensity: str = "balanced",
    wallpaper_style: str = "minimal",
    wallpaper_provider: str = "generated_future",
    topic_weights: dict[str, float] | None = None,
    recent_payloads: list[dict] | None = None,
    current_arcs: list[dict] | None = None,
) -> ContextRecommendation:
    recent_payloads = recent_payloads if recent_payloads is not None else load_recent_event_window(user_id, limit=48)
    profile = get_weighted_profile(user_id)
    preference_profile = load_preference_profile(user_id)
    if current_arcs is None:
        current_arcs = get_adaptive_arcs(user_id, classifier_mode=classifier_mode, recent_payloads=recent_payloads)
    session_context = build_session_context(recent_payloads, current_arcs)
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
        profile = apply_topic_weight_bias(profile, topic_weights)
        vibe = max(vibe_weighted, key=vibe_weighted.get)
        explanation = "Recent signals: " + "; ".join(reason_parts) if reason_parts else "Recent signals are still warming up."
    else:
        vibe = get_latest_vibe(user_id)
        explanation = "Using historical profile because recent events are sparse."

    profile = apply_topic_weight_bias(profile, topic_weights)
    normalized_intensity = apply_feedback_intensity_bias(
        normalize_recommendation_intensity(recommendation_intensity),
        preference_profile,
    )

    primary_topic = "unknown"
    if profile and max(profile.values()) > 0:
        primary_topic = max(profile, key=profile.get)
    mapped = recommendation_map(primary_topic, vibe)
    top_arc_name = current_arcs[0]["name"] if current_arcs else None
    wallpaper = build_wallpaper_payload(
        primary_topic,
        vibe,
        normalized_intensity,
        wallpaper_style,
        provider=wallpaper_provider,
        arc_name=top_arc_name,
        recent_memory=load_wallpaper_memory(user_id, limit=36),
        preview_base_url="http://127.0.0.1:8000",
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
    mirror_wallpaper_memory(
        {
            "user_id": user_id,
            "topic": primary_topic,
            "vibe": vibe,
            "style": wallpaper_style,
            "provider": wallpaper["wallpaper_provider"],
            "wallpaper_query": wallpaper["wallpaper_query"],
            "wallpaper_preview_url": wallpaper.get("wallpaper_preview_url"),
            "created_at": utc_now_iso(),
        }
    )
    if preference_profile:
        mirror_user_preferences(
            [
                {
                    "user_id": user_id,
                    "target_type": target_type,
                    "target_key": target_key,
                    "score": score,
                    "updated_at": utc_now_iso(),
                }
                for target_type, bucket in preference_profile.items()
                for target_key, score in bucket.items()
            ]
        )
    if top_arc_name:
        explanation = f"{explanation} Active arc: {top_arc_name}."
    explanation = (
        f"{explanation} Session: {session_context['kind']} / {session_context['dominant_category']} / "
        f"stability {session_context['stability']:.2f}."
    )
    if preference_profile:
        explanation = f"{explanation} Preference memory is active."
    
    # Build classification confidence metadata
    classification_confidence = {
        "topic_scores_all": {k: round(v, 4) for k, v in profile.items()},
        "primary_topic_confidence": profile.get(primary_topic, 0.0),
        "classifier_mode": classifier_mode,
        "topic_weight_bias": {topic: topic_weights.get(topic, DEFAULT_TOPIC_WEIGHT) for topic in TOPIC_KEYWORDS.keys()} if topic_weights else None,
        "normalized_intensity": normalized_intensity,
        "preference_profile": preference_profile or None,
    }
    
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
        prompt_components=wallpaper.get("prompt_components"),
        generation_metadata=wallpaper.get("generation_metadata"),
        novelty_context=wallpaper.get("novelty_context"),
        classification_confidence=classification_confidence,
        session_context=session_context,
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


def build_session_context(recent_payloads: list[dict], current_arcs: list[dict] | None = None) -> dict:
    if not recent_payloads:
        return {
            "signature": "empty",
            "kind": "warming_up",
            "stability": 0.0,
            "shift_score": 0.0,
            "event_streak": 0,
            "minutes_covered": 0.0,
            "dominant_category": "unknown",
            "dominant_process": "unknown",
        }

    window = recent_payloads[:12]
    category_counts: Dict[str, float] = {}
    process_counts: Dict[str, float] = {}
    first_signature = None
    streak = 0
    timestamps: list[datetime] = []

    for index, payload in enumerate(window):
        weight = max(0.25, 1.0 - (index * 0.08))
        category = str(payload.get("category") or payload.get("event_type") or "unknown")
        process = str(payload.get("process_name") or payload.get("source") or "unknown")
        signature = f"{category}|{process}"
        category_counts[category] = category_counts.get(category, 0.0) + weight
        process_counts[process] = process_counts.get(process, 0.0) + weight
        if first_signature is None:
            first_signature = signature
        if signature == first_signature:
            streak += 1
        try:
            timestamps.append(datetime.fromisoformat(str(payload.get("created_at", "")).replace("Z", "+00:00")))
        except ValueError:
            continue

    dominant_category = max(category_counts, key=category_counts.get)
    dominant_process = max(process_counts, key=process_counts.get)
    first_half = window[: max(1, len(window) // 2)]
    second_half = window[max(1, len(window) // 2) :]
    lead_category = first_half[0].get("category") or first_half[0].get("event_type") or "unknown"
    tail_category = second_half[-1].get("category") or second_half[-1].get("event_type") or lead_category
    shift_score = 0.25 if lead_category == tail_category else 0.72
    minutes_covered = 0.0
    if len(timestamps) >= 2:
        newest = max(timestamps)
        oldest = min(timestamps)
        minutes_covered = max(0.0, (newest - oldest).total_seconds() / 60.0)
    stability = min(
        1.0,
        (streak / max(1, len(window))) * 0.45
        + (category_counts[dominant_category] / max(1.0, sum(category_counts.values()))) * 0.35
        + min(1.0, minutes_covered / 45.0) * 0.2,
    )
    top_arc = current_arcs[0]["name"] if current_arcs else "general_flow"
    signature = "|".join(
        [
            top_arc,
            str(dominant_category),
            str(dominant_process),
            str(streak),
            "shift" if shift_score >= 0.55 else "steady",
        ]
    )
    return {
        "signature": signature,
        "kind": top_arc,
        "stability": round(stability, 4),
        "shift_score": round(shift_score, 4),
        "event_streak": streak,
        "minutes_covered": round(minutes_covered, 2),
        "dominant_category": dominant_category,
        "dominant_process": dominant_process,
    }


def load_recent_events_feed(user_id: str, limit: int) -> list[dict]:
    remote_events = fetch_supabase_recent_events(user_id, limit=limit)
    if remote_events:
        return remote_events
    return get_recent_events(user_id, limit)


def load_recent_event_window(user_id: str, limit: int = 48) -> list[dict]:
    remote_payloads = fetch_supabase_recent_event_payloads(user_id, limit=limit)
    if remote_payloads:
        return remote_payloads
    return get_recent_event_payloads(user_id, limit=limit)


def load_wallpaper_memory(user_id: str, limit: int = 36) -> list[dict]:
    local_memory = get_wallpaper_memory(user_id, limit=limit)
    if local_memory:
        return local_memory
    return fetch_supabase_wallpaper_memory(user_id, limit=limit)


def load_arc_centroid_state(user_id: str) -> dict[str, dict]:
    local_centroids = get_arc_centroids(user_id)
    if local_centroids:
        return local_centroids
    return fetch_supabase_arc_centroids(user_id)


def load_preference_profile(user_id: str) -> dict[str, dict[str, float]]:
    local_profile = get_user_preference_profile(user_id)
    if local_profile:
        return local_profile
    return fetch_supabase_user_preferences(user_id)


def get_adaptive_arcs(
    user_id: str,
    classifier_mode: str,
    recent_payloads: list[dict] | None = None,
) -> list[dict]:
    payloads = recent_payloads if recent_payloads is not None else get_recent_event_payloads(user_id, limit=48)
    stored_centroids = load_arc_centroid_state(user_id)
    arcs, centroid_updates = build_current_arcs(
        payloads,
        classifier_mode=classifier_mode,
        prior_centroids=stored_centroids,
    )
    if centroid_updates:
        upsert_arc_centroids(user_id, centroid_updates)
        mirror_arc_centroids(
            [
                {
                    "user_id": user_id,
                    "arc_name": arc_name,
                    "centroid_json": payload.get("centroid", []),
                    "sample_count": float(payload.get("sample_count", 0.0)),
                    "dominant_topic": payload.get("dominant_topic"),
                    "vibe": payload.get("vibe"),
                    "strength": float(payload.get("strength", 0.0)),
                    "updated_at": utc_now_iso(),
                }
                for arc_name, payload in centroid_updates.items()
            ]
        )
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
        duration_seconds=None,
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
            "duration_seconds": None,
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
        duration_seconds=None,
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
            "duration_seconds": None,
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
            f"{payload.duration_seconds or 0} seconds active",
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
        duration_seconds=payload.duration_seconds,
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
            "duration_seconds": payload.duration_seconds,
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
    wallpaper_provider: str = "generated_future",
    topic_weights_json: str | None = None,
    _: str = Depends(require_api_key),
) -> ContextRecommendation:
    topic_weights = parse_topic_weights(topic_weights_json)
    return build_context_recommendation(
        user_id,
        classifier_mode=classifier_mode,
        recommendation_intensity=recommendation_intensity,
        wallpaper_style=wallpaper_style,
        wallpaper_provider=wallpaper_provider,
        topic_weights=topic_weights,
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
        recommendation_vibe=payload.recommendation_vibe,
        wallpaper_style=payload.wallpaper_style,
    )
    mirror_feedback(
        {
            "user_id": payload.user_id,
            "recommendation_topic": payload.recommendation_topic,
            "action": payload.action,
            "created_at": utc_now_iso(),
        }
    )
    preference_profile = get_user_preference_profile(payload.user_id)
    if preference_profile:
        mirror_user_preferences(
            [
                {
                    "user_id": payload.user_id,
                    "target_type": target_type,
                    "target_key": target_key,
                    "score": score,
                    "updated_at": utc_now_iso(),
                }
                for target_type, bucket in preference_profile.items()
                for target_key, score in bucket.items()
            ]
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
    events = load_recent_events_feed(user_id, limit)
    return RecentEventsResponse(user_id=user_id, events=events)


@app.get("/me/dashboard", response_model=DashboardResponse)
def me_dashboard(
    user_id: str = "kumar",
    limit: int = 24,
    classifier_mode: str = "embedding_primary",
    recommendation_intensity: str = "balanced",
    wallpaper_style: str = "minimal",
    wallpaper_provider: str = "generated_future",
    topic_weights_json: str | None = None,
    _: str = Depends(require_api_key),
) -> DashboardResponse:
    topic_weights = parse_topic_weights(topic_weights_json)
    recent_events = load_recent_events_feed(user_id, limit)
    recent_payloads = load_recent_event_window(user_id, limit=48)
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
            topic_weights=topic_weights,
            recent_payloads=recent_payloads,
            current_arcs=current_arcs,
        ),
        events=recent_events,
        sources=get_user_sources(user_id),
        current_arcs=current_arcs,
        source_mix=build_source_mix(recent_events),
    )
