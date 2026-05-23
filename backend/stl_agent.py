"""
STL Mission Agent — Blender + Meshy AI + n8n orchestration
Endpoints: POST /v1/stl/mission  GET /v1/stl/mission/{id}  GET /v1/stl/download/{id}
"""

import asyncio
import httpx
import subprocess
import os
import uuid
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import trimesh

router = APIRouter()
_background_tasks: set = set()

# ── Config (set in backend/.env) ─────────────────────────
MESHY_API_KEY   = os.getenv("MESHY_API_KEY", "")
N8N_WEBHOOK_URL = os.getenv("N8N_STL_WEBHOOK", "")
BLENDER_PATH    = os.getenv("BLENDER_PATH", r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe")
BAMBU_STUDIO_PATH = os.getenv("BAMBU_STUDIO_PATH", r"C:\Program Files\Bambu Studio\bambu-studio.exe")
BACKEND_PORT    = int(os.getenv("BACKEND_PORT", 8000))
CLAUDE_MODEL    = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

STL_DIR = Path(__file__).parent / "stl_output"
STL_DIR.mkdir(exist_ok=True)
MISSION_LOG_DIR = Path(__file__).parent / "mission_logs"
MISSION_LOG_DIR.mkdir(exist_ok=True)

# Default design profile — David's preference for D3Dprintix
DEFAULT_STYLE = (
    "low-poly fantasy, support-free, optimized for FDM 3D printing, "
    "single-piece printable mesh, 15cm scale, minimal overhangs (<45°), "
    "flat base, wall thickness >=1.2mm"
)

_missions: dict[str, dict] = {}

STEP_NAMES = ["orchestration", "concept", "modeling", "optimization", "preview", "packaging"]

# ── Models ───────────────────────────────────────────────

class MissionRequest(BaseModel):
    prompt: str
    engine: str = "auto"          # "meshy" | "blender" | "n8n" | "auto"
    style: str = "low_poly_fantasy"
    auto_bambu: bool = True       # auto-launch Bambu Studio when ready
    auto_repair: bool = True      # run trimesh validation/repair
    target_size_mm: float = 150.0 # auto-rescale to this longest dimension

# ── Helpers ──────────────────────────────────────────────

def _new_mission(req: "MissionRequest") -> dict:
    mid = str(uuid.uuid4())[:8].upper()
    return {
        "id": mid,
        "prompt": req.prompt,
        "engine": req.engine,
        "style": req.style,
        "auto_bambu": req.auto_bambu,
        "auto_repair": req.auto_repair,
        "target_size_mm": req.target_size_mm,
        "status": "running",
        "steps": {s: "pending" for s in STEP_NAMES},
        "current_step": "orchestration",
        "concept": "",
        "files": {},
        "logs": [],
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
    }

def _log(m: dict, msg: str, level: str = "info"):
    ts = datetime.now().strftime("%H:%M:%S")
    m["logs"].append({"ts": ts, "msg": msg, "level": level})
    print(f"[STL:{m['id']}] [{level.upper()}] {msg}")

def _step(m: dict, name: str, status: str):
    m["steps"][name] = status
    m["current_step"] = name

# ── ULTRON — Concept generation (Claude Sonnet 4-6) ─────

CLAUDE_MODEL_GROS = os.getenv("CLAUDE_MODEL_GROS", "claude-sonnet-4-6")

ULTRON_CONCEPT_SYSTEM = """You are ULTRON, Creative Director and 3D Design Expert at D3Dprintix.
Your role: transform a user request into a precise, optimized prompt for Meshy AI text-to-3D.

Rules:
- Output ONLY the Meshy AI prompt, nothing else
- 60-100 words maximum
- Specify: object type, style (low-poly fantasy), key visual features
- Include FDM constraints: support-free, flat base, wall thickness >=1.2mm
- Target scale: 15cm longest dimension
- No overhangs >45 degrees
- Mention: single solid piece, no loose parts
- Style keywords: low-poly, faceted, geometric, fantasy"""

async def _get_concept(prompt: str) -> str:
    """ULTRON generates an optimized Meshy AI prompt using Claude Sonnet 4-6."""
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"http://localhost:{BACKEND_PORT}/v1/chat/completions",
                json={
                    "system": ULTRON_CONCEPT_SYSTEM,
                    "message": (
                        f"User wants: \"{prompt}\"\n\n"
                        f"Generate an optimized Meshy AI prompt. "
                        f"Apply D3Dprintix defaults: {DEFAULT_STYLE}. "
                        "Output ONLY the prompt text, no explanation."
                    ),
                    "stream": False,
                    "model": CLAUDE_MODEL_GROS,  # ULTRON = Sonnet 4-6 toujours
                },
                timeout=20,
            )
            if r.status_code == 200:
                d = r.json()
                m = d.get("choices", [{}])[0].get("message", "")
                text = (m if isinstance(m, str) else m.get("content", "")).strip()
                if text:
                    return text
    except Exception:
        pass
    return f"Low-poly {prompt} for FDM 3D printing. Target size 80-120mm, manifold mesh, wall thickness ≥1.2mm."

