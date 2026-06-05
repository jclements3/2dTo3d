# Lyon & Healy Style 25 — reconstructed profile & soundboard

Reconstruction of a real L&H Style 25 concert harp: **side profile**, **soundboard face**,
and the **47-string G/S/N/F/T/U/L geometry**, fusing the owner's tape measurements with
shape from photos and a 3D mesh, then physics-refined.

## Coordinate frame
ZX plane, **Y = 0**. **X** = across the front (bass C1 = 0 → treble G7 = 643 mm).
**Z** = height above floor (0 → 2000 mm crown). All deliverables share this frame and derive
from one source table, `lhstyle25_grid2m.csv`.

## Deliverables
| file | what |
|---|---|
| `style25_profile.svg/.png` | side silhouette (column/neck/chamber/base) — from 3D mesh, 2000×980 mm |
| `style25strings.svg/.png` | **the profile dots** — 47 strings × G/S/N/F/T + neck band U/L |
| `style25soundboard.svg/.png` | **soundboard face** — teardrop, 360 mm bass, 47 grommets |
| `style25_soundbox_xsection.png` | lemicon cross-section (flat face + round back) |
| `style25_engineering_sheet.png` | one-page: profile + face + spec |
| `style25_physics_validation.png` | tension/frequency validation |
| `lhstyle25_grid2m.csv` | **source table**: X + g/s/n/f/t/L/U per string |
| `lhstyle25_neck_spec.csv` | disc/pin gaps + buildability flag per string |

## How each dot is derived
- **G grommet** — measured grommet rib (straight, 23.5° from vertical).
- **F flat pin** — vibrating-string physics: open string sounds its **flat pitch** (C♭ major),
  `f = (1/2L)√(T/μ)`; per-material **smooth design-tension** recomputes L; **50/50 blend** with tape
  (50/50 recovers the smoothest scale given stepped published diameters). Wound bass = measured.
- **S sharp / N natural** — F × 2^(−2/12), 2^(−1/12) (semitone disc steps).
- **T tuner** — F + 35 mm (non-speaking length).
- **U/L neck edges** — quartic-bezier fit to the harmonic curve (U bass-anchored to your hand reads).

## Validated
- Design tension smooth (8% denoise); flat-pitch frequencies exact; treble strings octave-halve.
- F **invariant** to uniform diameter scaling → robust to the gauge/tension uncertainty.
- Ordering g<L<S<N<F<T<U: 47/47. Disc mechanism buildable (top octave = compact fourchettes).
- All deliverables cross-checked to one source frame.

## Measured vs derived vs estimated
- **Measured (authoritative):** string lengths, grommets/rib, soundboard 23.5°/1610 mm, bass face 360 mm,
  2000 mm height (tile-grid confirmed), C1/C2 neck-top U, string spacing, diameters/materials.
- **Physics-derived:** refined F, and S/N from semitone ratios.
- **Shape from mesh:** side silhouette, soundboard taper, lemicon.
- **Estimated:** U/L (bezier), soundboard bottom contraction, soundbox depth (owner: out of scope).

## To make it exact (needs owner)
- The 16 off-frame bass **U** values, read directly.
- One or two more **soundboard face widths** (mid + treble) to pin the taper.
- - Reconcile string spacing: measured air gaps sum to ~672 mm vs the C1→G7 rib span 643 mm (~4%);
  grommet X positions are faithful to the *relative* gaps (scaled), but the absolute could be pinned
  by confirming whether the caliper gaps are edge-to-edge vs center-to-center.
- (Soundbox depth intentionally out of scope — acoustic analysis will set it.)
