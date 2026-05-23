"""
Brain -> Vault bridge.

Indexe les notes Markdown du brain Obsidian (backend/BRAIN/BRAIN) dans
ChromaDB (collection "brain"), pour que les agents puissent chercher
sémantiquement dans le savoir personnel de David.

- Le BRAIN reste la source humaine (markdown, lisible, graphe Obsidian).
- Le VAULT (ChromaDB) devient le moteur de recherche (vecteurs).

Idempotent : IDs déterministes basés sur le chemin -> ré-indexer met à jour
au lieu de dupliquer.

Usage:
    from vault.brain_index import index_brain, search_brain
    await index_brain()                       # (ré)indexe tout le brain
    hits = await search_brain("budget Etsy")  # recherche sémantique
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from vault.vault_core import get_collection, embed

BRAIN_PATH = Path(
    os.getenv("BRAIN_PATH", r"C:\OpenJarvisNexus\backend\BRAIN\BRAIN")
)
COLLECTION = "brain"
_EXCLUDE = {".obsidian", ".trash", ".git", "node_modules", "Templates", "imported"}


def _iter_notes(root: Path):
    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        if any(part in _EXCLUDE for part in rel.parts):
            continue
        yield p


def _meta(p: Path, root: Path, text: str) -> dict:
    rel = str(p.relative_to(root)).replace("\\", "/")
    tags = ""
    m = re.search(r"^tags:\s*\[([^\]]*)\]", text, re.MULTILINE)
    if m:
        tags = ", ".join(t.strip().strip("\"'") for t in m.group(1).split(",") if t.strip())
    return {
        "path": rel,
        "title": p.stem,
        "folder": rel.split("/")[0] if "/" in rel else "",
        "tags": tags,
        "source": "brain",
    }


async def index_brain(brain_path: str | None = None) -> dict:
    """Embed chaque note du brain dans la collection ChromaDB 'brain'."""
    root = Path(brain_path) if brain_path else BRAIN_PATH
    if not root.exists():
        return {"ok": False, "error": f"brain introuvable: {root}"}
    col = get_collection(COLLECTION)
    indexed = skipped = 0
    for p in _iter_notes(root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if len(text.strip()) < 30:
            skipped += 1
            continue
        vec = await embed(text[:4000])
        meta = _meta(p, root, text)
        doc_id = "brain_" + meta["path"]
        if vec:
            col.upsert(documents=[text[:8000]], embeddings=[vec], metadatas=[meta], ids=[doc_id])
        else:
            col.upsert(documents=[text[:8000]], metadatas=[meta], ids=[doc_id])
        indexed += 1
    return {"ok": True, "collection": COLLECTION, "indexed": indexed,
            "skipped": skipped, "total": col.count()}


async def search_brain(query: str, n_results: int = 5) -> list[dict]:
    """Recherche sémantique dans le brain. Retourne path/title/score/excerpt."""
    col = get_collection(COLLECTION)
    n = col.count()
    if n == 0:
        return []
    vec = await embed(query)
    try:
        kw = dict(n_results=min(n_results, n), include=["documents", "metadatas", "distances"])
        res = col.query(query_embeddings=[vec], **kw) if vec else col.query(query_texts=[query], **kw)
        docs, metas, dists = res["documents"][0], res["metadatas"][0], res["distances"][0]
        return [
            {"path": m.get("path"), "title": m.get("title"),
             "score": round(1 - d, 3), "excerpt": doc[:240].replace("\n", " ")}
            for doc, m, d in zip(docs, metas, dists)
        ]
    except Exception:
        return []
