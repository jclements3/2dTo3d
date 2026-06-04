# AI image-to-3D harp — results (overnight run, 2026-06-02)

## TL;DR
The generative AI approach **worked** where every classical method failed.
From a single clean render of your harp, two models produced clean, connected,
single-piece 3-D harps — correct harmonic-curve neck, column, soundboard, open
triangle, base. The thin **strings are not generated** (AI doesn't synthesize
sub-mm threads), and the shapes are **plausible, not metric** (generative priors,
not measurement). For a presentable / printable / reference harp, these are by far
the best output of the whole project.

## BEST RESULT: ai3d/outputs/hunyuan_harp_colored.glb
Hunyuan3D-2's high-detail geometry (detailed neck with pin row, base with pedals,
watertight, 168k faces) + wood color transferred from TripoSR (mahogany frame,
lighter spruce soundboard). Open this in FreeCAD. Preview: hunyuan_colored_preview.png

## All results (FreeCAD-ready, scaled to 559 x 1911 x 1010 mm = 22" x 75.25" x 39.75")

| Model | Files | Verts/Faces | Color | Notes |
|---|---|---|---|---|
| **Hunyuan3D-2** | ai3d/outputs/hunyuan_harp.{glb,stl,obj} | 84k / 168k | no (gray) | **Best geometry.** Detailed neck w/ pin row, base with pedals, watertight. |
| **TripoSR** | ai3d/outputs/triposr_harp.{glb,stl,obj} | 16k / 32k | yes (wood) | Clean + colored, slightly chunky. Good for a quick textured view. |

Previews: ai3d/outputs/hunyuan_preview.png, triposr_preview.png, COMPARISON.png

## How it was done
- Input: one clean centered render of the harp (ai3d/inputs/harp_front.png).
- Each model run in a CUDA pytorch-devel Docker container, GPU-capped (no lockups).
- Output mesh reoriented upright, scaled to your target dimensions, exported glb/stl/obj.

## Honest limits
- **No strings** — both models omit them. Add separately (47 thin rods) if needed;
  the dimension sheet (HARP_DIMENSIONS.md) gives spacing/lengths.
- **Plausible, not exact** — proportions/curves are AI-inferred from one image, not
  measured. Good for form/visualization; for build dimensions use HARP_DIMENSIONS.md
  + the traced elevation.
- **No baked texture on Hunyuan** (shape-only model); TripoSR carries vertex color.

## Recommendation
Open **hunyuan_harp.glb** in FreeCAD for the best shape; use **triposr_harp.glb**
if you want the wood color. Both are clean, connected harps you can actually view,
print, or use as a CAD reference — the thing we were after.

## TRELLIS (attempted, abandoned)
TRELLIS-image-large was attempted for the highest quality, but its install
(flash-attn/xformers/kaolin/nvdiffrast + a torch version conflict) failed in the
container — it's the known-fragile one. Not worth the rabbit hole given Hunyuan3D-2
already produced top-tier geometry. Could be revisited with a prebuilt TRELLIS image.

## To add strings (optional finishing touch)
Neither AI model generates the 47 strings. Add them as thin rods from the
soundboard line to the neck, spacing/lengths per HARP_DIMENSIONS.md (13-17 mm
center-to-center, geometric length progression). Best done in FreeCAD on top of
hunyuan_harp_colored.glb.

## GPU note
Your llm-inference docker stack is still stopped (I used the GPU for this). Restart
it whenever with: docker start llm-inference-gptoss-1 llm-inference-gptoss-embed-1 llm-inference-minilm-embed-1
