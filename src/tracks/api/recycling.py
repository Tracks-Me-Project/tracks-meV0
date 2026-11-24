from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tracks import recycling
from tracks.api.accounts import current_account
from tracks.api.deps import Amount, Mbid, get_clock
from tracks.clock import Clock
from tracks.db import get_session
from tracks.models import Account

router = APIRouter()


class RecycleRequest(BaseModel):
    recording_mbid: Mbid
    quantity: Amount


@router.post("/collection/recycle")
def recycle(
    body: RecycleRequest,
    account: Annotated[Account, Depends(current_account)],
    session: Annotated[Session, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        result = recycling.recycle(session, account.id, body.recording_mbid, body.quantity, clock)
    except recycling.NotEnoughDuplicates as e:
        raise HTTPException(
            status_code=409, detail={"error": "doublons insuffisants", "available": e.available}
        ) from None
    except recycling.DailyCapExceeded as e:
        raise HTTPException(
            status_code=409, detail={"error": "plafond quotidien", "remaining": e.remaining}
        ) from None
    return {
        "recycled": result.count,
        "coins": result.coins,
        "remaining_cap_today": result.remaining_cap,
    }
