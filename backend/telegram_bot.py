"""
Jarvis Telegram Bot v2.0
- Monitoring proactif du système
- Alertes automatiques si backend tombe
- Jarvis connaît l'état réel du système
- Commandes avancées
"""

import asyncio
import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv(override=True)

BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
AUTH_USER   = int(os.getenv("TELEGRAM_AUTHORIZED_USER_ID", "0"))
BACKEND_URL = f"http://localhost:{os.getenv('BACKEND_PORT', 8000)}"
CHECK_EVERY = 300  # 5 minutes en secondes

logging.basicConfig(
    format="%(asctime)s │ %(levelname)s │ %(message)s",
    level=logging.INFO
)
log = logging.getLogger("jarvis-telegram")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN manquant dans .env")

# ── État voix ────────────────────────────────────────────
_voice_enabled: bool = False
_background_tasks: set = set()
TTS_VOICE = "fr-FR-HenriNeural"  # Voix Microsoft Neural française

# ── Cache état du système ───────────────────────────────
system_state = {
    "backend_online": False,
    "ollama_online":  False,
    "claude_model":   "inconnu",
    "ollama_model":   "inconnu",
    "last_check":     None,
    "alerts":         [],
}


def is_authorized(update: Update) -> bool:
    return update.effective_user.id == AUTH_USER


# ── Appels API backend ──────────────────────────────────
def get_backend_status() -> dict | None:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_memory() -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/v1/memory", timeout=5)
        return r.json()
    except Exception:
        return {}


