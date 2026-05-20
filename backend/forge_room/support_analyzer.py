"""Analyse des surplombs et besoins en supports pour impression FDM."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import trimesh


@dataclass
class SupportAnalysisResult:
    overhang_area_cm2: float
    total_area_cm2: float
    overhang_pct: float
    critical_overhang_pct: float   # > 60° (support quasi-obligatoire)
    bridging_area_cm2: float
    support_volume_estimate_cm3: float
    support_required: bool
    max_overhang_angle_deg: float
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.support_required


def analyze_supports(
    mesh: trimesh.Trimesh,
    max_overhang_deg: float = 45.0,
) -> SupportAnalysisResult:
    """
    Classifie les faces par angle avec la verticale.
    Angle 0° = face horizontale regardant vers le haut (pas de problème).
    Angle 90° = face verticale.
    Angle > 45° regardant vers le bas = surplomb FDM.
    """
    issues: list[str] = []
    face_normals = mesh.face_normals
    face_areas   = mesh.area_faces

    # Angle entre la normale et le vecteur -Z (bas)
    # cos(theta) = dot(normal, -Z) / |normal| = -normal_z
    # theta = 0 → face pointe vers le bas (surplomb absolu)
    # theta = 180 → face pointe vers le haut (OK)
    down = np.array([0.0, 0.0, -1.0])
    cos_vals  = np.clip(face_normals @ down, -1.0, 1.0)
    angles_deg = np.degrees(np.arccos(cos_vals))

    # Face est surplomb si elle regarde vers le bas et angle_avec_vertical > seuil
    # Normal Z < 0 AND angle with horizontal > (90 - max_overhang_deg)
    z_comp = face_normals[:, 2]
    downward_mask = z_comp < 0          # faces regardant vers le bas
    overhang_threshold = 90.0 - max_overhang_deg   # angle avec vertical

    # Surplombs simples (> seuil)
    overhang_mask = downward_mask & (angles_deg < (90.0 - max_overhang_deg + 90.0))
    # Reformulation: face en surplomb si normale_z < -sin(max_overhang_deg)
    sin_thresh = np.sin(np.radians(max_overhang_deg))
    overhang_mask = z_comp < -sin_thresh

    # Surplombs critiques (> 60°)
    critical_mask = z_comp < -np.sin(np.radians(60.0))

    overhang_area   = float(face_areas[overhang_mask].sum()) / 100.0    # mm² → cm²
    critical_area   = float(face_areas[critical_mask].sum()) / 100.0
    total_area      = float(face_areas.sum()) / 100.0

    overhang_pct  = round((overhang_area / max(total_area, 1e-9)) * 100.0, 1)
    critical_pct  = round((critical_area / max(total_area, 1e-9)) * 100.0, 1)

    # Bridging = faces quasi-horizontales regardant vers le bas (angle < 15° with horizontal)
    bridge_mask = (z_comp < -0.97)  # quasi-horizontal vers le bas
    bridge_area = float(face_areas[bridge_mask].sum()) / 100.0

    # Estimation volume support (grossier) : aire surplomb × hauteur moyenne surplomb
    support_vol = 0.0
    if overhang_mask.any():
        oh_verts = mesh.vertices[mesh.faces[overhang_mask].flatten()]
        mean_height = float(oh_verts[:, 2].mean()) / 10.0  # mm → cm
        support_vol = round(overhang_area * mean_height * 0.3, 3)  # coefficient remplissage

    support_required = overhang_pct > 5.0 or critical_pct > 1.0

    if support_required:
        issues.append(
            f"{overhang_pct}% de surface en surplomb (>{max_overhang_deg}°) — "
            f"supports probablement requis"
        )
    if critical_pct > 0:
        issues.append(f"{critical_pct}% de surplombs critiques (>60°)")

    max_angle = float(angles_deg[downward_mask].min()) if downward_mask.any() else 0.0
    max_angle = round(90.0 - max_angle + 90.0, 1) if max_angle < 90.0 else 0.0

    return SupportAnalysisResult(
        overhang_area_cm2=round(overhang_area, 3),
        total_area_cm2=round(total_area, 3),
        overhang_pct=overhang_pct,
        critical_overhang_pct=critical_pct,
        bridging_area_cm2=round(bridge_area, 3),
        support_volume_estimate_cm3=support_vol,
        support_required=support_required,
        max_overhang_angle_deg=max_angle,
        issues=issues,
    )
