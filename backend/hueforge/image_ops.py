"""HueForge image preparation — opérations PIL pures (aucun I/O de politique, aucun FastAPI).

Chaque fonction prend et renvoie une ``PIL.Image`` pour que le pipeline puisse les
enchaîner et journaliser chaque étape. La suppression du fond se dégrade proprement
si ``rembg`` est absent (même contrat que ``services/comfyui_images._remove_bg``) :
l'image est renvoyée inchangée plutôt que de casser le pipeline.
"""
from __future__ import annotations

import io

from PIL import Image, ImageEnhance

__all__ = [
    "load_image",
    "resize_longest",
    "crop_to_aspect",
    "boost_contrast",
    "remove_background",
    "flatten_onto",
    "dominant_colors",
    "to_png_bytes",
]


def load_image(data: bytes) -> Image.Image:
    """Décode des octets PNG/JPG en image PIL (laisse le mode d'origine)."""
    return Image.open(io.BytesIO(data))


def resize_longest(img: Image.Image, target_px: int) -> Image.Image:
    """Redimensionne pour que le côté le plus long == ``target_px`` (ratio préservé, LANCZOS)."""
    target_px = max(16, int(target_px))
    w, h = img.size
    longest = max(w, h)
    if longest == target_px:
        return img
    scale = target_px / float(longest)
    new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return img.resize(new_size, Image.LANCZOS)


def crop_to_aspect(img: Image.Image, target_w: float, target_h: float) -> Image.Image:
    """Recadre (centre) l'image pour coller au ratio target_w:target_h (plaque HueForge).

    Sert quand on vise une taille physique (ex: 119x47 mm) : l'image doit avoir le
    meme ratio que la plaque, sinon HueForge l'etire/letterboxe a l'import. Renvoie
    l'image inchangee si une dimension est nulle ou si le ratio colle deja.
    """
    if target_w <= 0 or target_h <= 0:
        return img
    w, h = img.size
    target_ar = target_w / target_h
    cur_ar = w / h
    if abs(cur_ar - target_ar) < 1e-3:
        return img
    if cur_ar > target_ar:  # trop large -> on rogne la largeur
        new_w = max(1, int(round(h * target_ar)))
        x0 = (w - new_w) // 2
        return img.crop((x0, 0, x0 + new_w, h))
    # trop haute -> on rogne la hauteur
    new_h = max(1, int(round(w / target_ar)))
    y0 = (h - new_h) // 2
    return img.crop((0, y0, w, y0 + new_h))


def boost_contrast(img: Image.Image, factor: float) -> Image.Image:
    """Augmente le contraste (1.0 = inchangé, >1 = plus de contraste)."""
    factor = float(factor)
    if abs(factor - 1.0) < 1e-3:
        return img
    return ImageEnhance.Contrast(img).enhance(factor)


def remove_background(img: Image.Image) -> tuple[Image.Image, bool]:
    """Détoure le sujet via rembg → RGBA. Renvoie ``(image, supprimé?)``.

    Si rembg n'est pas installé (dépendance optionnelle) ou échoue, renvoie
    l'image inchangée et ``False`` — le pipeline ne casse jamais sur une dépendance
    optionnelle manquante.
    """
    try:
        from rembg import remove

        out = remove(img)  # rembg accepte une PIL.Image et renvoie une PIL.Image (RGBA)
        if not isinstance(out, Image.Image):  # vieilles versions : peut renvoyer des bytes
            out = Image.open(io.BytesIO(out))
        return out.convert("RGBA"), True
    except Exception as e:  # noqa: BLE001 - dépendance optionnelle, on dégrade
        print(f"[hueforge.image_ops] rembg indisponible - fond conserve: {e}")
        return img, False


def _hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
    """'#rrggbb' ou 'rrggbb' → (r, g, b, 255). Tombe sur blanc si illisible."""
    s = (hex_color or "").lstrip("#").strip()
    try:
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        return (r, g, b, 255)
    except (ValueError, IndexError):
        return (255, 255, 255, 255)


def flatten_onto(img: Image.Image, hex_color: str) -> Image.Image:
    """Compose une image RGBA détourée sur un fond plein (base plate pour HueForge)."""
    rgba = img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, _hex_to_rgba(hex_color))
    return Image.alpha_composite(bg, rgba).convert("RGB")


def dominant_colors(img: Image.Image, n: int = 6) -> list[dict]:
    """Quantifie en ``n`` couleurs et renvoie ``[{hex, share}]`` trié par part décroissante.

    Sert à planifier les filaments / changements de couches HueForge (premier pas
    vers le palier 🟡 « analyse des couleurs »). Travaille sur une vignette 256px
    pour rester rapide.
    """
    n = max(1, int(n))
    rgb = img.convert("RGB")
    small = rgb.copy()
    small.thumbnail((256, 256))
    quant = small.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    palette = quant.getpalette() or []
    counts = quant.getcolors() or []  # [(count, palette_index), ...]
    if not counts or not palette:
        return []
    total = sum(c for c, _ in counts) or 1
    out: list[dict] = []
    for count, idx in sorted(counts, key=lambda t: t[0], reverse=True)[:n]:
        base = idx * 3
        r, g, b = palette[base], palette[base + 1], palette[base + 2]
        out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share": round(count / total, 4)})
    return out


def to_png_bytes(img: Image.Image) -> bytes:
    """Sérialise une image PIL en PNG (octets)."""
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
