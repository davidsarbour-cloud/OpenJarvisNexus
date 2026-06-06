"""Colorisation image→3MF AMS-ready pour The Forge Room.

Transforme un mesh texturé (Meshy image-to-3D avec ``should_texture=True``) en un
fichier **.3mf Bambu** prêt à slicer : la texture est cuite en couleurs par face,
quantifiée en N teintes dominantes (défaut 2, comme les ClaudeTokens de David), le
mesh est découpé en N sous-parts — une par couleur — et chaque part est assignée à
un slot AMS via ``extruder`` dans ``model_settings.config``. La palette est écrite
dans ``filament_colour`` du profil Bambu (template = profil réel A1 0.4 nozzle).

C'est exactement le mécanisme des ClaudeTokens.3mf : per-part ``extruder`` + palette
``filament_colour``. Aucun encodage propriétaire ``paint_color`` (plus fragile).

Pipeline offline-testable : extract → quantize → split → write. La validation finale
(Bambu lit bien les couleurs/AMS) se fait à l'ouverture du .3mf dans Bambu Studio.
"""
from __future__ import annotations

import io
import json
import uuid
import zipfile
from pathlib import Path

import numpy as np
import trimesh

_TEMPLATE = Path(__file__).parent / "templates" / "bambu_project_settings.config"

# Plateau Bambu Lab A1 = 256 x 256 mm ; on centre le modèle dessus.
_BED_MM = 256.0


def extract_face_colors(mesh: trimesh.Trimesh) -> np.ndarray | None:
    """Retourne un tableau uint8[F,3] de couleur par face, ou None si le mesh n'a
    pas de couleur exploitable (gris uniforme = pas de texture)."""
    vis = getattr(mesh, "visual", None)
    if vis is None:
        return None

    # TextureVisuals (UV + image) → cuire en couleurs par sommet
    try:
        if hasattr(vis, "to_color"):
            vis = vis.to_color()
    except Exception:
        pass

    face_cols: np.ndarray | None = None
    vcol = getattr(vis, "vertex_colors", None)
    if vcol is not None and len(vcol) == len(mesh.vertices):
        vcol = np.asarray(vcol)[:, :3].astype(np.float64)
        face_cols = vcol[mesh.faces].mean(axis=1)
    else:
        fcol = getattr(vis, "face_colors", None)
        if fcol is not None and len(fcol) == len(mesh.faces):
            face_cols = np.asarray(fcol)[:, :3].astype(np.float64)

    if face_cols is None:
        return None

    # Pas de vraie couleur si tout est quasi-identique (gris Meshy par défaut).
    if float(face_cols.std(axis=0).mean()) < 6.0:
        return None

    return np.clip(face_cols, 0, 255).astype(np.uint8)


def transfer_colors(target: trimesh.Trimesh, source_colored: trimesh.Trimesh) -> bool:
    """Re-projette les couleurs par sommet de ``source_colored`` (mesh Meshy texturé)
    sur ``target`` (mesh réparé, topologie différente, MÊME repère) par plus-proche
    voisin. Mute ``target.visual.vertex_colors``. True si la couleur a été posée.

    La réparation (pymeshfix/décimation) recrée la topologie et perd les couleurs ;
    ce transfert les restaure tant que les deux meshs partagent le même repère (cas
    Meshy : le STL et le GLB sortent dans les mêmes coordonnées)."""
    src = source_colored
    try:
        vis = src.visual
        if hasattr(vis, "to_color"):
            vis = vis.to_color()
        src_cols = np.asarray(getattr(vis, "vertex_colors", None))
    except Exception:
        return False
    if src_cols is None or len(src_cols) != len(src.vertices):
        return False
    if float(src_cols[:, :3].astype(np.float64).std(axis=0).mean()) < 6.0:
        return False  # source gris uniforme — rien à transférer

    # Garde-fou repère : src (GLB) et target (mesh réparé) décrivent le MÊME objet
    # AVANT orientation/scale → leurs boîtes englobantes doivent coïncider. Si une
    # étape de réparation a recadré le mesh (voxel remesh, décimation normalisée), le
    # transfert plus-proche-voisin serait faux : on saute (→ STL mono) plutôt que de
    # mal colorier. Tolérance large : ne déclenche que sur un vrai décalage de repère.
    try:
        src_c = np.asarray(src.bounds).mean(axis=0)
        tgt_c = np.asarray(target.bounds).mean(axis=0)
        scale = float(max(np.asarray(target.extents).max(), 1e-6))
        if float(np.linalg.norm(src_c - tgt_c)) > 0.5 * scale:
            return False
    except Exception:
        return False

    try:
        # trimesh expose un KDTree scipy sur les sommets.
        _dist, nn = src.kdtree.query(target.vertices)
    except Exception:
        return False

    target.visual.vertex_colors = src_cols[nn]
    return True


