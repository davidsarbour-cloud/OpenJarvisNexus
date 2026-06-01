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

POD_DESIGNS: list[dict] = [
    # Print-on-Demand textile/gift designs (D3Dprintix POD line). Generated by
    # FLUX as ILLUSTRATIVE art (no slogans/text — FLUX renders text poorly).
    # PROMPT RULES (learned the hard way): bold saturated colors + thick clean
    # outline + high contrast + plain white background. AVOID "fine line art",
    # "muted/pale", and transparent bg — they come out faint/invisible. White bg
    # is removed later (rembg) for dark-shirt placement.
    # Each: key, tier, label, product, art_prompt, tags (listing seed keywords).
    # ── S-Tier — proven Etsy POD sellers ─────────────────────────────────────
    {"key": "garden_floral", "tier": "S", "label": "Garden Era Floral", "product": "t-shirt",
     "art_prompt": "vintage garden floral bouquet illustration, sage and blush wildflowers, bold clean linework, rich soft colors, sticker style, isolated on plain white background, centered, print-ready apparel graphic, high detail",
     "tags": ["floral", "botanical", "cottagecore", "vintage", "garden", "womens tshirt"]},
    {"key": "coffee_cozy", "tier": "S", "label": "Coffee & Cozy", "product": "t-shirt",
     "art_prompt": "cozy autumn illustration, steaming coffee cup on a knit blanket with books and falling leaves, warm saturated tones, bold flat illustration with clean outline, isolated on plain white background, centered, print-ready",
     "tags": ["coffee", "cozy", "autumn", "fall", "book lover", "gift"]},
    {"key": "celestial_mystic", "tier": "S", "label": "Celestial Mystique", "product": "t-shirt",
     "art_prompt": "celestial illustration, crescent moon embracing a radiant sun surrounded by stars, bold deep navy and rich gold, solid filled shapes with thick clean outline, sticker style, high contrast, isolated on plain white background, centered, print-ready",
     "tags": ["celestial", "moon", "mystical", "boho", "stars", "witchy"]},
    {"key": "cottagecore_mush", "tier": "S", "label": "Cottagecore Mushrooms", "product": "t-shirt",
     "art_prompt": "cottagecore red toadstool mushrooms with wildflowers and greenery, saturated storybook colors, bold clean outline, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["cottagecore", "mushroom", "forest", "botanical", "whimsical", "nature"]},

    # ── A-Tier — strong demand ───────────────────────────────────────────────
    {"key": "retro_sunset", "tier": "A", "label": "Retro Sunset", "product": "t-shirt",
     "art_prompt": "70s retro sunset badge with warm horizontal stripes, bold vintage orange cream and brown palette, thick clean outline, isolated on plain white background, centered, print-ready",
     "tags": ["retro", "70s", "sunset", "vintage", "nature", "minimalist"]},
    {"key": "luna_moth", "tier": "A", "label": "Luna Moth Celestial", "product": "t-shirt",
     "art_prompt": "luna moth with crescent moon and botanicals, symmetrical mystical illustration, rich teal and gold, bold solid fills with thick clean outline, high contrast, isolated on plain white background, centered, print-ready",
     "tags": ["luna moth", "celestial", "moth", "boho", "nature", "mystical"]},
    {"key": "kawaii_cat", "tier": "A", "label": "Kawaii Cats", "product": "t-shirt",
     "art_prompt": "kawaii cute cat illustration, pastel colors, simple rounded shapes, bold clean outline, playful sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["cat", "kawaii", "cute", "pastel", "cat lover", "gift"]},
    {"key": "floral_skull", "tier": "A", "label": "Floral Skull", "product": "t-shirt",
     "art_prompt": "decorative sugar skull surrounded by colorful flowers, bold illustrated sticker style, rich saturated boho colors, thick clean outline, high contrast, isolated on plain white background, centered, print-ready",
     "tags": ["skull", "floral", "boho", "gothic", "dark academia", "flowers"]},
    {"key": "mountain_adventure", "tier": "A", "label": "Mountain Adventure", "product": "t-shirt",
     "art_prompt": "minimalist mountain and pine forest landscape badge, bold outdoorsy retro illustration, rich greens and burnt orange, thick clean outline, isolated on plain white background, centered, print-ready",
     "tags": ["mountain", "adventure", "outdoors", "hiking", "nature", "camping"]},

    # ── B-Tier ───────────────────────────────────────────────────────────────
    {"key": "groovy_daisy", "tier": "B", "label": "Groovy Daisy", "product": "t-shirt",
     "art_prompt": "retro groovy smiling daisies, 70s funky flowers, bold warm saturated palette, thick clean outline, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["groovy", "daisy", "retro", "70s", "flower", "hippie"]},
    {"key": "abstract_organic", "tier": "B", "label": "Abstract Organic", "product": "t-shirt",
     "art_prompt": "modern abstract organic shapes, matisse-style cut-outs, bold saturated earthy palette, solid fills, clean composition, isolated on plain white background, centered, print-ready",
     "tags": ["abstract", "modern", "minimalist", "boho", "art", "shapes"]},
]


GAME_ASSETS_2D: list[dict] = [
    # 2D game asset PACKS (sets of item icons) for the game-asset line. Each pack
    # = one theme; FLUX renders each item with a shared `style` suffix (bold,
    # clean, isolated on white -> rembg -> transparent), bundled into a ZIP for
    # itch.io / Unity Asset Store. Each: key, tier, label, style, items (subjects).
    # ── S-Tier — top-selling game asset themes ───────────────────────────────
    {"key": "fantasy_weapons", "tier": "S", "label": "Fantasy Weapons",
     "style": "hand-painted 2D RPG game item icon, fantasy, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["sword", "battle axe", "longbow", "dagger", "magic staff", "war hammer", "spear", "round shield"]},
    {"key": "potions_consumables", "tier": "S", "label": "Potions & Consumables",
     "style": "hand-painted 2D RPG game item icon, glass potion bottle style, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["red health potion", "blue mana potion", "green elixir", "golden elixir", "magic scroll", "healing herb", "antidote vial", "stamina potion"]},
    {"key": "rpg_item_icons", "tier": "S", "label": "RPG Item Icons",
     "style": "hand-painted 2D RPG inventory item icon, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["treasure chest", "iron key", "rolled map", "gold ring", "amulet", "leather pouch", "spell book", "torch"]},
    {"key": "coins_currency", "tier": "S", "label": "Coins & Currency",
     "style": "hand-painted 2D game currency icon, shiny, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["gold coin", "silver coin", "stack of coins", "gem coin", "ruby", "emerald", "diamond", "coin pouch"]},

    # ── A-Tier ───────────────────────────────────────────────────────────────
    {"key": "scifi_weapons", "tier": "A", "label": "Sci-Fi Weapons",
     "style": "2D sci-fi game item icon, sleek glowing tech, bold clean outline, neon accents, centered, isolated on plain white background, high detail",
     "items": ["laser pistol", "plasma rifle", "energy sword", "frag grenade", "rail gun", "shock baton", "rocket launcher", "energy shield"]},
    {"key": "food_items", "tier": "A", "label": "Food & Cooking",
     "style": "hand-painted 2D game food item icon, cute, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["roast meat", "loaf of bread", "red apple", "fish", "cheese wheel", "mug of ale", "bowl of soup", "cooked egg"]},
    {"key": "gems_crystals", "tier": "A", "label": "Gems & Crystals",
     "style": "2D game gem icon, faceted glowing crystal, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["blue crystal", "red ruby", "green emerald", "purple amethyst", "yellow topaz", "clear diamond", "raw ore chunk", "magic shard"]},
    {"key": "magic_spells", "tier": "A", "label": "Magic & Spell FX",
     "style": "2D game spell effect icon, glowing magic, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["fireball", "ice shard", "lightning bolt", "poison cloud", "holy light", "shadow orb", "wind slash", "earth spike"]},

    # ── B-Tier ───────────────────────────────────────────────────────────────
    {"key": "tools_crafting", "tier": "B", "label": "Tools & Crafting",
     "style": "hand-painted 2D game crafting tool icon, bold clean outline, vibrant, centered, isolated on plain white background, high detail",
     "items": ["pickaxe", "hammer", "saw", "fishing rod", "shovel", "anvil", "needle and thread", "wood log"]},
]


_UI_ELEMENTS = ["button", "health bar", "mana bar", "menu panel frame",
                "dialog box", "inventory slot", "progress bar", "banner header"]

UI_KITS: list[dict] = [
    # Game UI kits (sets of interface elements) for the ui-kit line. Same pack
    # mechanic as GAME_ASSETS_2D: FLUX renders each element with a shared `style`
    # -> rembg transparent -> ZIP. A strong shared style keeps the set coherent.
    # Each: key, tier, label, style, items (the UI elements).
    {"key": "fantasy_ui", "tier": "S", "label": "Fantasy RPG UI Kit",
     "style": "fantasy game UI element, ornate carved wood and gold frame, medieval RPG, bold clean, isolated on plain white background, high detail, game asset",
     "items": _UI_ELEMENTS},
    {"key": "scifi_ui", "tier": "S", "label": "Sci-Fi HUD UI Kit",
     "style": "sci-fi game UI element, sleek dark panel with neon cyan glow, holographic HUD, bold clean, isolated on plain white background, game asset",
     "items": _UI_ELEMENTS},
    {"key": "minimal_ui", "tier": "A", "label": "Minimal Flat UI Kit",
     "style": "minimal flat game UI element, clean modern, soft shadows, neutral palette, rounded corners, isolated on plain white background, game asset",
     "items": _UI_ELEMENTS},
    {"key": "cute_ui", "tier": "A", "label": "Cute Cartoon UI Kit",
     "style": "cute cartoon game UI element, rounded, pastel candy colors, playful, bold outline, isolated on plain white background, game asset",
     "items": _UI_ELEMENTS},
    {"key": "neon_arcade_ui", "tier": "B", "label": "Neon Arcade UI Kit",
     "style": "retro neon arcade game UI element, 80s synthwave, glowing grid, bold, isolated on plain white background, game asset",
     "items": _UI_ELEMENTS},
    {"key": "horror_ui", "tier": "B", "label": "Dark Horror UI Kit",
     "style": "dark horror game UI element, grungy metal with subtle blood accents, eerie, isolated on plain white background, game asset",
     "items": _UI_ELEMENTS},
]


AI_PACKS: list[dict] = [
    # AI automation / prompt packs — generated by Ollama (local LLM) as Markdown.
    # HONEST: output is a DRAFT to curate, not a finished sellable product.
    # Each: key, tier, label, brief (the instruction handed to the LLM).
    {"key": "etsy_seo_prompts", "tier": "S", "label": "Etsy SEO Prompt Pack",
     "brief": "Create a pack of 25 ready-to-use ChatGPT prompts that help an Etsy seller write SEO-optimized titles, tags, and descriptions. Group by use case, each prompt copy-pasteable with [placeholders]."},
    {"key": "marketing_prompts", "tier": "S", "label": "Marketing Prompt Pack",
     "brief": "Create a pack of 25 ChatGPT prompts for small-business marketing (ads, emails, social captions, product launches). Group by channel, each prompt with [placeholders]."},
    {"key": "content_calendar", "tier": "S", "label": "30-Day Content Calendar Prompts",
     "brief": "Create a 30-day social-media content calendar prompt pack: a master prompt plus 30 daily post-idea prompts for a niche brand, with hooks and CTAs, using [placeholders]."},
    {"key": "n8n_lead_gen", "tier": "A", "label": "n8n Lead-Gen Workflow Pack",
     "brief": "Describe and provide an importable n8n workflow (as JSON plus a setup README) that captures leads from a form, enriches them, and adds them to a CRM/Google Sheet. Note required credentials."},
    {"key": "support_prompts", "tier": "A", "label": "Customer Support Prompt Pack",
     "brief": "Create a pack of 20 customer-support reply prompts/templates (refunds, shipping delays, complaints, upsells) for an e-commerce store, polite and on-brand, with [placeholders]."},
    {"key": "coldemail_sequences", "tier": "B", "label": "Cold Email Sequence Pack",
     "brief": "Create 3 cold-email outreach sequences (4 emails each) for B2B prospecting, with subject lines and [placeholders], plus a short usage guide."},
]


SHOPIFY_TEMPLATES: list[dict] = [
    # Reusable Shopify SECTIONS (Liquid + schema) generated by Ollama.
    # HONEST: DRAFT code to review/test in a theme, not a finished product.
    # Each: key, tier, label, brief (the instruction handed to the LLM).
    {"key": "hero_banner", "tier": "S", "label": "Hero Banner Section",
     "brief": "A responsive hero banner section: background image, heading, subheading, and a CTA button, all editable via schema settings."},
    {"key": "product_grid", "tier": "S", "label": "Featured Product Grid",
     "brief": "A featured-products grid section pulling from a chosen collection, with columns count, heading, and 'view all' link as schema settings."},
    {"key": "testimonials", "tier": "S", "label": "Testimonials Carousel",
     "brief": "A customer-testimonials section with repeatable blocks (quote, author, avatar) and a heading, configurable via schema."},
    {"key": "faq_accordion", "tier": "A", "label": "FAQ Accordion",
     "brief": "An FAQ accordion section with repeatable question/answer blocks, expand/collapse via details/summary, styled and configurable via schema."},
    {"key": "announcement_bar", "tier": "A", "label": "Announcement Bar",
     "brief": "A top announcement bar section: message text, link, background and text colors, dismissible, all as schema settings."},
    {"key": "countdown_timer", "tier": "B", "label": "Countdown Timer",
     "brief": "A promotional countdown-timer section to a target date with heading and CTA, target date and colors as schema settings (vanilla JS countdown)."},
]


# Tier -> sort rank (S first). Used by the rotation selector.
TIER_RANK = {"S": 0, "A": 1, "B": 2}
