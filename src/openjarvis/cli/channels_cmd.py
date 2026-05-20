"""``jarvis channels`` — manage messaging channels for the agent."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

_TELEGRAM_PID_FILE = str(Path.home() / ".openjarvis" / "telegram-agent.pid")


@click.group("channels")
def channels() -> None:
    """Manage messaging channels (iMessage/SMS via SendBlue, Slack)."""


@channels.command("status")
def channels_status() -> None:
    """Show status of all configured channels."""
    from openjarvis.channels.imessage_daemon import is_running

    console = Console()
    table = Table(title="Channel Status")
    table.add_column("Channel", style="bold")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    if is_running():
        table.add_row("iMessage", "[green]running[/green]", "Polling chat.db")
    else:
        table.add_row("iMessage", "[dim]stopped[/dim]", "jarvis channels imessage-start <contact>")

    if _telegram_is_running():
        table.add_row("Telegram", "[green]running[/green]", "Long polling active")
    else:
        table.add_row("Telegram", "[dim]stopped[/dim]", "jarvis channels telegram-start")

    console.print(table)


@channels.command("imessage-start")
@click.argument("chat_identifier")
@click.option(
    "--background/--foreground",
    default=True,
    help="Run in background.",
)
def imessage_start(
    chat_identifier: str,
    background: bool,
) -> None:
    """Start the iMessage daemon for CHAT_IDENTIFIER.

    CHAT_IDENTIFIER is the phone number or email to monitor.
    """
    from openjarvis.channels.imessage_daemon import (
        is_running,
        run_daemon,
    )

    console = Console()

    if is_running():
        console.print("[yellow]iMessage daemon already running.[/yellow]")
        return

    if background:
        import subprocess

        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "openjarvis.channels.imessage_daemon",
                "--chat",
                chat_identifier,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        console.print(
            f"[green]iMessage daemon started[/green] "
            f"(PID {proc.pid})\n"
            f"Monitoring: {chat_identifier}\n"
            "Text this contact from your iPhone "
            "to chat with the agent."
        )
    else:
        console.print(
            f"[green]Starting iMessage daemon[/green] — monitoring {chat_identifier}"
        )
        console.print("Press Ctrl+C to stop.\n")

        from openjarvis.agents.deep_research import (
            DeepResearchAgent,
        )
        from openjarvis.connectors.retriever import (
            TwoStageRetriever,
        )
        from openjarvis.connectors.store import KnowledgeStore
        from openjarvis.engine.ollama import OllamaEngine
        from openjarvis.tools.knowledge_search import (
            KnowledgeSearchTool,
        )
        from openjarvis.tools.knowledge_sql import (
            KnowledgeSQLTool,
        )
        from openjarvis.tools.scan_chunks import ScanChunksTool
        from openjarvis.tools.think import ThinkTool

        engine = OllamaEngine()
        store = KnowledgeStore()
        retriever = TwoStageRetriever(store)
        tools = [
            KnowledgeSearchTool(retriever=retriever),
            KnowledgeSQLTool(store=store),
            ScanChunksTool(
                store=store,
                engine=engine,
                model="qwen3.5:4b",
            ),
            ThinkTool(),
        ]
        agent = DeepResearchAgent(
            engine=engine,
            model="qwen3.5:4b",
            tools=tools,
        )

        def handler(text: str) -> str:
            result = agent.run(text)
            return result.content or "No results found."

        run_daemon(
            chat_identifier=chat_identifier,
            handler=handler,
        )


@channels.command("imessage-stop")
def imessage_stop() -> None:
    """Stop the iMessage daemon."""
    from openjarvis.channels.imessage_daemon import stop_daemon

    console = Console()
    if stop_daemon():
        console.print("[green]iMessage daemon stopped.[/green]")
    else:
        console.print("[dim]iMessage daemon is not running.[/dim]")


def _telegram_is_running() -> bool:
    """Return True if a background Telegram daemon PID file exists and the process is alive."""
    pid_path = Path(_TELEGRAM_PID_FILE)
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        pid_path.unlink(missing_ok=True)
        return False


def _run_telegram_foreground(bot_token: str, allowed_chat_ids: str, parse_mode: str) -> None:
    """Start the Telegram bot in the foreground, blocking until Ctrl+C."""
    import time

    from openjarvis.agents.channel_agent import ChannelAgent
    from openjarvis.agents.simple import SimpleAgent
    from openjarvis.channels.telegram import TelegramChannel
    from openjarvis.core.config import load_config
    from openjarvis.engine._discovery import get_engine

    console = Console()
    config = load_config()

    result = get_engine(config)
    if result is None:
        console.print(
            "[red]No inference engine is running.[/red]\n"
            "Start Ollama or another engine first, then retry."
        )
        return

    engine_key, engine = result
    model = config.intelligence.default_model or ""
    agent = SimpleAgent(engine=engine, model=model)

    ch = TelegramChannel(
        bot_token=bot_token,
        allowed_chat_ids=allowed_chat_ids,
        parse_mode=parse_mode,
    )
    ChannelAgent(ch, agent)
    ch.connect()

    if ch.status().value != "connected":
        console.print("[red]Failed to connect. Check your bot token.[/red]")
        return

    console.print(f"[green]Telegram bot connected[/green] (engine: {engine_key})")
    console.print("Send a message to your bot on Telegram. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        console.print("\n[yellow]Stopping Telegram bot...[/yellow]")
        ch.disconnect()
        console.print("[green]Stopped.[/green]")


@channels.command("telegram-start")
@click.option(
    "--token",
    default="",
    envvar="TELEGRAM_BOT_TOKEN",
    help="Telegram Bot API token (or set TELEGRAM_BOT_TOKEN env var).",
)
@click.option(
    "--allowed-chats",
    default="",
    help="Comma-separated chat IDs allowed to interact (empty = allow all).",
)
@click.option(
    "--background/--foreground",
    default=True,
    help="Run in background (default) or foreground.",
)
def telegram_start(token: str, allowed_chats: str, background: bool) -> None:
    """Start the Telegram bot and connect it to the AI agent.

    Requires a bot token from @BotFather.  Set it in your config:

    \b
      [channel.telegram]
      bot_token = "YOUR_TOKEN"

    Or pass --token / set TELEGRAM_BOT_TOKEN.
    """
    from openjarvis.core.config import load_config

    console = Console()

    if _telegram_is_running():
        console.print("[yellow]Telegram bot is already running.[/yellow]")
        return

    config = load_config()
    bot_token = token or config.channel.telegram.bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")

    if not bot_token:
        console.print(
            "[red]No Telegram bot token found.[/red]\n\n"
            "Add it to your config (~/.openjarvis/config.toml):\n\n"
            "  [channel.telegram]\n"
            '  bot_token = "YOUR_TOKEN"\n\n'
            "Or run:  jarvis channels telegram-start --token YOUR_TOKEN\n"
            "Or set:  TELEGRAM_BOT_TOKEN=YOUR_TOKEN"
        )
        return

    allowed_ids = allowed_chats or config.channel.telegram.allowed_chat_ids
    parse_mode = config.channel.telegram.parse_mode or "Markdown"

    if background:
        import subprocess

        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "openjarvis.cli.__main__",
                "channels",
                "telegram-start",
                "--foreground",
                "--token",
                bot_token,
                *(["--allowed-chats", allowed_ids] if allowed_ids else []),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        Path(_TELEGRAM_PID_FILE).write_text(str(proc.pid))
        console.print(
            f"[green]Telegram bot started[/green] (PID {proc.pid})\n"
            "Message your bot on Telegram to chat with the agent.\n"
            "Stop with:  jarvis channels telegram-stop"
        )
    else:
        _run_telegram_foreground(bot_token, allowed_ids, parse_mode)


@channels.command("telegram-stop")
def telegram_stop() -> None:
    """Stop the background Telegram bot daemon."""
    import signal

    console = Console()
    pid_path = Path(_TELEGRAM_PID_FILE)

    if not _telegram_is_running():
        console.print("[dim]Telegram bot is not running.[/dim]")
        return

    try:
        pid = int(pid_path.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_path.unlink(missing_ok=True)
        console.print("[green]Telegram bot stopped.[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to stop Telegram bot: {exc}[/red]")
