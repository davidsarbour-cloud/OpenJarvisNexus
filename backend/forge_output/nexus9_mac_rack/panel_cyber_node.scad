include <core.scad>

// ============================================================
//  CYBERPUNK NODE panel — four stacked slot recesses
//  Each slot is cut 1.5 mm deep (NOT through) into the front face,
//  with a raised "NODE-0x" label embossed on the recess floor.
//  Industrial datacenter look.
// ============================================================

slot_depth = 1.5;            // recess depth (plate is 3 mm -> 1.5 mm remains)
n_slots    = 4;
row_pitch  = 10.0;           // vertical spacing between slot centers
slot_w     = 120;            // slot width (inside window 145)
slot_h     = 7.5;            // slot height
lbl_size   = 4;              // small text for the 44 mm window
lbl_rise   = 1.2;            // raised text height on the recess floor

// vertical centers for the 4 rows, centered in the window
function row_y(i) = (i - (n_slots - 1) / 2) * row_pitch;

module slot_cut(y) {
    // rounded rectangular pocket cut from the top face, slot_depth deep
    translate([0, y, panel_t - slot_depth])
        linear_extrude(slot_depth + 0.1)
            offset(r = 1.2) offset(delta = -1.2)
                square([slot_w, slot_h], center = true);
}

module node_label(txt, y) {
    // raised text sitting on the recess floor; total top sits below the
    // front face (floor at panel_t-slot_depth + rise = 1.5+1.2 = 2.7 < 3)
    translate([0, y, panel_t - slot_depth])
        linear_extrude(lbl_rise)
            text(txt, size = lbl_size, halign = "center", valign = "center",
                 font = "Liberation Mono:style=Bold");
}

module panel() {
    union() {
        difference() {
            panel_blank();
            for (i = [0 : n_slots - 1])
                slot_cut(row_y(i));
        }
        // raised labels inside each recess
        for (i = [0 : n_slots - 1])
            node_label(str("NODE-0", i + 1), row_y(i));
    }
}

panel();
