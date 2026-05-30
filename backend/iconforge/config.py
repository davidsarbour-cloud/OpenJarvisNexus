"""IconForge settings — env-driven, single source of truth."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # Output directory for generated packs (each pack in its own subfolder).
    storage_dir: Path = field(default_factory=lambda: Path(
        os.getenv("ICONFORGE_STORAGE", str(Path(__file__).parent / "storage"))
    ))
    # ComfyUI server (artistic packs only — Minimal pilot is procedural).
    # Default :8188 is ComfyUI's standard port. Module degrades gracefully when down.
    comfyui_url: str = os.getenv("COMFYUI_URL", "http://localhost:8188")
    # Gumroad personal access token (sales channel #1 — set when you create one
    # at gumroad.com/settings/advanced). Empty = listing draft only, no auto-upload.
    gumroad_token: str = os.getenv("GUMROAD_ACCESS_TOKEN", "")
    # Optional system font for procedural rendering. Falls back to Pillow default.
    font_path: str = os.getenv("ICONFORGE_FONT", "")

    def __post_init__(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)


SETTINGS = Settings()
