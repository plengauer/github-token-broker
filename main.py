import os
import time

import jwt
import requests
from flask import Flask, jsonify, request
from jwt import PyJWKClient
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Cloud Run terminates TLS; trust X-Forwarded-* so request.host_url reflects the public https URL.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

GITHUB_ISSUER = "https://token.actions.githubusercontent.com"
GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
jwks_client = PyJWKClient(f"{GITHUB_ISSUER}/.well-known/jwks")

APP_ID = os.environ["GITHUB_APP_ID"]  # Numeric App ID or Client ID
PRIVATE_KEY = os.environ["GITHUB_APP_PRIVATE_KEY"]  # Mounted from Secret Manager
# Optional explicit audience; defaults to the Cloud Run URL the request arrived on.
BROKER_AUDIENCE = os.environ.get("BROKER_AUDIENCE")

def _audience():
    return (BROKER_AUDIENCE or request.host_url).rstrip("/")

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})

@app.post("/token")
def mint_token():
    # 1. Extract and verify GitHub's OIDC JWT
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing Bearer token"}), 401
    oidc_token = auth_header.split(" ", 1)[1]

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(oidc_token)
        claims = jwt.decode(
            oidc_token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=GITHUB_ISSUER,
            audience=_audience(),
        )
    except Exception as e:
        return jsonify({"error": f"Invalid OIDC token: {e}"}), 401

    # 2. Enforce owner and extract the single caller repository
    full_repo = claims.get("repository")  # e.g. "plengauer/thoth"

    repo_name = full_repo.split("/", 1)[1]

    # 3. Sign a short-lived JWT as the GitHub App
    now = int(time.time())
    app_jwt = jwt.encode(
        {"iat": now - 60, "exp": now + 540, "iss": APP_ID},
        PRIVATE_KEY,
        algorithm="RS256",
    )
    gh_headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
    }

    # 4. Look up the Installation ID for this specific repo
    inst_resp = requests.get(
        f"{GITHUB_API}/repos/{full_repo}/installation",
        headers=gh_headers,
        timeout=10,
    )
    if inst_resp.status_code != 200:
        return jsonify({"error": "App not installed on this repo"}), 403
    installation_id = inst_resp.json()["id"]

    # 5. Mint a 1-hour installation token scoped ONLY to this single repo
    token_resp = requests.post(
        f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
        headers=gh_headers,
        json={"repositories": [repo_name]},
        timeout=10,
    )
    if token_resp.status_code != 201:
        return jsonify({"error": "Failed to mint installation token"}), 502

    data = token_resp.json()
    return jsonify({"token": data["token"], "expires_at": data["expires_at"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
