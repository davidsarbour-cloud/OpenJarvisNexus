# Changelog

All notable changes to OpenJarvis are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## NEXUS9 (fork de David Arbour) — 2026-05-27

### Performance (`-95 %` images, `~0` HTTP polls in idle)
- Agent avatars + world heroes resized (512 / 2560 px) and re-encoded
  as WebP via ffmpeg. Combined 93 MB → 3.5 MB (−96 %). `<picture>`
  source with PNG fallback so legacy browsers still work.
- New `wsBus` singleton multiplexes every `useLiveMetric({ wsTopic })`
  over one shared `/ws/events` socket. HTTP poll relaxed to 60 s
  fallback when a wsTopic is set.
- Backend `snapshot_publisher` spawns 10 asyncio loops (agents 8s ·
  jobs 6s · world-cards 6s · system-metrics 2s · budget 8s · docker
  8s · health 10s · chromadb 12s · models 30s · scheduled 60s) so
  card data is pushed instead of polled. Idle HTTP traffic dropped
  from ~140 req/min/client to ~0.
- React routes lazy-loaded (`React.lazy()` on 15 pages). Initial
  bundle ~30 % lighter; first paint quasi-instant.

### Added
- **Boot intro overlay** (`NexusBootIntro`) — splash that plays once per
  backend boot. `GET /v1/boot/info` returns a per-process uuid; the
  frontend compares with localStorage and replays only when it
  differs. `<video src="/intro/boot.mp4">` with an animated HUD
  placeholder fallback (NEXUS9 wordmark + scan lines + terminal
  trace + progress bar) so the overlay is never broken.
- **`<WorldShell>` shared component** — 5 world dashboard pages
  (Forge/Commerce/Vault/Cyberdeck/Docker) now thin wrappers (~45 LOC
  each) around one generic 3-column dashboard parameterised on
  colorKey, cardRegistry, imageCandidates, defaultSeeds.
  2 500 LOC of duplication → 886 LOC total (−65 %).
- **QuickForge card** — inline STL-mission launcher (`POST /v1/forge/mission`)
  docked in `/world/forge`. No nav required.
- **Telegram activity / Model routing / Daily digest** world cards —
  new snapshot keys in `/v1/world/cards/snapshot` + matching backend
  fetchers and an in-process `_telegram_state` counter.
- **Skill completion events on `/ws/events`** — scheduled and manual
  skill runs publish `{level, source: "SKILL", note: "<vault path>"}`.
  The RightPanel renders clickable rows that open the note via
  `obsidian://open?vault=BRAIN&file=…`.
- **Agent avatars** (7 of 10) — `<picture>` with WebP source +
  Lucide-icon fallback for agents without a photo yet.

### Tests (`25 → 45`, +80 %)
- `wsBus.test.ts` (7) — singleton socket, filter-routed delivery,
  history replay, ignored ping/error frames, unsubscribe, state.
- `useLiveMetric.test.ts` (8) — initial fetch, error capture, WS
  push replace, mismatched topic, no-sub-when-no-topic, exactly-one-
  when-set, HTTP poll relaxed to ≥60 s, unsubscribe on unmount.
- `test_snapshot_publisher.py` (3) — start_publishers spawns 10
  expected topics with correct names, `_publish_loop` nests results
  under `data`, fetcher exceptions are swallowed.
- `test_boot_endpoint.py` (2) — boot_id stable for the process
  lifetime; `/v1/info` and `/v1/boot/info` payloads don't overlap.