def quantize_faces(face_colors: np.ndarray, n_colors: int = 2) -> tuple[list[str], np.ndarray]:
    """Quantifie les couleurs de face en ``n_colors`` teintes dominantes (médian-cut
    PIL). Retourne (palette_hex, face_idx) où face_idx[f] ∈ [0, len(palette)-1]."""
    from PIL import Image

    n = max(2, int(n_colors))
    F = len(face_colors)
    img = Image.fromarray(face_colors.reshape(F, 1, 3), "RGB")
    q = img.quantize(colors=n, method=Image.MEDIANCUT)
    idx = np.asarray(q).reshape(F).astype(int)
    pal = q.getpalette() or []

    # Compacter les indices réellement utilisés (médian-cut peut en sauter).
    used = sorted(set(idx.tolist()))
    remap = {old: i for i, old in enumerate(used)}
    face_idx = np.array([remap[i] for i in idx], dtype=int)

    palette_hex: list[str] = []
    for old in used:
        r, g, b = pal[old * 3: old * 3 + 3]
        palette_hex.append(f"#{r:02X}{g:02X}{b:02X}")
    return palette_hex, face_idx


def _mesh_xml(mesh: trimesh.Trimesh) -> str:
    V = mesh.vertices
    F = mesh.faces
    verts = "".join(f'<vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in V)
    tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in F)
    return f"<mesh><vertices>{verts}</vertices><triangles>{tris}</triangles></mesh>"


def _uuid() -> str:
    return str(uuid.uuid4())


def _build_project_settings(palette_hex: list[str]) -> str:
    """Charge le profil Bambu template (X1C 0.4, AMS) et l'aligne sur n filaments.

    Le template est un profil 2 filaments : pour n≠2 il FAUT redimensionner TOUS les
    tableaux par-filament (longueur == nb filaments d'origine) ET les matrices de purge
    (flush_volumes_matrix n×n, flush_volumes_vector 2n) — sinon Bambu refuse avec
    « invalid configuration » (tableaux de tailles incohérentes)."""
    n = len(palette_hex)
    try:
        prof = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    except Exception:
        prof = {}

    orig = len(prof.get("filament_colour", [])) or 2

    if orig != n:
        # Tout tableau par-filament (longueur == orig) → longueur n (répète le dernier).
        # Les coordonnées plateau (printable_area, bed_exclude_area… longueur 4) ne sont
        # PAS de longueur orig → épargnées.
        for k, v in list(prof.items()):
            if isinstance(v, list) and len(v) == orig:
                prof[k] = [v[i] if i < len(v) else v[-1] for i in range(n)]
        # Matrices de purge AMS recalculées pour n filaments.
        prof["flush_volumes_matrix"] = [
            ("0" if i == j else "280") for i in range(n) for j in range(n)
        ]
        prof["flush_volumes_vector"] = ["140"] * (2 * n)

    prof["filament_colour"] = list(palette_hex)
    return json.dumps(prof, ensure_ascii=False, indent=4)


