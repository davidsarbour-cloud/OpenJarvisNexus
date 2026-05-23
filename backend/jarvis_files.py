"""
JARVIS File Workspace — acces lecture/ecriture au dossier OneDrive de David.

READ  : OneDrive/Bureau/Jarvis  (lecture du workspace de David, contexte chat)
WRITE : brain Obsidian (08_Command-Center/reports) — rapports IA

JARVIS peut scanner, lire, chercher et ecrire dans ces repertoires.
"""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from config import BRAIN_REPORTS_DIR

# READ : workspace OneDrive de David (lecture pour le contexte chat) — conservé.
JARVIS_READ_DIR  = Path(os.getenv("JARVIS_READ_DIR",  r"C:/Users/bobby/OneDrive/Bureau/Jarvis"))
# WRITE : rapports IA -> brain Obsidian (plus OneDrive).
JARVIS_WRITE_DIR = Path(os.getenv("JARVIS_WRITE_DIR", str(BRAIN_REPORTS_DIR)))

# Extensions texte lisibles
TEXT_EXTENSIONS = {'.txt', '.md', '.json', '.py', '.js', '.html', '.css',
                   '.csv', '.yaml', '.yml', '.log', '.xml', '.rst', '.ini', '.cfg'}

router = APIRouter(prefix="/v1/jarvis/files", tags=["jarvis-files"])


# ── Helpers ───────────────────────────────────────────────

def _safe_path(base: Path, rel: str) -> Path:
    """Résout un chemin relatif sécurisé dans base (empêche path traversal)."""
    resolved = (base / rel).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise ValueError(f"Path traversal refusé: {rel}")
    return resolved

def _read_text(path: Path, max_chars: int = 8000) -> str:
    """Lit un fichier texte, tronqué si trop long."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[... tronqué à {max_chars} caractères ...]"
        return content
    except Exception as e:
        return f"[Erreur lecture: {e}]"

def _file_info(path: Path, base: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "rel_path": str(path.relative_to(base)),
        "size_kb": round(stat.st_size / 1024, 1),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()[:16],
        "readable": path.suffix.lower() in TEXT_EXTENSIONS,
        "type": path.suffix.lower() or "dir" if path.is_dir() else "file",
    }


# ── Fonctions utilitaires (pour l'orchestrateur) ──────────

def list_jarvis_dir(subdir: str = "", max_files: int = 200, recursive: bool = False) -> list[dict]:
    """Liste les fichiers du répertoire Jarvis (récursif si recursive=True)."""
    base   = JARVIS_READ_DIR
    target = _safe_path(base, subdir) if subdir else base
    if not target.exists():
        return []
    items = []
    iterator = target.rglob("*") if recursive else target.iterdir()
    for p in sorted(iterator, key=lambda x: (0 if x.is_dir() else 1, x.stat().st_mtime)):
        if len(items) >= max_files:
            break
        try:
            info = _file_info(p, base)
            # Ajoute le niveau d'indentation pour la vue arbre
            info["depth"] = len(p.relative_to(target).parts) - 1
            info["is_dir"] = p.is_dir()
            items.append(info)
        except Exception:
            pass
    return items


def read_jarvis_file(rel_path: str) -> str:
    """Lit un fichier du répertoire Jarvis."""
    path = _safe_path(JARVIS_READ_DIR, rel_path)
    if not path.exists():
        return f"[Fichier non trouvé: {rel_path}]"
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return f"[Fichier binaire non lisible: {path.name}]"
    return _read_text(path)


def search_jarvis_files(query: str, max_results: int = 5) -> list[dict]:
    """Recherche textuelle dans les fichiers du répertoire Jarvis."""
    query_lower = query.lower()
    results = []
    for path in JARVIS_READ_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if query_lower in content.lower():
                # Extrait le contexte autour du match
                idx = content.lower().find(query_lower)
                start = max(0, idx - 100)
                end   = min(len(content), idx + 200)
                excerpt = content[start:end].replace("\n", " ").strip()
                results.append({
                    "file": str(path.relative_to(JARVIS_READ_DIR)),
                    "excerpt": excerpt,
                    "size_kb": round(path.stat().st_size / 1024, 1),
                })
                if len(results) >= max_results:
                    break
        except Exception:
            pass
    return results


def write_jarvis_report(filename: str, content: str, subdir: str = "") -> str:
    """Écrit un fichier dans le répertoire output de JARVIS."""
    JARVIS_WRITE_DIR.mkdir(parents=True, exist_ok=True)
    target_dir = JARVIS_WRITE_DIR
    if subdir:
        target_dir = _safe_path(JARVIS_WRITE_DIR, subdir)
        target_dir.mkdir(parents=True, exist_ok=True)

    # Ajoute un timestamp au nom si pas d'extension
    if "." not in filename:
        filename = f"{filename}_{datetime.now():%Y%m%d_%H%M%S}.txt"

    dest = target_dir / filename
    dest.write_text(content, encoding="utf-8")
    return str(dest)


# ── FastAPI Endpoints ─────────────────────────────────────

@router.get("/list")
def api_list(subdir: str = Query(""), max_files: int = Query(200), recursive: bool = Query(True)):
    """Liste les fichiers du workspace Jarvis — récursif par défaut."""
    files = list_jarvis_dir(subdir, max_files, recursive)
    dirs  = [f for f in files if f.get("is_dir")]
    txts  = [f for f in files if not f.get("is_dir")]
    return {
        "base":        str(JARVIS_READ_DIR),
        "subdir":      subdir or "/",
        "recursive":   recursive,
        "total":       len(files),
        "dirs_count":  len(dirs),
        "files_count": len(txts),
        "tree":        files,
    }


@router.get("/read")
def api_read(path: str = Query(...), max_chars: int = Query(8000)):
    """Lit un fichier du workspace Jarvis."""
    try:
        full = _safe_path(JARVIS_READ_DIR, path)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not full.exists():
        raise HTTPException(404, f"Fichier non trouvé: {path}")
    if full.suffix.lower() not in TEXT_EXTENSIONS:
        raise HTTPException(400, f"Fichier non textuel: {full.suffix}")
    return PlainTextResponse(_read_text(full, max_chars))


@router.get("/search")
def api_search(q: str = Query(...), max_results: int = Query(5)):
    """Recherche textuelle dans les fichiers Jarvis."""
    results = search_jarvis_files(q, max_results)
    return {"query": q, "results": results, "count": len(results)}


class WriteRequest(BaseModel):
    filename: str
    content: str
    subdir: str = ""

@router.post("/write")
def api_write(req: WriteRequest):
    """JARVIS écrit un fichier dans son dossier output."""
    try:
        dest = write_jarvis_report(req.filename, req.content, req.subdir)
        return {"ok": True, "path": dest, "filename": Path(dest).name}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/report")
def api_report(req: WriteRequest):
    """JARVIS sauvegarde un rapport daté."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{req.filename}_{ts}.md"
    try:
        dest = write_jarvis_report(filename, req.content, req.subdir)
        return {"ok": True, "path": dest, "filename": Path(dest).name}
    except Exception as e:
        raise HTTPException(500, str(e))
