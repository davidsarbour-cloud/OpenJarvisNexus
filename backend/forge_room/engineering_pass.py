"""Forge Engineering Pass — sculpt → multi-piece print-ready.

Takes a sculpted STL + specs (cut planes, plate size, hollow) and returns:
  - per-piece STL files, exported individually,
  - a unified report (manifold + walls + supports + plate-fit) per piece.

This is the "irreducible non-art" step from the sculpt playbook
(03_Projects/STL/sculpt-3d-playbook.md): the human (or sculpteur) sculpts;
this pass turns that artisan STL into slicer-ready pieces, validated.

Blender is invoked headless via the existing `blender_bridge.BLENDER_PATH`.
The Blender script is embedded below — it imports the STL, splits it on
Z-axis cut planes (recursive bisect, preserves both sides), optionally
hollows each piece via a Solidify modifier, and exports one STL per piece
plus a manifest. The orchestrator then validates each piece with the
existing `mesh_validator.validate_mesh` and rolls them into one report.

Limitations (MVP):
  - Cuts are Z-axis planes only (extend to X/Y if needed).
  - No auto-orient yet (TODO: orientation_optimizer per piece).
  - No procedural tenons/mortaises (assumes the sculpter pre-added them).
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

import trimesh

from forge_room.blender_bridge import BLENDER_PATH
from forge_room.blender_bridge import is_available as blender_available
from forge_room.mesh_validator import validate_mesh

# ── Embedded Blender script ──────────────────────────────────────────────────
# Reads ENG_IN / ENG_OUT / ENG_SPECS env vars; writes pieces + manifest.json.
# Robust to Blender 3.x (import_mesh.stl) vs 4.x (wm.stl_import).

_BLENDER_SCRIPT = r'''
import bpy, json, os
from pathlib import Path
from mathutils import Vector

IN   = Path(os.environ["ENG_IN"])
OUT  = Path(os.environ["ENG_OUT"])
SPEC = json.loads(os.environ["ENG_SPECS"])
OUT.mkdir(parents=True, exist_ok=True)


def import_stl(p):
    try:
        bpy.ops.wm.stl_import(filepath=str(p))           # Blender 4.x
    except AttributeError:
        bpy.ops.import_mesh.stl(filepath=str(p))         # Blender 3.x


def export_stl(p):
    try:
        bpy.ops.wm.stl_export(filepath=str(p), export_selected_objects=True)
    except AttributeError:
        bpy.ops.export_mesh.stl(filepath=str(p), use_selection=True)


def bisect(obj, z, *, clear_outer=False, clear_inner=False):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=(0, 0, z), plane_no=(0, 0, 1),
                        use_fill=True, clear_outer=clear_outer, clear_inner=clear_inner)
    bpy.ops.object.mode_set(mode="OBJECT")


# Clean scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

import_stl(IN)
src = bpy.context.selected_objects[0]
src.name = "src"

pieces = [src]
cuts = sorted([float(c["value_mm"]) for c in SPEC.get("cuts", [])
               if str(c.get("axis", "Z")).upper() == "Z"])

for z in cuts:
    new_pieces = []
    for obj in pieces:
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        zmin = min(c.z for c in corners)
        zmax = max(c.z for c in corners)
        if zmin < z < zmax:
            new_obj = obj.copy()
            new_obj.data = obj.data.copy()
            bpy.context.collection.objects.link(new_obj)
            bisect(obj, z, clear_outer=True)             # original keeps lower
            bisect(new_obj, z, clear_inner=True)         # copy keeps upper
            new_pieces.extend([obj, new_obj])
        else:
            new_pieces.append(obj)
    pieces = new_pieces

# Optional hollow — solidify inset on each piece
hollow = SPEC.get("hollow", {})
if hollow.get("enabled"):
    wall = float(hollow.get("wall_mm", 2.0))
    for p in pieces:
        bpy.context.view_layer.objects.active = p
        m = p.modifiers.new("Hollow", "SOLIDIFY")
        m.thickness = -wall
        m.offset = 1.0
        bpy.ops.object.modifier_apply(modifier=m.name)

# Export — order by descending bbox height (tallest piece first)
def _height(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return max(c.z for c in cs) - min(c.z for c in cs)

out_files = []
for i, p in enumerate(sorted(pieces, key=_height, reverse=True)):
    path = OUT / f"piece_{i}.stl"
    bpy.ops.object.select_all(action="DESELECT")
    p.select_set(True)
    bpy.context.view_layer.objects.active = p
    export_stl(path)
    out_files.append(str(path))

(OUT / "blender_manifest.json").write_text(json.dumps({
    "input": str(IN), "pieces": out_files, "count": len(out_files),
    "cuts_applied_mm": cuts, "hollow": SPEC.get("hollow", {}),
}, indent=2))
print(f"[engineering-pass] {len(out_files)} pieces exported")
'''


# ── Report shape ─────────────────────────────────────────────────────────────

@dataclass
class PieceReport:
    name:         str
    dims_mm:      tuple[float, float, float]   # x, y, z extents
    fits_plate:   bool
    manifold:     bool
    min_wall_mm:  float
    overhang_pct: float
    score:        float
    issues:       list[str] = field(default_factory=list)


@dataclass
class EngineeringReport:
    ok:                 bool
    blender_available:  bool
    input_path:         str
    pieces:             list[PieceReport]
    cuts_applied_mm:    list[float] = field(default_factory=list)
    warnings:           list[str]   = field(default_factory=list)
    stderr_tail:        str         = ""
    error:              str | None  = None


# ── Orchestrator ─────────────────────────────────────────────────────────────

def run_engineering_pass(input_stl: Path, specs: dict, output_dir: Path,
                         timeout: int = 240) -> EngineeringReport:
    """Run Blender headless to cut + hollow + export pieces, then validate each."""
    if not blender_available():
        return EngineeringReport(
            ok=False, blender_available=False, input_path=str(input_stl),
            pieces=[], error=f"Blender not found at {BLENDER_PATH}",
        )
    if not input_stl.exists():
        return EngineeringReport(
            ok=False, blender_available=True, input_path=str(input_stl),
            pieces=[], error="input STL not found",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    script_path = output_dir / "_engineering_pass.py"
    script_path.write_text(_BLENDER_SCRIPT, encoding="utf-8")

    env = os.environ.copy()
    env["ENG_IN"]    = str(input_stl)
    env["ENG_OUT"]   = str(output_dir)
    env["ENG_SPECS"] = json.dumps(specs, ensure_ascii=False)

    stderr_tail = ""
    try:
        r = subprocess.run(
            [BLENDER_PATH, "--background", "--python", str(script_path)],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        stderr_tail = (r.stderr or "")[-400:]
    except subprocess.TimeoutExpired:
        return EngineeringReport(
            ok=False, blender_available=True, input_path=str(input_stl),
            pieces=[], error=f"Blender timed out after {timeout}s",
        )
    finally:
        script_path.unlink(missing_ok=True)

    manifest = output_dir / "blender_manifest.json"
    if not manifest.exists():
        return EngineeringReport(
            ok=False, blender_available=True, input_path=str(input_stl),
            pieces=[], stderr_tail=stderr_tail,
            error="Blender did not produce a manifest (see stderr_tail)",
        )

    info = json.loads(manifest.read_text(encoding="utf-8"))
    plate = specs.get("plate_mm", [256, 256])
    piece_reports: list[PieceReport] = []
    for piece_path in info.get("pieces", []):
        p = Path(piece_path)
        try:
            mesh = trimesh.load(str(p), force="mesh")
            v    = validate_mesh(mesh, check_thickness=True, check_supports=True)
            dims = tuple(float(d) for d in mesh.extents)   # STL is in mm
            piece_reports.append(PieceReport(
                name=p.name, dims_mm=dims,
                fits_plate=(dims[0] <= plate[0] and dims[1] <= plate[1]),
                manifold=v.manifold.is_watertight,
                min_wall_mm=v.wall.min_thickness_mm,
                overhang_pct=v.supports.overhang_pct,
                score=v.printability_score,
                issues=list(v.failed_checks),
            ))
        except Exception as e:
            piece_reports.append(PieceReport(
                name=p.name, dims_mm=(0.0, 0.0, 0.0),
                fits_plate=False, manifold=False,
                min_wall_mm=0.0, overhang_pct=100.0, score=0.0,
                issues=[f"validate failed: {e}"],
            ))

    warnings: list[str] = []
    if any(not pr.fits_plate for pr in piece_reports):
        warnings.append("some pieces exceed the target plate")
    if any(not pr.manifold for pr in piece_reports):
        warnings.append("some pieces are non-manifold")
    if not piece_reports:
        warnings.append("no pieces produced")

    ok = bool(piece_reports) and all(pr.manifold and pr.fits_plate for pr in piece_reports)
    return EngineeringReport(
        ok=ok, blender_available=True, input_path=str(input_stl),
        pieces=piece_reports, cuts_applied_mm=info.get("cuts_applied_mm", []),
        warnings=warnings, stderr_tail=stderr_tail,
    )


def report_to_dict(r: EngineeringReport) -> dict:
    """JSON-safe view for the FastAPI endpoint."""
    return asdict(r)