def ask_jarvis(message: str, session: str = "telegram") -> str:
    """Appelle Jarvis — injecte l'état système dans le contexte."""
    state_context = (
        f"\n\n[ÉTAT SYSTÈME TEMPS RÉEL]\n"
        f"Backend: {'EN LIGNE' if system_state['backend_online'] else 'HORS LIGNE'}\n"
        f"Ollama: {'EN LIGNE' if system_state['ollama_online'] else 'HORS LIGNE'}\n"
        f"Claude: {system_state['claude_model']}\n"
        f"Ollama modèle: {system_state['ollama_model']}\n"
        f"Dernière vérification: {system_state['last_check']}\n"
        f"Tu peux répondre en te basant sur cet état réel."
    )
    try:
        r = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json={
                "message":    message + state_context,
                "session_id": session,
                "stream":     False,
                "max_tokens": 800,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.Timeout:
        return "⏳ Jarvis met du temps à répondre..."
    except Exception as e:
        return f"❌ Erreur: {e}"


async def send_voice_message(update: Update, text: str) -> None:
    """Voice reply via the BACKEND TTS so Telegram matches JARVIS's main voice
    (Kokoro bm_george for English, Edge French for French) instead of a separate
    local Edge voice. Falls back to reply_audio if Telegram rejects the format."""
    import io
    clean = text[:800].replace("*", "").replace("_", "").replace("`", "")
    if not clean:
        return
    try:
        r = await asyncio.to_thread(
            requests.get, f"{BACKEND_URL}/v1/tts",
            params={"text": clean}, timeout=90,
        )
        r.raise_for_status()
        data = r.content
        try:
            await update.message.reply_voice(io.BytesIO(data))
        except Exception:
            # WAV/MP3 may be refused as a "voice"; send as an audio clip instead.
            await update.message.reply_audio(io.BytesIO(data))
    except Exception as e:
        log.warning(f"TTS backend échoué: {e}")


def run_diagnostics() -> str:
    """Diagnostic complet du système."""
    lines = ["🔍 **DIAGNOSTIC NEXUSX9**\n"]
    status = get_backend_status()
    if status:
        lines.append(f"✅ Backend: EN LIGNE (v{status.get('version','?')})")
        lines.append(f"🧠 Claude: `{status.get('claude_model','?')}`")
        if status.get("ollama_online"):
            lines.append(f"💻 Ollama: EN LIGNE → `{status.get('ollama_model','?')}`")
        else:
            lines.append("⚠️ Ollama: HORS LIGNE (lance: `ollama serve`)")
    else:
        lines.append("❌ Backend: HORS LIGNE")
        lines.append("  → Lance: `python main.py`")
        lines.append("  → Dossier: `C:\\OpenJarvisNexus\\backend`")

    memory = get_memory()
    facts  = memory.get("facts", {})
    if facts.get("user_name"):
        lines.append(f"\n🧠 Mémoire: chargée pour {facts['user_name']}")
        lines.append(f"📁 Projets: {len(facts.get('projects', []))} enregistrés")
    else:
        lines.append("\n⚠️ Mémoire: aucun fait chargé")

    sessions = memory.get("sessions", [])
    lines.append(f"💬 Sessions actives: {len(sessions)}")
    lines.append(f"\n🕐 Check: {datetime.now().strftime('%H:%M:%S')}")
    return "\n".join(lines)


def run_crew(mission: str) -> str:
    try:
        r = requests.post(
            f"{BACKEND_URL}/v1/crew/run",
            json={"mission": mission, "mission_type": "auto"},
            timeout=300,
        )
        r.raise_for_status()
        d = r.json()
        agents   = ", ".join(d.get("agents_used", []))
        duration = d.get("duration_s", 0)
        result   = str(d.get("result", "Pas de résultat"))[:2000]
        return f"✅ *Mission terminée en {duration}s*\n👥 {agents}\n\n{result}"
    except requests.Timeout:
        return "⏳ Mission longue — vérifie les logs backend."
    except Exception as e:
        return f"❌ Erreur crew: {e}"


# ── Monitoring proactif ─────────────────────────────────
async def monitor_system(app: Application) -> None:
    """Vérifie le système toutes les 5 min et alerte si problème."""
    was_online = True
    while True:
        await asyncio.sleep(CHECK_EVERY)
        status = get_backend_status()
        now    = datetime.now().strftime("%H:%M")
        system_state["last_check"] = now

        if status:
            system_state["backend_online"] = True
            system_state["ollama_online"]  = status.get("ollama_online", False)
            system_state["claude_model"]   = status.get("claude_model", "?")
            system_state["ollama_model"]   = status.get("ollama_model", "?")
            if not was_online:
                was_online = True
                if AUTH_USER:
                    await app.bot.send_message(
                        AUTH_USER,
                        "✅ Backend revenu en ligne !",
                        parse_mode=ParseMode.MARKDOWN
                    )
            if not status.get("ollama_online"):
                if AUTH_USER:
                    await app.bot.send_message(
                        AUTH_USER,
                        "⚠️ Ollama est hors ligne.\nLance: `ollama serve`",
                        parse_mode=ParseMode.MARKDOWN
                    )
        else:
            system_state["backend_online"] = False
            if was_online:
                was_online = False
                if AUTH_USER:
                    await app.bot.send_message(
                        AUTH_USER,
                        "🔴 *ALERTE* — Backend hors ligne !\nLance: `python main.py`",
                        parse_mode=ParseMode.MARKDOWN
                    )


# ── Commandes ───────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ Accès refusé.")
        return
    status = get_backend_status()
    system_state["backend_online"] = bool(status)
    if status:
        system_state["last_check"]   = datetime.now().strftime("%H:%M")
        system_state["claude_model"] = status.get("claude_model", "?")
        system_state["ollama_online"]= status.get("ollama_online", False)
        system_state["ollama_model"] = status.get("ollama_model", "?")

    keyboard = [
        [InlineKeyboardButton("📊 Statut",    callback_data="status")],
        [InlineKeyboardButton("🧠 Mémoire",   callback_data="memory")],
        [InlineKeyboardButton("🔍 Diagnostic",callback_data="diag")],
        [InlineKeyboardButton("🗑️ Clear",     callback_data="clear")],
    ]
    await update.message.reply_text(
        f"🤖 *Jarvis NexusX9 en ligne*\n\n"
        f"Backend: {'✅' if status else '❌'}\n"
        f"Ollama:  {'✅' if system_state['ollama_online'] else '⚠️'}\n"
        f"Claude:  `{system_state['claude_model']}`\n\n"
        "Commandes:\n"
        "/start — ce menu\n"
        "/status — statut détaillé\n"
        "/diag — diagnostic complet\n"
        "/memory — ta mémoire\n"
        "/crew [mission] — lancer agents\n"
        "/hub — résumé hub NexusX9\n"
        "/clear — effacer session\n\n"
        "Ou envoie simplement un message 💬",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    status = get_backend_status()
    if status:
        system_state["backend_online"] = True
        system_state["last_check"] = datetime.now().strftime("%H:%M")
        online  = "✅ EN LIGNE"
        ollama  = "✅" if status.get("ollama_online") else "⚠️ HORS LIGNE"
    else:
        online  = "❌ HORS LIGNE"
        ollama  = "?"
    await update.message.reply_text(
        f"📊 *Statut NexusX9*\n\n"
        f"🔷 Backend: {online}\n"
        f"🧠 Claude: `{status.get('claude_model','?') if status else '?'}`\n"
        f"💻 Ollama: {ollama}\n"
        f"   Modèle: `{status.get('ollama_model','?') if status else '?'}`\n"
        f"📦 Version: `{status.get('version','?') if status else '?'}`\n"
        f"🕐 Vérifié: {datetime.now().strftime('%H:%M:%S')}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_diag(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(run_diagnostics(), parse_mode=ParseMode.MARKDOWN)


async def cmd_memory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    mem   = get_memory()
    facts = mem.get("facts", {})
    lines = ["🧠 *Mémoire Jarvis*\n"]
    if facts.get("user_name"):
        lines.append(f"👤 {facts['user_name']}")
    for p in facts.get("projects", [])[:3]:
        lines.append(f"📁 {p[:50]}")
    for g in facts.get("goals", [])[:2]:
        lines.append(f"🎯 {g[:50]}")
    for n in facts.get("notes", [])[:2]:
        lines.append(f"📌 {n[:50]}")
    sessions = mem.get("sessions", [])
    lines.append(f"\n💬 Sessions actives: {len(sessions)}")
    await update.message.reply_text(
        "\n".join(lines) if lines else "Aucune mémoire.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_hub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    status = get_backend_status()
    mem    = get_memory()
    facts  = mem.get("facts", {})
    lines  = [
        "🌌 *NexusX9 HUB RÉSUMÉ*\n",
        f"🔷 Backend: {'EN LIGNE' if status else 'HORS LIGNE'}",
        f"🧠 Claude: `{status.get('claude_model','?') if status else '?'}`",
        f"💻 Ollama: {'OK' if status and status.get('ollama_online') else 'HORS LIGNE'}",
        f"\n👤 Utilisateur: {facts.get('user_name','?')}",
        f"📁 Projets: {len(facts.get('projects', []))}",
        "\n🤖 Agents configurés: 8",
        "  ◈ Architecte (Claude)",
        "  ☼  Tour Claude",
        "  ✺  Laboratoire (Ollama)",
        "  ▤  Coffre Mémoire",
        "  ◐  Zone Locale (Ollama)",
        "  ⚙  Atelier Code",
        "  ◉  Surveillance",
        "  ✦  Tableau Missions",
        "\n🌐 Hub UI: http://localhost:5174",
        "🔌 API:    http://localhost:8000",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_crew(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    mission = " ".join(ctx.args) if ctx.args else ""
    if not mission:
        await update.message.reply_text(
            "Usage: `/crew [mission]`\n\nEx: `/crew analyse les tendances e-commerce pour Shopify`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    await update.message.reply_text(
        f"🚀 Mission lancée:\n_{mission}_\n\n⏳ 2-5 minutes...",
        parse_mode=ParseMode.MARKDOWN,
    )
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_crew, mission)
    for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        await asyncio.to_thread(requests.delete, f"{BACKEND_URL}/v1/memory/session/telegram", timeout=5)
        await update.message.reply_text("🗑️ Session effacée. Repartons à zéro !")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {e}")


async def cmd_voix(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Active ou désactive les réponses vocales de Jarvis."""
    global _voice_enabled
    if not is_authorized(update):
        return
    _voice_enabled = not _voice_enabled
    state = "🔊 *Voix activée* — Jarvis va parler !" if _voice_enabled else "🔇 *Voix désactivée*"
    await update.message.reply_text(state, parse_mode=ParseMode.MARKDOWN)


# ── Callback boutons inline ─────────────────────────────
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "status":  await cmd_status(update, ctx)
    elif data == "memory":await cmd_memory(update, ctx)
    elif data == "diag":  await cmd_diag(update, ctx)
    elif data == "clear": await cmd_clear(update, ctx)


# ── Messages texte ──────────────────────────────────────
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ Accès refusé.")
        return
    msg = update.message.text
    log.info(f"Message: {msg[:60]}")
    # Track activity for /v1/world/cards/snapshot (TELEGRAM ACTIVITY card)
    try:
        from datetime import datetime as _dt

        from app_state import _telegram_state
        today = _dt.now().strftime("%Y-%m-%d")
        if _telegram_state.get("today_date") != today:
            _telegram_state["today_date"] = today
            _telegram_state["messages_today"] = 0
        _telegram_state["messages_today"] = int(_telegram_state.get("messages_today", 0)) + 1
        _telegram_state["last_message_ts"] = _dt.now()
        _telegram_state["last_user_text"] = msg[:120]
    except Exception:
        pass
    await update.message.chat.send_action("typing")
    loop  = asyncio.get_event_loop()
    reply = await loop.run_in_executor(None, ask_jarvis, msg, "telegram")
    for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
        await update.message.reply_text(chunk)
    if _voice_enabled:
        await update.message.chat.send_action("record_voice")
        await send_voice_message(update, reply)


# ── Main ────────────────────────────────────────────────
async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([
        BotCommand("start",  "Menu principal"),
        BotCommand("status", "Statut du système"),
        BotCommand("diag",   "Diagnostic complet"),
        BotCommand("memory", "Ta mémoire"),
        BotCommand("hub",    "Résumé NexusX9"),
        BotCommand("crew",   "Lancer une mission agents"),
        BotCommand("voix",   "Activer/désactiver la voix Jarvis"),
        BotCommand("clear",  "Effacer la session"),
    ])
    _t = asyncio.create_task(monitor_system(app))
    _background_tasks.add(_t)
    _t.add_done_callback(_background_tasks.discard)
    # Check initial
    status = get_backend_status()
    system_state["backend_online"] = bool(status)
    system_state["last_check"]     = datetime.now().strftime("%H:%M")
    if status:
        system_state["claude_model"]  = status.get("claude_model", "?")
        system_state["ollama_online"] = status.get("ollama_online", False)
        system_state["ollama_model"]  = status.get("ollama_model", "?")
    log.info(f"Bot prêt — backend={'OK' if status else 'KO'}")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("diag",   cmd_diag))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("hub",    cmd_hub))
    app.add_handler(CommandHandler("crew",   cmd_crew))
    app.add_handler(CommandHandler("voix",   cmd_voix))
    app.add_handler(CommandHandler("clear",  cmd_clear))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("🤖 Jarvis Telegram Bot démarré...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
