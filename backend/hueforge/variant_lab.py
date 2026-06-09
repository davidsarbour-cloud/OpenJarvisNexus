"""HueForge tier 2 — variantes, scoring, selection, apercu Etsy (logique pure).

Aucun FastAPI, aucun app_state. La generation accepte un `render_fn` injecte
(le pipeline passe services.comfyui_images.render) pour que ce module reste
importable sans ComfyUI. Strategie par defaut `contrast_range` = balayage de
contraste sur UNE image de base -> 100% testable sans GPU. Chaines ASCII (cp1252).
"""
from __future__ import annotations

import asyncio
import math
import zlib

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

from hueforge import color_utils, image_ops

__all__ = [
    "generate_variants",
    "score_variant",
    "select_best_variant",
    "render_etsy_preview",
]

# Poids du score HueForge-suitability (somme = 1.0). layer_contrast domine :
# c'est le critere le plus pertinent pour un rendu HueForge en couches.
_WEIGHTS = {
    "tonal_range": 0.25,
    "color_separation": 0.25,
    "layer_contrast": 0.30,
    "palette_balance": 0.10,
    "edge_cleanliness": 0.10,
}


def _seed(s: str) -> int:
    """Seed deterministe depuis une chaine (meme pattern qu'auto_factory/iconforge)."""
    return zlib.crc32((s or "").encode("utf-8")) & 0x7FFFFFFF


def _contrast_sweep(base: float, count: int) -> list[float]:
    """`count` facteurs de contraste centres autour de `base` (borne a [0.5, 3.0])."""
    base = max(0.5, min(3.0, float(base)))
    count = max(1, int(count))
    if count == 1:
        return [round(base, 3)]
    lo = max(0.6, base - 0.35)
    hi = base + 0.5
    step = (hi - lo) / (count - 1)
    return [round(lo + step * i, 3) for i in range(count)]


def score_variant(img: Image.Image, palette: list[dict]) -> dict:
    """Note une variante pour son aptitude HueForge (0..100 + 5 composantes [0,1])."""
    gray = img.convert("L")
    gstat = ImageStat.Stat(gray)

    # tonal_range : etendue tonale (ecart-type des luminances)
    tonal = min(1.0, (gstat.stddev[0] or 0.0) / 80.0)

    # color_separation : delta-E moyen entre couleurs de la palette
    labs = [color_utils.srgb_to_lab(color_utils.hex_to_rgb(c["hex"])) for c in palette]
    if len(labs) >= 2:
        ds = [
            color_utils.delta_e_cie76(labs[i], labs[j])
            for i in range(len(labs))
            for j in range(i + 1, len(labs))
        ]
        sep = min(1.0, (sum(ds) / len(ds)) / 60.0)
    else:
        sep = 0.0

    # layer_contrast : ecart de luminance moyen entre paliers adjacents (tries)
    pl = sorted(palette, key=lambda c: color_utils.relative_luminance(color_utils.hex_to_rgb(c["hex"])))
    if len(pl) >= 2:
        gaps = []
        for i in range(len(pl) - 1):
            l1 = color_utils.relative_luminance(color_utils.hex_to_rgb(pl[i]["hex"]))
            l2 = color_utils.relative_luminance(color_utils.hex_to_rgb(pl[i + 1]["hex"]))
            gaps.append(abs(l2 - l1))
        layer_contrast = min(1.0, (sum(gaps) / len(gaps)) * 3.0)
    else:
        layer_contrast = 0.0

    # palette_balance : entropie de Shannon des parts (equilibre des couleurs)
    shares = [max(1e-6, float(c.get("share") or 0)) for c in palette]
    tot = sum(shares) or 1.0
    ps = [x / tot for x in shares]
    if len(ps) > 1:
        ent = -sum(p * math.log(p) for p in ps)
        balance = min(1.0, ent / math.log(len(ps)))
    else:
        balance = 0.0

    # edge_cleanliness : nettete des contours (proxy variance de FIND_EDGES)
    estat = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
    edge = min(1.0, (estat.stddev[0] or 0.0) / 60.0)

    components = {
        "tonal_range": round(tonal, 3),
        "color_separation": round(sep, 3),
        "layer_contrast": round(layer_contrast, 3),
        "palette_balance": round(balance, 3),
        "edge_cleanliness": round(edge, 3),
    }
    score = round(100.0 * sum(components[k] * _WEIGHTS[k] for k in _WEIGHTS), 1)
    return {"score": score, "components": components}


