# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A WebGL-capture → visual-hull reconstruction pipeline. A live Three.js viewer renders a
procedural colored LEGO tower; a headless browser captures RGBA views with exact camera
matrices; a voxel carver rebuilds a colored 3D mesh from those views and scores it against
ground truth. Pure Python (CPU) reconstruction + a single HTML/JS viewer — no build step,
no package manifest. See `README.md` (usage) and `RECONSTRUCTION.md` (algorithm + metrics).

## Commands

```bash
# Install (no requirements.txt exists — install explicitly)
pip install playwright numpy scipy scikit-image pillow
playwright install chromium
#   capture --model offline mode:   pip install pyvista
#   verify  --truth-mesh scoring:   pip install trimesh rtree

# Validate the whole pipeline with NO browser/GPU (this is the test suite):
python verify_reconstruction.py --selftest --out selftest_out/

# Full live run (3 terminals/steps):
python serve_viewer.py                                   # 1. serve viewer @ :8000
python capture_views.py --url http://localhost:8000/3d-viewer.html \
    --out shots/ --turntable 48 --elev -20,10,40         # 2. capture (needs GPU+browser)
python verify_reconstruction.py --shots shots/ --out recon/ --res 192   # 3. reconstruct+score
```

There are no unit tests, linter config, or CI. `--selftest` is the de-facto regression
test: it fabricates z-buffered truth images and runs the real carve→mesh→color→score path
end-to-end, so any change to the geometry/color/metric code should be validated against it
(expected: IoU ≈ 0.99, completeness ≈ 1.00, F-score ≈ 1.00, color_accuracy ≈ 0.81).

## Architecture — the critical coupling

The viewer and the verifier are **two implementations of the same camera math** that must
stay in lockstep. This is the one thing that breaks silently if edited carelessly:

- **Camera constants are duplicated, not shared.** `3d-viewer.html` uses
  `PerspectiveCamera(45, aspect, 0.1, 100)` and `baseRadius = boundR / sin(45°/2) * 1.08`.
  `verify_reconstruction.py` hardcodes the same values: `FOV_DEG, NEAR, FAR = 45.0, 0.1, 100.0`
  and the matching `baseRadius` formula (used by `--selftest` and the projection math).
  Change FOV/clip/framing in one file and you must change the other, or silhouettes and
  voxel projections desync (symptom: recall/completeness drops well below 1.0 = a pose bug).
- **The contract between them is `window.viewerAPI`** in `3d-viewer.html`:
  `setView(az,el,zoom)`, `getMatrices()` (returns the *actual* column-major 16-element
  `projection` + `view = matrixWorldInverse`), `getModelInfo()` (per-brick oriented boxes +
  colors + `worldMatrix`, the ground truth), and `setCaptureMode(on)` (transparent bg so the
  **alpha channel is the silhouette** and RGB is the color). `capture_views.py` calls these
  via Playwright and writes `cameras.json`. Camera poses are *recorded, not estimated* — the
  hard part of photogrammetry is sidestepped, so the math just has to match the GPU exactly.
- **Projection must mirror the GPU.** `verify_reconstruction.py:project/to_pixels` reproduces
  `clip = P·V·X; ndc = clip/w; pixel_y` flips Y (NDC is y-up, images y-down). Keep this
  identical to the WebGL transform.

### Reconstruction pipeline (`verify_reconstruction.py`)

1. **Carve** (visual hull): voxel grid around model center; a view may only *delete* a voxel
   if it projects onto a **background** pixel that is **inside frame** (out-of-frame = no info,
   keep). Parallelized across views (`carve_parallel`), AND-ed together. → Marching Cubes mesh.
2. **Color**: per-vertex, project into every view, take the color from the single most
   head-on valid (foreground + front-facing) view — *not* an average, to avoid bleeding brick
   colors across seams (`color_vertices`).
3. **Truth**: built analytically from the brick list (`truth_occupancy`) or from a mesh
   inside-test (`truth_from_mesh`, `--truth-mesh`), meshed on the same grid so the two `.ply`
   files overlay directly.
4. **Score** → `metrics.json`: IoU, volumetric precision/recall, Chamfer/Hausdorff,
   F-score@τ, color_rmse, color_accuracy. Outputs `reconstruction.ply` + `truth.ply`
   (per-vertex color).

## Conventions / gotchas

- **`--jobs` is speed-only**: parallel and serial runs produce *identical* metrics. Carving
  splits views across processes; `--truth-mesh` splits the voxel grid. Default = all cores
  capped at 38 (the lab box). Capture is GPU-bound and stays single-browser by default.
- **Cost scales with `--res`³** (96³≈0.9M, 192³≈7M, 256³≈17M cells). More viewing
  *directions* improves shape more than raw resolution does.
- **Capture defaults are tuned for the lab GPU Ubuntu box**: GPU on (`--use-gl=egl`), hi-res
  portrait (1080×1620 @ scale 2 ≈ 2160×3240). Fallbacks for headless-GPU trouble:
  `--browser firefox`, `--channel chromium`, `--no-gpu` (software SwiftShader).
- **`README.md` references `remove_background.py`, which does not exist in the repo.** If a
  real-photo background-removal first pass is needed, it must be created (the carver only
  consumes the alpha channel, so any RGBA-with-foreground-alpha source drops in).
- The browser **capture step cannot run in a sandbox** that blocks Playwright's Chromium
  download; only `--selftest` and `serve_viewer.py` are verifiable without a GPU/browser.
</content>
</invoke>
