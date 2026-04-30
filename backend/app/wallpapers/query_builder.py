from __future__ import annotations

from .styles import (
    INTENSITY_GRAMMAR,
    INTENSITY_HINTS,
    NEGATIVE_PROMPT,
    PALETTE_MAP,
    TOPIC_BASE,
    TOPIC_GRAMMAR,
    VIBE_BASE,
    VIBE_GRAMMAR,
    WALLPAPER_STYLE_HINTS,
)


def build_wallpaper_query(topic: str, vibe: str, intensity: str, style: str, arc_name: str | None) -> dict:
    topic_prompt = TOPIC_BASE.get(topic, TOPIC_BASE["unknown"])
    vibe_prompt = VIBE_BASE.get(vibe, VIBE_BASE["balanced"])
    style_prompt = WALLPAPER_STYLE_HINTS.get(style, WALLPAPER_STYLE_HINTS["minimal"])
    intensity_hint = INTENSITY_HINTS.get(intensity, INTENSITY_HINTS["balanced"])
    palette = PALETTE_MAP.get(vibe, PALETTE_MAP["balanced"])
    topic_grammar = TOPIC_GRAMMAR.get(topic, TOPIC_GRAMMAR["unknown"])
    vibe_grammar = VIBE_GRAMMAR.get(vibe, VIBE_GRAMMAR["balanced"])
    intensity_grammar = INTENSITY_GRAMMAR.get(intensity, INTENSITY_GRAMMAR["balanced"])
    arc_fragment = f"{arc_name}, " if arc_name else ""
    wallpaper_query = (
        f"{arc_fragment}{vibe_prompt}, {topic_prompt}, {style_prompt}, {intensity_hint}, "
        f"{topic_grammar['geometry']}, {topic_grammar['composition']}, "
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
        },
    }