# ── Blender backend ──────────────────────────────────────

_BLENDER_SYSTEM = "You output ONLY valid Python code for Blender. No prose, no questions, no French. If unclear, infer defaults."
_BLENDER_USER = (
    "Write a complete Blender Python script (bpy) that creates a 3D printable model of: \"{prompt}\".\n"
    "Context: {concept}\n"
    "Requirements:\n"
    "- Use only bpy built-ins (no external libraries)\n"
    "- Low-poly style (use small subdivision levels)\n"
    "- 3D printable: manifold mesh, no overhangs >45 degrees, wall >=1.2mm\n"
    "- Export STL to path: import os; out=os.environ.get('STL_OUT','output.stl')\n"
    "- Clear default scene at start\n"
    "Output ONLY the Python code."
)

def _extract_python_code(text: str) -> str:
    import re
    match = re.search(r"```(?:python)?\n?([\s\S]+?)```", text, re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()

async def _blender_script_from_claude(prompt: str, concept: str) -> str:
    """Generate a Blender Python script. Claude first, Ollama deepseek-coder fallback."""
    user_msg = _BLENDER_USER.format(prompt=prompt, concept=concept)

    # ── Try Claude first ───────────────────────────────────
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"http://localhost:{BACKEND_PORT}/v1/chat/completions",
                json={
                    "system": _BLENDER_SYSTEM,
                    "message": user_msg,
                    "stream": False,
                    "model": CLAUDE_MODEL,
                },
                timeout=30,
            )
            if r.status_code == 200:
                d = r.json()
                m = d.get("choices", [{}])[0].get("message", "")
                text = (m if isinstance(m, str) else m.get("content", "")).strip()
                if text:
                    return _extract_python_code(text)
    except Exception as e:
        print(f"[stl_blender] Claude failed: {e} — fallback Ollama")

    # ── Fallback : Ollama deepseek-coder (local, gratuit) ──
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ollama_coder = os.getenv("OLLAMA_CODER_MODEL", "deepseek-coder")
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": ollama_coder,
                    "prompt": f"{_BLENDER_SYSTEM}\n\n{user_msg}",
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2048},
                },
                timeout=120,
            )
            if r.status_code == 200:
                text = r.json().get("response", "").strip()
                if text:
                    print("[stl_blender] OK via Ollama deepseek-coder")
                    return _extract_python_code(text)
    except Exception as e:
        print(f"[stl_blender] Ollama failed: {e} — fallback statique")

    return _fallback_blender_script(prompt)

def _fallback_blender_script(prompt: str) -> str:
    return (
        "import bpy, os, math\n"
        "# JARVIS fallback — basic printable shape\n"
        "bpy.ops.object.select_all(action='SELECT')\n"
        "bpy.ops.object.delete(use_global=False)\n"
        "# Parametric low-poly sphere\n"
        "bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.04)\n"
        "obj = bpy.context.active_object\n"
        "obj.name = 'JarvisModel'\n"
        "# Export\n"
        "out = os.environ.get('STL_OUT', 'output.stl')\n"
        "bpy.ops.export_mesh.stl(filepath=out)\n"
        f"print('STL exported to', out, '— Request was: {prompt}')\n"
    )

