import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import auctions, bets, ledger
from tracks.api.accounts import current_account
from tracks.api.deps import MAX_INT, Amount, AuctionId, DbSession, Mbid, Offset, get_clock
from tracks.clock import Clock
from tracks.models import Account, Auction, Bet, Bid, Track

router = APIRouter()

_STATUS = {
    auctions.AuctionNotFound: 404,
    auctions.NotSeller: 403,
    auctions.InvalidDuration: 422,
    auctions.StartPriceTooLow: 422,
}


def _error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=_STATUS.get(type(exc), 409),
        detail={"error": type(exc).__name__, **vars(exc)},
    )


class NewAuction(BaseModel):
    recording_mbid: Mbid
    start_price: Amount
    duration_minutes: int = Field(gt=0, le=MAX_INT)


class NewBet(BaseModel):
    prediction: Amount


class NewBid(BaseModel):
    amount: Amount


def _name(session: Session, account_id: int | None) -> str | None:
    return None if account_id is None else session.get(Account, account_id).name


def _view(session: Session, a: Auction, clock: Clock, viewer_id: int) -> dict:
    # shortcut: jusqu'à 8 requêtes par enchère (100 au plus), à regrouper si la liste est lente.
    top = auctions.top_bid(session, a.id)
    track = session.get(Track, a.recording_mbid)
    count = session.scalar(select(func.count()).select_from(Bid).where(Bid.auction_id == a.id))
    leader_id = top.bidder_id if top else None
    now = clock.now()
    left = (a.ends_at - now).total_seconds() if a.status == "open" else 0
    # 0 dès qu'une mise existe : l'annulation n'est plus possible.
    cancellable = a.status == "open" and not top
    cancel_left = (auctions.cancel_deadline(a) - now).total_seconds() if cancellable else 0
    closes_at = auctions.bets_close_at(a)
    bets_left = (closes_at - now).total_seconds() if a.status == "open" else 0
    # Propres à celui qui regarde : le pronostic d'un autre ne sort jamais.
    mine = session.get(Bet, (a.id, viewer_id))
    i_have_bid = session.scalar(
        select(Bid.id).where(Bid.auction_id == a.id, Bid.bidder_id == viewer_id).limit(1)
    )
    return {
        "id": a.id,
        "seller_id": a.seller_id,
        "seller_name": _name(session, a.seller_id),
        "leader_id": leader_id,
        "leader_name": _name(session, leader_id),
        "recording_mbid": a.recording_mbid,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "start_price": a.start_price,
        "current_price": top.amount if top else a.start_price,
        "min_next_bid": auctions.min_next_bid(a.start_price, top.amount if top else None),
        "bid_count": count,
        "ends_at": a.ends_at,
        # calculé par le serveur : l'horloge du téléphone n'intervient pas. Arrondi au-dessus.
        "seconds_left": max(0, math.ceil(left)),
        "cancel_seconds_left": max(0, math.ceil(cancel_left)),
        "bet_stake": bets.stake_for(a.start_price),
        "bets_close_at": closes_at,
        "bets_seconds_left": max(0, math.ceil(bets_left)),
        "my_prediction": mine.prediction if mine else None,
        "i_have_bid": i_have_bid is not None,
        "status": a.status,
        "winner_id": a.winner_id,
        "winner_name": _name(session, a.winner_id),
        "final_price": a.final_price,
    }


@router.post("/auctions", status_code=201)
def create(
    body: NewAuction,
    account: Annotated[Account, Depends(current_account)],
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        a = auctions.create(
            session, account.id, body.recording_mbid, body.start_price, body.duration_minutes, clock
        )
    except auctions.AuctionError as exc:
        raise _error(exc) from None
    return _view(session, a, clock, account.id)


@router.get("/auctions")
def list_open(
    account: Annotated[Account, Depends(current_account)],
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Offset = 0,
) -> list[dict]:
    rows = session.scalars(
        select(Auction)
        .where(Auction.status == "open", Auction.ends_at > clock.now())
        .order_by(Auction.ends_at, Auction.id)
        .limit(limit)
        .offset(offset)
    )
    return [_view(session, a, clock, account.id) for a in rows]


@router.get("/auctions/{auction_id}")
def get_one(
    auction_id: AuctionId,
    account: Annotated[Account, Depends(current_account)],
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        auctions.settle_one(session, auction_id, clock)  # règlement paresseux à la lecture
    except auctions.AuctionError as exc:
        raise _error(exc) from None
    return _view(session, session.get(Auction, auction_id), clock, account.id)


@router.post("/auctions/{auction_id}/bids", status_code=201)
def bid(
    auction_id: AuctionId,
    body: NewBid,
    account: Annotated[Account, Depends(current_account)],
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        auctions.place_bid(session, auction_id, account.id, body.amount, clock)
    except (auctions.AuctionError, ledger.InsufficientFunds) as exc:
        raise _error(exc) from None
    return _view(session, session.get(Auction, auction_id), clock, account.id)


@router.post("/auctions/{auction_id}/cancel")
def cancel(
    auction_id: AuctionId,
    account: Annotated[Account, Depends(current_account)],
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        auctions.cancel(session, auction_id, account.id, clock)
    except auctions.AuctionError as exc:
        raise _error(exc) from None
    return _view(session, session.get(Auction, auction_id), clock, account.id)


@router.post("/auctions/{auction_id}/bets", status_code=201)
def place_bet(
    auction_id: AuctionId,
    body: NewBet,
    account: Annotated[Account, Depends(current_account)],
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        bet = auctions.place_bet(session, auction_id, account.id, body.prediction, clock)
    except (auctions.AuctionError, ledger.InsufficientFunds) as exc:
        raise _error(exc) from None
    return {"auction_id": bet.auction_id, "prediction": bet.prediction, "stake": bet.stake}


@router.get("/bets")
def my_bets(
    account: Annotated[Account, Depends(current_account)],
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Offset = 0,
) -> list[dict]:
    """Seulement mes paris : les pronostics des autres restent cachés."""
    rows = session.execute(
        select(Bet, Auction, Track)
        .join(Auction, Auction.id == Bet.auction_id)
        .join(Track, Track.recording_mbid == Auction.recording_mbid)
        .where(Bet.account_id == account.id)
        .order_by(Bet.created_at.desc(), Bet.auction_id)
        .limit(limit)
        .offset(offset)
    )
    now = clock.now()
    return [
        {
            "auction_id": b.auction_id,
            "title": t.title,
            "artist": t.artist,
            "seconds_left": max(0, math.ceil((a.ends_at - now).total_seconds()))
            if a.status == "open"
            else 0,
            "prediction": b.prediction,
            "stake": b.stake,
            "auction_status": a.status,
            "final_price": a.final_price,
            "payout": b.payout,
        }
        for b, a, t in rows
    ]
