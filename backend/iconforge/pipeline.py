"""Orchestrator — brief → PNGs → manifest → recipe → README → Theme.zip.

The single entry point for the whole pipeline. Deterministic when the
generator is procedural (Phase 1).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from iconforge.brief import PackBrief
from iconforge.config import SETTINGS
from iconforge.exports.packager import build_zip
from iconforge.generators.procedural import render_pack
from iconforge.installer.readme_builder import build_readme
from iconforge.manifest import _slug, build_manifest
from iconforge.postprocess import PLATFORM_SIZES, export_for_platform
from iconforge.shortcuts.builder import build_recipe


@dataclass
class PackResult:
    pack_id:    str
    name:       str
    pack_dir:   Path
    zip_path:   Path
    icon_count: int
    platforms:  list[str]


def run_pack(brief: PackBrief) -> PackResult:
    """Generate every icon, apply platform masks/sizes, write manifest +
    recipe + README, zip the lot. Returns paths so callers can stream/download."""
    if brief.generator != "procedural":
        # Phase 2 → ComfyUI client. Probe is in router; here we just guard.
        raise NotImplementedError(
            "Phase 2 generator (ComfyUI/FLUX) — Phase 1 ships procedural only."
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pack_id = f"{_slug(brief.name)}_{ts}"
    pack_dir = SETTINGS.storage_dir / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    # 1. Render once at the largest target size, then downscale per platform.
    src_size = max(PLATFORM_SIZES[p] for p in brief.targets)
    sources = render_pack(brief, size=src_size)

    # 2. Export per-platform PNGs + accumulate a delivery tree.
    for platform in brief.targets:
        (pack_dir / platform).mkdir(parents=True, exist_ok=True)
        for spec in brief.icons:
            img = sources[spec.name]
            exported = export_for_platform(img, platform)
            exported.save(pack_dir / platform / f"{_slug(spec.name)}.png", "PNG")

    # 3. Manifest + recipe + README.
    (pack_dir / "manifest.json").write_text(
        json.dumps(build_manifest(brief, brief.targets), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (pack_dir / "shortcut_recipe.json").write_text(
        json.dumps(build_recipe(brief), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (pack_dir / "README.md").write_text(
        build_readme(brief, brief.targets), encoding="utf-8",
    )

    # 4. Zip the lot.
    zip_path = SETTINGS.storage_dir / f"{pack_id}.zip"
    build_zip(pack_dir, zip_path)

    return PackResult(
        pack_id=pack_id,
        name=brief.name,
        pack_dir=pack_dir,
        zip_path=zip_path,
        icon_count=len(brief.icons),
        platforms=brief.targets,
    )