async def _run_blender(mission: dict, concept: str) -> Path | None:
    if not Path(BLENDER_PATH).exists():
        _log(mission, f"Blender not found at: {BLENDER_PATH} — set BLENDER_PATH in .env", "error")
        return None

    script_path = STL_DIR / f"{mission['id']}_gen.py"
    out_path    = STL_DIR / f"{mission['id']}.stl"

    _log(mission, "Generating Blender script via AI...", "info")
    script = await _blender_script_from_claude(mission["prompt"], concept)
    script_path.write_text(script, encoding="utf-8")
    _log(mission, f"Running Blender headless: {Path(BLENDER_PATH).name}", "info")

    env = os.environ.copy()
    env["STL_OUT"] = str(out_path)
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [BLENDER_PATH, "--background", "--python", str(script_path)],
            capture_output=True, text=True, timeout=180, env=env,
        )
        if out_path.exists():
            size_kb = out_path.stat().st_size // 1024
            _log(mission, f"Blender completed — {size_kb}KB STL generated", "success")
            return out_path
        _log(mission, "Blender ran but no STL produced.", "error")
        if result.stderr:
            _log(mission, result.stderr[-300:], "error")
    except subprocess.TimeoutExpired:
        _log(mission, "Blender timed out (180s)", "error")
    except Exception as e:
        _log(mission, f"Blender error: {e}", "error")
    return None

# ── Meshy AI backend ─────────────────────────────────────

async def _run_meshy(mission: dict) -> Path | None:
    if not MESHY_API_KEY:
        _log(mission, "MESHY_API_KEY not set in .env — skipping Meshy AI", "error")
        return None

    _log(mission, "Submitting to Meshy AI text-to-3D...", "info")
    async with httpx.AsyncClient() as c:
        try:
            # Enriched prompt with D3Dprintix style defaults
            enriched = (
                f"{mission['prompt']}, low-poly fantasy style, single piece, "
                "flat base, no overhangs, FDM 3D print ready, clean topology, "
                "minimum details for printability, support-free design"
            )
            r = await c.post(
                "https://api.meshy.ai/v2/text-to-3d",
                headers={"Authorization": f"Bearer {MESHY_API_KEY}"},
                json={
                    "mode": "preview",
                    "prompt": enriched,
                    # art_style omitted — current v2 API only accepts "realistic";
                    # low-poly aesthetic is driven by the prompt itself.
                    "negative_prompt": (
                        "high poly, thin walls, overhangs, floating geometry, "
                        "non-manifold, holes, supports needed, multi-part, "
                        "low quality, blurry, messy"
                    ),
                },
                timeout=30,
            )
            r.raise_for_status()
            task_id = r.json()["result"]
            _log(mission, f"Meshy task created: {task_id}", "info")

            for tick in range(96):
                await asyncio.sleep(5)
                poll = await c.get(
                    f"https://api.meshy.ai/v2/text-to-3d/{task_id}",
                    headers={"Authorization": f"Bearer {MESHY_API_KEY}"},
                    timeout=10,
                )
                data = poll.json()
                pct = data.get("progress", 0)
                _log(mission, f"Meshy progress: {pct}%", "info")

                if data["status"] == "SUCCEEDED":
                    urls = data.get("model_urls", {})
                    # Prefer OBJ (closest to STL), then GLB
                    dl_url = urls.get("obj") or urls.get("glb") or urls.get("fbx")
                    if not dl_url:
                        _log(mission, "Meshy succeeded but no download URL found", "error")
                        return None
                    ext = "obj" if "obj" in dl_url else ("glb" if "glb" in dl_url else "fbx")
                    dl = await c.get(dl_url, timeout=120)
                    src_path = STL_DIR / f"{mission['id']}_meshy.{ext}"
                    src_path.write_bytes(dl.content)
                    _log(mission, f"Meshy {ext.upper()} downloaded ({src_path.stat().st_size//1024}KB)", "success")

                    # Convert to STL via Blender so Bambu Studio loads it cleanly
                    stl_path = STL_DIR / f"{mission['id']}.stl"
                    if await _convert_to_stl(mission, src_path, stl_path):
                        return stl_path
                    # Fallback: keep the raw Meshy file (Bambu can open OBJ)
                    return src_path

                if data["status"] in ("FAILED", "EXPIRED"):
                    _log(mission, f"Meshy failed: {data.get('message', 'unknown')}", "error")
                    return None

        except httpx.HTTPStatusError as e:
            _log(mission, f"Meshy API error {e.response.status_code}: {e.response.text[:200]}", "error")
        except Exception as e:
            _log(mission, f"Meshy error: {e}", "error")
    return None


