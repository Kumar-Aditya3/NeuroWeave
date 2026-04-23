from __future__ import annotations

import hashlib
import urllib.parse
import urllib.request
from pathlib import Path

from .anchors import WALLPAPER_STYLE_HINTS

CACHE_ROOT = Path(__file__).resolve().parents[1] / "wallpaper_cache"

TOPIC_BASE = {
    "tech": "futuristic workstation interface steel glass midnight city",
    "education": "study desk library books warm light focus room",
    "anime": "stylized cinematic city neon illustration expressive composition",
    "fitness": "athletic motion training energy strong contrast body momentum",
    "philosophy": "monochrome sculpture stone hall abstract reflective shadows",
    "self-help": "clean interior sunrise notebook ritual calm order",
    "news": "editorial world map newsroom information grid modern print feel",
    "unknown": "atmospheric modern texture soft geometry neutral desktop art",
}

VIBE_BASE = {
    "calm": "soft ambient spacious quiet serene",
    "balanced": "steady elegant grounded refined",
    "intense": "dynamic cinematic fast electric high-energy",
    "dark": "moody shadowed nocturnal dramatic",
}

PALETTE_MAP = {
    "calm": ["#a8c8bc", "#e6d6b8", "#39423f"],
    "balanced": ["#d6a85a", "#5f786c", "#f2eee4"],
    "intense": ["#f08b64", "#2e455f", "#d9d9d9"],
    "dark": ["#c2b8ae", "#202325", "#6e7f88"],
}


def _cache_image(remote_url: str, cache_key: str) -> str | None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_ROOT / f"{cache_key}.jpg"
    if cache_path.exists():
        return str(cache_path)

    try:
        urllib.request.urlretrieve(remote_url, cache_path)
        return str(cache_path)
    except Exception:
        return None


def build_wallpaper_payload(topic: str, vibe: str, intensity: str, style: str) -> dict:
    topic_prompt = TOPIC_BASE.get(topic, TOPIC_BASE["unknown"])
    vibe_prompt = VIBE_BASE.get(vibe, VIBE_BASE["balanced"])
    style_prompt = WALLPAPER_STYLE_HINTS.get(style, WALLPAPER_STYLE_HINTS["minimal"])

    wallpaper_query = f"{vibe_prompt} {topic_prompt} {style_prompt} desktop wallpaper"
    encoded_query = urllib.parse.quote(wallpaper_query)

    alternates = []
    for index in range(3):
        seed = hashlib.sha256(f"{wallpaper_query}:{intensity}:{index}".encode("utf-8")).hexdigest()[:8]
        remote_url = f"https://source.unsplash.com/featured/1600x900/?{encoded_query}&sig={seed}"
        cached_path = _cache_image(remote_url, seed)
        alternates.append(
            {
                "preview_url": remote_url,
                "cached_path": cached_path,
                "source": "Unsplash Source",
            }
        )

    return {
        "wallpaper_query": wallpaper_query,
        "wallpaper_preview_url": alternates[0]["preview_url"],
        "wallpaper_palette": PALETTE_MAP.get(vibe, PALETTE_MAP["balanced"]),
        "wallpaper_source": alternates[0]["source"],
        "wallpaper_cached_path": alternates[0]["cached_path"],
        "wallpaper_alternates": alternates,
    }
