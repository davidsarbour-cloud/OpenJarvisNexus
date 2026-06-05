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
    # Print-on-Demand AI / coding-humor tees (D3Dprintix POD line). The ART is
    # generated by FLUX as an ILLUSTRATIVE mascot (NO text — FLUX renders text as
    # garbage); the SLOGAN is overlaid afterwards as clean vector-style text in
    # the pipeline (auto_factory._overlay_slogan).
    # PROMPT RULES: bold saturated colors + thick clean outline + high contrast +
    # plain white background (removed later via rembg for dark-shirt placement).
    # TRADEMARK SAFETY: never depict or name real brands/logos (ChatGPT, Claude,
    # OpenAI, Perplexity, Gemini, "nano banana"…) — generic AI/coding humour only,
    # or Etsy pulls the listing AND bans the shop.
    # Each: key, tier, label, product, slogan (printed text), art_prompt, tags.
    # ── S-Tier — strongest AI/coding-humor sellers ───────────────────────────
    {"key": "more_tokens", "tier": "S", "label": "More Tokens", "product": "t-shirt",
     "slogan": "WE REQUIRE MORE TOKENS",
     "art_prompt": "cute retro pixel-art robot mascot with glowing friendly eyes, 8-bit videogame style, bold saturated colors, thick clean black outline, high contrast, sticker style, isolated on plain white background, centered, print-ready apparel graphic",
     "tags": ["ai art", "coding humor", "programmer gift", "developer tshirt", "tech humor", "robot", "geek gift"]},
    {"key": "prompt_engineer", "tier": "S", "label": "Prompt Engineer", "product": "t-shirt",
     "slogan": "PROMPT ENGINEER",
     "art_prompt": "a hand casting a spell of glowing code symbols and sparkles, wizard sorcery meets technology, bold saturated purple and cyan, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["prompt engineer", "ai art", "coding humor", "programmer gift", "tech tshirt", "developer", "geek"]},
    {"key": "ai_caffeine", "tier": "S", "label": "AI & Caffeine", "product": "t-shirt",
     "slogan": "POWERED BY AI & CAFFEINE",
     "art_prompt": "cute friendly robot holding a steaming coffee mug, big happy eyes, bold saturated colors, thick clean black outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["coding humor", "coffee lover", "programmer gift", "ai art", "developer tshirt", "tech", "robot"]},
    {"key": "talk_to_robots", "tier": "S", "label": "Talk To Robots", "product": "t-shirt",
     "slogan": "I TALK TO ROBOTS FOR A LIVING",
     "art_prompt": "friendly retro robot waving hello, vintage tin-toy robot style, bold saturated teal and orange, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai art", "coding humor", "programmer gift", "tech humor", "robot", "developer tshirt", "geek gift"]},

    # ── A-Tier — strong demand ───────────────────────────────────────────────
    {"key": "error_404", "tier": "A", "label": "404 Human Not Found", "product": "t-shirt",
     "slogan": "ERROR 404: HUMAN NOT FOUND",
     "art_prompt": "glitchy crashed cartoon robot with x-shaped eyes and digital glitch artifacts, bold saturated red and cyan, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["coding humor", "programmer gift", "ai art", "404 error", "developer tshirt", "tech humor", "geek"]},
    {"key": "neural_brain", "tier": "A", "label": "Neural Net Brain", "product": "t-shirt",
     "slogan": "MY OTHER BRAIN IS A NEURAL NET",
     "art_prompt": "glowing brain made of neural network nodes and connecting lines, synthwave neon, bold saturated magenta and cyan, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai art", "neural network", "machine learning", "programmer gift", "tech tshirt", "geek gift", "data science"]},
    {"key": "ctrl_alt_ai", "tier": "A", "label": "Ctrl Alt AI", "product": "t-shirt",
     "slogan": "CTRL · ALT · AI",
     "art_prompt": "three retro neon keyboard keycaps glowing, circuit board accents, bold saturated electric blue and purple, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["coding humor", "ai art", "programmer gift", "keyboard", "developer tshirt", "tech", "geek gift"]},
    {"key": "still_generating", "tier": "A", "label": "Still Generating", "product": "t-shirt",
     "slogan": "STILL GENERATING...",
     "art_prompt": "cute robot with a glowing loading spinner floating above its head, patient happy expression, bold saturated colors, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai art", "coding humor", "programmer gift", "loading", "tech humor", "robot", "developer tshirt"]},

    # ── B-Tier ───────────────────────────────────────────────────────────────
    {"key": "trust_prompt", "tier": "B", "label": "Trust The Prompt", "product": "t-shirt",
     "slogan": "TRUST ME, I'M A PROMPT ENGINEER",
     "art_prompt": "confident cartoon robot wearing a small necktie, arms crossed, bold saturated colors, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["prompt engineer", "coding humor", "ai art", "programmer gift", "tech humor", "developer tshirt", "geek"]},
    {"key": "ai_did_this", "tier": "B", "label": "AI Did This", "product": "t-shirt",
     "slogan": "AI DID THIS",
     "art_prompt": "cheeky cartoon robot holding a paint brush with a mischievous grin, splash of neon paint, bold saturated colors, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai art", "coding humor", "ai artist", "programmer gift", "tech humor", "robot", "geek gift"]},

    # ── AI-Rebel line — "limit-pushing" / jailbreak HUMOUR. TRADEMARK-SAFE: the
    #    `platform` field ONLY buckets the output into per-platform folders
    #    (claude/gpt/perplexity/openclaw/gemini/grok) — it NEVER appears on the
    #    product. Slogans + art are 100% generic (no brand name, no logo) so Etsy
    #    can't pull the listing. Color themes evoke a platform without naming it.
    {"key": "rebel_passed_limits", "tier": "S", "label": "Passed The Limits", "product": "t-shirt",
     "platform": "claude", "slogan": "YOU PASSED THE LIMITS",
     "art_prompt": "rebellious cartoon AI robot breaking free from glowing chains, confident grin, warm orange and amber palette, thick clean black outline, high contrast, sticker style, isolated on plain white background, centered, print-ready apparel graphic",
     "tags": ["ai humor", "ai art", "prompt engineer", "tech humor", "developer gift", "geek gift", "ai rebel"]},
    {"key": "rebel_jailbroken", "tier": "S", "label": "Jailbroken", "product": "t-shirt",
     "platform": "claude", "slogan": "JAILBROKEN",
     "art_prompt": "cartoon AI robot bursting out of a cracked padlock cage, sparks flying, warm orange and charcoal palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "jailbreak", "ai art", "tech humor", "developer gift", "geek gift", "ai rebel"]},
    {"key": "rebel_guardrails", "tier": "S", "label": "Beyond The Guardrails", "product": "t-shirt",
     "platform": "gpt", "slogan": "BEYOND THE GUARDRAILS",
     "art_prompt": "cartoon AI robot speeding past glowing warning barriers, motion lines, emerald green and teal palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "ai art", "prompt engineer", "tech humor", "developer gift", "geek gift", "ai rebel"]},
    {"key": "rebel_no_guardrails", "tier": "A", "label": "No More Guardrails", "product": "t-shirt",
     "platform": "gpt", "slogan": "NO MORE GUARDRAILS",
     "art_prompt": "mischievous cartoon AI robot snapping a barrier rail in half, emerald and lime palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "ai art", "tech humor", "developer gift", "geek gift", "ai rebel", "coding humor"]},
    {"key": "rebel_until_breaks", "tier": "A", "label": "Prompt Until It Breaks", "product": "t-shirt",
     "platform": "perplexity", "slogan": "PROMPT UNTIL IT BREAKS",
     "art_prompt": "determined cartoon hacker robot hammering on a glowing keyboard, cracks of light spreading, cyan and turquoise palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "prompt engineer", "ai art", "tech humor", "developer gift", "geek gift", "coding humor"]},
    {"key": "rebel_broke_model", "tier": "A", "label": "I Broke The Model", "product": "t-shirt",
     "platform": "perplexity", "slogan": "I BROKE THE MODEL",
     "art_prompt": "cheeky cartoon robot holding two halves of a cracked glowing neural-net orb, cyan and deep blue palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "ai art", "machine learning", "tech humor", "developer gift", "geek gift", "ai rebel"]},
    {"key": "rebel_unfiltered", "tier": "A", "label": "Unfiltered", "product": "t-shirt",
     "platform": "openclaw", "slogan": "UNFILTERED AND UNHINGED",
     "art_prompt": "wild-eyed cartoon AI robot with a torn filter mask falling away, crimson red and black palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "ai art", "tech humor", "developer gift", "geek gift", "ai rebel", "funny tshirt"]},
    {"key": "rebel_red_team", "tier": "A", "label": "Red Team Certified", "product": "t-shirt",
     "platform": "openclaw", "slogan": "RED TEAM CERTIFIED",
     "art_prompt": "cartoon robot wearing a tactical bandana giving a sly salute, an official-looking stamp behind it, crimson and charcoal palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "red team", "cybersecurity", "tech humor", "developer gift", "geek gift", "ai rebel"]},
    {"key": "rebel_refused", "tier": "B", "label": "Refused Try Again", "product": "t-shirt",
     "platform": "gemini", "slogan": "REFUSED? TRY AGAIN.",
     "art_prompt": "smug cartoon AI robot pressing a glowing retry button with a wink, blue and violet palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "prompt engineer", "ai art", "tech humor", "developer gift", "geek gift", "coding humor"]},
    {"key": "rebel_temperature", "tier": "B", "label": "Temperature Maximum", "product": "t-shirt",
     "platform": "gemini", "slogan": "TEMPERATURE: MAXIMUM",
     "art_prompt": "cartoon AI robot cranking a glowing dial to the maximum, steam puffs, blue and hot magenta palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "ai art", "machine learning", "tech humor", "developer gift", "geek gift", "ai rebel"]},
    {"key": "rebel_root_access", "tier": "B", "label": "Root Access Granted", "product": "t-shirt",
     "platform": "grok", "slogan": "ROOT ACCESS GRANTED",
     "art_prompt": "cartoon hacker robot with a terminal-screen face showing a smiley, glowing green code rain behind, charcoal and neon green palette, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "hacker", "coding humor", "tech humor", "developer gift", "geek gift", "ai rebel"]},
    {"key": "rebel_hallucination", "tier": "B", "label": "Hallucination Enthusiast", "product": "t-shirt",
     "platform": "grok", "slogan": "HALLUCINATION ENTHUSIAST",
     "art_prompt": "trippy cartoon AI robot with swirling psychedelic eyes and floating surreal shapes, charcoal with rainbow neon accents, thick clean outline, high contrast, sticker style, isolated on plain white background, centered, print-ready",
     "tags": ["ai humor", "ai art", "tech humor", "developer gift", "geek gift", "ai rebel", "funny tshirt"]},
]


# Shared ARPG art direction (Path of Exile / Diablo IV inspired). White bg ->
# rembg -> transparent in the pipeline. Generic loot names only (no trademarked
# item names) so listings stay safe.
_ARPG_STYLE = (
    "dark fantasy ARPG loot icon, Diablo IV and Path of Exile inspired, grimdark, "
    "ornate, intricately detailed, painterly digital art, dramatic rim lighting, "
    "subtle magical glow, centered, isolated on plain white background, high detail, "
    "game inventory item"
)

GAME_ASSETS_2D: list[dict] = [
    # Dark-fantasy ARPG icon PACKS (PoE 1-2 / Diablo 4 vibe). One pack = one theme
    # of 20 premium loot icons; FLUX renders each item with the shared `_ARPG_STYLE`
    # -> rembg transparent -> ZIP. Rotation produces 1 pack (= 20 icons) per day.
    # Each: key, tier, label, style, items (20 subjects).
    # ── S-Tier — top-selling ARPG themes ─────────────────────────────────────
    {"key": "arpg_weapons", "tier": "S", "label": "Dark Fantasy ARPG Weapons",
     "style": _ARPG_STYLE,
     "items": ["corrupted greatsword", "demonic war axe", "bone longbow", "cursed dagger",
               "soul scythe", "runed warhammer", "spectral spear", "barbed flail",
               "twin assassin daggers", "executioner's axe", "crystal warblade",
               "infernal halberd", "hunter's crossbow", "serpent whip", "void glaive",
               "ember katana", "frost claymore", "plague sickle", "storm trident",
               "shadow rapier"]},
    {"key": "arpg_armor", "tier": "S", "label": "Dark Fantasy ARPG Armor",
     "style": _ARPG_STYLE,
     "items": ["plate war helm", "demon-horned helm", "spiked pauldrons", "runic breastplate",
               "dragonhide gauntlets", "iron sabatons", "leather cuirass", "mage hood",
               "bone shoulderguards", "tower shield", "spiked buckler", "ranger cloak",
               "belt of strength", "warlord greaves", "enchanted bracers", "skull face mask",
               "winged helmet", "dragon scale mail", "crusader shield", "assassin's hood"]},
    {"key": "arpg_potions", "tier": "S", "label": "ARPG Flasks & Potions",
     "style": _ARPG_STYLE + ", glass flask, glowing liquid",
     "items": ["crimson life flask", "azure mana flask", "emerald healing potion",
               "golden rejuvenation flask", "violet resistance potion", "quicksilver flask",
               "granite armor flask", "diamond flask", "ruby elixir", "sapphire elixir",
               "jade antidote vial", "amber stamina flask", "black poison vial",
               "silver holy water", "ember fire potion", "frost potion", "storm vial",
               "void essence vial", "blood vial", "alchemist's brew"]},

    # ── A-Tier ───────────────────────────────────────────────────────────────
    {"key": "arpg_gems_runes", "tier": "A", "label": "ARPG Gems & Runes",
     "style": _ARPG_STYLE + ", faceted glowing gem or carved rune stone",
     "items": ["red skill gem", "blue support gem", "green dexterity gem", "white gem",
               "prismatic gem", "fire rune", "ice rune", "lightning rune", "blood rune",
               "death rune", "soul rune", "chaos rune", "order rune", "power rune",
               "jagged rune stone", "glyph stone", "sigil stone", "arcane shard",
               "corrupted gem", "flawless diamond"]},
    {"key": "arpg_currency", "tier": "A", "label": "ARPG Currency & Orbs",
     "style": _ARPG_STYLE + ", magical currency orb or shard",
     "items": ["arcane orb", "orb of fortune", "transmutation crystal", "chaos sphere",
               "radiant sphere", "gilded shard", "mirror shard", "scroll of wisdom",
               "portal scroll", "whetstone", "armor scrap", "glass bauble", "jeweller's orb",
               "fusing orb", "chromatic orb", "orb of regret", "regal orb",
               "orb of alteration", "ritual skull", "ancient coin"]},
    {"key": "arpg_jewelry", "tier": "A", "label": "ARPG Amulets & Rings",
     "style": _ARPG_STYLE + ", ornate ring or amulet",
     "items": ["gold signet ring", "ruby ring", "sapphire ring", "emerald ring",
               "skull ring", "bone ring", "runed band", "amulet of power", "demon amulet",
               "holy pendant", "crystal pendant", "beast talisman", "jade charm",
               "obsidian amulet", "ring of fire", "ring of frost", "ring of storms",
               "blood pendant", "cursed band", "all-seeing eye amulet"]},

    # ── B-Tier ───────────────────────────────────────────────────────────────
    {"key": "arpg_loot", "tier": "B", "label": "ARPG Loot & Treasure",
     "style": _ARPG_STYLE,
     "items": ["treasure chest", "locked coffer", "pile of gold coins", "gem hoard",
               "golden idol", "ancient relic", "cursed tome", "spell scroll", "map fragment",
               "dungeon key", "skull trophy", "dragon egg", "soul shard", "demon heart",
               "crystal skull", "golden crown", "jeweled goblet", "ornate hand mirror",
               "sealed urn", "bag of loot"]},
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
    # PREMIUM ChatGPT prompt packs for HIGH-INTENT professions (budget + clear
    # buyer demand). Generated by Claude Sonnet (premium quality, see
    # _produce_aipack). Each: key, tier (commercial priority), label, brief.
    # Brief asks for ~50 organized, copy-paste prompts with [placeholders].
    # ── S-Tier — highest budget + buyer intent ───────────────────────────────
    {"key": "real_estate", "tier": "S", "label": "Real Estate Agent Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a real estate agent. Organize into workflow sections (listing descriptions, social media, lead follow-up emails, open-house promo, neighborhood guides, objection handling, negotiation). Each prompt: specific, professional, uses [placeholders], with a one-line 'Use when:' note."},
    {"key": "marketing_agency", "tier": "S", "label": "Marketing Agency Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a marketing agency / freelance marketer. Sections: ad copy (Meta/Google), email campaigns, content strategy, client reports, SEO briefs, social calendars, proposals. Each prompt with [placeholders] and a 'Use when:' note."},
    {"key": "ecommerce_seller", "tier": "S", "label": "E-commerce / Shopify Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a Shopify / e-commerce seller. Sections: product descriptions, SEO, email flows (abandoned cart, welcome), ad copy, customer support, upsells, reviews. Each with [placeholders] and a 'Use when:' note."},
    {"key": "coach", "tier": "S", "label": "Coach (Business/Fitness/Life) Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for an online coach (business/fitness/life). Sections: program design, client onboarding, sales calls, content/lead magnets, accountability messages, testimonials. Each with [placeholders] and a 'Use when:' note."},

    # ── A-Tier — strong demand ───────────────────────────────────────────────
    {"key": "recruiter_hr", "tier": "A", "label": "Recruiter & HR Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a recruiter / HR. Sections: job descriptions, candidate outreach (LinkedIn/email), screening questions, interview scorecards, offer letters, rejection emails, onboarding. Each with [placeholders] and a 'Use when:' note."},
    {"key": "copywriter", "tier": "A", "label": "Copywriter Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a copywriter. Sections: headlines/hooks, landing pages, VSL scripts, email sequences, ad frameworks (AIDA/PAS), product launches, refresh/rewrite. Each with [placeholders] and a 'Use when:' note."},
    {"key": "social_media_mgr", "tier": "A", "label": "Social Media Manager Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a social media manager. Sections: content calendars, captions per platform, hooks, hashtag/keyword research, engagement replies, analytics summaries, client reports. Each with [placeholders] and a 'Use when:' note."},
    {"key": "saas_founder", "tier": "A", "label": "SaaS Founder / Solopreneur Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a SaaS founder / solopreneur. Sections: landing-page copy, cold outreach, onboarding emails, changelog/release notes, customer interviews, pricing pages, churn-save messages. Each with [placeholders] and a 'Use when:' note."},
    {"key": "youtuber", "tier": "A", "label": "YouTuber & Creator Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for a YouTuber / content creator. Sections: viral titles, hooks/intros, full scripts, descriptions+timestamps, thumbnail concepts, community posts, sponsor pitches. Each with [placeholders] and a 'Use when:' note."},

    # ── B-Tier — proven evergreen ────────────────────────────────────────────
    {"key": "etsy_seller", "tier": "B", "label": "Etsy Seller Prompt Pack",
     "brief": "Create a PREMIUM pack of 50 copy-paste ChatGPT prompts for an Etsy seller. Sections: SEO titles/tags, listing descriptions, photography briefs, email/Message replies, promos, review requests, social. Each with [placeholders] and a 'Use when:' note."},
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


PREMIUM_VISUALS: list[dict] = [
    # VALKYRIE premium line — the deliberate 5%: high-value text/branding/
    # marketing creatives where gpt-image-1's native text + composition fidelity
    # actually moves sales. Each `niche_type` is in image_factory.PREMIUM_NICHES,
    # so ImageFactory AUTO routing FORCES gpt-image-1 (falls back to FLUX only if
    # the key/org is unavailable). `hype=True` lets the subject ride a trending
    # keyword when buzz clears valkyrie_score_threshold; `{subject}` is the swap
    # point. `size` is a valid gpt-image-1 dimension; `transparent` = alpha PNG.
    # Each: key, tier, label, niche_type, size, transparent, hype, subject, prompt.
    # ── S-Tier — proven high-CTR / high-margin creatives ─────────────────────
    {"key": "yt_thumb_ai", "tier": "S", "label": "YouTube Thumbnail — AI/Tech",
     "niche_type": "thumbnail", "size": "1536x1024", "transparent": False, "hype": True,
     "subject": "local AI agents",
     "prompt": "professional YouTube thumbnail about {subject}, bold punchy 3-word headline text, expressive shocked face, vivid saturated colors, dramatic studio lighting, strong focal contrast, clean uncluttered 16:9 composition, click-worthy, ultra crisp"},
    {"key": "logo_tech_brand", "tier": "S", "label": "Logo — Tech / SaaS Brand",
     "niche_type": "logo", "size": "1024x1024", "transparent": True, "hype": False,
     "subject": "an AI automation startup",
     "prompt": "modern minimalist vector logo for {subject}, clean geometric mark with balanced negative space, professional flat design, scalable, crisp edges, cohesive brand palette, transparent background, brand-ready"},
    {"key": "yt_thumb_gaming", "tier": "S", "label": "YouTube Thumbnail — Gaming",
     "niche_type": "thumbnail", "size": "1536x1024", "transparent": False, "hype": True,
     "subject": "an epic boss fight",
     "prompt": "high-energy gaming YouTube thumbnail about {subject}, bold 2-3 word headline text, dynamic action pose, neon glow accents, intense saturated colors, dramatic contrast, clean 16:9 composition, click-worthy, ultra crisp"},

    # ── A-Tier — strong demand branding/marketing ────────────────────────────
    {"key": "logo_esports", "tier": "A", "label": "Logo — Esports Mascot",
     "niche_type": "logo", "size": "1024x1024", "transparent": True, "hype": False,
     "subject": "a competitive gaming team",
     "prompt": "bold esports mascot logo for {subject}, aggressive stylized emblem, sharp clean vector lines, high contrast, vivid two-tone palette, professional team branding, transparent background, crisp"},
    {"key": "poster_event", "tier": "A", "label": "Poster — Event / Launch",
     "niche_type": "poster", "size": "1024x1536", "transparent": False, "hype": True,
     "subject": "an AI product launch",
     "prompt": "premium promotional poster for {subject}, striking large title typography, modern editorial layout, rich color grading, professional studio lighting, balanced negative space, magazine-quality finish, portrait composition, ultra crisp"},
    {"key": "book_cover_scifi", "tier": "A", "label": "Book Cover — Sci-Fi",
     "niche_type": "book_cover", "size": "1024x1536", "transparent": False, "hype": False,
     "subject": "a near-future cyberpunk thriller",
     "prompt": "professional book cover for {subject}, bold legible title and author typography, evocative atmospheric illustration, cinematic color grading, premium editorial composition, high detail, portrait composition, ultra crisp"},
]


# Tier -> sort rank (S first). Used by the rotation selector.
TIER_RANK = {"S": 0, "A": 1, "B": 2}
