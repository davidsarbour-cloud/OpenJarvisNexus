"""
Obsidian Knowledge Auto-Linker — Nexus9 BRAIN
==============================================
Automatically:
  1. Audits vault structure (orphans, broken links, stubs, tag inconsistencies)
  2. Normalizes frontmatter tags (add folder-based expected tags, fix format)
  3. Removes duplicate inline #tags when already in frontmatter
  4. Detects implicit links (mentions without [[brackets]])
  5. Adds missing [[links]] to the Liens section of orphan notes
  6. Creates missing MOC files (moc-trading, moc-dropshipping, moc-ia)
  7. Writes a full audit report to the BRAIN

Entry point: run_autolink(dry_run=False) → dict
Exposed via: POST /v1/brain/autolink
Scheduled:  weekly Sunday 02:30 (daily_tasks.py)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger("nexus9.autolinker")

BRAIN_DIR = Path(__file__).parent / "BRAIN" / "BRAIN"

# ── Regex ─────────────────────────────────────────────────────────────────────
_FM_RE      = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_LINK_RE    = re.compile(r"\[\[([^\]|#\n]+?)(?:\|[^\]]*)?\]\]")
_ITAG_RE    = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)", re.MULTILINE)
_YTAGS_RE   = re.compile(r"^tags\s*:\s*(.+)$", re.MULTILINE)

# ── Folder → expected tags ────────────────────────────────────────────────────
FOLDER_TAGS: dict[str, list[str]] = {
    "00_Core":                  ["core"],
    "02_Daily":                 ["daily"],
    "03_Projects/Daytrading":   ["trading", "project"],
    "03_Projects/Dropshipping": ["dropshipping", "project"],
    "03_Projects/STL":          ["stl", "project"],
    "04_Areas/Finance":         ["finance", "area"],
    "04_Areas/Santé":           ["santé", "area"],
    "04_Areas/Business":        ["business", "area"],
    "05_Resources/Research":    ["research"],
    "05_Resources/MOCs":        ["moc"],
    "05_Resources/Templates":   ["template"],
    "06_Agents":                ["agent"],
    "07_Schemas":               ["schema"],
    "08_Command-Center":        ["dashboard"],
}

# ── Data structures ───────────────────────────────────────────────────────────
class NoteInfo(NamedTuple):
    path:          Path
    stem:          str          # filename without .md
    rel:           str          # relative to BRAIN_DIR, forward slashes
    raw:           str          # full file content
    frontmatter:   dict         # parsed frontmatter (best-effort)
    fm_tags:       list[str]    # tags from frontmatter
    inline_tags:   list[str]    # #tags found in body
    out_links:     list[str]    # [[targets]] found in body
    is_stub:       bool         # body is "_a remplir_" or empty
    body:          str          # content after frontmatter


# ── Frontmatter parsing ───────────────────────────────────────────────────────
def _parse_tags_value(raw_val: str) -> list[str]:
    """Parse YAML tags: [a, b] or ["a", "b"] or a, b → list of clean strings."""
    s = raw_val.strip()
    # List form: [foo, bar] or ["foo", "bar"]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1]
        tags = [t.strip().strip('"').strip("'") for t in inner.split(",")]
        return [t for t in tags if t]
    # Scalar (single tag without brackets)
    return [s.strip().strip('"').strip("'")]


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Best-effort, no external YAML dep."""
    m = _FM_RE.match(content)
    if not m:
        return {}, content
    fm_raw = m.group(1)
    body   = content[m.end():]
    fm: dict = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, body


def _extract_fm_tags(fm: dict) -> list[str]:
    tags_val = fm.get("tags", "")
    if not tags_val:
        return []
    return _parse_tags_value(tags_val)


