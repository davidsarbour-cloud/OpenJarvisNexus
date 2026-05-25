"""
Skill Tools — gestion des skills JARVIS via Claude tool_use.

Skills = fichiers TOML dans SKILLS_DIR.
Aucune dépendance openjarvis — standalone.
Format TOML :
    [skill]
    name        = "mon-skill"
    description = "Ce que fait ce skill"

    [[skill.steps]]
    tool_name          = "docker_status"
    arguments_template = '{}'
    output_key         = "result"
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SKILLS_DIR = Path(os.getenv("SKILLS_DIR", "/app/skills"))

# Répertoire supplémentaire : skills Hermes/OpenClaw installés via CLI
_HERMES_DIR = Path(os.getenv("HERMES_SKILLS_DIR", "/app/skills/hermes"))


# ── TOML parser minimal (Python 3.11 = tomllib std, sinon fallback) ──────────

def _toml_loads(text: str) -> dict:
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(text)
    except ImportError:
        try:
            import tomli  # fallback pip package
            return tomli.loads(text)
        except ImportError:
            pass
    # Fallback artisanal — couvre le subset utilisé
    result: dict = {"skill": {}}
    section: str | None = None
    current_step: dict | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "[skill]":
            section = "skill"
            current_step = None
        elif line == "[[skill.steps]]":
            result["skill"].setdefault("steps", [])
            current_step = {}
            result["skill"]["steps"].append(current_step)
            section = "step"
        elif "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            # Nettoie les guillemets
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if section == "step" and current_step is not None:
                current_step[key] = val
            elif section == "skill":
                result["skill"][key] = val
    return result


# ── Helpers internes ─────────────────────────────────────────────────────────

def _skill_path(name: str) -> Path:
    return SKILLS_DIR / f"{name}.toml"


def _parse_skill_md(path: Path) -> dict:
    """Parse un SKILL.md avec frontmatter YAML (format Hermes)."""
    text = path.read_text(encoding="utf-8")
    name = path.parent.name  # le dossier = le nom
    description = ""
    content = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            content = parts[2].strip()
            for line in fm.splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip('"\'')
                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"\'')

    return {
        "name":        name,
        "description": description,
        "steps":       [],          # skills Hermes = instructions markdown, pas steps TOML
        "content":     content,
        "format":      "markdown",
    }


def _read_skill(path: Path) -> dict:
    if path.is_dir():
        md = path / "SKILL.md"
        if md.exists():
            return _parse_skill_md(md)
        return {"name": path.name, "description": "?", "steps": [], "content": "", "format": "dir"}
    data = _toml_loads(path.read_text(encoding="utf-8")).get("skill", {})
    return {
        "name":        data.get("name", path.stem),
        "description": data.get("description", ""),
        "steps":       data.get("steps", []),
        "content":     "",
        "format":      "toml",
    }


def _all_skills() -> list[dict]:
    seen: set[str] = set()
    skills = []

    def _add(path: Path) -> None:
        try:
            s = _read_skill(path)
            n = s["name"]
            if n in seen:
                return
            seen.add(n)
            skills.append({
                "name":        n,
                "description": s["description"],
                "step_count":  len(s["steps"]),
                "format":      s.get("format", "toml"),
            })
        except Exception:
            skills.append({"name": path.name, "description": "?", "step_count": 0, "format": "?"})

    # TOML perso
    if SKILLS_DIR.exists():
        for f in sorted(SKILLS_DIR.glob("*.toml")):
            _add(f)

    # Hermes / dossiers avec SKILL.md
    hermes_root = SKILLS_DIR / "hermes"
    if hermes_root.exists():
        for d in sorted(hermes_root.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                _add(d)

    return skills


# ── API publique ─────────────────────────────────────────────────────────────

def skill_list() -> dict:
    skills = _all_skills()
    return {"ok": True, "skills": skills, "total": len(skills)}


def skill_get(name: str) -> dict:
    # 1. Cherche TOML perso
    toml_path = _skill_path(name)
    if toml_path.exists():
        try:
            s = _read_skill(toml_path)
            s["ok"] = True
            return s
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # 2. Cherche dans hermes/
    hermes_path = SKILLS_DIR / "hermes" / name
    if hermes_path.is_dir() and (hermes_path / "SKILL.md").exists():
        try:
            s = _read_skill(hermes_path)
            s["ok"] = True
            return s
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {"ok": False, "error": f"Skill introuvable : {name}"}


def skill_create(name: str, description: str, steps: list[dict]) -> dict:
    if not name:
        return {"ok": False, "error": "name requis"}
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = _skill_path(name)
    lines = [
        "[skill]",
        f'name = "{name}"',
        f'description = "{description}"',
        "",
    ]
    for step in steps:
        lines.append("[[skill.steps]]")
        lines.append(f'tool_name = "{step.get("tool_name", "")}"')
        if "arguments_template" in step:
            tpl = step["arguments_template"].replace("'", '"')
            lines.append(f"arguments_template = '{tpl}'")
        if "output_key" in step:
            lines.append(f'output_key = "{step["output_key"]}"')
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "name": name, "path": str(path), "steps": len(steps)}


def skill_delete(name: str) -> dict:
    path = _skill_path(name)
    if not path.exists():
        return {"ok": False, "error": f"Skill introuvable : {name}"}
    path.unlink()
    return {"ok": True, "name": name}


# ── Injection système : liste compacte pour le prompt ────────────────────────

def skill_catalog_text() -> str:
    """Retourne une ligne par skill pour injection dans le system prompt."""
    skills = _all_skills()
    if not skills:
        return ""
    lines = ["[Skills JARVIS disponibles]"]
    for s in skills:
        lines.append(f"  {s['name']}: {s['description']}")
    return "\n".join(lines)


# ── Définitions outils pour Claude tool_use ───────────────────────────────────

CLAUDE_TOOL_DEFS = [
    {
        "name": "skill_list",
        "description": (
            "Liste toutes les skills JARVIS installées avec leur description. "
            "Utilise cet outil quand l'utilisateur demande quelles compétences "
            "ou procédures existent, ou ce que JARVIS sait faire."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "skill_get",
        "description": (
            "Charge le contenu complet d'une skill par son nom — description + "
            "étapes. Utilise cet outil avant d'exécuter une skill."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom exact de la skill (ex: docker-health)",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "skill_create",
        "description": (
            "Crée ou met à jour une skill procédurale réutilisable. "
            "Utilise cet outil quand tu identifies un pattern que David répète "
            "souvent et qui mérite d'être mémorisé comme skill."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom slug de la skill (ex: docker-health-check)",
                },
                "description": {
                    "type": "string",
                    "description": "Ce que fait la skill en 1 phrase",
                },
                "steps": {
                    "type": "array",
                    "description": "Étapes séquentielles avec tool_name",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool_name":          {"type": "string"},
                            "arguments_template": {"type": "string"},
                            "output_key":         {"type": "string"},
                        },
                        "required": ["tool_name"],
                    },
                },
            },
            "required": ["name", "description", "steps"],
        },
    },
    {
        "name": "skill_delete",
        "description": "Supprime une skill installée par son nom.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom de la skill à supprimer",
                },
            },
            "required": ["name"],
        },
    },
]


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch(tool_name: str, tool_input: dict) -> str:
    try:
        if tool_name == "skill_list":
            result = skill_list()
        elif tool_name == "skill_get":
            result = skill_get(name=tool_input.get("name", ""))
        elif tool_name == "skill_create":
            result = skill_create(
                name=tool_input.get("name", ""),
                description=tool_input.get("description", ""),
                steps=tool_input.get("steps", []),
            )
        elif tool_name == "skill_delete":
            result = skill_delete(name=tool_input.get("name", ""))
        else:
            result = {"ok": False, "error": f"Outil inconnu : {tool_name}"}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    return json.dumps(result, ensure_ascii=False, indent=2)
