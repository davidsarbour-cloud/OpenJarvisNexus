# NEXUS9 / OpenClaw — Mac Mini M4 Modular Rack
## Assembly Guide & Print Manual

A premium modular, stackable 3D-printable rack for up to **4 Mac Mini M4** units.
Designed for **Bambu Lab X1C** (every part prints flat, support-free).

---

## 1. Bill of Materials (printed parts)

| Part | File | Qty |
|------|------|-----|
| Base plate | `Nexus9_Base.stl` | 1 |
| Bay module | `Nexus9_BayModule.stl` | 4 |
| Top cap | `Nexus9_TopCap.stl` | 1 |
| Centre logo plate | `Nexus9_Logo.stl` | 1 |
| Front panel (pick your designs) | `Nexus9_Panel_*.stl` | 4 (10 designs available) |

**10 interchangeable panel designs:** AICluster · ApplePro · NeuralNetwork ·
Kraken · CyberpunkNode · Ollama · CircuitBoard · Turbine · Nexus9Datacenter ·
Customizable.

## 2. Hardware

| Item | Spec | Qty |
|------|------|-----|
| M3 heat-set inserts | 4.6 mm OD, 5 mm long | 10 (8 panels + 2 logo) |
| M3 screws | cap head, 8–10 mm | 10 |
| Super glue / CA (optional) | for stacking spigots | — |

> **Two assembly methods supported:** stack with **glue** on the spigots (fast),
> or rely on the **spigot friction fit** + screws on the panels. Heat-set inserts
> are only needed if you want the panels/logo screwed (recommended).

## 3. Print settings (Bambu X1C)

- Material: **PLA / PLA+ / PETG / ABS**
- Layer height: **0.20 mm**
- Walls: **3+** (min wall 2 mm in the model)
- Infill: **15–20 %** (gyroid)
- **Supports: OFF** — all parts are flat-base, support-free
- Orientation: print every part as exported (flat on the bed)
- Airflow: panels & shelves are ~60–65 % open — intake/exhaust stay clear

Per-part footprints (all ≤ 256 mm, X1C-safe):
- Base 163 × 168 × 9 mm · Bay 163 × 168 × 70 mm · Top cap 163 × 168 × 6 mm ·
  Panels 163 × 62 × ~4 mm · Logo 68 × 38 × 3 mm

## 4. Assembly steps

1. **Print** the base, 4 bay modules, top cap, logo, and your 4 chosen panels.
2. **Heat-set inserts** — with a soldering iron, press an M3 insert into each of
   the 2 front-column pockets of every bay (8 total) and the 2 logo holes in the
   top cap (2 total).
3. **Stack the structure** (alignment is automatic via the corner spigots):
   `Base → Bay 1 → Bay 2 → Bay 3 → Bay 4 → Top cap`.
   Each part's spigots drop into the recesses of the part above. Add a dab of glue
   on the spigots for a permanent build, or leave friction-fit to keep it modular.
4. **Insert a Mac Mini M4** into each bay (2–3 mm clearance all around; the floor
   airflow grid keeps the intake/exhaust clear).
5. **Mount a front panel** on each bay: align its 2 side holes with the front-column
   inserts and drive 2 M3 screws. Swap any panel later by removing 2 screws.
6. **Centre logo:** drop `Nexus9_Logo.stl` into the top-cap pocket and screw it down.
   Replace it with your own brand plate (see `logo.scad`) for white-label units.

Assembled size: **163 × 174 × ~281 mm**.

## 5. Files in this package

- **STL** — `Nexus9_*.stl` (14 print files: base, bay, top cap, logo, 10 panels)
- **3MF** — `Nexus9_Rack_Assembly.3mf` (positioned assembly project)
- **Exploded diagram** — `Nexus9_Rack_Exploded.png`
- **Parametric source (OpenSCAD)** — `core.scad` + per-part `.scad` (edit dims,
  tolerances, hardware in `core.scad` to re-generate everything)
- **Assembly rebuild** — `assembly_build.py` (regenerates the 3MF)

## 6. Customising

All dimensions, tolerances, M3/heat-set/pin specs and airflow live in **`core.scad`**.
Change a value there and re-render any part:

```
"C:\Program Files\OpenSCAD\openscad.exe" -o Nexus9_BayModule.stl bay_module.scad
```

Add a new panel design: copy any `panel_*.scad`, keep `panel_blank()` as the base,
and draw your pattern inside the `panel_win_w × panel_win_h` window.

---

*NEXUS9 / OpenClaw — Local AI Compute Cluster. Generated 2026-06-06.*