# ── Note scanner ─────────────────────────────────────────────────────────────
def scan_vault(brain_dir: Path = BRAIN_DIR) -> dict[str, NoteInfo]:
    """Read every .md file and return {stem → NoteInfo}."""
    notes: dict[str, NoteInfo] = {}
    for path in brain_dir.rglob("*.md"):
        try:
            raw  = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        fm, body     = _parse_frontmatter(raw)
        fm_tags      = _extract_fm_tags(fm)
        inline_tags  = _ITAG_RE.findall(body)
        out_links    = [m.strip() for m in _LINK_RE.findall(raw)]
        is_stub      = "_a remplir_" in body or body.strip() in ("", "## Notes\n", "## Notes")
        rel          = path.relative_to(brain_dir).as_posix()
        stem         = path.stem

        info = NoteInfo(
            path=path, stem=stem, rel=rel, raw=raw,
            frontmatter=fm, fm_tags=fm_tags, inline_tags=inline_tags,
            out_links=out_links, is_stub=is_stub, body=body,
        )
        notes[stem] = info
    return notes


# ── Graph analysis ────────────────────────────────────────────────────────────
def build_graph(notes: dict[str, NoteInfo]) -> dict:
    """Compute orphans, broken links, backlink map."""
    all_stems = set(notes.keys())
    backlinks: dict[str, list[str]] = {s: [] for s in all_stems}
    broken:    dict[str, list[str]] = {}

    for stem, note in notes.items():
        for target in note.out_links:
            target_stem = Path(target).stem  # handle relative paths like ../../file
            if target_stem in all_stems:
                backlinks[target_stem].append(stem)
            else:
                broken.setdefault(stem, []).append(target)

    orphans = [
        stem for stem, note in notes.items()
        if not backlinks[stem] and not note.out_links
    ]
    sinks = [
        stem for stem, note in notes.items()
        if not note.out_links and backlinks[stem]  # has backlinks but links nowhere
    ]

    return {
        "backlinks": backlinks,
        "broken":    broken,
        "orphans":   orphans,
        "sinks":     sinks,
    }


# ── Expected tags by folder ───────────────────────────────────────────────────
def get_expected_tags(note: NoteInfo, brain_dir: Path = BRAIN_DIR) -> list[str]:
    rel_dir = Path(note.rel).parent.as_posix()
    for folder_pattern, tags in FOLDER_TAGS.items():
        if rel_dir == folder_pattern or rel_dir.startswith(folder_pattern + "/"):
            return tags
    return []


# ── Tag normalization ─────────────────────────────────────────────────────────
def normalize_tags(note: NoteInfo, brain_dir: Path = BRAIN_DIR) -> str | None:
    """
    Returns updated file content if changes needed, else None.
    Changes:
      - Adds missing folder-expected tags to frontmatter
      - Normalizes format: tags: [a, b, c] (no quotes)
      - Removes trailing inline #tags that duplicate frontmatter tags
    """
    expected = get_expected_tags(note, brain_dir)
    current  = set(note.fm_tags)
    to_add   = [t for t in expected if t not in current]
    all_tags = note.fm_tags + to_add

    # Build normalized tags line
    tags_line = "tags: [" + ", ".join(all_tags) + "]"

    # Check if frontmatter needs updating
    fm_match = _FM_RE.match(note.raw)
    if not fm_match:
        # No frontmatter — skip (don't add one blindly)
        return None

    fm_block = fm_match.group(1)
    new_fm_block = _YTAGS_RE.sub(tags_line, fm_block)
    if "tags:" not in fm_block:
        # No tags line in frontmatter — append one
        new_fm_block = fm_block + f"\n{tags_line}"

    if new_fm_block == fm_block and not to_add:
        return None  # Nothing changed

    # Rebuild content with updated frontmatter
    rest = note.raw[fm_match.end():]

    # Remove trailing duplicate inline #tags (only exact duplicates of frontmatter tags)
    # Pattern: last block of #tag lines at end of file
    body_lines = rest.rstrip().split("\n")
    new_lines  = list(body_lines)
    removed    = []
    # Walk backwards, strip duplicate inline tags
    i = len(new_lines) - 1
    while i >= 0 and (not new_lines[i].strip() or re.match(r"^\s*(#[a-zA-Z][a-zA-Z0-9_/-]*\s*)+$", new_lines[i])):
        line = new_lines[i].strip()
        if not line:
            i -= 1
            continue
        line_tags = [t for t in re.findall(r"#([a-zA-Z][a-zA-Z0-9_/-]*)", line)
                     if t in set(all_tags)]
        non_dup   = [t for t in re.findall(r"#([a-zA-Z][a-zA-Z0-9_/-]*)", line)
                     if t not in set(all_tags)]
        if line_tags and not non_dup:
            removed.extend(line_tags)
            new_lines.pop(i)
        i -= 1

    new_rest = "\n".join(new_lines)
    if new_rest and not new_rest.endswith("\n"):
        new_rest += "\n"

    new_content = f"---\n{new_fm_block}\n---\n{new_rest}"
    if new_content == note.raw:
        return None
    return new_content