def write_bambu_color_3mf(
    mesh: trimesh.Trimesh,
    face_idx: np.ndarray,
    palette_hex: list[str],
    out_path: Path,
    name: str = "forge_model",
    thumbnail_bytes: "bytes | None" = None,
) -> Path:
    """Écrit un .3mf Bambu : 1 objet d'assemblage + N sous-parts (1 par couleur),
    chaque part assignée à un slot AMS via ``extruder``. Profil = A1 0.4 nozzle."""
    out_path = Path(out_path)
    n_colors = len(palette_hex)

    # Centrer le modèle sur le plateau A1 (X/Y) et le poser sur Z=0.
    m = mesh.copy()
    mins = m.bounds[0]
    ext = m.extents
    m.apply_translation([
        _BED_MM / 2.0 - (mins[0] + ext[0] / 2.0),
        _BED_MM / 2.0 - (mins[1] + ext[1] / 2.0),
        -mins[2],
    ])

    # Découpe en sous-parts par couleur. Réindexation manuelle des sommets : garantit
    # des indices de face compacts et 0-based, indépendamment de la version de trimesh
    # (pas de dépendance au comportement de submesh()).
    faces = np.asarray(m.faces)
    verts = np.asarray(m.vertices)
    parts: list[tuple[int, trimesh.Trimesh]] = []
    for k in range(n_colors):
        mask = np.where(face_idx == k)[0]
        if len(mask) == 0:
            continue
        fsub = faces[mask]
        uniq, inv = np.unique(fsub, return_inverse=True)
        sub = trimesh.Trimesh(
            vertices=verts[uniq], faces=inv.reshape(-1, 3), process=False
        )
        parts.append((k, sub))

    if not parts:
        raise ValueError("Aucune part colorée à écrire")

    # ── 3D/3dmodel.model : objets-parts + assemblage à composants ──
    # En-tête calqué EXACTEMENT sur un vrai projet BambuStudio (ClaudeTokens) : sans
    # le namespace BambuStudio + les metadata Application/3mfVersion, Bambu traite le
    # fichier comme un maillage ÉTRANGER (profil défaut X1C 0.2, 1 filament, aucune
    # couleur) au lieu de charger le profil A1 0.4 + la palette AMS embarqués.
    part_objs = []
    components = []
    for i, (_k, sub) in enumerate(parts):
        oid = i + 2  # 1 = assemblage
        part_objs.append(
            f'<object id="{oid}" p:UUID="{_uuid()}" type="model">{_mesh_xml(sub)}</object>'
        )
        components.append(
            f'<component objectid="{oid}" p:UUID="{_uuid()}" '
            f'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
        )
    assembly = (
        f'<object id="1" p:UUID="{_uuid()}" type="model">'
        f'<components>{"".join(components)}</components></object>'
    )
    model = (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'requiredextensions="p" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">'
        '<metadata name="Application">BambuStudio-02.06.00.51</metadata>'
        '<metadata name="BambuStudio:3mfVersion">1</metadata>'
        "<resources>"
        f"{''.join(part_objs)}{assembly}"
        "</resources>"
        f'<build><item objectid="1" p:UUID="{_uuid()}" '
        'transform="1 0 0 0 1 0 0 0 1 0 0 0" printable="1"/></build>'
        "</model>"
    )

    # ── Metadata/model_settings.config : assemblage + parts + extruder AMS ──
    parts_xml = []
    for i, (_k, sub) in enumerate(parts):
        pid = i + 1
        parts_xml.append(
            f'<part id="{pid}" subtype="normal_part">'
            f'<metadata key="name" value="{name}_c{pid}"/>'
            f'<metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>'
            f'<metadata key="extruder" value="{pid}"/>'
            f'<mesh_stat face_count="{len(sub.faces)}"/>'
            "</part>"
        )
    model_settings = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
        '  <object id="1">\n'
        f'    <metadata key="name" value="{name}"/>\n'
        '    <metadata key="extruder" value="1"/>\n'
        f'    {"".join(parts_xml)}\n'
        "  </object>\n</config>\n"
    )

    # Bambu mappe les parts aux filaments dans l'ordre INVERSE de leur déclaration
    # (vérifié : icône et modèle sortaient en couleurs permutées). On écrit donc la
    # palette filament inversée pour que part0→corps et part1→accent tombent juste.
    # Toggle FORGE_SWAP_COLORS=0 si une version de Bambu ne permute pas.
    import os as _os
    _fil_palette = list(reversed(palette_hex)) if _os.getenv("FORGE_SWAP_COLORS", "1") == "1" else list(palette_hex)
    project_settings = _build_project_settings(_fil_palette)

    # Miniature : PNG embarqué (rendu du modèle) pour que le .3mf affiche un aperçu
    # dans Bambu ET dans l'explorateur Windows, au lieu de l'icône verte générique.
    thumb_bytes = thumbnail_bytes

    # Content_Types : 'rels' + 'model' (configs lues par chemin fixe) + 'png' pour la
    # miniature (présent aussi dans les vrais projets Bambu). Pas de Default 'config'.
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        "</Types>"
    )
    _thumb_rel = (
        '<Relationship Target="/Auxiliaries/.thumbnails/thumbnail_3mf.png" Id="rel-thumb" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>'
        if thumb_bytes else ''
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        f'{_thumb_rel}'
        "</Relationships>"
    )

    # slice_info.config : marqueur projet BambuStudio (présent dans les vrais fichiers).
    slice_info = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
        '  <header>\n'
        '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
        '    <header_item key="X-BBL-Client-Version" value="02.06.00.51"/>\n'
        '  </header>\n</config>\n'
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", model_settings)
        z.writestr("Metadata/project_settings.config", project_settings)
        z.writestr("Metadata/slice_info.config", slice_info)
        if thumb_bytes:
            z.writestr("Auxiliaries/.thumbnails/thumbnail_3mf.png", thumb_bytes)
            z.writestr("Metadata/plate_1.png", thumb_bytes)
    return out_path


