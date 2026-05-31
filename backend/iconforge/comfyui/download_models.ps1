# Download the FLUX Schnell FP8 all-in-one checkpoint into the bind-mounted
# models volume. Apache-2.0 weights -> commercially usable for selling packs.
# ~17 GB. Idempotent: skips if the file already exists with a sane size.
# (ASCII only on purpose: PowerShell 5.1 mis-decodes UTF-8 dashes and fails to parse.)
$ErrorActionPreference = "Stop"
$dir  = Join-Path $PSScriptRoot "models\checkpoints"
$dest = Join-Path $dir "flux1-schnell-fp8.safetensors"
$url  = "https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors?download=true"

New-Item -ItemType Directory -Force -Path $dir | Out-Null

if (Test-Path $dest) {
    $gb = [math]::Round((Get-Item $dest).Length / 1GB, 2)
    if ($gb -gt 10) {
        Write-Host "Already present ($gb GB). Skipping."
        exit 0
    }
    Write-Host "Partial file ($gb GB) found. Re-downloading (curl resumes with -C -)."
}

Write-Host "Downloading FLUX Schnell FP8 (~17 GB) to $dest"
curl.exe -L --fail --retry 3 -C - -o $dest $url
$gb = [math]::Round((Get-Item $dest).Length / 1GB, 2)
Write-Host "Done. Size: $gb GB"