# ── Implicit link detection ───────────────────────────────────────────────────
def find_implicit_links(note: NoteInfo, all_stems: set[str]) -> list[str]:
    """
    Find note stems mentioned in the body text WITHOUT an existing [[link]].
    Returns list of stems that should be linked.
    """
    existing_targets = {Path(l).stem for l in note.out_links}
    body_lower = note.body.lower()
    found = []
    for stem in all_stems:
        if stem == note.stem:
            continue
        if stem in existing_targets:
            continue
        # Match stem as a word/phrase (with - treated as space)
        pattern_bare  = re.escape(stem)
        pattern_space = re.escape(stem.replace("-", " "))
        if re.search(rf"\b{pattern_bare}\b", body_lower) or \
           (pattern_space != pattern_bare and re.search(rf"\b{pattern_space}\b", body_lower)):
            found.append(stem)
    return found


def add_links_to_liens_section(note: NoteInfo, new_links: list[str]) -> str | None:
    """
    Add [[links]] to the ## Liens section if they're not already there.
    Returns updated content or None if no change.
    """
    if not new_links:
        return None
    existing = {Path(l).stem for l in note.out_links}
    to_add   = [l for l in new_links if l not in existing]
    if not to_add:
        return None

    content = note.raw

    # If ## Liens section exists, deduplicate against existing content then insert
    liens_match = re.search(r"(## Liens\s*\n)((?:- \[\[.*?\]\]\n?)*)", content)
    if liens_match:
        after_section = content[liens_match.start():]
        # Remove links already present anywhere in the Liens section (list comprehension — safe)
        to_add = [l for l in to_add if f"[[{l}]]" not in after_section]
        if not to_add:
            return None
        insert_pos = liens_match.end()
        new_block  = "\n".join(f"- [[{l}]]" for l in to_add) + "\n"
        content    = content[:insert_pos] + new_block + content[insert_pos:]
    else:
        # No Liens section — append a dedicated Auto-liens block at end
        new_block = "\n".join(f"- [[{l}]]" for l in to_add)
        content   = content.rstrip() + "\n\n## Auto-liens\n" + new_block + "\n"

    return content if content != note.raw else None


