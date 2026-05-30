"""Pydantic schemas for a pack brief.

A brief is the SINGLE input that drives the whole pipeline: it specifies what
to generate (icons list), the style (theme), and the target platforms.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

GeneratorKind = Literal["procedural", "comfyui"]
Platform = Literal["ios", "android", "streamdeck"]


class IconSpec(BaseModel):
    """One icon in the pack."""
    name:       str = Field(..., description="Display name (e.g. 'Mail')")
    bundle_id:  Optional[str] = Field(
        None,
        description="iOS bundle id — required for the Siri Shortcut installer "
                    "to know what to open (e.g. 'com.apple.mobilesafari')",
    )
    label:      Optional[str] = Field(
        None,
        description="Short text to render in procedural mode (1-4 chars, defaults to first letter)",
    )
    prompt:     Optional[str] = Field(
        None,
        description="FLUX prompt subject for ComfyUI artistic mode",
    )


class PackBrief(BaseModel):
    """Everything needed to generate, validate, package, and list a pack."""
    name:        str = Field(..., description="Pack name (e.g. 'Minimal Black')")
    version:     str = "1.0.0"
    theme:       str = Field(..., description="One-line style brief")
    category:    str = "Minimal"

    generator:   GeneratorKind = "procedural"
    targets:     list[Platform] = Field(default_factory=lambda: ["ios"])

    # Style knobs (procedural). Hex strings (e.g. '#000000').
    bg_color:    str = "#000000"
    fg_color:    str = "#FFFFFF"
    # iOS squircle radius as a fraction of icon size (0 = sharp square, 0.22 ≈ iOS).
    corner_radius_frac: float = 0.22

    icons:       list[IconSpec] = Field(..., description="Icons to generate")
