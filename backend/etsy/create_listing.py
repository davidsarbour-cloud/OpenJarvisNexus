import os
import requests

from dotenv import load_dotenv
from pathlib import Path

# =========================================================
# LOAD ENV
# =========================================================

ROOT_PATH = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_PATH / ".env")

ETSY_API_KEY = os.getenv("ETSY_API_KEY")
ETSY_ACCESS_TOKEN = os.getenv("ETSY_ACCESS_TOKEN")
ETSY_SHOP_ID = os.getenv("ETSY_SHOP_ID")

# =========================================================
# HEADERS
# =========================================================

headers = {
    "x-api-key": ETSY_API_KEY,
    "Authorization": f"Bearer {ETSY_ACCESS_TOKEN}"
}

# =========================================================
# URL
# =========================================================

url = f"https://openapi.etsy.com/v3/application/shops/{ETSY_SHOP_ID}/listings"

# =========================================================
# DATA
# =========================================================

data = {
    "quantity": 1,
    "title": "AI TEST LISTING",
    "description": "Created automatically with OpenJarvis Nexus",
    "price": 9.99,
    "who_made": "i_did",
    "when_made": "2020_2025",
    "taxonomy_id": 1,
    "type": "physical",
    "state": "draft"
}

# =========================================================
# REQUEST
# =========================================================

response = requests.post(
    url,
    headers=headers,
    json=data
)

# =========================================================
# OUTPUT
# =========================================================

print("\nSTATUS:\n")
print(response.status_code)

print("\nRESPONSE:\n")
print(response.text)