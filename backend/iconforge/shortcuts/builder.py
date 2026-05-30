"""Siri Shortcut "installer" recipe builder.

⚠️ HONEST CAVEAT: iOS does NOT let any Shortcut globally replace an app's home-
screen icon (Apple security). The "installer" generates N shortcuts of type
"Open <App>" with custom icon — but the BUYER still has to tap "Add to Home
Screen" for each icon (one confirmation per icon, imposed by iOS).

What we deliver is the RECIPE the buyer's Shortcuts app needs:
  - shortcut_recipe.json   — one entry per app: bundle id, app name, icon path
  - The buyer's installer Shortcut reads this JSON and creates the N child
    Shortcuts in a loop. Building the actual binary .shortcut file from Python
    is a Phase 1b deliverable (Apple's plist/signed format).

For now the recipe is human-readable AND machine-readable, and the README
(installer/readme_builder.py) walks the buyer through the manual flow.
"""
from __future__ import annotations

from iconforge.brief import PackBrief


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def build_recipe(brief: PackBrief) -> dict:
    """Schema-versioned recipe consumed by the installer Shortcut (Phase 1b)."""
    entries = []
    for spec in brief.icons:
        slug = _slug(spec.name)
        entries.append({
            "app_name":  spec.name,
            "bundle_id": spec.bundle_id,
            "icon":      f"ios/{slug}.png",
            "shortcut_name": f"Open {spec.name}",
        })
    return {
        "schema":  "iconforge.installer-recipe.v1",
        "pack":    brief.name,
        "version": brief.version,
        "note":    ("iOS requires one 'Add to Home Screen' confirmation per icon "
                    "(Apple security). The installer Shortcut loops over these "
                    "entries and creates one 'Open <App>' shortcut per entry "
                    "with the corresponding icon; the buyer then adds each to "
                    "the home screen."),
        "entries": entries,
    }
