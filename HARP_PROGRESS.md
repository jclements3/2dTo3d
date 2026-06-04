# Lyon & Healy Style 25 — reconstruction progress

Autonomous work log. Goal: **high-resolution side profile + soundboard face** of the
real Style 25, fusing the owner's tape measurements with shape from photos.

## Coordinate frame
ZX plane, Y=0. X = across (bass C1=0 -> treble G7=643 mm). Z = height (floor=0, crown=2000 mm).

## Status legend: ✅ measured  🟡 partial  ⚠️ estimated/guessed

| element | status | source |
|---|---|---|
| 47 string lengths / grommets (rib, 23.5°) | ✅ | tape (157.6cm C1 -> ~12cm G7) |
| sharp/natural disc heights (S,N) | ✅ | L_flat × semitone ratios |
| flat pin (F, open length) | ✅ | tape |
| tuner (T) | ⚠️ | estimated F+38mm (measured tuner_cm available to swap in) |
| neck-top U | 🟡 | 2 hand + 29 photo(full-res) + 16 interpolated |
| neck-bottom L | ⚠️ | estimated S−15 |
| soundboard angle 23.5°, length 1610mm | ✅ | grommet rib + spans |
| soundboard bass face width 360mm | ✅ | tape on style25 base |
| soundboard taper / bottom contraction | ⚠️ | guessed |
| pillar: ~3° vertical, ~90mm from C1, 1840 capital | 🟡 | photo + spans |
| pillar/base/chamber detailed outlines | ✅ | SLICED from Hunyuan3D mesh -> style25_profile.svg |
| overall height 2000mm | ✅ | owner + tile-grid check (tile≈236mm) |

## Deliverables
- `lhstyle25_grid2m.csv` — 47 strings × (X, g,s,n,f,t,L,U) Z-heights
- `style25strings.svg` — side profile
- `style25soundboard.svg` — soundboard face (±Y)
- `style25frame.md` — pillar/base/chamber/shoulder corners

## In progress (autonomous)
1. Hunyuan3D-2 mesh from style25.avif (GPU freed) -> slice symmetry plane for
   pillar/neck/chamber/base outlines + perpendicular slices for soundboard cross-section.
2. Fallbacks: TRELLIS, TripoSR.
3. Fuse sliced shapes with measured points -> high-res profile + soundboard face.

## Milestone log
- Hunyuan3D-2 mesh generated from style25.avif (124k verts) on freed GPU.
- Side profile extracted from mesh symmetry plane (YZ), window preserved,
  scaled to real 2000x980mm -> `style25_profile.svg`. Shows pillar/neck/chamber/base outlines.
- NEXT: soundboard face + cross-section (lemicon) from perpendicular slices; fuse measured strings.

- Soundbox cross-sections sliced from mesh -> `style25_soundbox_xsection.png`.
  Confirms LEMICON shape: flat soundboard face + rounded back bulge, tapering bass->treble.
  CAVEAT: single-image-3D over-deepens the front-back (mesh ~580mm at bass);
  scale across-width to measured face (360mm) and depth to real soundbox depth.
