"""
FastAPI router — OAuth2 Etsy (PKCE S256).
Endpoints:
  GET  /v1/etsy/auth           → URL d'autorisation Etsy
  GET  /v1/etsy/callback       → Callback OAuth (échange de code)
  POST /v1/etsy/exchange-token → Échange code + verifier contre access_token
  GET  /v1/etsy/status         → Statut authentification
"""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1/etsy", tags=["etsy-oauth"])


# ── /auth ────────────────────────────────────────────────────────────────────

@router.get("/auth", summary="URL d'autorisation Etsy OAuth")
def etsy_auth_redirect():
    """Retourne l'URL OAuth Etsy (PKCE). Le verifier est stocké en mémoire."""
    from commerce.etsy_client import get_oauth_url, ETSY_API_KEY
    if not ETSY_API_KEY:
        return JSONResponse(status_code=400, content={"ok": False, "error": "ETSYPUBLIC_KEY manquant dans .env"})
    url, state = get_oauth_url()
    return {
        "oauth_url":    url,
        "state":        state,
        "redirect_uri": "http://localhost:8000/callback",
        "instruction":  "Ouvre oauth_url dans le navigateur — le callback /callback s'occupe du reste automatiquement",
    }


# ── /callback ────────────────────────────────────────────────────────────────

@router.get("/callback", summary="Callback OAuth Etsy")
async def etsy_callback(
    code:  Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """
    Callback OAuth — reçoit le code d'autorisation Etsy.
    Pour finaliser, appelle POST /v1/etsy/exchange-token avec ce code
    et ton code_verifier PKCE.
    """
    if error:
        return JSONResponse(status_code=400, content={"ok": False, "error": error})
    if not code:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Code manquant"})

    return {
        "ok":          True,
        "code":        code,
        "state":       state,
        "instruction": "Ajoute dans .env: ETSYYOAUTH_ACCESS_TOKEN=<token>",
        "next_step":   "POST /v1/etsy/exchange-token avec ce code et ton code_verifier PKCE",
    }


# ── /exchange-token ──────────────────────────────────────────────────────────

from pydantic import BaseModel

class TokenExchangeRequest(BaseModel):
    code:          str
    state:         str = ""          # state OAuth retourné par Etsy
    code_verifier: str = ""          # optionnel — auto-lookup depuis le store si state fourni
    redirect_uri:  str = "http://localhost:8000/callback"


@router.post("/exchange-token", summary="Échange le code OAuth contre un access_token")
async def etsy_exchange_token(body: TokenExchangeRequest):
    """
    Échange le code d'autorisation contre un access_token Etsy.
    Le code_verifier est récupéré automatiquement depuis le store PKCE si state est fourni.
    """
    from commerce.etsy_client import ETSY_API_KEY, ETSY_REDIRECT_URI, get_stored_verifier

    if not ETSY_API_KEY:
        return JSONResponse(status_code=400, content={"ok": False, "error": "ETSYPUBLIC_KEY manquant dans .env"})

    # Récupère le verifier depuis le store si pas fourni directement
    verifier = body.code_verifier
    if not verifier and body.state:
        verifier = get_stored_verifier(body.state) or ""

    if not verifier:
        return JSONResponse(status_code=400, content={
            "ok": False,
            "error": "code_verifier manquant — relance /v1/etsy/auth et utilise le même flow"
        })

    payload = {
        "grant_type":    "authorization_code",
        "client_id":     ETSY_API_KEY,
        "redirect_uri":  body.redirect_uri or ETSY_REDIRECT_URI,
        "code":          body.code,
        "code_verifier": verifier,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.etsy.com/v3/public/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.is_success:
        data = resp.json()
        token = data.get("access_token", "")
        env_line = f"ETSYYOAUTH_ACCESS_TOKEN={token}"
        return {
            "ok":           True,
            "access_token": token,
            "refresh_token": data.get("refresh_token", ""),
            "expires_in":   data.get("expires_in"),
            "env_line":     env_line,
            "instruction":  f"Copie dans backend/.env: {env_line}",
        }

    return JSONResponse(status_code=resp.status_code, content={"ok": False, "error": resp.text})


# ── /status ──────────────────────────────────────────────────────────────────

@router.get("/status", summary="Statut authentification Etsy")
def etsy_status():
    """Vérifie si le client Etsy est authentifié."""
    from commerce.etsy_client import is_authenticated, ETSY_SHOP_NAME, ETSY_SHOP_ID

    authenticated = is_authenticated()
    return {
        "authenticated": authenticated,
        "shop_name":     ETSY_SHOP_NAME,
        "shop_id":       ETSY_SHOP_ID,
        "auth_url":      "/v1/etsy/auth" if not authenticated else None,
    }
