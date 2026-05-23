"""
Memory Manager — ajouter, rechercher, résumer les mémoires.
"""
from __future__ import annotations
from datetime import datetime

from vault.vault_core import get_collection, embed, make_id


async def add_memory(
    collection_name: str,
    text: str,
    metadata: dict | None = None,
    pinned: bool = False,
) -> str:
    """Ajoute une mémoire dans la collection. Retourne l'ID."""
    col = get_collection(collection_name)
    doc_id = make_id(text, prefix=collection_name[:4] + "_")
    meta = {
        "timestamp": datetime.now().isoformat(),
        "pinned": str(pinned),
        **(metadata or {}),
    }
    # Convertir toutes les valeurs en str (ChromaDB requirement)
    meta = {k: str(v) for k, v in meta.items()}

    embedding = await embed(text)
    if embedding:
        col.add(documents=[text], embeddings=[embedding], metadatas=[meta], ids=[doc_id])
    else:
        col.add(documents=[text], metadatas=[meta], ids=[doc_id])
    return doc_id


async def search_memory(
    collection_name: str,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    """Recherche sémantique dans une collection."""
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    n = min(n_results, count)
    embedding = await embed(query)
    try:
        if embedding:
            results = col.query(
                query_embeddings=[embedding],
                n_results=n,
                include=["documents", "metadatas", "distances"],
            )
        else:
            results = col.query(
                query_texts=[query],
                n_results=n,
                include=["documents", "metadatas", "distances"],
            )
        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]
        return [
            {"text": d, "metadata": m, "score": round(1 - dist, 3)}
            for d, m, dist in zip(docs, metas, distances)
        ]
    except Exception:
        return []


async def vault_query(query: str, collections: list[str] | None = None) -> list[dict]:
    """
    Requête cross-collection — utilisé par JARVIS avant chaque tâche majeure.
    Retourne les mémoires les plus pertinentes (collections + brain Obsidian).
    """
    cols = collections or list(get_collection_names().keys())
    # Toujours inclure le brain (notes Obsidian indexées via brain_index)
    if "brain" not in cols:
        cols = [*cols, "brain"]
    results = []
    for col_name in cols:
        hits = await search_memory(col_name, query, n_results=3)
        for h in hits:
            h["collection"] = col_name
            results.append(h)
    # Trier par score descendant
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:8]


def get_collection_names() -> dict:
    from vault.vault_core import COLLECTIONS
    return COLLECTIONS


def get_stats() -> dict:
    """Stats de toutes les collections."""
    stats = {}
    for name in get_collection_names():
        try:
            stats[name] = get_collection(name).count()
        except Exception:
            stats[name] = 0
    return stats

# Claude-Mem integration
async def save_to_claude_mem(
    memory_type: str,  # "conversation", "workflow", etc.
    content: str,
    metadata: dict | None = None,
) -> str:
    """Save memory to claude-mem for cross-session persistence"""
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            r = await c.post(
                "http://localhost:8084/api/memories",
                json={
                    "type": memory_type,
                    "content": content,
                    "metadata": metadata or {}
                },
                timeout=5,
            )
            if r.status_code == 200:
                return r.json().get("id", "saved")
    except Exception as e:
        print(f"[WARN] Claude-Mem save failed: {e}")
    return None