import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from tracks import accounts, recycling
from tracks.clock import FakeClock
from tracks.models import Account, CollectionItem, Track

T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def clock():
    return FakeClock(T0)


@pytest.fixture
def acc(session, clock):
    session.add_all(
        Track(recording_mbid=m, title=m, album_mbid="a", album="A", artist_mbid="x", artist="X",
              album_year=None)
        for m in ("r1", "r2")
    )
    account, _ = accounts.create_account(session, "a", clock)
    session.flush()
    session.add_all(
        [CollectionItem(account_id=account.id, recording_mbid="r1", quantity=80),
         CollectionItem(account_id=account.id, recording_mbid="r2", quantity=3)]
    )
    session.commit()
    return account


def test_recycle_pays_one_per_duplicate(session, acc, clock):
    res = recycling.recycle(session, acc.id, "r2", 2, clock)
    assert (res.count, res.coins, res.remaining_cap) == (2, 2, 48)
    assert acc.balance_available == 1002
    assert session.get(CollectionItem, (acc.id, "r2")).quantity == 1


def test_last_copy_cannot_be_recycled(session, acc, clock):
    with pytest.raises(recycling.NotEnoughDuplicates) as e:
        recycling.recycle(session, acc.id, "r2", 3, clock)
    assert e.value.available == 2


def test_unowned_title_refused(session, acc, clock):
    with pytest.raises(recycling.NotEnoughDuplicates):
        recycling.recycle(session, acc.id, "nope", 1, clock)


def test_quantity_must_be_positive(session, acc, clock):
    with pytest.raises(ValueError):
        recycling.recycle(session, acc.id, "r1", 0, clock)


def test_daily_cap_refuses_whole_request(session, acc, clock):
    recycling.recycle(session, acc.id, "r1", 49, clock)
    with pytest.raises(recycling.DailyCapExceeded) as e:
        recycling.recycle(session, acc.id, "r1", 2, clock)
    assert e.value.remaining == 1
    assert session.get(CollectionItem, (acc.id, "r1")).quantity == 31  # rien n'a bougé
    assert recycling.recycle(session, acc.id, "r1", 1, clock).remaining_cap == 0


def test_cap_resets_at_utc_midnight(session, acc, clock):
    recycling.recycle(session, acc.id, "r1", 50, clock)
    clock.advance(timedelta(hours=13, minutes=59))  # 23 h 59 UTC : même jour
    with pytest.raises(recycling.DailyCapExceeded):
        recycling.recycle(session, acc.id, "r1", 1, clock)
    clock.advance(timedelta(minutes=1))  # minuit
    assert recycling.recycle(session, acc.id, "r1", 1, clock).remaining_cap == 49


def test_concurrent_recycles_respect_cap(engine, session, acc, clock):
    barrier, results = threading.Barrier(2), []

    def worker() -> None:
        with Session(engine) as s:
            barrier.wait()
            try:
                recycling.recycle(s, acc.id, "r1", 30, clock)
                s.commit()
                results.append("ok")
            except recycling.DailyCapExceeded:
                results.append("refused")

    ts = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["ok", "refused"]
    session.expire_all()
    assert session.get(Account, acc.id).balance_available == 1030