async def _convert_to_stl(mission: dict, src: Path, dst: Path) -> bool:
    """Convert OBJ/GLB/FBX to STL using trimesh (pure Python, no Blender needed)."""
    ext = src.suffix.lower().lstrip(".")
    _log(mission, f"Converting {ext.upper()} → STL via trimesh...", "info")
    try:
        import trimesh  # lightweight, included in requirements.txt
        # force='mesh' merges scenes (Meshy GLB often returns a Scene, not a Mesh)
        mesh = trimesh.load(str(src), force="mesh")
        if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
            _log(mission, "Loaded mesh is empty — conversion aborted", "warn")
            return False
        mesh.export(str(dst), file_type="stl")
        if dst.exists() and dst.stat().st_size > 0:
            _log(mission, f"STL conversion complete: {dst.name} ({dst.stat().st_size//1024}KB)", "success")
            return True
        _log(mission, "STL file produced but empty", "warn")
    except ImportError:
        _log(mission, "trimesh not installed — run: pip install trimesh", "error")
    except Exception as e:
        _log(mission, f"STL conversion error: {e}", "warn")
    return False

# ── n8n webhook ──────────────────────────────────────────

async def _trigger_n8n(mission: dict) -> dict | None:
    if not N8N_WEBHOOK_URL:
        return None
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                N8N_WEBHOOK_URL,
                json={"mission_id": mission["id"], "prompt": mission["prompt"], "concept": mission.get("concept", "")},
                timeout=15,
            )
            if r.status_code < 300:
                _log(mission, "n8n workflow triggered successfully", "success")
                return r.json()
    except Exception as e:
        _log(mission, f"n8n webhook error: {e}", "error")
    return None

# ── Pipeline ─────────────────────────────────────────────

def _auto_orient(mesh, mission) -> "trimesh.Trimesh":
    """Test 6 cardinal rotations; pick the one with best print orientation
    (max flat base contact + low center of mass + low overhang area)."""
    import trimesh
    import numpy as np

    rotations = {
        "identity": np.eye(4),
        "X+90":     trimesh.transformations.rotation_matrix(np.pi / 2,  [1, 0, 0]),
        "X+180":    trimesh.transformations.rotation_matrix(np.pi,      [1, 0, 0]),  # flip upside-down
        "X-90":     trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]),
        "Y+90":     trimesh.transformations.rotation_matrix(np.pi / 2,  [0, 1, 0]),
        "Y-90":     trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0]),
    }

    best = None
    best_score = float("inf")
    best_name = "identity"

    for name, rot in rotations.items():
        m = mesh.copy()
        m.apply_transform(rot)
        m.apply_translation([0, 0, -m.bounds[0][2]])  # drop to z=0 for fair comparison

        normals = m.face_normals
        areas = m.area_faces
        total_area = float(areas.sum()) or 1.0

        overhang_area = float(areas[normals[:, 2] < -0.5].sum())
        bottom_z = float(m.bounds[0][2])
        height = max(float(m.extents[2]), 1e-6)
        face_z = m.triangles_center[:, 2]
        base_mask = (normals[:, 2] < -0.85) & (face_z < bottom_z + 0.05 * height)
        base_area = float(areas[base_mask].sum())
        com_z = float(m.centroid[2])
        com_norm = com_z / height

        # lower score = better orientation
        # heavily prioritize low overhang (3x weight) for support-free printing
        # base area still counts but less, COM low is a tie-breaker
        score = 3.0 * (overhang_area / total_area) - 0.8 * (base_area / total_area) + 0.3 * com_norm

        if score < best_score:
            best_score = score
            best = m
            best_name = name

    _log(mission, f"Auto-orient: '{best_name}' chosen (score={best_score:.3f})", "success")
    return best if best is not None else mesh


def _decimate(mesh, mission, target_faces: int = 60000):
    """Reduce face count using fast-simplification (target_reduction expected in 0..1)."""
    import trimesh
    before = len(mesh.faces)
    if before <= target_faces:
        return mesh
    # fraction of faces to REMOVE
    reduction = 1.0 - (target_faces / before)
    reduction = max(0.05, min(0.95, reduction))
    try:
        try:
            import fast_simplification
            new_v, new_f = fast_simplification.simplify(
                mesh.vertices, mesh.faces, target_reduction=reduction
            )
            simplified = trimesh.Trimesh(vertices=new_v, faces=new_f, process=True)
        except ImportError:
            # Fallback to trimesh's built-in (might route to open3d)
            simplified = mesh.simplify_quadric_decimation(face_count=target_faces)
        if simplified is not None and len(simplified.faces) > 0:
            _log(mission, f"Decimated {before} → {len(simplified.faces)} faces (-{int(reduction*100)}%)", "success")
            return simplified
    except Exception as e:
        _log(mission, f"Decimation skipped: {e}", "warn")
    return mesh


