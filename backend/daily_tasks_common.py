"""Shared primitives for the daily-task modules (split from daily_tasks.py
to keep file sizes sane and avoid circular imports)."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("nexus9.daily")
BACKEND_DIR = Path(__file__).parent


def _write_skill_brain_note(
    skill_name: str,
    kind: str,
    body: str,
    when: str = "daily",
) -> Path | None:
    """Write a skill-run report to BRAIN/02_Daily/<today>/skill-<name>.md and
    publish a completion event in the EventHub so the RightPanel shows it
    live with a clickable note link.

    Returns the path (or None if BRAIN_DIR isn't writable, which we never
    raise on — scheduled jobs must not crash the scheduler).
    """
    note_path: Path | None = None
    relative_note: str | None = None
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
        day_dir = brain_root / "02_Daily" / today
        day_dir.mkdir(parents=True, exist_ok=True)
        note_path = day_dir / f"skill-{skill_name}.md"
        relative_note = f"02_Daily/{today}/skill-{skill_name}.md"
        front_matter = (
            "---\n"
            f"nexus9_skill: {skill_name}\n"
            f"nexus9_kind: {kind}\n"
            f"nexus9_schedule: {when}\n"
            f"nexus9_run_at: {datetime.now().isoformat(timespec='seconds')}\n"
            f"tags: [skill-run, {skill_name}, automated]\n"
            f"related: [[../../05_Resources/Research/hermes/{skill_name}]]\n"
            "---\n\n"
        )
        note_path.write_text(front_matter + body, encoding="utf-8")
    except Exception as e:
        logger.error(f"Skill brain note write failed for {skill_name}: {e}")
        return None

    # Publish a completion event — fire-and-forget so a publish failure
    # never crashes the scheduler loop.
    try:
        import asyncio as _aio

        from ws_router import hub
        evt = {
            "level":  "info",
            "source": "SKILL",
            "msg":    f"{skill_name} · {when} complete",
            "note":   relative_note,
            "skill":  skill_name,
        }
        try:
            loop = _aio.get_running_loop()   # py3.12: get_event_loop() raises if no loop
            loop.create_task(hub.publish(evt))
        except RuntimeError:
            _aio.run(hub.publish(evt))
    except Exception as e:
        logger.debug(f"Event publish failed for {skill_name}: {e}")

    return note_path
