"""
YouTube Data API v3 client — read-only channel audience stats for the
Command Center.

Auth: a simple API key (YOUTUBE_API_KEY), generated in Google Cloud Console
→ APIs & Services → Credentials → "Create credentials" → API key, with the
"YouTube Data API v3" enabled. NO OAuth needed for public channel stats.
The key is passed as the `key` query param. READ-ONLY: we only GET
/youtube/v3/channels to read subscriber/view/video counts.

Channel target: YOUTUBE_CHANNEL_ID (preferred, the UC… id) or, as a
fallback, YOUTUBE_HANDLE (the @handle). Set one of them in backend/.env.

Shape of get_channel_stats() mirrors the connected/_disconnected pattern of
commerce.gumroad_client so the Command Center cards behave the same way.
"""
from __future__ import annotations

import os

import httpx

YOUTUBE_API_KEY    = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_HANDLE     = os.getenv("YOUTUBE_HANDLE", "")
YT_BASE            = "https://www.googleapis.com/youtube/v3"


# ── Auth ──────────────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """Vrai si YOUTUBE_API_KEY est configurée."""
    return bool(YOUTUBE_API_KEY)


def _auth_error() -> str:
    return ("Non authentifié — configure YOUTUBE_API_KEY dans backend/.env "
            "(Google Cloud Console → Credentials → API key, YouTube Data API v3 activée).")


def _disconnected(error: str) -> dict:
    return {
        "connected": False, "error": error,
        "title": "", "subscribers": 0, "subs_hidden": False,
        "views": 0, "videos": 0, "thumbnail": None, "channel_id": "",
    }


def _channel_param() -> dict:
    """Identifiant de la chaîne pour /channels : id=UC… ou forHandle=@…."""
    if YOUTUBE_CHANNEL_ID:
        return {"id": YOUTUBE_CHANNEL_ID}
    if YOUTUBE_HANDLE:
        return {"forHandle": YOUTUBE_HANDLE.lstrip("@")}
    return {}


def _api_error(resp: httpx.Response) -> str:
    """Extrait le message d'erreur de l'API YouTube (sinon code HTTP brut)."""
    try:
        msg = ((resp.json() or {}).get("error", {}) or {}).get("message")
        if msg:
            return f"YouTube API {resp.status_code}: {msg}"
    except Exception:
        pass
    return f"YouTube API erreur {resp.status_code}"


# ── Channel stats ─────────────────────────────────────────────────────────────

async def get_channel_stats() -> dict:
    """
    Stats publiques de la chaîne YouTube — alimente la carte audience du
    Command Center.
    Retourne {connected, channel_id, title, subscribers, subs_hidden,
    views, videos, thumbnail}.
    """
    if not is_authenticated():
        return _disconnected(_auth_error())

    ident = _channel_param()
    if not ident:
        return _disconnected(
            "YOUTUBE_CHANNEL_ID (ou YOUTUBE_HANDLE) manquant dans backend/.env."
        )

    params = {"part": "snippet,statistics", "key": YOUTUBE_API_KEY, **ident}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{YT_BASE}/channels", params=params)
    except Exception as e:  # réseau / DNS / timeout
        return _disconnected(f"YouTube injoignable : {e}")

    if not resp.is_success:
        return _disconnected(_api_error(resp))

    items = (resp.json() or {}).get("items") or []
    if not items:
        return _disconnected(
            "Chaîne introuvable — vérifie YOUTUBE_CHANNEL_ID / YOUTUBE_HANDLE."
        )

    it     = items[0]
    snip   = it.get("snippet", {}) or {}
    stats  = it.get("statistics", {}) or {}
    thumbs = snip.get("thumbnails", {}) or {}
    thumb  = (thumbs.get("default") or {}).get("url")

    return {
        "connected":   True,
        "channel_id":  it.get("id", ""),
        "title":       snip.get("title", ""),
        "subscribers": int(stats.get("subscriberCount", 0) or 0),
        "subs_hidden": bool(stats.get("hiddenSubscriberCount", False)),
        "views":       int(stats.get("viewCount", 0) or 0),
        "videos":      int(stats.get("videoCount", 0) or 0),
        "thumbnail":   thumb,
    }
