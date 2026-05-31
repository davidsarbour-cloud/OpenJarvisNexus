# IconForge — ComfyUI service (Phase 2)

Dockerized ComfyUI + FLUX Schnell FP8 for the **artistic** icon packs. The
Minimal Black pilot stays procedural (Pillow) and does **not** need this.

## What runs where

- **ComfyUI** runs in a container on `:8188`, GPU via WSL2 passthrough.
- **Models** live in `./models/` (bind mount, gitignored) so the 17 GB
  checkpoint survives image rebuilds.
- The **backend** (`iconforge/generators/comfyui_client.py`) talks to it over
  HTTP — submit `/prompt`, poll `/history/{id}`, fetch `/view`.

## One-time setup

```powershell
# 1. Download the FLUX Schnell FP8 checkpoint (~17 GB, Apache-2.0 = commercial OK)
./download_models.ps1

# 2. Build + start the container (first build ~10 min: torch + ComfyUI deps)
docker compose up -d --build

# 3. Verify
curl http://localhost:8188/system_stats
```

## Daily use

```powershell
docker compose up -d        # start
docker compose logs -f      # watch
docker compose down         # stop (models persist)
```

## VRAM handshake (important)

FLUX Schnell FP8 (~11 GB) + Ollama (qwen3:14b ~10 GB) do **not** fit together
in 12 GB. The pipeline unloads Ollama (`keep_alive: 0`) before a batch and lets
it reload on the next chat. See `generators/comfyui_client.py::unload_ollama`.

## Files

| File | Role |
|---|---|
| `Dockerfile` | ComfyUI on CUDA 12.4 runtime |
| `docker-compose.yml` | service `comfyui`, GPU, `:8188`, model volumes |
| `download_models.ps1` | fetch FLUX Schnell FP8 into `models/checkpoints/` |
| `workflows/flux_schnell.json` | API-format graph `generate()` injects into |
