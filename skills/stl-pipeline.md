# stl-pipeline.md — D3Dprintix STL Pipeline

Full pipeline for 3D model generation for Etsy shop D3Dprintix.
Agent responsable: FORGE

---

## PIPELINE FLOW

JARVIS detects STL intent
  POST /v1/stl/mission
  [Concept Agent]  — brief technique + contraintes FDM
  [FORGE]          — génération via Meshy AI (priorité) ou Blender
  [Optimizer]      — audit qualité: overhangs, scaling, score
  [File Manager]   — validation trimesh + pymeshfix — Bambu Studio
  [Researcher]     — veille quotidienne 21h (rapport indépendant)

---

## ROUTING (first success wins)

1. n8n webhook (if configured)
2. Meshy AI (if MESHY_API_KEY set) — cloud, organic quality
3. Blender headless (if BLENDER_PATH valid) — parametric
4. Fallback — embedded minimal script

---

## D3DPRINTIX DEFAULTS — ALWAYS APPLY

- Style: low-poly fantasy
- Scale: 15cm longest dimension (auto-rescaled)
- Support-free design
- Single piece printable mesh
- Overhangs: less than 45 degrees
- Flat base at z=0
- Wall thickness: 1.2mm minimum
- Target: FDM Bambu Lab

---

## PIPELINE AGENTS

| Agent | ID | Role |
|-------|-----|------|
| Concept Agent | stl_concept | Technical brief, specs, constraints |
| FORGE | stl_blender | 3D generation via Meshy AI or Blender |
| Optimizer | stl_optim | Quality audit, overhangs, scaling |
| Renderer | stl_render | Preview, thumbnail |
| File Manager | stl_files | trimesh + pymeshfix, Bambu Studio handoff |
| Researcher | stl_research | Daily 21:00 — Thingiverse, Cults3D, Etsy |

---

## MESHY AI PROMPT FORMAT

ULTRON generates prompts: 60-100 words
Style: low-poly fantasy, printable, support-free, flat base
