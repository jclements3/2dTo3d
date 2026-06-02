# WebGL Capture → Colored Reconstruction Pipeline

Serve a live WebGL 3D model (a procedural colorful LEGO tower), capture views from a headless browser, reconstruct a **colored** 3D model from those images, and score it against the original. See `RECONSTRUCTION.md` for the algorithm and metric details.

## Files

| File | Purpose |
|---|---|
| `3d-viewer.html` | The WebGL viewer (Three.js). Renders a procedural twisting LEGO tower and exposes `window.viewerAPI` for programmatic camera control, the exact render matrices, the per-brick ground truth, and a transparent capture mode whose alpha channel is the silhouette and whose RGB is the color. |
| `serve_viewer.py` | Serves the viewer locally so it has a real URL to capture. |
| `capture_views.py` | Drives a headless browser to that URL. Default = 7 perspectives × 3 zooms for documentation; `--turntable N` = dense ring(s) of views for reconstruction. Saves RGBA PNGs + `cameras.json`. Also has an offline `--model` mode (PyVista). |
| `remove_background.py` | **First pass for real photos**: removes the background and writes RGBA silhouettes (alpha = foreground) for the carver. Border/color methods need no extra deps; `--method rembg` adds ML matting for cluttered backgrounds. |
| `verify_reconstruction.py` | Visual-hull geometry + best-view color reconstruction, scored vs the per-brick truth. Includes `--selftest`. |
| `RECONSTRUCTION.md` | Documentation of the reconstruction process, algorithms, and metrics. |
| `examples/` | A sample `metrics.json` and `lego_preview.png` (truth vs reconstruction). |

## Install

```bash
pip install playwright numpy scipy scikit-image pillow
playwright install chromium
# offline mesh mode for capture_views.py only:  pip install pyvista
# scoring against a real model file (--truth-mesh):  pip install trimesh rtree
# ML background removal (remove_background.py --method rembg):  pip install rembg onnxruntime
```

## Run order

```bash
# 1. Serve the viewer (terminal 1)
python serve_viewer.py
#    -> Viewer URL: http://localhost:8000/3d-viewer.html

# 2. Capture a dense turntable (terminal 2) - high-res PORTRAIT + GPU are the defaults
python capture_views.py --url http://localhost:8000/3d-viewer.html --out shots/ \
    --turntable 48 --elev -20,10,40
#    -> shots/view_*.png (RGBA, ~2160x3240) + shots/cameras.json
#    if headless Chromium has GPU trouble on the box:  add  --browser firefox
#    to force software rendering anywhere:             add  --no-gpu
#    optional parallel capture (GPU is shared, 4-6 is plenty):  --jobs 6

# 3. Reconstruct (geometry + color) and score against the original
python verify_reconstruction.py --shots shots/ --out recon/ --res 192
#    --jobs defaults to all CPU cores (capped at 38) for carving + inside-tests
#    -> recon/metrics.json, reconstruction.ply (per-vertex color), truth.ply
```

For documentation stills instead, drop `--turntable` (gives the 7 standard views × 3 zooms plus paste-ready `captures.md` / `captures.tex`). Open the two `.ply` files together in MeshLab/Blender to compare.

To score against a **real model file** instead of the procedural tower, add `--truth-mesh model.glb` (any `.glb`/`.gltf`/`.obj`/`.stl`/`.ply`): it voxelizes that mesh as the reference, with color taken from the mesh's vertex colors or material. Load the same file in the viewer (via `GLTFLoader`) so the captured scene and the truth mesh share a coordinate frame. Works best on watertight meshes; non-watertight ones may need `trimesh` repair first.

If you're starting from **real photos** (or screenshots that aren't transparent) rather than the synthetic viewer, run the background-removal first pass before reconstruction:

```bash
python remove_background.py --in photos/ --out masked/ --preview
#    -> masked/*.png  (RGBA, alpha = foreground)  + masked/_preview.png
#    cluttered backgrounds:  --method rembg --jobs 38
#    known flat backdrop:    --method color --bg-color "#ffffff" --tol 0.15
# then point the verifier at masked/ (it reads the alpha channel) together with
# a cameras.json of poses for those photos.
```

The carver only needs the alpha channel, so background-removed images drop straight in. Camera poses for real photos come from your own calibration or a Structure-from-Motion pass (COLMAP) — this stage only handles the silhouettes.

## What has been tested in this environment

- `verify_reconstruction.py --selftest` **runs end-to-end** on a colored LEGO tower: geometry IoU ≈ 0.99, completeness ≈ 1.00, F-score ≈ 1.00, color accuracy ≈ 0.81, and valid per-vertex-colored PLY meshes. `examples/lego_preview.png` shows the truth vs the reconstruction.
- `serve_viewer.py` serves the viewer (HTTP 200) with the capture API present.
- All scripts are byte-compiled (syntax-clean).

## What needs your GPU / browser machine

The **browser capture step (step 2) was not run here** because this sandbox blocks Playwright's Chromium download. On your machine, after `playwright install chromium` (and optionally `playwright install firefox`), it runs directly. The defaults are tuned for the lab GPU Ubuntu box:

- **GPU is on by default.** Chromium launches with hardware GL (`--use-gl=egl --ignore-gpu-blocklist`, no sandbox), so it uses the GPU rather than software SwiftShader. If headless Chromium still misbehaves on the box, switch engine with `--browser firefox` (run `playwright install firefox` first), point at a system build with `--channel chromium`, or fall back to software with `--no-gpu`.
- **Frames are high-res portrait by default** (1080×1620 CSS px at 2× ≈ 2160×3240), matching a tall model. Override with `--size W H` and `--scale`.
- **The 38 cores are used by the reconstruction**, where the work is CPU-bound: `--jobs` defaults to all cores (capped at 38) and parallelizes both the silhouette carving and the mesh inside-tests. The capture step is GPU-bound, so it stays single-browser unless you ask for `--jobs N` there (a small N, since the GPU is shared).
- **Resolution / quality:** `--res` 192–256 gives finer meshes (cost scales with res³); more turntable azimuths/elevations improve the shape more than raw resolution; `--tau` and `--ctol` set the surface and color tolerances.
- **Going fully photometric:** for color and concavities beyond a visual hull, feed the same images + `cameras.json` poses into COLMAP / a NeRF / Gaussian splatting.
- **Swapping the model:** point the viewer at a real `.glb` and score with `--truth-mesh that_file.glb`. The capture and carving code is model-agnostic.
