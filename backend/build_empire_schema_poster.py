"""Render the AI Product Empire architecture as a portrait poster PNG (phone-readable)."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 2000, 3200
BG = (14, 17, 23)
CARD = (22, 27, 34)
LINE = (48, 54, 61)
WHITE = (230, 237, 243)
MUTE = (139, 148, 158)

# accent palette per category
C_PROMPT = (88, 166, 255)  # blue
C_GUIDE = (63, 185, 80)  # green
C_SKILL = (188, 140, 255)  # purple
C_VISUAL = (255, 123, 114)  # coral
C_VAULT = (240, 180, 41)  # gold
C_ATOM = (255, 255, 255)

FONTS = r"C:\Windows\Fonts"


def F(name, size):
    return ImageFont.truetype(str(Path(FONTS) / name), size)


f_title = F("arialbd.ttf", 64)
f_sub = F("arial.ttf", 30)
f_h2 = F("arialbd.ttf", 40)
f_card_t = F("arialbd.ttf", 34)
f_item = F("arial.ttf", 27)
f_small = F("arial.ttf", 23)
f_price = F("arialbd.ttf", 30)
f_chip = F("arialbd.ttf", 28)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def rrect(xy, r, fill=None, outline=None, width=2):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def text_w(s, font):
    return d.textbbox((0, 0), s, font=font)[2]


def center(s, x0, x1, y, font, fill=WHITE):
    d.text(((x0 + x1) / 2 - text_w(s, font) / 2, y), s, font=font, fill=fill)


def wrap(s, font, maxw):
    out, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if text_w(t, font) <= maxw:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


y = 50
# ---- HEADER ----
center("AI PRODUCT EMPIRE", 0, W, y, f_title, WHITE)
y += 80
center("Schema d'architecture commercial  ·  livrable quotidien Auto-Factory", 0, W, y, f_sub, MUTE)
y += 50
center("Claude · Hermes · OpenClaw · OpenJarvis · n8n · Ollama", 0, W, y, f_sub, (88, 166, 255))
y += 70

# ---- 3 AXES chips ----
axes = [
    ("AXE A — FORMAT", "Prompts · Guides · Skills/Agents · Visuels", C_PROMPT),
    ("AXE B — VERTICALE", "Claude · Hermes · OpenClaw · OpenJarvis · n8n · Ollama", C_SKILL),
    ("AXE C — ALTITUDE", "Atome > Single > Bundle > Mega > Vault", C_VAULT),
]
cw = (W - 100 - 40) // 3
for i, (t, sub, col) in enumerate(axes):
    x0 = 50 + i * (cw + 20)
    rrect((x0, y, x0 + cw, y + 130), 16, fill=CARD, outline=col, width=3)
    d.text((x0 + 24, y + 22), t, font=f_chip, fill=col)
    for j, ln in enumerate(wrap(sub, f_small, cw - 48)):
        d.text((x0 + 24, y + 62 + j * 28), ln, font=f_small, fill=WHITE)
y += 170

# ---- SECTION: THE ATOM ----
d.text(
    (50, y), "1 · L'ATOME  —  generic.zip  (la seule chose qu'on fabrique)", font=f_h2, fill=WHITE
)
y += 60
rrect((50, y, W - 50, y + 150), 16, fill=CARD, outline=C_ATOM, width=2)
atom_files = "README.md   +   LICENSE.txt   +   cover.png   +   manifest.json   +   payload/"
center(atom_files, 50, W - 50, y + 28, f_card_t, C_ATOM)
center(
    "payload/ = prompts.md  |  guide.pdf  |  skill/SKILL.md  |  workflow.json  |  ios+android+streamdeck",
    50,
    W - 50,
    y + 78,
    f_item,
    MUTE,
)
center(
    "Un bundle ne fait que REUNIR plusieurs payload/ + regenerer README/cover/manifest",
    50,
    W - 50,
    y + 112,
    f_small,
    (240, 180, 41),
)
y += 195

# ---- SECTION: MATRYOSHKA LADDER ----
d.text(
    (50, y),
    "2 · LA MATRIOCHKA  —  quels packs sont des dossiers d'autres packs",
    font=f_h2,
    fill=WHITE,
)
y += 60
ladder = [
    ("ATOME", "README + payload + LICENSE + cover", "(jamais vendu seul)", C_ATOM, ""),
    ("SINGLE PACK", "1 atome", "Real Estate Claude Prompts · Ollama Setup", C_PROMPT, "3-8 CA$"),
    (
        "THEMED BUNDLE",
        "dossier de 5-12 singles",
        "Claude for Business (10 agents)",
        C_GUIDE,
        "12-25 CA$",
    ),
    (
        "MEGA / EMPIRE",
        "dossier de 3-6 bundles",
        "The AI Money Machine (9 empires)",
        C_VISUAL,
        "25-75 CA$",
    ),
    (
        "VAULT / MRR",
        "acces a TOUTE la bibliotheque + drops quotidiens",
        "19,000+ Claude Skills — Coworker OS",
        C_VAULT,
        "9-29 /mo",
    ),
]
indent = 0
for i, (name, what, ex, col, price) in enumerate(ladder):
    x0 = 50 + indent
    x1 = W - 50
    bh = 96
    rrect((x0, y, x1, y + bh), 14, fill=CARD, outline=col, width=3)
    d.text((x0 + 24, y + 14), name, font=f_card_t, fill=col)
    d.text((x0 + 24, y + 56), what, font=f_item, fill=WHITE)
    if ex:
        d.text((x0 + 24 + text_w(name, f_card_t) + 40, y + 18), "· " + ex, font=f_small, fill=MUTE)
    if price:
        d.text((x1 - text_w(price, f_price) - 28, y + 32), price, font=f_price, fill=col)
    # down arrow
    if i < len(ladder) - 1:
        ax = x0 + 60
        d.line((ax, y + bh, ax, y + bh + 26), fill=col, width=4)
        d.polygon([(ax - 9, y + bh + 18), (ax + 9, y + bh + 18), (ax, y + bh + 30)], fill=col)
    y += bh + 30
    indent += 60
y += 10

# ---- SECTION: CATEGORY TREE (5 columns) ----
d.text((50, y), "3 · LE GRAND SCHEMA DE CATEGORIES", font=f_h2, fill=WHITE)
y += 60
cols = [
    (
        "1 PROMPTS",
        C_PROMPT,
        [
            "Claude Prompt Packs",
            "  Par-Role (10 AI_PACKS)",
            "  Par-Tache: SEO/Email/Sales",
            "  MEGA 4000+ Prompts",
            "GPT Packs (miroir)",
            "Multi-modele (Rebel)",
        ],
    ),
    (
        "2 GUIDES",
        C_GUIDE,
        [
            "Ollama Setup Pack",
            "AI Server Kit (FLAGSHIP)",
            "ComfyUI Pack",
            "Claude Mastery / Masterclass",
            "Claude Code Beginners",
            "MEGA 10 ebooks",
        ],
    ),
    (
        "3 SKILLS/AGENTS",
        C_SKILL,
        [
            "Hermes Skill Packs",
            "OpenClaw Catalog 13.7k",
            "Claude Agents Pro 300+",
            "n8n Workflows .json",
            "OpenJarvis Recipes",
            "= ton ADVICE",
        ],
    ),
    (
        "4 VISUELS",
        C_VISUAL,
        [
            "Icon Packs (IconForge)",
            "POD Designs",
            "Game2D / UIKits",
            "Premium / Valkyrie",
            "thumbnails · covers",
            "auto-ameliorant",
        ],
    ),
    (
        "5 THE VAULT",
        C_VAULT,
        [
            "Coworker OS",
            "= TOUT, chaque jour",
            "abonnement MRR",
            "drops quotidiens",
            "Auto-Factory feed",
            "le moat",
        ],
    ),
]
colw = (W - 100 - 4 * 16) // 5
col_h = 360
for i, (title, col, items) in enumerate(cols):
    x0 = 50 + i * (colw + 16)
    x1 = x0 + colw
    rrect((x0, y, x1, y + col_h), 14, fill=CARD, outline=col, width=3)
    rrect((x0, y, x1, y + 50), 14, fill=col)
    d.rectangle((x0, y + 30, x1, y + 50), fill=col)
    center(title, x0, x1, y + 10, f_card_t, (14, 17, 23))
    yy = y + 66
    for it in items:
        bold = it.startswith("MEGA") or it.startswith("=") or "FLAGSHIP" in it
        fnt = f_small
        fill = col if bold else WHITE
        for ln in wrap(it, fnt, colw - 28):
            d.text((x0 + 16, yy), ln, font=fnt, fill=fill)
            yy += 30
        yy += 6
y += col_h + 40

# ---- SECTION: OPTIMIZATION LOOP ----
d.text((50, y), "4 · L'OPTIMISATION  —  build once, sell at every altitude", font=f_h2, fill=WHITE)
y += 60
loop = [
    "Auto-Factory\ngenere des ATOMES",
    "recompose.py\nrezippe les bundles",
    "metadata_gen\nSEO titre+tags",
    "Etsy / Gumroad\nlisting + cover",
    "VAULT\nse met a jour",
]
lw = (W - 100 - 4 * 50) // 5
for i, step in enumerate(loop):
    x0 = 50 + i * (lw + 50)
    x1 = x0 + lw
    rrect((x0, y, x1, y + 120), 14, fill=CARD, outline=C_GUIDE, width=3)
    lines = step.split("\n")
    center(lines[0], x0, x1, y + 30, f_item, WHITE)
    center(lines[1], x0, x1, y + 64, f_small, MUTE)
    if i < len(loop) - 1:
        ay = y + 60
        d.line((x1 + 8, ay, x1 + 42, ay), fill=C_GUIDE, width=4)
        d.polygon([(x1 + 34, ay - 9), (x1 + 34, ay + 9), (x1 + 46, ay)], fill=C_GUIDE)
y += 150

center(
    "Tu n'ecris QUE l'atome. Bundles / Mega / Vault = listes d'atomes recompilees automatiquement.",
    0,
    W,
    y,
    f_item,
    C_VAULT,
)

out = Path(r"C:\Users\bobby\OneDrive\Bureau\Jarvis\AI_PRODUCT_EMPIRE_SCHEMA.png")
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out, "PNG")
print("saved:", out, img.size)