# ── Missing MOC generation ────────────────────────────────────────────────────
_MOC_TEMPLATES = {
    "moc-trading": {
        "emoji": "📈",
        "title": "MOC — Trading",
        "desc":  "Map of Content : index de tout ce qui touche au day-trading dans BRAIN.",
        "sections": {
            "📐 Stratégies & Setups": [
                "[[../../03_Projects/Daytrading/setups]]",
                "[[../../05_Resources/Research/trading-strategies]]",
                "[[../../05_Resources/Research/psychologie-trading]]",
            ],
            "📔 Journal & Post-mortems": [
                "[[../../03_Projects/Daytrading/journal-trades]]",
                "[[../../03_Projects/Daytrading/post-mortems]]",
            ],
            "⚠️ Risk Management": [
                "[[../../03_Projects/Daytrading/risk-management]]",
                "[[../../03_Projects/Daytrading/watchlist]]",
            ],
            "🗺️ MOCs reliées": [
                "[[moc-finance]]",
                "[[moc-mindset]]",
            ],
        },
        "tags": ["moc", "trading"],
    },
    "moc-dropshipping": {
        "emoji": "🛒",
        "title": "MOC — Dropshipping",
        "desc":  "Map of Content : index de tout ce qui touche au dropshipping dans BRAIN.",
        "sections": {
            "🛍️ Produits": [
                "[[../../03_Projects/Dropshipping/produits-test]]",
                "[[../../03_Projects/Dropshipping/produits-validés]]",
                "[[../../03_Projects/Dropshipping/fournisseurs]]",
            ],
            "📣 Marketing": [
                "[[../../03_Projects/Dropshipping/ads-meta]]",
                "[[../../03_Projects/Dropshipping/tunnels-vente]]",
                "[[../../05_Resources/Research/marketing-frameworks]]",
                "[[../../05_Resources/Research/dropshipping-tactics]]",
            ],
            "🗺️ MOCs reliées": [
                "[[moc-finance]]",
                "[[moc-mindset]]",
            ],
        },
        "tags": ["moc", "dropshipping"],
    },
    "moc-ia": {
        "emoji": "🤖",
        "title": "MOC — IA & Outils",
        "desc":  "Map of Content : index de tout ce qui touche à l'IA, Nexus9 et les outils dans BRAIN.",
        "sections": {
            "🧠 Agents Nexus9": [
                "[[../../06_Agents/_shared/adn-commun]]",
                "[[../../06_Agents/_shared/shared-tools]]",
                "[[../../06_Agents/_shared/agents]]",
                "[[../../07_Schemas/system/system-overview]]",
                "[[../../07_Schemas/system/architecture]]",
            ],
            "🔧 Outils & Recherche": [
                "[[../../05_Resources/Research/ia-tools]]",
                "[[../../05_Resources/Research/obsidian-skills]]",
                "[[../../05_Resources/Research/superpowers]]",
            ],
            "🏗️ Architecture": [
                "[[../../07_Schemas/system/data-flow]]",
                "[[../../07_Schemas/system/design]]",
                "[[../../07_Schemas/workflows/routing]]",
            ],
            "🗺️ MOCs reliées": [
                "[[moc-finance]]",
                "[[moc-mindset]]",
            ],
        },
        "tags": ["moc", "ia", "nexus9"],
    },
    "moc-mindset": {
        "emoji": "🧠",
        "title": "MOC — Mindset & Mental Models",
        "desc":  "Map of Content : philosophie, mental models, psychologie de performance.",
        "sections": {
            "🌟 Vision & Identité": [
                "[[../../00_Core/core-vision]]",
                "[[../../00_Core/core-identité]]",
                "[[../../00_Core/core-principes]]",
                "[[../../00_Core/core-mindset]]",
            ],
            "🧩 Mental Models": [
                "[[../../07_Schemas/mental-models/first-principles]]",
                "[[../../07_Schemas/mental-models/80-20-pareto]]",
                "[[../../07_Schemas/mental-models/eisenhower-matrix]]",
                "[[../../07_Schemas/mental-models/decision-tree]]",
            ],
            "📊 Psychologie trading": [
                "[[../../05_Resources/Research/psychologie-trading]]",
            ],
            "🗺️ MOCs reliées": [
                "[[moc-finance]]",
                "[[moc-ia]]",
                "[[moc-trading]]",
            ],
        },
        "tags": ["moc", "mindset", "mental-models"],
    },
}


def _render_moc(key: str, tpl: dict, date_str: str) -> str:
    tags_yaml = "[" + ", ".join(tpl["tags"]) + "]"
    lines = [
        "---",
        f"created: {date_str}",
        f"updated: {date_str}",
        f"tags: {tags_yaml}",
        "auto_generated: true",
        "---",
        "",
        f"# {tpl['emoji']} {tpl['title']}",
        "",
        f"**Map of Content** : {tpl['desc']}",
        "",
    ]
    for section_title, entries in tpl["sections"].items():
        lines.append(f"## {section_title}")
        lines.append("")
        for entry in entries:
            lines.append(f"- {entry}")
        lines.append("")
    # Inline tags
    lines.append("#" + "  #".join(tpl["tags"]))
    lines.append("")
    return "\n".join(lines)


