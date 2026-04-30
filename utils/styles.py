from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    key: str
    emoji: str
    label_key: str
    suffix: str


STYLES: tuple[Style, ...] = (
    Style("photo", "📷", "style.photo", "professional photography, 8k, hyperrealistic, sharp focus"),
    Style("anime", "🎌", "style.anime", "anime style, studio ghibli, vibrant colors"),
    Style("digital", "🎨", "style.digital", "digital painting, artstation trending, concept art"),
    Style("oil", "🖼", "style.oil", "oil painting, classical art, museum quality"),
    Style("3d", "🤖", "style.3d", "3d render, octane render, unreal engine 5"),
    Style("cyberpunk", "🌃", "style.cyberpunk", "cyberpunk, neon lights, blade runner aesthetic"),
    Style("sketch", "✏️", "style.sketch", "pencil sketch, hand drawn, detailed line art"),
)

STYLES_BY_KEY: dict[str, Style] = {s.key: s for s in STYLES}


def apply_style(prompt: str, style_key: str | None) -> str:
    if not style_key or style_key not in STYLES_BY_KEY:
        return prompt
    suffix = STYLES_BY_KEY[style_key].suffix
    return f"{prompt}, {suffix}"
