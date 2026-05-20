"""
index_skills.py — Indexe les SKILL.md de Superpowers + Obsidian dans ChromaDB
Run once: python index_skills.py
"""
import asyncio
import sys
from pathlib import Path

# Ajouter backend au PYTHONPATH pour importer vault.*
sys.path.insert(0, str(Path(__file__).parent))

from vault.memory_manager import add_memory, get_stats

SUPERPOWERS_DIR = Path(r"C:\Users\bobby\superpowers\skills")
OBSIDIAN_DIR    = Path(r"C:\Users\bobby\obsidian-skills\skills")

async def index_folder(folder: Path, collection: str, source: str):
    """Indexe tous les SKILL.md d'un dossier dans une collection."""
    if not folder.exists():
        print(f"[SKIP] {folder} not found")
        return 0
    
    count = 0
    for skill_dir in folder.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        
        text = skill_file.read_text(encoding="utf-8", errors="ignore")
        meta = {
            "source": source,
            "skill_name": skill_dir.name,
            "path": str(skill_file),
        }
        doc_id = await add_memory(collection, text, metadata=meta, pinned=True)
        print(f"  [OK] {source}/{skill_dir.name} -> {doc_id[:20]}...")
        count += 1
    return count

async def main():
    print("=" * 60)
    print("NEXUS9 - Skills Indexer")
    print("=" * 60)
    
    print("\n[1/2] Indexing Superpowers skills...")
    sp_count = await index_folder(
        SUPERPOWERS_DIR,
        "skills_superpowers",
        "superpowers"
    )
    
    print("\n[2/2] Indexing Obsidian skills...")
    obs_count = await index_folder(
        OBSIDIAN_DIR,
        "skills_obsidian",
        "obsidian"
    )
    
    print("\n" + "=" * 60)
    print(f"DONE - {sp_count} Superpowers + {obs_count} Obsidian indexed")
    print("=" * 60)
    
    print("\nVault stats:")
    stats = get_stats()
    for col, count in stats.items():
        marker = " <-- NEW" if "skills_" in col else ""
        print("  " + col.ljust(25) + " " + str(count).rjust(4) + " items" + marker)

if __name__ == "__main__":
    asyncio.run(main())
