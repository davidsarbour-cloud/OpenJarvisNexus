"""Printability analysis for FDM 3D prints.

Turns a trimesh mesh into a 0-100 printability score plus actionable flags
(supports needed, thin features, overhang, watertight) so the STL pipeline can
gate "risky" models and tell the user exactly what to do before slicing.

Honesty note: TRUE per-wall thickness is a slicer-grade computation. The thin
heuristic here catches gross thinness (smallest dimension), not every thin wall.
The prompt side (stl_agent) asks Meshy for >=2-3 mm; this module flags + scores.
"""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
from pathlib import Path

# FDM self-support rule: faces steeper than 45° from vertical need support. A
# downward-pointing face normal with z < -sin(45°) ≈ -0.707 is an unsupported
# overhang. (Stricter than the legacy -0.5 proxy → fewer false positives.)
OVERHANG_NORMAL_Z = -math.sin(math.radians(45))  # ≈ -0.7071

GATE_SCORE_READY  = 70   # >= this and no supports → "ready"
GATE_SCORE_RISKY  = 50   # below this → "risky" (hard gate)


def analyze(mesh, *, min_wall_mm: float = 2.0) -> dict:
    """Compute printability metrics + a 0-100 score for a trimesh mesh."""
    normals = mesh.face_normals
    areas   = mesh.area_faces
    total   = float(areas.sum()) or 1.0

    # A face is a true overhang if it points downward beyond 45° AND sits above
    # the build plate. The flat bottom resting ON the bed points straight down
    # too, but it's supported — exclude faces near min-z so we don't count it.
    centers_z = mesh.triangles_center[:, 2]
    min_z     = float(mesh.bounds[0][2])
    height    = max(float(mesh.extents[2]), 1e-6)
    bed_band  = min_z + 0.03 * height
    is_overhang = (normals[:, 2] < OVERHANG_NORMAL_Z) & (centers_z > bed_band)
    overhang_area = float(areas[is_overhang].sum())
    overhang_pct  = round(overhang_area / total * 100, 1)

    bbox    = [float(x) for x in mesh.bounding_box.extents]
    min_dim = round(min(bbox), 2) if bbox else 0.0
    faces   = int(len(mesh.faces))
    watertight = bool(mesh.is_watertight)
    winding_ok = bool(mesh.is_winding_consistent)

    # Thin-feature heuristic: smallest overall dimension vs target wall. Catches
    # gross thinness (a 1mm-thick wing) but not every interior thin wall.
    really_thin = min_dim < min_wall_mm
    thin        = min_dim < min_wall_mm * 1.5

    supports_required = overhang_pct > 15

    # ── Score 0-100 ──
    score = 100.0
    if not watertight:        score -= 40          # biggest killer for slicing
    if not winding_ok:        score -= 10
    score -= min(overhang_pct, 40) / 40 * 30       # up to -30 for overhang
    if really_thin:           score -= 20
    elif thin:                score -= 10
    if faces > 300_000:       score -= 5
    score = max(0, min(100, round(score)))

    warnings: list[str] = []
    if not watertight:
        warnings.append("non-watertight — le slicer va galérer")
    if overhang_pct > 30:
        warnings.append(f"overhang critique {overhang_pct}% — supports OBLIGATOIRES")
    elif overhang_pct > 15:
        warnings.append(f"overhang {overhang_pct}% — supports recommandés")
    if really_thin:
        warnings.append(f"trop fin (min {min_dim}mm < {min_wall_mm}mm) — risque non-imprimable / casse")
    elif thin:
        warnings.append(f"parties fines (min {min_dim}mm) — fragile")
    if faces > 300_000:
        warnings.append(f"{faces} faces — slicing lent")

    verdict = ("ready" if score >= GATE_SCORE_READY and not supports_required
               else "supports_required" if score >= GATE_SCORE_RISKY
               else "risky")

    return {
        "printability_score": score,
        "verdict":            verdict,           # ready | supports_required | risky
        "supports_required":  supports_required,
        "support_type":       "tree" if supports_required else None,
        "overhang_pct":       overhang_pct,
        "min_dimension_mm":   min_dim,
        "thin_features":      thin,
        "watertight":         watertight,
        "winding_ok":         winding_ok,
        "faces":              faces,
        "bbox_mm":            [round(x, 2) for x in bbox],
        "warnings":           warnings,
    }


# ── Blender headless preview ──────────────────────────────────────────────────

_PREVIEW_SCRIPT = r'''
import bpy, os, math
from mathutils import Vector

stl = os.environ["STL_IN"]; out = os.environ["PNG_OUT"]
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import STL (Blender 4.0+: wm.stl_import; older: import_mesh.stl)
try:
    bpy.ops.wm.stl_import(filepath=stl)
except Exception:
    bpy.ops.import_mesh.stl(filepath=stl)

objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not objs:
    raise SystemExit("no mesh imported")
obj = objs[0]

# Center the object at world origin and measure its radius.
bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
center = sum(bbox, Vector()) / 8.0
obj.location -= center
radius = max((Vector(b) - center).length for b in bbox) or 1.0

# Simple matte material.
mat = bpy.data.materials.new("preview"); mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.55, 0.58, 0.62, 1.0)
    if "Roughness" in bsdf.inputs: bsdf.inputs["Roughness"].default_value = 0.6
obj.data.materials.append(mat)

# Camera at a 3/4 angle, framed to the bounding sphere.
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
d = radius * 3.0
cam.location = Vector((d, -d, d * 0.8))
direction = -cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam
cam_data.lens = 50

# Sun lamps: no distance falloff, so brightness is independent of model scale.
for rot, energy in [((0.9, 0.1, 0.7), 4.5), ((1.3, 0.0, -2.3), 2.0), ((-0.5, 0.2, 1.2), 1.5)]:
    ld = bpy.data.lights.new("S", "SUN"); ld.energy = energy
    lo = bpy.data.objects.new("S", ld); lo.rotation_euler = rot
    bpy.context.scene.collection.objects.link(lo)

scene = bpy.context.scene
for _eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = _eng; break
    except Exception:
        continue
scene.render.resolution_x = 640; scene.render.resolution_y = 640
scene.render.film_transparent = True
scene.render.filepath = out
try:
    scene.world = bpy.data.worlds.new("w"); scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.18,0.18,0.20,1)
except Exception:
    pass
bpy.ops.render.render(write_still=True)
'''


def render_preview(stl_path: str | Path, out_png: str | Path,
                   blender_path: str, timeout: float = 90.0) -> bool:
    """Render a preview PNG of the STL via Blender headless. Best-effort:
    returns False (never raises) if Blender is missing or the render fails."""
    if not blender_path or not Path(blender_path).exists():
        return False
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(_PREVIEW_SCRIPT)
            tmp = f.name
        env = {**os.environ, "STL_IN": str(stl_path), "PNG_OUT": str(out_png)}
        subprocess.run([blender_path, "--background", "--python", tmp],
                       env=env, capture_output=True, timeout=timeout)
        return Path(out_png).exists()
    except Exception as e:
        print(f"[printability] preview render failed: {e}")
        return False
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
