from __future__ import annotations

import hashlib
import urllib.parse

from .cache import cache_image


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


def generated_future_provider(query: str, intensity: str, count: int = 3) -> list[dict]:
    # Placeholder for future on-the-fly generation path.
    return curated_unsplash_provider(query, intensity, count=count)
