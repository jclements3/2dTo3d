// harp_measured.scad -- YOUR Lyon & Healy Style 25, built from PHOTO MEASUREMENTS.
// Frame lives in the XZ symmetry plane (X = bass->treble, Z = height above floor, mm);
// the soundbox extrudes in -Y (depth). All numbers below are measured/derived:
//   overall height 1911 | soundboard 23.5 deg from vertical | pillar ~7 deg | base ~250
//   47 string grommets on a STRAIGHT rib | neck = measured tuning-pin locus.
$fn = 40;
HEIGHT     = 1911;   // crown, measured
CAPITAL_Z  = 1840;   // column capital top, MEASURED (IMG_5752)
SB_ANGLE   = 23.5;   // soundboard rib, deg from vertical (measured)
PILLAR_LEAN= 6.8;    // deg from vertical (grommet-anchored fit)

// ---- measured profile point lists [X, Z] ----
rib_pts    = [
  [0.0,330.0],
  [14.2,362.5],
  [27.7,393.7],
  [41.8,425.9],
  [56.2,459.1],
  [70.1,490.9],
  [84.6,524.3],
  [99.8,559.2],
  [114.0,591.8],
  [128.3,624.5],
  [142.5,657.2],
  [156.7,689.8],
  [170.9,722.5],
  [185.2,755.1],
  [199.4,787.8],
  [213.6,820.4],
  [227.5,852.4],
  [241.1,883.6],
  [254.5,914.3],
  [268.0,945.4],
  [281.8,976.9],
  [297.1,1012.2],
  [312.3,1047.1],
  [327.4,1081.7],
  [342.5,1116.3],
  [357.5,1150.9],
  [372.6,1185.5],
  [387.7,1220.2],
  [402.8,1254.8],
  [417.5,1288.5],
  [431.8,1321.4],
  [446.1,1354.3],
  [460.9,1388.2],
  [476.0,1422.9],
  [490.4,1456.0],
  [504.3,1487.9],
  [517.7,1518.7],
  [531.1,1549.5],
  [543.7,1578.4],
  [556.3,1607.3],
  [568.9,1636.2],
  [581.5,1665.1],
  [594.1,1694.0],
  [606.7,1722.9],
  [618.9,1750.9],
  [631.1,1779.0],
  [643.3,1807.0]
];      // soundboard grommet line (bass C1 -> treble G7)
neck_pts   = [
  [0.0,1925.6],
  [14.2,1927.4],
  [27.7,1924.8],
  [41.8,1957.0],
  [56.2,1983.3],
  [70.1,2001.2],
  [84.6,1982.9],
  [99.8,1965.2],
  [114.0,1989.0],
  [128.3,1989.8],
  [142.5,1971.9],
  [156.7,1972.8],
  [170.9,1972.7],
  [185.2,1946.8],
  [199.4,1952.6],
  [213.6,1963.5],
  [227.5,1969.6],
  [241.1,1955.2],
  [254.5,1917.4],
  [268.0,1814.5],
  [281.8,1731.9],
  [297.1,1733.3],
  [312.3,1755.4],
  [327.4,1764.2],
  [342.5,1721.4],
  [357.5,1645.8],
  [372.6,1628.8],
  [387.7,1642.6],
  [402.8,1657.4],
  [417.5,1664.3],
  [431.8,1679.3],
  [446.1,1702.3],
  [460.9,1730.2],
  [476.0,1749.1],
  [490.4,1761.3],
  [504.3,1754.5],
  [517.7,1758.5],
  [531.1,1769.4],
  [543.7,1798.3],
  [556.3,1820.3],
  [568.9,1838.3],
  [581.5,1866.2],
  [594.1,1890.1],
  [606.7,1896.2],
  [618.9,1908.3],
  [631.1,1925.5],
  [643.3,1948.5]
];      // harmonic curve = tuning-pin locus
pillar_pts = [
  [-357.8,180.0],
  [-396.3,500.0],
  [-444.3,900.0],
  [-492.4,1300.0],
  [-540.4,1700.0],
  [-557.2,1840.0]
];   // column centerline, base -> capital

// ---- helpers ----
module tube(P, d) for(i=[0:len(P)-2]) hull(){
  translate([P[i][0],   0, P[i][1]])   sphere(d=d);
  translate([P[i+1][0], 0, P[i+1][1]]) sphere(d=d);
}

// soundbox: tapered body behind the board (depth in -Y, width in +/-Y)
module soundbox() for(i=[0:len(rib_pts)-2]) hull(){
  for(j=[i,i+1]) let(z=rib_pts[j][1], x=rib_pts[j][0])
    translate([x,0,z]) rotate([0,0,0])
      // a flat-ish wedge: board face at Y~0, body bulging to -Y
      scale([1, depth(z)/40, 1]) translate([0,-20,0]) sphere(d=40);
}
function depth(z) = 230*(1-constrain((z-330)/1477,0,1)) + 35*constrain((z-330)/1477,0,1);
function constrain(t,a,b) = max(a, min(b, t));

// soundboard face plate (the spruce the grommets sit in): a thin wide ribbon on the rib
module soundboard_face() for(i=[0:len(rib_pts)-2]) hull(){
  for(j=[i,i+1]) let(z=rib_pts[j][1], x=rib_pts[j][0], w=wid(z))
    translate([x,0,z]) scale([1, w/12, 1]) sphere(d=12);
}
function wid(z) = 360*(1-constrain((z-330)/1477,0,1)) + 45*constrain((z-330)/1477,0,1);

// ---- assemble ----
color([0.62,0.42,0.22]) soundbox();                       // body
color([0.80,0.62,0.40]) soundboard_face();                // soundboard face + grommet line
color([0.78,0.60,0.12]) tube(pillar_pts, 64);             // gilt column / pillar
color([0.80,0.64,0.20]) tube(neck_pts, 70);               // neck / harmonic curve
// crown link: capital -> bass tuning pin
color([0.80,0.64,0.20]) tube([pillar_pts[len(pillar_pts)-1],[neck_pts[0][0],neck_pts[0][1]]], 60);
// base / pedestal
color([0.74,0.57,0.12]) translate([pillar_pts[0][0]-90,-160,0]) cube([rib_pts[0][0]-pillar_pts[0][0]+260, 320, 150]);

// strings (optional thin cylinders) -- comment out for a clean frame
module strings() for(i=[0:len(rib_pts)-1])
  hull(){ translate([rib_pts[i][0],0,rib_pts[i][1]]) sphere(d=2);
          translate([neck_pts[i][0],0,neck_pts[i][1]]) sphere(d=2); }
color([0.9,0.9,0.9]) strings();
