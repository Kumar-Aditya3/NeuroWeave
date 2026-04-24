from __future__ import annotations

from .styles import PALETTE_MAP, TOPIC_BASE, VIBE_BASE, WALLPAPER_STYLE_HINTS


def build_wallpaper_query(topic: str, vibe: str, intensity: str, style: str, arc_name: str | None) -> dict:
    topic_prompt = TOPIC_BASE.get(topic, TOPIC_BASE["unknown"])
    vibe_prompt = VIBE_BASE.get(vibe, VIBE_BASE["balanced"])
    style_prompt = WALLPAPER_STYLE_HINTS.get(style, WALLPAPER_STYLE_HINTS["minimal"])
    arc_fragment = f"{arc_name} " if arc_name else ""
    wallpaper_query = f"{arc_fragment}{vibe_prompt} {topic_prompt} {style_prompt} desktop wallpaper landscape 16:9"

    return {
        "wallpaper_query": wallpaper_query,
        "wallpaper_palette": PALETTE_MAP.get(vibe, PALETTE_MAP["balanced"]),
        "wallpaper_rationale": f"Based on current arc: {arc_name or 'general flow'} with a {vibe} {topic} mood and {style} treatment.",
        "recommendation_intensity": intensity,
        "wallpaper_style": style,
    }
