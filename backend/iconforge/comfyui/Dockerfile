# ComfyUI for IconForge Phase 2 — FLUX Schnell FP8 on an RTX 4070 Super (12 GB).
# CUDA 12.4 runtime base; GPU reaches the container via `--gpus all` (WSL2 ok).
# Models are NOT baked in — they live in a bind-mounted ./models volume so the
# image stays small and the 17 GB checkpoint survives rebuilds.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# Pin ComfyUI to a ref for reproducible rebuilds (override at build time).
ARG COMFYUI_REF=master
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip git ca-certificates libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Torch first from the CUDA 12.4 wheel index, then ComfyUI's own requirements
# (which list torch but find it already satisfied — no CPU torch gets pulled).
RUN pip3 install --upgrade pip && \
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

RUN git clone https://github.com/comfyanonymous/ComfyUI.git /opt/ComfyUI && \
    cd /opt/ComfyUI && git checkout "$COMFYUI_REF"
WORKDIR /opt/ComfyUI
RUN pip3 install -r requirements.txt

EXPOSE 8188
# --listen 0.0.0.0 so the host backend (and the IconForge client) can reach it.
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
