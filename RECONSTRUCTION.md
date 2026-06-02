# Reconstruction & Verification — How It Works

This document describes how `verify_reconstruction.py` turns the captured 2D images back into a **colored** 3D model, and the metrics it uses to score that reconstruction against the original ("ground-truth") model — here, the procedural LEGO tower in `3d-viewer.html`.

---

## 1. Data flowing in

The capture stage (`capture_views.py --url`) produces one RGBA PNG per view plus a `cameras.json`. A complex shape needs many viewing **directions**, so for reconstruction you capture a dense turntable rather than the 7 documentation views:

```
python capture_views.py --url http://localhost:8000/3d-viewer.html --out shots/ \
    --turntable 36 --elev -20,10,40
```

Each image is an RGBA PNG captured in *capture mode* (transparent background). This gives two things at once: the **alpha channel is the exact object silhouette**, and the **RGB channels are the object's color**. `cameras.json` records, per image, the exact `projection` and `view` matrices the GPU used (16 column-major numbers each), plus a full description of the model: every brick as an oriented box with a color, and the model center / framing radius. Because the camera poses are recorded rather than estimated, the hardest part of normal photogrammetry — recovering where each photo was taken — is already solved exactly.

---

## 2. Geometry: Shape-from-Silhouette (Visual Hull)

The shape is reconstructed as the **visual hull**: the largest 3D volume consistent with every silhouette. Each silhouette + its camera defines a cone of rays that could be the object; the object lies in the intersection of all those cones. This is implemented by **voxel carving**.

A cubic voxel grid is placed around the model center (resolution set by `--res`). Every voxel starts occupied. For each view, every voxel center **X** is projected to a pixel with the recorded matrices, exactly mirroring the GPU transform:

```
clip    = P · V · [X, 1]ᵀ
ndc     = clip.xyz / clip.w
pixel_x = (ndc.x · 0.5 + 0.5) · W
pixel_y = (1 − (ndc.y · 0.5 + 0.5)) · H     # flip Y: NDC is y-up, images are y-down
```

The carving rule is conservative: a view may only **delete** a voxel if it projects onto a **background** pixel that lies **inside** the image frame. Projecting out of frame carries no information, so the voxel is kept — this lets framed and zoomed/cropped views be mixed safely. The voxels that survive all views form the visual hull, which is converted to a triangle mesh with **Marching Cubes** (`skimage.measure.marching_cubes`, iso-level 0.5).

---

## 3. Color: best-view back-projection

The visual hull is geometry only, so color is added in a second pass. Each mesh vertex's normal is oriented outward, then the vertex is projected into every view. A view is a valid color source for that vertex if the vertex lands on a foreground pixel and the view is front-facing (the surface normal points toward the camera). Among all valid views, the vertex takes the color of the pixel from its **single most head-on view** (largest normal·view-direction). Picking one sharp view rather than averaging avoids blending adjacent brick colors across seams. The result is written as a per-vertex-colored `reconstruction.ply`.

This is a baked best-view texture, and it has two known weaknesses: at brick **seams** the smooth hull surface straddles a hard color boundary, and **occlusion** is only handled approximately (a head-on view is usually, but not always, unoccluded). In practice this colors the large majority of the surface correctly; for a fully photometric result, swap in TSDF fusion or MVS texturing (see §5).

---

## 4. Ground truth

