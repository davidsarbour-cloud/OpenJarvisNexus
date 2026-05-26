"""
Vault Core — ChromaDB vector store + Ollama embeddings.
Collections: conversations, forge_reports, orchestration, agent_memory, workflows
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings

_BACKEND_DIR = Path(__file__).parent.parent
VAULT_DIR    = _BACKEND_DIR / "vault_data"
VAULT_DIR.mkdir(exist_ok=True)

from config import OLLAMA_HOST

EMBED_MODEL  = os.getenv("VAULT_EMBED_MODEL", "nomic-embed-text")

# Singleton ChromaDB client
_client: chromadb.ClientAPI | None = None

def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(VAULT_DIR / "chromadb"),
            settings=Settings(anonymized_telemetry=False)
        )
    return _client

# Collections

COLLECTIONS = {
    "conversations":    "conv",
    "forge_reports":    "forge",
    "orchestration":    "orch",
    "agent_memory":     "agent",
    "workflows":        "workflow",
    "architecture":     "arch",
    "skills_superpowers": "skill_sp",
    "skills_obsidian":    "skill_obs",
    "brain":              "brain",
}
def get_collection(name: str):
    return get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )

async def embed(text: str) -> list[float] | None:
    """Génère un embedding via Ollama nomic-embed-text. Fallback: None."""
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text[:2000]},
                timeout=15,
            )
            if r.status_code == 200:
                return r.json().get("embedding")
    except Exception:
        pass
    return None

def make_id(text: str, prefix: str = "") -> str:
    """ID déterministe basé sur le contenu."""
    h = hashlib.md5(text.encode()).hexdigest()[:12]
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{ts}_{h}"
