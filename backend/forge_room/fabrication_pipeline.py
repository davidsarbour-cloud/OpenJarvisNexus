"""
Pipeline de fabrication complet — 11 étapes.
Orchestré par JARVIS, planifié par ULTRON, exécuté par The Forge Room.
"""
from __future__ import annotations
import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx
import traceback
import trimesh

from forge_room.mesh_validator      import validate_mesh
from forge_room.mesh_repair         import auto_repair, scale_to_target, place_on_build_plate
from forge_room.orientation_optimizer import optimize_orientation, apply_orientation
from forge_room.support_analyzer    import analyze_supports
from forge_room.export_pipeline     import run_export_pipeline
from forge_room.manufacturing_report import generate_report, save_report
from forge_room.blender_bridge      import generate_stl_via_blender, is_available as blender_ok
from forge_room.openscad_generator  import generate_stl_via_openscad, openscad_to_stl
from forge_room.meshy_bridge        import generate_stl_via_meshy, is_available as meshy_ok
from forge_room.deepseek_coder_bridge import is_available as deepseek_ok

BACKEND_PORT    = int(os.getenv("BACKEND_PORT", 8000))
CLAUDE_MODEL_GROS = os.getenv("CLAUDE_MODEL_GROS", "claude-sonnet-4-6")

# Répertoires de sortie dans backend/
_BACKEND_DIR = Path(__file__).parent.parent
FORGE_OUTPUT  = _BACKEND_DIR / "forge_output"
FORGE_REPORTS = _BACKEND_DIR / "forge_reports"
FORGE_OUTPUT.mkdir(exist_ok=True)
FORGE_REPORTS.mkdir(exist_ok=True)

# Registre des missions — persisté sur disque pour survivre aux redémarrages uvicorn
_MISSIONS_CACHE = _BACKEND_DIR / "forge_missions_cache.json"

