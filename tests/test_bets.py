import random
import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import accounts, auctions, bets, ledger
from tracks.bets import compute_payouts
from tracks.clock import FakeClock
from tracks.models import Account, Bet, CollectionItem, Track

T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


# --- calcul des gains (fonctions pures) -------------------------------------------------------

def test_payouts_example_from_bilan_paris():
    # mise 20, prix final 580, paris 600/550/620/450/800/350 (section 3 de bilan_paris.md)
    distances = [abs(p - 580) for p in (600, 550, 620, 450, 800, 350)]
    assert compute_payouts(20, distances) == [48, 28, 19, 8, 8, 8]


@pytest.mark.parametrize(
    ("distances", "expected"),
    [
        ([7], [10]),                                  # parieur seul : remboursé
        ([5, 1], [6, 14]),                            # 70 / 30 de 20
        ([5, 1, 9], [9, 15, 6]),                      # tout le pot (30) en 50 / 30 / 20
        ([1, 2, 3, 4], [16, 10, 6, 6]),               # 4e = 3e (podium 83,3 %)
        ([1, 2, 3, 4, 5], [20, 12, 8, 5, 5]),         # 80 % au podium, 20 % aux deux autres
        ([5, 5, 20, 30], [13, 13, 6, 6]),             # égalité pour la 1re place : moyenne 16,7/10
        ([4, 4, 4, 4], [10, 10, 10, 10]),             # tous à égalité : chacun récupère sa mise
    ],
)
def test_payouts_cases(distances, expected):
    assert compute_payouts(10, distances) == expected


def test_payout_capped_at_four_times_stake():
    assert compute_payouts(10, list(range(15)))[0] == 40  # 6 x la mise sans plafond


def test_payouts_properties():
    rng = random.Random(0)
    for _ in range(300):
        n = rng.randint(1, 20)
        distances = [rng.randint(0, 50) for _ in range(n)]
        payouts = compute_payouts(10, distances)
        assert sum(payouts) <= 10 * n  # on ne crée jamais de monnaie
        assert max(payouts) <= 40
        for i in range(n):
            for j in range(n):
                if n > 1 and distances[i] < distances[j]:
                    assert payouts[i] >= payouts[j]  # plus proche => au moins autant


@pytest.mark.parametrize(("start", "stake"), [(200, 20), (15, 2), (11, 2), (10, 1), (1, 1)])
def test_stake_is_ceil_of_ten_percent(start, stake):
    assert bets.stake_for(start) == stake


# --- règles de pari et règlement --------------------------------------------------------------

@pytest.fixture
def clock():
    return FakeClock(T0)


@pytest.fixture
def tracks(session):
    session.add(
        Track(recording_mbid="r1", title="r1", album_mbid="a", album="A", artist_mbid="x",
              artist="X", album_year=None)
    )
    session.commit()


def _player(session, clock, name, copies=0):
    acc, _ = accounts.create_account(session, name, clock)
    if copies:
        session.add(CollectionItem(account_id=acc.id, recording_mbid="r1", quantity=copies))
    session.commit()
    return acc


def _sell(session, clock, seller, price=200, minutes=60):
    a = auctions.create(session, seller.id, "r1", price, minutes, clock)
    session.commit()
    return a


def _balances(session, acc):
    session.refresh(acc)
    return acc.balance_available, acc.balance_locked


def _total(session) -> int:
    return session.scalar(select(func.sum(Account.balance_available + Account.balance_locked)))


@pytest.fixture
def market(session, clock, tracks):
    seller = _player(session, clock, "seller", copies=6)
    return seller, _sell(session, clock, seller)


def test_place_bet_locks_fixed_stake(session, clock, market):
    _, auction = market
    p = _player(session, clock, "p")
    bet = auctions.place_bet(session, auction.id, p.id, 250, clock)
    session.commit()
    assert (bet.stake, _balances(session, p)) == (20, (980, 20))


def test_bet_refusals(session, clock, market):
    seller, auction = market
    p, w = _player(session, clock, "p"), _player(session, clock, "w")
    with pytest.raises(auctions.BetOnOwnAuction):
        auctions.place_bet(session, auction.id, seller.id, 250, clock)
    with pytest.raises(auctions.PredictionTooLow) as e:
        auctions.place_bet(session, auction.id, p.id, 199, clock)
    assert e.value.minimum == 200
    auctions.place_bid(session, auction.id, w.id, 300, clock)
    with pytest.raises(auctions.PredictionTooLow) as e:  # le prix courant a monté
        auctions.place_bet(session, auction.id, p.id, 250, clock)
    assert e.value.minimum == 300
    with pytest.raises(auctions.BidderCannotBet):
        auctions.place_bet(session, auction.id, w.id, 400, clock)
    session.commit()
    auctions.place_bet(session, auction.id, p.id, 300, clock)
    with pytest.raises(auctions.AlreadyBet):
        auctions.place_bet(session, auction.id, p.id, 310, clock)
    with pytest.raises(auctions.AuctionNotFound):
        auctions.place_bet(session, 999, p.id, 300, clock)


