import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import accounts, auctions, ledger
from tracks.clock import FakeClock
from tracks.models import Account, Auction, CollectionItem, Track

T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def clock():
    return FakeClock(T0)


@pytest.fixture
def tracks(session):
    session.add_all(
        Track(recording_mbid=m, title=m, album_mbid="a", album="A", artist_mbid="x", artist="X",
              album_year=None)
        for m in ("r1", "r2")
    )
    session.commit()


def _player(session, clock, name, copies=0):
    acc, _ = accounts.create_account(session, name, clock)
    if copies:
        session.add(CollectionItem(account_id=acc.id, recording_mbid="r1", quantity=copies))
    session.commit()
    return acc


@pytest.fixture
def world(session, clock, tracks):
    seller = _player(session, clock, "seller", copies=2)
    a, b = _player(session, clock, "a"), _player(session, clock, "b")
    return seller, a, b


def _copies(session, acc, mbid="r1") -> int:
    item = session.scalar(
        select(CollectionItem.quantity).where(
            CollectionItem.account_id == acc.id, CollectionItem.recording_mbid == mbid
        )
    )
    return item or 0


def _total(session) -> int:
    return session.scalar(select(func.sum(Account.balance_available + Account.balance_locked)))


def _sell(session, clock, seller, price=100, minutes=60):
    a = auctions.create(session, seller.id, "r1", price, minutes, clock)
    session.commit()
    return a


def _balances(session, acc):
    session.refresh(acc)
    return acc.balance_available, acc.balance_locked


# --- création -------------------------------------------------------------------------------

def test_create_takes_copy_into_escrow(session, clock, world):
    seller, _, _ = world
    a = _sell(session, clock, seller)
    assert _copies(session, seller) == 1
    assert a.ends_at == T0 + timedelta(minutes=60) and a.status == "open"


def test_create_with_last_copy_removes_row(session, clock, tracks):
    seller = _player(session, clock, "s", copies=1)
    _sell(session, clock, seller)
    assert _copies(session, seller) == 0


def test_create_refusals(session, clock, world):
    seller, _, _ = world
    with pytest.raises(auctions.NotOwned):
        auctions.create(session, seller.id, "r2", 100, 60, clock)
    with pytest.raises(auctions.InvalidDuration):
        auctions.create(session, seller.id, "r1", 100, 45, clock)
    with pytest.raises(auctions.StartPriceTooLow) as e:
        auctions.create(session, seller.id, "r1", 9, 60, clock)
    assert e.value.minimum == 10


def test_max_five_open_auctions(session, clock, tracks):
    seller = _player(session, clock, "s", copies=10)
    made = [_sell(session, clock, seller) for _ in range(5)]
    with pytest.raises(auctions.TooManyOpen):
        auctions.create(session, seller.id, "r1", 100, 60, clock)
    session.rollback()
    auctions.cancel(session, made[0].id, seller.id, clock)  # libère une place
    session.commit()
    assert auctions.create(session, seller.id, "r1", 100, 60, clock)


def test_ended_auction_does_not_count_as_open(session, clock, tracks):
    seller = _player(session, clock, "s", copies=10)
    for _ in range(5):
        _sell(session, clock, seller, minutes=30)
    clock.advance(timedelta(minutes=31))
    assert auctions.create(session, seller.id, "r1", 100, 60, clock)


# --- mises ----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("top", "expected"), [(None, 100), (10, 11), (99, 104), (100, 105), (1000, 1050)]
)
def test_min_next_bid(top, expected):
    assert auctions.min_next_bid(100, top) == expected


def test_first_bid_at_start_price_locks_funds(session, clock, world):
    seller, a, _ = world
    auction = _sell(session, clock, seller)
    with pytest.raises(auctions.BidTooLow) as e:
        auctions.place_bid(session, auction.id, a.id, 99, clock)
    assert e.value.minimum == 100
    session.rollback()
    auctions.place_bid(session, auction.id, a.id, 100, clock)
    session.commit()
    assert _balances(session, a) == (900, 100)


def test_outbid_releases_previous_bidder(session, clock, world):
    seller, a, b = world
    auction = _sell(session, clock, seller)
    auctions.place_bid(session, auction.id, a.id, 100, clock)
    with pytest.raises(auctions.BidTooLow):
        auctions.place_bid(session, auction.id, b.id, 104, clock)
    session.rollback()
    auctions.place_bid(session, auction.id, b.id, 105, clock)
    session.commit()
    assert _balances(session, a) == (1000, 0)
    assert _balances(session, b) == (895, 105)


def test_bid_refusals(session, clock, world):
    seller, a, _ = world
    auction = _sell(session, clock, seller)
    with pytest.raises(auctions.OwnAuction):
        auctions.place_bid(session, auction.id, seller.id, 100, clock)
    with pytest.raises(ledger.InsufficientFunds):
        auctions.place_bid(session, auction.id, a.id, 5000, clock)
    session.rollback()
    auctions.place_bid(session, auction.id, a.id, 100, clock)
    with pytest.raises(auctions.AlreadyTopBidder):
        auctions.place_bid(session, auction.id, a.id, 200, clock)
    with pytest.raises(auctions.AuctionNotFound):
        auctions.place_bid(session, 999, a.id, 100, clock)


def test_no_bid_after_end(session, clock, world):
    seller, a, _ = world
    auction = _sell(session, clock, seller, minutes=30)
    clock.advance(timedelta(minutes=30))
    with pytest.raises(auctions.AuctionClosed):
        auctions.place_bid(session, auction.id, a.id, 100, clock)


# --- annulation -----------------------------------------------------------------------------

