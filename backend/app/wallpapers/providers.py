from __future__ import annotations

import hashlib
from pathlib import Path
import urllib.parse

from .cache import cache_generated_image, cache_image
from .procedural import render_procedural_wallpaper
from .styles import PALETTE_MAP
from .diffusion import get_generator


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
    negative_prompt: str | None = None,
    count: int = 3,
    seed_offset: int = 0,
    base_url: str = "http://127.0.0.1:8000",
) -> list[dict]:
    """Generate wallpapers via diffusion (primary) with procedural/Picsum fallback."""
    alternates = []
    generator = get_generator()
    effective_count = count
    if generator.device != "cuda" or (generator.gpu_memory_gb is not None and generator.gpu_memory_gb <= 4.5):
        effective_count = 1
    
    for index in range(effective_count):
        signature_index = index + max(0, seed_offset)
        seed = hashlib.sha256(f"diff:{query}:{intensity}:{topic}:{vibe}:{style}:{signature_index}".encode("utf-8")).hexdigest()[:12]
        cache_key = f"diff-{seed}"
        
        # Try diffusion generation first
        generation_metadata = {"fallback_used": False}
        try:
            cached_path = cache_generated_image(
                cache_key,
                lambda output: _generate_diffusion_image(
                    output,
                    prompt=query,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    metadata_container=generation_metadata,
                ),
                extension="jpg",
                propagate_errors=True,
            )
            
            if cached_path:
                preview_url = f"{base_url.rstrip('/')}/wallpapers/cache/{Path(cached_path).name}"
                alternates.append({
                    "preview_url": preview_url,
                    "cached_path": cached_path,
                    "source": "Diffusion Generated Mood Wallpaper",
                    "provider": "generated_future",
                    "generation_metadata": generation_metadata,
                })
                continue
        except Exception as e:
            # Diffusion failed, fall through to procedural fallback
            generation_metadata["fallback_used"] = True
            generation_metadata["fallback_reason"] = str(e)
        
        # Fallback: procedural generation
        try:
            seed_proc = hashlib.sha256(f"proc:{query}:{intensity}:{topic}:{vibe}:{style}:{signature_index}".encode("utf-8")).hexdigest()[:12]
            cache_key_proc = f"proc-{seed_proc}"
            cached_path = cache_generated_image(
                cache_key_proc,
                lambda output: render_procedural_wallpaper(
                    output,
                    query=query,
                    topic=topic,
                    vibe=vibe,
                    style=style,
                    palette=PALETTE_MAP.get(vibe, PALETTE_MAP["balanced"]),
                    seed=seed_proc,
                ),
                extension="jpg",
            )
            
            if cached_path:
                preview_url = f"{base_url.rstrip('/')}/wallpapers/cache/{Path(cached_path).name}"
                alternates.append({
                    "preview_url": preview_url,
                    "cached_path": cached_path,
                    "source": "Procedural Mood Pattern Generator (Fallback)",
                    "provider": "generated_future",
                    "generation_metadata": {**generation_metadata, "fallback_to": "procedural"},
                })
                continue
        except Exception:
            pass
        
        # Final fallback: Picsum
        try:
            fallback = curated_unsplash_provider(query, intensity, count=1, seed_offset=signature_index)[0]
            fallback["generation_metadata"] = {**generation_metadata, "fallback_to": "picsum"}
            alternates.append(fallback)
        except Exception:
            pass
    
    return alternates


def _generate_diffusion_image(
    output_path: Path,
    prompt: str,
    negative_prompt: str | None,
    seed: str,
    metadata_container: dict,
) -> None:
    """Generate image via local diffusion pipeline and save to output_path."""
    try:
        generator = get_generator()
        image, metadata = generator.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=int(seed[:8], 16),
        )
        metadata_container.update(metadata)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="JPEG", quality=96, optimize=True, progressive=True)
    except Exception as e:
        raise RuntimeError(f"Failed to generate diffusion image: {e}")
