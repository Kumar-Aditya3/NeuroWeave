from __future__ import annotations

from . import styles
from ..ml import cosine_similarity, encode_text
from .providers import curated_unsplash_provider, generated_future_provider
from .query_builder import build_wallpaper_query

NOVELTY_HINTS = [
    "high detail texture study",
    "wide angle composition",
    "atmospheric depth layering",
    "architectural framing",
    "organic forms and gradients",
    "editorial lighting contrast",
]


def _max_query_similarity(candidate_query: str, memory: list[dict]) -> float:
    candidate_vec = encode_text(candidate_query)
    max_similarity = 0.0
    for row in memory:
        previous_query = row.get("wallpaper_query", "")
        if not previous_query:
            continue
        similarity = cosine_similarity(candidate_vec, encode_text(previous_query))
        max_similarity = max(max_similarity, similarity)
    return max_similarity


def _matching_memory_count(topic: str, vibe: str, style: str, provider: str, memory: list[dict]) -> int:
    return sum(
        1
        for row in memory
        if row.get("topic") == topic
        and row.get("vibe") == vibe
        and row.get("style") == style
        and row.get("provider") == provider
    )


def build_wallpaper_payload(
    topic: str,
    vibe: str,
    intensity: str,
    style: str,
    provider: str = "generated_future",
    arc_name: str | None = None,
    recent_memory: list[dict] | None = None,
    preview_base_url: str = "http://127.0.0.1:8000",
) -> dict:
    memory = recent_memory or []
    query_payload = build_wallpaper_query(topic, vibe, intensity, style, arc_name)
    query = query_payload["wallpaper_query"]

    style_key = style if style in styles.WALLPAPER_STYLE_HINTS else "minimal"
    repeated_count = _matching_memory_count(topic, vibe, style_key, provider, memory)
    if repeated_count > 0:
        novelty_hint = NOVELTY_HINTS[repeated_count % len(NOVELTY_HINTS)]
        candidate_query = f"{query} {novelty_hint}"
        if _max_query_similarity(candidate_query, memory[:18]) >= 0.92:
            novelty_hint = NOVELTY_HINTS[(repeated_count + 2) % len(NOVELTY_HINTS)]
            candidate_query = f"{query} {novelty_hint}"
        query_payload["wallpaper_query"] = candidate_query

    seed_offset = repeated_count * 5
    if provider == "generated_future":
        alternates = generated_future_provider(
            query_payload["wallpaper_query"],
            intensity,
            topic=topic,
            vibe=vibe,
            style=style_key,
            seed_offset=seed_offset,
            base_url=preview_base_url,
        )
    else:
        alternates = curated_unsplash_provider(
            query_payload["wallpaper_query"],
            intensity,
            seed_offset=seed_offset,
        )
        provider = "curated_unsplash"

    return {
        **query_payload,
        "wallpaper_preview_url": alternates[0]["preview_url"],
        "wallpaper_source": alternates[0]["source"],
        "wallpaper_provider": provider,
        "wallpaper_cached_path": alternates[0]["cached_path"],
        "wallpaper_alternates": alternates,
    }