def _image_dominant_palette(image_path: "Path | str", n: int = 2) -> list[str] | None:
    """Couleurs dominantes de l'OBJET dans l'image (les VRAIES couleurs voulues).
    Exclut le fond (échantillonné sur le bord de l'image) — sinon le blanc autour du
    jeton est pris pour le corps. Retourne [corps, accent] : corps = couleur la plus
    présente, accent = la plus saturée. Ex. robot orange sur fond noir → [noir, orange]."""
    try:
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((160, 160))
        a = np.asarray(img).astype(np.float64)
        # Fond = médiane des pixels du bord (les 4 arêtes de l'image).
        border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]).reshape(-1, 3)
        bg = np.median(border, axis=0)

        q = img.quantize(colors=8, method=Image.MEDIANCUT).convert("RGB")
        arr = np.asarray(q).reshape(-1, 3).astype(np.float64)
        uniq, cnt = np.unique(arr, axis=0, return_counts=True)

        # Écarter les teintes proches du fond (le jeton n'inclut pas son fond d'image).
        keep = np.linalg.norm(uniq - bg, axis=1) > 70
        if int(keep.sum()) >= 2:
            uniq, cnt = uniq[keep], cnt[keep]

        mx = uniq.max(axis=1)
        mn = uniq.min(axis=1)
        sat = (mx - mn) / np.maximum(mx, 1.0)
        share = cnt / cnt.sum()
        accent_i = int(np.argmax(sat * np.sqrt(share)))     # accent = saturé & présent
        accent = uniq[accent_i]
        dist = np.linalg.norm(uniq - accent, axis=1)         # corps = présent & distinct
        cand = np.where(dist > 60)[0]
        body_i = int(cand[np.argmax(cnt[cand])]) if len(cand) else int(np.argmax(cnt))
        body = uniq[body_i]

        def _hx(c):
            return "#%02X%02X%02X" % (int(c[0]), int(c[1]), int(c[2]))
        pal = [_hx(body), _hx(accent)]
        while len(pal) < n:
            pal.append(_hx(accent))
        return pal[:max(2, n)]
    except Exception:
        return None