The truth is built directly from the brick list the website reported. For every voxel center (transformed into the model's local frame via the inverse `worldMatrix`), the voxel is occupied if it falls inside any brick's oriented box — tested by translating to the brick center and rotating by −rotY about Y, then comparing against the box half-extents. The occupied voxel inherits that brick's color. Studs are sub-voxel detail and are not modeled in the truth. The truth volume is meshed the same way as the reconstruction, so `truth.ply` and `reconstruction.ply` can be overlaid directly in MeshLab or Blender.

For a real loaded model (e.g. a Sketchfab-style `.glb`) there is no analytic brick list, so pass `--truth-mesh <file>` instead. The verifier loads the mesh with `trimesh` (baking any scene-graph transforms into one mesh), then marks a voxel occupied if its center is inside the mesh — an inside-test on the same grid as the reconstruction, so the metrics line up directly. Truth color is read from the mesh's per-vertex colors, or sampled from its material/texture when only those exist. This path assumes a roughly watertight mesh (non-watertight meshes can give unreliable inside-tests and should be repaired first) and that the file loaded in the viewer and the file passed as truth share a coordinate frame.

---

## 5. Why this method, and its limits

For known camera poses and clean silhouettes, the visual hull is the correct, deterministic, GPU-free baseline. The twisting tower is a mostly-stacked, mostly-convex shape, so its silhouette envelope from a dense turntable recovers the geometry very accurately. The trade-offs: the visual hull **cannot carve concavities** that never appear on a silhouette (a deep pocket between bricks gets filled), and the baked color is approximate at seams. For a fully photometric reconstruction that captures concavities and view-dependent shading, the same capture rig (known poses + many views) feeds directly into Structure-from-Motion / Multi-View Stereo (COLMAP), a NeRF, or Gaussian splatting — those use the RGB rather than just the silhouette, but need a dense turntable and benefit from the texture a colorful LEGO surface provides.

---

## 6. Verification metrics

All metrics are written to `metrics.json`. Geometry compares the reconstructed voxel set (R) to the truth voxel set (T); color compares surface vertex colors.

Geometry, volumetric:

- **IoU (Jaccard)** = |R ∩ T| / |R ∪ T| — overall agreement; 1.0 is perfect.
- **Precision (volumetric)** = |R ∩ T| / |R| — fraction of the reconstruction that is real.
- **Recall / Completeness (volumetric)** = |R ∩ T| / |T| — fraction of the truth recovered; should be ≈ 1.0 for a correct visual hull, since the hull is a superset of the true object.

Geometry, surface (nearest-neighbour between marching-cubes meshes, both directions):

- **Chamfer distance** — mean surface error, also reported as **% of the bounding diagonal** (scale-independent).
- **Hausdorff distance** — worst-case error; read alongside Chamfer.
- **F-score @ τ** — harmonic mean of surface precision and recall within distance τ (the standard reconstruction-benchmark metric); higher is better, `--tau` sets the threshold.

Color:

- **color_rmse** — root-mean-square RGB distance (0..√3) between each reconstructed surface vertex and the true color at the nearest truth surface point.
- **color_accuracy** — fraction of surface whose color is within `--ctol` (default 0.30) of the truth; this is the headline color number.

How to read them: a healthy run shows completeness ≈ 1.0, high IoU and F-score, low Chamfer, and color_accuracy well above chance. If recall/completeness drops far below 1.0, silhouettes and matrices are misaligned (a pose bug). If Chamfer is stuck near one voxel, raise `--res`.

---

## 7. Built-in self-test

`verify_reconstruction.py --selftest` needs no browser or GPU. It builds a small LEGO tower in Python, fabricates the colored RGBA images a dense turntable would produce (z-buffered color splat of the truth, so occlusion is correct), then runs the full carve → mesh → color → score pipeline. It exercises every line of the real code path and is how the pipeline was validated. Representative output (res 110, 32 views):

```
IoU                              ~0.99
recall_completeness_volumetric   ~1.00   ← hull contains the truth, as expected
chamfer_pct_of_diagonal          ~0.08 %
f_score_at_tau                   ~1.00
color_accuracy                   ~0.81
```

These are an optimistic upper bound, since the silhouettes are generated from the truth itself — they measure pipeline *correctness*, not real-capture accuracy. Real GPU captures will score somewhat lower (anti-aliased silhouette edges, lighting/shadow on the color), which is expected.

---

## 8. Performance, resolution, and the lab defaults

Two resolutions drive quality. The **image resolution** (capture `--size` × `--scale`, default high-res portrait ≈ 2160×3240) sets how sharply each silhouette edge is sampled. The **voxel resolution** (`--res`) sets the reconstruction grid: the model is carved on a grid of res³ cells, so surface detail ≈ (grid size ÷ res), and both memory and time scale with res³ (96³ ≈ 0.9M cells, 192³ ≈ 7M, 256³ ≈ 17M). More viewing **directions** improve the overall shape more than raw resolution does; resolution mainly sharpens the surface once enough views constrain it.

The expensive steps are CPU-bound and parallelized with `--jobs` (default: all cores, capped at 38). Carving splits the views across processes — each process carves all voxels for its subset, then the partial hulls are AND-ed together. The `--truth-mesh` inside-tests split the voxel grid into chunks tested in parallel. Parallel and serial runs produce identical metrics; `--jobs` only changes speed. The browser capture, by contrast, is GPU-bound and runs hardware GL by default (`--use-gl=egl`), with `--browser firefox` and `--no-gpu` as fallbacks for machines where headless Chromium has GPU trouble.
