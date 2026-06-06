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
    prefer_upright: bool = False,
) -> tuple[float, float, float]:
    """Retourne (score, overhang_pct, contact_pct) pour une rotation donnée."""
    m = mesh.copy()
    m.vertices = (rot @ m.vertices.T).T
    m.fix_normals()

    face_areas  = m.area_faces
    total_area  = max(face_areas.sum(), 1e-9)
    face_normals = m.face_normals

    # Contact build plate (calculé d'abord : sert aussi à exclure la base des surplombs)
    z_min = m.bounds[0][2]
    contact_mask = m.triangles_center[:, 2] <= z_min + 0.5
    contact_area = face_areas[contact_mask].sum()
    contact_pct  = float((contact_area / total_area) * 100.0)

    # Surplombs : faces tournées vers le bas, MAIS pas la base posée sur le plateau.
    # Une face de contact orientée vers le bas n'est PAS un surplomb — sinon un objet
    # plat (jeton, médaille, relief) est pénalisé pour SA PROPRE base et l'optimiseur
    # le dresse sur la tranche (le bug du jeton debout). Exclure la base est aussi
    # physiquement correct pour tout objet (FDM : base à plat = idéal).
    sin_thresh = np.sin(np.radians(overhang_deg))
    overhang_mask = (face_normals[:, 2] < -sin_thresh) & ~contact_mask
    overhang_area = face_areas[overhang_mask].sum()
    overhang_pct  = float((overhang_area / total_area) * 100.0)

    if prefer_upright:
        # Figurines / personnages (image-to-3D) : on PRIVILÉGIE la pose DEBOUT
        # (hauteur Z maximale) au lieu de coucher le modèle sur le dos juste pour
        # réduire les surplombs. Les supports gèrent les overhangs (assumé). Pas de
        # pénalité "pas de contact" : un perso debout sur de petites jambes a peu
        # de contact mais c'est la bonne pose d'affichage.
        ext = m.extents
        height_ratio = float(ext[2] / max(float(ext.max()), 1e-9))   # 1.0 = orientation la plus haute
        # Bonus à l'orientation NATIVE de Meshy (identité) : Meshy génère le modèle
        # dans la pose de l'image (debout). On la garde sauf si une autre est
        # nettement plus haute. (Vérifié sur le cowboy : identité = debout.)
        native_bonus = 15.0 if np.allclose(rot, np.eye(3), atol=1e-6) else 0.0
        score = (100.0 * height_ratio) + native_bonus + (0.3 * contact_pct) - (0.15 * overhang_pct)
    else:
        # Score : maximiser contact, minimiser surplombs.
        # Pénalité forte si aucun contact avec la build plate (objet en l'air).
        no_contact_penalty = 50.0 if contact_pct < 0.5 else 0.0
        score = (contact_w * contact_pct) - (overhang_w * overhang_pct) - no_contact_penalty

    return score, overhang_pct, contact_pct


def optimize_orientation(
    mesh: trimesh.Trimesh,
    max_overhang_deg: float = 45.0,
    prefer_upright: bool = False,
) -> OrientationResult:
    """
    Teste les 8 orientations candidates et retourne la meilleure.

    prefer_upright=True (figurines image-to-3D) : garde le modèle DEBOUT (pose la
    plus haute) au lieu de le coucher pour minimiser les surplombs.
    """
    best_score   = -1e9
    best_idx     = 0
    all_scores: list[dict] = []

    for i, rot in enumerate(_CANDIDATE_ROTATIONS):
        score, oh_pct, ct_pct = _score_orientation(
            mesh, rot, overhang_deg=max_overhang_deg, prefer_upright=prefer_upright
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
    _, oh_pct, ct_pct = _score_orientation(
        mesh, best_rot, max_overhang_deg, prefer_upright=prefer_upright)

    return OrientationResult(
        rotation_matrix=best_rot,
        label=_CANDIDATE_LABELS[best_idx],
        score=round(best_score, 3),
        overhang_pct=round(oh_pct, 1),
        contact_pct=round(ct_pct, 1),
        all_scores=all_scores,
    )


def lay_flat(mesh: trimesh.Trimesh, overhang_deg: float = 45.0) -> OrientationResult:
    """Pose un objet PLAT (jeton, médaille, relief, plaque) à plat sur le plateau.

    Le scoring surplomb/contact des 8 rotations cardinales échoue sur un relief : la
    face du dessous est bosselée, donc l'orientation à plat est faussement pénalisée
    comme « surplombante » et l'optimiseur dresse le jeton sur la tranche. Ici on
    aligne géométriquement (PCA) l'axe le plus mince du mesh sur Z — ça couche le
    disque quel que soit son angle d'arrivée — puis on choisit le côté (face avant /
    arrière vers le bas) qui maximise le contact plateau.
    """
    m = mesh.copy()
    v = m.vertices - m.vertices.mean(axis=0)
    cov = v.T @ v
    evals, evecs = np.linalg.eigh(cov)
    normal = evecs[:, int(np.argmin(evals))]                 # axe le plus mince = normale du disque
    R4 = trimesh.geometry.align_vectors(normal, [0.0, 0.0, 1.0])
    R = np.asarray(R4)[:3, :3]
    flip = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])[:3, :3] @ R

    def _contact(rot: np.ndarray) -> float:
        mm = mesh.copy()
        mm.vertices = (rot @ mm.vertices.T).T
        z0 = mm.bounds[0][2]
        cmask = mm.triangles_center[:, 2] <= z0 + 0.5
        return float(mm.area_faces[cmask].sum() / max(mm.area_faces.sum(), 1e-9))

    best = R if _contact(R) >= _contact(flip) else flip
    score, oh_pct, ct_pct = _score_orientation(mesh, best, overhang_deg=overhang_deg)
    return OrientationResult(
        rotation_matrix=best,
        label="à plat (PCA)",
        score=round(score, 3),
        overhang_pct=round(oh_pct, 1),
        contact_pct=round(ct_pct, 1),
        all_scores=[],
    )


