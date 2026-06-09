"""HueForge — pipeline de préparation d'images pour HueForge (impression couleur).

Génère (ComfyUI / FLUX) ou ingère une image, puis : redimensionne → augmente le
contraste → supprime le fond → sauvegarde dans le dossier « Prêt pour HueForge ».
Étape report : analyse de palette (couleurs dominantes) pour planifier les filaments.

Modules :
  - image_ops          : opérations PIL pures (resize / contrast / rembg / palette)
  - hueforge_pipeline  : gestion des missions + orchestration des étapes
  - hueforge_router    : APIRouter FastAPI (/v1/hueforge/*)
"""