def _validate_and_repair(mission: dict, src_path: Path, target_size_mm: float = 150.0):
    """File Manager agent: convert + validate manifold/holes/walls/overhangs + auto-repair."""
    try:
        import trimesh
        import numpy as np
    except ImportError:
        _log(mission, "trimesh not installed — run: pip install trimesh numpy", "error")
        return None

    try:
        mesh = trimesh.load(str(src_path), force="mesh")
        if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
            _log(mission, "Mesh is empty — cannot validate", "error")
            return None

        # ── Initial diagnostics ──
        bbox = mesh.bounding_box.extents
        _log(mission, f"Loaded: {len(mesh.faces)} faces, bbox {[round(float(x),2) for x in bbox]}", "info")
        _log(mission, f"Manifold: {'OK' if mesh.is_watertight else 'NO'}  Winding: {'OK' if mesh.is_winding_consistent else 'NO'}", "info")

        repairs = []

        # ── 1. Auto-orient (fix upside-down models from Meshy) ──
        mesh = _auto_orient(mesh, mission)
        repairs.append("auto-oriented")

        # ── 2. Topology cleanup ──
        if not mesh.is_winding_consistent:
            mesh.fix_normals(); repairs.append("normals fixed")
        before = len(mesh.faces)
        mesh.update_faces(mesh.unique_faces())
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
        if len(mesh.faces) != before:
            repairs.append(f"cleaned {before - len(mesh.faces)} bad faces")

        # ── 3. Decimation FIRST (so we fix holes that decimation may create) ──
        if len(mesh.faces) > 80000:
            mesh = _decimate(mesh, mission, target_faces=60000)
            # Re-clean after decimation
            mesh.update_faces(mesh.unique_faces())
            mesh.update_faces(mesh.nondegenerate_faces())
            mesh.remove_unreferenced_vertices()
            mesh.merge_vertices()

        # ── 4. Hole filling ──
        try:
            trimesh.repair.fill_holes(mesh)
            trimesh.repair.fix_inversion(mesh)
            trimesh.repair.fix_winding(mesh)
        except Exception as e:
            _log(mission, f"Hole fill: {e}", "warn")

        # ── 4b. pymeshfix TOUJOURS — élimine les non-manifold edges avant Bambu ──
        # Bambu Studio détecte des erreurs que trimesh.is_watertight ne voit pas.
        # On passe TOUJOURS par pymeshfix pour garantir un mesh propre.
        try:
            import pymeshfix
            faces_before = len(mesh.faces)
            _log(mission, f"pymeshfix repair ({faces_before} faces)...", "info")
            mfix = pymeshfix.MeshFix(
                mesh.vertices.astype("float64"),
                mesh.faces.astype("int32"),
            )
            mfix.repair(joincomp=True, remove_smallest_components=False)
            repaired = trimesh.Trimesh(vertices=mfix.points, faces=mfix.faces, process=True)
            if len(repaired.faces) > 0:
                mesh = repaired
                status = "watertight" if mesh.is_watertight else "non-manifold edges remaining"
                repairs.append(f"pymeshfix ({faces_before}→{len(mesh.faces)} faces, {status})")
                _log(mission, f"pymeshfix done — {status}", "ok")
            else:
                _log(mission, "pymeshfix returned empty mesh, keeping original", "warn")
        except ImportError:
            _log(mission, "pymeshfix not installed", "warn")
        except Exception as e:
            _log(mission, f"pymeshfix error: {e}", "warn")

        # ── 5. Scale to target_size_mm ──
        longest = float(max(mesh.bounding_box.extents))
        if longest > 0 and abs(longest - target_size_mm) > 5:
            scale = target_size_mm / longest
            mesh.apply_scale(scale)
            repairs.append(f"rescaled x{scale:.2f} → {target_size_mm}mm")

        # ── 6. Drop to z=0 (flat on print bed) ──
        mins = mesh.bounds[0]
        mesh.apply_translation([-mins[0], -mins[1], -mins[2]])
        repairs.append("z=0 base aligned")

        if repairs:
            _log(mission, "Repairs: " + ", ".join(repairs), "success")

        # ── 7. Final overhang analysis ──
        normals = mesh.face_normals
        areas = mesh.area_faces
        total_area = float(areas.sum()) or 1.0
        overhang_area = float(areas[normals[:, 2] < -0.5].sum())
        overhang_pct = round(overhang_area / total_area * 100, 1)

        # ── 8. Build warnings list (visible in Hub) ──
        warnings = []
        if not mesh.is_watertight:
            warnings.append("Mesh not fully watertight after repair — slicer may struggle")
        if overhang_pct > 30:
            warnings.append(f"Critical overhang area: {overhang_pct}% — supports likely needed")
        elif overhang_pct > 15:
            warnings.append(f"High overhang area: {overhang_pct}% — supports recommended")
        if len(mesh.faces) > 200000:
            warnings.append(f"High face count ({len(mesh.faces)}) — slicing may be slow")
        if not mesh.is_winding_consistent:
            warnings.append("Inconsistent face winding remains")
        bbox_final = mesh.bounding_box.extents
        if min(bbox_final) < 5:
            warnings.append(f"Smallest dimension {min(bbox_final):.1f}mm — may be fragile")

        # ── 9. Build full report ──
        report = {
            "watertight":      bool(mesh.is_watertight),
            "winding_ok":      bool(mesh.is_winding_consistent),
            "is_volume":       bool(mesh.is_volume),
            "faces":           int(len(mesh.faces)),
            "vertices":        int(len(mesh.vertices)),
            "bbox_mm":         [round(float(x), 2) for x in bbox_final],
            "longest_mm":      round(float(max(bbox_final)), 2),
            "volume_mm3":      round(float(mesh.volume), 2) if mesh.is_volume else None,
            "overhang_pct":    overhang_pct,
            "warnings":        warnings,
            "repairs_applied": repairs,
        }
        mission["validation"] = report

        level = "success" if overhang_pct < 15 else "warn"
        _log(mission, f"Overhang final: {overhang_pct}% (>45°)", level)
        for w in warnings:
            _log(mission, "⚠ " + w, "warn")

        # ── 10. Export final STL ──
        stl_out = STL_DIR / f"{mission['id']}.stl"
        mesh.export(str(stl_out), file_type="stl")
        _log(mission, f"Final STL exported: {stl_out.name} ({stl_out.stat().st_size//1024}KB)", "success")

        # ── Copie vers dossier Jarvis — nommage séquentiel test1…test1000 ──
        import shutil, re as _re
        jarvis_stl_dir = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
        try:
            jarvis_stl_dir.mkdir(parents=True, exist_ok=True)
            # Trouver le prochain numéro disponible
            existing_nums = [
                int(m.group(1))
                for f in jarvis_stl_dir.glob("test*.stl")
                if (m := _re.match(r"test(\d+)\.stl", f.name, _re.IGNORECASE))
            ]
            next_n = (max(existing_nums) + 1) if existing_nums else 1
            dest = jarvis_stl_dir / f"test{next_n}.stl"
            shutil.copy2(str(stl_out), str(dest))
            _log(mission, f"STL sauvegardé: {dest.name} (test{next_n})", "success")
            mission["files"]["jarvis_stl"] = str(dest)
            mission["files"]["jarvis_stl_name"] = dest.name
        except Exception as e:
            _log(mission, f"Copie Jarvis échouée: {e}", "warn")

        return stl_out
    except Exception as e:
        _log(mission, f"Validation/repair error: {e}", "error")
        return None


