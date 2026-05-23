"""
Shopify Admin API client — create products, variants, media.
Nécessite: SHOPIFY_SHOP_URL + SHOPIFY_ACCESS_TOKEN dans .env
"""
from __future__ import annotations

import os
from typing import Optional, Union

import httpx

SHOPIFY_SHOP_URL     = os.getenv("SHOPIFY_STORE") or os.getenv("SHOPIFY_SHOP_URL", "")  # .env: SHOPIFY_STORE = myshop.myshopify.com
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION  = "2024-01"


# ── Auth ──────────────────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Vrai si SHOPIFY_SHOP_URL et SHOPIFY_ACCESS_TOKEN sont définis."""
    return bool(SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN)


def _base_url() -> str:
    return f"https://{SHOPIFY_SHOP_URL}/admin/api/{SHOPIFY_API_VERSION}"


def _headers() -> dict:
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def _config_error() -> dict:
    return {
        "error": "Shopify non configuré — définis SHOPIFY_SHOP_URL et SHOPIFY_ACCESS_TOKEN dans .env",
    }


# ── Products ──────────────────────────────────────────────────────────────────

async def create_product(
    title: str,
    description: str,
    price: float,
    tags: Union[list[str], str],
    images: Optional[list] = None,
    vendor: str = "D3Dprintix",
) -> dict:
    """
    Crée un produit Shopify (téléchargement numérique, sans expédition).
    images : liste optionnelle de dicts {"src": url} ou {"attachment": base64}.
    Retourne le JSON de la réponse ou {"error": ...}.
    """
    if not is_configured():
        return _config_error()

    tag_str = tags if isinstance(tags, str) else ", ".join(tags)

    product_body: dict = {
        "title":     title,
        "body_html": description,
        "vendor":    vendor,
        "tags":      tag_str,
        "variants": [
            {
                "price":              str(round(price, 2)),
                "requires_shipping":  False,
                "taxable":            True,
            }
        ],
    }
    if images:
        product_body["images"] = images

    payload = {"product": product_body}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base_url()}/products.json",
            headers=_headers(),
            json=payload,
        )
    if resp.is_success:
        return resp.json().get("product", resp.json())
    return {"error": resp.text, "status_code": resp.status_code}


async def add_product_image(
    product_id: Union[int, str],
    image_url_or_base64: str,
) -> dict:
    """
    Ajoute une image à un produit Shopify existant.
    Accepte une URL publique ou une chaîne base64 (sans préfixe data:...).
    """
    if not is_configured():
        return _config_error()

    # Détection URL vs base64
    if image_url_or_base64.startswith(("http://", "https://")):
        image_payload: dict = {"src": image_url_or_base64}
    else:
        image_payload = {"attachment": image_url_or_base64}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base_url()}/products/{product_id}/images.json",
            headers=_headers(),
            json={"image": image_payload},
        )
    if resp.is_success:
        return resp.json().get("image", resp.json())
    return {"error": resp.text, "status_code": resp.status_code}


async def list_products(limit: int = 25) -> list:
    """
    Récupère la liste des produits de la boutique Shopify.
    """
    if not is_configured():
        return [_config_error()]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{_base_url()}/products.json",
            headers=_headers(),
            params={"limit": limit, "status": "active"},
        )
    if resp.is_success:
        return resp.json().get("products", [])
    return [{"error": resp.text, "status_code": resp.status_code}]
