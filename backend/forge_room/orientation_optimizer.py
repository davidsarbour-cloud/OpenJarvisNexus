"""
Optimiseur d'orientation FDM.
Teste 8 orientations candidates et choisit celle qui minimise les surplombs
tout en maximisant le contact avec la build plate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh

# 8 orientations candidates : 6 faces + 2 diagonales
_CANDIDATE_ROTATIONS = [
    np.eye(3),                                           # identité
    trimesh.transformations.rotation_matrix(np.pi/2,  [1,0,0])[:3,:3],  # +90° X
    trimesh.transformations.rotation_matrix(np.pi,    [1,0,0])[:3,:3],  # 180° X
    trimesh.transformations.rotation_matrix(-np.pi/2, [1,0,0])[:3,:3],  # -90° X
    trimesh.transformations.rotation_matrix(np.pi/2,  [0,1,0])[:3,:3],  # +90° Y
    trimesh.transformations.rotation_matrix(-np.pi/2, [0,1,0])[:3,:3],  # -90° Y
    trimesh.transformations.rotation_matrix(np.pi,    [0,1,0])[:3,:3],  # 180° Y
    trimesh.transformations.rotation_matrix(np.pi/2,  [0,0,1])[:3,:3],  # +90° Z
]

_CANDIDATE_LABELS = [
    "identité", "+90°X", "180°X", "-90°X", "+90°Y", "-90°Y", "180°Y", "+90°Z"
]


@dataclass
class OrientationResult:
    rotation_matrix: np.ndarray
    label: str
    score: float
    overhang_pct: float
    contact_pct: float
    all_scores: list[dict] = field(default_factory=list)


def _score_orientation(
    mesh: trimesh.Trimesh,
    rot: np.ndarray,
    overhang_deg: float = 45.0,
    overhang_w: float = 0.6,
    contact_w: float = 0.4,
) -> tuple[float, float, float]:
    """Retourne (score, overhang_pct, contact_pct) pour une rotation donnée."""
    m = mesh.copy()
    m.vertices = (rot @ m.vertices.T).T
    m.fix_normals()

    face_areas  = m.area_faces
    total_area  = max(face_areas.sum(), 1e-9)
    face_normals = m.face_normals

    # Surplombs
    sin_thresh = np.sin(np.radians(overhang_deg))
    overhang_mask = face_normals[:, 2] < -sin_thresh
    overhang_area = face_areas[overhang_mask].sum()
    overhang_pct  = float((overhang_area / total_area) * 100.0)

    # Contact build plate
    z_min = m.bounds[0][2]
    contact_mask = m.triangles_center[:, 2] <= z_min + 0.5
    contact_area = face_areas[contact_mask].sum()
    contact_pct  = float((contact_area / total_area) * 100.0)

    # Score : maximiser contact, minimiser surplombs
    # Pénalité forte si aucun contact avec la build plate (objet en l'air)
    no_contact_penalty = 50.0 if contact_pct < 0.5 else 0.0
    score = (contact_w * contact_pct) - (overhang_w * overhang_pct) - no_contact_penalty

    return score, overhang_pct, contact_pct


def optimize_orientation(
    mesh: trimesh.Trimesh,
    max_overhang_deg: float = 45.0,
) -> OrientationResult:
    """
    Teste les 8 orientations candidates et retourne la meilleure.
    """
    best_score   = -1e9
    best_idx     = 0
    all_scores: list[dict] = []

    for i, rot in enumerate(_CANDIDATE_ROTATIONS):
        score, oh_pct, ct_pct = _score_orientation(
            mesh, rot, overhang_deg=max_overhang_deg
        )
        all_scores.append({
            "label": _CANDIDATE_LABELS[i],
            "score": round(score, 3),
            "overhang_pct": round(oh_pct, 1),
            "contact_pct": round(ct_pct, 1),
        })
        if score > best_score:
            best_score = score
            best_idx   = i

    best_rot = _CANDIDATE_ROTATIONS[best_idx]
    _, oh_pct, ct_pct = _score_orientation(mesh, best_rot, max_overhang_deg)

    return OrientationResult(
        rotation_matrix=best_rot,
        label=_CANDIDATE_LABELS[best_idx],
        score=round(best_score, 3),
        overhang_pct=round(oh_pct, 1),
        contact_pct=round(ct_pct, 1),
        all_scores=all_scores,
    )


def apply_orientation(mesh: trimesh.Trimesh, result: OrientationResult) -> trimesh.Trimesh:
    """Applique la rotation optimale et pose le mesh sur la build plate."""
    m = mesh.copy()
    m.vertices = (result.rotation_matrix @ m.vertices.T).T
    m.fix_normals()
    z_min = m.bounds[0][2]
    m.apply_translation([0.0, 0.0, -z_min])
    return m
