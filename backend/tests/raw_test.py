"""
Bypasses the Anthropic SDK entirely.
Talks directly to the API with raw HTTP.

Manual probe — invoked as `python backend/tests/raw_test.py`. The
`if __name__ == "__main__"` guard keeps pytest from running the live
API calls during collection.
"""
import os

import requests
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(override=True)
    key = os.getenv("ANTHROPIC_API_KEY", "")

    print(f"Key prefix : {key[:30]}...")
    print(f"Key length : {len(key)}")
    print()

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Test 1: Can we reach the API at all?
    print("=== Test 1: GET /v1/models ===")
    r = requests.get("https://api.anthropic.com/v1/models", headers=headers)
    print(f"Status : {r.status_code}")
    print(f"Body   : {r.text[:500]}")
    print()

    print("=== All available models ===")
    r = requests.get("https://api.anthropic.com/v1/models", headers=headers)
    data = r.json()
    for m in data.get("data", []):
        print(f"  {m['id']:45} → {m['display_name']}")


if __name__ == "__main__":
    main()
