include <core.scad>

// ---- VENTILATION TURBINE ----
// Central solid hub + N curved tapered blades cut THROUGH the plate for airflow,
// inside a bounding circle. A thin solid outer rim is kept by the bounding circle
// staying inside the window.

N        = 9;                         // number of blades
bound_r  = panel_win_h/2 - 2;         // 20 mm bounding circle (fits inside window)
hub_r    = 5;                         // central solid hub radius
rim      = 1.8;                       // approx solid wall between blade tips and bound

// one tapered curved blade slot: hull of a small inner cylinder and a larger
// outer cylinder, offset radially -> a teardrop airflow slot. Rotated about Z to
// sweep, giving a swept (curved) impression across the N blades.
module blade_slot(t) {
    r_in  = hub_r + 1.6;              // start just outside hub
    r_out = bound_r - rim;           // stop before the outer rim
    // inner (narrow) end
    translate([0,0,-0.1])
        hull() {
            translate([r_in,  0, 0]) cylinder(h = t + 0.2, r = 1.2);
            // sweep the outer (wide) end angularly to make the slot look curved
            rotate([0,0,22]) translate([r_out, 0, 0]) cylinder(h = t + 0.2, r = 2.4);
        }
}

module turbine_cut(t) {
    intersection() {
        // keep all cuts inside the bounding circle
        translate([0,0,-0.2]) cylinder(h = t + 0.4, r = bound_r - rim/2);
        union() {
            for (k = [0 : N - 1])
                rotate([0, 0, k * 360 / N]) blade_slot(t);
        }
    }
}

module turbine() {
    union() {
        difference() {
            panel_blank();
            turbine_cut(panel_t);
        }
        // tiny raised mark at top of window, on solid plate (no cut beneath)
        emboss("//", 6, panel_win_h/2 + 4);
    }
}

turbine();
