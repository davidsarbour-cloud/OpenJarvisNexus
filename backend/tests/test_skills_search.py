"""
Manual probe — query the vault skills_* collections to see what comes back.

Invoked as `python backend/tests/test_skills_search.py`. Guarded so
pytest doesn't fire the asyncio.run on collection.
"""
import asyncio
import sys
from pathlib import Path


async def main() -> None:
    # Import inside main() so pytest collection doesn't pull chromadb when
    # the venv it's running under doesn't have it.
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from vault.memory_manager import search_memory

    queries = [
        "comment debugger un probleme",
        "ecrire un plan pour mon projet",
        "automatiser obsidian",
    ]
    for q in queries:
        print(f"\n[Q] {q}")
        results = await search_memory("skills_superpowers", q, n_results=2)
        results += await search_memory("skills_obsidian", q, n_results=2)
        results.sort(key=lambda x: x["score"], reverse=True)
        for r in results[:3]:
            name = r["metadata"].get("skill_name", "?")
            print(f"  -> {name} (score: {r['score']})")


if __name__ == "__main__":
    asyncio.run(main())