def test_cancel_returns_card(session, clock, world):
    seller, a, _ = world
    auction = _sell(session, clock, seller)
    clock.advance(timedelta(minutes=29))
    auctions.cancel(session, auction.id, seller.id, clock)
    session.commit()
    assert _copies(session, seller) == 2
    assert session.get(Auction, auction.id).status == "cancelled"
    with pytest.raises(auctions.AuctionClosed):
        auctions.place_bid(session, auction.id, a.id, 100, clock)


def test_cancel_refused_once_a_bid_exists(session, clock, world):
    seller, a, _ = world
    auction = _sell(session, clock, seller)
    auctions.place_bid(session, auction.id, a.id, 100, clock)
    session.commit()
    with pytest.raises(auctions.HasBids):
        auctions.cancel(session, auction.id, seller.id, clock)


def test_cancel_refused_after_half_or_by_other(session, clock, world):
    seller, a, _ = world
    auction = _sell(session, clock, seller)
    with pytest.raises(auctions.NotSeller):
        auctions.cancel(session, auction.id, a.id, clock)
    clock.advance(timedelta(minutes=30))  # exactement la moitié
    with pytest.raises(auctions.CancelWindowPassed):
        auctions.cancel(session, auction.id, seller.id, clock)


# --- règlement ------------------------------------------------------------------------------

def test_sold_moves_money_and_card_without_commission(session, clock, world):
    seller, a, b = world
    auction = _sell(session, clock, seller)
    auctions.place_bid(session, auction.id, a.id, 100, clock)
    auctions.place_bid(session, auction.id, b.id, 150, clock)
    session.commit()
    total = _total(session)
    assert auctions.settle_one(session, auction.id, clock) is False  # pas encore échue
    clock.advance(timedelta(minutes=60))
    assert auctions.settle_one(session, auction.id, clock) is True
    session.commit()
    assert _balances(session, seller) == (1150, 0)
    assert _balances(session, a) == (1000, 0)
    assert _balances(session, b) == (850, 0)
    assert _copies(session, b) == 1 and _copies(session, seller) == 1
    sold = session.get(Auction, auction.id)
    assert (sold.status, sold.winner_id, sold.final_price) == ("sold", b.id, 150)
    assert _total(session) == total
    assert auctions.settle_one(session, auction.id, clock) is False  # une seule fois


def test_unsold_returns_card(session, clock, world):
    seller, _, _ = world
    auction = _sell(session, clock, seller, minutes=30)
    clock.advance(timedelta(minutes=30))
    assert auctions.settle_due(session, clock) == 1
    assert session.get(Auction, auction.id).status == "unsold"
    assert _copies(session, seller) == 2


def test_settle_due_only_settles_due_ones(session, clock, world):
    seller, _, _ = world
    short = _sell(session, clock, seller, minutes=30)
    long = _sell(session, clock, seller, minutes=180)
    clock.advance(timedelta(minutes=60))
    assert auctions.settle_due(session, clock) == 1
    assert session.get(Auction, short.id).status == "unsold"
    assert session.get(Auction, long.id).status == "open"


# --- concurrence ----------------------------------------------------------------------------

def _run_parallel(jobs):
    barrier, results = threading.Barrier(len(jobs)), []

    def run(job):
        barrier.wait()
        try:
            job()
            results.append("ok")
        except Exception as exc:
            results.append(type(exc).__name__)

    ts = [threading.Thread(target=run, args=(j,)) for j in jobs]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return sorted(results)


def test_simultaneous_identical_bids_only_one_wins(engine, session, clock, world):
    seller, a, b = world
    auction = _sell(session, clock, seller)

    def bidder(acc):
        def job():
            with Session(engine) as s:
                auctions.place_bid(s, auction.id, acc.id, 100, clock)
                s.commit()
        return job

    assert _run_parallel([bidder(a), bidder(b)]) == ["BidTooLow", "ok"]


def test_crossed_outbids_do_not_deadlock(engine, session, clock, tracks):
    seller = _player(session, clock, "s", copies=2)
    x, y = _player(session, clock, "x"), _player(session, clock, "y")
    a1, a2 = _sell(session, clock, seller), _sell(session, clock, seller)
    auctions.place_bid(session, a1.id, y.id, 100, clock)
    auctions.place_bid(session, a2.id, x.id, 100, clock)
    session.commit()

    def outbid(acc, auction):
        def job():
            with Session(engine) as s:
                auctions.place_bid(s, auction.id, acc.id, 105, clock)
                s.commit()
        return job

    assert _run_parallel([outbid(x, a1), outbid(y, a2)]) == ["ok", "ok"]
    assert _balances(session, x) == (895, 105) and _balances(session, y) == (895, 105)


def test_same_player_bidding_on_two_auctions_cannot_overspend(engine, session, clock, tracks):
    seller = _player(session, clock, "s", copies=2)
    x = _player(session, clock, "x")
    a1, a2 = _sell(session, clock, seller), _sell(session, clock, seller)

    def bid(auction):
        def job():
            with Session(engine) as s:
                accounts_loaded_first = s.get(Account, x.id)  # comme l'authentification
                assert accounts_loaded_first
                auctions.place_bid(s, auction.id, x.id, 600, clock)
                s.commit()
        return job

    assert _run_parallel([bid(a1), bid(a2)]) == ["InsufficientFunds", "ok"]
    assert _balances(session, x) == (400, 600)


def test_cancel_deadline_is_half_the_duration(session, clock, world):
    seller, *_ = world
    auction = _sell(session, clock, seller)  # 60 min
    assert auctions.cancel_deadline(auction) == T0 + timedelta(minutes=30)


def test_bets_close_at_half_the_duration(session, clock, world):
    seller, *_ = world
    auction = _sell(session, clock, seller)  # 60 min
    assert auctions.bets_close_at(auction) == T0 + timedelta(minutes=30)
