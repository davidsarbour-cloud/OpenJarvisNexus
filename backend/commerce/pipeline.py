"""
Commerce Pipeline — orchestration complète:
idea → concept → STL → validation → metadata → approval → publish
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent.parent
COMMERCE_DIR = _BACKEND_DIR / "commerce_data"
COMMERCE_DIR.mkdir(exist_ok=True)

BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))

@dataclass
class ProductPipeline:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    idea: str = ""
    status: str = "pending"   # pending|concept|fabrication|validation|metadata|approval|draft_created|publishing|published|rejected
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Concept (ULTRON)
    concept: dict = field(default_factory=dict)

    # Fabrication (Forge Room)
    forge_mission_id: str = ""
    stl_path: str = ""
    printability_score: int = 0
    bambu_ready: bool = False

    # Metadata (ULTRON + GWEN)
    title: str = ""
    description: str = ""
    tags: list = field(default_factory=list)
    price_usd: float = 0.0
    category: str = ""

    # Approval
    requires_approval: bool = True
    approved: bool = False
    approved_by: str = ""
    approved_at: str = ""
    rejection_reason: str = ""

    # Publishing
    etsy_listing_id: str = ""
    shopify_product_id: str = ""
    published_at: str = ""

    # Analytics
    logs: list = field(default_factory=list)
    error: str = ""


_pipelines: dict[str, ProductPipeline] = {}
_PIPELINE_CACHE = COMMERCE_DIR / "pipeline_cache.json"


def _load_pipelines() -> None:
    if _PIPELINE_CACHE.exists():
        try:
            data = json.loads(_PIPELINE_CACHE.read_text(encoding="utf-8"))
            for pid, pdata in data.items():
                _pipelines[pid] = ProductPipeline(
                    **{k: v for k, v in pdata.items() if k in ProductPipeline.__dataclass_fields__}
                )
        except Exception:
            pass


def _save_pipelines() -> None:
    try:
        _PIPELINE_CACHE.write_text(
            json.dumps(
                {pid: asdict(p) for pid, p in _pipelines.items()},
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


_load_pipelines()


def _log(p: ProductPipeline, msg: str, level: str = "info") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    p.logs.append({"ts": ts, "msg": msg, "level": level})
    print(f"[COMMERCE:{p.id}] [{level.upper()}] {msg}")


def new_pipeline(idea: str) -> ProductPipeline:
    p = ProductPipeline(idea=idea)
    _pipelines[p.id] = p
    _save_pipelines()
    return p


def get_pipeline(pid: str) -> ProductPipeline | None:
    return _pipelines.get(pid.upper())


def list_pipelines() -> list[dict]:
    return [
        asdict(p)
        for p in sorted(_pipelines.values(), key=lambda x: x.created_at, reverse=True)
    ]


async def run_commerce_pipeline(pipeline_id: str) -> None:
    """Pipeline complet : concept → STL → metadata → approval queue."""
    from forge_room.fabrication_pipeline import (
        get_mission,
        new_mission,
        run_forge_pipeline,
    )

    p = _pipelines.get(pipeline_id)
    if not p:
        return

    try:
        # ── ÉTAPE 1 : Concept ULTRON ──────────────────────────────────
        p.status = "concept"
        _log(p, "ULTRON — génération du concept produit...")
        from commerce.metadata_gen import generate_concept
        p.concept = await generate_concept(p.idea)
        _log(p, f"Concept: {p.concept.get('title', '?')} — {p.concept.get('niche', '?')}")
        _save_pipelines()

        # ── ÉTAPE 2 : Forge Room STL (in-process, fusion 1->2) ────────
        p.status = "fabrication"
        _log(p, "FORGE ROOM — génération STL (in-process)...")
        m = new_mission(p.concept.get("forge_prompt", p.idea))
        p.forge_mission_id = m["id"]
        _log(p, f"Mission Forge: {p.forge_mission_id}")

        # Appel direct du pipeline de fabrication — plus de HTTP localhost ni polling.
        await run_forge_pipeline(m["id"])

        fd = get_mission(m["id"]) or {}
        if fd.get("status") != "completed":
            raise Exception(
                f"Forge failed: {fd.get('error') or 'status=' + str(fd.get('status'))}"
            )
        report = fd.get("report", {}) or {}
        p.printability_score = report.get("printability_score", 0)
        p.bambu_ready = report.get("bambu_ready", False)
        p.stl_path = fd.get("files", {}).get("final_stl", "")
        _log(
            p,
            f"STL: score={p.printability_score}/100, bambu_ready={p.bambu_ready}",
            "success",
        )
        _save_pipelines()

        # ── ÉTAPE 3 : Metadata ULTRON + GWEN ────────────────────────
        p.status = "metadata"
        _log(p, "ULTRON+GWEN — génération metadata SEO...")
        from commerce.metadata_gen import generate_listing_metadata
        meta = await generate_listing_metadata(p.idea, p.concept, p.printability_score)
        p.title       = meta.get("title", p.idea[:100])
        p.description = meta.get("description", "")
        p.tags        = meta.get("tags", [])
        p.price_usd   = meta.get("price_usd", 4.99)
        p.category    = meta.get("category", "3D Printing")
        _log(p, f"Metadata: '{p.title}' ${p.price_usd}")
        _save_pipelines()

        # ── ÉTAPE 4 : Human Approval Queue ───────────────────────────
        p.status = "approval"
        p.requires_approval = True
        p.approved = False
        _log(p, "En attente d'approbation humaine — HUMAN APPROVAL MODE", "warning")
        _save_pipelines()

        # Vault save
        try:
            from vault.memory_manager import add_memory
            await add_memory(
                "workflows",
                f"Product pipeline: '{p.title}' | Score: {p.printability_score}/100 | Price: ${p.price_usd}",
                {
                    "pipeline_id": p.id,
                    "status": "awaiting_approval",
                    "score": str(p.printability_score),
                },
            )
        except Exception:
            pass

    except Exception as e:
        import traceback
        p.status = "error"
        p.error  = str(e)
        _log(p, f"Pipeline error: {e}\n{traceback.format_exc()}", "error")
        _save_pipelines()
