"""Big weekly/monthly brain-report tasks, split out of daily_tasks.py.
Moved verbatim — referenced by daily_tasks.create_scheduler()."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from daily_tasks_common import BACKEND_DIR, _write_skill_brain_note, logger

__all__ = ['task_weekly_vault_growth', 'task_daily_brain_stubs_check',
           'task_monthly_repo_audit', 'task_monthly_brain_snapshot']


async def task_weekly_vault_growth():
    """Weekly Sunday 20:00 — vault growth & health report.

    Counts notes added / modified in the last 7 days, top tags, orphans,
    largest sub-folders, and writes a markdown brief to the brain. The
    completion event surfaces in RightPanel ALERTS & EVENTS with a
    clickable obsidian:// deep-link to the report."""
    import re
    from collections import Counter
    from datetime import timedelta

    brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
    if not brain_root.exists():
        logger.warning("task_weekly_vault_growth: BRAIN/ not found, skipping")
        _write_skill_brain_note(
            "vault-growth-report", "report",
            "# Vault Growth Report\n\n**Status**: BRAIN/ vault not found on disk.\n",
            "weekly",
        )
        return

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    today = now.date()

    total = 0
    added_this_week  = 0
    modif_this_week  = 0
    by_day: Counter[str] = Counter()
    by_tag: Counter[str] = Counter()
    by_folder: Counter[str] = Counter()
    orphan_count = 0
    recent_notes: list[tuple[datetime, str]] = []
    tag_pattern = re.compile(r"(?:^|[\s,])#([a-zA-Z][\w-]*)")
    link_pattern = re.compile(r"\[\[([^\]]+)\]\]")

    try:
        for md in brain_root.rglob("*.md"):
            if any(p in md.parts for p in (".obsidian", ".trash", "node_modules")):
                continue
            total += 1
            try:
                stat = md.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                ctime = datetime.fromtimestamp(stat.st_ctime)
                rel_folder = md.relative_to(brain_root).parts[0] if md.relative_to(brain_root).parts else "(root)"
                by_folder[rel_folder] += 1

                # Read once for tags + backlinks. Skip files > 256 KB
                # (paste dumps etc.) so the report stays fast.
                if stat.st_size < 262144:
                    content = md.read_text(encoding="utf-8", errors="ignore")
                    for m in tag_pattern.finditer(content):
                        by_tag[m.group(1).lower()] += 1
                    if not link_pattern.search(content):
                        orphan_count += 1

                if ctime >= week_ago:
                    added_this_week += 1
                if mtime >= week_ago and mtime != ctime:
                    modif_this_week += 1
                if mtime >= week_ago:
                    by_day[mtime.strftime("%Y-%m-%d")] += 1
                    recent_notes.append((mtime, str(md.relative_to(brain_root)).replace("\\", "/")))
            except Exception:                                         # noqa: BLE001 - per-file errors must not kill the loop
                continue
    except Exception as e:                                            # noqa: BLE001
        logger.error(f"task_weekly_vault_growth: scan failed: {e}")

    recent_notes.sort(reverse=True)
    week_iso = today.strftime("%G-W%V")

    def _bar(value: int, top: int, width: int = 24) -> str:
        if top <= 0:
            return ""
        filled = int(round(width * value / top))
        return "█" * filled + "·" * (width - filled)

    # Daily activity sparkline-ish bar chart (last 7 days)
    day_chart_lines = []
    top_day = max(by_day.values(), default=0)
    for delta in range(6, -1, -1):
        d = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
        n = by_day.get(d, 0)
        day_chart_lines.append(f"  {d}  {n:>3}  {_bar(n, top_day, 30)}")

    top_tags    = by_tag.most_common(10)
    top_folders = by_folder.most_common(8)

    body_lines: list[str] = [
        f"# Vault Growth Report · week {week_iso}",
        "",
        f"_Generated automatically Sunday 20:00 · run_at: {now.isoformat(timespec='seconds')}_",
        "",
        "## Headline",
        f"- **Total notes** in vault: **{total}**",
        f"- **Added this week**: **{added_this_week}**",
        f"- **Modified this week**: **{modif_this_week}**",
        f"- **Orphan notes** (no `[[backlinks]]`): **{orphan_count}**  "
        f"({(orphan_count / total * 100) if total else 0:.1f}% of vault)",
        "",
        "## Daily activity (last 7 days)",
        "```",
        *day_chart_lines,
        "```",
        "",
        "## Top tags",
    ]
    if top_tags:
        for tag, n in top_tags:
            body_lines.append(f"- `#{tag}` — {n}")
    else:
        body_lines.append("- _(no `#tags` detected)_")
    body_lines.extend([
        "",
        "## Top folders",
    ])
    for folder, n in top_folders:
        body_lines.append(f"- `{folder}/` — {n} notes")

    body_lines.extend(["", "## 10 most recently touched notes"])
    for mtime, rel in recent_notes[:10]:
        body_lines.append(f"- `{mtime.strftime('%Y-%m-%d %H:%M')}` · `{rel}`")

    body_lines.extend([
        "",
        "## Health flags",
    ])
    if total == 0:
        body_lines.append("- ⚠️ Vault is empty")
    if orphan_count > total * 0.30 and total > 20:
        body_lines.append(
            f"- ⚠️ Orphan ratio > 30 % ({orphan_count}/{total}) — consider running brain-autolink"
        )
    if added_this_week == 0 and modif_this_week == 0:
        body_lines.append("- ⚠️ No vault activity this week")
    if not [ln for ln in body_lines if ln.startswith("- ⚠️")]:
        body_lines.append("- ✅ All clear")

    body = "\n".join(body_lines) + "\n"
    _write_skill_brain_note("vault-growth-report", "report", body, "weekly")


