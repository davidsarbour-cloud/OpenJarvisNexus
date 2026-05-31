"""ComfyUI client — FLUX Schnell FP8 generation for Phase 2 artistic packs.

Talks to the dockerized ComfyUI server (see ``iconforge/comfyui/``) over its
REST API: submit the workflow to ``/prompt``, poll ``/history/{id}``, fetch the
PNG from ``/view``. Synchronous on purpose — a pack batch is a long blocking
job and the FastAPI endpoints that drive it run in a threadpool.

VRAM contention: FLUX Schnell FP8 (~11 GB) cannot share 12 GB with Ollama
(qwen3:14b ~10 GB). ``unload_ollama()`` evicts Ollama before a batch; Ollama
reloads lazily on the next chat. The pipeline calls it once per ComfyUI pack.

``httpx`` is imported at module load (the backend already depends on it).
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import httpx

from iconforge.config import SETTINGS


class ComfyUIError(RuntimeError):
    """ComfyUI rejected the workflow or a node failed during execution."""


class ComfyUIClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or SETTINGS.comfyui_url).rstrip("/")

    # ── availability ────────────────────────────────────────────────────────
    def is_available(self) -> bool:
        """Probe ``/system_stats`` — True if a ComfyUI server is up."""
        try:
            r = httpx.get(f"{self.base_url}/system_stats", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    # ── VRAM handshake ──────────────────────────────────────────────────────
    def unload_ollama(self) -> list[str]:
        """Evict every model Ollama holds in VRAM so FLUX FP8 fits in 12 GB.

        Returns the model names it unloaded (empty if Ollama is down or already
        idle). Ollama reloads them on the next request, so calling this is
        always safe — worst case it's a no-op.
        """
        base = SETTINGS.ollama_url.rstrip("/")
        try:
            running = httpx.get(f"{base}/api/ps", timeout=3.0).json().get("models", [])
        except Exception:
            return []
        unloaded: list[str] = []
        for m in running:
            name = m.get("name") or m.get("model")
            if not name:
                continue
            try:
                # keep_alive=0 tells Ollama to drop this model right after the call.
                httpx.post(
                    f"{base}/api/generate",
                    json={"model": name, "prompt": "", "keep_alive": 0},
                    timeout=30.0,
                )
                unloaded.append(name)
            except Exception:
                pass
        return unloaded

    # ── generation ──────────────────────────────────────────────────────────
    def _load_workflow(self) -> dict:
        return json.loads(Path(SETTINGS.comfyui_workflow).read_text(encoding="utf-8"))

    def generate(self, prompt: str, seed: int, size: int = 1024,
                 style_ref: bytes | None = None, timeout: float = 300.0) -> bytes:
        """Render one icon via FLUX Schnell and return PNG bytes.

        ``style_ref`` (IP-Adapter visual coherence across a pack) is Phase 2b —
        accepted for forward-compat but not wired into the workflow yet.
        """
        wf = self._load_workflow()
        wf["6"]["inputs"]["text"] = prompt          # positive prompt
        wf["3"]["inputs"]["seed"] = int(seed)        # KSampler seed
        wf["5"]["inputs"]["width"] = size            # latent W
        wf["5"]["inputs"]["height"] = size           # latent H

        client_id = uuid.uuid4().hex
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{self.base_url}/prompt",
                       json={"prompt": wf, "client_id": client_id})
            r.raise_for_status()
            body = r.json()
            if body.get("node_errors"):
                raise ComfyUIError(f"workflow rejected: {body['node_errors']}")
            prompt_id = body["prompt_id"]
            entry = self._await_history(c, prompt_id, timeout)
            img = self._first_image(entry)
            v = c.get(f"{self.base_url}/view", params=img)
            v.raise_for_status()
            return v.content

    def _await_history(self, c: httpx.Client, prompt_id: str, timeout: float) -> dict:
        """Poll ``/history/{id}`` until the prompt completes; raise on error/timeout.

        Tolerates transient connection drops: ComfyUI (aiohttp) sometimes closes
        a keep-alive socket while the GPU is busy, so a single failed poll is
        retried rather than aborting a whole batch.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                entry = c.get(f"{self.base_url}/history/{prompt_id}").json().get(prompt_id)
            except httpx.TransportError:
                time.sleep(1.0)
                continue
            if entry is not None:
                status = entry.get("status", {})
                # status_str can be 'error' with completed=True — check error first.
                if status.get("status_str") == "error":
                    raise ComfyUIError(f"execution error: {status.get('messages')}")
                if status.get("completed"):
                    return entry
            time.sleep(1.0)
        raise ComfyUIError(f"timed out after {timeout:.0f}s waiting for {prompt_id}")

    @staticmethod
    def _first_image(entry: dict) -> dict:
        """Pull the first SaveImage output's view params out of a history entry."""
        for node_out in entry.get("outputs", {}).values():
            for im in node_out.get("images", []):
                return {"filename": im["filename"],
                        "subfolder": im.get("subfolder", ""),
                        "type": im.get("type", "output")}
        raise ComfyUIError("no image in ComfyUI output")