def _smooth_face_labels(mesh: trimesh.Trimesh, idx: np.ndarray, iters: int = 3) -> np.ndarray:
    """Filtre majoritaire sur les faces voisines : nettoie les frontières en dents de
    scie et les faces isolées → lignes orange/noir continues et nettes (plus esthétique
    à l'impression). Sans ça, chaque triangle bascule seul selon sa hauteur → bords bruités."""
    try:
        adj = np.asarray(mesh.face_adjacency)
    except Exception:
        return idx
    if adj is None or len(adj) == 0:
        return idx
    a, b = adj[:, 0], adj[:, 1]
    idx = idx.copy().astype(int)
    for _ in range(max(0, int(iters))):
        v1 = np.zeros(len(idx))
        v0 = np.zeros(len(idx))
        np.add.at(v1, a, idx[b])
        np.add.at(v0, a, 1 - idx[b])
        np.add.at(v1, b, idx[a])
        np.add.at(v0, b, 1 - idx[a])
        tot = v0 + v1
        idx = np.where(tot > 0, (v1 > v0).astype(int), idx)
    return idx


def assign_by_relief(mesh: trimesh.Trimesh, frac: float | None = None) -> np.ndarray:
    """Découpe 2 zones par hauteur : fond/base (Z bas → 0) vs design embossé surélevé
    (Z haut → 1). Le design prend la couleur accent, le corps la base. frac=0.82 isole
    juste le relief du dessus (~haut 18%) — réglable via FORGE_RELIEF_FRAC. Les
    frontières sont ensuite lissées (FORGE_COLOR_SMOOTH itérations) pour des lignes nettes."""
    import os
    if frac is None:
        try:
            frac = float(os.getenv("FORGE_RELIEF_FRAC", "0.82"))
        except ValueError:
            frac = 0.82
    z = np.asarray(mesh.triangles_center[:, 2], dtype=np.float64)
    zmin = float(z.min())
    zr = float(np.ptp(z)) or 1e-9
    idx = (z > zmin + frac * zr).astype(int)
    try:
        iters = int(os.getenv("FORGE_COLOR_SMOOTH", "3"))
    except ValueError:
        iters = 3
    return _smooth_face_labels(mesh, idx, iters)


def render_thumbnail_png(
    mesh: trimesh.Trimesh,
    size: int = 256,
    bg: tuple[int, int, int] = (245, 245, 245),
    face_colors: "np.ndarray | None" = None,
) -> bytes | None:
    """Rendu top-down (orthographique) du modèle coloré → PNG (bytes), sans GPU/GL.
    Painter's algorithm + ombrage lambert : l'icône montre le jeton coloré tel
    qu'imprimé (vue de dessus, le relief ressort). None si échec (autre miniature).
    face_colors : couleurs par face explicites (sinon extraites de la texture)."""
    try:
        from PIL import Image, ImageDraw

        V = np.asarray(mesh.vertices, dtype=np.float64)
        F = np.asarray(mesh.faces)
        if len(F) == 0:
            return None

        fc = face_colors if face_colors is not None else extract_face_colors(mesh)
        fc = np.full((len(F), 3), 170, dtype=np.float64) if fc is None else np.asarray(fc, dtype=np.float64)

        # Vue de dessus : X→droite, Y→haut ; Z = profondeur (relief vers +Z = caméra).
        mn = V[:, :2].min(axis=0)
        span = float(np.ptp(V[:, :2], axis=0).max()) or 1.0
        margin = size * 0.08
        scale = (size - 2 * margin) / span
        px = (V[:, 0] - mn[0]) * scale + margin
        py = (size - margin) - (V[:, 1] - mn[1]) * scale       # flip Y (repère image)
        P = np.column_stack([px, py])

        order = np.argsort(V[F][:, :, 2].mean(axis=1))          # painter : bas d'abord
        light = np.array([0.35, 0.35, 0.87])
        light /= np.linalg.norm(light)
        shade = np.clip(np.asarray(mesh.face_normals) @ light, 0.30, 1.0)

        img = Image.new("RGB", (size, size), bg)
        draw = ImageDraw.Draw(img)
        for i in order:
            a, b, c = F[i]
            col = tuple(int(v) for v in np.clip(fc[i] * shade[i], 0, 255))
            draw.polygon([tuple(P[a]), tuple(P[b]), tuple(P[c])], fill=col)

        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
    except Exception:
        return None


