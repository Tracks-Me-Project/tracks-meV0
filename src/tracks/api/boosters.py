import random
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tracks import boosters, collection
from tracks.api.accounts import current_account
from tracks.clock import Clock, SystemClock
from tracks.config import get_rules
from tracks.db import get_session
from tracks.models import Account, Track

router = APIRouter()


def get_clock() -> Clock:
    return SystemClock()


def get_rng() -> random.Random:
    return random.Random()


def _track(t: Track) -> dict:
    return {
        "id": t.recording_mbid,
        "title": t.title,
        "album": t.album,
        "year": t.album_year,
        "artist": t.artist,
    }


@router.get("/boosters")
def stock(
    account: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    now = clock.now()
    state = boosters.refill(session, account.id, now)
    return {
        "stock": state.stock,
        "max_stock": get_rules().booster.max_stock,
        "seconds_until_next": boosters.seconds_until_next(state, now),
    }


@router.post("/boosters/open")
def open_one(
    account: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    rng: Annotated[random.Random, Depends(get_rng)],
) -> dict:
    try:
        drawn = boosters.open_booster(session, account.id, clock, rng)
    except boosters.NoBoosterAvailable:
        raise HTTPException(status_code=409, detail="aucun booster disponible") from None
    except boosters.EmptyCatalogue:
        raise HTTPException(status_code=503, detail="catalogue vide") from None
    return {"tracks": [_track(t) for t in drawn]}


@router.get("/collection")
def my_collection(
    account: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    rows = collection.list_collection(session, account.id, limit, offset)
    return [{**_track(t), "quantity": q} for t, q in rows]
