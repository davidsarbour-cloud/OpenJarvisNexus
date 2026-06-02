"""ImageFactory — the single image-generation abstraction (NEXUS9).

One entry point, ``render()``, dispatches to a backend so every caller stays
provider-agnostic. Add a provider = add a module under services/ + one branch.

Backends (config key ``auto_factory.image_backend``):
  • comfyui     — FLUX Schnell via ComfyUI (local, free, seed-controlled) [bulk]
  • gpt-image-1 — OpenAI gpt-image-1 (cloud, paid, native transparency + text)
  • auto        — premium niches -> gpt-image-1, everything else -> comfyui

The 95/5 rule: ~95% of factory assets are bulk (game assets, UI kits, icons,
sprites) and stay on free FLUX; ~5% are high-value text/branding/marketing
creatives where gpt-image-1's text fidelity actually moves sales.

Resolution always degrades gracefully: if gpt-image-1 is unavailable (no key /
unverified org), ``choose()`` falls back to FLUX so an unattended daily run
never fails on a paid-backend outage.
"""
from __future__ import annotations

import asyncio

from services import comfyui_images, openai_images

# Niche types whose text/branding/marketing quality justifies the paid backend.
# Extend this set as new premium product lines are added.
PREMIUM_NICHES = {
    "thumbnail", "logo", "pod_text", "book_cover", "branding",
    "ad", "marketing", "mockup", "poster", "cover",
}

# Config aliases that mean "use OpenAI gpt-image-1".
_OPENAI_ALIASES = {"gpt-image-1", "gpt_image_1", "gptimage1", "openai", "valkyrie"}


def resolve_backend(configured: str | None, niche_type: str | None = None) -> str:
    """Map a config value (+ niche) to a concrete backend: 'comfyui' | 'openai'."""
    c = (configured or "comfyui").strip().lower()
    if c in _OPENAI_ALIASES:
        return "openai"
    if c == "auto":
        return "openai" if (niche_type or "").strip().lower() in PREMIUM_NICHES else "comfyui"
    return "comfyui"


def choose(configured: str | None, niche_type: str | None = None) -> str:
    """Resolve a backend AND degrade gracefully if the paid one is unreachable."""
    backend = resolve_backend(configured, niche_type)
    if backend == "openai" and not openai_images.is_available():
        print("[image_factory] gpt-image-1 indisponible (clé/org) → fallback comfyui")
        return "comfyui"
    return backend


def is_available(backend: str) -> bool:
    """Liveness of a concrete backend ('comfyui' | 'openai')."""
    if backend == "openai":
        return openai_images.is_available()
    return comfyui_images.is_available()


async def prepare(backend: str) -> None:
    """Backend-specific pre-batch setup. FLUX: free VRAM by evicting Ollama."""
    if backend == "comfyui":
        await asyncio.to_thread(comfyui_images.unload_ollama)


def _openai_size(size) -> str:
    """Coerce a size to a valid gpt-image-1 dimension string."""
    if isinstance(size, str) and size in openai_images.VALID_SIZES:
        return size
    return "1024x1024"


async def render(
    prompt: str,
    *,
    size=1024,
    seed: int = 0,
    backend: str = "comfyui",
    transparent: bool = False,
    quality: str = "high",
) -> bytes:
    """Render ONE image and return PNG bytes.

    ``backend`` must be concrete ('comfyui' | 'openai') — resolve 'auto' via
    ``choose()`` first. ``transparent`` yields an alpha PNG: native for OpenAI
    (background=transparent), rembg-stripped for FLUX. ``seed`` is FLUX-only
    (deterministic packs); OpenAI has no seed. ``quality`` is OpenAI-only.
    """
    if backend == "openai":
        raws = await openai_images.generate(
            prompt,
            size=_openai_size(size),
            quality=quality,
            n=1,
            background="transparent" if transparent else None,
        )
        return raws[0]
    # FLUX/ComfyUI is synchronous — keep the event loop free.
    return await asyncio.to_thread(
        comfyui_images.render, prompt, size=size, seed=seed, transparent=transparent,
    )
