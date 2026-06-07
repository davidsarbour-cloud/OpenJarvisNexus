// ============================================================
//  NEXUS9 Mac Mini M4 Rack — bay_module.scad
//  One stacking bay (holds 1 Mac Mini). 4 of these stack with
//  a base + top cap. Prints flat, support-free, on Bambu X1C.
// ============================================================
include <core.scad>

col_h    = floor_t + bay_h;   // full height incl. floor slab -> guarantees fusion
// spigot / spigot_h / recess are defined in core.scad (shared by all parts)

// One corner column: full-height square post (runs through the floor slab so the
// union is a single watertight body) + locating spigot on top.
// Stacking is spigot + glue (no capped heat-set here); screws hold the panels.
module column() {
    union() {
        translate([-col/2, -col/2, 0]) cube([col, col, col_h]);
        // locating spigot on top (mates the recess in the floor above)
        translate([-spigot/2, -spigot/2, col_h]) cube([spigot, spigot, spigot_h]);
    }
}

// Floor / shelf plate: airflow grid + corner spigot recesses + screw clearance.
module floor_plate() {
    difference() {
        translate([-out_w/2, -out_d/2, 0]) cube([out_w, out_d, floor_t]);
        airflow_grid(inner_w - 8, inner_d - 8, floor_t);
        for (c = corners) {
            // underside recess to receive the spigot of the module below
            // (alignment for stack; stacking is spigot + glue, screws hold panels)
            translate([c[0] - recess/2, c[1] - recess/2, -0.1])
                cube([recess, recess, spigot_h + 0.4]);
        }
    }
}

// Front (-Y) panel mounts: 2 horizontal heat-set pockets on the front columns.
module front_panel_mounts() {
    front = [[cx, -cy], [-cx, -cy]];
    for (c = front)
        translate([c[0], c[1] - col/2, floor_t + bay_h/2])
            rotate([-90, 0, 0]) heatset_pocket();   // pocket runs +Y into the column
}

module bay_module() {
    difference() {
        union() {
            floor_plate();
            for (c = corners) translate([c[0], c[1], 0]) column();
        }
        front_panel_mounts();
    }
}

bay_module();
