from datetime import timezone
from typing import Dict

from fastapi import Depends, FastAPI

from .auth import require_api_key
from .db import (
    create_event,
    create_feedback,
    get_latest_vibe,
    get_user_sources,
    get_weighted_profile,
    init_db,
    upsert_device,
    update_profiles,
    utc_now_iso,
)
from .models import (
    ContextRecommendation,
    FeedbackRequest,
    HealthResponse,
    IngestResponse,
    PageIngestRequest,
    PdfIngestRequest,
    SourcesResponse,
)

TOPIC_KEYWORDS = {
    "tech": ["python", "fastapi", "ml", "ai", "code", "programming", "software"],
    "anime": ["anime", "manga", "otaku", "episode", "studio", "shonen"],
    "fitness": ["fitness", "workout", "gym", "cardio", "strength", "nutrition"],
    "philosophy": ["philosophy", "ethics", "stoic", "stoicism", "meaning", "existence"],
    "self-help": ["habit", "motivation", "focus", "discipline", "self improvement"],
    "news": ["news", "breaking", "update", "world", "politics", "economy"],
}

POSITIVE_WORDS = {"calm", "happy", "growth", "focus", "hope", "progress", "joy"}
NEGATIVE_WORDS = {"angry", "sad", "dark", "stress", "anxiety", "doom", "rage"}


def classify_text(text: str) -> Dict[str, object]:
    lowered = text.lower()
    topic_scores: Dict[str, float] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        matches = sum(lowered.count(word) for word in keywords)
        topic_scores[topic] = float(matches)

    total = sum(topic_scores.values())
    if total > 0:
        topic_scores = {k: round(v / total, 4) for k, v in topic_scores.items()}
    else:
        topic_scores = {k: 0.0 for k in TOPIC_KEYWORDS.keys()}
        topic_scores["tech"] = 1.0

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


def recommendation_map(primary_topic: str, vibe: str) -> Dict[str, object]:
    wallpaper_by_topic = {
        "tech": ["minimal", "dark-ui", "futuristic"],
        "anime": ["cinematic", "neon", "character-art"],
        "fitness": ["dynamic", "high-contrast", "athletic"],
        "philosophy": ["abstract", "statue", "monochrome"],
        "self-help": ["clean", "focus", "morning-light"],
        "news": ["editorial", "world-map", "neutral"],
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


app = FastAPI(title="NeuroWeave API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


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
    created_at = (
        payload.timestamp.replace(tzinfo=timezone.utc).isoformat()
        if payload.timestamp
        else utc_now_iso()
    )

    event_id = create_event(
        user_id=payload.user_id,
        device_id=payload.device_id,
        client_name=payload.client_name,
        source=payload.source,
        event_type="page",
        url=str(payload.url),
        title=payload.title,
        selected_text=payload.selected_text,
        content_text=text_blob,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
        created_at=created_at,
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    update_profiles(payload.user_id, analysis["topic_scores"])

    return IngestResponse(
        event_id=event_id,
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
    created_at = (
        payload.timestamp.replace(tzinfo=timezone.utc).isoformat()
        if payload.timestamp
        else utc_now_iso()
    )
    event_id = create_event(
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
    )
    upsert_device(payload.user_id, payload.device_id, payload.client_name)
    update_profiles(payload.user_id, analysis["topic_scores"])
    return IngestResponse(
        event_id=event_id,
        topic_scores=analysis["topic_scores"],
        sentiment=analysis["sentiment"],
        vibe=analysis["vibe"],
    )


@app.get("/recommend/context", response_model=ContextRecommendation)
def recommend_context(
    user_id: str = "default",
    _: str = Depends(require_api_key),
) -> ContextRecommendation:
    profile = get_weighted_profile(user_id)
    primary_topic = max(profile, key=profile.get) if profile else "tech"
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
    user_id: str = "default",
    _: str = Depends(require_api_key),
) -> SourcesResponse:
    sources = get_user_sources(user_id)
    return SourcesResponse(user_id=user_id, sources=sources)
