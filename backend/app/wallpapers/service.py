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


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _query_contains(query: str, phrase: str) -> bool:
    return phrase.lower() in query.lower()


def _build_visual_fit(
    *,
    topic: str,
    vibe: str,
    intensity: str,
    style: str,
    query: str,
    query_payload: dict,
    repeated_count: int,
    novelty_hint: str | None,
) -> dict:
    grammar = query_payload.get("visual_grammar") or {}
    topic_grammar = grammar.get("topic") or {}
    vibe_grammar = grammar.get("vibe") or {}
    intensity_grammar = grammar.get("intensity") or {}
    color_grammar = grammar.get("color") or {}
    preference_grammar = grammar.get("preference") or {}

    topic_terms = [
        topic,
        str(styles.TOPIC_BASE.get(topic, "")),
        str(topic_grammar.get("geometry", "")),
        str(topic_grammar.get("composition", "")),
    ]
    vibe_terms = [
        vibe,
        str(styles.VIBE_BASE.get(vibe, "")),
        str(vibe_grammar.get("color_energy", "")),
        str(vibe_grammar.get("contrast", "")),
        str(vibe_grammar.get("motion", "")),
    ]
    structure_terms = [
        str(intensity_grammar.get("detail", "")),
        str(intensity_grammar.get("negative_space", "")),
        str(styles.WALLPAPER_STYLE_HINTS.get(style, "")),
    ]
    palette = [str(color) for color in color_grammar.get("palette", [])]

    topic_hits = sum(1 for term in topic_terms if term and _query_contains(query, term))
    vibe_hits = sum(1 for term in vibe_terms if term and _query_contains(query, term))
    structure_hits = sum(1 for term in structure_terms if term and _query_contains(query, term))
    palette_hits = sum(1 for color in palette if color and _query_contains(query, color))

    preference_state = str(preference_grammar.get("state") or "neutral")
    preference_bonus = 0.08 if preference_state == "reinforced" else 0.04 if preference_state == "neutral" else 0.0
    novelty_bonus = 0.05 if repeated_count == 0 or novelty_hint else 0.0

    components = {
        "topic_alignment": _clamp_score(topic_hits / max(1, len(topic_terms))),
        "vibe_alignment": _clamp_score(vibe_hits / max(1, len(vibe_terms))),
        "structure_alignment": _clamp_score(structure_hits / max(1, len(structure_terms))),
        "palette_alignment": _clamp_score(palette_hits / max(1, len(palette))),
        "preference_alignment": _clamp_score(preference_bonus),
        "novelty_alignment": _clamp_score(novelty_bonus),
    }
    score = _clamp_score(
        (components["topic_alignment"] * 0.28)
        + (components["vibe_alignment"] * 0.18)
        + (components["structure_alignment"] * 0.22)
        + (components["palette_alignment"] * 0.17)
        + components["preference_alignment"]
        + components["novelty_alignment"]
    )
    if score >= 0.78:
        grade = "strong"
    elif score >= 0.58:
        grade = "usable"
    else:
        grade = "weak"

    return {
        "score": score,
        "grade": grade,
        "components": components,
        "topic": topic,
        "vibe": vibe,
        "intensity": intensity,
        "style": style,
    }


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
    transition_context: dict | None = None,
    preference_profile: dict[str, dict[str, float]] | None = None,
    preview_base_url: str = "http://127.0.0.1:8000",
) -> dict:
    memory = recent_memory or []
    query_payload = build_wallpaper_query(
        topic,
        vibe,
        intensity,
        style,
        arc_name,
        transition_context=transition_context,
        preference_profile=preference_profile,
    )
    query = query_payload["wallpaper_query"]
    visual_grammar = query_payload.get("visual_grammar")

    style_key = style if style in styles.WALLPAPER_STYLE_HINTS else "minimal"
    repeated_count = _matching_memory_count(topic, vibe, style_key, provider, memory)
    
    # Track novelty hint for explainability
    novelty_hint = None
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
            negative_prompt=query_payload.get("negative_prompt"),
            visual_grammar=visual_grammar,
            palette=query_payload["wallpaper_palette"],
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

    # Extract generation metadata from first alternate
    generation_metadata = alternates[0].get("generation_metadata", {}) if alternates else {}
    
    # Build explainability data
    prompt_components = {
        "arc_name": arc_name,
        "vibe_base": styles.VIBE_BASE.get(vibe, styles.VIBE_BASE["balanced"]),
        "topic_base": styles.TOPIC_BASE.get(topic, styles.TOPIC_BASE["unknown"]),
        "style_hint": styles.WALLPAPER_STYLE_HINTS.get(style_key, styles.WALLPAPER_STYLE_HINTS["minimal"]),
        "novelty_hint": novelty_hint,
        "transition_context": transition_context,
        "preference_profile": preference_profile or None,
    }
    
    novelty_context = {
        "recent_count": repeated_count,
        "novelty_hint_applied": novelty_hint is not None,
    }
    visual_fit = _build_visual_fit(
        topic=topic,
        vibe=vibe,
        intensity=intensity,
        style=style_key,
        query=query_payload["wallpaper_query"],
        query_payload=query_payload,
        repeated_count=repeated_count,
        novelty_hint=novelty_hint,
    )

    return {
        **query_payload,
        "wallpaper_preview_url": alternates[0]["preview_url"],
        "wallpaper_source": alternates[0]["source"],
        "wallpaper_provider": provider,
        "wallpaper_cached_path": alternates[0]["cached_path"],
        "wallpaper_alternates": alternates,
        "prompt_components": prompt_components,
        "generation_metadata": generation_metadata,
        "novelty_context": novelty_context,
        "visual_fit": visual_fit,
        "visual_grammar": visual_grammar,
    }
