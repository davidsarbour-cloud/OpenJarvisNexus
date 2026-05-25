"""
brain_tools.py — Lecture / écriture / recherche dans le vault Obsidian.

Expose 3 outils Claude :
  brain_read   — lit une note par chemin relatif
  brain_write  — crée ou modifie une note (append ou overwrite)
  brain_search — cherche dans le contenu et les noms de fichiers

Et 3 endpoints FastAPI montés dans main.py :
  GET  /v1/brain/read?path=...
  POST /v1/brain/write
  GET  /v1/brain/search?q=...
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/app/BRAIN/BRAIN"))

# ── Helpers ─────────────────────────────────────────────────────────────────

def _resolve(path: str) -> Path | None:
    """Résout un chemin relatif au vault et vérifie qu'il reste dans le vault."""
    p = (VAULT_PATH / path).resolve()
    try:
        p.relative_to(VAULT_PATH.resolve())
        return p
    except ValueError:
        return None  # hors vault — refusé


def _auto_frontmatter(path: str) -> str:
    """Génère un frontmatter YAML minimal pour une nouvelle note."""
    domain = "daily" if path.startswith("02_Daily") else \
             "project" if path.startswith("03_Projects") else \
             "core" if path.startswith("00_Core") else \
             "agent" if path.startswith("06_Agents") else \
             "resource" if path.startswith("05_Resources") else "note"
    return f"---\ndate: {date.today().isoformat()}\ndomain: {domain}\ntags: []\n---\n\n"


# ── Outils ──────────────────────────────────────────────────────────────────

def brain_read(path: str) -> dict:
    """Lit une note du vault Obsidian.
    path : chemin relatif depuis la racine du vault (ex: '02_Daily/sessions/2026-05-25.md')
    """
    note = _resolve(path)
    if note is None:
        return {"ok": False, "error": "Chemin hors du vault — refusé."}
    if not note.exists():
        return {"ok": False, "error": f"Note introuvable : {path}"}
    try:
        content = note.read_text(encoding="utf-8")
        return {
            "ok":      True,
            "path":    str(note.relative_to(VAULT_PATH)),
            "size":    len(content),
            "content": content,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def brain_write(path: str, content: str, append: bool = False) -> dict:
    """Crée ou modifie une note dans le vault.
    path    : chemin relatif (ex: '02_Daily/sessions/2026-05-25.md')
    content : texte markdown à écrire
    append  : True = ajoute à la fin, False = écrase (défaut False)
    """
    note = _resolve(path)
    if note is None:
        return {"ok": False, "error": "Chemin hors du vault — refusé."}
    note.parent.mkdir(parents=True, exist_ok=True)

    try:
        if append and note.exists():
            existing = note.read_text(encoding="utf-8")
            note.write_text(existing.rstrip() + "\n\n" + content.strip() + "\n",
                            encoding="utf-8")
            action = "append"
        else:
            # Nouvelle note → ajouter frontmatter si absent
            rel = str(note.relative_to(VAULT_PATH))
            if not content.strip().startswith("---"):
                content = _auto_frontmatter(rel) + content.strip() + "\n"
            note.write_text(content, encoding="utf-8")
            action = "write"
        return {
            "ok":     True,
            "path":   str(note.relative_to(VAULT_PATH)),
            "action": action,
            "size":   note.stat().st_size,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def brain_search(query: str, max_results: int = 10) -> dict:
    """Cherche dans le vault Obsidian (noms de fichiers + contenu).
    query : texte à chercher (insensible à la casse)
    Retourne les chemins et les lignes correspondantes.
    """
    if not VAULT_PATH.exists():
        return {"ok": False, "error": "Vault introuvable."}

    results = []
    q = query.lower()

    for note in sorted(VAULT_PATH.rglob("*.md")):
        if ".obsidian" in note.parts:
            continue
        try:
            rel = str(note.relative_to(VAULT_PATH))
            content = note.read_text(encoding="utf-8")
            name_match = q in note.stem.lower()
            matching_lines = [
                l.strip() for l in content.splitlines()
                if q in l.lower() and l.strip()
            ][:3]

            if name_match or matching_lines:
                results.append({
                    "path":    rel,
                    "matches": matching_lines,
                })
                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return {
        "ok":     True,
        "query":  query,
        "count":  len(results),
        "results": results,
    }


# ── Dispatch (appelé depuis main.py dans la boucle tool_use Claude) ─────────

def dispatch(tool_name: str, tool_input: dict) -> str:
    if tool_name == "brain_read":
        return json.dumps(brain_read(tool_input.get("path", "")), ensure_ascii=False)
    if tool_name == "brain_write":
        return json.dumps(brain_write(
            tool_input.get("path", ""),
            tool_input.get("content", ""),
            tool_input.get("append", False),
        ), ensure_ascii=False)
    if tool_name == "brain_search":
        return json.dumps(brain_search(
            tool_input.get("query", ""),
            tool_input.get("max_results", 10),
        ), ensure_ascii=False)
    return json.dumps({"ok": False, "error": f"Outil inconnu : {tool_name}"})


# ── Définitions Claude tool_use ──────────────────────────────────────────────

CLAUDE_TOOL_DEFS = [
    {
        "name":        "brain_read",
        "description": "Lit une note du vault Obsidian de David. Utilise cet outil quand David demande de lire, afficher ou consulter une note du brain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type":        "string",
                    "description": "Chemin relatif depuis la racine du vault. Ex: '02_Daily/sessions/2026-05-25.md' ou '00_Core/core-identité.md'",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name":        "brain_write",
        "description": "Crée ou modifie une note dans le vault Obsidian. Utilise append=true pour ajouter du contenu à une note existante sans effacer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type":        "string",
                    "description": "Chemin relatif depuis la racine du vault. Ex: '02_Daily/sessions/2026-05-25.md'",
                },
                "content": {
                    "type":        "string",
                    "description": "Contenu markdown à écrire dans la note.",
                },
                "append": {
                    "type":        "boolean",
                    "description": "true = ajoute à la fin de la note existante. false = écrase (défaut).",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name":        "brain_search",
        "description": "Cherche dans les notes du vault Obsidian de David (noms de fichiers + contenu). Utilise cet outil quand David demande de trouver une note, chercher dans le brain, ou retrouver une information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "Texte à chercher dans le vault (insensible à la casse).",
                },
                "max_results": {
                    "type":        "integer",
                    "description": "Nombre maximum de résultats (défaut 10).",
                },
            },
            "required": ["query"],
        },
    },
]