def _image_to_png_bytes(thumbnail_path: "Path | str | None") -> bytes | None:
    if not thumbnail_path:
        return None
    try:
        tp = Path(thumbnail_path)
        if not tp.exists():
            return None
        data = tp.read_bytes()
        if tp.suffix.lower() != ".png":
            from PIL import Image
            buf = io.BytesIO()
            Image.open(io.BytesIO(data)).convert("RGBA").save(buf, "PNG")
            data = buf.getvalue()
        return data
    except Exception:
        return None


# Codes paint_color Bambu mmu (décodés sur OpenClaw3D.3mf = 3 filaments → 4/8/0C) :
# filament 2 = "4", filament 3 = "8", filament 4 = "0C". (Pas de paint = filament 1.)
PAINT_CODE = {2: "4", 3: "8", 4: "0C"}


def _mesh_xml_painted(mesh: trimesh.Trimesh, paint_codes: list) -> str:
    """Mesh XML avec paint_color par triangle (code Bambu mmu) ; chaîne vide = pas de
    peinture (= filament 1). Garde UN seul objet étanche → ne flotte pas."""
    V = np.asarray(mesh.vertices)
    F = np.asarray(mesh.faces)
    verts = "".join(f'<vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in V)
    tris = []
    for i in range(len(F)):
        a, b, c = F[i]
        code = paint_codes[i]
        if code:
            tris.append(f'<triangle v1="{a}" v2="{b}" v3="{c}" paint_color="{code}"/>')
        else:
            tris.append(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>')
    return f"<mesh><vertices>{verts}</vertices><triangles>{''.join(tris)}</triangles></mesh>"


def write_bambu_paint_3mf(
    mesh: trimesh.Trimesh,
    paint_codes: list,
    palette_hex: list[str],
    out_path: Path,
    name: str = "forge_model",
    thumbnail_bytes: "bytes | None" = None,
) -> Path:
    """Écrit un .3mf Bambu où des triangles sont peints (paint_color) sur UN SEUL objet
    étanche — pour colorer des détails (yeux) sans découper le solide (donc sans le
    faire flotter). filament_colour = palette ; paint_color "4"/"8" = filament 2/3."""
    out_path = Path(out_path)
    m = mesh.copy()
    mins = m.bounds[0]
    ext = m.extents
    m.apply_translation([
        _BED_MM / 2.0 - (mins[0] + ext[0] / 2.0),
        _BED_MM / 2.0 - (mins[1] + ext[1] / 2.0),
        -mins[2],
    ])

    mesh_xml = _mesh_xml_painted(m, paint_codes)
    model = (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'requiredextensions="p" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">'
        '<metadata name="Application">BambuStudio-02.06.00.51</metadata>'
        '<metadata name="BambuStudio:3mfVersion">1</metadata>'
        f'<resources><object id="1" p:UUID="{_uuid()}" type="model">{mesh_xml}</object></resources>'
        f'<build><item objectid="1" p:UUID="{_uuid()}" '
        'transform="1 0 0 0 1 0 0 0 1 0 0 0" printable="1"/></build>'
        "</model>"
    )
    model_settings = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
        '  <object id="1">\n'
        f'    <metadata key="name" value="{name}"/>\n'
        '    <metadata key="extruder" value="1"/>\n'
        f'    <metadata face_count="{len(m.faces)}"/>\n'
        "  </object>\n</config>\n"
    )
    project_settings = _build_project_settings(palette_hex)   # direct (pas d'inversion)

    thumb_bytes = thumbnail_bytes
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        "</Types>"
    )
    _thumb_rel = (
        '<Relationship Target="/Auxiliaries/.thumbnails/thumbnail_3mf.png" Id="rel-thumb" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>'
        if thumb_bytes else ''
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        f'{_thumb_rel}'
        "</Relationships>"
    )
    slice_info = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
        '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
        '    <header_item key="X-BBL-Client-Version" value="02.06.00.51"/>\n'
        '  </header>\n</config>\n'
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", model_settings)
        z.writestr("Metadata/project_settings.config", project_settings)
        z.writestr("Metadata/slice_info.config", slice_info)
        if thumb_bytes:
            z.writestr("Auxiliaries/.thumbnails/thumbnail_3mf.png", thumb_bytes)
            z.writestr("Metadata/plate_1.png", thumb_bytes)
    return out_path


