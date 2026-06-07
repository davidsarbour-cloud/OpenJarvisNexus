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
        f"&scope=listings_w+listings_r+transactions_r+email_r"
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


# ── Token refresh / persistence ─────────────────────────────────────────────
# Les access tokens Etsy expirent en 1h. On rafraîchit automatiquement via le
# refresh token (valide 90 j) et on persiste le nouveau token dans backend/.env
# pour qu'il survive aux redémarrages.

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"   # backend/.env


def _persist_tokens_to_env(access: str, refresh: str) -> None:
    """Réécrit ETSY_ACCESS_TOKEN / ETSY_REFRESH_TOKEN dans backend/.env."""
    try:
        if not _ENV_PATH.exists():
            return
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
        out, seen_a, seen_r = [], False, False
        for ln in lines:
            if ln.startswith("ETSY_ACCESS_TOKEN="):
                out.append(f"ETSY_ACCESS_TOKEN={access}")
                seen_a = True
            elif ln.startswith("ETSY_REFRESH_TOKEN="):
                out.append(f"ETSY_REFRESH_TOKEN={refresh}")
                seen_r = True
            else:
                out.append(ln)
        if not seen_a:
            out.append(f"ETSY_ACCESS_TOKEN={access}")
        if not seen_r:
            out.append(f"ETSY_REFRESH_TOKEN={refresh}")
        _ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    except Exception:
        pass


async def refresh_access_token() -> dict:
    """
    Rafraîchit l'access token via ETSY_REFRESH_TOKEN (grant_type=refresh_token).
    Met à jour les globals en mémoire + persiste dans backend/.env.
    Retourne {ok, expires_in} ou {ok: False, error}. Ne renvoie jamais le token.
    """
    global ETSY_ACCESS_TOKEN, ETSY_REFRESH_TOKEN
    if not ETSY_API_KEY:
        return {"ok": False, "error": "ETSY_API_KEY manquant dans .env"}
    if not ETSY_REFRESH_TOKEN:
        return {"ok": False, "error": "ETSY_REFRESH_TOKEN manquant — refais le flow /v1/etsy/auth"}

    payload = {
        "grant_type":    "refresh_token",
        "client_id":     ETSY_API_KEY,
        "refresh_token": ETSY_REFRESH_TOKEN,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.etsy.com/v3/public/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if not resp.is_success:
        return {"ok": False, "error": resp.text, "status_code": resp.status_code}

    data    = resp.json()
    access  = data.get("access_token", "")
    refresh = data.get("refresh_token", ETSY_REFRESH_TOKEN)
    if not access:
        return {"ok": False, "error": "réponse Etsy sans access_token"}
    ETSY_ACCESS_TOKEN  = access
    ETSY_REFRESH_TOKEN = refresh
    _persist_tokens_to_env(access, refresh)
    return {"ok": True, "expires_in": data.get("expires_in")}


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


# ── Receipts / Revenue ──────────────────────────────────────────────────────────

async def get_shop_receipts(limit: int = 100, min_created: int | None = None) -> dict:
    """
    Récupère les commandes payées (receipts) de la boutique.
    min_created : epoch seconds (filtre les commandes créées après cette date).
    """
    if not is_authenticated():
        return _auth_error()
    if not ETSY_SHOP_ID:
        return {"error": "ETSY_SHOP_ID non configuré dans .env"}

    url = f"{ETSY_BASE}/application/shops/{ETSY_SHOP_ID}/receipts"
    params: dict = {"limit": limit, "was_paid": "true"}
    if min_created is not None:
        params["min_created"] = int(min_created)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        # Access token expiré (1h) → refresh auto + un seul retry.
        if resp.status_code == 401:
            refreshed = await refresh_access_token()
            if refreshed.get("ok"):
                resp = await client.get(url, headers=_headers(), params=params)
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


async def get_shop_revenue(days: int = 30) -> dict:
    """
    Agrège le chiffre d'affaires Etsy sur les N derniers jours (commandes payées).
    Alimente la carte $$$ du Command Center.
    Retourne {connected, days, currency, total, orders, today, last_order, recent[]}.
    """
    import time as _time
    now         = int(_time.time())
    midnight    = now - (now % 86400)
    min_created = now - days * 86400

    data = await get_shop_receipts(limit=100, min_created=min_created)
    if not isinstance(data, dict) or data.get("error"):
        return {
            "connected": False,
            "error":     (data or {}).get("error", "réponse Etsy invalide") if isinstance(data, dict) else "réponse Etsy invalide",
            "days":      days, "currency": "USD",
            "total":     0.0, "orders": 0, "today": 0.0,
            "last_order": None, "recent": [],
        }

    results  = data.get("results", []) or []
    total    = 0.0
    today    = 0.0
    currency = "USD"
    recent   = []
    for r in results:
        gt       = r.get("grandtotal") or {}
        divisor  = float(gt.get("divisor", 1) or 1)
        amount   = float(gt.get("amount", 0)) / divisor
        currency = gt.get("currency_code", currency)
        total   += amount
        ts       = int(r.get("created_timestamp", 0) or 0)
        if ts >= midnight:
            today += amount
        recent.append({
            "name":       r.get("name", ""),
            "amount":     round(amount, 2),
            "ts":         ts,
            "is_shipped": bool(r.get("is_shipped", False)),
        })
    recent.sort(key=lambda x: x["ts"], reverse=True)

    return {
        "connected":  True,
        "days":       days,
        "currency":   currency,
        "total":      round(total, 2),
        "orders":     len(results),
        "today":      round(today, 2),
        "last_order": recent[0] if recent else None,
        "recent":     recent[:5],
    }
