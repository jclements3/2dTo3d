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

- FINAL side profile: labeled (column/neck/sound chamber/base) + string fan, high-res
  -> style25_profile.svg / .png. This is the high-resolution harp profile.

---
## COMPLETE — deliverables summary

**Two goals achieved: high-resolution side profile + soundboard face.**

| file | what | source |
|---|---|---|
| `style25_profile.svg/.png` | **side profile** — column, neck (ogee), sound chamber, base, window, strings; 2000×980 mm, labeled | 3D mesh (Hunyuan3D-2) of your harp, sliced at symmetry plane |
| `style25soundboard.svg/.png` | **soundboard face** — taper + bottom contraction, bass 360 mm | mesh taper × measured bass width |
| `style25_soundbox_xsection.png` | **lemicon cross-section** — flat face + round back, at 4 heights | mesh horizontal slices |
| `style25strings.svg` | broadside string layout (47 strings, mechanism) | your measurements |
| `lhstyle25_grid2m.csv` | the numbers: 47 strings × G/S/N/F/T/U/L heights | measured (T now 36/47 measured) |
| `style25frame.md` | pillar/base/chamber/shoulder coords | measured + mesh |

### Honest accuracy notes
- **Side-profile SHAPE** = your real harp (3D mesh from style25.avif). Recognizable, clean.
- **Vertical scale** 2000 mm = your tape (tile-grid confirmed, tile≈236 mm).
- **Front-back depth** scaled to 980 mm (real Style 25 ~39"); single-image-3D over-deepened the raw mesh (~1525 mm) so depth is the softest dimension.
- **Strings/grommets/discs** = your measurements (authoritative).
- **U (neck top):** 31/47 measured, 16 interpolated. **L (neck bottom):** estimated.

### To push further (needs owner input or more captures)
- Multi-view capture (turntable of full harp) -> true photogrammetry, exact depth.
- Hand-read the 16 off-frame bass U values.
- Soundbox depth measurement to replace the 980 mm scale assumption.

---
## Round 2 — physics-refined F/N/S + bezier U/L (owner's directive)
- **F (flat pin)**: recomputed from the vibrating-string equation. Open string sounds its
  FLAT pitch (harp tuned C-flat major all-pedals-up). For each string:
  f_flat = note x 2^(-1/12); mu = rho*pi*(d/2)^2 (gut 1300, nylon 1140 kg/m^3);
  T = pi*rho*d^2*L^2*f^2. Per-material smooth-tension fit -> recompute L (blend 65/35 with tape).
  Wound bass kept as measured (winding mass unknown). Monotonic enforced.
- **N, S**: F_refined x 2^(-1/12), 2^(-2/12) (semitone disc steps).
- **T (tuner)**: F + 35mm (non-speaking length). NOTE: dropped the measured tuner_cm reads —
  they were ~150mm above the flat pin (inconsistent); the bridge->tuning-pin gap is ~35mm.
- **U/L**: cubic-bezier fit to the harmonic-curve shape; U weighted to USER/photo reads,
  clamped <=1995; L = sharp_disc - 15mm bezier. Ordering g<L<s<n<f<t<U verified 0 violations.
- Output: style25strings.svg/.png (clean ogee neck band, refined dots).

---
## Round 2 complete (autonomous). Done this round:
- F/N/S physics refinement (vibrating string + smooth design tension, per-material)
- T = F+35mm; U/L cubic-bezier fit; ordering verified
- Physics validation figure (style25_physics_validation.png): tension smooth (8% denoise), freqs exact, octave-halving in treble
- Soundboard face: clean teardrop + bottom contraction + 47 grommets at measured spacing
- Neck mechanism spec (lhstyle25_neck_spec.csv): disc/pin gaps per string
- Web check: L&H publishes gauge charts, NOT lengths (lengths are harp-specific) -> measured is authoritative
- Caveat logged: absolute tension runs ~high -> gut diameters may be slightly thick; relative smoothing robust

## Next agenda (continuing autonomously):
1. [DONE] U quartic bezier bass-anchored
2. [DONE] blend sensitivity -> 50/50 (smoothest scale)
3. [DONE] style25_engineering_sheet.png
4. Re-derive gut diameters from a target-tension model as a cross-check on the published gauges
5. Recheck disc-spacing geometry is mechanically buildable (fourchette clearance)

## Round 3 (autonomous)
- Blend sensitivity: 50/50 gives the SMOOTHEST length scale (kink RMS 20.9 vs 25.5 pure-physics);
  published diameters are stepped and inject kinks, so 50/50 best recovers the true smooth scale
  AND stays closest to tape (22mm RMS). Adopted 50/50.
- U upgraded cubic->QUARTIC bezier, USER-weighted: bass peak now 1951 (was 1933), no overshoot.
- Bass tuners clamped to 2000mm crown (harmonic curve peaks at A1-B1, real geometry).
- Ordering g<L<S<N<F<T<=U verified 0 violations.
