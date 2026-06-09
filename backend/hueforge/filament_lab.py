"""HueForge tier 3 — filaments possedes, couches, simulation, parametres (logique pure).

Inventaire editable : `filament_inventory.default.json` (committe) -> copie vers
`filament_inventory.json` (live, gitignore) au 1er chargement. Validation-et-degrade
comme _load_cache : jamais d'exception, repli sur les defauts. La simulation est une
APPROXIMATION honnete (remap luminance->bande filament), flaggee approx=True : un vrai
HueForge demande des mesures TD par filament. Aucun FastAPI. Chaines ASCII (cp1252).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PIL import Image

from hueforge import color_utils

__all__ = [
    "load_inventory",
    "save_inventory",
    "analyze_filaments",
    "estimate_layer_changes",
    "simulate_hueforge_render",
    "build_print_params",
]

_DIR = Path(__file__).parent
_DEFAULT_PATH = _DIR / "filament_inventory.default.json"
_LIVE_PATH = _DIR / "filament_inventory.json"

# Repli code si meme le .default.json est illisible (ne devrait jamais arriver).
_HARDCODED_DEFAULT = {
    "slots": 4,
    "updated_at": None,
    "filaments": [
        {"hex": "#000000", "name": "Black", "brand": "Bambu Basic", "material": "PLA",
         "ams_slot": 1, "count_m": 240, "density": 1.24, "nozzle_temp": 220, "bed_temp": 55, "td_mm": 0.8},
        {"hex": "#FFFFFF", "name": "Jade White", "brand": "Bambu Basic", "material": "PLA",
         "ams_slot": 2, "count_m": 240, "density": 1.24, "nozzle_temp": 220, "bed_temp": 55, "td_mm": 2.0},
        {"hex": "#8E9089", "name": "Bambu Gray", "brand": "Bambu Basic", "material": "PLA",
         "ams_slot": 3, "count_m": 240, "density": 1.24, "nozzle_temp": 220, "bed_temp": 55, "td_mm": 1.2},
        {"hex": "#00AE42", "name": "Bambu Green", "brand": "Bambu Basic", "material": "PLA",
         "ams_slot": 4, "count_m": 240, "density": 1.24, "nozzle_temp": 220, "bed_temp": 55, "td_mm": 1.0},
    ],
}

# delta-E CIE76 au-dela duquel un match filament est juge mauvais.
_MATCH_THRESHOLD = 25.0


def _load_default() -> dict:
    try:
        return json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - repli ultime
        print(f"[filament_lab] default.json illisible ({e}) - repli code en dur")
        return dict(_HARDCODED_DEFAULT)


def _valid_hex(h: str) -> bool:
    try:
        color_utils.hex_to_rgb(h)
        s = (h or "").lstrip("#")
        return len(s) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in s)
    except Exception:
        return False


def _sanitize(data: dict) -> dict:
    """Valide/normalise un inventaire : hex valides, ams_slot 1..slots, numeriques bornes."""
    slots = int(data.get("slots", 4) or 4)
    fils_in = data.get("filaments", []) or []
    clean: list[dict] = []
    for f in fils_in:
        if not isinstance(f, dict) or not _valid_hex(f.get("hex", "")):
            continue
        slot = f.get("ams_slot")
        if slot is not None:
            try:
                slot = int(slot)
                slot = slot if 1 <= slot <= slots else None
            except (TypeError, ValueError):
                slot = None
        clean.append({
            "hex": color_utils.rgb_to_hex(color_utils.hex_to_rgb(f["hex"])),
            "name": str(f.get("name", "Filament"))[:40],
            "brand": str(f.get("brand", ""))[:40],
            "material": str(f.get("material", "PLA"))[:20],
            "ams_slot": slot,
            "count_m": max(0.0, float(f.get("count_m", 0) or 0)),
            "density": max(0.5, min(3.0, float(f.get("density", 1.24) or 1.24))),
            "nozzle_temp": int(f.get("nozzle_temp", 220) or 220),
            "bed_temp": int(f.get("bed_temp", 55) or 55),
            "td_mm": max(0.05, min(10.0, float(f.get("td_mm", 1.0) or 1.0))),
        })
    return {"slots": slots, "updated_at": data.get("updated_at"), "filaments": clean}


def load_inventory() -> dict:
    """Charge l'inventaire live ; le seede depuis le defaut au 1er appel ; degrade
    proprement (sans jamais lever) sur fichier corrompu."""
    if not _LIVE_PATH.exists():
        seed = _sanitize(_load_default())
        try:
            _LIVE_PATH.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"[filament_lab] seed inventaire live impossible ({e})")
        return seed
    try:
        data = json.loads(_LIVE_PATH.read_text(encoding="utf-8"))
        clean = _sanitize(data)
        if not clean["filaments"]:
            raise ValueError("inventaire live vide apres validation")
        return clean
    except Exception as e:  # noqa: BLE001
        print(f"[filament_lab] inventaire live invalide ({e}) - repli sur les defauts")
        return _sanitize(_load_default())


def save_inventory(data: dict) -> dict:
    """Valide puis ecrit l'inventaire live. Renvoie l'inventaire normalise."""
    clean = _sanitize(data or {})
    clean["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _LIVE_PATH.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return clean


def analyze_filaments(palette: list[dict], inventory: dict) -> dict:
    """Associe chaque couleur de palette au filament possede le plus proche (Lab/delta-E)."""
    fils = inventory.get("filaments", [])
    matched: list[dict] = []
    unmatched: list[dict] = []
    for c in palette or []:
        best, d = color_utils.nearest_by_lab(c.get("hex", "#000000"), fils)
        rec = {
            "palette_hex": c.get("hex"),
            "share": c.get("share"),
            "filament": best,
            "delta_e": round(d, 2) if d != float("inf") else None,
        }
        if best and d <= _MATCH_THRESHOLD:
            matched.append(rec)
        else:
            unmatched.append({**rec, "recommended_substitution": best})
    n = len(palette or [])
    return {
        "owned_count": len(fils),
        "coverage_pct": round(100 * len(matched) / n) if n else 0,
        "colors_matched": matched,
        "unmatched_palette": unmatched,
        "match_threshold_delta_e": _MATCH_THRESHOLD,
    }


def estimate_layer_changes(palette: list[dict], inventory: dict, *,
                           layer_height: float, model_height_mm: float) -> list[dict]:
    """Bandes de couleur sombre->clair (convention HueForge) + hauteurs de swap.

    Epaisseur de bande proportionnelle a la part de la couleur ; flagge under_opaque
    si l'epaisseur est inferieure au td_mm du filament (couleur pas pleinement opaque).
    """
    fils = inventory.get("filaments", [])
    if not fils:
        return []
    groups: dict[str, dict] = {}
    for c in palette or []:
        best, d = color_utils.nearest_by_lab(c.get("hex", "#000000"), fils)
        if not best:
            continue
        g = groups.setdefault(best["hex"], {"filament": best, "maps_palette": [], "share": 0.0})
        g["maps_palette"].append(c.get("hex"))
        g["share"] += float(c.get("share") or 0.0)
    used = list(groups.values())
    if not used:
        return []
    tot = sum(g["share"] for g in used) or 1.0
    used.sort(key=lambda g: color_utils.relative_luminance(color_utils.hex_to_rgb(g["filament"]["hex"])))

    bands: list[dict] = []
    z = 0.0
    lh = float(layer_height) or 0.08
    for i, g in enumerate(used):
        thickness = max(lh, round(model_height_mm * g["share"] / tot, 3))
        z_start = round(z, 3)
        z += thickness
        td = float(g["filament"].get("td_mm", 1.0))
        bands.append({
            "order": i + 1,
            "filament": g["filament"],
            "maps_palette": g["maps_palette"],
            "share": round(g["share"] / tot, 4),
            "band_thickness_mm": round(thickness, 3),
            "swap_z_mm": z_start,            # Z ou ce filament COMMENCE (0 = base)
            "swap_layer": round(z_start / lh),
            "under_opaque": thickness < td,  # epaisseur < TD -> couleur pas pleine
        })
    return bands


def simulate_hueforge_render(img: Image.Image, bands: list[dict], *,
                             layer_height: float, model_height_mm: float,
                             footprint_mm: float = 150.0,
                             plate_mm: tuple | None = None) -> dict:
    """Apercu approxime du rendu HueForge (remap luminance -> couleur filament).

    Honnete : method='luminance_band_remap', approx=True. Les estimations poids/temps
    supposent un bloc plein a la taille de plaque (sur-estimation, sans infill).
    plate_mm = (largeur, hauteur) en mm si une taille physique est visee (ex: 119x47).
    """
    import numpy as np

    rgb = img.convert("RGB")
    n = len(bands)
    if n == 0:
        return {"method": "luminance_band_remap", "approx": True, "preview_png": None,
                "note": "aucun filament possede ne correspond a la palette"}

    band_colors = np.array(
        [color_utils.hex_to_rgb(b["filament"]["hex"]) for b in bands], dtype=np.uint8
    )
    # uint32 : evite l'overflow de (gray * n) si l'inventaire a beaucoup de bandes.
    gray = np.asarray(rgb.convert("L"), dtype=np.uint32)
    # luminance -> index de bande (0 = sombre ... n-1 = clair)
    idx = np.minimum(n - 1, (gray * n) // 256)
    preview = Image.fromarray(band_colors[idx], "RGB")

    # Empreinte au sol : plaque physique si fournie, sinon deduite du ratio image.
    w, h = rgb.size
    if plate_mm and plate_mm[0] and plate_mm[1]:
        foot_w, foot_h = float(plate_mm[0]), float(plate_mm[1])
    else:
        aspect = (w / h) if h else 1.0
        if w >= h:
            foot_w, foot_h = footprint_mm, footprint_mm / aspect
        else:
            foot_w, foot_h = footprint_mm * aspect, footprint_mm
    area_mm2 = foot_w * foot_h
    volume_cm3 = area_mm2 * float(model_height_mm) / 1000.0
    avg_density = sum(b["filament"].get("density", 1.24) for b in bands) / n
    weight_g = round(volume_cm3 * avg_density, 1)
    lh = float(layer_height) or 0.08
    total_layers = max(1, round(float(model_height_mm) / lh))
    swaps = n - 1
    time_min = round(total_layers * 0.18 + swaps * 3.0 + 6.0)

    from hueforge import image_ops
    return {
        "method": "luminance_band_remap",
        "approx": True,
        "preview_png": image_ops.to_png_bytes(preview),
        "bands": n,
        "footprint_mm": [round(foot_w, 1), round(foot_h, 1)],
        "model_height_mm": float(model_height_mm),
        "estimated_weight_g": weight_g,
        "estimated_time_min": int(time_min),
        "note": "Approximation: remap luminance->filament; poids/temps sur bloc plein, non-slicer.",
    }


def build_print_params(bands: list[dict], *, layer_height: float, model_height_mm: float,
                       plate_mm: tuple | None = None) -> dict:
    """Parametres d'impression (taille plaque, hauteurs de swap, ordre, slots AMS, temperatures)."""
    if not bands:
        return {"note": "aucune bande - palette non couverte par l'inventaire"}
    fils = [b["filament"] for b in bands]
    lh = float(layer_height) or 0.08
    swaps = [
        {
            "at_z_mm": b["swap_z_mm"],
            "at_layer": b["swap_layer"],
            "to_filament": b["filament"]["name"],
            "to_hex": b["filament"]["hex"],
            "ams_slot": b["filament"].get("ams_slot"),
        }
        for b in bands[1:]
    ]
    total_h = round(sum(b["band_thickness_mm"] for b in bands), 3)
    ams_map: dict[str, dict] = {}
    to_load: list[dict] = []
    for f in fils:
        slot = f.get("ams_slot")
        if slot:
            ams_map[str(slot)] = {"name": f["name"], "hex": f["hex"]}
        else:
            to_load.append({"name": f["name"], "hex": f["hex"]})
    return {
        "plate_size_mm": [float(plate_mm[0]), float(plate_mm[1])] if (plate_mm and plate_mm[0] and plate_mm[1]) else None,
        "layer_height_mm": lh,
        "first_layer_height_mm": 0.2,
        "nozzle_mm": 0.4,
        "nozzle_temp_c": max(int(f.get("nozzle_temp", 220)) for f in fils),
        "bed_temp_c": max(int(f.get("bed_temp", 55)) for f in fils),
        "model_height_mm": total_h,
        "total_layers": max(1, round(total_h / lh)),
        "color_swap_count": len(swaps),
        "color_swaps": swaps,
        "filament_order_dark_to_light": [f["name"] for f in fils],
        "ams_slot_mapping": ams_map,
        "filaments_to_load": to_load,
        "note": "Hauteurs de swap basees sur la part de chaque couleur; charge 'filaments_to_load' dans l'AMS.",
    }
