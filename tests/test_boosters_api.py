import pytest
from fastapi.testclient import TestClient

from tracks.db import get_session
from tracks.main import app
from tracks.models import Track


@pytest.fixture
def client(session):
    def _session():
        yield session
        session.commit()

    session.add_all(
        Track(recording_mbid=f"r{i}", title=f"t{i}", album_mbid="a", album="A", artist_mbid="x",
              artist="X", album_year=2000)
        for i in range(20)
    )
    session.commit()
    app.dependency_overrides[get_session] = _session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    token = client.post("/accounts", json={"name": "alice"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_stock_open_collection(client, auth):
    assert client.get("/boosters", headers=auth).json() == {
        "stock": 10, "max_stock": 10, "seconds_until_next": None}
    opened = client.post("/boosters/open", headers=auth).json()["tracks"]
    assert len(opened) == 5
    assert client.get("/boosters", headers=auth).json()["stock"] == 9
    coll = client.get("/collection", headers=auth).json()
    assert sum(c["quantity"] for c in coll) == 5


def test_open_without_stock_is_409(client, auth):
    for _ in range(10):
        assert client.post("/boosters/open", headers=auth).status_code == 200
    assert client.post("/boosters/open", headers=auth).status_code == 409


def test_requires_token(client):
    assert client.get("/collection").status_code == 401


def test_recycle_api(client, auth, session):
    from tracks.models import CollectionItem

    session.add(CollectionItem(account_id=1, recording_mbid="r1", quantity=4))
    session.commit()

    def recycle(quantity: int):
        body = {"recording_mbid": "r1", "quantity": quantity}
        return client.post("/collection/recycle", headers=auth, json=body)

    assert recycle(3).json() == {"recycled": 3, "coins": 3, "remaining_cap_today": 47}
    refused = recycle(1)
    assert refused.status_code == 409 and refused.json()["detail"]["available"] == 0
    assert recycle(0).status_code == 422


def test_collection_search_param(client, auth):
    client.post("/boosters/open", headers=auth)
    assert client.get("/collection", params={"q": "introuvable"}, headers=auth).json() == []
    assert client.get("/collection", params={"q": "T"}, headers=auth).json()
    for bad in ("a\x00", "x" * 101):
        assert client.get("/collection", params={"q": bad}, headers=auth).status_code == 422
