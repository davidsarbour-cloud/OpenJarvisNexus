"""
Générateur OpenSCAD — DeepSeek Coder génère le script, OpenSCAD l'exporte en STL.
Hook préparé pour génération procédurale avancée.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from forge_room.deepseek_coder_bridge import generate_code_async

OPENSCAD_PATH = os.getenv("OPENSCAD_PATH", r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe")

_OPENSCAD_SYSTEM = """You are an OpenSCAD 2025 expert. Output ONLY valid OpenSCAD code. No explanations, no markdown, no comments.

MANDATORY RULES:
- Use ONLY these primitives: cube([x,y,z]), sphere(r=N), cylinder(h=N,r=N), translate([x,y,z]), rotate([x,y,z]), scale([x,y,z]), union(){}, difference(){}, hull(){}
- Root must be a single union(){} or difference(){}
- NO variables, NO modules, NO for loops, NO echo()
- ALL dimensions in millimeters
- Minimum wall thickness 1.2mm
- Object must sit flat at z=0 (translate to ensure z_min=0)
- Target size: 80-140mm longest dimension
- Every opening brace { must have matching closing brace }"""

_OPENSCAD_PROMPT_TEMPLATE = """Generate a single valid OpenSCAD script for: {description}

Context: {plan}

Output ONLY this structure (fill in dimensions):
union() {{
    // main body
    translate([0,0,HEIGHT/2]) cube([WIDTH,DEPTH,HEIGHT], center=true);
    // optional details using sphere(), cylinder(), hull()
}}

Rules: only cube/sphere/cylinder/translate/rotate/union/difference/hull. No variables. Dimensions in mm. Object base at z=0."""


async def generate_openscad_script(description: str, plan: str = "") -> str | None:
    """Génère un script OpenSCAD via DeepSeek Coder."""
    prompt = _OPENSCAD_PROMPT_TEMPLATE.format(description=description, plan=plan or description)
    return await generate_code_async(prompt, lang="openscad", system=_OPENSCAD_SYSTEM)


def openscad_to_stl(script_content: str, output_path: Path, timeout: int = 120) -> bool:
    """
    Exécute OpenSCAD en mode headless pour convertir un script en STL.
    Retourne True si le fichier STL a été généré.
    """
    if not Path(OPENSCAD_PATH).exists():
        print(f"[openscad] introuvable: {OPENSCAD_PATH} — set OPENSCAD_PATH in .env")
        return False

    with tempfile.NamedTemporaryFile(suffix=".scad", mode="w", delete=False, encoding="utf-8") as f:
        f.write(script_content)
        scad_path = Path(f.name)

    try:
        result = subprocess.run(
            [OPENSCAD_PATH, "-o", str(output_path), str(scad_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = output_path.exists() and output_path.stat().st_size > 100
        if not success:
            print(f"[openscad] échec — stderr: {result.stderr[-300:]}")
        return success
    except subprocess.TimeoutExpired:
        print(f"[openscad] timeout ({timeout}s)")
        return False
    except Exception as e:
        print(f"[openscad] erreur: {e}")
        return False
    finally:
        scad_path.unlink(missing_ok=True)


def is_available() -> bool:
    return Path(OPENSCAD_PATH).exists()


async def generate_stl_via_openscad(
    description: str,
    output_path: Path,
    plan: str = "",
) -> bool:
    """Pipeline complet : DeepSeek → OpenSCAD script → STL."""
    if not is_available():
        print(f"[openscad] introuvable: {OPENSCAD_PATH}")
        return False
    script = await generate_openscad_script(description, plan)
    if not script:
        print("[openscad] DeepSeek n'a pas généré de script")
        return False
    return openscad_to_stl(script, output_path)