def _load_cache() -> dict:
    try:
        if _MISSIONS_CACHE.exists():
            return json.loads(_MISSIONS_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_cache(missions: dict) -> None:
    try:
        # Ne sauver que les missions des dernières 24h (évite le fichier infini)
        from datetime import timezone
        cutoff = datetime.now().isoformat()[:10]  # date du jour
        pruned = {
            mid: m for mid, m in missions.items()
            if m.get("created_at", "")[:10] >= cutoff
        }
        _MISSIONS_CACHE.write_text(
            json.dumps(pruned, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception:
        pass

_forge_missions: dict[str, dict] = _load_cache()

STEP_LABELS = [
    "routing",          # 1. JARVIS route
    "planning",         # 2. ULTRON planifie
    "code_generation",  # 3. DeepSeek génère le code géométrique
    "mesh_generation",  # 4. Blender/OpenSCAD génère le mesh brut
    "validation_raw",   # 5. Validation mesh brut
    "repair",           # 6. Réparation automatique
    "orientation",      # 7. Optimisation orientation FDM
    "support_analysis", # 8. Analyse des supports
    "validation_final", # 9. Validation finale
    "export",           # 10. Export STL propre
    "report",           # 11. Rapport de fabrication
]


def new_mission(prompt: str, auto_bambu: bool = False) -> dict:
    # ── Anti-duplication : même prompt déjà "running" depuis <5min → retourne la mission existante
    prompt_stripped = prompt.strip()
    for existing in _forge_missions.values():
        if (
            existing.get("status") == "running"
            and existing.get("prompt", "").strip() == prompt_stripped
        ):
            try:
                created = datetime.fromisoformat(existing["created_at"])
                age_s = (datetime.now() - created).total_seconds()
                if age_s < 300:  # 5 minutes
                    print(f"[FORGE] Anti-duplication: mission {existing['id']} déjà en cours ({age_s:.0f}s)")
                    return existing
            except Exception:
                pass

    mid = str(uuid.uuid4())[:8].upper()
    m = {
        "id": mid,
        "prompt": prompt_stripped,
        "status": "running",
        "current_step": "routing",
        "steps": {s: "pending" for s in STEP_LABELS},
        "plan": "",
        "files": {},
        "report": None,
        "logs": [],
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
        "auto_bambu": auto_bambu,
    }
    _forge_missions[mid] = m
    _save_cache(_forge_missions)
    return m


def get_mission(mid: str) -> dict | None:
    m = _forge_missions.get(mid)
    if m is None:
        # Tente de recharger depuis le cache disque (survie redémarrage uvicorn)
        fresh = _load_cache()
        if mid in fresh:
            _forge_missions.update(fresh)
            m = _forge_missions.get(mid)
    return m


def _log(m: dict, msg: str, level: str = "info"):
    ts = datetime.now().strftime("%H:%M:%S")
    m["logs"].append({"ts": ts, "msg": msg, "level": level})
    print(f"[FORGE:{m['id']}] [{level.upper()}] {msg}")


def _step(m: dict, name: str, status: str = "running"):
    m["steps"][name] = status
    m["current_step"] = name


def _step_done(m: dict, name: str):
    m["steps"][name] = "done"


def _step_fail(m: dict, name: str, reason: str):
    m["steps"][name] = "failed"
    _log(m, f"ÉTAPE ÉCHOUÉE [{name}]: {reason}", "error")


# ── ULTRON — Planification fabrication (Claude Sonnet) ───

_ULTRON_FORGE_SYSTEM = """You are ULTRON, The Forge Room strategic intelligence.
You generate structured fabrication plans for FDM 3D printing.
Output a JSON object with these fields:
{
  "object_name": "...",
  "description": "...",
  "construction_approach": "...",
  "key_dimensions_mm": {"x": N, "y": N, "z": N},
  "geometry_primitives": ["..."],
  "fdm_constraints": ["..."],
  "deepseek_instructions": "..."
}
Be precise. deepseek_instructions must guide a code generator to produce the geometry."""


async def _ultron_plan(prompt: str) -> dict:
    """ULTRON génère un plan de fabrication structuré via Claude Sonnet."""
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"http://localhost:{BACKEND_PORT}/v1/chat/completions",
                json={
                    "system": _ULTRON_FORGE_SYSTEM,
                    "message": f"Fabrication request: {prompt}\n\nGenerate a precise fabrication plan.",
                    "stream": False,
                    "model": CLAUDE_MODEL_GROS,
                },
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                msg = data.get("choices", [{}])[0].get("message", "")
                text = (msg if isinstance(msg, str) else msg.get("content", "")).strip()
                # Extraction JSON de la réponse
                import re
                m = re.search(r"\{[\s\S]+\}", text)
                if m:
                    return json.loads(m.group(0))
    except Exception as e:
        print(f"[ULTRON] plan échoué: {e}")
    # Fallback plan minimal
    return {
        "object_name": prompt[:40],
        "description": prompt,
        "construction_approach": "basic parametric solid",
        "key_dimensions_mm": {"x": 80, "y": 80, "z": 100},
        "geometry_primitives": ["sphere", "cylinder", "box"],
        "fdm_constraints": ["no overhangs >45°", "flat base", "wall >=1.2mm"],
        "deepseek_instructions": (
            f"Create a 3D printable model of: {prompt}. "
            "Single manifold solid, flat base at z=0, wall >=1.2mm, max dim 120mm."
        ),
    }


# ── Classifieur moteur : Blender vs OpenSCAD ─────────────

_MECHANICAL_KEYWORDS = {
    # Pièces mécaniques
    "gear", "engrenage", "bolt", "vis", "screw", "bracket", "support",
    "enclosure", "boitier", "boîtier", "case", "housing", "holder",
    "mount", "clip", "hinge", "charnière", "joint", "coupling",
    "thread", "filetage", "hex", "hexagonal", "nut", "écrou",
    "washer", "rondelle", "bearing", "roulement", "pulley", "poulie",
    "rack", "pignon", "flange", "bride", "spacer", "entretoise",
    # Style
    "mechanical", "mécanique", "industrial", "industriel",
    "parametric", "paramétrique", "precise", "précis", "technical",
    "functional", "fonctionnel", "engineering", "ingénierie",
    "CAD", "connector", "connecteur", "adapter", "adaptateur",
    "box", "boite", "cube", "cylinder", "cylindre", "prism",
}

_ARTISTIC_KEYWORDS = {
    # Animaux — liste étendue
    "dragon", "cat", "chat", "dog", "chien", "wolf", "loup",
    "lion", "tiger", "tigre", "bear", "ours", "fox", "renard",
    "bird", "oiseau", "fish", "poisson", "snake", "serpent",
    "elephant", "éléphant", "horse", "cheval", "deer", "cerf",
    "rabbit", "lapin", "owl", "hibou", "eagle", "aigle",
    "shark", "requin", "whale", "baleine", "dolphin", "dauphin",
    "gorilla", "gorille", "monkey", "singe", "panda", "koala",
    "crocodile", "dinosaur", "dinosaure", "phoenix", "griffin", "griffon",
    "creature", "créature", "monster", "monstre", "beast", "bête",
    "demon", "démon", "angel", "ange", "fairy", "fée",
    # Figurines & art
    "figurine", "statue", "sculpture", "bust", "buste",
    "character", "personnage", "warrior", "guerrier", "knight",
    "wizard", "mage", "robot", "alien", "human", "face", "visage",
    "portrait", "head", "tête", "body", "corps",
    # Style artistique
    "artistic", "artistique", "organic", "organique", "fantasy",
    "fantasy", "fantaisie", "low-poly", "lowpoly", "anime",
    "cute", "mignon", "decorative", "décoratif",
}

ENGINE_BLENDER   = "blender"
ENGINE_OPENSCAD  = "openscad"


def _classify_engine(prompt: str, plan: dict) -> tuple[str, str]:
    """
    Retourne (engine, raison) en analysant mots-clés du prompt et du plan ULTRON.
    Blender   → organique / artistique / créatures
    OpenSCAD  → mécanique / précis / technique
    """
    text = (prompt + " " + plan.get("description", "") + " " +
            plan.get("construction_approach", "")).lower()

    mech_hits = [kw for kw in _MECHANICAL_KEYWORDS if kw in text]
    art_hits  = [kw for kw in _ARTISTIC_KEYWORDS   if kw in text]

    if mech_hits and not art_hits:
        return ENGINE_OPENSCAD, f"mécanique/technique ({', '.join(mech_hits[:3])})"

    if art_hits and not mech_hits:
        return ENGINE_BLENDER, f"artistique/organique ({', '.join(art_hits[:3])})"

    if mech_hits and art_hits:
        # Les deux — score par densité
        if len(mech_hits) > len(art_hits):
            return ENGINE_OPENSCAD, f"dominant mécanique ({len(mech_hits)} vs {len(art_hits)})"
        return ENGINE_BLENDER, f"dominant artistique ({len(art_hits)} vs {len(mech_hits)})"

    # Aucun signal clair — Blender par défaut (plus polyvalent)
    return ENGINE_BLENDER, "aucun signal — défaut Blender"


# ── Génération mesh brut ──────────────────────────────────

async def _generate_raw_mesh(m: dict, plan: dict) -> Path | None:
    """
    Routing intelligent :
    - Organique/artistique → Meshy AI (cloud, qualité organique réelle)
    - Mécanique/technique  → OpenSCAD (CAD paramétrique)
    - Fallbacks croisés
    - Dernier recours : trimesh cylindre

    NE lève jamais d'exception non catchée — toujours retourne Path ou None.
    """
    import traceback as _tb
    from forge_room.openscad_generator import is_available as openscad_ok

    desc  = plan.get("deepseek_instructions", m["prompt"])
    fplan = json.dumps(plan, ensure_ascii=False)
    out   = FORGE_OUTPUT / f"{m['id']}_raw.stl"

    try:
        engine, reason = _classify_engine(m["prompt"], plan)
        _log(m, f"Moteur sélectionné: {engine.upper()} — {reason}")
    except Exception as e:
        _log(m, f"Erreur classification moteur: {e} — défaut Blender", "warning")
        engine = ENGINE_BLENDER

    if engine == ENGINE_BLENDER:
        # ── Priorité 1 : Meshy AI (formes organiques réelles) ─
        if meshy_ok():
            _log(m, "Génération via Meshy AI text-to-3D (cloud)...")
            try:
                result = await generate_stl_via_meshy(m["prompt"], out)
                if result:
                    _log(m, f"STL généré via Meshy AI: {out.name}", "success")
                    return out
                _log(m, "Meshy AI échoué — bascule Blender...", "warning")
            except httpx.TimeoutException:
                _log(m, "Meshy AI timeout — bascule Blender...", "warning")
            except Exception as e:
                _log(m, f"Meshy AI exception: {e} — bascule Blender...\n{_tb.format_exc()}", "warning")
        else:
            _log(m, "Meshy AI non configuré — bascule Blender...", "warning")

        # ── Priorité 2 : Blender + DeepSeek ──────────────────
        if blender_ok():
            _log(m, "Fallback: Blender 5.1 + DeepSeek Coder...")
            try:
                if await generate_stl_via_blender(desc, out, plan=fplan):
                    _log(m, f"STL généré via Blender: {out.name}", "success")
                    return out
                _log(m, "Blender a échoué.", "warning")
            except Exception as e:
                _log(m, f"Blender exception: {e}", "warning")

    else:
        # ── Priorité 1 : OpenSCAD (mécanique paramétrique) ───
        if openscad_ok():
            _log(m, "Génération via OpenSCAD 2025 + DeepSeek Coder...")
            try:
                if await generate_stl_via_openscad(desc, out, plan=fplan):
                    _log(m, f"STL généré via OpenSCAD: {out.name}", "success")
                    return out
                _log(m, "OpenSCAD a échoué — bascule Blender...", "warning")
            except Exception as e:
                _log(m, f"OpenSCAD exception: {e} — bascule Blender...", "warning")
        else:
            _log(m, "OpenSCAD non disponible — bascule Blender...", "warning")

        # ── Priorité 2 : Blender ─────────────────────────────
        if blender_ok():
            _log(m, "Fallback: Blender 5.1 + DeepSeek Coder...")
            try:
                if await generate_stl_via_blender(desc, out, plan=fplan):
                    _log(m, f"STL généré via Blender (fallback): {out.name}", "success")
                    return out
                _log(m, "Blender a échoué.", "warning")
            except Exception as e:
                _log(m, f"Blender exception (fallback): {e}", "warning")

        # ── Priorité 3 : Meshy AI (dernier recours organique) ─
        if meshy_ok():
            _log(m, "Dernière tentative: Meshy AI...")
            try:
                if await generate_stl_via_meshy(m["prompt"], out):
                    _log(m, f"STL généré via Meshy AI (fallback): {out.name}", "success")
                    return out
            except httpx.TimeoutException:
                _log(m, "Meshy AI timeout (fallback)", "warning")
            except Exception as e:
                _log(m, f"Meshy AI exception (fallback): {e}", "warning")

    # ── Dernier recours : trimesh paramétrique ────────────
    _log(m, "Dernier recours — mesh trimesh paramétrique...", "warning")
    dims = plan.get("key_dimensions_mm", {"x": 80, "y": 80, "z": 100})
    try:
        box  = trimesh.creation.box(extents=[dims.get("x", 80), dims.get("y", 80), dims.get("z", 100)])
        base = trimesh.creation.cylinder(radius=dims.get("x", 80) * 0.6, height=5.0)
        base.apply_translation([0, 0, -dims.get("z", 100) / 2 - 2.5])
        combined = trimesh.util.concatenate([box, base])
        combined.export(str(out))
        _log(m, f"STL fallback trimesh généré: {out.name}")
        return out
    except Exception as e:
        _log(m, f"Fallback trimesh échoué: {e}\n{_tb.format_exc()}", "error")
        return None


# ── Pipeline principal ────────────────────────────────────

async def run_forge_pipeline(mission_id: str) -> None:
    """
    Exécute les 11 étapes du pipeline The Forge Room.
    Appelé en background task par forge_engine.

    Chaque step a un timeout de 120s via asyncio.wait_for.
    mesh_generation est bloquant (échec = abort mission).
    Les autres steps peuvent échouer et le pipeline continue.
    """
    STEP_TIMEOUT = 120  # secondes par step

    m = _forge_missions.get(mission_id)
    if not m:
        return

    # Variables locales réutilisées entre steps
    plan: dict     = {}
    raw_stl: Path  = None
    raw_mesh       = None
    mesh           = None
    pre_val        = None
    post_val       = None
    repair         = None
    orient         = None

    async def _run_step(step_name: str, coro, is_blocking: bool = False):
        """Wrapper: timeout 120s + try/except. Retourne la valeur ou None."""
        _step(m, step_name, "running")
        try:
            result = await asyncio.wait_for(coro, timeout=STEP_TIMEOUT)
            _step_done(m, step_name)
            return result
        except asyncio.TimeoutError:
            _step_fail(m, step_name, f"Timeout {STEP_TIMEOUT}s dépassé")
            if is_blocking:
                raise  # re-lève pour stopper le pipeline
            return None
        except Exception as exc:
            _step_fail(m, step_name, f"{type(exc).__name__}: {exc}")
            _log(m, traceback.format_exc(), "error")
            if is_blocking:
                raise
            return None

    try:
        # ── Étape 1 : Routing ─────────────────────────────
        async def _do_routing():
            _log(m, f"JARVIS → THE FORGE ROOM | Mission: {m['prompt'][:60]}")
        await _run_step("routing", _do_routing())

        # ── Étape 2 : Planning ULTRON ─────────────────────
        async def _do_planning():
            _log(m, "ULTRON — génération du plan de fabrication...")
            p = await _ultron_plan(m["prompt"])
            m["plan"] = p
            _log(m, f"Plan: {p.get('object_name', '?')} — {p.get('construction_approach', '?')}")
            return p

        plan_result = await _run_step("planning", _do_planning())
        plan = plan_result if plan_result else {
            "object_name": m["prompt"][:40],
            "description": m["prompt"],
            "construction_approach": "basic parametric solid",
            "key_dimensions_mm": {"x": 80, "y": 80, "z": 100},
            "geometry_primitives": ["sphere", "cylinder", "box"],
            "fdm_constraints": ["no overhangs >45°", "flat base", "wall >=1.2mm"],
            "deepseek_instructions": (
                f"Create a 3D printable model of: {m['prompt']}. "
                "Single manifold solid, flat base at z=0, wall >=1.2mm, max dim 120mm."
            ),
        }

        # ── Étape 3 : Code DeepSeek ──────────────────────
        async def _do_code_gen():
            ds_ok = deepseek_ok()
            _log(m, f"DeepSeek Coder disponible: {'Oui' if ds_ok else 'Non — fallback actif'}")

        await _run_step("code_generation", _do_code_gen())

        # ── Étape 4 : Génération mesh brut (BLOQUANT) ─────
        async def _do_mesh_gen():
            stl = await _generate_raw_mesh(m, plan)
            if not stl:
                raise RuntimeError("Aucun moteur de génération disponible — Blender, OpenSCAD et Meshy non disponibles")
            m["files"]["raw_stl"] = str(stl)
            return stl

        raw_stl = await _run_step("mesh_generation", _do_mesh_gen(), is_blocking=True)

        # ── Étape 5 : Validation mesh brut ────────────────
        async def _do_validation_raw():
            _log(m, "Validation mesh brut...")
            rm = trimesh.load(str(raw_stl), force="mesh")
            pv = validate_mesh(rm, check_thickness=True, check_supports=True)
            _log(m, f"Score initial: {pv.printability_score}/100")
            for issue in pv.all_issues:
                _log(m, f"  {issue}")
            return rm, pv

        val_raw_result = await _run_step("validation_raw", _do_validation_raw())
        if val_raw_result:
            raw_mesh, pre_val = val_raw_result
        else:
            # Step échoué — charge le mesh brut directement sans validation
            try:
                raw_mesh = trimesh.load(str(raw_stl), force="mesh")
            except Exception:
                raw_mesh = None

        # ── Étape 6 : Réparation ──────────────────────────
        async def _do_repair():
            if raw_mesh is None:
                _log(m, "Mesh brut indisponible — réparation ignorée", "warning")
                return raw_mesh, None
            if pre_val and not pre_val.passed:
                _log(m, "Réparation automatique...")
                msh, rep = auto_repair(raw_mesh)
                for r in rep.repairs_applied:
                    _log(m, f"  {r}")
                return msh, rep
            else:
                _log(m, "Mesh déjà valide — réparation ignorée")
                return raw_mesh, None

        repair_result = await _run_step("repair", _do_repair())
        if repair_result:
            mesh, repair = repair_result
        else:
            mesh   = raw_mesh
            repair = None

        # ── Étape 7 : Orientation FDM ─────────────────────
        async def _do_orientation():
            if mesh is None:
                _log(m, "Mesh indisponible — orientation ignorée", "warning")
                return mesh, None
            _log(m, "Optimisation orientation FDM...")
            scaled  = scale_to_target(mesh, 150.0)
            ort     = optimize_orientation(scaled)
            oriented = apply_orientation(scaled, ort)
            _log(m, f"Orientation: {ort.label} (surplombs: {ort.overhang_pct}%, contact: {ort.contact_pct}%)")
            return oriented, ort

        orient_result = await _run_step("orientation", _do_orientation())
        if orient_result:
            mesh, orient = orient_result

        # ── Étape 8 : Analyse supports ────────────────────
        async def _do_support_analysis():
            if mesh is None:
                _log(m, "Mesh indisponible — analyse supports ignorée", "warning")
                return
            sup = analyze_supports(mesh)
            _log(m, f"Supports requis: {'Oui' if sup.support_required else 'Non'} ({sup.overhang_pct}% surplombs)")

        await _run_step("support_analysis", _do_support_analysis())

        # ── Étape 9 : Validation finale ───────────────────
        async def _do_validation_final():
            if mesh is None:
                _log(m, "Mesh indisponible — validation finale ignorée", "warning")
                return None
            pv = validate_mesh(mesh, check_thickness=True, check_supports=True)
            _log(m, f"Score final: {pv.printability_score}/100")
            for c in pv.passed_checks:
                _log(m, f"  {c}")
            for f in pv.failed_checks:
                _log(m, f"  {f}", "warning")
            return pv

        post_val = await _run_step("validation_final", _do_validation_final())

        # ── Étape 10 : Export STL ─────────────────────────
        async def _do_export():
            if mesh is None:
                raise RuntimeError("Mesh indisponible — export impossible")
            final_stl = FORGE_OUTPUT / f"{m['id']}_final.stl"
            mesh.export(str(final_stl))
            size_b   = final_stl.stat().st_size
            size_str = f"{size_b // 1024}KB" if size_b >= 1024 else f"{size_b}B"
            _log(m, f"STL exporté: {final_stl.name} ({size_str})")
            m["files"]["final_stl"] = str(final_stl)

            # ── Sauvegarde automatique vers dossier Jarvis ──────
            import shutil
            JARVIS_STL_DIR = Path(
                os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL")
            )
            try:
                JARVIS_STL_DIR.mkdir(parents=True, exist_ok=True)
                # Nom de fichier : prompt nettoyé + ID
                safe_name = "".join(
                    c if c.isalnum() or c in " -_" else "_"
                    for c in m["prompt"][:40]
                ).strip().replace(" ", "_")
                dest = JARVIS_STL_DIR / f"{safe_name}_{m['id']}.stl"
                shutil.copy2(str(final_stl), str(dest))
                _log(m, f"STL sauvegardé: {dest}", "success")
                m["files"]["jarvis_stl"] = str(dest)
            except Exception as e:
                _log(m, f"Sauvegarde Jarvis échouée: {e}", "warning")

            # Auto-launch Bambu Studio si demandé
            if m.get("auto_bambu"):
                import subprocess
                bambu = os.getenv("BAMBU_STUDIO_PATH", r"C:\Program Files\Bambu Studio\bambu-studio.exe")
                if Path(bambu).exists():
                    subprocess.Popen([bambu, str(final_stl)], shell=False)
                    _log(m, f"Bambu Studio lancé: {final_stl.name}", "success")
                else:
                    _log(m, f"Bambu Studio introuvable: {bambu}", "warning")

            return final_stl

        final_stl_path = await _run_step("export", _do_export())

        # ── Étape 11 : Rapport de fabrication ────────────
        async def _do_report():
            if not final_stl_path or mesh is None:
                _log(m, "Export absent — rapport ignoré", "warning")
                return
            report = generate_report(
                mission_id=m["id"],
                mesh=mesh,
                validation=post_val,
                repair=repair,
                orientation=orient,
                stl_path=final_stl_path,
            )
            report_path = FORGE_REPORTS / f"{m['id']}_report.json"
            save_report(report, report_path)
            from dataclasses import asdict
            m["report"]       = asdict(report)
            m["files"]["report"] = str(report_path)
            _log(m, f"Rapport généré — Score: {report.printability_score}/100, Bambu-ready: {report.bambu_ready}")

            # ── Sauvegarde dans Vault Learning Database ──────
            try:
                from vault.forge_learning import save_forge_result
                await save_forge_result(m, m["report"])
                _log(m, "Forge analytics sauvegardés dans Vault", "success")
            except Exception as e:
                _log(m, f"Vault save skipped: {e}", "warning")

        await _run_step("report", _do_report())

        # ── Mission complète ──────────────────────────────
        m["status"]       = "completed"
        m["completed_at"] = datetime.now().isoformat()
        _log(m, "MISSION FORGE COMPLETE", "success")
        _save_cache(_forge_missions)

    except asyncio.TimeoutError:
        # Uniquement si un step bloquant (mesh_generation) a timeout
        m["status"] = "failed"
        m["error"]  = f"Timeout {STEP_TIMEOUT}s dépassé sur step bloquant (mesh_generation)"
        _log(m, f"PIPELINE ABORT: {m['error']}", "error")
        _save_cache(_forge_missions)

    except Exception as e:
        m["status"] = "failed"
        m["error"]  = str(e)
        _log(m, f"ERREUR PIPELINE: {e}\n{traceback.format_exc()}", "error")
        _save_cache(_forge_missions)
