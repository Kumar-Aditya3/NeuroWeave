TOPIC_BASE = {
    "tech": "glowing circuit traces, soft teal data lines, futuristic glass panels",
    "education": "knowledge spaces, warm study light, ordered architectural lines",
    "anime": "stylized skyline, neon gradients, dreamlike motion",
    "fitness": "kinetic motion trails, athletic rhythm, sharp contrast",
    "philosophy": "sculptural forms, stone texture, contemplative depth",
    "self-help": "sunrise clarity, calm ritual objects, balanced space",
    "news": "editorial grids, global patterns, modern print texture",
    "unknown": "atmospheric geometry, layered light, uncluttered focus",
}

VIBE_BASE = {
    "calm": "serene, airy, restorative",
    "balanced": "grounded, elegant, composed",
    "intense": "electric, cinematic, high-energy",
    "dark": "moody, nocturnal, shadow-rich",
}

PALETTE_MAP = {
    "calm": ["#a8c8bc", "#e6d6b8", "#39423f"],
    "balanced": ["#d6a85a", "#5f786c", "#f2eee4"],
    "intense": ["#f08b64", "#2e455f", "#d9d9d9"],
    "dark": ["#c2b8ae", "#202325", "#6e7f88"],
}

TOPIC_GRAMMAR = {
    "tech": {"geometry": "layered circuit lattices and signal paths", "composition": "structured asymmetric grid", "density": "medium"},
    "education": {"geometry": "measured frames, shelves, and ruled lines", "composition": "ordered horizon bands", "density": "medium"},
    "anime": {"geometry": "radiant streaks, crescents, and stylized bursts", "composition": "central cinematic vanishing point", "density": "high"},
    "fitness": {"geometry": "kinetic diagonals and impact arcs", "composition": "forward-driving diagonals", "density": "high"},
    "philosophy": {"geometry": "monolithic columns and concentric forms", "composition": "quiet monumental balance", "density": "low"},
    "self-help": {"geometry": "soft ritual shapes and rising gradients", "composition": "open breathing space", "density": "low"},
    "news": {"geometry": "editorial blocks, columns, and ticker bands", "composition": "modular headline grid", "density": "medium"},
    "unknown": {"geometry": "abstract planes and layered contours", "composition": "clean exploratory balance", "density": "medium"},
}

VIBE_GRAMMAR = {
    "calm": {"color_energy": "muted and restorative", "contrast": "soft", "motion": "slow"},
    "balanced": {"color_energy": "measured and grounded", "contrast": "moderate", "motion": "steady"},
    "intense": {"color_energy": "charged and vivid", "contrast": "high", "motion": "fast"},
    "dark": {"color_energy": "nocturnal and shadow-heavy", "contrast": "deep", "motion": "hushed"},
}

INTENSITY_GRAMMAR = {
    "low": {"detail": "restrained", "negative_space": "generous"},
    "balanced": {"detail": "readable", "negative_space": "balanced"},
    "high": {"detail": "rich", "negative_space": "compressed"},
}

WALLPAPER_STYLE_HINTS = {
    "minimal": "minimal abstract composition, premium surface texture",
    "cinematic": "cinematic lighting, immersive depth",
    "warm": "warm ambient glow, soft gradients",
    "neon": "neon futurism, vibrant night glow",
    "editorial": "editorial art direction, refined layout",
}

INTENSITY_HINTS = {
    "low": "subtle motion, restful pacing",
    "balanced": "moderate motion, readable detail",
    "high": "bold motion, dramatic contrast",
}

NEGATIVE_PROMPT = (
    "text, letters, logo, watermark, frame, border, person, face, hands, anatomy, "
    "photograph of a real room, lowres, blurry, noisy, distorted, duplicated elements, "
    "busy collage, clutter, artifacts, oversaturated highlights"
)
