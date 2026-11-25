"""Enchères. Aucune fonction ne commit (sauf settle_due, qui règle une enchère par transaction)."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import bets, collection, ledger
from tracks.clock import Clock
from tracks.config import get_rules
from tracks.models import Auction, Bet, Bid


class AuctionError(Exception):
    pass


class NotOwned(AuctionError):
    pass


class InvalidDuration(AuctionError):
    pass


class StartPriceTooLow(AuctionError):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum


class TooManyOpen(AuctionError):
    pass


class AuctionNotFound(AuctionError):
    pass


class AuctionClosed(AuctionError):
    pass


class OwnAuction(AuctionError):
    pass


class AlreadyTopBidder(AuctionError):
    pass


class BidTooLow(AuctionError):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum


class HasBids(AuctionError):
    pass


class BetsClosed(AuctionError):
    pass


class BetOnOwnAuction(AuctionError):
    pass


class BidderCannotBet(AuctionError):
    pass


class BettorCannotBid(AuctionError):
    pass


class AlreadyBet(AuctionError):
    pass


class PredictionTooLow(AuctionError):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum


class TooManyOpenBets(AuctionError):
    pass


class NotSeller(AuctionError):
    pass


class CancelWindowPassed(AuctionError):
    pass


def min_next_bid(start_price: int, top_amount: int | None) -> int:
    """Première mise : le prix de départ. Ensuite : +5 % arrondi à l'entier supérieur."""
    if top_amount is None:
        return start_price
    pct = get_rules().auction.min_raise_percent
    return top_amount + (top_amount * pct + 99) // 100


def top_bid(session: Session, auction_id: int) -> Bid | None:
    return session.scalar(
        select(Bid).where(Bid.auction_id == auction_id).order_by(Bid.amount.desc()).limit(1)
    )


