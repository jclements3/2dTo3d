#!/bin/bash
# TRELLIS (microsoft) image->3D, MESH format only (skips gaussian/octree renderers
# and GL texture baking). Best-effort; xformers attn backend to avoid flash-attn.
set -e
cd "$(dirname "$0")"
ABS=$(pwd)
IMG=pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel
mkdir -p outputs/trellis hf_cache
docker run --gpus all --rm \
  -v "$ABS":/work -w /work \
  -e TORCH_CUDA_ARCH_LIST=7.5 -e HF_HOME=/work/hf_cache -e PYTHONUNBUFFERED=1 \
  -e ATTN_BACKEND=xformers -e SPCONV_ALGO=native \
  "$IMG" bash -lc '
    set -e
    apt-get update -qq && apt-get install -y -qq git build-essential libgl1 libglib2.0-0 libegl1 ninja-build >/dev/null 2>&1 || true
    rm -rf /tmp/TRELLIS && git clone -q --recurse-submodules https://github.com/microsoft/TRELLIS.git /tmp/TRELLIS
    cd /tmp/TRELLIS
    echo "== core deps =="
    pip install -q --no-input pillow imageio "imageio[ffmpeg]" tqdm easydict opencv-python-headless scipy ninja rembg onnxruntime trimesh xatlas pyvista pymeshfix igraph transformers accelerate safetensors einops "huggingface_hub<0.26" 2>&1 | tail -3
    pip install -q --no-input xformers==0.0.27.post2 2>&1 | tail -2 || pip install -q --no-input xformers 2>&1 | tail -2 || true
    pip install -q --no-input spconv-cu120 2>&1 | tail -2 || true
    pip install -q --no-input git+https://github.com/NVlabs/nvdiffrast.git 2>&1 | tail -3 || true
    pip install -q --no-input kaolin -f https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.4.1_cu121.html 2>&1 | tail -3 || true
    pip install -q --no-input git+https://github.com/EasternJournalist/utils3d.git 2>&1 | tail -2 || true
    echo "== run TRELLIS (mesh only) =="
    python - <<PY 2>&1 | tail -30
import os, numpy as np, trimesh, torch
from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline
pipe = TrellisImageTo3DPipeline.from_pretrained("JeffreyXiang/TRELLIS-image-large")
pipe.cuda()
img = Image.open("/work/inputs/harp_front.png")
out = pipe.run(img, formats=["mesh"], preprocess_image=True)
m = out["mesh"][0]
v = m.vertices.detach().cpu().numpy(); f = m.faces.detach().cpu().numpy()
trimesh.Trimesh(v, f, process=False).export("/work/outputs/trellis/harp_mesh.glb")
print("EXPORTED", len(v), "verts", len(f), "faces")
PY
    ls -la /work/outputs/trellis
  '
