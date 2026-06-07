// ============================================================
//  NEXUS9 Mac Mini M4 Rack — panel_custom.scad  (Customizable)
//  Honeycomb airflow mesh around a CENTERED raised blank plaque
//  the buyer can relabel. Embossed "YOUR LOGO HERE" placeholder.
//  Built on the shared panel_blank() so it is interchangeable.
// ============================================================
include <core.scad>

// ----- Plaque parameters (the customizable blank area) -----
plaque_w  = 70;     // plaque width
plaque_h  = 28;     // plaque height
plaque_r  = 3;      // corner radius
plaque_up = 1.0;    // raised height above front face
clear     = 2.0;    // keep honeycomb holes this far away from the plaque

// Honeycomb hole field filling w x h (centered), holes through thickness t.
// Holes that fall within the plaque keep-out rectangle are skipped so the
// plaque sits on solid plate (no cut-through under a raised feature).
module honeycomb(w, h, t, r = 6, wall = 2.4) {
    cw = (r + wall) * 1.5;
    rh = (r + wall) * 1.732;
    nx = ceil(w / cw) + 1;
    ny = ceil(h / rh) + 1;
    kx = plaque_w/2 + clear + r;   // keep-out half-width (hole center test)
    ky = plaque_h/2 + clear + r;   // keep-out half-height
    for (i = [-nx : nx])
        for (j = [-ny : ny]) {
            x = i * cw;
            y = j * rh + ((i % 2 != 0) ? rh / 2 : 0);
            inside_win = abs(x) <= w/2 - r*0.5 && abs(y) <= h/2 - r*0.5;
            in_plaque  = abs(x) <= kx && abs(y) <= ky;
            if (inside_win && !in_plaque)
                translate([x, y, -0.1]) rotate([0, 0, 30])
                    cylinder(h = t + 0.2, r = r, $fn = 6);
        }
}

// Rounded rectangle (2D) for the plaque footprint.
module rrect(w, h, rad) {
    hull() for (sx = [-1, 1]) for (sy = [-1, 1])
        translate([sx*(w/2 - rad), sy*(h/2 - rad)])
            circle(r = rad);
}

module panel_custom() {
    union() {
        difference() {
            panel_blank();
            // honeycomb fills the whole window, skipping the plaque keep-out
            honeycomb(panel_win_w, panel_win_h, panel_t);
        }
        // raised blank plaque, centered — the customizable area
        translate([0, 0, panel_t])
            linear_extrude(plaque_up)
                rrect(plaque_w, plaque_h, plaque_r);
        // placeholder text embossed on top of the plaque (two lines)
        translate([0, 0, plaque_up]) {
            emboss("YOUR LOGO",  size = 5.5, y =  5.5);
            emboss("HERE",       size = 5.5, y = -6.0);
        }
    }
}

panel_custom();
