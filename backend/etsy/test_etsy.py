import os
import requests

from dotenv import load_dotenv
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_PATH / ".env")

ETSY_API_KEY = os.getenv("ETSY_API_KEY")

headers = {
    "x-api-key": ETSY_API_KEY
}

url = "https://openapi.etsy.com/v3/application/openapi-ping"

response = requests.get(
    url,
    headers=headers
)

print("\nSTATUS:\n")
print(response.status_code)

print("\nRESPONSE:\n")
print(response.text)