async def task_daily_brain_stubs_check():
    """Daily 22:00 — list vault notes that look like stubs (empty body,
    `stub: true` in frontmatter, or under 100 chars of content). Output
    is a brain note + WS event so the RightPanel surfaces it.

    Heuristic for "stub":
      - explicit `stub: true` in YAML frontmatter, or
      - explicit `tags: [stub]` / `tags: [..., stub, ...]`, or
      - body (post-frontmatter) shorter than 100 non-blank characters.
    """
    import re
    brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
    if not brain_root.exists():
        _write_skill_brain_note(
            "brain-stubs-check", "report",
            "# Brain Stubs Check\n\n**Status**: BRAIN/ not found.\n", "daily",
        )
        return

    stubs: list[tuple[str, str]] = []   # (relative_path, reason)
    scanned = 0
    fm_re   = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)

    try:
        for md in brain_root.rglob("*.md"):
            if any(p in md.parts for p in (".obsidian", ".trash", "node_modules", "_snapshots")):
                continue
            scanned += 1
            try:
                if md.stat().st_size > 524288:   # > 512 KB → not a stub
                    continue
                content = md.read_text(encoding="utf-8", errors="ignore")
                rel = str(md.relative_to(brain_root)).replace("\\", "/")

                # Strip frontmatter
                fm_match = fm_re.match(content)
                frontmatter = fm_match.group(1) if fm_match else ""
                body = content[fm_match.end():] if fm_match else content

                # Explicit stub markers
                if re.search(r"^\s*stub\s*:\s*true\b", frontmatter, re.MULTILINE | re.IGNORECASE):
                    stubs.append((rel, "frontmatter `stub: true`"))
                    continue
                tags_match = re.search(r"^\s*tags\s*:\s*\[([^\]]*)\]", frontmatter, re.MULTILINE | re.IGNORECASE)
                if tags_match and re.search(r"\bstub\b", tags_match.group(1), re.IGNORECASE):
                    stubs.append((rel, "tag `stub`"))
                    continue

                # Body length heuristic — strip blank lines + markdown noise
                lean = re.sub(r"^\s*#+ .*$", "", body, flags=re.MULTILINE)   # headings
                lean = re.sub(r"\s+", " ", lean).strip()
                if len(lean) < 100:
                    stubs.append((rel, f"body < 100 chars ({len(lean)})"))
            except Exception:                                                  # noqa: BLE001
                continue
    except Exception as e:                                                     # noqa: BLE001
        logger.error(f"task_daily_brain_stubs_check: scan failed: {e}")

    body_lines = [
        f"# Brain Stubs Check · daily {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"_Scanned {scanned} notes — found **{len(stubs)} stubs** to fill in._",
        "",
    ]
    if not stubs:
        body_lines.append("## ✅ No stubs detected — vault is fully fleshed out")
    else:
        # Top 30 — anything more is noise in the daily ping
        body_lines.append("## Notes flagged (top 30)")
        for rel, reason in stubs[:30]:
            body_lines.append(f"- `{rel}` — {reason}")
        if len(stubs) > 30:
            body_lines.append(f"- _… +{len(stubs) - 30} more_")

    body = "\n".join(body_lines) + "\n"
    _write_skill_brain_note("brain-stubs-check", "report", body, "daily")