def _contact_pct(mesh: trimesh.Trimesh) -> float:
    z = mesh.triangles_center[:, 2]
    a = mesh.area_faces
    return float(a[z <= mesh.bounds[0][2] + 0.6].sum() / max(a.sum(), 1e-9) * 100.0)


def stand_upright(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Redresse une figurine à la VERTICALE : aligne son axe le plus long (le corps)
    sur Z par PCA, quel que soit l'angle d'arrivée de Meshy (souvent couché/penché).
    Choisit le sens (pieds en bas = côté avec le plus de matière au sol). Les rotations
    cardinales ne suffisent pas quand le maillage est penché → d'où le 'mal orienté'."""
    m = mesh.copy()
    V = np.asarray(m.vertices, dtype=np.float64)
    Vc = V - V.mean(axis=0)
    evals, evecs = np.linalg.eigh(Vc.T @ Vc)
    longax = evecs[:, int(np.argmax(evals))]
    m.apply_transform(np.asarray(trimesh.geometry.align_vectors(longax, [0.0, 0.0, 1.0])))

    flip = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    a = m.copy()
    a.apply_translation([0, 0, -a.bounds[0][2]])
    b = m.copy()
    b.apply_transform(flip)
    b.apply_translation([0, 0, -b.bounds[0][2]])

    def _bottom_mass(x: trimesh.Trimesh) -> int:
        zt = x.bounds[0][2] + 0.15 * float(x.extents[2])
        return int((x.triangles_center[:, 2] < zt).sum())

    chosen = a if _bottom_mass(a) >= _bottom_mass(b) else b
    chosen.fix_normals()
    return chosen


def add_base_pad(mesh: trimesh.Trimesh, thickness: float = 3.0,
                 margin: float = 1.2) -> trimesh.Trimesh:
    """Ajoute un socle cylindrique plat sous une figurine pour qu'elle tienne debout
    (pieds fins/pointus → instable sinon). Le socle couvre l'empreinte du bas."""
    zt = mesh.bounds[0][2] + 0.08 * float(mesh.extents[2])
    bot = mesh.vertices[mesh.vertices[:, 2] < zt]
    if len(bot) < 3:
        bot = mesh.vertices
    cx, cy = float(bot[:, 0].mean()), float(bot[:, 1].mean())
    r = max(float(np.linalg.norm(bot[:, :2] - [cx, cy], axis=1).max()) * margin, 12.0)
    disc = trimesh.creation.cylinder(radius=r, height=thickness, sections=96)
    disc.apply_translation([cx, cy, thickness / 2.0])
    fig = mesh.copy()
    fig.apply_translation([0, 0, thickness - mesh.bounds[0][2]])
    return trimesh.util.concatenate([disc, fig])


def apply_orientation(mesh: trimesh.Trimesh, result: OrientationResult) -> trimesh.Trimesh:
    """Applique la rotation optimale et pose le mesh sur la build plate."""
    m = mesh.copy()
    m.vertices = (result.rotation_matrix @ m.vertices.T).T
    m.fix_normals()
    z_min = m.bounds[0][2]
    m.apply_translation([0.0, 0.0, -z_min])
    return m
