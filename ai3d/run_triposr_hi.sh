#!/bin/bash
# TripoSR (single image -> textured mesh) in a pytorch-devel container.
set -e
cd "$(dirname "$0")"
ABS=$(pwd)
IMG=pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel
mkdir -p outputs/triposr_hi hf_cache
docker run --gpus all --rm \
  -v "$ABS":/work -w /work \
  -e TORCH_CUDA_ARCH_LIST=7.5 -e HF_HOME=/work/hf_cache -e PYTHONUNBUFFERED=1 \
  "$IMG" bash -lc '
    set -e
    echo "== apt deps =="
    apt-get update -qq && apt-get install -y -qq git build-essential libgl1 libglib2.0-0 >/dev/null 2>&1 || true
    echo "== clone TripoSR =="
    rm -rf /tmp/TripoSR && git clone -q https://github.com/VAST-AI-Research/TripoSR.git /tmp/TripoSR
    cd /tmp/TripoSR
    echo "== pip deps (this compiles torchmcubes against CUDA) =="
    pip install -q --no-input setuptools wheel
    pip install -q --no-input -r requirements.txt 2>&1 | tail -8
    pip install -q --no-input onnxruntime "imageio[ffmpeg]" 2>&1 | tail -2
    echo "== run TripoSR on the harp =="
    python run.py /work/inputs/harp_front.png \
      --output-dir /work/outputs/triposr_hi \
      --mc-resolution 512 --no-remove-bg --model-save-format obj 2>&1 | tail -20
    echo "== outputs =="
    ls -laR /work/outputs/triposr_hi
  '
