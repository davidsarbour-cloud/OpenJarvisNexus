"""OpenAI gpt-image-1 image-generation service (shared).

Single source of truth for talking to the OpenAI Images API. Consumed by:
  • valkyrie_router  — the VALKYRIE agent page (/v1/valkyrie/*)
  • image_factory    — premium factory assets (auto_factory)

Mirrors the httpx + Bearer pattern of forge_room/meshy_bridge — NO new
dependency (the `openai` SDK is not installed). A dedicated AsyncClient with a
long timeout is created per call: image generation is punctual, never polled,
so a client per request is negligible and dodges the shared 30s client limit.

gpt-image-1 requires a *verified* OpenAI org — an unverified org returns 403,
surfaced verbatim through OpenAIImageError.
"""
from __future__ import annotations

import base64

import httpx
from app_state import OPENAI_API_KEY

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-1"

# gpt-image-1 constraints.
VALID_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}
VALID_QUALITIES = {"low", "medium", "high", "auto"}
VALID_BACKGROUNDS = {"transparent", "opaque", "auto"}

# Per-image cost estimate (USD) — gpt-image-1 (~$40 / 1M image tokens).
_COST_TABLE = {
    ("1024x1024", "low"): 0.011, ("1024x1024", "medium"): 0.042, ("1024x1024", "high"): 0.167,
    ("1024x1536", "low"): 0.016, ("1024x1536", "medium"): 0.063, ("1024x1536", "high"): 0.25,
    ("1536x1024", "low"): 0.016, ("1536x1024", "medium"): 0.063, ("1536x1024", "high"): 0.25,
}


class OpenAIImageError(RuntimeError):
    """OpenAI rejected the request (bad key, unverified org, quota, …)."""


def is_available() -> bool:
    """True if an OpenAI key is configured (gpt-image-1 reachable)."""
    return bool(OPENAI_API_KEY)


def estimate_cost(size: str, quality: str, n: int) -> float:
    return round(_COST_TABLE.get((size, quality), 0.042) * max(1, n), 4)


async def generate(
    prompt: str,
    *,
    size: str = "1024x1024",
    quality: str = "high",
    n: int = 1,
    background: str | None = None,
    timeout: float = 180.0,
) -> list[bytes]:
    """Generate ``n`` images, return a list of raw PNG bytes (b64-decoded).

    Raises OpenAIImageError on a missing key or any non-200 response (the raw
    OpenAI error text is included so callers can surface org-verification etc.).
    Lets httpx.TimeoutException propagate so callers can map it to a 504.
    """
    if not is_available():
        raise OpenAIImageError("OPENAI_API_KEY manquant")

    size = size if size in VALID_SIZES else "1024x1024"
    quality = quality if quality in VALID_QUALITIES else "high"
    payload: dict = {
        "model": MODEL,
        "prompt": prompt,
        "n": max(1, n),
        "size": size,
        "quality": quality,
        "output_format": "png",
    }
    if background in VALID_BACKGROUNDS:
        payload["background"] = background

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as c:
        r = await c.post(
            OPENAI_IMAGES_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if r.status_code != 200:
        raise OpenAIImageError(f"OpenAI {r.status_code}: {r.text[:500]}")

    data = r.json()
    out = [base64.b64decode(d["b64_json"]) for d in data.get("data", []) if d.get("b64_json")]
    if not out:
        raise OpenAIImageError("OpenAI: réponse sans image")
    return out
