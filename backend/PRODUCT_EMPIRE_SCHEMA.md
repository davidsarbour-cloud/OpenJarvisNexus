# 🏛️ AI PRODUCT EMPIRE — Schéma d'architecture commercial

> Livrable quotidien Auto-Factory. Comment vendre les packs (guide / advice / prompts),
> quels packs sont des **dossiers d'autres packs** (matriochka), et comment tout se
> recompose à partir d'**un seul atome** : le `generic.zip`.
>
> Stack couverte : **Claude · Hermes · OpenClaw · OpenJarvis · n8n · Ollama**

---

## 0. L'IDÉE EN UNE PHRASE

> Tu n'écris **qu'une seule chose** : l'**atome** (un `generic.zip`).
> Tout le reste — bundles, mega-packs, empire, abonnement — n'est qu'une **liste d'atomes**
> recompilée automatiquement. **Build once, sell at every altitude.**

---

## 1. LES 3 AXES (toute la boutique tient là-dessus)

Chaque produit = un point dans un cube à 3 dimensions :

| Axe | Question | Valeurs |
|-----|----------|---------|
| **A — FORMAT** | *Comment on le consomme ?* | `Prompts` (copier-coller) · `Guides` (lire-et-faire) · `Skills/Agents/Workflows` (installer-et-lancer = ton "advice") · `Visuels` (assets) |
| **B — VERTICALE** | *Sur quel outil ?* | `Claude` · `Hermes` · `OpenClaw` · `OpenJarvis` · `n8n` · `Ollama` |
| **C — ALTITUDE** | *Quelle taille de boîte ?* | `Atome → Single → Bundle → Mega/Empire → Vault(MRR)` |

Un produit = **Format × Verticale × Altitude**. Exemple :
`Prompts × Claude × Bundle` = « Claude for Business — 10 agent packs ».

---

## 2. L'ATOME — `generic.zip` (la seule chose qu'on fabrique)

Structure canonique (= ta structure IconForge `packager.py`, généralisée à TOUT produit) :

```
{pack_id}_{YYYYMMDD}/
├── README.md          ← install + usage en 5 min (vendeur)
├── LICENSE.txt        ← single-user, no redistribution
├── cover.png          ← 2000×2000 Etsy + 1280×720 Gumroad
├── manifest.json      ← métadonnées machine (id, tier, format, verticale, prix)
└── payload/           ← LE contenu, selon le FORMAT :
    ├── prompts.md / prompts.json      (Format = Prompts)
    ├── guide.md + guide.pdf           (Format = Guides)
    ├── skill/SKILL.md  ou  workflow.json   (Format = Skills/Agents/Workflows)
    └── ios/ android/ streamdeck/      (Format = Visuels — IconForge)
```

**Règle d'or :** tout atome a EXACTEMENT ces 4 fichiers + `payload/`. Un bundle ne fait que
**réunir plusieurs `payload/` dans des sous-dossiers** + régénérer README/cover/manifest.

---

## 3. LA MATRIOCHKA — quels packs sont des « dossiers d'autres packs »

C'est ta question centrale. Réponse : **chaque altitude est physiquement un dossier
qui contient les zips de l'altitude en dessous.**

```
                 PRIX        CONTENU PHYSIQUE                     EXEMPLE (marché)
┌───────────────────────────────────────────────────────────────────────────────┐
│ ATOME          —          README+payload+LICENSE+cover         (jamais vendu seul)
│   │ ×1
│   ▼
│ SINGLE PACK    3–8 CA$    1 atome                              "Real Estate Claude Prompts"
│   │ ×5–12 (même verticale)                                     "Ollama Setup Pack"
│   ▼
│ THEMED BUNDLE  12–25 CA$  dossier de 5–12 singles              "Claude for Business (10 agents)"
│   │ ×3–6 bundles                                               "Ultimate AI Productivity (10 books)"
│   ▼
│ MEGA / EMPIRE  25–75 CA$  dossier de 3–6 bundles               "The AI Money Machine (9 empires)"
│   │ tout, qui grossit                                          "4000+ Claude Power Prompts"
│   ▼
│ VAULT / MRR    9–29 CA$/mois  accès à TOUTE la bibliothèque    "19,000+ Claude Skills — Coworker OS"
│                              + les drops quotidiens
└───────────────────────────────────────────────────────────────────────────────┘
```

> **Un mega-pack = un manifeste** (liste d'ids d'atomes). Le builder zippe les atomes
> référencés, génère un README « ce qui est inclus » + une cover, et c'est vendu.
> Zéro contenu neuf à écrire.

---

## 4. LE GRAND SCHÉMA DE CATÉGORIES (la boutique entière)

