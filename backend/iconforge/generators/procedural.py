"""Procedural generator — Pillow-based, deterministic, zero VRAM cost.

Renders a solid colored square with a centered text label. The Phase-1 pilot
("Minimal Black") uses this. No diffusion model is involved → no consistency
risk, no GPU contention with Ollama.

Output: an RGBA Image of size×size, with the BACKGROUND extended to all four
corners (NO corner rounding here — postprocess applies the platform mask).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from iconforge.brief import IconSpec, PackBrief
from iconforge.config import SETTINGS

# ── Font resolution ──────────────────────────────────────────────────────────
# Try (1) brief-/env-configured path, then (2) common system fonts, then
# (3) Pillow's default bitmap font as a last resort.

_WIN_FONTS = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf",
              r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\segoeui.ttf"]
_LINUX_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
_MAC_FONTS = ["/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/SFNS.ttf"]


def _find_font_path(override: str = "") -> str | None:
    for candidate in [override, SETTINGS.font_path, *_WIN_FONTS, *_LINUX_FONTS, *_MAC_FONTS]:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def _load_font(path: str | None, size: int) -> ImageFont.ImageFont:
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _parse_hex(c: str) -> tuple[int, int, int]:
    s = c.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


# ── Single-icon render ──────────────────────────────────────────────────────

def render_icon(spec: IconSpec, brief: PackBrief, size: int = 1024,
                font_override: str = "") -> Image.Image:
    """Render ONE icon as a solid-bg square with the spec's label centered."""
    bg = _parse_hex(brief.bg_color) + (255,)
    fg = _parse_hex(brief.fg_color) + (255,)
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)

    label = (spec.label or spec.name[:1]).strip()
    if not label:
        return img

    # Auto-fit: start at ~45 % of size, shrink if it overflows the safe area (80 %).
    font_path = _find_font_path(font_override)
    target = size  # sentinel; will be reduced if too wide
    safe = int(size * 0.78)
    font_size = int(size * 0.46)
    while font_size > 24:
        font = _load_font(font_path, font_size)
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
        except Exception:                       # default font fallback
            bbox = (0, 0, font_size * len(label) // 2, font_size)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= safe and h <= safe:
            target = (w, h, bbox[0], bbox[1])
            break
        font_size = int(font_size * 0.92)

    if isinstance(target, tuple):
        w, h, ox, oy = target
        pos = ((size - w) // 2 - ox, (size - h) // 2 - oy)
        draw.text(pos, label, fill=fg, font=font)
    return img


def render_pack(brief: PackBrief, size: int = 1024) -> dict[str, Image.Image]:
    """Render every icon in `brief`. Returns {icon_name: PIL.Image}."""
    return {spec.name: render_icon(spec, brief, size=size) for spec in brief.icons}


# ── Tiny smoke test ─────────────────────────────────────────────────────────
if __name__ == "__main__":                                # pragma: no cover
    from iconforge.catalog import minimal_black_pilot
    out = Path(__file__).parent.parent / "storage" / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    for name, img in render_pack(minimal_black_pilot()).items():
        safe = name.lower().replace(" ", "_")
        img.save(out / f"{safe}.png")
    print(f"wrote {len(list(out.glob('*.png')))} icons to {out}", file=sys.stderr)
