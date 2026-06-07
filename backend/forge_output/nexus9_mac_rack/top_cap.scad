// ============================================================
//  NEXUS9 Mac Mini M4 Rack — top_cap.scad
//  Top plate. Sits on Bay 4 column spigots (underside recesses).
//  Top face has a recessed pocket for the interchangeable centre
//  logo plate + airflow.
// ============================================================
include <core.scad>

cap_t   = 6;
logo_w  = 70;
logo_h  = 40;
logo_pocket_depth = 2;

module top_cap() {
    difference() {
        translate([-out_w/2, -out_d/2, 0]) cube([out_w, out_d, cap_t]);
        // underside recesses receive Bay 4 column spigots
        for (c = corners)
            translate([c[0] - recess/2, c[1] - recess/2, -0.1])
                cube([recess, recess, spigot_h + 0.4]);
        // centre logo pocket on top (drop-in logo plate)
        translate([-logo_w/2, -logo_h/2, cap_t - logo_pocket_depth])
            cube([logo_w, logo_h, logo_pocket_depth + 0.1]);
        // 2 screw holes to retain the logo plate
        for (sx = [-logo_w/2 + 6, logo_w/2 - 6])
            translate([sx, 0, cap_t - logo_pocket_depth - 0.1])
                cylinder(h = cap_t, d = m3_clear);
        // airflow ring around the logo
        airflow_grid(inner_w - 20, inner_d - 20, cap_t);
    }
}

top_cap();
