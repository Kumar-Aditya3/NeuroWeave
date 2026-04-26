from __future__ import annotations

import hashlib
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + ((b - a) * t))


def _blend(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t), _lerp(c1[2], c2[2], t))


def render_procedural_wallpaper(
    output_path: Path,
    *,
    query: str,
    topic: str,
    vibe: str,
    style: str,
    palette: list[str],
    seed: str,
    width: int = 1920,
    height: int = 1080,
) -> None:
    seed_value = int(hashlib.sha256(f"{seed}:{query}:{topic}:{vibe}:{style}".encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed_value)

    base_a = _hex_to_rgb(palette[0] if len(palette) > 0 else "#6d8592")
    base_b = _hex_to_rgb(palette[1] if len(palette) > 1 else "#b6a68c")
    accent = _hex_to_rgb(palette[2] if len(palette) > 2 else "#2f3238")

    # Build a smooth gradient base first, then layer translucent geometry for mood.
    canvas = Image.new("RGB", (width, height), color=base_a)
    px = canvas.load()
    for y in range(height):
        t = y / max(1, height - 1)
        row = _blend(base_a, base_b, t)
        for x in range(width):
            px[x, y] = row

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    shape_count = 34 if vibe in {"calm", "balanced"} else 56
    if style == "minimal":
        shape_count = max(18, shape_count - 14)
    if style == "neon":
        shape_count += 16

    for idx in range(shape_count):
        spread = 0.35 + (idx / max(1, shape_count))
        alpha = rng.randint(18, 95)
        c = (
            _lerp(accent[0], rng.randint(30, 255), spread * 0.35),
            _lerp(accent[1], rng.randint(30, 255), spread * 0.35),
            _lerp(accent[2], rng.randint(30, 255), spread * 0.35),
            alpha,
        )

        if vibe in {"calm", "balanced"}:
            w = rng.randint(width // 10, width // 3)
            h = rng.randint(height // 12, height // 4)
            x = rng.randint(-w // 2, width - 1)
            y = rng.randint(-h // 2, height - 1)
            draw.ellipse((x, y, x + w, y + h), fill=c)
        else:
            points = [
                (rng.randint(0, width), rng.randint(0, height))
                for _ in range(rng.randint(3, 6))
            ]
            draw.polygon(points, fill=c)

    blur_radius = 12 if vibe == "calm" else 8 if vibe == "balanced" else 5
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    result = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    if style == "cinematic":
        vignette = Image.new("L", (width, height), 0)
        vg_draw = ImageDraw.Draw(vignette)
        vg_draw.ellipse((-width // 4, -height // 3, width + width // 4, height + height // 3), fill=175)
        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=130))
        shade = Image.new("RGB", (width, height), (8, 8, 10))
        result = Image.composite(result, shade, vignette)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, format="JPEG", quality=92, optimize=True)
