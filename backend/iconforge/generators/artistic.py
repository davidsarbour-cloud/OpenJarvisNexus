"""Artistic generator — FLUX Schnell via ComfyUI. Phase 2 packs.

Mirrors ``procedural.render_pack``: returns ``{icon_name: RGBA Image}`` at the
requested size, BACKGROUND extended to the corners (postprocess applies the
platform mask). The difference is each icon is diffused on the GPU instead of
drawn with Pillow.

Determinism: each icon gets a stable seed derived from its name, so re-running
a brief reproduces the same pack (and a fixed seed keeps a pack visually
coherent run-to-run). Phase 2b will add an IP-Adapter style reference for
cross-icon coherence within a single pack.
"""
from __future__ import annotations

import zlib
from io import BytesIO

from PIL import Image

from iconforge.brief import IconSpec, PackBrief
from iconforge.generators.comfyui_client import ComfyUIClient, ComfyUIError


def _seed_for(name: str) -> int:
    """Stable non-negative seed from an icon name (process-independent)."""
    return zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF


def _prompt_for(spec: IconSpec, brief: PackBrief) -> str:
    """Compose the FLUX prompt: icon subject + the pack's style brief."""
    subject = (spec.prompt or spec.name).strip()
    return f"app icon of {subject}, {brief.theme}, centered, single subject, flat background"


def render_pack(brief: PackBrief, size: int = 1024,
                client: ComfyUIClient | None = None) -> dict[str, Image.Image]:
    """Diffuse every icon in `brief` through ComfyUI. Returns {name: PIL.Image}.

    Unloads Ollama once up front (VRAM handshake) before the batch. Raises
    ``ComfyUIError`` if the server is unreachable so the caller fails loudly
    instead of silently producing nothing.
    """
    client = client or ComfyUIClient()
    if not client.is_available():
        raise ComfyUIError(
            f"ComfyUI not reachable at {client.base_url} — start it with "
            "`docker compose up -d` in iconforge/comfyui/."
        )

    client.unload_ollama()  # free VRAM for FLUX; Ollama reloads on next chat.

    out: dict[str, Image.Image] = {}
    for spec in brief.icons:
        png = client.generate(_prompt_for(spec, brief), seed=_seed_for(spec.name),
                              size=size)
        out[spec.name] = Image.open(BytesIO(png)).convert("RGBA")
    return out
