"""Validateur unifie - orchestre tous les checks de fabricabilite."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import trimesh

from forge_room.floating_geometry_detector import FloatingResult, detect_floating
from forge_room.manifold_checker import ManifoldResult, check_manifold
from forge_room.support_analyzer import SupportAnalysisResult, analyze_supports
from forge_room.wall_thickness_checker import WallThicknessResult, check_wall_thickness

_RULES_PATH = Path(__file__).parent / "manufacturing_rules.json"
_RULES: dict = json.loads(_RULES_PATH.read_text(encoding="utf-8"))


@dataclass
class ValidationReport:
    passed: bool
    printability_score: int          # 0-100
    manifold:     ManifoldResult
    floating:     FloatingResult
    wall:         WallThicknessResult
    supports:     SupportAnalysisResult
    all_issues:   list = field(default_factory=list)
    passed_checks: list = field(default_factory=list)
    failed_checks: list = field(default_factory=list)


def validate_mesh(
    mesh: trimesh.Trimesh,
    check_thickness: bool = True,
    check_supports: bool = True,
) -> ValidationReport:
    """Lance tous les validateurs et calcule un score de fabricabilite (0-100).
    Un mesh FDM-ready industriel doit scorer >= 75.
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

    weights = rules["scoring"]
    score = 0
    passed_checks = []
    failed_checks = []

    if manifold.passed:
        score += weights["watertight_weight"]
        passed_checks.append("OK Watertight/Etanche")
    else:
        failed_checks.append("FAIL Watertight/Etanche")

    # Contact build plate - pondere par SURFACE (coherent avec orientation_optimizer)
    z_min = float(mesh.bounds[0][2])
    face_z = mesh.triangles_center[:, 2]
    face_areas = mesh.area_faces
    total_area = float(max(face_areas.sum(), 1e-9))
    contact_tolerance = max(2.0, float(mesh.bounding_box.extents[2]) * 0.02)
    contact_mask = face_z <= z_min + contact_tolerance
    contact_area = float(face_areas[contact_mask].sum())
    contact_pct = (contact_area / total_area) * 100.0
    if contact_pct >= rules["fdm"]["min_build_plate_contact_pct"]:
        score += weights["build_contact_weight"]
        passed_checks.append(f"OK Contact build plate ({contact_pct:.1f}%)")
    else:
        failed_checks.append(f"FAIL Contact build plate insuffisant ({contact_pct:.1f}%)")

    if wall.passed:
        score += weights["wall_thickness_weight"]
        passed_checks.append(f"OK Epaisseur paroi ({wall.min_thickness_mm}mm min)")
    else:
        failed_checks.append(f"FAIL Parois trop fines ({wall.min_thickness_mm}mm)")

    if not supports.support_required:
        score += weights["overhang_weight"]
        passed_checks.append("OK Surplombs dans limites FDM")
    else:
        failed_checks.append(f"FAIL Surplombs excessifs ({supports.overhang_pct}%)")

    if floating.passed:
        score += weights["manifold_integrity_weight"]
        passed_checks.append("OK Aucune geometrie flottante")
    else:
        failed_checks.append(f"FAIL Geometrie flottante ({floating.floating_components})")

    if not supports.support_required:
        score += weights["support_requirements_weight"]
        passed_checks.append("OK Aucun support requis")
    else:
        failed_checks.append(f"FAIL Supports requis ({supports.support_volume_estimate_cm3:.1f}cm3)")

    all_issues = manifold.issues + floating.issues + wall.issues + supports.issues

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


def validate_stl_file(stl_path, **kwargs):
    mesh = trimesh.load(str(stl_path), force="mesh")
    return validate_mesh(mesh, **kwargs)


def _dummy_wall(threshold):
    from forge_room.wall_thickness_checker import WallThicknessResult
    return WallThicknessResult(
        min_thickness_mm=threshold,
        mean_thickness_mm=threshold,
        thin_face_pct=0.0,
        samples_checked=0,
        threshold_mm=threshold,
    )


def _dummy_supports():
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
