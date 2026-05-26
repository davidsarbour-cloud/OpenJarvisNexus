"""Génération du rapport de fabrication manufacturing_report.json."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import trimesh

from forge_room.mesh_repair import RepairResult
from forge_room.mesh_validator import ValidationReport
from forge_room.orientation_optimizer import OrientationResult

_RULES = json.loads((Path(__file__).parent / "manufacturing_rules.json").read_text())


@dataclass
class ManufacturingReport:
    mission_id: str
    generated_at: str
    # Fabricabilité
    printability_score: int
    bambu_ready: bool
    manifold_valid: bool
    floating_regions_detected: int
    repaired_geometry: bool
    repairs_applied: list[str]
    # Supports
    support_required: bool
    overhang_pct: float
    # Géométrie
    face_count: int
    vertex_count: int
    volume_cm3: float
    surface_area_cm2: float
    bounding_box_mm: dict
    # Estimation fabrication
    estimated_material_g: float
    estimated_print_time_min: float
    recommended_layer_height_mm: float
    recommended_material: str
    # Orientation
    orientation_used: str
    orientation_score: float
    # Risque
    structural_risk_score: int      # 0 (faible) → 100 (élevé)
    # Détail checks
    passed_checks: list[str]
    failed_checks: list[str]
    all_issues: list[str]
    # Analyse industrielle détaillée
    wall_thickness_min_mm: float
    overhang_max_angle_deg: float
    estimated_print_time_str: str   # ex: "12min" ou "1h23min"
    support_volume_cm3: float
    printability_grade: str          # "A", "B", "C", "D" basé sur score


def generate_report(
    mission_id: str,
    mesh: trimesh.Trimesh,
    validation: ValidationReport,
    repair: RepairResult | None = None,
    orientation: OrientationResult | None = None,
    stl_path: Path | None = None,
) -> ManufacturingReport:
    """Construit le rapport complet depuis les résultats des modules."""
    rules = _RULES

    # Estimation matière
    vol_cm3 = validation.manifold.volume_cm3
    density = rules["print_estimation"]["material_density_g_cm3"]
    infill  = rules["print_estimation"]["infill_pct"] / 100.0
    # Volume effectif = surface + infill intérieur
    shell_thickness_cm = rules["fdm"]["min_wall_thickness_mm"] / 10.0
    area_cm2 = validation.manifold.surface_area_cm2
    shell_vol  = area_cm2 * shell_thickness_cm
    infill_vol = max(vol_cm3 - shell_vol, 0.0) * infill
    material_g = round((shell_vol + infill_vol) * density, 2)

    # Estimation temps d'impression (très approximatif — basé sur volume)
    speed_mm_s = rules["print_estimation"]["print_speed_mm_s"]
    layer_h_mm = rules["fdm"]["layer_height_default_mm"]
    # Nombre de couches
    bbox = mesh.bounding_box.extents
    height_mm = max(bbox[2], 1.0)
    layers = height_mm / layer_h_mm
    # Périmètre moyen par couche ≈ sqrt(section) * 4
    section_mm2 = bbox[0] * bbox[1]
    perimeter_mm = 4 * (section_mm2 ** 0.5)
    travel_per_layer = perimeter_mm * (1 + infill * 3)
    print_time_min = round((layers * travel_per_layer / speed_mm_s) / 60.0, 1)

    # Score risque structurel (inverse du score fabricabilité)
    risk = max(0, 100 - validation.printability_score)
    if validation.supports.critical_overhang_pct > 5.0:
        risk = min(100, risk + 15)
    if validation.floating.floating_components > 0:
        risk = min(100, risk + 20)

    # Analyse industrielle détaillée
    wall_thickness_min_mm = validation.wall.min_thickness_mm
    overhang_max_angle_deg = validation.supports.max_overhang_angle_deg
    support_volume_cm3 = validation.supports.support_volume_estimate_cm3

    # Conversion temps d'impression en format lisible
    total_min = int(round(print_time_min))
    if total_min < 60:
        estimated_print_time_str = f"{total_min}min"
    else:
        heures = total_min // 60
        minutes = total_min % 60
        estimated_print_time_str = f"{heures}h{minutes:02d}min"

    # Grade de fabricabilité basé sur le score
    score = validation.printability_score
    if score >= 90:
        printability_grade = "A"
    elif score >= 75:
        printability_grade = "B"
    elif score >= 60:
        printability_grade = "C"
    else:
        printability_grade = "D"

    return ManufacturingReport(
        mission_id=mission_id,
        generated_at=datetime.now().isoformat(),
        printability_score=validation.printability_score,
        bambu_ready=validation.passed,
        manifold_valid=validation.manifold.passed,
        floating_regions_detected=validation.floating.floating_components,
        repaired_geometry=repair is not None and bool(repair.repairs_applied),
        repairs_applied=repair.repairs_applied if repair else [],
        support_required=validation.supports.support_required,
        overhang_pct=validation.supports.overhang_pct,
        face_count=len(mesh.faces),
        vertex_count=len(mesh.vertices),
        volume_cm3=vol_cm3,
        surface_area_cm2=validation.manifold.surface_area_cm2,
        bounding_box_mm={
            "x": round(float(bbox[0]), 2),
            "y": round(float(bbox[1]), 2),
            "z": round(float(bbox[2]), 2),
        },
        estimated_material_g=material_g,
        estimated_print_time_min=print_time_min,
        recommended_layer_height_mm=layer_h_mm,
        recommended_material=rules["fdm"]["default_material"],
        orientation_used=orientation.label if orientation else "identité",
        orientation_score=orientation.score if orientation else 0.0,
        structural_risk_score=risk,
        passed_checks=validation.passed_checks,
        failed_checks=validation.failed_checks,
        all_issues=validation.all_issues,
        wall_thickness_min_mm=wall_thickness_min_mm,
        overhang_max_angle_deg=overhang_max_angle_deg,
        estimated_print_time_str=estimated_print_time_str,
        support_volume_cm3=support_volume_cm3,
        printability_grade=printability_grade,
    )


def save_report(report: ManufacturingReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
