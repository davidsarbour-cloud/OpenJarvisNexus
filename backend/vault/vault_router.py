"""
Vault Router — endpoints FastAPI pour le Vault Intelligence Hub.
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from vault.memory_manager import add_memory, search_memory, vault_query, get_stats
from vault.forge_learning import get_similar_forge
from vault.analytics import get_vault_analytics

router = APIRouter(prefix="/v1/vault", tags=["vault"])

class MemoryRequest(BaseModel):
    collection: str = "conversations"
    text: str
    metadata: dict = {}
    pinned: bool = False

@router.post("/memory")
async def create_memory(req: MemoryRequest):
    mid = await add_memory(req.collection, req.text, req.metadata, req.pinned)
    return {"ok": True, "id": mid, "collection": req.collection}

@router.get("/search")
async def search(q: str = Query(...), collection: str = "conversations", n: int = 5):
    results = await search_memory(collection, q, n)
    return {"query": q, "collection": collection, "results": results}

@router.get("/query")
async def jarvis_query(q: str = Query(...)):
    results = await vault_query(q)
    return {"query": q, "results": results, "count": len(results)}

@router.get("/stats")
def vault_stats():
    return {"collections": get_stats()}

@router.get("/analytics")
def vault_analytics():
    return get_vault_analytics()

@router.get("/forge/similar")
async def forge_similar(prompt: str = Query(...)):
    results = await get_similar_forge(prompt)
    return {"prompt": prompt, "similar": results}
