import os
import webbrowser
import hashlib
import base64
import requests

from flask import Flask, request
from dotenv import load_dotenv
from pathlib import Path

# =========================================================
# LOAD ENV
# =========================================================

ROOT_PATH = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_PATH / ".env")

ETSY_API_KEY = os.getenv("ETSY_API_KEY")

REDIRECT_URI = os.getenv(
    "ETSY_OAUTH_REDIRECT_URI"
)

# =========================================================
# VALIDATION
# =========================================================

if not ETSY_API_KEY:

    raise Exception(
        "Missing ETSY_API_KEY in .env"
    )

if not REDIRECT_URI:

    raise Exception(
        "Missing ETSY_OAUTH_REDIRECT_URI in .env"
    )

# =========================================================
# PKCE
# =========================================================

CODE_VERIFIER = (
    "openjarvisnexuspkce123456789"
)

sha256 = hashlib.sha256(
    CODE_VERIFIER.encode("utf-8")
).digest()

CODE_CHALLENGE = (
    base64.urlsafe_b64encode(sha256)
    .decode("utf-8")
    .replace("=", "")
)

# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return "HOME OK"

# =========================================================
# ETSY CALLBACK
# =========================================================

@app.route("/etsy/callback")
def etsy_callback():

    code = request.args.get("code")

    error = request.args.get("error")

    print("\n================================")
    print("ETSY CALLBACK HIT")
    print("CODE:", code)
    print("ERROR:", error)
    print("================================\n")

    # =====================================================
    # TOKEN EXCHANGE
    # =====================================================

    token_url = (
        "https://api.etsy.com/v3/public/oauth/token"
    )

    payload = {
        "grant_type": "authorization_code",
        "client_id": ETSY_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": code,
        "code_verifier": CODE_VERIFIER
    }

    response = requests.post(
        token_url,
        json=payload
    )

    tokens = response.json()

    print("\n================================")
    print("TOKENS")
    print("================================\n")

    print(tokens)

    access_token = tokens.get(
        "access_token"
    )

    refresh_token = tokens.get(
        "refresh_token"
    )

    return f"""

    <h1>ETSY TOKENS SUCCESS</h1>

    <h2>ACCESS TOKEN</h2>

    <textarea rows="10" cols="120">
    {access_token}
    </textarea>

    <br><br>

    <h2>REFRESH TOKEN</h2>

    <textarea rows="10" cols="120">
    {refresh_token}
    </textarea>

    """

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    auth_url = (
        "https://www.etsy.com/oauth/connect"
        f"?response_type=code"
        f"&client_id={ETSY_API_KEY}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=listings_r%20listings_w%20shops_r%20shops_w%20transactions_r"
        f"&state=openjarvisnexus"
        f"&code_challenge={CODE_CHALLENGE}"
        f"&code_challenge_method=S256"
    )

    print("\n================================")
    print("OPENING ETSY OAUTH")
    print("================================\n")

    print(auth_url)

    webbrowser.open(auth_url)

    app.run(
        host=os.getenv("BIND_HOST", "0.0.0.0"),
        port=4000,
        debug=False
    )