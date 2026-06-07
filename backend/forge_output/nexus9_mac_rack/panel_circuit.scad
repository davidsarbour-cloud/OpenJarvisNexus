include <core.scad>

// ============================================================
//  panel_circuit.scad — CIRCUIT BOARD front panel
//  Raised PCB traces (thin cube strips) with right-angle turns,
//  raised round pads at junctions, and through-hole vias.
// ============================================================

trace_w  = 1.6;   // trace width (>= feat_min)
trace_h  = 1.3;   // raised height (>= 1.2)
pad_r    = 2.2;   // junction pad radius
via_d    = 2.0;   // through-hole via diameter

// One raised trace segment between two points (axis-aligned, right angles only).
// Sits on the front face: base at z = panel_t.
module trace(p0, p1) {
    x0 = p0[0]; y0 = p0[1];
    x1 = p1[0]; y1 = p1[1];
    len_x = abs(x1 - x0);
    len_y = abs(y1 - y0);
    // overlap the endpoints slightly so segments fuse cleanly
    sx = (len_x >= len_y) ? len_x + trace_w : trace_w;
    sy = (len_y >  len_x) ? len_y + trace_w : trace_w;
    translate([(x0 + x1)/2, (y0 + y1)/2, panel_t + trace_h/2])
        cube([sx, sy, trace_h], center = true);
}

// Raised round pad at a junction.
module pad(p) {
    translate([p[0], p[1], panel_t])
        cylinder(h = trace_h, r = pad_r);
}

// A routed track = ordered list of waypoints -> chained right-angle segments + pads.
module track(pts) {
    for (i = [0 : len(pts) - 2]) trace(pts[i], pts[i + 1]);
    for (i = [0 : len(pts) - 1]) pad(pts[i]);
}

// Through-hole via (cut through the plate, inside window).
module via(p) {
    translate([p[0], p[1], -0.1])
        cylinder(h = panel_t + 0.2, d = via_d);
}

// ----- Routing waypoints (all inside the window) -----
// window half-extents: |x| <= 72.5, |y| <= 22

trackA = [[-60, 14], [-30, 14], [-30, -10], [10, -10], [10, 8], [40, 8], [40, -14], [62, -14]];
trackB = [[-62, -16], [-46, -16], [-46, 16], [-12, 16], [-12, -16], [22, -16], [22, 14], [58, 14]];
trackC = [[-58, 0], [-8, 0], [-8, 18], [34, 18], [34, -2], [60, -2]];

// vias placed in open areas (NOT under any raised pad/trace)
vias = [[-52, 8], [4, 12], [48, 2], [-20, -14], [28, -8], [54, -16]];

module panel() {
    union() {
        difference() {
            panel_blank();
            for (v = vias) via(v);
        }
        track(trackA);
        track(trackB);
        track(trackC);
        emboss("PCB", 6, -panel_h/2 + 11);
    }
}

panel();
