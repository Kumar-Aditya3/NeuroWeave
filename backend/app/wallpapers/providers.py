from __future__ import annotations

import hashlib
from pathlib import Path
import urllib.parse

from .cache import cache_generated_image, cache_image
from .procedural import render_procedural_wallpaper
from .styles import PALETTE_MAP


def curated_unsplash_provider(query: str, intensity: str, count: int = 3, seed_offset: int = 0) -> list[dict]:
    encoded_query = urllib.parse.quote(query)
    alternates = []
    for index in range(count):
        signature_index = index + max(0, seed_offset)
        seed = hashlib.sha256(f"{query}:{intensity}:{signature_index}".encode("utf-8")).hexdigest()[:8]
        # Unsplash Source is no longer reliable and can return an app error page.
        # Use a deterministic Picsum seed URL so the preview is always an image.
        remote_url = f"https://picsum.photos/seed/{seed}-{encoded_query}/1920/1080"
        alternates.append(
            {
                "preview_url": remote_url,
                "cached_path": cache_image(remote_url, seed),
                "source": "Picsum Seeded 16:9",
                "provider": "curated_unsplash",
            }
        )
    return alternates


def generated_future_provider(
    query: str,
    intensity: str,
    *,
    topic: str,
    vibe: str,
    style: str,
    count: int = 3,
    seed_offset: int = 0,
    base_url: str = "http://127.0.0.1:8000",
) -> list[dict]:
    alternates = []
    for index in range(count):
        signature_index = index + max(0, seed_offset)
        seed = hashlib.sha256(f"proc:{query}:{intensity}:{topic}:{vibe}:{style}:{signature_index}".encode("utf-8")).hexdigest()[:12]
        cache_key = f"proc-{seed}"
        cached_path = cache_generated_image(
            cache_key,
            lambda output: render_procedural_wallpaper(
                output,
                query=query,
                topic=topic,
                vibe=vibe,
                style=style,
                palette=PALETTE_MAP.get(vibe, PALETTE_MAP["balanced"]),
                seed=seed,
            ),
            extension="jpg",
        )
        if cached_path:
            preview_url = f"{base_url.rstrip('/')}/wallpapers/cache/{Path(cached_path).name}"
            alternates.append(
                {
                    "preview_url": preview_url,
                    "cached_path": cached_path,
                    "source": "Procedural Mood Generator",
                    "provider": "generated_future",
                }
            )
            continue

        fallback = curated_unsplash_provider(query, intensity, count=1, seed_offset=signature_index)[0]
        alternates.append(fallback)
    return alternates
