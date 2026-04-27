from __future__ import annotations

import hashlib
import math
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


def _rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return (color[0], color[1], color[2], alpha)


def _polygon(cx: float, cy: float, radius: float, sides: int, rotation: float) -> list[tuple[float, float]]:
    return [
        (
            cx + math.cos(rotation + (math.tau * index / sides)) * radius,
            cy + math.sin(rotation + (math.tau * index / sides)) * radius,
        )
        for index in range(sides)
    ]


def _draw_gradient(canvas: Image.Image, base_a: tuple[int, int, int], base_b: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    px = canvas.load()
    width, height = canvas.size
    for y in range(height):
        vertical = y / max(1, height - 1)
        for x in range(width):
            diagonal = (x / max(1, width - 1)) * 0.34
            radial = abs((x / width) - 0.72) * 0.18
            t = min(1.0, max(0.0, vertical * 0.72 + diagonal - radial))
            base = _blend(base_a, base_b, t)
            glow = max(0.0, 1.0 - math.hypot((x - width * 0.78) / width, (y - height * 0.22) / height) * 2.6)
            px[x, y] = _blend(base, accent, glow * 0.16)


def _draw_noise(draw: ImageDraw.ImageDraw, rng: random.Random, width: int, height: int, color: tuple[int, int, int], density: int) -> None:
    for _ in range(density):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        alpha = rng.randint(10, 28)
        draw.point((x, y), fill=_rgba(color, alpha))


def _draw_topic_motif(
    draw: ImageDraw.ImageDraw,
    rng: random.Random,
    *,
    topic: str,
    width: int,
    height: int,
    color: tuple[int, int, int],
    muted: tuple[int, int, int],
) -> None:
    if topic == "tech":
        step = 96
        for x in range(-step, width + step, step):
            draw.line((x, 0, x + width * 0.18, height), fill=_rgba(color, 52), width=1)
        for y in range(60, height, step):
            draw.line((0, y, width, y + rng.randint(-24, 24)), fill=_rgba(muted, 36), width=1)
        for _ in range(34):
            x = rng.randint(80, width - 80)
            y = rng.randint(80, height - 80)
            r = rng.randint(3, 8)
            draw.ellipse((x - r, y - r, x + r, y + r), outline=_rgba(color, 110), width=2)
            draw.line((x, y, x + rng.randint(-130, 130), y + rng.randint(-70, 70)), fill=_rgba(color, 50), width=1)
        return

    if topic == "education":
        for y in range(120, height - 80, 58):
            draw.line((140, y, width - 140, y + rng.randint(-4, 4)), fill=_rgba(muted, 50), width=2)
        for x in range(180, width - 120, 220):
            draw.rounded_rectangle((x, 150, x + 118, height - 150), radius=4, outline=_rgba(color, 42), width=3)
        return

    if topic == "anime":
        origin = (width * 0.5, height * 0.5)
        for index in range(44):
            angle = math.tau * index / 44 + rng.uniform(-0.025, 0.025)
            end = (origin[0] + math.cos(angle) * width, origin[1] + math.sin(angle) * height)
            draw.line((origin, end), fill=_rgba(color, rng.randint(18, 62)), width=rng.randint(1, 4))
        for _ in range(11):
            cx = rng.randint(160, width - 160)
            cy = rng.randint(120, height - 120)
            draw.arc((cx - 75, cy - 38, cx + 75, cy + 38), rng.randint(0, 120), rng.randint(190, 340), fill=_rgba(muted, 88), width=3)
        return

    if topic == "fitness":
        for _ in range(18):
            x = rng.randint(-120, width)
            y = rng.randint(80, height - 80)
            draw.line((x, y, x + rng.randint(180, 420), y - rng.randint(20, 110)), fill=_rgba(color, 88), width=rng.randint(5, 12))
        for _ in range(8):
            cx = rng.randint(220, width - 220)
            cy = rng.randint(160, height - 160)
            draw.arc((cx - 110, cy - 110, cx + 110, cy + 110), 210, 510, fill=_rgba(muted, 76), width=5)
        return

    if topic == "philosophy":
        for cx in range(240, width, 330):
            draw.rectangle((cx - 34, 230, cx + 34, height - 190), fill=_rgba(muted, 22), outline=_rgba(color, 54), width=2)
            draw.line((cx - 70, 230, cx + 70, 230), fill=_rgba(color, 72), width=4)
            draw.line((cx - 86, height - 190, cx + 86, height - 190), fill=_rgba(color, 64), width=4)
        for radius in range(130, 520, 72):
            draw.ellipse((width * 0.62 - radius, height * 0.48 - radius, width * 0.62 + radius, height * 0.48 + radius), outline=_rgba(color, 22), width=2)
        return

    if topic == "news":
        for y in range(120, height - 100, 92):
            draw.rectangle((100, y, width - 100, y + 28), fill=_rgba(muted, 36))
            draw.line((120, y + 46, width - 220, y + 46), fill=_rgba(color, 42), width=2)
        return

    for _ in range(22):
        cx = rng.randint(100, width - 100)
        cy = rng.randint(100, height - 100)
        sides = rng.choice([3, 4, 5, 6])
        points = _polygon(cx, cy, rng.randint(34, 96), sides, rng.random() * math.tau)
        draw.polygon(points, outline=_rgba(color, 62), fill=_rgba(muted, 12))


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

    canvas = Image.new("RGB", (width, height), color=base_a)
    _draw_gradient(canvas, base_a, base_b, accent)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    muted = _blend(base_a, base_b, 0.55)

    if vibe == "calm":
        for radius in range(120, 760, 90):
            draw.ellipse(
                (width * 0.58 - radius, height * 0.46 - radius * 0.56, width * 0.58 + radius, height * 0.46 + radius * 0.56),
                outline=_rgba(accent, 32),
                width=2,
            )
    elif vibe == "balanced":
        for x in range(90, width, 130):
            draw.line((x, 0, x - 180, height), fill=_rgba(accent, 30), width=2)
        for y in range(70, height, 116):
            draw.line((0, y, width, y), fill=_rgba(muted, 28), width=1)
    elif vibe == "intense":
        for _ in range(36):
            x = rng.randint(-100, width - 50)
            y = rng.randint(40, height - 40)
            draw.polygon(
                [(x, y), (x + rng.randint(260, 620), y - rng.randint(24, 120)), (x + rng.randint(160, 460), y + rng.randint(26, 130))],
                fill=_rgba(accent, rng.randint(26, 72)),
            )
    else:
        for _ in range(20):
            cx = rng.randint(80, width - 80)
            cy = rng.randint(80, height - 80)
            radius = rng.randint(80, 280)
            draw.regular_polygon((cx, cy, radius), n_sides=rng.choice([3, 4, 5]), rotation=rng.randint(0, 90), outline=_rgba(accent, 54), fill=_rgba((8, 10, 12), 18))

    _draw_topic_motif(draw, rng, topic=topic, width=width, height=height, color=accent, muted=muted)

    if style == "neon":
        glow = overlay.filter(ImageFilter.GaussianBlur(radius=18))
        overlay = Image.alpha_composite(glow, overlay)
    elif style == "warm":
        draw.rectangle((0, 0, width, height), fill=(255, 184, 90, 18))
    elif style == "editorial":
        draw.rectangle((72, 70, width - 72, height - 70), outline=_rgba(accent, 70), width=2)
        draw.line((width * 0.64, 70, width * 0.64, height - 70), fill=_rgba(muted, 42), width=2)

    texture = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    texture_draw = ImageDraw.Draw(texture, "RGBA")
    _draw_noise(texture_draw, rng, width, height, _blend(accent, (255, 255, 255), 0.45), density=width * height // 1800)
    overlay = Image.alpha_composite(overlay, texture)
    result = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    if style == "cinematic":
        vignette = Image.new("L", (width, height), 0)
        vg_draw = ImageDraw.Draw(vignette)
        vg_draw.ellipse((-width // 4, -height // 3, width + width // 4, height + height // 3), fill=175)
        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=130))
        shade = Image.new("RGB", (width, height), (8, 8, 10))
        result = Image.composite(result, shade, vignette)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, format="JPEG", quality=96, optimize=True, progressive=True)
