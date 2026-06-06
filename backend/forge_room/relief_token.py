"""Image → jeton relief 2 couleurs (AMS), SANS Meshy.

Pour un jeton/médaille/badge plat à partir d'une image 2D, on n'a pas besoin de
l'image-to-3D de Meshy (bruité + couleurs perdues). On construit le jeton
directement depuis l'image :

  • corps  = cylindre lisse (couleur de fond, ex. noir)
  • design = les zones « accent » de l'image (ex. robot orange) vectorisées par
             contours puis extrudées en relief — bords NETS, fidèles au dessin.

Les 2 parts (corps / design) deviennent les 2 slots AMS. Résultat : jetons
2-couleurs de qualité pro, exacts à l'image, sans bruit ni couleurs reconstruites.
Voir [[reference-bambu-3mf-format]] pour l'écriture du .3mf (write_bambu_color_3mf).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import trimesh

from forge_room.color_3mf import (
    _image_dominant_palette,
    render_thumbnail_png,
    write_bambu_color_3mf,
)

# Intentions « objet plat 2D depuis image » → on prend la voie relief (pas Meshy).
_TOKEN_KW = re.compile(
    r"\bjeton(s)?\b|\btoken(s)?\b|\bcoin(s)?\b|\bm[ée]daille(s)?\b|\bmedal(s)?\b|"
    r"\bbadge(s)?\b|\bpog(s)?\b|\bpi[èe]ce(s)?\b|\bplaque(tte)?(s)?\b|\brelief\b|"
    r"\bcoaster(s)?\b|\bsous[-\s]?verre(s)?\b|\bmagnet(s)?\b|\bemboss",
    re.I,
)


def is_token_request(prompt: str) -> bool:
    """True si la demande est un objet plat 2D-depuis-image (jeton, médaille, badge…)."""
    return bool(_TOKEN_KW.search(prompt or ""))


def _hex_to_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=np.float64)


def build_relief_token(
    image_path: "Path | str",
    diameter_mm: float = 50.0,
    base_mm: float = 2.0,
    relief_mm: float = 0.8,
    work_px: int = 320,
    simplify_mm: float = 0.8,
) -> tuple[trimesh.Trimesh, np.ndarray, list[str]]:
    """Construit le jeton relief. Retourne (mesh, face_idx, palette[corps, accent]).
    face_idx : 0 = corps (cylindre), 1 = design (relief extrudé)."""
    import os

    from PIL import Image
    from scipy import ndimage
    from shapely import affinity, ops
    from shapely.geometry import Point, Polygon
    from skimage import measure

    src = str(image_path)
    palette = _image_dominant_palette(src, 2) or ["#1A1A1A", "#F66B09"]
    body_rgb, accent_rgb = _hex_to_rgb(palette[0]), _hex_to_rgb(palette[1])

    img = Image.open(src).convert("RGB")
    img = img.resize((work_px, max(1, int(work_px * img.height / img.width))))
    a = np.asarray(img).astype(np.float64)
    H, W = a.shape[:2]

    # Masque « design » = pixels plus proches de l'accent que du corps.
    da = np.linalg.norm(a - accent_rgb, axis=2)
    db = np.linalg.norm(a - body_rgb, axis=2)
    mask = da < db
    # Nettoyage morpho : enlève le bruit isolé, referme les petits trous.
    mask = ndimage.binary_opening(mask, iterations=1)
    mask = ndimage.binary_closing(mask, iterations=2)

    # Design CENTRAL seulement : on garde le motif au centre (le robot/logo) et on
    # jette la bordure ornée du bord (perlée/dorée) qui ne donne qu'un anneau bruité.
    # Un anneau LISSE programmatique est ajouté ensuite. center_frac = rayon gardé.
    cx, cy = W / 2.0, H / 2.0
    R = min(cx, cy) * 0.97
    center_frac = float(os.getenv("FORGE_TOKEN_CENTER_FRAC", "0.62"))
    yy, xx = np.mgrid[0:H, 0:W]
    rad = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    mask = mask & (rad < center_frac * R)

    # Vectorisation : contours marching-squares → polygones, XOR (even-odd) pour les
    # trous internes (ex. les yeux noirs du robot deviennent des trous dans le relief).
    contours = measure.find_contours(mask.astype(np.float64), 0.5)
    polys = []
    for c in contours:
        if len(c) < 4:
            continue
        p = Polygon(c[:, ::-1]).buffer(0)   # (col,row) → (x,y)
        if p.is_valid and p.area > 8:
            polys.append(p)
    if not polys:
        raise ValueError("Aucune zone de design détectée dans l'image")
    polys.sort(key=lambda p: p.area, reverse=True)
    motif = polys[0]
    for p in polys[1:]:
        motif = motif.symmetric_difference(p)

    # px → mm, centré à l'origine, Y vers le haut.
    mm = diameter_mm / (2.0 * R)
    motif = affinity.translate(motif, -cx, -cy)
    motif = affinity.scale(motif, mm, -mm, origin=(0, 0))
    # Lissage : closing arrondi (buffer +/-) → enlève dents de scie, puis simplify.
    sm = float(os.getenv("FORGE_TOKEN_SMOOTH_MM", "0.5"))
    motif = motif.buffer(sm, join_style=1).buffer(-sm, join_style=1).simplify(simplify_mm / 2)

    parts = [motif]
    # Anneau de bordure LISSE (cercles parfaits), à la place de la bordure ornée.
    if os.getenv("FORGE_TOKEN_RING", "1") == "1":
        Rmm = diameter_mm / 2.0
        ri = float(os.getenv("FORGE_TOKEN_RING_INNER", "0.80")) * Rmm
        ro = float(os.getenv("FORGE_TOKEN_RING_OUTER", "0.92")) * Rmm
        ring = (Point(0, 0).buffer(ro, quad_segs=96)
                .difference(Point(0, 0).buffer(ri, quad_segs=96)))
        parts.append(ring)
    design = ops.unary_union(parts)

    # Corps : cylindre lisse (bord rond net).
    base = trimesh.creation.cylinder(radius=diameter_mm / 2.0, height=base_mm, sections=160)
    base.apply_translation([0, 0, base_mm / 2.0])

    # Design : extrusion des polygones, posée sur le corps (légèrement enfoncée pour
    # garantir la liaison solide).
    geoms = list(design.geoms) if design.geom_type == "MultiPolygon" else [design]
    reliefs = []
    for g in geoms:
        if g.area < 1.0:
            continue
        try:
            r = trimesh.creation.extrude_polygon(g, relief_mm)
            r.apply_translation([0, 0, base_mm - 0.1])
            reliefs.append(r)
        except Exception:
            continue
    if not reliefs:
        raise ValueError("Extrusion du design impossible")
    relief = trimesh.util.concatenate(reliefs)

    mesh = trimesh.util.concatenate([base, relief])
    face_idx = np.concatenate([
        np.zeros(len(base.faces), dtype=int),
        np.ones(len(relief.faces), dtype=int),
    ])
    return mesh, face_idx, palette


def generate_relief_token_3mf(
    image_path: "Path | str",
    out_path: "Path | str",
    name: str = "jeton",
    diameter_mm: float = 50.0,
    base_mm: float = 2.0,
    relief_mm: float = 0.8,
) -> tuple[Path | None, list[str]]:
    """Image → .3mf jeton relief 2 couleurs AMS (X1C 0.4, miniature embarquée).
    Retourne (chemin|None, palette). None si la génération échoue."""
    try:
        mesh, face_idx, palette = build_relief_token(
            image_path, diameter_mm=diameter_mm, base_mm=base_mm, relief_mm=relief_mm)
    except Exception:
        return None, []

    pal_rgb = np.array([_hex_to_rgb(h) for h in palette])
    face_cols = pal_rgb[np.clip(face_idx, 0, len(pal_rgb) - 1)]
    thumb = render_thumbnail_png(mesh, face_colors=face_cols)
    path = write_bambu_color_3mf(
        mesh, face_idx, palette, Path(out_path), name=name, thumbnail_bytes=thumb)
    return path, palette
