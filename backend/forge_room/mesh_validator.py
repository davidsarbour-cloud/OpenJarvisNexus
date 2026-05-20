"""Validateur unifié — orchestre tous les checks de fabricabilité."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
import trimesh

from forge_room.manifold_checker         import check_manifold,       ManifoldResult
from forge_room.floating_geometry_detector import detect_floating,    FloatingResult
from forge_room.wall_thickness_checker   import check_wall_thickness, WallThicknessResult
from forge_room.support_analyzer         import analyze_supports,     SupportAnalysisResult

_RULES_PATH = Path(__file__).parent / "manufacturing_rules.json"
_RULES: dict = json.loads(_RULES_PATH.read_text())


@dataclass
class ValidationReport:
    passed: bool
    printability_score: int          # 0–100
    manifold:     ManifoldResult
    floating:     FloatingResult
    wall:         WallThicknessResult
    supports:     SupportAnalysisResult
    all_issues:   list[str] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)


def validate_mesh(
    mesh: trimesh.Trimesh,
    check_thickness: bool = True,
    check_supports: bool = True,
) -> ValidationReport:
    """
    Lance tous les validateurs et calcule un score de fabricabilité (0–100).
    Un mesh FDM-ready industriel doit scorer ≥ 75.
    """
    rules = _RULES

    manifold = check_manifold(mesh)
    floating = detect_floating(
        mesh,
        z_threshold_mm=rules["repair"]["merge_threshold_mm"] * 10,
    )
    wall = (
        check_wall_thickness(mesh, rules["fdm"]["min_wall_thickness_mm"])
        if check_thickness else _dummy_wall(rules["fdm"]["min_wall_thickness_mm"])
    )
    supports = (
        analyze_supports(mesh, rules["fdm"]["max_overhang_angle_deg"])
        if check_supports else _dummy_supports()
    )

    # Score pondéré — 6 critères industriels (total = 100)
    weights = rules["scoring"]
    score = 0
    passed_checks: list[str] = []
    failed_checks: list[str] = []

    # Watertight (30) : mesh étanche, sans trous ni bords ouverts
    if manifold.passed:
        score += weights["watertight_weight"]
        passed_checks.append("✓ Watertight/Étanche")
    else:
        failed_checks.append("✗ Watertight/Étanche")

    # Contact build plate (20) : adhérence suffisante au plateau
    # Fenêtre élargie à 2mm pour meshes organiques (pattes, bases irrégulières)
    z_min = float(mesh.bounds[0][2])
    face_z = mesh.triangles_center[:, 2]
    contact_tolerance = max(2.0, float(mesh.bounding_box.extents[2]) * 0.02)
    contact_faces = (face_z <= z_min + contact_tolerance).sum()
    contact_pct = (contact_faces / max(len(face_z), 1)) * 100
    if contact_pct >= rules["fdm"]["min_build_plate_contact_pct"]:
        score += weights["build_contact_weight"]
        passed_checks.append(f"✓ Contact build plate ({contact_pct:.1f}%)")
    else:
        failed_checks.append(f"✗ Contact build plate insuffisant ({contact_pct:.1f}%)")

    # Épaisseur de paroi (15)
    if wall.passed:
        score += weights["wall_thickness_weight"]
        passed_checks.append(f"✓ Épaisseur de paroi ({wall.min_thickness_mm}mm min)")
    else:
        failed_checks.append(f"✗ Parois trop fines ({wall.min_thickness_mm}mm — min {wall.threshold_mm}mm)")

    # Surplombs / overhangs (15)
    if not supports.support_required:
        score += weights["overhang_weight"]
        passed_checks.append("✓ Surplombs dans les limites FDM")
    else:
        failed_checks.append(f"✗ Surplombs excessifs ({supports.overhang_pct}%)")

    # Intégrité manifold — absence de géométrie flottante (10)
    if floating.passed:
        score += weights["manifold_integrity_weight"]
        passed_checks.append("✓ Aucune géométrie flottante")
    else:
        failed_checks.append(f"✗ Géométrie flottante ({floating.floating_components} composante(s))")

    # Exigences support — pas de supports nécessaires (10)
    if not supports.support_required:
        score += weights["support_requirements_weight"]
        passed_checks.append("✓ Aucun support requis")
    else:
        failed_checks.append(f"✗ Supports requis ({supports.support_volume_estimate_cm3:.1f}cm³ estimé)")

    all_issues = (
        manifold.issues + floating.issues + wall.issues + supports.issues
    )

    return ValidationReport(
        passed=score >= 75,
        printability_score=score,
        manifold=manifold,
        floating=floating,
        wall=wall,
        supports=supports,
        all_issues=all_issues,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
    )


def validate_stl_file(stl_path: Path, **kwargs) -> ValidationReport:
    mesh = trimesh.load(str(stl_path), force="mesh")
    return validate_mesh(mesh, **kwargs)


# ── Dummies pour skip optionnel ───────────────────────────

def _dummy_wall(threshold: float) -> WallThicknessResult:
    from forge_room.wall_thickness_checker import WallThicknessResult
    return WallThicknessResult(
        min_thickness_mm=threshold,
        mean_thickness_mm=threshold,
        thin_face_pct=0.0,
        samples_checked=0,
        threshold_mm=threshold,
    )

def _dummy_supports() -> SupportAnalysisResult:
    return SupportAnalysisResult(
        overhang_area_cm2=0.0,
        total_area_cm2=0.0,
        overhang_pct=0.0,
        critical_overhang_pct=0.0,
        bridging_area_cm2=0.0,
        support_volume_estimate_cm3=0.0,
        support_required=False,
        max_overhang_angle_deg=0.0,
    )
