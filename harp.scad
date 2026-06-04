// harp.scad -- YOUR harp as SIMPLE SHAPES, centerlines EXTRACTED from the real
// instrument's silhouette (medial axis), scaled to 1911 mm tall x 1010 mm deep.
// Each member is a swept tube of [x, z, radius] points -- edit any point to taste.
sb_W = 559;   // soundboard left-right width at the bass end (extrude/plate depth)
$fn = 28;

neck_pts   = [
  [-354,1911,40],
  [-335,1667,45],
  [-333,1561,41],
  [-332,1374,41],
  [-330,1882,64],
  [-306,1860,86],
  [-252,1795,124],
  [-136,1767,105],
  [-31,1677,91],
  [22,1564,80],
  [67,1446,75],
  [127,1330,80],
  [244,1314,63],
  [361,1388,57],
  [452,1246,48],
  [490,1323,45],
  [505,1403,47]
];   // harmonic curve (front -> back)
column_pts = [
  [-328,1222,41],
  [-326,1126,41],
  [-325,1031,41],
  [-323,935,41],
  [-321,839,41],
  [-319,744,41],
  [-318,648,41],
  [-316,552,41],
  [-314,456,43],
  [-313,361,46],
  [-311,265,52],
  [-307,169,61],
  [-462,97,38],
  [-265,74,90],
  [-311,68,91],
  [-436,60,62],
  [-484,12,15]
];    // front pillar (top -> base)
board_pts  = [
  [436,1222,44],
  [371,1099,50],
  [311,976,55],
  [252,853,64],
  [187,730,70],
  [125,607,77],
  [64,484,81],
  [2,361,88],
  [-58,238,93],
  [-122,159,63],
  [-180,135,40],
  [89,115,10],
  [-58,106,18],
  [-53,68,10],
  [-201,34,45],
  [-132,15,34],
  [-5,0,2]
];     // soundboard / body line (top -> base)

module tube(P) for(i=[0:len(P)-2]) hull(){
  translate([P[i][0],0,P[i][1]])     sphere(d=max(8,2*P[i][2]));
  translate([P[i+1][0],0,P[i+1][1]]) sphere(d=max(8,2*P[i+1][2]));
}
color([0.85,0.75,0.55]) tube(neck_pts);                 // neck
color([0.45,0.12,0.10]) tube(column_pts);               // column
// soundboard as a wide plate following the body line (gives it real width)
color([0.5,0.16,0.13]) for(i=[0:len(board_pts)-2]) hull(){
  translate([board_pts[i][0],0,board_pts[i][1]])     scale([1,sb_W/max(8,2*board_pts[i][2]),1])   sphere(d=max(8,2*board_pts[i][2]));
  translate([board_pts[i+1][0],0,board_pts[i+1][1]]) scale([1,sb_W*0.5/max(8,2*board_pts[i+1][2]),1]) sphere(d=max(8,2*board_pts[i+1][2]));
}
// base
color([0.4,0.1,0.09]) translate([column_pts[len(column_pts)-1][0]-40,-sb_W/2,0]) cube([460, sb_W, 110]);
