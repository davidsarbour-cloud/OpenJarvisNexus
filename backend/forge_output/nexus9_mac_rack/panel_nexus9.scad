// ============================================================
//  NEXUS9 Mac Mini M4 Rack — panel_nexus9.scad
//  "NEXUS9 DATACENTER" — sober enterprise text block:
//    NEXUS9 (large) over LOCAL AI / COMPUTE / CLUSTER, with a
//    thin raised rectangular frame around the text. No airflow
//    cuts: solid plate, all decoration raised 1.2 mm proud.
//  Built on the shared panel_blank() so it is interchangeable.
// ============================================================
include <core.scad>

// Thin raised rectangular outline frame (proud of the front face).
// Sits at z = panel_t, height = raised, wall thickness = fw.
module raised_frame(w, h, raised = 1.2, fw = 2.2) {
    translate([0, 0, panel_t])
        linear_extrude(raised)
            difference() {
                square([w, h], center = true);
                square([w - 2*fw, h - 2*fw], center = true);
            }
}

module panel_nexus9() {
    union() {
        // No cut-through pattern: keep the plate solid for the enterprise look.
        panel_blank();

        // Thin raised frame inside the window border.
        raised_frame(panel_win_w - 6, panel_win_h - 4, 1.2, 2.2);

        // Title — large, top of the window.
        emboss("NEXUS9",  9, 13.5);

        // Sub-lines — stacked at decreasing y across the 44 mm window.
        emboss("LOCAL AI", 5,  3.0);
        emboss("COMPUTE",  5, -4.5);
        emboss("CLUSTER",  5, -12.0);
    }
}

panel_nexus9();