def enlarge_feet(mesh: trimesh.Trimesh, bottom_frac: float | None = None,
                 factor: float | None = None) -> trimesh.Trimesh:
    """Élargit le bas (pieds) en XY pour qu'une figurine tienne debout. Scale gradué :
    plein au sol, nul à bottom_frac de la hauteur. Préserve la topologie (donc les
    couleurs par sommet). Réglable via FORGE_FEET_FRAC / FORGE_FEET_FACTOR."""
    import os
    if bottom_frac is None:
        bottom_frac = float(os.getenv("FORGE_FEET_FRAC", "0.12"))
    if factor is None:
        factor = float(os.getenv("FORGE_FEET_FACTOR", "0.6"))
    m = mesh.copy()
    V = np.asarray(m.vertices, dtype=np.float64).copy()
    zmin = float(V[:, 2].min())
    h = float(np.ptp(V[:, 2])) or 1.0
    cx, cy = float(V[:, 0].mean()), float(V[:, 1].mean())
    t = np.clip((zmin + bottom_frac * h - V[:, 2]) / (bottom_frac * h), 0.0, 1.0)
    fac = 1.0 + factor * t
    V[:, 0] = cx + (V[:, 0] - cx) * fac
    V[:, 1] = cy + (V[:, 1] - cy) * fac
    m.vertices = V
    m.apply_translation([0, 0, -m.bounds[0][2]])   # repose à plat sur le plateau
    return m


def paint_figurine_3mf(
    colored_mesh: trimesh.Trimesh,
    out_path: Path,
    name: str = "figurine",
    thumbnail_path: "Path | str | None" = None,
    ring_hex: str = "#1A1A1A",
    center_hex: str = "#F0F0F0",
    widen_feet: bool = True,
) -> tuple[Path | None, list[str]]:
    """Figurine : élargit les pieds (tient debout) + peint les yeux en 2 tons par
    paint_color sur UN SEUL objet étanche (ne flotte pas) : contour sombre (filament 2)
    + centre clair (filament 3), comme un vrai œil. Retourne (chemin|None, palette
    [corps, contour, centre]). None si aucune zone distincte (→ mono géré ailleurs)."""
    mesh = enlarge_feet(colored_mesh) if widen_feet else colored_mesh
    fc = extract_face_colors(mesh)
    if fc is None:
        return None, []
    fc = fc.astype(int)
    # Yeux = teintes bleutées (B > R) — isole le cyan sans toucher le rouge/les ombres.
    eye = fc[:, 2] > (fc[:, 0] + 10)
    if int(eye.sum()) < max(20, int(0.002 * len(fc))):
        return None, []

    # Œil cartoon : contour sombre + point blanc au CENTRE de chaque œil (géométrique,
    # car la texture Meshy rend les yeux uniformément sombres — pas de vrai centre clair).
    eye_idx = np.where(eye)[0]
    ec = mesh.triangles_center[eye]
    center = np.zeros(len(fc), dtype=bool)
    if len(ec):
        xmed = float(np.median(ec[:, 0]))          # sépare œil gauche / droit
        for g in (ec[:, 0] < xmed, ec[:, 0] >= xmed):
            if not g.any():
                continue
            pts = ec[g]
            c = pts.mean(axis=0)
            r = np.linalg.norm(pts[:, [0, 2]] - c[[0, 2]], axis=1)
            inner = r < 0.42 * (float(r.max()) or 1.0)
            center[eye_idx[g][inner]] = True        # centre → blanc
    ring = eye & ~center                            # contour → sombre

    body = np.median(fc[~eye], axis=0).astype(int) if (~eye).any() else np.array([200, 40, 30])
    body_hex = "#%02X%02X%02X" % (int(body[0]), int(body[1]), int(body[2]))
    palette = [body_hex, ring_hex, center_hex]      # filaments 1, 2, 3

    paint_codes = [""] * len(fc)
    for i in np.where(ring)[0]:
        paint_codes[i] = PAINT_CODE[2]              # "4" → filament 2 (contour)
    for i in np.where(center)[0]:
        paint_codes[i] = PAINT_CODE[3]              # "8" → filament 3 (centre)

    def _rgb(h):
        h = h.lstrip("#")
        return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=float)
    fcol = np.tile(_rgb(body_hex), (len(fc), 1))
    fcol[ring] = _rgb(ring_hex)
    fcol[center] = _rgb(center_hex)
    thumb = render_thumbnail_png(mesh, face_colors=fcol) or _image_to_png_bytes(thumbnail_path)

    path = write_bambu_paint_3mf(mesh, paint_codes, palette, Path(out_path),
                                 name=name, thumbnail_bytes=thumb)
    return path, palette


