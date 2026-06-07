// ============================================================
//  NEXUS9 Mac Mini M4 Rack — panel_ollama.scad  (Variant: OLLAMA)
//  Stylised geometric llama silhouette RAISED 1.5 mm on the front
//  face, airflow vents in the window, embossed "OLLAMA" at bottom.
//  Built on the shared panel_blank() so it is interchangeable.
// ============================================================
include <core.scad>

llama_h = 1.5;   // raised height of the llama silhouette (>=1.2)

// ---- 2D building blocks for the llama (drawn in XY, extruded later) ----

// rounded rectangle via hull of 4 corner circles
module rrect(w, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx * (w/2 - r), sy * (h/2 - r)]) circle(r = r);
}

// Stylised llama silhouette, centered roughly on origin, ~38 mm tall.
// Body + upright neck + head + 2 ears + 4 short legs. All one fused 2D blob
// so the raised extrusion is a single connected solid sitting on the plate.
module llama_2d() {
    union() {
        // body (rounded rect)
        translate([2, 0]) rrect(26, 14, 5);
        // neck (upright, leaning slightly forward over the front of the body)
        translate([13, 11]) rotate(12) rrect(8, 22, 3.5);
        // head (rounded rect on top of the neck)
        translate([16, 21]) rotate(-8) rrect(12, 8, 3.5);
        // snout nub forward of the head
        translate([22, 19]) rrect(6, 6, 2.5);
        // ears (two little triangles on top of the head)
        translate([14.5, 26]) rotate(15) square([3, 6], center = true);
        translate([17.5, 26.5]) rotate(-10) square([3, 6], center = true);
        // legs (four short stubs hanging from the body underside)
        for (lx = [-7, -1, 7, 13])
            translate([lx, -11]) rrect(4, 10, 1.8);
    }
}

// Airflow slots flanking the llama (kept INSIDE the window).
module side_vents(t) {
    slot_w = 3.5; slot_h = 22; gap = 6.5;
    // left bank
    for (i = [0 : 2])
        translate([-panel_win_w/2 + 8 + i*gap, 6, -0.1])
            linear_extrude(t + 0.2) rrect(slot_w, slot_h, slot_w/2);
    // right bank
    for (i = [0 : 2])
        translate([panel_win_w/2 - 8 - i*gap, 6, -0.1])
            linear_extrude(t + 0.2) rrect(slot_w, slot_h, slot_w/2);
}

module panel_ollama() {
    text_band = 13;            // solid band at the bottom for the text
    llama_cx = 0;              // llama horizontal center
    // keep the whole silhouette (ears highest ~+29, legs lowest ~-16) inside
    // the plate: top edge is panel_h/2 = 31, so center at -1 leaves ~1 mm margin
    llama_cy = -1;
    union() {
        difference() {
            panel_blank();
            // airflow vents in the window, clear of where the text sits
            side_vents(panel_t);
        }
        // raised llama silhouette on the front face (over solid plate)
        translate([llama_cx, llama_cy, panel_t])
            linear_extrude(llama_h)
                llama_2d();
        // embossed title near the bottom of the window
        emboss("OLLAMA", size = 9, y = -panel_h/2 + 9);
    }
}

panel_ollama();
