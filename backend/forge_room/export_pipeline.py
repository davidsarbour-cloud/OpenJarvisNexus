"""Pipeline export complet : validate -> repair -> orient -> scale -> validate finale -> STL.
Aucun STL ne sort sans passer par cette sequence.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
import trimesh

from forge_room.mesh_validator      import validate_mesh, ValidationReport
from forge_room.mesh_repair         import auto_repair, scale_to_target, place_on_build_plate, RepairResult
from forge_room.orientation_optimizer import optimize_orientation, apply_orientation, OrientationResult

_RULES = json.loads((Path(__file__).parent / "manufacturing_rules.json").read_text(encoding="utf-8"))


@dataclass
class ExportResult:
    success: bool
    stl_path: Path | None
    pre_validation:  ValidationReport | None
    repair:          RepairResult | None
    orientation:     OrientationResult | None
    post_validation: ValidationReport | None
    final_score: int
    errors: list = field(default_factory=list)
    log: list = field(default_factory=list)


def run_export_pipeline(
    input_path: Path,
    output_path: Path,
    skip_orientation: bool = False,
    skip_repair: bool = False,
) -> ExportResult:
    """Pipeline complet depuis un STL brut vers un STL Bambu-ready."""
    log = []
    errors = []

    try:
        mesh = trimesh.load(str(input_path), force="mesh")
        log.append(f"Charge: {input_path.name} - {len(mesh.faces)} faces, {len(mesh.vertices)} vertices")
    except Exception as e:
        return ExportResult(
            success=False, stl_path=None,
            pre_validation=None, repair=None, orientation=None, post_validation=None,
            final_score=0, errors=[f"Chargement STL echoue: {e}"],
        )

    log.append("Validation initiale...")
    pre_val = validate_mesh(mesh, check_thickness=True, check_supports=True)
    log.append(f"Score initial: {pre_val.printability_score}/100")
    if pre_val.all_issues:
        log.extend([f"  WARN {i}" for i in pre_val.all_issues])

    repair_result = None
    if not skip_repair and not pre_val.passed:
        log.append("Reparation automatique...")
        mesh, repair_result = auto_repair(mesh)
        for r in repair_result.repairs_applied:
            log.append(f"  OK {r}")
        if repair_result.error:
            errors.append(f"Reparation partielle: {repair_result.error}")

    target_mm = _RULES["fdm"]["target_longest_dim_mm"]
    mesh = scale_to_target(mesh, target_mm)
    log.append(f"Echelle appliquee - dimension max: {target_mm}mm")

    orient_result = None
    if not skip_orientation:
        log.append("Optimisation orientation FDM...")
        orient_result = optimize_orientation(mesh, _RULES["fdm"]["max_overhang_angle_deg"])
        log.append(
            f"Meilleure orientation: {orient_result.label} "
            f"(score={orient_result.score}, surplombs={orient_result.overhang_pct}%)"
        )
        mesh = apply_orientation(mesh, orient_result)
    else:
        mesh = place_on_build_plate(mesh)

    log.append("Validation finale...")
    post_val = validate_mesh(mesh, check_thickness=True, check_supports=True)
    log.append(f"Score final: {post_val.printability_score}/100")
    log.extend([f"  OK {c}" for c in post_val.passed_checks])
    if post_val.failed_checks:
        log.extend([f"  FAIL {c}" for c in post_val.failed_checks])
        errors.extend(post_val.failed_checks)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mesh.export(str(output_path))
        size_kb = output_path.stat().st_size // 1024
        log.append(f"STL exporte: {output_path.name} ({size_kb}KB)")
    except Exception as e:
        errors.append(f"Export STL echoue: {e}")
        return ExportResult(
            success=False, stl_path=None,
            pre_validation=pre_val,
            repair=repair_result,
            orientation=orient_result,
            post_validation=post_val,
            final_score=post_val.printability_score,
            errors=errors, log=log,
        )

    return ExportResult(
        success=True,
        stl_path=output_path,
        pre_validation=pre_val,
        repair=repair_result,
        orientation=orient_result,
        post_validation=post_val,
        final_score=post_val.printability_score,
        errors=errors,
        log=log,
    )
