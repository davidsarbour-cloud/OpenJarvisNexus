"""Build the Nexus9 Mac Mini M4 rack assembly as a positioned 3MF project.
base -> 4x bay_module -> top_cap -> logo, with 4 sample front panels.
Run: backend/.venv/Scripts/python.exe assembly_build.py
"""
import os

import numpy as np
import trimesh

D = os.path.dirname(os.path.abspath(__file__))
def L(n):
    return trimesh.load(os.path.join(D, n))

PITCH = 67          # vertical stack pitch per bay (floor_t 5 + bay_h 62)
FRONT_Y = -84.0     # rack front face (-out_d/2)

scene = trimesh.Scene()

base = L("Nexus9_Base.stl")
scene.add_geometry(base, node_name="Base")

# rotate panels from flat (XY) to vertical on the front face
Rx = trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0])
sample_panels = [
    "Nexus9_Panel_AICluster.stl",
    "Nexus9_Panel_Kraken.stl",
    "Nexus9_Panel_Nexus9Datacenter.stl",
    "Nexus9_Panel_Ollama.stl",
]

for i in range(4):
    z = 6 + i * PITCH
    bay = L("Nexus9_BayModule.stl")
    bay.apply_translation([0, 0, z])
    scene.add_geometry(bay, node_name=f"Bay{i+1}")
    p = L(sample_panels[i])
    p.apply_transform(Rx)
    p.apply_translation([0, FRONT_Y - 1.5, z + 36])   # front face, bay mid-height
    scene.add_geometry(p, node_name=f"Panel{i+1}")

top_z = 6 + 4 * PITCH      # 274
top = L("Nexus9_TopCap.stl")
top.apply_translation([0, 0, top_z])
scene.add_geometry(top, node_name="TopCap")

logo = L("Nexus9_Logo.stl")
logo.apply_translation([0, 0, top_z + 4])
scene.add_geometry(logo, node_name="Logo")

out = os.path.join(D, "Nexus9_Rack_Assembly.3mf")
scene.export(out)
size = [round(float(x), 1) for x in (scene.bounds[1] - scene.bounds[0])]
print("3MF written:", os.path.basename(out))
print("parts:", len(scene.geometry), "| assembly size mm:", size)
