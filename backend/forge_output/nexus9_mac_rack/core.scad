// ============================================================
//  NEXUS9 / OpenClaw — Mac Mini M4 Modular Stacking Rack
//  core.scad — shared parameters + reusable modules
//  Units: mm | Printer: Bambu X1C (256^3) | Support-free, flat base
//  Generated 2026-06-06
// ============================================================

// ----- Mac Mini M4 -----
mac_w = 127;
mac_d = 127;
mac_h = 50;
clearance = 3;            // air gap around each unit

// ----- Bay internal -----
inner_w = 135;            // internal width
inner_d = 140;            // internal depth
bay_h   = 62;             // per-module clear column height (mac_h + airflow)

// ----- Structure -----
wall     = 3;
floor_t  = 5;             // floor / shelf plate thickness (>= spigot recess + feat_min)
col      = 14;            // corner column cross-section (square)
feat_min = 1.5;

// derived footprint (4 corner columns around the inner volume)
out_w = inner_w + 2*col;     // 163
out_d = inner_d + 2*col;     // 168

// column corner centers — inset 1 mm from the floor edge so column outer faces
// are NOT coplanar with the floor edges (coincident faces stop CGAL from fusing
// the union into a single watertight body).
edge = 1.0;
cx = out_w/2 - col/2 - edge;
cy = out_d/2 - col/2 - edge;
corners = [[ cx, cy], [ cx,-cy], [-cx, cy], [-cx,-cy]];

// ----- M3 hardware -----
m3_clear  = 3.2;          // clearance hole
heatset_d = 4.6;          // heat-set insert pocket
heatset_h = 5;
m3_head   = 6.0;

// ----- Alignment pins -----
pin_d    = 5;
pin_len  = 8;
pin_fit  = 0.25;          // socket clearance
socket_d = pin_d + pin_fit;
socket_h = pin_len + 0.6;
pin_off  = 4;             // pin offset from column center (toward inner corner)

// ----- Stacking spigot (column top -> floor recess), shared by all parts -----
spigot   = col - 5;       // 9 mm square locating spigot
spigot_h = 3;
recess   = spigot + 2*pin_fit;

// ----- Airflow -----
vent_hole = 8;
vent_gap  = 4;            // wall between holes -> ~64% open area

// ----- Front panel interface (shared by EVERY panel variant) -----
panel_t        = 3;
panel_w        = out_w;        // 163 — covers the bay front
panel_h        = bay_h;        // 62
panel_border   = 9;            // solid frame (holds screws + strength)
panel_win_w    = panel_w - 2*panel_border;   // 145 — decorative window width
panel_win_h    = panel_h - 2*panel_border;   // 44  — decorative window height
panel_mount_dx = cx;           // screw holes align with bay front heat-sets (+-cx, mid)

$fn = 40;

// ---------- reusable modules ----------
module m3_clearance_hole(depth = 40) { cylinder(h = depth, d = m3_clear); }

module heatset_pocket() { cylinder(h = heatset_h + 0.2, d = heatset_d); }

module align_pin() { cylinder(h = pin_len, d = pin_d); }

module align_socket() { cylinder(h = socket_h, d = socket_d); }

// airflow grid filling an area w x d (centered), holes through thickness t
module airflow_grid(w, d, t) {
    step = vent_hole + vent_gap;
    nx = max(1, floor((w + vent_gap) / step));
    ny = max(1, floor((d + vent_gap) / step));
    ox = -(nx - 1) * step / 2;
    oy = -(ny - 1) * step / 2;
    for (i = [0 : nx - 1])
        for (j = [0 : ny - 1])
            translate([ox + i*step, oy + j*step, -0.1])
                cylinder(h = t + 0.2, d = vent_hole);
}

// Standard front-panel blank: plate + 2 side screw holes + 2 alignment pins.
// Every decorative panel variant starts from this so they are interchangeable.
// Panel lies in the XY plane, thickness along +Z. Decorative pattern is cut/added
// by the variant on top of this.
// Framed plate + 2 mount screw holes (align with the bay front heat-sets at
// +-cx, mid-height). Decorative pattern goes in the central window
// (panel_win_w x panel_win_h). Printed flat: plate in XY, thickness along +Z.
// Every variant starts from this so all panels are interchangeable.
module panel_blank() {
    difference() {
        translate([-panel_w/2, -panel_h/2, 0]) cube([panel_w, panel_h, panel_t]);
        for (sx = [-panel_mount_dx, panel_mount_dx])
            translate([sx, 0, -0.1]) cylinder(h = panel_t + 0.2, d = m3_clear);
    }
}

// Raised (embossed) text helper — 1.2 mm proud of the front face, per spec.
module emboss(txt, size = 7, y = 0) {
    translate([0, y, panel_t])
        linear_extrude(1.2)
            text(txt, size = size, halign = "center", valign = "center");
}
