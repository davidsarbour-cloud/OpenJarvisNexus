"""Minimal Printify REST client for the POD line — gated on PRINTIFY_API_KEY.

Capability ladder (degrades gracefully — never raises out of `sync`):
  no key                         -> {"status": "skipped"}      (assets stay local)
  key only                       -> upload image to library    {"status": "uploaded"}
  key + blueprint + provider     -> create a product draft      {"status": "product_created"}
  + PRINTIFY_AUTO_PUBLISH=1       -> publish to the connected store (Etsy)

Env:
  PRINTIFY_API_KEY            personal access token (printify.com/app/account/api)
  PRINTIFY_SHOP_ID            target shop id (GET /v1/shops.json to find it)
  PRINTIFY_BLUEPRINT_ID       e.g. 6 = Bella+Canvas 3001 tee (optional)
  PRINTIFY_PRINT_PROVIDER_ID  print provider for that blueprint (optional)
  PRINTIFY_AUTO_PUBLISH       "1" to push the draft live to the store (optional)
"""
from __future__ import annotations

import base64
import os

import httpx

API = "https://api.printify.com/v1"


def _key() -> str:
    return os.getenv("PRINTIFY_API_KEY", "")


def is_configured() -> bool:
    return bool(_key())


def _headers() -> dict:
    return {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}


def upload_image(filename: str, content: bytes) -> str | None:
    """Upload a PNG to the Printify media library. Returns the image id."""
    b64 = base64.b64encode(content).decode("ascii")
    r = httpx.post(f"{API}/uploads/images.json", headers=_headers(),
                   json={"file_name": filename, "contents": b64}, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


def _first_variant_ids(blueprint_id: str, provider_id: str, limit: int = 8) -> list[int]:
    """Pull a handful of variant ids for a blueprint+provider so the product has
    something to sell. Best-effort — returns [] on failure."""
    try:
        r = httpx.get(f"{API}/catalog/blueprints/{blueprint_id}/print_providers/"
                      f"{provider_id}/variants.json", headers=_headers(), timeout=30)
        r.raise_for_status()
        return [v["id"] for v in r.json().get("variants", [])[:limit]]
    except Exception:
        return []


def create_product(shop_id: str, blueprint_id: str, provider_id: str,
                   image_id: str, title: str, description: str,
                   tags: list[str]) -> str | None:
    """Create a draft product with the uploaded art on the front. Returns id."""
    variant_ids = _first_variant_ids(blueprint_id, provider_id)
    if not variant_ids:
        return None
    payload = {
        "title": title,
        "description": description,
        "tags": tags,
        "blueprint_id": int(blueprint_id),
        "print_provider_id": int(provider_id),
        "variants": [{"id": vid, "price": 2499, "is_enabled": True} for vid in variant_ids],
        "print_areas": [{
            "variant_ids": variant_ids,
            "placeholders": [{
                "position": "front",
                "images": [{"id": image_id, "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}],
            }],
        }],
    }
    r = httpx.post(f"{API}/shops/{shop_id}/products.json", headers=_headers(),
                   json=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


def publish_product(shop_id: str, product_id: str) -> bool:
    r = httpx.post(f"{API}/shops/{shop_id}/products/{product_id}/publish.json",
                   headers=_headers(),
                   json={"title": True, "description": True, "images": True,
                         "variants": True, "tags": True}, timeout=60)
    return r.status_code in (200, 201)


def sync(filename: str, png: bytes, title: str, description: str,
         tags: list[str]) -> dict:
    """Push a design to Printify as far as the env config allows. Best-effort:
    always returns a status dict, never raises."""
    if not is_configured():
        return {"status": "skipped", "reason": "no PRINTIFY_API_KEY — assets saved locally"}
    shop = os.getenv("PRINTIFY_SHOP_ID", "")
    blueprint = os.getenv("PRINTIFY_BLUEPRINT_ID", "")
    provider = os.getenv("PRINTIFY_PRINT_PROVIDER_ID", "")
    try:
        image_id = upload_image(filename, png)
        if not image_id:
            return {"status": "error", "reason": "image upload returned no id"}
        if not (shop and blueprint and provider):
            return {"status": "uploaded", "image_id": image_id,
                    "note": "image in Printify library; set PRINTIFY_SHOP_ID/"
                            "BLUEPRINT_ID/PRINT_PROVIDER_ID for auto product"}
        product_id = create_product(shop, blueprint, provider, image_id,
                                    title, description, tags)
        if not product_id:
            return {"status": "uploaded", "image_id": image_id,
                    "note": "no variants found for blueprint/provider — product not created"}
        out = {"status": "product_created", "product_id": product_id, "image_id": image_id}
        if os.getenv("PRINTIFY_AUTO_PUBLISH") == "1":
            out["published"] = publish_product(shop, product_id)
        return out
    except Exception as e:
        return {"status": "error", "reason": str(e)}
