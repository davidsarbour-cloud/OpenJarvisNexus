// ============================================================
//  NEXUS9 Mac Mini M4 Rack — logo.scad
//  Drop-in centre logo plate for the top_cap pocket (70x40x2).
//  Replaceable: swap the text/emblem for a custom brand.
// ============================================================
include <core.scad>

lw = 68; lh = 38; lt = 2;        // fits the top_cap logo pocket with clearance

module logo() {
    union() {
        difference() {
            translate([-lw/2, -lh/2, 0]) cube([lw, lh, lt]);
            for (sx = [-29, 29])
                translate([sx, 0, -0.1]) cylinder(h = lt + 0.2, d = m3_clear);
        }
        // raised brand text
        translate([0, 0, lt])
            linear_extrude(1.2)
                text("NEXUS9", size = 12, halign = "center", valign = "center");
    }
}

logo();
