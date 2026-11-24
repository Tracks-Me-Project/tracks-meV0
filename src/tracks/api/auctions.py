from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import auctions, ledger
from tracks.api.accounts import current_account
from tracks.api.boosters import get_clock
from tracks.clock import Clock
from tracks.db import get_session
from tracks.models import Account, Auction, Bid, Track

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
    recording_mbid: str
    start_price: int = Field(gt=0)
    duration_minutes: int


class NewBid(BaseModel):
    amount: int = Field(gt=0)


def _view(session: Session, a: Auction) -> dict:
    # shortcut: 3 requêtes par enchère (liste limitée à 100), à regrouper si la liste devient lente.
    top = auctions.top_bid(session, a.id)
    track = session.get(Track, a.recording_mbid)
    count = session.scalar(select(func.count()).select_from(Bid).where(Bid.auction_id == a.id))
    return {
        "id": a.id,
        "seller_id": a.seller_id,
        "recording_mbid": a.recording_mbid,
        "title": track.title,
        "artist": track.artist,
        "start_price": a.start_price,
        "current_price": top.amount if top else a.start_price,
        "min_next_bid": auctions.min_next_bid(a.start_price, top.amount if top else None),
        "bid_count": count,
        "ends_at": a.ends_at,
        "status": a.status,
        "winner_id": a.winner_id,
        "final_price": a.final_price,
    }


@router.post("/auctions", status_code=201)
def create(
    body: NewAuction,
    account: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        a = auctions.create(
            session, account.id, body.recording_mbid, body.start_price, body.duration_minutes, clock
        )
    except auctions.AuctionError as exc:
        raise _error(exc) from None
    return _view(session, a)


@router.get("/auctions")
def list_open(
    _: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    rows = session.scalars(
        select(Auction)
        .where(Auction.status == "open", Auction.ends_at > clock.now())
        .order_by(Auction.ends_at, Auction.id)
        .limit(limit)
        .offset(offset)
    )
    return [_view(session, a) for a in rows]


@router.get("/auctions/{auction_id}")
def get_one(
    auction_id: int,
    _: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        auctions.settle_one(session, auction_id, clock)  # règlement paresseux à la lecture
    except auctions.AuctionError as exc:
        raise _error(exc) from None
    return _view(session, session.get(Auction, auction_id))


@router.post("/auctions/{auction_id}/bids", status_code=201)
def bid(
    auction_id: int,
    body: NewBid,
    account: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        auctions.place_bid(session, auction_id, account.id, body.amount, clock)
    except (auctions.AuctionError, ledger.InsufficientFunds) as exc:
        raise _error(exc) from None
    return _view(session, session.get(Auction, auction_id))


@router.post("/auctions/{auction_id}/cancel")
def cancel(
    auction_id: int,
    account: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        auctions.cancel(session, auction_id, account.id, clock)
    except auctions.AuctionError as exc:
        raise _error(exc) from None
    return _view(session, session.get(Auction, auction_id))
