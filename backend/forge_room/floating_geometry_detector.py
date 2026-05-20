"""Détection de géométrie flottante — composantes déconnectées non ancrées à la build plate."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import trimesh


@dataclass
class FloatingResult:
    total_components: int
    floating_components: int
    main_body_volume_pct: float
    floating_volumes_cm3: list[float] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.floating_components == 0


def detect_floating(mesh: trimesh.Trimesh, z_threshold_mm: float = 0.5) -> FloatingResult:
    """
    Identifie les composantes connexes qui ne touchent pas la build plate (z ≈ 0).
    z_threshold_mm : distance max au-dessus du plan Z=0 pour considérer "ancré".
    """
    issues: list[str] = []

    # Décomposition en composantes connexes
    components = mesh.split(only_watertight=False)

    if not components:
        return FloatingResult(
            total_components=1,
            floating_components=0,
            main_body_volume_pct=100.0,
            issues=["Aucune composante trouvée"],
        )

    total = len(components)
    z_min_global = mesh.bounds[0][2]  # Z minimum global

    floating: list[trimesh.Trimesh] = []
    grounded: list[trimesh.Trimesh] = []

    for comp in components:
        comp_z_min = comp.bounds[0][2]
        # Ancré si le bas de la composante est proche du plan Z global minimum
        if (comp_z_min - z_min_global) <= z_threshold_mm:
            grounded.append(comp)
        else:
            floating.append(comp)

    floating_vols = []
    for f in floating:
        vol = abs(float(f.volume)) / 1000.0 if f.is_watertight else 0.0
        floating_vols.append(round(vol, 4))

    total_vol = abs(float(mesh.volume)) / 1000.0 if mesh.is_watertight else 1.0
    grounded_vol = sum(
        abs(float(g.volume)) / 1000.0 for g in grounded if g.is_watertight
    )
    main_pct = round(min(100.0, (grounded_vol / max(total_vol, 1e-9)) * 100.0), 1)

    if floating:
        issues.append(
            f"{len(floating)} composante(s) flottante(s) détectée(s) — "
            f"volumes: {floating_vols} cm³"
        )

    return FloatingResult(
        total_components=total,
        floating_components=len(floating),
        main_body_volume_pct=main_pct,
        floating_volumes_cm3=floating_vols,
        issues=issues,
    )