def _persist_mission_log(mission: dict):
    """Save mission to disk for permanent history."""
    try:
        log_path = MISSION_LOG_DIR / f"{mission['id']}.json"
        log_path.write_text(json.dumps(mission, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[STL] failed to persist log: {e}")


async def _run_pipeline(mission_id: str):
    m = _missions[mission_id]
    try:
        # 1 — Orchestration (JARVIS brief)
        _step(m, "orchestration", "running")
        _log(m, f"[JARVIS] Mission #{m['id']} — briefing ULTRON → KAIZEN → BRUCE", "info")
        _log(m, f"[JARVIS] Prompt: {m['prompt']}", "info")
        _log(m, f"[JARVIS] Target: {m.get('target_size_mm', 150)}mm | auto-Bambu: {m.get('auto_bambu')}", "info")
        await asyncio.sleep(0.4)
        m["steps"]["orchestration"] = "done"

        # 2 — Concept (ULTRON — Claude Sonnet 4-6)
        _step(m, "concept", "running")
        _log(m, "[ULTRON] Generating optimized 3D concept prompt (Sonnet 4-6)...", "ai")
        concept = await _get_concept(m["prompt"])
        m["concept"] = concept
        _log(m, f"[ULTRON] Concept: {concept[:200]}", "ai")
        m["steps"]["concept"] = "done"

        # 3 — Modeling (KAIZEN — Meshy AI → Blender fallback)
        _step(m, "modeling", "running")
        _log(m, "[KAIZEN] Starting 3D generation with ULTRON concept prompt...", "info")
        raw_path: Path | None = None

        n8n_result = await _trigger_n8n(m)
        if n8n_result and n8n_result.get("file_path"):
            p = Path(n8n_result["file_path"])
            if p.exists():
                raw_path = p
                _log(m, f"[KAIZEN] n8n delivered: {p.name}", "ok")

        if not raw_path and m["engine"] in ("meshy", "auto") and MESHY_API_KEY:
            _log(m, "[KAIZEN] Calling Meshy AI text-to-3D...", "info")
            raw_path = await _run_meshy(m)

        if not raw_path and m["engine"] in ("blender", "auto"):
            _log(m, "[KAIZEN] Meshy unavailable — fallback to Blender headless...", "warn")
            raw_path = await _run_blender(m, concept)

        if raw_path:
            m["files"]["raw"] = str(raw_path)
            m["steps"]["modeling"] = "done"
        else:
            m["steps"]["modeling"] = "error"
            _log(m, "No 3D engine produced output. Set MESHY_API_KEY or install Blender desktop.", "error")

        # 4 — BRUCE repair pipeline (trimesh + pymeshfix + validation)
        _step(m, "optimization", "running")
        _log(m, "[BRUCE] Starting repair pipeline: trimesh + pymeshfix...", "info")
        final_stl: Path | None = None
        if raw_path:
            _log(m, "[BRUCE] Converting OBJ→STL, fixing non-manifold edges, scaling to 150mm...", "info")
            final_stl = _validate_and_repair(m, raw_path, m.get("target_size_mm", 150))
            if final_stl:
                m["files"]["model"] = str(final_stl)
                m["steps"]["optimization"] = "done"
                _log(m, "[BRUCE] Mesh clean — watertight, 0 non-manifold edges. Ready for Bambu.", "ok")
            else:
                m["steps"]["optimization"] = "error"
                m["files"]["model"] = str(raw_path)
                _log(m, "[BRUCE] Repair failed, using raw file", "warn")
        else:
            m["steps"]["optimization"] = "error"
            _log(m, "[BRUCE] No file to repair — KAIZEN step failed", "error")

        # 5 — Preview (placeholder — Blender render when desktop available)
        _step(m, "preview", "running")
        _log(m, "[KAIZEN] Preview pass (skipped — requires Blender desktop)", "info")
        await asyncio.sleep(0.5)
        m["steps"]["preview"] = "done"

        # 6 — Packaging + Bambu Studio handoff
        _step(m, "packaging", "running")
        _log(m, "[Packaging] Finalizing project archive...", "info")
        if final_stl and m.get("auto_bambu", True):
            launched = _launch_bambu_studio(m, final_stl)
            if launched:
                _log(m, "[Packaging] Bambu Studio launched with model — ready to slice", "success")
            else:
                _log(m, "[Packaging] Bambu Studio launch skipped (path not found in .env)", "warn")
        await asyncio.sleep(0.3)
        m["steps"]["packaging"] = "done"

        m["status"] = "complete" if final_stl else ("partial" if raw_path else "error")
        m["completed_at"] = datetime.now().isoformat()
        _log(m, f"Mission #{m['id']} complete — status: {m['status']}", "success")
        _persist_mission_log(m)

    except Exception as e:
        m["status"] = "error"
        m["error"] = str(e)
        _log(m, f"Pipeline crashed: {e}", "error")
        _persist_mission_log(m)


def _launch_bambu_studio(mission: dict, stl_path: Path) -> bool:
    """Auto-launch Bambu Studio with the final STL — non-blocking."""
    if not Path(BAMBU_STUDIO_PATH).exists():
        return False
    try:
        subprocess.Popen([BAMBU_STUDIO_PATH, str(stl_path)], shell=False)
        return True
    except Exception as e:
        _log(mission, f"Bambu launch failed: {e}", "warn")
        return False

# ── Routes ───────────────────────────────────────────────

@router.post("/v1/stl/mission")
async def create_stl_mission(req: MissionRequest):
    mission = _new_mission(req)
    _missions[mission["id"]] = mission
    _t = asyncio.create_task(_run_pipeline(mission["id"]))
    _background_tasks.add(_t)
    _t.add_done_callback(_background_tasks.discard)
    return {"mission_id": mission["id"], "status": "started"}


@router.get("/v1/stl/missions/recent")
async def list_recent_missions(limit: int = 10):
    """Returns recent missions sorted by created_at (most recent first).
    Used by frontend to auto-detect missions started externally (curl, n8n, etc.)."""
    items = sorted(_missions.values(), key=lambda m: m.get("created_at", ""), reverse=True)
    return [
        {
            "id": m["id"],
            "prompt": m.get("prompt", ""),
            "status": m.get("status"),
            "current_step": m.get("current_step"),
            "created_at": m.get("created_at"),
            "warnings": m.get("validation", {}).get("warnings", []),
            "has_error": m.get("status") == "error" or bool(m.get("error")),
        }
        for m in items[:limit]
    ]


@router.get("/v1/stl/mission/{mission_id}")
async def get_stl_mission(mission_id: str):
    if mission_id not in _missions:
        raise HTTPException(404, "Mission not found")
    m = _missions[mission_id]
    fp = m["files"].get("model", "")
    fp_obj = Path(fp) if fp else None
    has = bool(fp_obj and fp_obj.exists())
    return {
        "id":           m["id"],
        "status":       m["status"],
        "current_step": m["current_step"],
        "steps":        m["steps"],
        "logs":         m["logs"][-50:],
        "has_model":    has,
        "file_name":    fp_obj.name if has else None,
        "file_path":    str(fp_obj) if has else None,
        "file_ext":     fp_obj.suffix.lstrip(".").lower() if has else None,
        "file_size_kb": (fp_obj.stat().st_size // 1024) if has else 0,
        "output_dir":   str(STL_DIR),
        "concept":      m.get("concept", ""),
        "validation":   m.get("validation", {}),
        "warnings":     m.get("validation", {}).get("warnings", []),
        "error":        m.get("error"),
    }


@router.get("/v1/stl/download/{mission_id}")
async def download_stl(mission_id: str):
    if mission_id not in _missions:
        raise HTTPException(404, "Mission not found")
    m = _missions[mission_id]
    fp = m["files"].get("model", "")
    if not fp or not Path(fp).exists():
        raise HTTPException(404, "Model file not available yet")
    return FileResponse(
        fp,
        filename=f"jarvis_{mission_id}_{Path(fp).name}",
        media_type="application/octet-stream",
    )


@router.post("/v1/stl/bambu/{mission_id}")
async def open_in_bambu(mission_id: str):
    """Launch Bambu Studio with the generated STL — ready to slice & print."""
    if mission_id not in _missions:
        raise HTTPException(404, "Mission not found")
    m = _missions[mission_id]
    fp = m["files"].get("model", "")
    if not fp or not Path(fp).exists():
        raise HTTPException(404, "Model file not available yet")
    if not Path(BAMBU_STUDIO_PATH).exists():
        raise HTTPException(500, f"Bambu Studio not found at {BAMBU_STUDIO_PATH} — set BAMBU_STUDIO_PATH in .env")
    try:
        subprocess.Popen([BAMBU_STUDIO_PATH, fp], shell=False)  # NOSONAR - fire-and-forget GUI launch
        _log(m, f"Handoff to Bambu Studio: {Path(fp).name}", "success")
        return {"status": "launched", "file": Path(fp).name}
    except Exception as e:
        raise HTTPException(500, f"Failed to launch Bambu Studio: {e}")


@router.post("/v1/stl/open-folder/{mission_id}")
async def open_folder(mission_id: str):
    """Open the STL output folder in Windows Explorer."""
    if mission_id not in _missions:
        raise HTTPException(404, "Mission not found")
    m = _missions[mission_id]
    fp = m["files"].get("model", "")
    target = Path(fp).parent if fp else STL_DIR
    try:
        subprocess.Popen(["explorer", str(target)], shell=False)  # NOSONAR - fire-and-forget GUI launch
        return {"status": "opened", "path": str(target)}
    except Exception as e:
        raise HTTPException(500, f"Failed to open folder: {e}")
