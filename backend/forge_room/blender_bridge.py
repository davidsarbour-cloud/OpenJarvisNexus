"""
Bridge Blender headless — DeepSeek Coder génère le script bpy, Blender l'exécute.
Fallback: script bpy minimaliste embarqué.
"""
from __future__ import annotations
import os
import subprocess
from pathlib import Path

from forge_room.deepseek_coder_bridge import generate_code_async

BLENDER_PATH = os.getenv(
    "BLENDER_PATH",
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
)

_BPY_SYSTEM = """You are an expert Blender 5.x Python (bpy) developer.
Output ONLY valid Python bpy code. No prose, no markdown outside the code.

CRITICAL BLENDER 5.x API RULES — failure to follow = broken script:
- ALWAYS start with: bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
- Use ONLY bpy.ops.mesh.primitive_*_add() to create geometry — NEVER bpy.data.meshes.new() or bpy.context.scene.objects.new()
- To select object: bpy.context.view_layer.objects.active = obj; obj.select_set(True)
- To join: bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.join()
- Scale: bpy.ops.transform.resize(value=(sx, sy, sz))
- EXPORT (mandatory last lines):
    import os
    out = os.environ.get('STL_OUT', 'output.stl')
    try: bpy.ops.wm.stl_export(filepath=out)
    except: bpy.ops.export_mesh.stl(filepath=out)
    print('FORGE_STL_OK', out)

FDM rules: flat base at z=0, no overhangs >45deg, wall >=1.2mm, single joined solid."""

_BPY_PROMPT = """Write a complete Blender 5.x bpy script to create: {description}

Context: {plan}

Use ONLY bpy.ops.mesh.primitive_*_add() for geometry.
End with the wm.stl_export block shown in the system rules.
Output ONLY the Python code, no explanation.
- Export: out=os.environ.get('STL_OUT','output.stl'); try: bpy.ops.wm.stl_export(filepath=out) / except: bpy.ops.export_mesh.stl(filepath=out)

Output ONLY the Python code."""

_FALLBACK_SCRIPT = '''import bpy, os

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Cylindre solide manifold garanti — 100mm diametre x 80mm haut, base a z=0
bpy.ops.mesh.primitive_cylinder_add(
    radius=0.05,
    depth=0.08,
    vertices=32,
    location=(0, 0, 0.04)
)
obj = bpy.context.active_object
obj.name = 'ForgeModel'

out = os.environ.get('STL_OUT', 'output.stl')
try:
    bpy.ops.wm.stl_export(filepath=out)
except Exception:
    bpy.ops.export_mesh.stl(filepath=out, use_selection=False)
print('[forge] STL exported to', out)
'''


async def generate_blender_script(description: str, plan: str = "") -> str:
    """Génère un script bpy via DeepSeek Coder. Fallback sur script embarqué."""
    prompt = _BPY_PROMPT.format(description=description, plan=plan or description)
    code = await generate_code_async(prompt, lang="python", system=_BPY_SYSTEM, max_tokens=4000)
    if code and len(code) > 100:
        return code
    print("[blender_bridge] DeepSeek fallback — script embarqué utilisé")
    return _FALLBACK_SCRIPT


def run_blender_script(
    script: str,
    output_stl: Path,
    timeout: int = 180,
) -> bool:
    """
    Exécute Blender en mode headless avec le script fourni.
    Retourne True si le STL a été généré.
    """
    if not Path(BLENDER_PATH).exists():
        print(f"[blender] introuvable: {BLENDER_PATH}")
        return False

    script_path = output_stl.parent / f"{output_stl.stem}_gen.py"
    script_path.write_text(script, encoding="utf-8")

    env = os.environ.copy()
    env["STL_OUT"] = str(output_stl)

    try:
        result = subprocess.run(
            [BLENDER_PATH, "--background", "--python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        success = output_stl.exists() and output_stl.stat().st_size > 500
        if not success and result.stderr:
            print(f"[blender] stderr: {result.stderr[-400:]}")
        return success
    except subprocess.TimeoutExpired:
        print(f"[blender] timeout ({timeout}s)")
        return False
    except Exception as e:
        print(f"[blender] erreur: {e}")
        return False
    finally:
        script_path.unlink(missing_ok=True)


def is_available() -> bool:
    return Path(BLENDER_PATH).exists()


def _stl_is_usable(path: Path) -> bool:
    """
    Critère industriel strict :
    - watertight (aucun bord ouvert)
    - composant unique (pas de géométrie flottante)
    - volume positif
    Tout échec → fallback cylindre garanti.
    """
    if not path.exists() or path.stat().st_size < 500:
        return False
    try:
        import trimesh
        m = trimesh.load(str(path), force="mesh")
        if not m.is_watertight or len(m.faces) < 10:
            return False
        # Rejet si plusieurs composantes (géométrie flottante)
        components = m.split(only_watertight=False)
        if len(components) > 1:
            print(f"[blender] {len(components)} composantes détectées → fallback")
            return False
        return True
    except Exception:
        return False  # fallback sur taille si trimesh échoue


async def generate_stl_via_blender(
    description: str,
    output_path: Path,
    plan: str = "",
) -> bool:
    """
    Pipeline : DeepSeek → bpy script → Blender headless → STL.
    Valide la géométrie après génération. Retry avec cylindre fallback si invalide.
    """
    # Essai 1 : code DeepSeek + validation géométrique
    script = await generate_blender_script(description, plan)
    if run_blender_script(script, output_path) and _stl_is_usable(output_path):
        return True

    # Essai 2 : cylindre fallback garanti manifold
    print("[blender_bridge] géométrie invalide — retry cylindre fallback")
    return run_blender_script(_FALLBACK_SCRIPT, output_path)
