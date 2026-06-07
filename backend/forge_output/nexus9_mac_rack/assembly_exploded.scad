// ============================================================
//  NEXUS9 Mac Mini M4 Rack — assembly_exploded.scad
//  Exploded assembly diagram (imports the rendered STLs).
//  Render PNG:
//   openscad -o exploded.png --imgsize=900,1500 --autocenter --viewall assembly_exploded.scad
// ============================================================
g = 45;   // explosion gap

zpos  = [0, 54, 169, 284, 399, 514, 565];
files = ["Nexus9_Base.stl",
         "Nexus9_BayModule.stl", "Nexus9_BayModule.stl",
         "Nexus9_BayModule.stl", "Nexus9_BayModule.stl",
         "Nexus9_TopCap.stl", "Nexus9_Logo.stl"];

for (i = [0 : len(files) - 1])
    translate([0, 0, zpos[i]]) import(files[i]);

// one sample front panel, exploded out toward the front
translate([0, -130, 250]) rotate([90, 0, 0])
    import("Nexus9_Panel_AICluster.stl");
