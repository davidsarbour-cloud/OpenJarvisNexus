"""
etsy_integration.py
Classe complète pour gérer tous les appels à l'API Etsy v3
Placer dans : C:\OpenJarvisNexus\backend\etsy\etsy_integration.py
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ━━━ CONFIGURATION LOGGING ━━━
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("etsy/logs/etsy_api.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


class EtsyClient:
    """
    Client complet pour l'API Etsy v3
    Gère : OAuth, listings, images, variantes, publication
    """

    BASE_URL = "https://openapi.etsy.com/v3/application"
    TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
    TOKEN_FILE = Path("etsy/config/oauth-tokens.json")

    def __init__(self):
        self.api_key    = os.getenv("ETSYPUBLIC_KEY")
        self.secret     = os.getenv("ETSYYOUR_SECRET")
        self.shop_id    = os.getenv("ETSYSHOP_ID")
        self.shop_name  = os.getenv("ETSYSHOP_NAME")
        self.access_token  = os.getenv("ETSYYOAUTH_ACCESS_TOKEN", "")
        self.refresh_token = os.getenv("ETSYYOAUTH_REFRESH_TOKEN", "")

        # Charger tokens depuis fichier si disponibles
        self._load_tokens_from_file()

        # Rate limit : 10 req/sec max
        self._last_request_time = 0
        self._min_interval = 0.15  # 150ms entre chaque requête

        log.info(f"✅ EtsyClient initialisé — Shop: {self.shop_name}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 1 : AUTHENTIFICATION & TOKENS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_tokens_from_file(self):
        """Charge les tokens OAuth depuis le fichier JSON"""
        if self.TOKEN_FILE.exists():
            try:
                with open(self.TOKEN_FILE, "r") as f:
                    data = json.load(f)
                self.access_token  = data.get("access_token", self.access_token)
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                self._token_expires_at = data.get("expires_at", "")
                log.info("🔑 Tokens chargés depuis oauth-tokens.json")
            except Exception as e:
                log.warning(f"⚠️ Impossible de charger les tokens: {e}")

    def _save_tokens_to_file(self, access_token: str, refresh_token: str, expires_in: int):
        """Sauvegarde les tokens dans le fichier JSON"""
        self.TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "expires_in":    expires_in,
            "generated_at":  datetime.now().isoformat(),
            "expires_at":    (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        }
        with open(self.TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)
        log.info("💾 Tokens sauvegardés dans oauth-tokens.json")

    def refresh_access_token(self) -> bool:
        """Rafraîchit l'access_token avec le refresh_token"""
        if not self.refresh_token:
            log.error("❌ Pas de refresh_token disponible")
            return False

        try:
            response = requests.post(
                self.TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type":    "refresh_token",
                    "client_id":     self.api_key,
                    "refresh_token": self.refresh_token
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            self.access_token  = data["access_token"]
            self.refresh_token = data.get("refresh_token", self.refresh_token)
            self._save_tokens_to_file(
                self.access_token,
                self.refresh_token,
                data.get("expires_in", 3600)
            )
            log.info("✅ Access token rafraîchi avec succès")
            return True

        except Exception as e:
            log.error(f"❌ Erreur refresh token: {e}")
            return False

    def _get_headers(self) -> dict:
        """Headers pour tous les appels API Etsy"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key":     self.api_key,
            "Content-Type":  "application/json"
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 2 : RATE LIMITING & REQUÊTES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _rate_limit(self):
        """Respecte le rate limit Etsy (10 req/sec)"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, method: str, endpoint: str, retries: int = 3, **kwargs) -> dict:
        """
        Requête HTTP avec retry automatique et gestion rate limit
        """
        self._rate_limit()
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(retries):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self._get_headers(),
                    timeout=30,
                    **kwargs
                )

                # Token expiré → refresh et retry
                if response.status_code == 401:
                    log.warning("🔄 Token expiré, rafraîchissement...")
                    if self.refresh_access_token():
                        continue
                    raise Exception("Impossible de rafraîchir le token")

                # Rate limit → attendre et retry
                if response.status_code == 429:
                    wait = int(response.headers.get("Retry-After", 60))
                    log.warning(f"⏱️ Rate limit atteint, attente {wait}s...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                log.warning(f"⚠️ Tentative {attempt + 1}/{retries} échouée: {e}")
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))  # Backoff exponentiel
                else:
                    raise

        raise Exception(f"Toutes les tentatives ont échoué pour {endpoint}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 3 : LISTINGS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def create_draft_listing(self, product: dict) -> dict:
        """
        Crée un listing en mode DRAFT sur Etsy
        
        Args:
            product: dict avec title, description, price_usd, tags, material
        
        Returns:
            dict avec listing_id et autres infos
        """
        log.info(f"📝 Création listing draft: {product.get('title_etsy', '')[:50]}...")

        payload = {
            "quantity":            999,
            "title":               product["title_etsy"],
            "description":         product["description_etsy"],
            "price":               float(product["price_usd"]),
            "who_made":            "i_did",
            "is_supply":           False,
            "when_made":           "made_to_order",
            "taxonomy_id":         1,
            "state":               "draft",
            "shipping_profile_id": int(os.getenv("ETSY_SHIPPING_PROFILE_ID", 0)),
            "tags":                product.get("tags_etsy", [])[:13],
            "materials":           [product.get("material", "PLA")],
            "type":                "physical"
        }

        result = self._request(
            "POST",
            f"/shops/{self.shop_id}/listings",
            json=payload
        )

        listing_id = result["listing_id"]
        log.info(f"✅ Draft créé — listing_id: {listing_id}")
        return result

    def publish_listing(self, listing_id: int) -> dict:
        """
        Publie un listing (passe de draft à active)
        ⚠️ Coûte $0.20 USD sur Etsy
        """
        log.info(f"🚀 Publication listing {listing_id}...")
        result = self._request(
            "PATCH",
            f"/shops/{self.shop_id}/listings/{listing_id}",
            json={"state": "active"}
        )
        log.info(f"✅ Listing {listing_id} publié — URL: https://etsy.com/listing/{listing_id}")
        return result

    def update_listing(self, listing_id: int, updates: dict) -> dict:
        """Met à jour un listing existant"""
        log.info(f"✏️ Mise à jour listing {listing_id}...")
        return self._request(
            "PATCH",
            f"/shops/{self.shop_id}/listings/{listing_id}",
            json=updates
        )

    def get_listing(self, listing_id: int) -> dict:
        """Récupère les infos d'un listing"""
        return self._request("GET", f"/listings/{listing_id}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 4 : IMAGES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def upload_image(self, listing_id: int, image_path: str, rank: int = 1) -> dict:
        """
        Upload une image vers un listing Etsy
        
        Args:
            listing_id: ID du listing Etsy
            image_path: Chemin local vers l'image
            rank: Position de l'image (1 = principale)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image introuvable: {image_path}")

        log.info(f"📸 Upload image {image_path.name} → listing {listing_id} (rank {rank})")

        self._rate_limit()
        url = f"{self.BASE_URL}/shops/{self.shop_id}/listings/{listing_id}/images"

        # Upload en multipart — PAS de Content-Type JSON ici
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key":     self.api_key
        }

        with open(image_path, "rb") as img:
            files   = {"image": (image_path.name, img, "image/jpeg")}
            data    = {"rank": rank, "overwrite": "true"}
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)

        if response.status_code == 401:
            self.refresh_access_token()
            with open(image_path, "rb") as img:
                files    = {"image": (image_path.name, img, "image/jpeg")}
                data     = {"rank": rank, "overwrite": "true"}
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)

        response.raise_for_status()
        log.info(f"✅ Image uploadée avec succès — rank {rank}")
        return response.json()

    def upload_all_images(self, listing_id: int, product_id: str) -> list:
        """
        Upload toutes les images d'un produit depuis le dossier local
        Dossier attendu : etsy/data/images/{product_id}/
        """
        images_dir = Path(f"etsy/data/images/{product_id}")
        if not images_dir.exists():
            log.warning(f"⚠️ Dossier images introuvable: {images_dir}")
            return []

        results = []
        extensions = {".jpg", ".jpeg", ".png", ".webp"}
        image_files = sorted([
            f for f in images_dir.iterdir()
            if f.suffix.lower() in extensions
        ])

        for rank, image_file in enumerate(image_files[:10], start=1):
            try:
                result = self.upload_image(listing_id, str(image_file), rank)
                results.append(result)
                time.sleep(0.5)  # Petite pause entre les uploads
            except Exception as e:
                log.error(f"❌ Erreur upload {image_file.name}: {e}")

        log.info(f"📸 {len(results)}/{len(image_files)} images uploadées")
        return results

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 5 : VARIANTES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def add_variants(self, listing_id: int, colors: list, sizes: list, base_price: float) -> dict:
        """
        Ajoute les variantes couleurs × tailles à un listing
        
        Args:
            listing_id: ID du listing
            colors: Liste de couleurs ["Black", "White", "Green"]
            sizes: Liste de tailles ["Small", "Medium", "Large"]
            base_price: Prix de base en USD
        """
        log.info(f"🎨 Ajout variantes: {len(colors)} couleurs × {len(sizes)} tailles")

        # Ajustements prix par taille
        size_adjustments = {
            "Small":  -3.00,
            "Medium":  0.00,
            "Large":   5.00,
            "XL":      8.00,
            "XXL":    10.00
        }

        products = []
        for color in colors:
            for size in sizes:
                adjust = size_adjustments.get(size, 0)
                price  = round(base_price + adjust, 2)
                products.append({
                    "sku":      f"{color[:3].upper()}-{size[:3].upper()}",
                    "price":    price,
                    "quantity": 999,
                    "is_enabled": True,
                    "property_values": [
                        {
                            "property_id":   200,
                            "property_name": "Color",
                            "values":        [color]
                        },
                        {
                            "property_id":   100,
                            "property_name": "Size",
                            "values":        [size]
                        }
                    ]
                })

        result = self._request(
            "PUT",
            f"/listings/{listing_id}/inventory",
            json={
                "products":              products,
                "price_on_property":     [200, 100],
                "quantity_on_property":  []
            }
        )

        log.info(f"✅ {len(products)} variantes ajoutées")
        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 6 : PIPELINE COMPLET
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def create_full_listing(self, product: dict, publish: bool = False) -> dict:
        """
        Pipeline complet : Draft → Images → Variantes → (Publish)
        
        Args:
            product: dict complet du produit (depuis Google Sheets)
            publish: True pour publier directement (coûte $0.20)
        
        Returns:
            dict avec listing_id, url, status
        """
        result = {
            "product_id":  product.get("product_id"),
            "listing_id":  None,
            "listing_url": None,
            "status":      "error",
            "error":       None
        }

        try:
            # ÉTAPE 1 : Créer le draft
            draft = self.create_draft_listing(product)
            listing_id = draft["listing_id"]
            result["listing_id"]  = listing_id
            result["listing_url"] = f"https://www.etsy.com/listing/{listing_id}"

            # ÉTAPE 2 : Upload images
            time.sleep(1)
            self.upload_all_images(listing_id, product.get("product_id", ""))

            # ÉTAPE 3 : Ajouter variantes
            time.sleep(1)
            colors = product.get("colors_array", ["One Color"])
            sizes  = product.get("sizes_array",  ["One Size"])
            if colors and sizes:
                self.add_variants(listing_id, colors, sizes, float(product["price_usd"]))

            # ÉTAPE 4 : Publier (optionnel)
            time.sleep(1)
            if publish:
                self.publish_listing(listing_id)
                result["status"] = "published"
                log.info(f"🎉 Listing publié: {result['listing_url']}")
            else:
                result["status"] = "draft"
                log.info(f"📝 Listing en draft: {result['listing_url']}")

        except Exception as e:
            result["error"] = str(e)
            log.error(f"❌ Erreur create_full_listing: {e}")

        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 7 : UTILITAIRES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_shop_info(self) -> dict:
        """Récupère les infos de la boutique"""
        return self._request("GET", f"/shops/{self.shop_id}")

    def get_shipping_profiles(self) -> list:
        """Liste les profils d'expédition disponibles"""
        result = self._request("GET", f"/shops/{self.shop_id}/shipping-profiles")
        profiles = result.get("results", [])
        for p in profiles:
            log.info(f"📦 Profil: {p['title']} — ID: {p['shipping_profile_id']}")
        return profiles

    def test_connection(self) -> bool:
        """Teste la connexion à l'API Etsy"""
        try:
            info = self.get_shop_info()
            log.info(f"✅ Connexion OK — Boutique: {info.get('shop_name')} | Listings: {info.get('listing_active_count')}")
            return True
        except Exception as e:
            log.error(f"❌ Connexion échouée: {e}")
            return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST RAPIDE (lance avec: python etsy_integration.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("../.env")  # Charge le .env depuis backend/

    client = EtsyClient()

    # Test 1 : Connexion
    print("\n━━━ TEST CONNEXION ━━━")
    client.test_connection()

    # Test 2 : Profils d'expédition (pour trouver ton SHIPPING_PROFILE_ID)
    print("\n━━━ PROFILS EXPÉDITION ━━━")
    client.get_shipping_profiles()

    # Test 3 : Créer un listing de test (draft seulement, pas de publication)
    print("\n━━━ TEST CRÉATION LISTING (DRAFT) ━━━")
    test_product = {
        "product_id":       "test_001",
        "title_etsy":       "3D Printed Dragon Geometric Vase | Fantasy Home Decor | Unique Gift",
        "description_etsy": "Beautiful 3D printed dragon vase. Made to order in 3-5 days.",
        "price_usd":        34.99,
        "tags_etsy":        ["3d printed", "dragon vase", "home decor", "fantasy", "gift", "unique", "handmade", "3d print", "vase", "dragon", "geometric", "modern", "art"],
        "material":         "PLA",
        "colors_array":     ["Black", "White"],
        "sizes_array":      ["Small", "Medium"]
    }
    result = client.create_full_listing(test_product, publish=False)
    print(f"\n🎯 Résultat: {json.dumps(result, indent=2)}")
