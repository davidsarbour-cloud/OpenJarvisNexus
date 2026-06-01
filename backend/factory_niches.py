"""Catalogs for the Auto-Factory — TWO independent product lines.

NICHES       : 3D objects for the STL line (D3Dprintix). Drives stl_agent.
ICON_THEMES  : visual aesthetics for the icon-pack line (IconForge/FLUX).

These are deliberately SEPARATE: a 3D object ("book nook") is not an icon-pack
theme, and an icon aesthetic ("vaporwave") is not a 3D print. Each line rotates
over its own list, by commercial tier.

NICHES is filtered to what Meshy text-to-3D produces well — STATIC decorative
pieces. Excluded on purpose: articulated/print-in-place (no working joints),
lithophanes (need a customer photo), precise-fit functional gear (won't hold
exact dimensions). Each item: key, tier (S/A/B), label (FR), stl_prompt (EN).

ICON_THEMES: real Etsy/Gumroad icon-pack aesthetics. Each: key, tier, label,
theme (the FLUX style fragment applied to the standard app-icon set).
"""
from __future__ import annotations

NICHES: list[dict] = [
    # ── S-Tier — machine à cash ──────────────────────────────────────────────
    {"key": "book_nook_fantasy", "tier": "S", "label": "Book Nook fantasy",
     "stl_prompt": "fantasy book nook diorama insert, miniature medieval alleyway with stone archway and tiny lanterns, highly detailed decorative bookshelf piece"},
    {"key": "book_nook_scifi", "tier": "S", "label": "Book Nook sci-fi",
     "stl_prompt": "sci-fi book nook diorama insert, miniature futuristic corridor with neon panels and pipes, detailed decorative bookshelf piece"},
    {"key": "rpg_miniature", "tier": "S", "label": "Miniature JDR originale",
     "stl_prompt": "original tabletop RPG miniature, heroic fantasy character, 32mm scale, detailed base, single solid piece"},
    {"key": "giant_dice", "tier": "S", "label": "Dés géants décoratifs",
     "stl_prompt": "oversized decorative d20 dice, faceted geometric, engraved numerals, display piece"},
    {"key": "dice_tower", "tier": "S", "label": "Tour à dés",
     "stl_prompt": "decorative fantasy dice tower, dragon-themed castle turret, ornate detailing"},
    {"key": "planter_animal", "tier": "S", "label": "Pot de plante animal",
     "stl_prompt": "cute animal-shaped succulent planter pot, smooth stylized form, flat stable base, drainage"},
    {"key": "planter_geek", "tier": "S", "label": "Pot de plante geek",
     "stl_prompt": "geeky themed succulent planter pot, stylized robot/skull motif, flat stable base"},

    # ── A-Tier — très forte demande ──────────────────────────────────────────
    {"key": "led_lamp", "tier": "A", "label": "Lampe LED imprimée",
     "stl_prompt": "decorative 3D printed lamp shade, organic flowing form, diffuse lattice for soft LED light"},
    {"key": "vase_voronoi", "tier": "A", "label": "Vase Voronoi",
     "stl_prompt": "Voronoi pattern decorative vase, organic cellular lattice, elegant tapered silhouette"},
    {"key": "vase_organic", "tier": "A", "label": "Vase organique",
     "stl_prompt": "organic flowing decorative vase, smooth sculptural curves, modern art piece"},
    {"key": "wallart_geometric", "tier": "A", "label": "Déco murale géométrique",
     "stl_prompt": "geometric wall art panel, faceted low-poly relief, modern minimalist decor"},
    {"key": "wallart_scifi", "tier": "A", "label": "Déco murale sci-fi",
     "stl_prompt": "sci-fi wall art panel, futuristic tech relief with circuitry motifs, decorative plaque"},
    {"key": "wallart_fantasy", "tier": "A", "label": "Déco murale fantasy",
     "stl_prompt": "fantasy wall art panel, ornate dragon crest relief, decorative plaque"},
    {"key": "organizer_gamer", "tier": "A", "label": "Organisateur bureau gamer",
     "stl_prompt": "decorative gamer desk organizer, stylized controller-inspired tray, pen and accessory holders"},
    {"key": "organizer_tech", "tier": "A", "label": "Organisateur bureau IA/tech",
     "stl_prompt": "minimalist tech desk organizer, clean geometric tray with compartments"},

    # ── A-Tier Geek ──────────────────────────────────────────────────────────
    {"key": "reliquary_fantasy", "tier": "A", "label": "Reliquaire fantasy",
     "stl_prompt": "fantasy reliquary box, ornate gothic detailing, decorative trinket container"},
    {"key": "decorative_skull", "tier": "A", "label": "Crâne décoratif stylisé",
     "stl_prompt": "stylized decorative skull sculpture, intricate engraved patterns, display piece"},
    {"key": "creature_bust", "tier": "A", "label": "Buste de créature originale",
     "stl_prompt": "original fantasy creature bust sculpture, detailed display piece on a plinth"},
    {"key": "chinese_dragon", "tier": "A", "label": "Dragon chinois décoratif",
     "stl_prompt": "decorative Chinese dragon statue, flowing serpentine form, ornate scales, display piece"},
    {"key": "lovecraftian_creature", "tier": "A", "label": "Créature lovecraftienne",
     "stl_prompt": "original Lovecraftian eldritch creature sculpture, tentacled cosmic horror, detailed display piece"},
    {"key": "retro_robot", "tier": "A", "label": "Robot rétro-futuriste",
     "stl_prompt": "retro-futuristic robot figurine, 1950s tin-toy styling, rounded chrome forms, static display"},
    {"key": "mecha", "tier": "A", "label": "Mécha original",
     "stl_prompt": "original mecha robot figurine, angular armored panels, posed static display piece"},
    {"key": "fictional_artifact", "tier": "A", "label": "Artefact archéologique fictif",
     "stl_prompt": "fictional ancient archaeological artifact, weathered carved relic, museum display piece"},
    {"key": "mystic_totem", "tier": "A", "label": "Totem mystique",
     "stl_prompt": "mystic totem sculpture, stacked symbolic carved figures, occult decorative piece"},
    {"key": "diorama", "tier": "A", "label": "Diorama miniature",
     "stl_prompt": "miniature diorama scene, detailed environment base, decorative display"},

    # ── A-Tier Gaming (generable subset) ─────────────────────────────────────
    {"key": "rpg_markers", "tier": "A", "label": "Marqueurs de ressources JDR",
     "stl_prompt": "set of fantasy RPG resource tokens, stylized coin and gem markers, tabletop accessories"},
    {"key": "rpg_terrain", "tier": "A", "label": "Accessoires de campagne RPG",
     "stl_prompt": "tabletop RPG terrain prop, ruined fantasy pillar and crates scatter piece"},

    # ── B-Tier (generable subset) ────────────────────────────────────────────
    {"key": "wall_hooks", "tier": "B", "label": "Crochets décoratifs muraux",
     "stl_prompt": "decorative wall hook, stylized animal or geometric form, single mounting piece"},
]


