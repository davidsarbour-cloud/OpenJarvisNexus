"""ComfyUI image provider — thin adapter over the existing FLUX client.

Normalizes ``iconforge.generators.comfyui_client.ComfyUIClient`` to the
ImageFactory interface (prompt + size + seed -> PNG bytes) and owns the
FLUX-on-white -> transparent strip (rembg). No FLUX logic is duplicated: every
call delegates to the canonical ComfyUIClient.

FLUX (local, free, RTX 4070) is the bulk/production backend: seed-controlled,
no per-image cost. ``unload_ollama`` frees VRAM before a batch so FLUX FP8 fits.
"""
from __future__ import annotations

from iconforge.generators.comfyui_client import ComfyUIClient

__all__ = ["is_available", "unload_ollama", "render"]


def is_available() -> bool:
    """True if a ComfyUI server answers."""
    try:
        return ComfyUIClient().is_available()
    except Exception:
        return False


def unload_ollama() -> list[str]:
    """Evict Ollama models from VRAM so FLUX FP8 fits (best-effort, idempotent)."""
    try:
        return ComfyUIClient().unload_ollama()
    except Exception:
        return []


def _remove_bg(png: bytes) -> bytes:
    """Detour a render onto a transparent background (best-effort).

    FLUX renders on white; this strips it so the asset composites on anything.
    Returns the original bytes unchanged if rembg isn't installed or fails — the
    pipeline never breaks on a missing optional dependency.
    """
    try:
        from rembg import remove
        return remove(png)
    except Exception as e:
        print(f"[comfyui_images] rembg unavailable — keeping white bg: {e}")
        return png


def render(prompt: str, *, size: int = 1024, seed: int = 0, transparent: bool = False) -> bytes:
    """Render ONE FLUX image and return PNG bytes (sync — wrap in a thread).

    ``transparent`` strips the white background via rembg after generation.
    """
    px = int(size) if isinstance(size, int) else _px(size)
    png = ComfyUIClient().generate(prompt, int(seed), px)
    return _remove_bg(png) if transparent else png


def _px(size) -> int:
    """Coerce a size to an int pixel edge (accepts 1024 or '1024x1024')."""
    if isinstance(size, int):
        return size
    if isinstance(size, str) and "x" in size:
        try:
            return int(size.split("x", 1)[0])
        except ValueError:
            return 1024
    return 1024
