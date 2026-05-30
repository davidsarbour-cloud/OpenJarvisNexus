"""Per-pack manifest.json builder.

Shape (versioned, forward-compatible):

  {
    "schema":       "iconforge.pack.v1",
    "name":         "Minimal Black",
    "version":      "1.0.0",
    "theme":        "...",
    "category":     "Minimal",
    "generator":    "procedural",
    "generated_at": "2026-05-30T...",
    "icons": [
      {"name": "Mail", "bundle_id": "com.apple.mobilemail",
       "files": {"ios": "ios/mail.png", "android": "android/mail.png",
                 "streamdeck": "streamdeck/mail.png"}},
      ...
    ]
  }
"""
from __future__ import annotations

from datetime import datetime, timezone

from iconforge.brief import PackBrief


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def build_manifest(brief: PackBrief, platforms: list[str]) -> dict:
    icons = []
    for spec in brief.icons:
        slug = _slug(spec.name)
        icons.append({
            "name":      spec.name,
            "bundle_id": spec.bundle_id,
            "label":     spec.label,
            "files":     {p: f"{p}/{slug}.png" for p in platforms},
        })
    return {
        "schema":       "iconforge.pack.v1",
        "name":         brief.name,
        "version":      brief.version,
        "theme":        brief.theme,
        "category":     brief.category,
        "generator":    brief.generator,
        "platforms":    platforms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "icons":        icons,
    }
