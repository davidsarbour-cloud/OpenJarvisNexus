"""Postprocess — apply platform masks + export to platform sizes.

Generators output a raw square (no rounding). This module:
  - applies a rounded-rectangle alpha mask (iOS squircle approximation,
    Android adaptive icon, none for Stream Deck);
  - resizes to each platform's canonical size.

  iOS         1024×1024  radius_frac ≈ 0.22 (Apple's squircle ≈ 22 % of side)
  Android      512×512   radius_frac ≈ 0.15 (Material adaptive icon mask)
  Stream Deck  144×144   no mask (the Deck shows the raw square)
"""
from __future__ import annotations

from PIL import Image, ImageDraw

PLATFORM_SIZES = {"ios": 1024, "android": 512, "streamdeck": 144}
PLATFORM_RADIUS_FRAC = {"ios": 0.22, "android": 0.15, "streamdeck": 0.0}


def apply_corner_mask(img: Image.Image, radius_frac: float) -> Image.Image:
    """Mask `img`'s corners with an alpha rounded-rectangle."""
    if radius_frac <= 0:
        return img.convert("RGBA")
    w, h = img.size
    radius = int(min(w, h) * radius_frac)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def export_for_platform(img: Image.Image, platform: str) -> Image.Image:
    """Return a fresh image masked + resized for `platform`."""
    target = PLATFORM_SIZES[platform]
    masked = apply_corner_mask(img, PLATFORM_RADIUS_FRAC[platform])
    if masked.size != (target, target):
        masked = masked.resize((target, target), Image.LANCZOS)
    return masked
