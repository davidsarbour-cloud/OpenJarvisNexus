"""
Système de réparation automatique de mesh.
Séquence : normales → vertices → pymeshfix → holes → floating → voxel (dernier recours).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
import trimesh

_RULES = json.loads((Path(__file__).parent / "manufacturing_rules.json").read_text())


@dataclass
class RepairResult:
    success: bool
    repairs_applied: list[str] = field(default_factory=list)
    iterations: int = 0
    pre_watertight: bool = False
    post_watertight: bool = False
    error: str | None = None


def auto_repair(mesh: trimesh.Trimesh, max_iterations: int | None = None) -> tuple[trimesh.Trimesh, RepairResult]:
    """
    Applique la séquence de réparation complète.
    Retourne (mesh_réparé, RepairResult).
    """
    rules = _RULES["repair"]
    max_iter = max_iterations or rules["max_repair_iterations"]
    repairs: list[str] = []
    pre_watertight = bool(mesh.is_watertight)

    try:
        mesh = mesh.copy()

        for iteration in range(1, max_iter + 1):
            changed = False

            # 1. Fusion des vertices dupliqués
            if rules["auto_merge_vertices"]:
                before = len(mesh.vertices)
                mesh.merge_vertices()
                after = len(mesh.vertices)
                if before != after:
                    repairs.append(f"Merge vertices: {before - after} supprimés")
                    changed = True

            # 2. Correction des normales
            if rules["auto_fix_normals"]:
                trimesh.repair.fix_normals(mesh)
                trimesh.repair.fix_winding(mesh)
                repairs.append("Normales corrigées")
                changed = True

            # 3. Suppression des faces dégénérées
            degen = mesh.area_faces < 1e-10
            if degen.any():
                keep = ~degen
                mesh.update_faces(keep)
                repairs.append(f"Faces dégénérées supprimées: {degen.sum()}")
                changed = True

            # 4. pymeshfix — réparation manifold robuste
            if rules["use_pymeshfix"]:
                try:
                    import pymeshfix
                    mf = pymeshfix.MeshFix(mesh.vertices, mesh.faces)
                    mf.repair()
                    repaired = trimesh.Trimesh(vertices=mf.points, faces=mf.faces, process=False)
                    if len(repaired.faces) > 0:
                        mesh = repaired
                        repairs.append(f"pymeshfix: {len(mesh.faces)} faces après réparation")
                        changed = True
                except Exception as e:
                    repairs.append(f"pymeshfix erreur: {e}")

            # 5. Fermeture des trous (fill holes)
            if rules["auto_fill_holes"] and not mesh.is_watertight:
                trimesh.repair.fill_holes(mesh)
                if mesh.is_watertight:
                    repairs.append("Trous fermés — mesh watertight")
                    changed = True

            # 6. Suppression de la géométrie flottante
            if rules["auto_remove_floating"]:
                components = mesh.split(only_watertight=False)
                if len(components) > 1:
                    # Garde uniquement la plus grande composante
                    z_min_global = mesh.bounds[0][2]
                    grounded = [
                        c for c in components
                        if (c.bounds[0][2] - z_min_global) <= 0.5
                    ]
                    if grounded:
                        main = max(grounded, key=lambda m: len(m.faces))
                        if len(main.faces) < len(mesh.faces):
                            removed = len(mesh.faces) - len(main.faces)
                            mesh = main
                            repairs.append(f"Géométrie flottante supprimée: {len(components)-1} composante(s), {removed} faces")
                            changed = True

            if mesh.is_watertight:
                break

            if not changed:
                break

        # 7. Voxel remesh — dernier recours si toujours non-watertight
        if not mesh.is_watertight:
            pitch_mm = rules["voxel_pitch_mm"]
            try:
                voxels = mesh.voxelized(pitch=pitch_mm)
                remeshed = voxels.marching_cubes
                if remeshed and len(remeshed.faces) > 0 and remeshed.is_watertight:
                    mesh = remeshed
                    repairs.append(f"Voxel remesh appliqué (pitch={pitch_mm}mm) — watertight restauré")
                else:
                    repairs.append("Voxel remesh tenté — résultat non-watertight")
            except Exception as e:
                repairs.append(f"Voxel remesh échoué: {e}")

        post_watertight = bool(mesh.is_watertight)

        return mesh, RepairResult(
            success=post_watertight,
            repairs_applied=repairs,
            iterations=min(max_iter, len(repairs)),
            pre_watertight=pre_watertight,
            post_watertight=post_watertight,
        )

    except Exception as e:
        return mesh, RepairResult(
            success=False,
            repairs_applied=repairs,
            error=str(e),
        )


def scale_to_target(mesh: trimesh.Trimesh, target_mm: float = 150.0) -> trimesh.Trimesh:
    """Redimensionne le mesh pour que la dimension la plus grande = target_mm."""
    extents = mesh.bounding_box.extents
    longest = max(extents)
    if longest > 0:
        factor = target_mm / longest
        mesh = mesh.apply_scale(factor)
    return mesh


def place_on_build_plate(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Translate le mesh pour que Z_min = 0 (posé sur la build plate)."""
    z_min = mesh.bounds[0][2]
    mesh.apply_translation([0.0, 0.0, -z_min])
    return mesh
