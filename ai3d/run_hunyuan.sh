#!/bin/bash
# Hunyuan3D-2 (Tencent) image->3D SHAPE in a pytorch-devel container (no GL needed).
set -e
cd "$(dirname "$0")"
ABS=$(pwd)
IMG=pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel
mkdir -p outputs/hunyuan hf_cache
docker run --gpus all --rm \
  -v "$ABS":/work -w /work \
  -e TORCH_CUDA_ARCH_LIST=7.5 -e HF_HOME=/work/hf_cache -e PYTHONUNBUFFERED=1 \
  -e HF_HUB_ENABLE_HF_TRANSFER=0 \
  "$IMG" bash -lc '
    set -e
    echo "== apt =="; apt-get update -qq && apt-get install -y -qq git libgl1 libglib2.0-0 >/dev/null 2>&1 || true
    echo "== clone Hunyuan3D-2 =="; rm -rf /tmp/H3D && git clone -q https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git /tmp/H3D || git clone -q https://github.com/Tencent/Hunyuan3D-2.git /tmp/H3D
    cd /tmp/H3D
    echo "== deps (shape-only; skip texture custom CUDA) =="
    pip install -q --no-input "huggingface_hub<0.26" diffusers transformers accelerate trimesh pymeshlab einops opencv-python-headless omegaconf scikit-image rembg onnxruntime 2>&1 | tail -4
    pip install -q --no-input -e . 2>&1 | tail -3 || true
    echo "== run shape inference =="
    python - <<PY 2>&1 | tail -25
import torch, trimesh, numpy as np
from PIL import Image
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
mdl = "tencent/Hunyuan3D-2"
print("loading", mdl, flush=True)
pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(mdl)
img = Image.open("/work/inputs/harp_front.png")
print("generating...", flush=True)
mesh = pipe(image=img, num_inference_steps=40, octree_resolution=320, mc_algo="mc")[0]
mesh.export("/work/outputs/hunyuan/harp_shape.glb")
print("EXPORTED", len(mesh.vertices), "verts", len(mesh.faces), "faces", flush=True)
PY
    echo "== outputs =="; ls -la /work/outputs/hunyuan
  '
