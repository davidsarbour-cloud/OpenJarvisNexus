"""VALKYRIE self-improvement memory — learns from its own generations.

The idea (kept deliberately simple, no ML stack): every image VALKYRIE makes is
logged to an append-only JSONL ledger with the *prompt modifiers* that were
appended to it. The implicit quality signal is **kept-vs-deleted**: an image
that survives is a soft "good", an image the user deletes is a hard "bad". Each
modifier accumulates (used, kept) counts; its score is a Bayesian-smoothed
keep-rate. ``enhance()`` then re-ranks a curated modifier pool by that score and
appends the current best ones — so prompts get measurably better as more images
are made and culled.

Why a JSONL ledger and not the DB: it is the robust source of truth (works with
ChromaDB/Ollama down) and trivially auditable. A best-effort mirror into the
``agent_memory`` ChromaDB collection (``mirror_to_memory``) makes generations
semantically searchable too, but the learning never depends on it.

Public API
  enhance(prompt, niche_type, k)      -> (final_prompt, modifiers_appended)
  record_generation(...)              -> None   (sync, ledger append)
  record_feedback(image_name, kept)   -> None   (sync, ledger append)
  await mirror_to_memory(text, meta)  -> None   (async, best-effort Chroma)
  stats()                             -> dict
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

_MEM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "valkyrie_memory"))
_LEDGER = os.path.join(_MEM_DIR, "ledger.jsonl")
os.makedirs(_MEM_DIR, exist_ok=True)

# ── Curated modifier pools ────────────────────────────────────────────────────
# These are quality enhancers appended to prompts. Learning RE-RANKS within a
# pool by measured keep-rate; it never invents free-text, so output stays safe
# and bounded. Extend a pool to widen what VALKYRIE can learn to prefer.
_THUMB_MODS = [
    "bold readable headline text", "high color saturation", "dramatic rim lighting",
    "exaggerated facial expression", "strong focal contrast", "cinematic depth",
]
_LOGO_MODS = [
    "clean vector lines", "balanced negative space", "minimal flat design",
    "scalable geometric mark", "professional brand palette", "crisp sharp edges",
]
_BRAND_MODS = [
    "professional studio lighting", "premium editorial composition", "rich color grading",
    "sharp high detail", "balanced typography space", "magazine-quality finish",
]
_GENERIC_MODS = [
    "ultra detailed", "professional lighting", "high contrast",
    "crisp sharp focus", "balanced composition", "vivid color",
]

_BRAND_NICHES = {"poster", "cover", "book_cover", "branding", "ad", "marketing", "mockup"}


def _pool_for(niche_type: str | None) -> list[str]:
    n = (niche_type or "").strip().lower()
    if n == "thumbnail":
        return _THUMB_MODS
    if n == "logo":
        return _LOGO_MODS
    if n in _BRAND_NICHES:
        return _BRAND_MODS
    return _GENERIC_MODS


# ── Ledger I/O ────────────────────────────────────────────────────────────────

def _append(rec: dict) -> None:
    """Append one JSON record to the ledger (best-effort, never raises)."""
    rec.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    try:
        with open(_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:  # learning is non-critical — never break a generation
        print(f"[valkyrie_memory] ledger append failed: {e}")


def _resolve_records() -> dict[str, dict]:
    """Replay the ledger into {image_id -> generation record}, applying the
    latest kept-state from any feedback rows (append-only, last write wins)."""
    out: dict[str, dict] = {}
    if not os.path.isfile(_LEDGER):
        return out
    try:
        with open(_LEDGER, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                kind = obj.get("kind")
                rid = obj.get("id")
                if not rid:
                    continue
                if kind == "gen":
                    out[rid] = obj
                elif kind == "fb" and rid in out:
                    out[rid]["kept"] = bool(obj.get("kept", True))
    except Exception as e:
        print(f"[valkyrie_memory] ledger read failed: {e}")
    return out


def _modifier_scores() -> dict[str, float]:
    """Bayesian-smoothed keep-rate per modifier: (kept+1)/(used+2) → prior 0.5."""
    used: dict[str, int] = {}
    kept: dict[str, int] = {}
    for rec in _resolve_records().values():
        survived = bool(rec.get("kept", True))
        for m in rec.get("modifiers", []) or []:
            used[m] = used.get(m, 0) + 1
            kept[m] = kept.get(m, 0) + (1 if survived else 0)
    return {m: (kept.get(m, 0) + 1) / (u + 2) for m, u in used.items()}


# ── Public API ────────────────────────────────────────────────────────────────

def enhance(prompt: str, niche_type: str | None = None, k: int = 3) -> tuple[str, list[str]]:
    """Append the current top-`k` learned modifiers for `niche_type` to `prompt`.

    Returns (final_prompt, modifiers_appended). Modifiers already present in the
    prompt are skipped so we never duplicate. With no history, the curated pool
    order is used (all priors equal), so day-one output is already sensible.
    """
    pool = _pool_for(niche_type)
    if not pool or k <= 0:
        return prompt, []
    scores = _modifier_scores()
    # Stable sort: learned score desc, then original pool order (index) as tiebreak.
    ranked = sorted(pool, key=lambda m: (-scores.get(m, 0.5), pool.index(m)))
    low = prompt.lower()
    chosen = [m for m in ranked if m.lower() not in low][:k]
    if not chosen:
        return prompt, []
    return prompt.rstrip(". ") + ", " + ", ".join(chosen), chosen


def record_generation(
    *,
    image_name: str,
    base_prompt: str,
    final_prompt: str,
    modifiers: list[str],
    niche_type: str | None = None,
    backend: str = "openai",
    hype_score: float | None = None,
) -> None:
    """Log a generation (kept defaults True until/unless the image is deleted)."""
    _append({
        "kind": "gen",
        "id": image_name,
        "base_prompt": base_prompt,
        "final_prompt": final_prompt,
        "modifiers": list(modifiers or []),
        "niche_type": niche_type,
        "backend": backend,
        "hype_score": hype_score,
        "kept": True,
    })


def record_feedback(image_name: str, kept: bool) -> None:
    """Log an explicit keep/delete signal for a previously generated image."""
    _append({"kind": "fb", "id": image_name, "kept": bool(kept)})


async def mirror_to_memory(text: str, metadata: dict | None = None) -> None:
    """Best-effort mirror of a generation note into the ``agent_memory`` Chroma
    collection so it is cross-agent searchable. Never raises — learning lives in
    the ledger, this is an optional convenience."""
    try:
        from vault.memory_manager import add_memory
        await add_memory("agent_memory", text, metadata=metadata or {}, pinned=False)
    except Exception as e:
        print(f"[valkyrie_memory] chroma mirror skipped: {e}")


def stats() -> dict:
    """Summary for the HUD/endpoint: totals, keep-rate, top modifiers."""
    records = _resolve_records()
    total = len(records)
    kept = sum(1 for r in records.values() if r.get("kept", True))
    scores = _modifier_scores()
    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:8]
    return {
        "total_generations": total,
        "kept": kept,
        "deleted": total - kept,
        "keep_rate": round(kept / total, 3) if total else None,
        "top_modifiers": [{"modifier": m, "score": round(s, 3)} for m, s in top],
    }
