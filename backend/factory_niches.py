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
