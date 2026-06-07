"""
Social Router — endpoints FastAPI pour les stats d'audience des réseaux.

GET /v1/social/youtube/stats   — stats publiques de la chaîne YouTube

(TikTok viendra ici plus tard — il exige une app dev + OAuth, pas une
simple clé API comme YouTube.)
"""
from __future__ import annotations

from fastapi import APIRouter

from social import youtube_client as yt

router = APIRouter(prefix="/v1/social", tags=["Social"])


@router.get("/youtube/stats", summary="Stats d'audience de la chaîne YouTube")
async def youtube_stats():
    """
    Abonnés / vues / vidéos de la chaîne — carte audience du Command Center.
    Nécessite YOUTUBE_API_KEY + YOUTUBE_CHANNEL_ID dans backend/.env.
    """
    return await yt.get_channel_stats()