def generate_missing_mocs(
    brain_dir: Path,
    notes: dict[str, NoteInfo],
    dry_run: bool = False,
) -> list[str]:
    """Create MOC files that are referenced but don't exist yet. Returns list of created stems."""
    moc_dir  = brain_dir / "05_Resources" / "MOCs"
    date_str = datetime.now().strftime("%Y-%m-%d")
    created  = []

    for key, tpl in _MOC_TEMPLATES.items():
        if key in notes:
            continue  # already exists
        content = _render_moc(key, tpl, date_str)
        target  = moc_dir / f"{key}.md"
        if not dry_run:
            moc_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info(f"[autolinker] MOC créé: {key}")
        created.append(key)

    return created


# ── Audit report writer ───────────────────────────────────────────────────────
def write_audit_report(
    notes:      dict[str, NoteInfo],
    graph:      dict,
    tag_fixed:  list[str],
    mocs_created: list[str],
    impl_links: dict[str, list[str]],
    brain_dir:  Path,
    dry_run:    bool,
) -> Path:
    now = datetime.now()
    date_str  = now.strftime("%Y-%m-%d")
    ts_str    = now.strftime("%Y-%m-%dT%H:%M:%S")

    stubs    = [s for s, n in notes.items() if n.is_stub]
    orphans  = graph["orphans"]
    broken   = graph["broken"]

    broken_list = ""
    for stem, targets in broken.items():
        for t in targets:
            broken_list += f"  - `{stem}` → `[[{t}]]` introuvable\n"

    impl_list = ""
    for stem, links in impl_links.items():
        if links:
            impl_list += f"  - `{stem}` → {', '.join(f'[[{l}]]' for l in links)}\n"

    content = f"""---
created: {date_str}
updated: {date_str}
tags: [audit, autolinker, report]
auto_generated: true
---

# 🔗 Autolinker Report — {date_str}

Généré le {ts_str} | Mode: {"DRY RUN" if dry_run else "LIVE"}

---

## 📊 Vue d'ensemble

| Métrique | Valeur |
|---|---|
| Total notes | {len(notes)} |
| Stubs ("_a remplir_") | {len(stubs)} |
| Orphelins (no links in/out) | {len(orphans)} |
| Notes avec liens brisés | {len(broken)} |
| Tags normalisés | {len(tag_fixed)} |
| MOCs créés | {len(mocs_created)} |
| Backlinks implicites ajoutés | {sum(len(v) for v in impl_links.values())} |

---

## 🟢 MOCs créés

{chr(10).join(f"- [[{m}]]" for m in mocs_created) if mocs_created else "_Aucun (tous existaient déjà)_"}

---

## 🟡 Liens brisés (non auto-corrigés — vérification manuelle)

{broken_list if broken_list else "_Aucun_"}

---

## 🔵 Backlinks implicites ajoutés

{impl_list if impl_list else "_Aucun_"}

---

## 🔴 Notes stubs (à remplir manuellement)

{chr(10).join(f"- [[{s}]]" for s in sorted(stubs)) if stubs else "_Aucun_"}

---

## ⬡ Notes orphelines (ni liens entrants ni sortants)

{chr(10).join(f"- [[{o}]]" for o in sorted(orphans)) if orphans else "_Aucun_"}

---

## 🏷️ Tags normalisés

{chr(10).join(f"- `{t}`" for t in sorted(tag_fixed)) if tag_fixed else "_Aucun_"}

---

## Liens

- [[../../08_Command-Center/dashboard-main]]
- [[architecture-optimizer]]

#audit #autolinker #report
"""
    report_dir  = brain_dir / "05_Resources" / "Research"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"autolink-report-{date_str}.md"
    if not dry_run:
        report_path.write_text(content, encoding="utf-8")
    return report_path