ICON_THEMES: list[dict] = [
    # ── S-Tier — best-selling icon aesthetics ────────────────────────────────
    {"key": "minimal_black", "tier": "S", "label": "Minimal Black",
     "theme": "matte black background, bold minimal white glyph, high-contrast, clean geometric"},
    {"key": "pastel_soft", "tier": "S", "label": "Pastel doux",
     "theme": "soft pastel palette, rounded, cute, clean flat, cohesive"},
    {"key": "cyberpunk_neon", "tier": "S", "label": "Cyberpunk néon",
     "theme": "cyberpunk neon, dark background, glowing edges, futuristic, vibrant"},

    # ── A-Tier — strong demand ───────────────────────────────────────────────
    {"key": "y2k_chrome", "tier": "A", "label": "Y2K chrome",
     "theme": "Y2K chrome, glossy liquid metal, early 2000s, holographic"},
    {"key": "vaporwave", "tier": "A", "label": "Vaporwave",
     "theme": "vaporwave, pink and teal gradient, retro 80s, dreamy"},
    {"key": "dark_academia", "tier": "A", "label": "Dark Academia",
     "theme": "dark academia, vintage parchment tones, muted browns, scholarly, ornate"},
    {"key": "cottagecore", "tier": "A", "label": "Cottagecore",
     "theme": "cottagecore, botanical, soft watercolor, floral, cozy, earthy"},
    {"key": "kawaii", "tier": "A", "label": "Kawaii",
     "theme": "kawaii, cute mascot, pastel, rounded, playful, japanese"},
    {"key": "gold_luxe", "tier": "A", "label": "Or luxe / verre",
     "theme": "luxury gold and frosted glass, elegant, premium, glossy, minimal"},
    {"key": "anime", "tier": "A", "label": "Anime",
     "theme": "anime style, vibrant, cel-shaded, expressive, colorful"},

    # ── B-Tier — seasonal (rotate in near the season) ────────────────────────
    {"key": "halloween", "tier": "B", "label": "Halloween / Automne",
     "theme": "halloween autumn, cute spooky, orange and purple, cozy"},
    {"key": "christmas", "tier": "B", "label": "Noël / Hiver",
     "theme": "christmas winter, festive, red green and gold, cozy snow"},
]

# Tier -> sort rank (S first). Used by the rotation selector.
TIER_RANK = {"S": 0, "A": 1, "B": 2}
