"""
index_skills_enriched.py — Indexe les SKILL.md avec mots-cles FR/EN
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vault.memory_manager import add_memory

SUPERPOWERS_DIR = Path(r"C:\Users\bobby\superpowers\skills")
OBSIDIAN_DIR    = Path(r"C:\Users\bobby\obsidian-skills\skills")
KEYWORDS_FILE   = Path(__file__).parent / "vault" / "skills_keywords.json"

# Charger les mots-cles
if KEYWORDS_FILE.exists():
    KEYWORDS = json.loads(KEYWORDS_FILE.read_text(encoding="utf-8-sig"))
    print(f"[INFO] Loaded keywords for {len(KEYWORDS)} skills")
else:
    KEYWORDS = {}
    print("[WARN] No keywords file found")

def enrich(skill_name: str, text: str) -> tuple[str, bool]:
    """Ajoute les mots-cles au debut du texte si disponibles."""
    if skill_name not in KEYWORDS:
        return text, False
    kw = KEYWORDS[skill_name]
    all_kw = kw.get("keywords_fr", []) + kw.get("keywords_en", [])
    header = f"[KEYWORDS: {', '.join(all_kw)}]\n\n"
    return header + text, True

async def index_folder(folder: Path, collection: str, source: str):
    if not folder.exists():
        print(f"[SKIP] {folder} not found")
        return 0, 0
    count = 0
    enriched_count = 0
    for skill_dir in folder.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        text = skill_file.read_text(encoding="utf-8", errors="ignore")
        text, was_enriched = enrich(skill_dir.name, text)
        meta = {"source": source, "skill_name": skill_dir.name, "path": str(skill_file), "enriched": was_enriched}
        doc_id = await add_memory(collection, text, metadata=meta, pinned=True)
        marker = " [ENRICHED]" if was_enriched else ""
        print(f"  [OK] {source}/{skill_dir.name}{marker}")
        count += 1
        if was_enriched:
            enriched_count += 1
    return count, enriched_count

async def main():
    print("=" * 60)
    print("NEXUS9 - Skills Indexer (ENRICHED)")
    print("=" * 60)
    print("\n[1/2] Superpowers...")
    sp, sp_e = await index_folder(SUPERPOWERS_DIR, "skills_superpowers", "superpowers")
    print("\n[2/2] Obsidian...")
    obs, obs_e = await index_folder(OBSIDIAN_DIR, "skills_obsidian", "obsidian")
    print("\n" + "=" * 60)
    print(f"DONE - {sp+obs} total ({sp_e+obs_e} enriched)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