async def task_monthly_repo_audit():
    """Monthly 1st 03:00 — repo health audit: LOC by language, test count,
    outdated dependencies (npm + pip). Writes a brain note for trend
    tracking (compare against last month's report by hand)."""
    import asyncio as _aio
    import subprocess
    repo_root = BACKEND_DIR.parent

    # ── LOC count by extension (backend Python + frontend TS) ───────────
    loc_by_ext: dict[str, int] = {}
    file_count_by_ext: dict[str, int] = {}
    scope = [
        ("backend",  ".py"),
        ("frontend/src", ".ts"),
        ("frontend/src", ".tsx"),
        ("frontend/src", ".css"),
    ]
    skip_parts = {".venv", "node_modules", "__pycache__", "dist", "build", ".vite"}
    for sub, ext in scope:
        root = repo_root / sub
        if not root.exists():
            continue
        total_lines = 0
        files = 0
        for f in root.rglob(f"*{ext}"):
            if any(p in f.parts for p in skip_parts):
                continue
            try:
                total_lines += sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
                files += 1
            except Exception:                                                  # noqa: BLE001
                continue
        loc_by_ext[ext] = loc_by_ext.get(ext, 0) + total_lines
        file_count_by_ext[ext] = file_count_by_ext.get(ext, 0) + files

    # ── Test counts ─────────────────────────────────────────────────────
    py_tests = len(list((repo_root / "backend" / "tests").rglob("test_*.py"))) if (repo_root / "backend" / "tests").exists() else 0
    ts_tests = sum(1 for _ in (repo_root / "frontend" / "src").rglob("*.test.ts*")) + \
               sum(1 for _ in (repo_root / "frontend" / "src").rglob("*.spec.ts*"))

    # ── Outdated deps ───────────────────────────────────────────────────
    async def _run(cmd: list[str], cwd: Path, timeout: int = 90) -> tuple[int, str]:
        try:
            proc = await _aio.to_thread(
                subprocess.run, cmd, cwd=str(cwd),
                capture_output=True, text=True, timeout=timeout, shell=False,
            )
            return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        except Exception as e:                                                 # noqa: BLE001
            return -1, f"error: {e}"

    npm_outdated_count = 0
    npm_summary = ""
    try:
        _, npm_out = await _run(["npm", "outdated", "--json"], repo_root / "frontend", timeout=60)
        if npm_out.strip():
            data = json.loads(npm_out)
            if isinstance(data, dict):
                npm_outdated_count = len(data)
                top = sorted(data.items())[:10]
                lines = []
                for name, info in top:
                    cur = info.get("current", "?")
                    lat = info.get("latest", "?")
                    lines.append(f"  - `{name}` : `{cur}` → `{lat}`")
                npm_summary = "\n".join(lines)
                if npm_outdated_count > 10:
                    npm_summary += f"\n  - _… +{npm_outdated_count - 10} more_"
    except Exception as e:                                                     # noqa: BLE001
        npm_summary = f"  - _error parsing npm outdated: {e}_"

    pip_outdated_count = 0
    pip_summary = ""
    try:
        venv_python = repo_root / "backend" / ".venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = Path("python")
        _, pip_out = await _run([str(venv_python), "-m", "pip", "list", "--outdated", "--format=json"], repo_root, timeout=120)
        if pip_out.strip():
            data = json.loads(pip_out)
            if isinstance(data, list):
                pip_outdated_count = len(data)
                top = sorted(data, key=lambda d: d.get("name", ""))[:10]
                lines = []
                for d in top:
                    name = d.get("name", "?")
                    cur  = d.get("version", "?")
                    lat  = d.get("latest_version", "?")
                    lines.append(f"  - `{name}` : `{cur}` → `{lat}`")
                pip_summary = "\n".join(lines)
                if pip_outdated_count > 10:
                    pip_summary += f"\n  - _… +{pip_outdated_count - 10} more_"
    except Exception as e:                                                     # noqa: BLE001
        pip_summary = f"  - _error parsing pip outdated: {e}_"

    # ── Compose report ──────────────────────────────────────────────────
    total_loc = sum(loc_by_ext.values())
    total_files = sum(file_count_by_ext.values())
    body_lines = [
        f"# Monthly Repo Audit · {datetime.now().strftime('%Y-%m')}",
        "",
        "_Generated automatically 1st of month 03:00 — compare with previous month's note in `02_Daily/`._",
        "",
        "## Codebase size",
        f"- **Total LOC** (source files): **{total_loc:,}**",
        f"- **Total source files**: **{total_files}**",
        "",
    ]
    for ext in sorted(loc_by_ext):
        body_lines.append(f"- `{ext}` : {loc_by_ext[ext]:,} lines across {file_count_by_ext[ext]} files")
    body_lines.extend([
        "",
        "## Tests",
        f"- Backend `pytest` files: **{py_tests}**",
        f"- Frontend `*.test.ts*` / `*.spec.ts*`: **{ts_tests}**",
        f"- **Combined**: {py_tests + ts_tests} test files",
        "",
        "## Dependencies",
        f"- **npm outdated**: **{npm_outdated_count}**",
    ])
    if npm_summary:
        body_lines.append(npm_summary)
    body_lines.extend([
        "",
        f"- **pip outdated**: **{pip_outdated_count}**",
    ])
    if pip_summary:
        body_lines.append(pip_summary)
    body_lines.extend(["", "## Health flags"])
    if npm_outdated_count > 30:
        body_lines.append(f"- ⚠️ npm has {npm_outdated_count} outdated deps — bulk upgrade overdue")
    if pip_outdated_count > 30:
        body_lines.append(f"- ⚠️ pip has {pip_outdated_count} outdated deps — bulk upgrade overdue")
    if py_tests + ts_tests < 20:
        body_lines.append(f"- ⚠️ Test count low ({py_tests + ts_tests}) — coverage hasn't grown")
    if not [ln for ln in body_lines if ln.startswith("- ⚠️")]:
        body_lines.append("- ✅ All clear")

    body = "\n".join(body_lines) + "\n"
    _write_skill_brain_note("monthly-repo-audit", "report", body, "monthly")


