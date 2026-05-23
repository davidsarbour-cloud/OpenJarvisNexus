import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from vault.memory_manager import search_memory

async def main():
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

asyncio.run(main())
