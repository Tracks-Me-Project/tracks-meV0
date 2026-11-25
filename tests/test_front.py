from fastapi.testclient import TestClient

from tracks.main import app

client = TestClient(app)


def test_root_redirects_to_app():
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/app/"


def test_page_served():
    r = client.get("/app/")
    assert r.status_code == 200 and 'id="login-form"' in r.text
    assert 'id="open-booster"' in r.text
    assert client.get("/app/app.js").status_code == 200


def test_rules_endpoint():
    body = client.get("/rules").json()
    assert body["file"] == "rules.toml"
    assert body["rules"]["booster"]["max_stock"] == 10
