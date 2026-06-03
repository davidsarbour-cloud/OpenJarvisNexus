"""
Etsy API v3 client — create/update listings, upload images, manage shop.
OAuth2 flow pour obtenir le token si pas configuré.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
from pathlib import Path

import httpx

ETSY_API_KEY        = os.getenv("ETSY_API_KEY", "")
ETSY_API_SECRET     = os.getenv("ETSY_SHARED_SECRET", "")
ETSY_ACCESS_TOKEN   = os.getenv("ETSY_ACCESS_TOKEN", "")
ETSY_REFRESH_TOKEN  = os.getenv("ETSY_REFRESH_TOKEN", "")
ETSY_SHOP_ID        = os.getenv("ETSY_SHOP_ID", "")
ETSY_SHOP_NAME      = os.getenv("ETSY_SHOP_NAME", "D3Dprintix")
ETSY_REDIRECT_URI   = os.getenv("ETSY_OAUTH_REDIRECT_URI", "http://localhost:8000/callback")
ETSY_BASE           = "https://openapi.etsy.com/v3"

# Store in-memory du code_verifier PKCE (survie le temps du flow OAuth)
_pkce_store: dict[str, str] = {}   # state → code_verifier


# ── PKCE helpers ─────────────────────────────────────────────────────────────

def _pkce_pair() -> tuple[str, str]:
    """Génère (code_verifier, code_challenge) pour PKCE S256."""
    verifier  = secrets.token_urlsafe(64)
    digest    = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge

def get_stored_verifier(state: str) -> str | None:
    """Récupère le code_verifier stocké pour cet état OAuth."""
    return _pkce_store.get(state)

def store_verifier(state: str, verifier: str) -> None:
    """Stocke le code_verifier associé à un état OAuth."""
    # Nettoyage : garde max 10 états en mémoire
    if len(_pkce_store) > 10:
        oldest = next(iter(_pkce_store))
        del _pkce_store[oldest]
    _pkce_store[state] = verifier


# ── Auth ──────────────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """Vrai si ETSY_ACCESS_TOKEN est configuré."""
    return bool(ETSY_ACCESS_TOKEN)


def get_oauth_url() -> tuple[str, str]:
    """
    Retourne (url_oauth, state) pour le flow PKCE S256.
    Le code_verifier est stocké en mémoire associé au state.
    """
    import secrets as _s
    state = _s.token_hex(8)
    verifier, challenge = _pkce_pair()
    store_verifier(state, verifier)
    url = (
        "https://www.etsy.com/oauth/connect"
        f"?response_type=code"
        f"&redirect_uri={ETSY_REDIRECT_URI}"
        f"&scope=listings_w+listings_r+email_r"
        f"&client_id={ETSY_API_KEY}"
        f"&state={state}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )
    return url, state


# ── Headers ───────────────────────────────────────────────────────────────────

def _headers(json_content: bool = True) -> dict:
    # This Etsy app is "Personal Access": the API requires the shared secret
    # appended to the keystring in x-api-key as "keystring:shared_secret".
    # Without it Etsy returns 403 "Shared secret is required in x-api-key header".
    api_key = f"{ETSY_API_KEY}:{ETSY_API_SECRET}" if ETSY_API_SECRET else ETSY_API_KEY
    h: dict = {
        "x-api-key": api_key,
        "Authorization": f"Bearer {ETSY_ACCESS_TOKEN}",
    }
    if json_content:
        h["Content-Type"] = "application/json"
    return h


def _auth_error() -> dict:
    return {
        "error": "Non authentifié — configure ETSY_ACCESS_TOKEN dans .env",
        "auth_url": "/v1/etsy/auth",
    }


# ── Listings ──────────────────────────────────────────────────────────────────

async def create_draft_listing(
    title: str,
    description: str,
    price_usd: float,
    tags: list[str],
    quantity: int = 999,
    who_made: str = "i_did",
    when_made: str = "2020_2025",
    taxonomy_id: int = 2078,
) -> dict:
    """
    Crée un listing en mode brouillon sur Etsy.
    Retourne le JSON de la réponse ou {"error": ...}.
    """
    if not is_authenticated():
        return _auth_error()

    body = {
        "title":       title,
        "description": description,
        "price":       round(price_usd, 2),
        "who_made":    who_made,
        "when_made":   when_made,
        "taxonomy_id": taxonomy_id,
        "tags":        tags[:13],   # Etsy limite à 13 tags
        "quantity":    quantity,
        "type":        "download",
        "state":       "draft",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{ETSY_BASE}/application/shops/{ETSY_SHOP_ID}/listings",
            headers=_headers(),
            json=body,
        )
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


async def upload_listing_image(listing_id: int | str, image_path: str) -> dict:
    """
    Upload une image sur un listing Etsy existant.
    image_path : chemin local vers le fichier image.
    """
    if not is_authenticated():
        return _auth_error()

    path = Path(image_path)
    if not path.exists():
        return {"error": f"Fichier introuvable: {image_path}"}

    url = f"{ETSY_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/images"
    async with httpx.AsyncClient(timeout=60) as client:
        with path.open("rb") as fh:  # NOSONAR - sync open required for httpx multipart upload compatibility
            resp = await client.post(
                url,
                headers=_headers(json_content=False),
                files={"image": (path.name, fh, "image/jpeg")},
            )
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


async def upload_listing_file(listing_id: int | str, file_path: str) -> dict:
    """
    Upload un fichier numérique (ex: STL) sur un listing Etsy.
    """
    if not is_authenticated():
        return _auth_error()

    path = Path(file_path)
    if not path.exists():
        return {"error": f"Fichier introuvable: {file_path}"}

    url = f"{ETSY_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/files"
    async with httpx.AsyncClient(timeout=120) as client:
        with path.open("rb") as fh:  # NOSONAR - sync open required for httpx multipart upload compatibility
            resp = await client.post(
                url,
                headers=_headers(json_content=False),
                files={"file": (path.name, fh, "application/octet-stream")},
                data={"name": path.name, "rank": 1},
            )
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


async def publish_listing(listing_id: int | str) -> dict:
    """
    Passe un listing de 'draft' à 'active'.
    """
    if not is_authenticated():
        return _auth_error()

    url = f"{ETSY_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            url,
            headers=_headers(),
            json={"state": "active"},
        )
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


async def get_shop_listings(limit: int = 25) -> list:
    """
    Récupère les listings actifs de la boutique.
    """
    if not is_authenticated():
        return [_auth_error()]

    url = f"{ETSY_BASE}/application/shops/{ETSY_SHOP_ID}/listings"
    params = {"limit": limit, "state": "active"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers(), params=params)
    if resp.is_success:
        data = resp.json()
        return data.get("results", data)
    return [{"error": resp.text, "status_code": resp.status_code}]
