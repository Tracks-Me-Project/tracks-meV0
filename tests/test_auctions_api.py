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


def test_bets_api_flow(client, session, clock):
    seller = _player(client, session, "s", 1)
    p1, p2, w = (_player(client, session, n) for n in ("p1", "p2", "w"))
    aid = client.post("/auctions", headers=seller, json={
        "recording_mbid": "r1", "start_price": 100, "duration_minutes": 60}).json()
    assert aid["bet_stake"] == 10
    aid = aid["id"]

    def bet(headers, guess):
        return client.post(f"/auctions/{aid}/bets", headers=headers, json={"prediction": guess})

    assert bet(p1, 150).json() == {"auction_id": aid, "prediction": 150, "stake": 10}
    assert bet(p1, 160).status_code == 409                                    # un seul pari
    assert bet(seller, 150).status_code == 409                                # propre enchère
    low = bet(p2, 50)
    assert low.status_code == 409 and low.json()["detail"]["minimum"] == 100
    assert bet(p2, 300).status_code == 201
    assert client.post(f"/auctions/{aid}/bids", headers=p1, json={"amount": 120}).status_code == 409
    assert client.post(f"/auctions/{aid}/bids", headers=w, json={"amount": 200}).status_code == 201

    mine = client.get("/bets", headers=p1).json()
    # seulement mon pari, pas ceux des autres
    assert [(b["prediction"], b["payout"]) for b in mine] == [(150, None)]
    clock.advance(timedelta(minutes=60))
    client.get(f"/auctions/{aid}", headers=w)  # règlement paresseux
    # écarts : p1 = 50, p2 = 100 -> 70 / 30 de la cagnotte (20) : 14 et 6
    assert client.get("/bets", headers=p1).json()[0]["payout"] == 14
    assert client.get("/bets", headers=p2).json()[0]["payout"] == 6
    assert client.get("/bets").status_code == 401


def test_view_names_and_time_left(client, session, clock):
    seller, a = _player(client, session, "vendeur", 1), _player(client, session, "acheteur")
    body = {"recording_mbid": "r1", "start_price": 100, "duration_minutes": 30}
    view = client.post("/auctions", headers=seller, json=body).json()
    assert (view["seller_name"], view["leader_id"], view["leader_name"]) == ("vendeur", None, None)
    assert (view["album"], view["seconds_left"], view["winner_name"]) == ("A", 1800, None)

    aid = view["id"]
    view = client.post(f"/auctions/{aid}/bids", headers=a, json={"amount": 100}).json()
    assert (view["leader_id"], view["leader_name"]) == (2, "acheteur")

    clock.advance(timedelta(minutes=29, seconds=59.5))  # arrondi au-dessus : pas 0 avant la fin
    assert client.get(f"/auctions/{aid}", headers=a).json()["seconds_left"] == 1

    clock.advance(timedelta(seconds=1))
    done = client.get(f"/auctions/{aid}", headers=a).json()
    assert (done["status"], done["seconds_left"], done["winner_name"]) == ("sold", 0, "acheteur")
