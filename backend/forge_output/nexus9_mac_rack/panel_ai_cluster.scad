// ============================================================
//  NEXUS9 Mac Mini M4 Rack — panel_ai_cluster.scad  (Variant 01)
//  Hexagonal honeycomb airflow mesh + embossed "AI CLUSTER".
//  Built on the shared panel_blank() so it is interchangeable.
// ============================================================
include <core.scad>

// Honeycomb hole field filling w x h (centered), holes through thickness t.
module honeycomb(w, h, t, r = 6, wall = 2.4) {
    cw = (r + wall) * 1.5;
    rh = (r + wall) * 1.732;
    nx = ceil(w / cw) + 1;
    ny = ceil(h / rh) + 1;
    for (i = [-nx : nx])
        for (j = [-ny : ny]) {
            x = i * cw;
            y = j * rh + ((i % 2 != 0) ? rh / 2 : 0);
            if (abs(x) <= w/2 - r*0.5 && abs(y) <= h/2 - r*0.5)
                translate([x, y, -0.1]) rotate([0, 0, 30])
                    cylinder(h = t + 0.2, r = r, $fn = 6);
        }
}

module panel_ai_cluster() {
    text_band = 16;                 // solid band at top for the text
    union() {
        difference() {
            panel_blank();
            // honeycomb fills the window BELOW the text band
            translate([0, -text_band/2, 0])
                honeycomb(panel_win_w, panel_win_h - text_band, panel_t);
        }
        // embossed title near the top of the window
        emboss("AI CLUSTER", size = 8, y = panel_h/2 - 11);
    }
}

panel_ai_cluster();
