"""ComfyUI client — skeleton for Phase 2 artistic packs (FLUX Schnell FP8).

Phase 1 (Minimal Black) is procedural so this is not on the critical path.
The skeleton is here so the pipeline can probe availability and so Phase 2 can
fill `generate()` with a real workflow (text-to-image + style reference) when
ComfyUI is installed and running on the configured port.

VRAM contention: FLUX Schnell FP8 (~7 GB) + T5XXL FP8 (~5 GB) on a 12 GB RTX
4070 Super means Ollama (qwen3:14b ~10 GB) MUST be unloaded during a batch
generation. The pipeline orchestrator is responsible for that handshake.

`httpx` is imported lazily so this module imports without it installed.
"""
from __future__ import annotations

from iconforge.config import SETTINGS


class ComfyUIClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or SETTINGS.comfyui_url).rstrip("/")

    async def is_available(self) -> bool:
        """Probe /system_stats — returns True if a ComfyUI server is up."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as c:
                r = await c.get(f"{self.base_url}/system_stats")
                return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, seed: int, size: int = 1024,
                       style_ref: bytes | None = None) -> bytes:
        """TODO Phase 2: queue a workflow on /prompt, poll /history, return PNG bytes.

        Workflow stub: FLUX Schnell FP8 + T5XXL FP8 + (optional IP-Adapter on
        style_ref) + EmptyLatentImage(size, size, 1) + Sampler(steps=4, cfg=1.0)
        + VAEDecode + SaveImage. Workflow JSON lives in templates/."""
        raise NotImplementedError(
            "Phase 2 — install ComfyUI + FLUX Schnell FP8, then implement workflow."
        )
