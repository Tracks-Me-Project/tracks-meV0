import random
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import accounts, boosters
from tracks.clock import FakeClock
from tracks.models import CollectionItem, Track

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def clock():
    return FakeClock(T0)


@pytest.fixture
def acc(session, clock):
    session.add_all(
        Track(recording_mbid=f"r{i}", title=f"t{i}", album_mbid="a", album="A", artist_mbid="x",
              artist="X", album_year=None)
        for i in range(20)
    )
    account, _ = accounts.create_account(session, "a", clock)
    session.commit()
    return account


def _stock(session, acc, clock) -> int:
    return boosters.refill(session, acc.id, clock.now()).stock


def _total_cards(session, acc) -> int:
    return session.scalar(
        select(func.coalesce(func.sum(CollectionItem.quantity), 0)).where(
            CollectionItem.account_id == acc.id
        )
    )


def test_new_account_has_full_stock(session, acc, clock):
    assert _stock(session, acc, clock) == 10


def test_open_removes_one_and_adds_five_cards(session, acc, clock):
    drawn = boosters.open_booster(session, acc.id, clock, random.Random(1))
    assert len(drawn) <= 5  # moins de 5 objets si un titre sort deux fois
    assert _stock(session, acc, clock) == 9
    assert _total_cards(session, acc) == 5


def test_stock_regenerates_one_per_hour_and_caps(session, acc, clock):
    for _ in range(10):
        boosters.open_booster(session, acc.id, clock, random.Random(1))
    assert _stock(session, acc, clock) == 0
    clock.advance(timedelta(minutes=59))
    assert _stock(session, acc, clock) == 0
    clock.advance(timedelta(minutes=1))
    assert _stock(session, acc, clock) == 1
    clock.advance(timedelta(hours=100))
    assert _stock(session, acc, clock) == 10


def test_partial_hour_is_kept(session, acc, clock):
    for _ in range(10):
        boosters.open_booster(session, acc.id, clock, random.Random(1))
    clock.advance(timedelta(minutes=90))
    state = boosters.refill(session, acc.id, clock.now())
    assert state.stock == 1
    assert boosters.seconds_until_next(state, clock.now()) == 30 * 60


def test_open_refused_without_stock(session, acc, clock):
    for _ in range(10):
        boosters.open_booster(session, acc.id, clock, random.Random(1))
    with pytest.raises(boosters.NoBoosterAvailable):
        boosters.open_booster(session, acc.id, clock, random.Random(1))


def test_empty_catalogue(session, clock):
    account, _ = accounts.create_account(session, "b", clock)
    with pytest.raises(boosters.EmptyCatalogue):
        boosters.open_booster(session, account.id, clock, random.Random(1))


def test_full_stock_timer_starts_at_first_open(session, acc, clock):
    clock.advance(timedelta(hours=5))
    boosters.open_booster(session, acc.id, clock, random.Random(1))
    clock.advance(timedelta(minutes=30))
    state = boosters.refill(session, acc.id, clock.now())
    assert (state.stock, boosters.seconds_until_next(state, clock.now())) == (9, 30 * 60)


def test_concurrent_opens_use_one_booster_once(engine, session, acc, clock):
    import threading

    for _ in range(9):
        boosters.open_booster(session, acc.id, clock, random.Random(1))
    session.commit()  # il reste exactement 1 booster
    barrier, results = threading.Barrier(2), []

    def worker() -> None:
        with Session(engine) as s:
            barrier.wait()
            try:
                boosters.open_booster(s, acc.id, clock, random.Random(2))
                s.commit()
                results.append("ok")
            except boosters.NoBoosterAvailable:
                results.append("refused")

    ts = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["ok", "refused"]
