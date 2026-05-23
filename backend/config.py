"""
Configuration centrale Nexus9 — source unique de vérité pour Ollama.

Importer depuis ce module plutôt que de redéfinir
os.getenv("OLLAMA_HOST", ...) dans chaque fichier :

    from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_NUM_CTX
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# 127.0.0.1 force IPv4 — évite le stall ~2s de résolution ::1 sur Windows.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")
# 4096 garde qwen3:14b 100% sur GPU (RTX 4070 SUPER, 12 Go) ~44 tok/s.
# Le défaut Ollama (8192) fait déborder le KV cache sur CPU → ~24 tok/s.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

# ── Brain Obsidian — source de vérité; les rapports IA y sont écrits (plus OneDrive) ──
BRAIN_DIR          = Path(__file__).resolve().parent / "BRAIN" / "BRAIN"
BRAIN_REPORTS_DIR  = BRAIN_DIR / "08_Command-Center" / "reports"
BRAIN_RESEARCH_DIR = BRAIN_DIR / "05_Resources" / "research"