```
🏛️ AI PRODUCT EMPIRE
│
├── 1️⃣ PROMPTS  — intelligence copier-coller
│   ├── Claude Prompt Packs
│   │   ├── Par-Rôle  ← tes AI_PACKS : RealEstate · Marketing · Ecommerce · Coach ·
│   │   │              Recruiter · Copywriter · SocialMedia · SaaS · YouTuber · EtsySeller
│   │   ├── Par-Tâche : Email · SEO · Sales · Productivité
│   │   └── 🧳 MEGA "4000+ Claude Power Prompts" = dossier de TOUS les rôles+tâches
│   ├── GPT Prompt Packs (miroir 1:1 des Claude)
│   └── Multi-modèle (Claude+GPT+Gemini+Grok)  ← tes POD "Rebel" buckets
│
├── 2️⃣ GUIDES  — ebooks / blueprints lire-et-faire
│   ├── Setup Guides
│   │   ├── 🦙 Ollama Setup Pack         ← docker-compose réellement testé
│   │   ├── 🖥️ AI Server Kit (FLAGSHIP)  ← 250 prompts + hardware CSV + ROI calc
│   │   └── 🎨 ComfyUI Pack
│   ├── Mastery Guides
│   │   ├── Claude AI Mastery / Masterclass
│   │   └── Claude Code for Beginners
│   └── 🧳 MEGA "AI Tech Productivity Mastery" = dossier de 10 ebooks
│
├── 3️⃣ SKILLS / AGENTS / WORKFLOWS  — intelligence installer-et-lancer  (= ton "ADVICE")
│   ├── 🛠️ Hermes Skill Packs        ← backend/skills/hermes/*  (SKILL.md prêts)
│   ├── 🌐 OpenClaw Skill Catalog     ← 13 700 skills communautaires, bundles curés
│   ├── 🤖 Claude Agents Pro          ← "300+ agents spécialisés", install < 2 min
│   ├── 🔗 n8n Workflow Templates     ← workflows .json automatisation
│   └── 🧠 OpenJarvis Recipes/Operators ← tes .toml recipes/operators (self-hosted)
│
├── 4️⃣ VISUELS  — les lignes non-texte de l'Auto-Factory
│   ├── 🎯 Icon Packs (IconForge)     ← ios/android/streamdeck
│   ├── 👕 POD Designs
│   ├── 🎮 Game2D / UIKits
│   └── 💎 Premium/Valkyrie           ← thumbnails YouTube · covers · logos (auto-améliorant)
│
└── 5️⃣ THE VAULT  — MRR / abonnement = accès à la bibliothèque qui grossit
    └── 🔁 "Coworker OS" = TOUT, mis à jour chaque jour par l'Auto-Factory
```

---

## 5. MAPPING STACK → FORMAT → PRODUIT (ta techno = ton catalogue)

| Verticale | Ce que c'est chez toi | Format vendable | Altitude de départ | Prix |
|-----------|----------------------|-----------------|--------------------|------|
| **Claude** | Modèle + Claude Code | Prompts · Guides · Agents | Single → Mega | 3–75 CA$ |
| **Hermes** | `backend/skills/hermes/*` (150+ SKILL.md) | Skills | Bundle | 12–25 CA$ |
| **OpenClaw** | 13 700 skills communautaires | Skills (curation) | Mega + Vault | 25 CA$ / 19 CA$mo |
| **OpenJarvis** | Ton OS d'orchestration self-hosted | Guide + Recipes + Agents | Flagship | 39–99 CA$ |
| **n8n** | Plateforme d'automatisation | Workflows .json | Bundle | 12–20 CA$ |
| **Ollama** | LLM local (Docker) | Guide (setup pack) | Single → dans AI Server Kit | 5 CA$ → 39 CA$ |

---

## 6. L'OPTIMISATION (« je les veux optimiser »)

1. **Build-once-sell-many** — on n'écrit que des **atomes**. Bundles = manifestes (`bundle.json` = liste d'ids).
2. **Recompose nocturne** — chaque nuit après l'Auto-Factory, un step `recompose` rezippe les
   bundles touchés par les nouveaux atomes + régénère le Vault. **C'est ça le livrable quotidien.**
3. **Échelle de prix / ancrage** — sur chaque mega : prix barré haut + single pas cher en entrée
   (exactement ce que font tes captures : 42→21, 72→21).
4. **Graphe de cross-sell** — chaque README de single pointe vers son bundle (« prends les 10 pour X »),
   chaque bundle pointe vers le Vault.
5. **Miroir multi-plateforme** — chaque atome Claude se clone en GPT/Gemini/Grok (coût marginal nul).
6. **SEO auto** — `commerce/metadata_gen.py` (ULTRON) génère titre/tags/description par atome ET par bundle.

---

## 7. CE QU'IL MANQUE POUR L'AUTOMATISER (proposition d'implémentation)

| Pièce | Statut | À faire |
|-------|--------|---------|
| Atome standard (`generic.zip`) | ✅ existe (IconForge `packager.py`) | généraliser à Prompts/Guides/Skills |
| `bundle.json` (manifeste de recompose) | ❌ | nouveau format : `{tier, includes:[atom_ids], price, cover_theme}` |
| `recompose.py` (nightly) | ❌ | zippe atomes référencés + README + cover + manifest |
| Lien Auto-Factory → recompose | ⚠️ partiel | hook après les 8 lignes dans `auto_factory.py` |
| Génération covers de bundle | ✅ (`build_kit_cover.py`) | paramétrer par thème de bundle |
| Listing Etsy/Gumroad par bundle | ✅ (`commerce/pipeline.py`) | étendre `metadata_gen` au niveau bundle |

---

*Généré pour David — régénérable quotidiennement. Voir le poster PNG associé.*