async def generate_variants(
    base_img: Image.Image,
    *,
    count: int,
    strategy: str,
    params: dict,
    out_dir,
    render_fn=None,
    prompt: str = "",
) -> list[dict]:
    """Genere `count` variantes entierement traitees (resize->contraste->fond->palette).

    strategy :
      - 'contrast_range'      : balayage de contraste sur base_img (DEFAUT, sans GPU)
      - 'seed_variation'      : N rendus FLUX a seeds differents (necessite render_fn)
      - 'comfyui_prompt_tweak': N rendus avec variantes de prompt (necessite render_fn)
    Chaque variante est sauvee dans out_dir/V{i}.png et notee via score_variant.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    size = int(params["size"])
    contrast = float(params["contrast"])
    remove_bg = bool(params["remove_bg"])
    flatten = params.get("flatten_bg")
    pcolors = int(params["palette_colors"])

    _STYLE_TWEAKS = [
        "", ", flat color blocks", ", high contrast poster",
        ", bold minimal shapes", ", clean vector style",
    ]

    # (label, image source, facteur de contraste)
    sources: list[tuple[str, Image.Image, float]] = []
    if strategy == "seed_variation" and render_fn:
        for i in range(max(1, count)):
            seed = _seed(f"{prompt}#{i}")
            png = await asyncio.to_thread(render_fn, prompt, size, seed)
            sources.append((f"seed{seed}", image_ops.load_image(png).convert("RGB"), contrast))
    elif strategy == "comfyui_prompt_tweak" and render_fn:
        for i in range(max(1, count)):
            tweak = _STYLE_TWEAKS[i % len(_STYLE_TWEAKS)]
            png = await asyncio.to_thread(render_fn, f"{prompt}{tweak}", size, _seed(f"{prompt}{tweak}"))
            sources.append((f"tweak{i+1}", image_ops.load_image(png).convert("RGB"), contrast))
    else:
        # contrast_range (defaut) + repli si render_fn manquant
        for f in _contrast_sweep(contrast, count):
            sources.append((f"c{f}", base_img, f))

    variants: list[dict] = []
    for i, (label, src, factor) in enumerate(sources):
        img = await asyncio.to_thread(image_ops.resize_longest, src.convert("RGB"), size)
        img = await asyncio.to_thread(image_ops.boost_contrast, img, factor)
        removed = False
        if remove_bg:
            img, removed = await asyncio.to_thread(image_ops.remove_background, img)
            if removed and flatten:
                img = await asyncio.to_thread(image_ops.flatten_onto, img, flatten)
        palette = await asyncio.to_thread(image_ops.dominant_colors, img, pcolors)
        vid = f"V{i+1}"
        vpath = out_dir / f"{vid}.png"
        await asyncio.to_thread(img.save, str(vpath), "PNG")
        sc = score_variant(img, palette)
        variants.append({
            "id": vid,
            "label": label,
            "strategy": strategy,
            "contrast": round(factor, 3),
            "file": str(vpath),
            "palette": palette,
            "bg_removed": removed,
            "score": sc["score"],
            "components": sc["components"],
        })
    return variants


def select_best_variant(variants: list[dict]) -> dict | None:
    """Choisit la variante au meilleur score HueForge. Renvoie id + rationale ASCII."""
    if not variants:
        return None
    winner = max(variants, key=lambda v: v.get("score", 0))
    comp = winner.get("components", {})
    rationale = (
        f"score {winner['score']}/100, meilleure sur {len(variants)} variantes - "
        + ", ".join(f"{k}={comp.get(k)}" for k in _WEIGHTS)
    )
    return {"best_variant_id": winner["id"], "rationale": rationale, "winner": winner}


# ── Apercu Etsy (composition PIL pure, calque sur les builders kit-cover) ──────
def _load_font(size: int, bold: bool = False):
    """Charge une police truetype (Windows/DejaVu), repli sur la police par defaut."""
    names = (
        ["arialbd.ttf", "Arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold else
        ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
    )
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return (r - l, b - t)
    except Exception:
        return (len(text) * 8, 14)


def render_etsy_preview(img: Image.Image, title: str, palette: list[dict], *, canvas: int = 2000) -> bytes:
    """Apercu de fiche Etsy carre : visuel + bande de palette + titre + badge.

    Composition PIL pure (pas de dependance reseau). Renvoie des octets PNG.
    """
    bg_top, bg_bot = (18, 20, 30), (8, 10, 18)
    out = Image.new("RGB", (canvas, canvas), bg_bot)
    # degrade vertical
    grad = Image.new("RGB", (1, canvas))
    for y in range(canvas):
        t = y / max(1, canvas - 1)
        grad.putpixel((0, y), tuple(int(bg_top[c] + (bg_bot[c] - bg_top[c]) * t) for c in range(3)))
    out = grad.resize((canvas, canvas))
    draw = ImageDraw.Draw(out)

    # zone visuelle (carre centre dans la moitie haute)
    margin = int(canvas * 0.08)
    art_box = int(canvas * 0.62)
    art = img.convert("RGB").copy()
    art.thumbnail((art_box, art_box), Image.LANCZOS)
    ax = (canvas - art.width) // 2
    ay = margin
    # cadre + ombre legere
    draw.rectangle([ax - 6, ay - 6, ax + art.width + 6, ay + art.height + 6], outline=(255, 79, 203), width=4)
    out.paste(art, (ax, ay))

    # bande de palette (swatches)
    pal = palette[:6] or [{"hex": "#888888"}]
    sw_y = ay + art.height + int(canvas * 0.04)
    sw_h = int(canvas * 0.07)
    sw_w = (canvas - 2 * margin) // len(pal)
    for i, c in enumerate(pal):
        x0 = margin + i * sw_w
        draw.rectangle([x0, sw_y, x0 + sw_w - 8, sw_y + sw_h], fill=color_utils.hex_to_rgb(c.get("hex", "#888888")))

    # titre
    title_font = _load_font(int(canvas * 0.055), bold=True)
    ttl = (title or "HueForge").strip()[:42]
    tw, th = _text_size(draw, ttl, title_font)
    ty = sw_y + sw_h + int(canvas * 0.05)
    draw.text(((canvas - tw) // 2, ty), ttl, fill=(235, 240, 255), font=title_font)

    # badge "HUEFORGE READY"
    badge_font = _load_font(int(canvas * 0.03), bold=True)
    badge = "HUEFORGE READY"
    bw, bh = _text_size(draw, badge, badge_font)
    by = ty + th + int(canvas * 0.04)
    pad = int(canvas * 0.02)
    bx = (canvas - bw) // 2
    draw.rectangle([bx - pad, by - pad // 2, bx + bw + pad, by + bh + pad // 2], outline=(0, 212, 168), width=3)
    draw.text((bx, by), badge, fill=(0, 212, 168), font=badge_font)

    return image_ops.to_png_bytes(out)