async def task_monthly_brain_snapshot():
    """Monthly 1st 04:00 — tarball snapshot of BRAIN/BRAIN/ outside the
    repo to survive accidental `rm -rf` / vault corruption. Keeps the
    last 6 snapshots rolling (older ones auto-pruned)."""
    import tarfile
    brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
    if not brain_root.exists():
        _write_skill_brain_note(
            "monthly-brain-snapshot", "report",
            "# Monthly Brain Snapshot\n\n**Status**: BRAIN/ not found.\n", "monthly",
        )
        return

    # Snapshots live OUTSIDE the repo so a `git clean -fdx` doesn't wipe
    # them. ~/.nexus9/brain-snapshots/ works on Windows + Unix.
    out_root = Path.home() / ".nexus9" / "brain-snapshots"
    out_root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m")
    archive_path = out_root / f"brain-{stamp}.tar.gz"

    skipped_dirs = {".obsidian", ".trash", "node_modules", "_snapshots"}
    files_archived = 0
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            for md in brain_root.rglob("*"):
                if md.is_dir():
                    continue
                if any(p in md.parts for p in skipped_dirs):
                    continue
                try:
                    tar.add(md, arcname=str(md.relative_to(brain_root)))
                    files_archived += 1
                except Exception:                                              # noqa: BLE001
                    continue
        archive_size_mb = archive_path.stat().st_size / 1024 / 1024
    except Exception as e:                                                     # noqa: BLE001
        logger.error(f"task_monthly_brain_snapshot: failed to write archive: {e}")
        _write_skill_brain_note(
            "monthly-brain-snapshot", "report",
            f"# Monthly Brain Snapshot\n\n**Status**: FAILED — `{e}`\n", "monthly",
        )
        return

    # Rotate — keep last 6 snapshots
    snapshots = sorted(out_root.glob("brain-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed: list[str] = []
    for old in snapshots[6:]:
        try:
            old.unlink()
            removed.append(old.name)
        except Exception:                                                      # noqa: BLE001
            continue

    body_lines = [
        f"# Monthly Brain Snapshot · {stamp}",
        "",
        "_Generated automatically 1st of month 04:00._",
        "",
        "## Archive",
        f"- **Path**: `{archive_path}`",
        f"- **Files archived**: {files_archived}",
        f"- **Size**: {archive_size_mb:.1f} MB",
        "",
        "## Rotation",
        f"- Snapshots kept: {min(len(snapshots), 6)}",
    ]
    if removed:
        body_lines.append(f"- Removed (rolling 6-month window): {', '.join(removed)}")
    body_lines.extend([
        "",
        "## Restore",
        "If you ever need to restore this snapshot:",
        "```pwsh",
        f"tar -xzf '{archive_path}' -C 'C:/OpenJarvisNexus/backend/BRAIN/BRAIN/'",
        "```",
        "",
    ])

    _write_skill_brain_note("monthly-brain-snapshot", "report", "\n".join(body_lines), "monthly")
