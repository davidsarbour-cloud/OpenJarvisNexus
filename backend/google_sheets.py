"""
Google Sheets — intégration Nexus9.
Sauvegarde les résultats Daily Research + pipelines dans une Google Sheet.

Setup requis (une seule fois) :
  1. Google Cloud Console → créer un projet → activer "Google Sheets API"
  2. Créer un Service Account → télécharger le JSON → poser dans backend/google_credentials.json
  3. Ouvrir ta Google Sheet → Partager avec l'email du service account (éditeur)
  4. Copier l'ID de la sheet dans .env → GOOGLE_SHEETS_ID=xxx

Variables .env :
  GOOGLE_SHEETS_ID           = ID de la Google Sheet (dans l'URL)
  GOOGLE_CREDENTIALS_PATH    = chemin vers le JSON (défaut: backend/google_credentials.json)
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

CREDS_PATH  = os.getenv("GOOGLE_CREDENTIALS_PATH",
              str(Path(__file__).parent / "google_credentials.json"))
SHEETS_ID   = os.getenv("GOOGLE_SHEETS_ID", "")

# Noms des feuilles
SHEET_DAILY    = "Daily Research"
SHEET_PIPELINES = "Pipelines"

# En-têtes
HEADERS_DAILY = [
    "Date", "Heure", "Task #", "Catégorie", "Modèle",
    "Statut", "Résultat (extrait)", "Fichier",
]
HEADERS_PIPELINES = [
    "Date", "Heure", "Pipeline", "Statut", "Détails",
]


def _get_client():
    """Retourne un client gspread authentifié via service account."""
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
    return gspread.authorize(creds)


def _get_or_create_sheet(gc, title: str, headers: list[str]):
    """Ouvre ou crée une feuille dans la Google Sheet, ajoute les en-têtes si vide."""
    try:
        sh = gc.open_by_key(SHEETS_ID)
    except Exception as e:
        raise RuntimeError(f"Impossible d'ouvrir la Google Sheet ({SHEETS_ID}): {e}")

    try:
        ws = sh.worksheet(title)
    except Exception:
        ws = sh.add_worksheet(title=title, rows=1000, cols=len(headers))

    # Ajoute les en-têtes si la feuille est vide
    if ws.row_count == 0 or not ws.row_values(1):
        ws.append_row(headers, value_input_option="RAW")

    return ws


def save_daily_research(tasks: list[dict], date: str) -> bool:
    """
    Sauvegarde les 8 tâches du daily research dans la feuille 'Daily Research'.
    Chaque tâche = une ligne.
    """
    if not SHEETS_ID:
        print("⚠️  GOOGLE_SHEETS_ID manquant dans .env — Google Sheets désactivé")
        return False
    if not Path(CREDS_PATH).exists():
        print(f"⚠️  Credentials Google manquantes : {CREDS_PATH}")
        return False

    try:
        gc = _get_client()
        ws = _get_or_create_sheet(gc, SHEET_DAILY, HEADERS_DAILY)

        now = datetime.now()
        rows = []
        for t in tasks:
            result_text = t.get("result_preview", "")[:300].replace("\n", " ")
            rows.append([
                date,
                now.strftime("%H:%M"),
                t.get("task_id", "?"),
                t.get("category", ""),
                t.get("model", ""),
                "✅ OK" if t.get("ok") else "❌ Erreur",
                result_text,
                t.get("file", ""),
            ])

        ws.append_rows(rows, value_input_option="RAW")
        print(f"✅ Google Sheets — {len(rows)} lignes ajoutées dans '{SHEET_DAILY}'")
        return True

    except Exception as e:
        print(f"⚠️  Google Sheets erreur : {e}")
        return False


def save_pipeline_result(pipeline: str, status: str, details: str = "") -> bool:
    """Sauvegarde le résultat d'un pipeline dans la feuille 'Pipelines'."""
    if not SHEETS_ID or not Path(CREDS_PATH).exists():
        return False
    try:
        gc = _get_client()
        ws = _get_or_create_sheet(gc, SHEET_PIPELINES, HEADERS_PIPELINES)
        now = datetime.now()
        ws.append_row([
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M"),
            pipeline,
            status,
            details[:200],
        ], value_input_option="RAW")
        return True
    except Exception as e:
        print(f"⚠️  Google Sheets pipeline erreur : {e}")
        return False


def is_configured() -> bool:
    return bool(SHEETS_ID) and Path(CREDS_PATH).exists()