def test_bettor_cannot_bid(session, clock, market):
    _, auction = market
    p = _player(session, clock, "p")
    auctions.place_bet(session, auction.id, p.id, 250, clock)
    with pytest.raises(auctions.BettorCannotBid):
        auctions.place_bid(session, auction.id, p.id, 300, clock)


def test_insufficient_funds(session, clock, market):
    _, auction = market
    p = _player(session, clock, "p")
    ledger.lock(session, p.id, 990)
    with pytest.raises(ledger.InsufficientFunds):
        auctions.place_bet(session, auction.id, p.id, 250, clock)


def test_bets_close_at_half_duration(session, clock, market):
    _, auction = market
    p = _player(session, clock, "p")
    clock.advance(timedelta(minutes=29, seconds=59))
    assert auctions.place_bet(session, auction.id, p.id, 250, clock)
    q = _player(session, clock, "q")
    clock.advance(timedelta(seconds=1))
    with pytest.raises(auctions.BetsClosed):
        auctions.place_bet(session, auction.id, q.id, 250, clock)


def test_three_open_bets_at_most(session, clock, market):
    seller, first = market
    p = _player(session, clock, "p")
    others = [_sell(session, clock, seller) for _ in range(3)]
    for a in (first, *others[:2]):
        auctions.place_bet(session, a.id, p.id, 250, clock)
    with pytest.raises(auctions.TooManyOpenBets):
        auctions.place_bet(session, others[2].id, p.id, 250, clock)
    session.commit()
    clock.advance(timedelta(minutes=61))  # les trois premières sont terminées : place libérée
    fresh = _sell(session, clock, seller)
    assert auctions.place_bet(session, fresh.id, p.id, 250, clock)


def test_settlement_follows_bilan_example_and_destroys_the_rest(session, clock, market):
    _, auction = market
    gamblers = [_player(session, clock, f"g{i}") for i in range(6)]
    winner = _player(session, clock, "w")
    for g, guess in zip(gamblers, (600, 550, 620, 450, 800, 350), strict=True):
        auctions.place_bet(session, auction.id, g.id, guess, clock)
    session.commit()
    # on mise ensuite 580 : les paris sont déjà posés avec le prix de départ comme minimum
    auctions.place_bid(session, auction.id, winner.id, 580, clock)
    session.commit()
    before = _total(session)
    clock.advance(timedelta(minutes=60))
    assert auctions.settle_due(session, clock) == 1
    assert [_balances(session, g)[0] - 1000 for g in gamblers] == [28, 8, -1, -12, -12, -12]
    assert all(_balances(session, g)[1] == 0 for g in gamblers)
    assert _total(session) == before - 1  # 120 de cagnotte, 119 distribués
    pays = session.scalars(select(Bet.payout).order_by(Bet.account_id)).all()
    assert pays == [48, 28, 19, 8, 8, 8]


@pytest.mark.parametrize("ending", ["unsold", "cancelled"])
def test_bets_refunded_when_unsold_or_cancelled(session, clock, market, ending):
    seller, auction = market
    ps = [_player(session, clock, f"p{i}") for i in range(3)]
    for p in ps:
        auctions.place_bet(session, auction.id, p.id, 250, clock)
    session.commit()
    before = _total(session)
    if ending == "cancelled":
        auctions.cancel(session, auction.id, seller.id, clock)
    else:
        clock.advance(timedelta(minutes=60))
        auctions.settle_due(session, clock)
    session.commit()
    assert [_balances(session, p) for p in ps] == [(1000, 0)] * 3
    assert _total(session) == before
    assert session.scalars(select(Bet.payout)).all() == [20, 20, 20]


def test_lone_bettor_refunded_on_sale(session, clock, market):
    _, auction = market
    p, w = _player(session, clock, "p"), _player(session, clock, "w")
    auctions.place_bet(session, auction.id, p.id, 250, clock)
    auctions.place_bid(session, auction.id, w.id, 250, clock)
    session.commit()
    clock.advance(timedelta(minutes=60))
    auctions.settle_due(session, clock)
    assert _balances(session, p) == (1000, 0)


# --- concurrence ------------------------------------------------------------------------------

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


def test_same_player_cannot_bet_and_bid_simultaneously(engine, session, clock, market):
    _, auction = market
    p = _player(session, clock, "p")

    def bet():
        with Session(engine) as s:
            auctions.place_bet(s, auction.id, p.id, 250, clock)
            s.commit()

    def bid():
        with Session(engine) as s:
            auctions.place_bid(s, auction.id, p.id, 250, clock)
            s.commit()

    assert _run_parallel([bet, bid]) in (["BettorCannotBid", "ok"], ["BidderCannotBet", "ok"])


def test_parallel_bets_respect_open_limit(engine, session, clock, tracks):
    seller = _player(session, clock, "s", copies=6)
    auctions_ = [_sell(session, clock, seller) for _ in range(5)]
    p = _player(session, clock, "p")

    def bet(a):
        def job():
            with Session(engine) as s:
                s.get(Account, p.id)  # compte chargé avant le verrou, comme l'authentification
                auctions.place_bet(s, a.id, p.id, 250, clock)
                s.commit()
        return job

    assert _run_parallel([bet(a) for a in auctions_]) == ["TooManyOpenBets"] * 2 + ["ok"] * 3
    assert _balances(session, p) == (940, 60)

