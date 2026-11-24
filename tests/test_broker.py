import os
os.environ.setdefault("GITHUB_APP_ID", "1")
os.environ.setdefault("GITHUB_APP_PRIVATE_KEY", "x")
os.environ.setdefault("ALLOWED_GITHUB_OWNER", "plengauer")

from main import app


def test_health():
    assert app.test_client().get("/healthz").status_code == 200


def test_missing_bearer():
    assert app.test_client().post("/token").status_code == 401


def test_invalid_bearer():
    r = app.test_client().post("/token", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401
