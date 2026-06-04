"""STL modification tools for JARVIS — repair, scale, hollow, cut, decimate,
validate. Each takes an STL path (absolute, OR a filename resolved under
JARVIS_STL_DIR), runs the op (trimesh + the forge_room helpers / Blender), saves
a NEW .stl next to the source, and returns a JSON-able status dict.

`dispatch(name, input)` routes a Claude tool_use call to the right function and
returns a JSON string (the tool_result content), mirroring brain/skill/docker
dispatchers used by chat_router.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

STL_DIR = Path(os.getenv(
    "JARVIS_STL_DIR",
    str(Path.home() / "OneDrive" / "Bureau" / "Jarvis" / "STL"),
))


# ── helpers ──────────────────────────────────────────────────────────────────

_BASES = [STL_DIR, STL_DIR.parent, STL_DIR.parent / "Important"]


def _resolve(path: str) -> "Path | None":
    """Find the STL: absolute path, then by name under the Jarvis STL / root /
    Important folders, then a fuzzy *stem*.stl glob there."""
    if not path:
        return None
    p = Path(path)
    if p.is_absolute() and p.exists():
        return p
    for base in _BASES:
        for c in (base / p.name, base / (p.stem + ".stl")):
            if c.exists():
                return c
    for base in _BASES:                       # fuzzy fallback
        if base.is_dir() and p.stem:
            hits = sorted(base.glob(f"*{p.stem}*.stl"))
            if hits:
                return hits[0]
    return None


def _out(src: Path, suffix: str) -> Path:
    return src.with_name(f"{src.stem}_{suffix}.stl")


def _load(src: Path):
    import trimesh
    return trimesh.load(str(src), force="mesh")


def _dims(mesh) -> list:
    return [round(float(d), 1) for d in mesh.extents]


# ── operations ───────────────────────────────────────────────────────────────

def stl_validate(path: str) -> dict:
    src = _resolve(path)
    if not src:
        return {"ok": False, "error": f"STL introuvable: {path}"}
    m = _load(src)
    out = {"ok": True, "file": src.name, "watertight": bool(m.is_watertight),
           "dims_mm": _dims(m), "faces": int(len(m.faces))}
    try:
        from forge_room.mesh_validator import validate_mesh
        v = validate_mesh(m, check_thickness=True, check_supports=True)
        wall = getattr(v, "wall", None)
        out["min_wall_mm"] = getattr(wall, "min_thickness_mm", None)
        man = getattr(v, "manifold", None)
        out["manifold"] = getattr(man, "is_watertight", m.is_watertight)
    except Exception:
        pass
    return out


def stl_repair(path: str) -> dict:
    src = _resolve(path)
    if not src:
        return {"ok": False, "error": f"STL introuvable: {path}"}
    from forge_room.mesh_repair import auto_repair
    fixed, _res = auto_repair(_load(src))
    dst = _out(src, "repaired")
    fixed.export(str(dst))
    return {"ok": True, "input": src.name, "output": str(dst),
            "watertight": bool(fixed.is_watertight), "faces": int(len(fixed.faces))}


def stl_scale(path: str, target_mm: "float | None" = None,
              factor: "float | None" = None) -> dict:
    src = _resolve(path)
    if not src:
        return {"ok": False, "error": f"STL introuvable: {path}"}
    m = _load(src)
    if factor:
        m.apply_scale(float(factor))
        tag = f"x{factor}"
    elif target_mm:
        from forge_room.mesh_repair import scale_to_target
        m = scale_to_target(m, float(target_mm))
        tag = f"{int(float(target_mm))}mm"
    else:
        return {"ok": False, "error": "Donne target_mm (plus grande dimension) ou factor (multiplicateur)."}
    dst = _out(src, f"scaled_{tag}")
    m.export(str(dst))
    return {"ok": True, "input": src.name, "output": str(dst), "dims_mm": _dims(m)}


def stl_decimate(path: str, target_faces: int = 60000) -> dict:
    src = _resolve(path)
    if not src:
        return {"ok": False, "error": f"STL introuvable: {path}"}
    import trimesh
    m = _load(src)
    orig = len(m.faces)
    if orig > int(target_faces):
        try:
            import fast_simplification
            pts, faces = fast_simplification.simplify(
                m.vertices, m.faces, target_reduction=1.0 - int(target_faces) / orig)
            m = trimesh.Trimesh(vertices=pts, faces=faces, process=False)
            m.fix_normals()
        except Exception as e:
            return {"ok": False, "error": f"décimation impossible: {e}"}
    dst = _out(src, f"decimated_{int(target_faces)}")
    m.export(str(dst))
    return {"ok": True, "input": src.name, "output": str(dst),
            "faces": int(len(m.faces)), "was": orig}


def stl_hollow(path: str, wall_mm: float = 2.0) -> dict:
    src = _resolve(path)
    if not src:
        return {"ok": False, "error": f"STL introuvable: {path}"}
    from forge_room.engineering_pass import report_to_dict, run_engineering_pass
    out_dir = src.parent / f"{src.stem}_hollow"
    rep = run_engineering_pass(
        src, {"hollow": {"enabled": True, "wall_mm": float(wall_mm)}}, out_dir)
    d = report_to_dict(rep)
    return {"ok": bool(d.get("ok")), "input": src.name, "wall_mm": float(wall_mm),
            "output_dir": str(out_dir),
            "note": None if d.get("ok") else d.get("error", "voir report"),
            "pieces": d.get("pieces", [])}


def stl_cut(path: str, cuts_mm: "list | None" = None,
            plate_mm: "list | None" = None) -> dict:
    src = _resolve(path)
    if not src:
        return {"ok": False, "error": f"STL introuvable: {path}"}
    from forge_room.engineering_pass import report_to_dict, run_engineering_pass
    specs: dict = {}
    if cuts_mm:
        specs["cuts"] = [{"value_mm": float(z)} for z in cuts_mm]
    if plate_mm:
        specs["plate_mm"] = [float(x) for x in plate_mm]
    if not specs:
        return {"ok": False, "error": "Donne cuts_mm (hauteurs Z des coupes) ou plate_mm (taille plateau)."}
    out_dir = src.parent / f"{src.stem}_cut"
    rep = run_engineering_pass(src, specs, out_dir)
    d = report_to_dict(rep)
    return {"ok": bool(d.get("ok")), "input": src.name, "output_dir": str(out_dir),
            "note": None if d.get("ok") else d.get("error", "voir report"),
            "pieces": d.get("pieces", [])}


# ── Claude tool_use defs ─────────────────────────────────────────────────────

_PATH = {"type": "string",
         "description": "Chemin du STL (absolu) OU juste le nom du fichier (résolu dans le dossier Jarvis/STL)."}

CLAUDE_TOOL_DEFS = [
    {"name": "stl_validate",
     "description": "Vérifie l'imprimabilité d'un STL existant : watertight/manifold, dimensions (mm), nb de faces, épaisseur de paroi mini. Utilise quand David demande si un STL est imprimable / valide.",
     "input_schema": {"type": "object", "properties": {"path": _PATH}, "required": ["path"]}},
    {"name": "stl_repair",
     "description": "Répare un STL : rend le maillage étanche (watertight/manifold), bouche les trous. Exporte un nouveau fichier _repaired.stl.",
     "input_schema": {"type": "object", "properties": {"path": _PATH}, "required": ["path"]}},
    {"name": "stl_scale",
     "description": "Redimensionne un STL. Donne SOIT target_mm (plus grande dimension voulue en mm) SOIT factor (multiplicateur, ex 1.5 = +50%). Exporte _scaled.stl.",
     "input_schema": {"type": "object", "properties": {
         "path": _PATH,
         "target_mm": {"type": "number", "description": "Plus grande dimension cible en mm (ex 100)."},
         "factor": {"type": "number", "description": "Multiplicateur d'échelle (ex 0.5 = moitié, 2 = double)."},
     }, "required": ["path"]}},
    {"name": "stl_decimate",
     "description": "Réduit le nombre de faces d'un STL trop lourd (target_faces, défaut 60000). Exporte _decimated.stl.",
     "input_schema": {"type": "object", "properties": {
         "path": _PATH,
         "target_faces": {"type": "integer", "description": "Nombre de faces cible (défaut 60000)."},
     }, "required": ["path"]}},
    {"name": "stl_hollow",
     "description": "Évide/creuse un STL pour économiser de la matière (paroi wall_mm, défaut 2.0). Nécessite Blender. Exporte les pièces creusées.",
     "input_schema": {"type": "object", "properties": {
         "path": _PATH,
         "wall_mm": {"type": "number", "description": "Épaisseur de paroi en mm (défaut 2.0)."},
     }, "required": ["path"]}},
    {"name": "stl_cut",
     "description": "Découpe un gros STL en pièces (plans de coupe Z cuts_mm, ou taille plateau plate_mm pour qu'il rentre). Nécessite Blender.",
     "input_schema": {"type": "object", "properties": {
         "path": _PATH,
         "cuts_mm": {"type": "array", "items": {"type": "number"}, "description": "Hauteurs Z (mm) où couper, ex [50, 100]."},
         "plate_mm": {"type": "array", "items": {"type": "number"}, "description": "Taille du plateau [X, Y] en mm, ex [256, 256]."},
     }, "required": ["path"]}},
]

_FUNCS = {
    "stl_validate": stl_validate, "stl_repair": stl_repair, "stl_scale": stl_scale,
    "stl_decimate": stl_decimate, "stl_hollow": stl_hollow, "stl_cut": stl_cut,
}


def dispatch(name: str, tool_input: dict) -> str:
    """Route a Claude tool_use call to the matching STL op; return JSON string."""
    fn = _FUNCS.get(name)
    if not fn:
        return json.dumps({"ok": False, "error": f"outil STL inconnu: {name}"})
    try:
        return json.dumps(fn(**(tool_input or {})), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