# ── Main entry point ──────────────────────────────────────────────────────────
def run_autolink(dry_run: bool = False, brain_dir: Path = BRAIN_DIR) -> dict:
    """
    Full autolink pass. Returns a summary dict.

    Args:
        dry_run: If True, compute changes but don't write any files.
        brain_dir: Path to the Obsidian BRAIN directory.
    """
    start      = __import__("time").perf_counter()
    logger.info(f"[autolinker] START — dry_run={dry_run}")

    # 1. Scan
    notes      = scan_vault(brain_dir)
    all_stems  = set(notes.keys())
    logger.info(f"[autolinker] {len(notes)} notes scannées")

    # 2. Graph analysis
    graph      = build_graph(notes)
    logger.info(
        f"[autolinker] graph: {len(graph['orphans'])} orphelins, "
        f"{len(graph['broken'])} notes avec liens brisés"
    )

    # 3. Normalize tags — iterate ALL .md files directly (not through by-stem dict)
    # This avoids the stem-collision bug where multiple files share the same stem
    # (e.g. 06_Agents/*/logs.md, 06_Agents/*/memory.md) and only one would be processed.
    tag_fixed: list[str] = []
    for path in brain_dir.rglob("*.md"):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fm, body   = _parse_frontmatter(raw)
        fm_tags_   = _extract_fm_tags(fm)
        rel_       = path.relative_to(brain_dir).as_posix()
        stem_      = path.stem
        tmp_note   = NoteInfo(
            path=path, stem=stem_, rel=rel_, raw=raw,
            frontmatter=fm, fm_tags=fm_tags_, inline_tags=[],
            out_links=[], is_stub=False, body=body,
        )
        updated = normalize_tags(tmp_note, brain_dir)
        if updated is not None:
            tag_fixed.append(rel_)           # use rel path so each file is uniquely identified
            if not dry_run:
                path.write_text(updated, encoding="utf-8")
            # Refresh the by-stem entry if this is the canonical stem in notes
            if stem_ in notes and notes[stem_].path == path:
                notes[stem_] = notes[stem_]._replace(raw=updated)

    logger.info(f"[autolinker] tags normalisés: {len(tag_fixed)} notes")

    # 4. Create missing MOCs
    mocs_created = generate_missing_mocs(brain_dir, notes, dry_run=dry_run)
    logger.info(f"[autolinker] MOCs créés: {mocs_created}")

    # Re-scan after MOC creation so new MOCs appear in graph
    if mocs_created and not dry_run:
        notes = scan_vault(brain_dir)
        all_stems = set(notes.keys())

    # 5. Detect implicit links — only for non-stub notes (stubs have no real content)
    impl_links:    dict[str, list[str]] = {}
    links_written: int = 0
    for stem, note in notes.items():
        if note.is_stub:
            continue
        found = find_implicit_links(note, all_stems)
        if not found:
            continue
        impl_links[stem] = found
        updated = add_links_to_liens_section(note, found)
        if updated is not None:
            # Count only links actually added (deduplication already applied inside)
            added_count = updated.count("[[") - note.raw.count("[[")
            links_written += max(0, added_count)
            if not dry_run:
                note.path.write_text(updated, encoding="utf-8")

    logger.info(f"[autolinker] backlinks implicites: {links_written} liens ajoutés")

    # 6. Write report
    report_path = write_audit_report(
        notes=notes,
        graph=graph,
        tag_fixed=tag_fixed,
        mocs_created=mocs_created,
        impl_links=impl_links,
        brain_dir=brain_dir,
        dry_run=dry_run,
    )

    elapsed = round((__import__("time").perf_counter() - start) * 1000)
    logger.info(f"[autolinker] DONE — {elapsed}ms | rapport: {report_path}")

    return {
        "ok":           True,
        "dry_run":      dry_run,
        "elapsed_ms":   elapsed,
        "notes_total":  len(notes),
        "stubs":        len([n for n in notes.values() if n.is_stub]),
        "orphans":      len(graph["orphans"]),
        "broken_links": {k: v for k, v in graph["broken"].items()},
        "tags_fixed":   tag_fixed,
        "mocs_created": mocs_created,
        "implicit_links_added": links_written,
        "report_path":  str(report_path),
        "graph": {
            "orphan_list": sorted(graph["orphans"]),
            "sink_list":   sorted(graph["sinks"]),
        },
    }
