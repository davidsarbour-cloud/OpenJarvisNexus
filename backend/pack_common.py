"""Shared helpers for the Auto-Factory pack/bundle builders.

Extracted from the build_*.py scripts + recompose.py, where the hex->RGB parser
was byte-identical in 4 files and the TrueType font loader near-identical in 4.
One copy here prevents drift. Behavior is unchanged for every existing call site
(all used C:\\Windows\\Fonts and the same parse / load+fallback).
"""
from __future__ import annotations

from pathlib import Path

# Windows system font directory — every builder rendered covers from here.
WIN_FONTS = r"C:\Windows\Fonts"


def hex_rgb(c: str) -> tuple[int, int, int]:
    """'#d97757' (or 'd97757') -> (217, 119, 87)."""
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def load_font(name: str, size: int, fonts_dir: str = WIN_FONTS):
    """A Windows TrueType font by filename, falling back to PIL's default font
    if it can't be loaded (missing file / headless). PIL is imported lazily so
    importing this module never requires Pillow."""
    from PIL import ImageFont

    try:
        return ImageFont.truetype(str(Path(fonts_dir) / name), size)
    except Exception:
        return ImageFont.load_default()