def _lock_auction(session: Session, auction_id: int) -> Auction:
    auction = session.scalar(
        select(Auction)
        .where(Auction.id == auction_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if auction is None:
        raise AuctionNotFound
    return auction


def create(
    session: Session,
    seller_id: int,
    recording_mbid: str,
    start_price: int,
    duration_minutes: int,
    clock: Clock,
) -> Auction:
    """Met en vente un exemplaire : il sort de la collection (séquestre) jusqu'à la fin."""
    rules = get_rules().auction
    if duration_minutes not in rules.durations_minutes:
        raise InvalidDuration
    if start_price < rules.min_start_price:
        raise StartPriceTooLow(rules.min_start_price)
    now = clock.now()
    ledger.lock_accounts(session, seller_id)  # sérialise les créations du même vendeur
    open_count = session.scalar(
        select(func.count())
        .select_from(Auction)
        .where(Auction.seller_id == seller_id, Auction.status == "open", Auction.ends_at > now)
    )
    if open_count >= rules.max_open_per_account:
        raise TooManyOpen
    if not collection.take_copy(session, seller_id, recording_mbid):
        raise NotOwned
    auction = Auction(
        seller_id=seller_id,
        recording_mbid=recording_mbid,
        start_price=start_price,
        starts_at=now,
        ends_at=now + timedelta(minutes=duration_minutes),
        status="open",
    )
    session.add(auction)
    session.flush()
    return auction


def place_bid(
    session: Session, auction_id: int, bidder_id: int, amount: int, clock: Clock
) -> Bid:
    now = clock.now()
    auction = _lock_auction(session, auction_id)
    if auction.status != "open" or now >= auction.ends_at:
        raise AuctionClosed
    if bidder_id == auction.seller_id:
        raise OwnAuction
    if session.get(Bet, (auction_id, bidder_id)):
        raise BettorCannotBid
    top = top_bid(session, auction_id)
    if top and top.bidder_id == bidder_id:
        raise AlreadyTopBidder
    minimum = min_next_bid(auction.start_price, top.amount if top else None)
    if amount < minimum:
        raise BidTooLow(minimum)

    ref = f"auction:{auction_id}"
    ledger.lock_accounts(session, bidder_id, *([top.bidder_id] if top else []))
    ledger.lock(session, bidder_id, amount, ref)  # InsufficientFunds si le solde ne suffit pas
    if top:
        ledger.unlock(session, top.bidder_id, top.amount, ref)
    bid = Bid(auction_id=auction_id, bidder_id=bidder_id, amount=amount, created_at=now)
    session.add(bid)
    session.flush()
    return bid


def cancel_deadline(auction: Auction) -> datetime:
    """Instant à partir duquel le vendeur ne peut plus annuler."""
    window = (auction.ends_at - auction.starts_at) * get_rules().auction.cancel_window_percent
    return auction.starts_at + window // 100


def cancel(session: Session, auction_id: int, seller_id: int, clock: Clock) -> None:
    """Le vendeur annule pendant la première moitié de la durée, tant qu'il n'y a pas de mise.
    Les mises des paris sont rendues."""
    auction = _lock_auction(session, auction_id)
    if auction.seller_id != seller_id:
        raise NotSeller
    if auction.status != "open":
        raise AuctionClosed
    if clock.now() >= cancel_deadline(auction):
        raise CancelWindowPassed
    if top_bid(session, auction_id):
        raise HasBids
    ledger.lock_accounts(session, *bets.bettor_ids(session, auction_id))
    bets.refund_bets(session, auction_id)
    collection.add_copies(session, seller_id, auction.recording_mbid, 1)
    auction.status = "cancelled"


def settle_one(session: Session, auction_id: int, clock: Clock) -> bool:
    """Règle l'enchère (et ses paris) si elle est ouverte et échue. True si elle vient d'être
    réglée."""
    auction = _lock_auction(session, auction_id)
    if auction.status != "open" or clock.now() < auction.ends_at:
        return False
    top = top_bid(session, auction_id)
    bettors = bets.bettor_ids(session, auction_id)
    if top is None:
        ledger.lock_accounts(session, *bettors)
        bets.refund_bets(session, auction_id)
        collection.add_copies(session, auction.seller_id, auction.recording_mbid, 1)
        auction.status = "unsold"
        return True
    ref = f"auction:{auction_id}"
    # Tous les comptes d'un coup, dans l'ordre : pas de blocage entre deux règlements.
    ledger.lock_accounts(session, auction.seller_id, top.bidder_id, *bettors)
    ledger.spend_locked(session, top.bidder_id, top.amount, ref)
    ledger.credit(session, auction.seller_id, top.amount, "sale", ref)  # aucune commission
    collection.add_copies(session, top.bidder_id, auction.recording_mbid, 1)
    bets.settle_bets(session, auction_id, top.amount)
    auction.status = "sold"
    auction.winner_id = top.bidder_id
    auction.final_price = top.amount
    return True


def settle_due(session: Session, clock: Clock) -> int:
    """Règle toutes les enchères échues, une transaction par enchère (peu de verrous à la fois)."""
    due = session.scalars(
        select(Auction.id)
        .where(Auction.status == "open", Auction.ends_at <= clock.now())
        .order_by(Auction.ends_at)
    ).all()
    settled = 0
    for auction_id in due:
        settled += settle_one(session, auction_id, clock)
        session.commit()
    return settled


def bets_close_at(auction: Auction) -> datetime:
    """Instant à partir duquel on ne peut plus parier."""
    pct = get_rules().bet.close_at_percent_of_duration
    return auction.starts_at + (auction.ends_at - auction.starts_at) * pct // 100


def place_bet(
    session: Session, auction_id: int, account_id: int, prediction: int, clock: Clock
) -> Bet:
    """Pari sur le prix final : mise fixe bloquée, un seul pari par enchère."""
    rules = get_rules().bet
    now = clock.now()
    auction = _lock_auction(session, auction_id)
    if auction.status != "open" or now >= auction.ends_at:
        raise AuctionClosed
    if now >= bets_close_at(auction):
        raise BetsClosed
    if account_id == auction.seller_id:
        raise BetOnOwnAuction
    if session.scalar(
        select(Bid.id).where(Bid.auction_id == auction_id, Bid.bidder_id == account_id).limit(1)
    ):
        raise BidderCannotBet
    if session.get(Bet, (auction_id, account_id)):
        raise AlreadyBet
    top = top_bid(session, auction_id)
    current = top.amount if top else auction.start_price
    if prediction < current:
        raise PredictionTooLow(current)
    ledger.lock_accounts(session, account_id)  # sérialise les paris d'un même joueur
    open_bets = session.scalar(
        select(func.count())
        .select_from(Bet)
        .join(Auction, Auction.id == Bet.auction_id)
        .where(Bet.account_id == account_id, Auction.status == "open", Auction.ends_at > now)
    )
    if open_bets >= rules.max_open_per_account:
        raise TooManyOpenBets
    stake = bets.stake_for(auction.start_price)
    ledger.lock(session, account_id, stake, f"bet:auction:{auction_id}")
    bet = Bet(
        auction_id=auction_id,
        account_id=account_id,
        prediction=prediction,
        stake=stake,
        created_at=now,
    )
    session.add(bet)
    session.flush()
    return bet