### Security
- `CORSMiddleware` switched from `allow_origins=["*"]` to an explicit
  allow-list (localhost:5173 / :8000 / :1420 + tauri://localhost).
  `NEXUS9_CORS_ORIGINS` env var extends without code changes. The
  `["*"]` + `allow_credentials=True` combination violated the CORS
  spec and is now impossible.

### Documentation
- New `docs/nexus9/` section with: architecture overview (mermaid
  diagrams), quickstart, adding-a-card walkthrough, adding-a-skill
  walkthrough (TOML + Hermes flavours), endpoint catalog with curl
  examples, Windows-first troubleshooting guide.

### Fixed
- PWA service-worker build (`workbox.globIgnores` skips heavy world
  PNG fallbacks; the WebP versions are precached instead).
- "Phare de lumière" sweep animation removed from every world page
  + the JARVIS portrait (too distracting; vignette breath + scan
  lines kept).

---

## NEXUS9 (fork de David Arbour) — 2026-05-23

Surcouche NEXUS9 (Command Center React + agents) au-dessus d'OpenJarvis.

### Performance
- qwen3:14b maintenu 100% GPU via `num_ctx=4096` (24 → 44 tok/s sur RTX 4070 SUPER)
- `OLLAMA_HOST` forcé en IPv4 (127.0.0.1) — évite le stall ~2s de résolution `::1`
- Config Ollama centralisée dans `backend/config.py`

### Added
- Bridge **Brain → Vault** : indexe les notes Obsidian dans ChromaDB ; `vault_query` cherche le brain ; ré-index quotidien (04:30)
- Hub **WebSocket** `/ws/events` relié au Command Center React
- **Smoke tests Playwright** sur `/` (Command Center) et `/orbital`

### Changed
- **Forge fusionné** dans le pipeline Commerce en in-process (plus de self-HTTP/polling)
- `docker-compose` : service `ollama` retiré (Ollama natif via `host.docker.internal`) ; profiles `monitoring`/`quality`/`agents`
- `START_ALL.bat` réécrit pour le stack natif (attentes bornées)

### Removed
- Legacy : `orbital_ui` (vanilla JS), `Nexus9.html`, `Nexusx9`, `vault_notes`, `desktop/`, scripts one-off morts, `agent_logger`, ancien `index_skills`, binaire macOS 77 Mo, submodules crush cassés
- `.gitignore` : brain perso (`backend/BRAIN`) + données locales

---

## [Unreleased]

### Added

- AI stack support for evaluating other agentic frameworks via subprocess.
  New `evals/backends/external/` subpackage wraps Hermes Agent and OpenClaw
  as one-shot subprocess backends behind the existing `InferenceBackend`
  ABC; new `evals/comparison/` toolkit provides path + commit-pin
  enforcement (`third_party.py`), config templating (`make_configs.py`),
  and LaTeX table generation (`table_gen.py`).
- New optional extra `framework-comparison` (depends on `polars`).
- New pytest marker `live_external` for integration tests requiring real
  foreign-framework installations.

### Changed

- `JarvisAgentBackend.generate_full` and `JarvisDirectBackend.generate_full` now return
  the spec §6.2 extended fields (`energy_joules`, `peak_power_w`, `tool_calls`,
  `turn_count`, `framework`, `framework_commit`, `error`) for cross-framework
  comparison parity. Existing callers that didn't read these fields are unaffected.
- `_third_party.toml` no longer ships user-specific default paths. Set
  `HERMES_AGENT_PATH` and `OPENCLAW_PATH` env vars to point at your local
  checkouts before running the framework-comparison harness; missing or
  empty paths now raise `ThirdPartyNotFoundError` with an actionable hint.

#### Skills System (Plans 1, 2A, 2B)

- **Skills core** — every skill is a tool. Skills appear in a system prompt catalog, agents invoke them on demand, content (pipeline results, markdown instructions, or both) gets injected into context.
  - `SkillManifest` + `SkillStep` types with tags, depends, invocation flags, markdown content
  - `SkillManager` — discovery, precedence resolution, catalog XML generation, tool wrapping
  - `SkillTool(BaseTool)` — auto-extracts parameters from step argument templates
  - `SkillExecutor` — sequential pipeline execution with sub-skill delegation
  - Dependency graph with cycle detection, max depth enforcement, capability unions
  - Security: four trust tiers (bundled/indexed/unreviewed/workspace), capability-gated enforcement
  - Skill index module for git-backed registry search

- **agentskills.io spec adoption** — canonical `SKILL.md` format with YAML frontmatter following the [agentskills.io](https://agentskills.io/specification) open standard.
  - `SkillParser` with strict spec validation + tolerant field mapping via `FIELD_MAPPING` table
  - `ToolTranslator` for external tool name translation (Bash -> shell_exec, Read -> file_read, etc.)
  - Source resolvers: `HermesResolver`, `OpenClawResolver`, `GitHubResolver`
  - `SkillImporter` with provenance tracking (`.source` metadata files), optional script import
  - Sourced subdirectory layout (`~/.openjarvis/skills/<source>/<name>/`)

- **Skills learning loop** — trace tagging, pattern discovery, DSPy/GEPA optimization.
  - Trace metadata tagging: `skill`, `skill_source`, `skill_kind` flow through ToolExecutor -> TraceCollector -> TraceStep
  - `SkillDiscovery` wired into `SkillManager.discover_from_traces()` with kebab name normalization
  - `SkillOptimizer` — per-skill DSPy/GEPA wrapper that buckets traces and writes sidecar overlays
  - `SkillOverlay` — sidecar storage at `~/.openjarvis/learning/skills/<name>/optimized.toml`
  - `SkillManager._load_overlays()` applies optimized descriptions + few-shot examples at discovery time
  - `LearningOrchestrator._maybe_optimize_skills()` — opt-in auto-trigger

- **Skills benchmark harness** — 4-condition PinchBench evaluation.
  - I3 fix: `skill_few_shot_examples` wired through SystemBuilder -> `_run_agent` -> `ToolUsingAgent` -> `native_react.REACT_SYSTEM_PROMPT`
  - `SkillBenchmarkRunner` — 4-condition x N-seed x M-task sweep with markdown report
  - `JarvisAgentBackend` accepts `skills_enabled` and `overlay_dir` kwargs
  - Conditions: `no_skills`, `skills_on`, `skills_optimized_dspy`, `skills_optimized_gepa`

- **CLI commands:**
  - `jarvis skill list` / `info` / `run` / `install` / `sync` / `sources` / `update` / `remove` / `search`
  - `jarvis skill discover` — mine traces for recurring tool patterns
  - `jarvis skill show-overlay` — inspect optimization output
  - `jarvis optimize skills` — run DSPy/GEPA per-skill optimization
  - `jarvis bench skills` — run the PinchBench skills benchmark

- **Agent prompt improvement:**
  - `native_react.REACT_SYSTEM_PROMPT` now includes "Using Skills" guidance that teaches agents to distinguish executable vs. instructional skill responses
  - `{skill_examples}` placeholder for optimized few-shot example injection

- **Configuration:**
  - `[skills]` section: `enabled`, `skills_dir`, `active`, `auto_discover`, `auto_sync`, `max_depth`, `sandbox_dangerous`
  - `[[skills.sources]]` section: `source`, `url`, `filter`, `auto_update`
  - `[learning.skills]` section: `auto_optimize`, `optimizer`, `min_traces_per_skill`, `optimization_interval_seconds`, `overlay_dir`
  - `SkillSourceConfig` and `SkillsLearningConfig` dataclasses

- **Documentation:**
  - `docs/user-guide/skills.md` — comprehensive user guide
  - `docs/architecture/skills.md` — technical deep-dive
  - `docs/tutorials/skills-workflow.md` — end-to-end tutorial
  - `docs/getting-started/configuration.md` — expanded with skills config sections
  - `CLAUDE.md` — updated architecture section

### Fixed

- **Trace metadata flow** — `ToolResult.metadata` now propagates through `TOOL_CALL_END` event to `TraceStep.metadata` (was silently dropped at the event-bus boundary)
- **TaintSet JSON serialization** — `ToolExecutor._json_safe_metadata()` filters non-JSON-serializable values (like `TaintSet`) from event payloads before they reach `TraceStore`
- **Non-dict YAML frontmatter** — source resolvers handle `yaml.safe_load()` returning a string instead of a dict (discovered on real OpenClaw imports)
- **OpenClaw category/name queries** — `jarvis skill install openclaw:owner/slug` now correctly splits into category + name match
- **SkillDiscovery trace compatibility** — `_extract_tool_sequence` reads from `step.input["tool"]` (the actual `TraceStep` format), not the nonexistent `step.tool_name` attribute
- **LearningOrchestrator skill trigger** — `_maybe_optimize_skills` runs BEFORE the SFT-data short-circuit (skills are tagged via trace metadata, not mined as SFT pairs)
- **PinchBenchScorer constructor** — `SkillBenchmarkRunner` constructs `PinchBenchScorer(judge_backend, model)` instead of no-args
- **EvalRunner results access** — reads per-task data from `eval_runner.results` property, not nonexistent `summary.results`
