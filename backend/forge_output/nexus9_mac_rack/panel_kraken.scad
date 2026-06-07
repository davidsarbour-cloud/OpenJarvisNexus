include <core.scad>

// ============================================================
//  NEXUS9 Front Panel — KRAKEN
//  OPENCLAW kraken emblem: raised head + 6 curving tentacles.
//  Emblem sits on the solid plate (raised 1.5 mm). "OPENCLAW" embossed.
// ============================================================

raise_h = 1.5;          // raised height of the emblem
head_r  = 8;            // central head radius
emblem_cy = 2;          // emblem vertical center (leave room for text below)

// one tentacle: a curving chain of shrinking circles, hull()'d segment-to-segment
module tentacle(ang, len = 17, seg = 7, r0 = 4.0, curl = 34) {
    rotate([0, 0, ang]) {
        for (i = [0 : seg - 1]) {
            // parametric position along the arm, base near head edge
            t0 = i / seg;
            t1 = (i + 1) / seg;
            // arc curving sideways as it extends
            a0 = curl * t0;
            a1 = curl * t1;
            d0 = head_r - 1 + len * t0;
            d1 = head_r - 1 + len * t1;
            x0 = d0 * cos(a0); y0 = d0 * sin(a0);
            x1 = d1 * cos(a1); y1 = d1 * sin(a1);
            rr0 = r0 * (1 - t0) + 0.9;   // taper toward the tip
            rr1 = r0 * (1 - t1) + 0.9;
            hull() {
                translate([x0, y0, 0]) cylinder(h = raise_h, r = rr0);
                translate([x1, y1, 0]) cylinder(h = raise_h, r = rr1);
            }
        }
    }
}

module kraken() {
    translate([0, emblem_cy, panel_t]) {
        // central head
        cylinder(h = raise_h, r = head_r);
        // 6 tentacles radiating out, all curling the same direction (spiral feel)
        for (k = [0 : 5])
            tentacle(60 * k - 90);
    }
}

module panel() {
    union() {
        panel_blank();          // solid framed plate, no cut-through (silhouette emblem)
        kraken();               // raised emblem on the front face
        emboss("OPENCLAW", 7, -panel_h/2 + 7);   // raised text near bottom border
    }
}

panel();
