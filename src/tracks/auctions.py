"""Enchères. Aucune fonction ne commit (sauf settle_due, qui règle une enchère par transaction)."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import collection, ledger
from tracks.clock import Clock
from tracks.config import get_rules
from tracks.models import Auction, Bid


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


def cancel(session: Session, auction_id: int, seller_id: int, clock: Clock) -> None:
    """Le vendeur annule pendant la première moitié de la durée, même s'il y a des mises."""
    auction = _lock_auction(session, auction_id)
    if auction.seller_id != seller_id:
        raise NotSeller
    if auction.status != "open":
        raise AuctionClosed
    window = (auction.ends_at - auction.starts_at) * get_rules().auction.cancel_window_percent
    if clock.now() >= auction.starts_at + window // 100:
        raise CancelWindowPassed
    top = top_bid(session, auction_id)
    if top:
        ledger.lock_accounts(session, top.bidder_id)
        ledger.unlock(session, top.bidder_id, top.amount, f"auction:{auction_id}")
    collection.add_copies(session, seller_id, auction.recording_mbid, 1)
    auction.status = "cancelled"


def settle_one(session: Session, auction_id: int, clock: Clock) -> bool:
    """Règle l'enchère si elle est ouverte et échue. Renvoie True si elle vient d'être réglée."""
    auction = _lock_auction(session, auction_id)
    if auction.status != "open" or clock.now() < auction.ends_at:
        return False
    top = top_bid(session, auction_id)
    if top is None:
        collection.add_copies(session, auction.seller_id, auction.recording_mbid, 1)
        auction.status = "unsold"
        return True
    ref = f"auction:{auction_id}"
    ledger.lock_accounts(session, auction.seller_id, top.bidder_id)
    ledger.spend_locked(session, top.bidder_id, top.amount, ref)
    ledger.credit(session, auction.seller_id, top.amount, "sale", ref)  # aucune commission
    collection.add_copies(session, top.bidder_id, auction.recording_mbid, 1)
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
