import pytest
from fastapi.testclient import TestClient

from tracks.db import get_session
from tracks.main import app


@pytest.fixture
def client(session):
    def _session():
        yield session
        session.commit()

    app.dependency_overrides[get_session] = _session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_then_me(client):
    r = client.post("/accounts", json={"name": "alice"})
    assert r.status_code == 201
    me = client.get("/me", headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert me.json() == {"id": r.json()["id"], "name": "alice", "available": 1000, "locked": 0}


def test_duplicate_name_refused(client):
    client.post("/accounts", json={"name": "alice"})
    assert client.post("/accounts", json={"name": "alice"}).status_code == 409


def test_bad_or_missing_token_refused(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_token_not_stored_in_clear(client, session):
    from sqlalchemy import select

    from tracks.models import Account

    token = client.post("/accounts", json={"name": "bob"}).json()["token"]
    assert session.scalar(select(Account.token_hash)) != token
