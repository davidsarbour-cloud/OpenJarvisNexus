// ============================================================
//  NEXUS9 Mac Mini M4 Rack — base.scad
//  Bottom plate. Bay 1 sits on this; its floor recesses receive
//  the base's locating spigots. Flat bottom, airflow grid.
// ============================================================
include <core.scad>

base_t = 6;

module base() {
    difference() {
        union() {
            translate([-out_w/2, -out_d/2, 0]) cube([out_w, out_d, base_t]);
            // locating spigots on top (mate Bay 1 floor underside recesses)
            for (c = corners)
                translate([c[0] - spigot/2, c[1] - spigot/2, base_t])
                    cube([spigot, spigot, spigot_h]);
        }
        // bottom airflow
        airflow_grid(inner_w - 10, inner_d - 10, base_t);
    }
}

base();
