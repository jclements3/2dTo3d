# Concert (Pedal) Harp — Buildable Dimension Reference

A workbench reference for designing your own pedal harp, assembled from (a) published
concert-harp specs + harp-acoustics/building literature and (b) **angles and proportions
measured from the Sketchfab reference** "Classical Harp (Pedal Harp)" by Marine Mazurier
(model `6e31140ec5dc4d7aa2e9c1286f2b4d25`).

Every number here drives a variable in **`harp.scad`** (parametric — change strings,
tensions, and the soundboard cross-section to suit your design).

## Reconstructed 3D mesh (`recon/`)

Alongside the parametric `harp.scad`, a **visual-hull reconstruction** of the reference
harp was carved from a 360° turntable of rendered silhouettes (no original asset extracted):

- `recon/harp_reconstruction.glb` / `.obj` / `.ply` — colored mesh, **63k verts / 127k faces**
  (vs. the original art asset's ~9k/15k). Open the `.glb` in any 3D viewer.
- Pipeline: `capture_sketchfab.py` (320 GPU-rendered transparent views) →
  `reconstruct_sketchfab.py` (36-CPU voxel carve at res 256 → marching cubes → best-view color).
- **What it captures:** the solid frame — harmonic-curve **neck**, **column**, **soundboard/body**,
  **base**. Preview: `examples/harp_reconstruction_views.png`.
- **What it loses:** the **strings** (sub-voxel, carved away) and fine detail; the mesh is the
  visual hull, so deep concavities are filled. Built from the consistent equatorial (el 0) ring
  because Sketchfab's viewer doesn't expose exact camera matrices and the off-axis rings didn't
  register to sub-pixel accuracy. For a fully photometric mesh (strings, concavities), feed the
  same captures into COLMAP/Gaussian-splatting. **For building, use the dimensions below and
  `harp.scad`** — the mesh is a visual reference, not a metrology source.

## What this is / honest caveats

- This is **not** the Sketchfab model's geometry. That model is marked **not downloadable**
  (`isDownloadable:false`), so its mesh was not extracted. Instead the public viewer was
  rendered near-orthographically and **angles/proportions were measured** off the silhouette
  (`examples/harp_measured_angles.png`), then anchored to real published dimensions.
- The model is a 15 k-face **art asset**, not a metrology source. Treat all model-measured
  angles as **±2–3°**. They are useful because the angles a builder most wants
  (soundboard-to-vertical, column lean, the triangle apex) are **not published by any
  maker** — the model fills that gap, and where it can be cross-checked (overall
  proportions) it matches real harps to within a few percent.
- Tags below: **[spec]** = manufacturer/published, **[lit]** = acoustics/building literature,
  **[measured]** = from the reference model, **[derived]** = computed/estimated (no public figure).

---

## 1. Overall envelope  [spec]

| Dimension | Value | Source |
|---|---|---|
| Height (floor → crown) | **1850 mm** (73–74 in) | L&H Style 23/30, Salvi Diana, Camac Atlantide |
| Extreme width (front-to-back footprint) | **980–1000 mm** (38.6–39.5 in) | same |
| Soundboard width at bass end | **550 mm** (21.5 in) | same |
| Weight | 36–41 kg (80–90 lb) | same |
| Strings | **47** (also 46/40 variants) | — |

Cross-check: model **H/W = 1.88** in the string plane → at 1850 mm tall, front-back spread
**≈ 985 mm** [measured], matching the published 980–1000 mm. The model is dimensionally faithful.

Sources: [L&H Style 30](https://www.lyonhealy.com/harps/style-30/),
[Style 23](https://www.harp.com/product/style-23-concert-grand/),
[Camac Atlantide](https://www.vaharpcenter.com/pedal-harps/p/camac-atlantide-prestige),
[Pedal harp — Wikipedia](https://en.wikipedia.org/wiki/Pedal_harp).

---

## 2. The structural triangle & KEY ANGLES  ← the main value-add

The three members (column, neck, soundboard) form a triangle in the **string plane**.
The angles below were measured face-on from the reference model and cross-checked against
the literature.

| Angle | Value | Tag | Notes |
|---|---|---|---|
| **Column lean** from vertical | **~3°** (measured ~1°) | [measured] | front pillar is nearly upright |
| **Soundboard / body tilt** from vertical | **~24°** | [measured] | the back member leans back going up |
| **String-to-soundboard angle** (apex) | **~25°** | [measured] | lit. gives 25–35° → consistent |
| String plane ⟂ soundboard plane | **90°** | [lit] | defining feature of a harp |
| String break angle over bridge pin | **15–25°** | [lit] | <15° lifts off pin, >25° hard to tune |
| Apex angle at crown (neck∧column) | **~30–40°** | [derived] | geometric consequence |
| Shoulder (neck∧body) position | **0.26 H** below crown | [measured] | where the ogive meets the body |
| Whole-harp tilt-back when played | **25–35°** | [derived] | rests on player's right shoulder |

The published sources are explicit that **soundboard-to-vertical and column-lean are NOT
published by any maker** — these measured values are the reference you otherwise can't get.
Sources: [Harp Column – string angle](https://harpcolumn.com/forums/topic/strings-angle-on-pedal-harps/),
[Sligo statics](http://www.sligoharps.com/statics.htm),
[Waltham, Acoustics Today 2024](https://acousticstoday.org/wp-content/uploads/2024/07/AT-8-Origins_featured_summer2024.pdf).

---

## 3. Strings  [spec/lit + your design]

- **Count/range:** 47, 7 per octave, ~C1 (lowest) to G7 (highest); 6.5 octaves.
- **Sounding lengths:** longest (bass) **1550 mm** (61 in); shortest (treble) **74 mm** (2.9 in)
  [measured specimen, Grinnell College]. Length ≈ **doubles per octave** (×2.0) in the treble,
  **compressed below ~C3** (switch to wire-wound bass). Per semitone the length changes by
  **2^(1/12) = 1.0595** (each disc shortens a string by **5.613 %**).
- **Spacing / "air gap" (center-to-center):** **13–14 mm treble**, **15–17 mm bass**, min 12.5 mm.
  Geometric note from the model: string **feet** sit ~**30 mm apart along the soundboard**, and
  because the strings meet the board at ~25°, the **perpendicular gap you pluck ≈ 30·sin25° ≈
  13 mm** — reconciling the two figures. `harp.scad` echoes this.
- **Diameters:** ~2.8 mm bass → ~0.5 mm treble. **Materials:** wire-wound bass → gut mid → nylon treble.
- **Tension:** ~60 N treble to ~210 N bass per string; **total ≈ 10–12 kN (~1 ton)** — design
  the neck/column/board to this. *(You are substituting your own strings/tensions — recompute
  the harmonic curve from your length table; see §4.)*

Sources: [Harp Connection 47-string chart](https://www.harpconnection.com/PDF%20String%20Charts/String%20Chart%20Pedal%2047.pdf),
[Grinnell measured L&H](https://omeka-s.grinnell.edu/s/MusicalInstruments/item/2134),
[Heartland string spacing](https://heartlandharps.com/string-spacing/),
[Brown harmonic-curve PDF](https://www.harpkit.com/mm5/articles/Harmonic_curve.pdf),
[Waltham 2024](https://acousticstoday.org/wp-content/uploads/2024/07/AT-8-Origins_featured_summer2024.pdf).

---

## 4. Soundboard & body  [lit + your lenticular variant]

- **Outline:** trapezoidal; length **~1400 mm**; width **550 mm bass → ~70 mm treble**
  (each side flares ~6–8° from centerline). [spec/patent]
- **Thickness taper:** **12 mm at the bass → 2.5 mm at the treble** [Le Carrou; Salvi patent
  10→2.5 mm]. Folk-scale rule (thinner): 6.4 → 3.2 mm.
- **Lenticular (convex) cross-section — your variant:** this is *standard practice*, not exotic
  ("rounded, not flat… thinned ~20 % from centerline to edges"). It raises stiffness-to-weight
  (lets the board be thinner for the same strength) and resists the string pull, at the cost of
  biasing response toward treble if over-domed. In `harp.scad` set `lenticular=true` and
  `lenticular_crown` (mm of extra centerline thickness). Keep the crown modest to preserve bass.
- **Material/grain:** Sitka spruce face, built from ~15–20 spruce slats 30–80 mm wide, grain
  running **across** the width (concert convention); ~1 mm decorative face veneer.
- **Central string rib** (carries the string knots): quarter-sawn hard maple, **~½″×1/16″ at
  treble → ~1″×2″ at bass**, with nylon plugs at each string.
- **Body/soundbox:** rounded/stave half-cone, **deep+wide at the bass** (~8 in / 340 mm deep)
  → shallow+narrow at the treble (~3.5 in / 90 mm); soundholes on the **back**; tune the box
  volume + hole area for the A0/T1 coupled modes.

Sources: [Le Carrou soundboard](https://link.springer.com/chapter/10.1007/978-3-319-32080-9_6),
[Salvi/NSM patent US8759647B2](https://patents.google.com/patent/US8759647B2/en),
[Musicmakers soundboard (convex)](https://www.harpkit.com/resources/harp-soundboards),
[Sligo components](http://www.sligoharps.com/Components.html),
[Waltham 2024](https://acousticstoday.org/wp-content/uploads/2024/07/AT-8-Origins_featured_summer2024.pdf).

---

## 5. Neck / harmonic curve  [lit]

- **Shape = ogive (S-curve)**; there is **no published equation**. The curve is *generated*:
  lay out your string feet along the soundboard at your spacing, mark each string's vibrating
  length, and **the locus of the upper (tuning-pin) ends IS the harmonic curve** (`harp.scad`
  draws the neck as a Bézier through those points). Jeremy Brown's book supplies full-size paper
  patterns for exactly this.
- **Cross-section:** neck blank **~38 mm wide** (Érard standard) × ~90–100 mm deep; laminated
  maple with **brass action plates** both sides (~400 holes each).
- **Lateral crank/offset:** strings run ~⟂ to the board but pass one **side face** of the neck;
  offset **~13 mm** off the neck centerline (creates a torque the joints must resist).
- **Pins & discs:** one row of **47 tuning pins**; below, **two rows of fourchette discs**
  (double action): upper disc flat→natural, lower disc natural→sharp; the two discs on a string
  sit **5.613 % of that string's length** apart. ~1,400 parts total.

Sources: [Brown / harmonic curve](https://www.harpkit.com/mm5/articles/Harmonic_curve.pdf),
[The Pedal Harp Unveiled (38 mm neck)](https://www.linkedin.com/pulse/pedal-harp-unveiled-complete-guide-building-double-action-oliynyk-1e),
[Sligo structural](http://www.sligoharps.com/struc1.htm),
[Érard 1810 patent](https://holburne.org/erard-harp/).

---

## 6. Column / pillar  [spec/lit]

- **Height:** spans the ~1850 mm instrument; carries **>½ the total string load in compression**.
- **Cross-section:** carved/laminated maple, **~75 mm at base → ~48 mm at crown** (tapers),
  capped by a decorative capital/crown; **HOLLOW** to enclose the **7 brass pedal rods**.
- **Lean:** deliberately leaned forward for stability (couples with the soundboard tilt — set
  them together). Model measures the column **~1–3° from vertical** in the string plane.

Sources: [Britannica](https://www.britannica.com/art/pedal-harp),
[Sligo structural](http://www.sligoharps.com/struc1.htm), [BYU Design Review](https://www.designreview.byu.edu/collections/the-harp-a-perfect-union-of-design-function-and-form).

---

## 7. Base / pedal box + 7 pedals  [spec + derived — biggest public gap]

- **Base footprint:** **~980–1000 mm (front-back) × ~550 mm**; **box height ~50–75 mm** off the
  floor; **4 corner feet**.
- **7 pedals:** **D, C, B on the left foot; E, F, G, A on the right.** Each has **3 notched
  positions** (flat / natural / sharp — Érard double action).
- **Disc rotation:** ~**45°** (flat→natural) then ~**35°** (natural→sharp). Pedal **felts ⅛–3/16″**.
- **Pedal throw (notch-to-notch):** **~15–25 mm** [derived]. **Protrusion beyond the base:**
  **~30–60 mm** [derived] — *no maker publishes this*. **Pedal rods:** 7, **~3–5 mm** dia, up
  the hollow column to **94 fork discs**.
- **Ergonomics:** bench **~46–53 cm**; harp tips back onto the right shoulder until the strings
  are near-vertical.

**Builder note:** exact pedal spacing, foot-plate size, protrusion, throw, and rod diameter are
**not published anywhere** — measure a real instrument or buy a pedal-box hardware set
(e.g. Markwood / Camac kit). `harp.scad` uses the [derived] estimates above as placeholders.

Sources: [Harp Column pedal order](https://harpcolumn.com/forums/topic/pedal-order/),
[HARPTECH felts](https://harptech.com/Articles/Felts/Felts.html),
[Harp Spectrum Pedal Harp 101](https://www.harpspectrum.org/pedal/wooster.shtml),
[Wikipedia](https://en.wikipedia.org/wiki/Pedal_harp).

---

## 8. How it maps to `harp.scad`

Open the file and edit the parameter blocks at the top, then preview:

```bash
openscad harp.scad                       # interactive
openscad -o harp.png --viewall harp.scad # render (also prints sanity echoes)
```

Built from 4 corner points (A = column foot, B = soundbox foot, C = crown, D = shoulder) so the
frame always closes. Key knobs: `column_lean`, `soundboard_tilt`, `string_to_board`,
`neck_bow` (angles §2); `n_strings`, `spacing_*`, `str_len_*` (§3); `soundboard_t_*`,
`lenticular`, `lenticular_crown`, `string_rib_*` (§4 — your lenticular board); `neck_*` (§5);
`column_dia_*` (§6); `base_*`, `pedal_*` (§7). Previews: `examples/harp_scad_preview.png`
(model output) and `examples/harp_measured_angles.png` (the angle measurement on the reference).

## Confidence summary

- **Build directly:** overall envelope (§1); string count/range/length/spacing/material/tension
  (§3); soundboard taper/thickness/rib + the lenticular approach (§4); the string-lay & break
  angles (§2).
- **Measured from the model (±2–3°), otherwise unpublished:** soundboard tilt, column lean,
  apex/shoulder geometry (§2).
- **Needs a donor instrument or hardware kit (unpublished):** pedal-box internal geometry,
  pedal protrusion/throw, exact neck depth & disc spacing in mm, column cross-section (§5–7).
