// ============================================================
//  NEXUS9 Mac Mini M4 Rack — panel_neural.scad  (Variant: NEURAL)
//  Neural-network node graph emblem: ~10 raised node discs joined
//  by thin raised links (hull of two cylinders) + embossed "NEURAL".
//  Built on the shared panel_blank() so it is interchangeable.
// ============================================================
include <core.scad>

// ---- design parameters ----
node_r   = 2.5;     // node disc radius
node_h   = 1.4;     // raised height of nodes/links (>= 1.2 mm)
link_w   = 1.5;     // link bar width (>= feat_min)
graph_dy = -5;      // shift graph down to leave room for "NEURAL" title

// Node layout: organised in 3 columns (input / hidden / output) like a
// small neural net. Coords are within the window: |x|<=72.5, |y|<=22.
// All kept clear of the title band (top) and inside the window.
nodes = [
    // input layer (left)
    [-52,  10 + graph_dy],   // 0
    [-52,  -2 + graph_dy],   // 1
    [-52, -14 + graph_dy],   // 2
    // hidden layer (middle)
    [ -8,  14 + graph_dy],   // 3
    [ -8,   2 + graph_dy],   // 4
    [ -8, -10 + graph_dy],   // 5
    [ -8, -20 + graph_dy],   // 6
    // output layer (right)
    [ 44,   8 + graph_dy],   // 7
    [ 44,  -6 + graph_dy],   // 8
    [ 44, -18 + graph_dy]    // 9
];

// Edges connecting layers (a tidy feed-forward graph).
edges = [
    [0,3],[0,4],[1,4],[1,5],[2,5],[2,6],
    [3,7],[4,7],[4,8],[5,8],[5,9],[6,9]
];

// A raised link bar between two node centres (hull of two short cylinders).
module link(a, b) {
    translate([0, 0, panel_t])
        linear_extrude(node_h)
            hull() {
                translate(a) circle(d = link_w);
                translate(b) circle(d = link_w);
            }
}

// A raised node disc.
module node(p) {
    translate([p[0], p[1], panel_t])
        cylinder(h = node_h, r = node_r);
}

module panel_neural() {
    union() {
        panel_blank();                 // base plate + screw holes (solid)
        // links first (under nodes; they overlap and fuse into one solid)
        for (e = edges) link(nodes[e[0]], nodes[e[1]]);
        // nodes on top of the links
        for (p = nodes) node(p);
        // embossed title near the top of the window
        emboss("NEURAL", size = 8, y = panel_h/2 - 11);
    }
}

panel_neural();