def colorize_to_3mf(
    colored_mesh: trimesh.Trimesh,
    out_path: Path,
    name: str = "forge_model",
    n_colors: int = 2,
    thumbnail_path: "Path | str | None" = None,
    image_path: "Path | str | None" = None,
    flat: bool = False,
) -> tuple[Path | None, list[str]]:
    """Mesh → .3mf Bambu AMS. Retourne (chemin|None, palette).

    Objet PLAT (jeton) + image fournie → couleurs assignées par RELIEF (corps vs
    design embossé) avec la palette des VRAIES couleurs de l'image (Meshy ternit la
    texture). Sinon → quantization de la texture du mesh. Miniature = rendu coloré."""
    palette_hex: list[str] = []
    face_idx = None

    if flat and image_path:
        pal = _image_dominant_palette(image_path, n_colors)
        if pal:
            palette_hex = pal
            face_idx = assign_by_relief(colored_mesh)

    if face_idx is None:
        face_colors = extract_face_colors(colored_mesh)
        if n_colors <= 1:
            # MONO : 1 seul part watertight. Indispensable pour les figurines/solides
            # organiques : un split 2-parts y crée 2 coquilles ouvertes que Bambu
            # traite comme 2 objets séparés → l'un flotte, l'autre devient un "cube".
            if face_colors is not None:
                base = face_colors.mean(axis=0).astype(int)
            else:
                # Pas de couleur sur le maillage → couleur dominante de l'image source.
                ip = _image_dominant_palette(image_path, 2) if image_path else None
                h = ip[0].lstrip("#") if ip else "B4B4B4"
                base = np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)])
            palette_hex = ["#%02X%02X%02X" % (int(base[0]), int(base[1]), int(base[2]))]
            face_idx = np.zeros(len(colored_mesh.faces), dtype=int)
        elif face_colors is None:
            return None, []
        else:
            palette_hex, face_idx = quantize_faces(face_colors, n_colors=n_colors)

    # Couleurs par face d'après la palette (pour une miniature fidèle au résultat).
    _pal_rgb = np.array(
        [[int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)] for h in palette_hex],
        dtype=np.float64,
    )
    _face_cols = _pal_rgb[np.clip(face_idx, 0, len(_pal_rgb) - 1)]

    thumb = render_thumbnail_png(colored_mesh, face_colors=_face_cols) \
        or _image_to_png_bytes(thumbnail_path)
    path = write_bambu_color_3mf(
        colored_mesh, face_idx, palette_hex, out_path, name=name, thumbnail_bytes=thumb,
    )
    return path, palette_hex
