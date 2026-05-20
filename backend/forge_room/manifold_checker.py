"""Vérification manifold/watertight — condition nécessaire pour l'impression FDM."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import trimesh


@dataclass
class ManifoldResult:
    is_watertight: bool
    is_winding_consistent: bool
    non_manifold_edges: int
    open_edges: int
    degenerate_faces: int
    volume_cm3: float
    surface_area_cm2: float
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.is_watertight
            and self.is_winding_consistent
            and self.non_manifold_edges == 0
            and self.volume_cm3 > 0
        )


def check_manifold(mesh: trimesh.Trimesh) -> ManifoldResult:
    issues: list[str] = []

    is_watertight = bool(mesh.is_watertight)
    if not is_watertight:
        issues.append("Mesh non-watertight — surfaces ouvertes détectées")

    is_winding = bool(mesh.is_winding_consistent)
    if not is_winding:
        issues.append("Orientation des normales incohérente")

    # Arêtes non-manifold (partagées par ≠ 2 faces) et arêtes ouvertes
    edges_sorted = np.sort(mesh.edges_unique, axis=1)
    _, inv = np.unique(edges_sorted, axis=0, return_inverse=True)
    counts = np.bincount(inv)
    non_manifold = int((counts > 2).sum())
    open_edges   = int((counts == 1).sum())

    if non_manifold > 0:
        issues.append(f"{non_manifold} arêtes non-manifold")
    if open_edges > 0:
        issues.append(f"{open_edges} arêtes ouvertes (bordure)")

    # Faces dégénérées (aire ≈ 0)
    face_areas = mesh.area_faces
    degen = int((face_areas < 1e-10).sum())
    if degen > 0:
        issues.append(f"{degen} faces dégénérées")

    # Volume (mm³ → cm³)
    vol_cm3 = float(mesh.volume) / 1000.0 if is_watertight else 0.0
    if vol_cm3 < 0:
        vol_cm3 = abs(vol_cm3)
        issues.append("Volume négatif — normales probablement inversées")

    area_cm2 = float(mesh.area) / 100.0

    return ManifoldResult(
        is_watertight=is_watertight,
        is_winding_consistent=is_winding,
        non_manifold_edges=non_manifold,
        open_edges=open_edges,
        degenerate_faces=degen,
        volume_cm3=round(vol_cm3, 4),
        surface_area_cm2=round(area_cm2, 4),
        issues=issues,
    )
