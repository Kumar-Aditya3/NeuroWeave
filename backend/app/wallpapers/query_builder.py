from __future__ import annotations

from .styles import (
    INTENSITY_GRAMMAR,
    INTENSITY_HINTS,
    NEGATIVE_PROMPT,
    PALETTE_MAP,
    TOPIC_ACCENT_MAP,
    TOPIC_BASE,
    TOPIC_GRAMMAR,
    VIBE_BASE,
    VIBE_GRAMMAR,
    WALLPAPER_STYLE_HINTS,
)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))


def _rgb_to_hex(color: tuple[int, int, int]) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


def _blend_hex(base: str, accent: str, amount: float) -> str:
    base_rgb = _hex_to_rgb(base)
    accent_rgb = _hex_to_rgb(accent)
    mixed = tuple(int(base_rgb[index] + ((accent_rgb[index] - base_rgb[index]) * amount)) for index in range(3))
    return _rgb_to_hex(mixed)


def _topic_tuned_palette(vibe: str, topic: str) -> list[str]:
    vibe_palette = PALETTE_MAP.get(vibe, PALETTE_MAP["balanced"])
    topic_accent = TOPIC_ACCENT_MAP.get(topic, TOPIC_ACCENT_MAP["unknown"])
    return [
        vibe_palette[0],
        _blend_hex(vibe_palette[1], topic_accent, 0.28),
        _blend_hex(vibe_palette[2], topic_accent, 0.62),
    ]


def build_wallpaper_query(
    topic: str,
    vibe: str,
    intensity: str,
    style: str,
    arc_name: str | None,
    transition_context: dict | None = None,
    preference_profile: dict[str, dict[str, float]] | None = None,
) -> dict:
    topic_prompt = TOPIC_BASE.get(topic, TOPIC_BASE["unknown"])
    vibe_prompt = VIBE_BASE.get(vibe, VIBE_BASE["balanced"])
    style_prompt = WALLPAPER_STYLE_HINTS.get(style, WALLPAPER_STYLE_HINTS["minimal"])
    intensity_hint = INTENSITY_HINTS.get(intensity, INTENSITY_HINTS["balanced"])
    palette = _topic_tuned_palette(vibe, topic)
    topic_accent = TOPIC_ACCENT_MAP.get(topic, TOPIC_ACCENT_MAP["unknown"])
    topic_grammar = TOPIC_GRAMMAR.get(topic, TOPIC_GRAMMAR["unknown"])
    vibe_grammar = VIBE_GRAMMAR.get(vibe, VIBE_GRAMMAR["balanced"])
    intensity_grammar = INTENSITY_GRAMMAR.get(intensity, INTENSITY_GRAMMAR["balanced"])
    transition_hint = ""
    if transition_context and transition_context.get("is_transitioning"):
        prev_topic = transition_context.get("previous_topic") or "prior state"
        transition_hint = f"gradual transition from {prev_topic} motifs, smooth continuity, "
    fitness_shape_hint = ""
    if topic == "fitness":
        fitness_shape_hint = (
            "readable fitness symbolism through sprint-lane geometry, impact rhythm, "
            "repeating training cadence, no ambiguous generic abstraction, "
        )
    preference_profile = preference_profile or {}
    topic_affinity = float(preference_profile.get("topic", {}).get(topic, 0.0))
    vibe_affinity = float(preference_profile.get("vibe", {}).get(vibe, 0.0))
    style_affinity = float(preference_profile.get("style", {}).get(style, 0.0))
    preference_hint = ""
    preference_state = "neutral"
    if max(topic_affinity, vibe_affinity, style_affinity) >= 0.75:
        preference_state = "reinforced"
        preference_hint = "personal preference reinforced, make the favored visual language more deliberate, "
    elif min(topic_affinity, vibe_affinity, style_affinity) <= -0.75:
        preference_state = "softened"
        preference_hint = "personal preference softened, reduce disliked intensity and avoid overusing this treatment, "
    arc_fragment = f"{arc_name}, " if arc_name else ""
    wallpaper_query = (
        f"{arc_fragment}{vibe_prompt}, {topic_prompt}, {style_prompt}, {intensity_hint}, "
        f"{transition_hint}"
        f"{fitness_shape_hint}"
        f"{preference_hint}"
        f"{topic_grammar['geometry']}, {topic_grammar['composition']}, "
        f"palette anchored by {palette[0]} {palette[1]} with {topic_accent} semantic accent, "
        f"{vibe_grammar['color_energy']} color field, {vibe_grammar['contrast']} contrast, {vibe_grammar['motion']} motion, "
        f"{intensity_grammar['detail']} detail, {intensity_grammar['negative_space']} negative space, "
        f"abstract desktop wallpaper, premium digital art, atmospheric depth, "
        f"clean negative space, 16:9, no text, no logo"
    )

    return {
        "wallpaper_query": wallpaper_query,
        "wallpaper_palette": palette,
        "wallpaper_rationale": f"Based on current arc: {arc_name or 'general flow'} with a {vibe} {topic} mood and {style} treatment.",
        "recommendation_intensity": intensity,
        "wallpaper_style": style,
        "negative_prompt": NEGATIVE_PROMPT,
        "visual_grammar": {
            "topic": topic_grammar,
            "vibe": vibe_grammar,
            "intensity": intensity_grammar,
            "color": {
                "palette": palette,
                "semantic_accent": topic_accent,
                "strategy": "vibe base blended with topic accent",
            },
            "preference": {
                "state": preference_state,
                "topic_affinity": round(topic_affinity, 4),
                "vibe_affinity": round(vibe_affinity, 4),
                "style_affinity": round(style_affinity, 4),
            },
        },
    }
