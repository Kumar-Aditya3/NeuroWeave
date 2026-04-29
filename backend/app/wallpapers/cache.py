from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Callable

CACHE_ROOT = Path(__file__).resolve().parents[2] / "wallpaper_cache"


def cache_image(remote_url: str, cache_key: str) -> str | None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_ROOT / f"{cache_key}.jpg"
    if cache_path.exists():
        return str(cache_path)

    try:
        urllib.request.urlretrieve(remote_url, cache_path)
        return str(cache_path)
    except Exception:
        return None


def cache_generated_image(
    cache_key: str,
    writer: Callable[[Path], None],
    extension: str = "jpg",
    propagate_errors: bool = False,
) -> str | None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_ROOT / f"{cache_key}.{extension}"
    if cache_path.exists():
        return str(cache_path)

    try:
        writer(cache_path)
        return str(cache_path)
    except Exception:
        if propagate_errors:
            raise
        return None
