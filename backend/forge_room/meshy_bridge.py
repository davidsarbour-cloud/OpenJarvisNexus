"""
Meshy AI bridge — génération STL via text-to-3D cloud.
Moteur primaire pour les formes organiques : animaux, figurines, créatures.
Réutilise la logique de stl_agent.py.
"""
from __future__ import annotations
import asyncio
import os
from pathlib import Path

import httpx

MESHY_API_KEY = os.getenv("MESHY_API_KEY", "")
MESHY_BASE    = "https://api.meshy.ai"


def is_available() -> bool:
    return bool(MESHY_API_KEY)


async def generate_stl_via_meshy(
    prompt: str,
    output_path: Path,
    style: str = "low-poly",
    timeout_s: int = 300,
) -> bool:
    """
    Soumet un job text-to-3D à Meshy AI, attend la complétion, télécharge le GLB,
    convertit en STL via trimesh. Retourne True si STL généré.
    """
    if not MESHY_API_KEY:
        print("[meshy] MESHY_API_KEY non configuré")
        return False

    headers = {
        "Authorization": f"Bearer {MESHY_API_KEY}",
        "Content-Type": "application/json",
    }

    enriched = (
        f"{prompt}, {style} style, single piece, flat base, "
        "FDM 3D print ready, no overhangs, support-free, clean topology"
    )
    negative = (
        "high poly, thin walls, overhangs, floating geometry, "
        "non-manifold, holes, multi-part, broken mesh"
    )

    async with httpx.AsyncClient(timeout=30) as c:
        # ── 1. Soumettre le job ─────────────────────────
        try:
            r = await c.post(
                f"{MESHY_BASE}/v2/text-to-3d",
                headers=headers,
                json={"mode": "preview", "prompt": enriched, "negative_prompt": negative},
            )
            if r.status_code not in (200, 201, 202):
                print(f"[meshy] submit error {r.status_code}: {r.text[:200]}")
                return False
            task_id = r.json().get("result") or r.json().get("id")
            if not task_id:
                print("[meshy] pas de task_id dans la réponse")
                return False
            print(f"[meshy] task {task_id} soumis")
        except Exception as e:
            print(f"[meshy] submit exception: {e}")
            return False

        # ── 2. Polling ──────────────────────────────────
        glb_url = None
        elapsed = 0
        async with httpx.AsyncClient(timeout=15) as poll_c:
            while elapsed < timeout_s:
                await asyncio.sleep(5)
                elapsed += 5
                try:
                    pr = await poll_c.get(
                        f"{MESHY_BASE}/v2/text-to-3d/{task_id}",
                        headers=headers,
                    )
                    d  = pr.json()
                    st = d.get("status", "")
                    pct = d.get("progress", 0)
                    print(f"[meshy] {st} {pct}%")

                    if st == "SUCCEEDED":
                        urls = d.get("model_urls", {})
                        glb_url = urls.get("glb") or urls.get("fbx") or urls.get("obj")
                        break
                    if st in ("FAILED", "EXPIRED"):
                        print(f"[meshy] task {st}: {d.get('task_error',{})}")
                        return False
                except Exception as e:
                    print(f"[meshy] poll error: {e}")

        if not glb_url:
            print("[meshy] pas d'URL GLB après timeout")
            return False

        # ── 3. Télécharger le GLB ───────────────────────
        glb_path = output_path.with_suffix(".glb")
        try:
            async with httpx.AsyncClient(timeout=60) as dl_c:
                resp = await dl_c.get(glb_url)
                resp.raise_for_status()
                glb_path.write_bytes(resp.content)
            print(f"[meshy] GLB téléchargé: {glb_path.stat().st_size // 1024}KB")
        except Exception as e:
            print(f"[meshy] download error: {e}")
            return False

        # ── 4. Convertir GLB → STL ──────────────────────
        try:
            import trimesh
            scene = trimesh.load(str(glb_path))
            # Extraire le mesh principal (scene ou mesh direct)
            if isinstance(scene, trimesh.Scene):
                meshes = [g for g in scene.geometry.values()
                          if isinstance(g, trimesh.Trimesh) and len(g.faces) > 0]
                if not meshes:
                    print("[meshy] scène GLB vide")
                    return False
                mesh = trimesh.util.concatenate(meshes)
            else:
                mesh = scene

            # Décimation pour FDM — max 60k faces (Bambu Studio optimal)
            original_faces = len(mesh.faces)
            max_faces = 60_000
            if original_faces > max_faces:
                try:
                    import fast_simplification
                    ratio = max_faces / original_faces
                    pts, faces = fast_simplification.simplify(
                        mesh.vertices, mesh.faces, target_reduction=1.0 - ratio
                    )
                    import numpy as np
                    mesh = trimesh.Trimesh(vertices=pts, faces=faces, process=False)
                    mesh.fix_normals()
                    print(f"[meshy] décimation: {original_faces} → {len(mesh.faces)} faces")
                except Exception as e:
                    print(f"[meshy] décimation impossible ({e}) — export brut")

            mesh.export(str(output_path))
            size_kb = output_path.stat().st_size // 1024
            print(f"[meshy] STL exporté: {output_path.name} ({size_kb}KB, {len(mesh.faces)} faces)")
            glb_path.unlink(missing_ok=True)
            return size_kb > 1
        except Exception as e:
            print(f"[meshy] conversion GLB→STL error: {e}")
            glb_path.unlink(missing_ok=True)
            return False
