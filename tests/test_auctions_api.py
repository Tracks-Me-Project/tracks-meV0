from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tracks.api.boosters import get_clock
from tracks.clock import FakeClock
from tracks.db import get_session
from tracks.main import app
from tracks.models import CollectionItem, Track


@pytest.fixture
def clock():
    return FakeClock(datetime(2026, 1, 1, 10, tzinfo=UTC))


@pytest.fixture
def client(session, clock):
    def _session():
        yield session
        session.commit()

    session.add(Track(recording_mbid="r1", title="t", album_mbid="a", album="A", artist_mbid="x",
                      artist="X", album_year=None))
    session.commit()
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_clock] = lambda: clock
    yield TestClient(app)
    app.dependency_overrides.clear()


def _player(client, session, name, copies=0):
    r = client.post("/accounts", json={"name": name}).json()
    if copies:
        session.add(CollectionItem(account_id=r["id"], recording_mbid="r1", quantity=copies))
        session.commit()
    return {"Authorization": f"Bearer {r['token']}"}


def test_full_auction_flow(client, session, clock):
    seller, a, b = (_player(client, session, "s", 1), _player(client, session, "a"),
                    _player(client, session, "b"))
    created = client.post("/auctions", headers=seller,
                          json={"recording_mbid": "r1", "start_price": 100, "duration_minutes": 30})
    assert created.status_code == 201
    aid = created.json()["id"]
    assert [x["id"] for x in client.get("/auctions", headers=a).json()] == [aid]

    assert client.post(f"/auctions/{aid}/bids", headers=a, json={"amount": 100}).status_code == 201
    low = client.post(f"/auctions/{aid}/bids", headers=b, json={"amount": 101})
    assert low.status_code == 409 and low.json()["detail"]["minimum"] == 105
    won = client.post(f"/auctions/{aid}/bids", headers=b, json={"amount": 105})
    assert won.json()["current_price"] == 105 and won.json()["min_next_bid"] == 111

    clock.advance(timedelta(minutes=30))
    done = client.get(f"/auctions/{aid}", headers=a).json()  # règlement paresseux
    assert (done["status"], done["winner_id"], done["final_price"]) == ("sold", 3, 105)
    assert client.get("/me", headers=seller).json()["available"] == 1105
    assert client.get("/auctions", headers=a).json() == []
    assert [c["id"] for c in client.get("/collection", headers=b).json()] == ["r1"]


def test_error_codes(client, session):
    seller, a = _player(client, session, "s", 1), _player(client, session, "a")
    body = {"recording_mbid": "r1", "start_price": 100, "duration_minutes": 30}
    assert client.post("/auctions", headers=a, json=body).status_code == 409  # rien à vendre
    assert client.post("/auctions", headers=seller, json={**body, "duration_minutes": 7}
                       ).status_code == 422
    aid = client.post("/auctions", headers=seller, json=body).json()["id"]
    assert client.post(f"/auctions/{aid}/cancel", headers=a).status_code == 403
    assert client.post(f"/auctions/{aid}/bids", headers=seller, json={"amount": 100}
                       ).status_code == 409
    assert client.get("/auctions/999", headers=a).status_code == 404
    assert client.get("/auctions").status_code == 401
