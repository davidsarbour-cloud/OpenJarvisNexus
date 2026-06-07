include <core.scad>

// APPLE PRO — clean symmetric perforation grid (round through-holes) in the
// lower window, embossed "PRO" at the top. Minimalist. No Apple logo.

hole_d  = 5;      // through-hole diameter
pitch   = 9;      // center-to-center spacing (both axes)

// Symmetric round-hole array centered in (w x h). Holes are cut through t.
// Count chosen so the grid is centered and stays inside the window margins.
module hole_grid(w, h, t, d = hole_d, p = pitch) {
    // keep at least d/2 + 0.5 margin from the area edge
    nx = floor((w - d) / p) + 1;
    ny = floor((h - d) / p) + 1;
    ox = -(nx - 1) * p / 2;
    oy = -(ny - 1) * p / 2;
    for (i = [0 : nx - 1])
        for (j = [0 : ny - 1])
            translate([ox + i * p, oy + j * p, -0.1])
                cylinder(h = t + 0.2, d = d);
}

module panel() {
    top_band = 16;                 // reserved top strip for "PRO" emboss
    grid_h   = panel_win_h - top_band;
    union() {
        difference() {
            panel_blank();
            // grid sits in the lower part of the window, shifted down by half the band
            translate([0, -top_band / 2, 0])
                hole_grid(panel_win_w, grid_h, panel_t);
        }
        emboss("PRO", 11, panel_h / 2 - 11);
    }
}

panel();
