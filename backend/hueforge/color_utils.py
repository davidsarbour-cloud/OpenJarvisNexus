"""HueForge — helpers couleur purs (source unique pour Lab / delta-E / luminance).

Aucune dependance lourde : stdlib `math` uniquement (pas de numpy/SciPy/colormath).
Utilise par variant_lab (separation de palette) et filament_lab (matching filament
+ ordre des couches sombre->clair). Aucun I/O, aucun FastAPI. Chaines ASCII (cp1252).
"""
from __future__ import annotations

import math

__all__ = [
    "hex_to_rgb",
    "rgb_to_hex",
    "srgb_to_lab",
    "delta_e_cie76",
    "relative_luminance",
    "nearest_by_lab",
]


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """'#rrggbb' / 'rrggbb' / '#rgb' -> (r, g, b). Tombe sur noir si illisible."""
    s = (hex_color or "").lstrip("#").strip()
    try:
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except (ValueError, IndexError):
        return (0, 0, 0)


def rgb_to_hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _linearize(c: float) -> float:
    """sRGB 8 bits -> canal lineaire [0,1] (gamma inverse)."""
    c = c / 255.0
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def srgb_to_lab(rgb) -> tuple[float, float, float]:
    """sRGB (0-255) -> CIELab (D65). Pur math, suffisant pour du matching couleur."""
    r, g, b = _linearize(rgb[0]), _linearize(rgb[1]), _linearize(rgb[2])
    # Lineaire RGB -> XYZ (matrice sRGB D65)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    # Normalisation par le blanc de reference D65
    x /= 0.95047
    y /= 1.00000
    z /= 1.08883

    def _f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t + 16.0 / 116.0)

    fx, fy, fz = _f(x), _f(y), _f(z)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e_cie76(lab1, lab2) -> float:
    """Distance perceptuelle CIE76 (euclidienne en Lab)."""
    return math.sqrt(
        (lab1[0] - lab2[0]) ** 2 + (lab1[1] - lab2[1]) ** 2 + (lab1[2] - lab2[2]) ** 2
    )


def relative_luminance(rgb) -> float:
    """Luminance relative Rec.709 [0,1] (0 = noir, 1 = blanc).

    Sert a ordonner les filaments sombre->clair (convention d'empilement HueForge :
    le plus sombre en bas, le plus clair au sommet)."""
    r, g, b = _linearize(rgb[0]), _linearize(rgb[1]), _linearize(rgb[2])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def nearest_by_lab(target_hex: str, candidates: list[dict], key: str = "hex") -> tuple[dict | None, float]:
    """Renvoie (candidat le plus proche, delta_e) pour target_hex parmi candidates.

    Chaque candidat est un dict contenant une couleur hex sous `key`. delta_e plus
    petit = meilleur match. Renvoie (None, inf) si la liste est vide.
    """
    if not candidates:
        return (None, float("inf"))
    tgt_lab = srgb_to_lab(hex_to_rgb(target_hex))
    best, best_d = None, float("inf")
    for c in candidates:
        d = delta_e_cie76(tgt_lab, srgb_to_lab(hex_to_rgb(c.get(key, "#000000"))))
        if d < best_d:
            best, best_d = c, d
    return (best, best_d)
