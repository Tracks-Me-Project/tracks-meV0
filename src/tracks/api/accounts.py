from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from tracks import accounts
from tracks.api.deps import DbSession, get_clock
from tracks.clock import Clock
from tracks.models import Account

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


class NewAccount(BaseModel):
    name: str = Field(min_length=1, max_length=50, pattern=r"^[^\x00]+$")


def current_account(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: DbSession,
) -> Account:
    account = accounts.find_by_token(session, creds.credentials) if creds else None
    if account is None:
        raise HTTPException(status_code=401, detail="jeton invalide")
    return account


@router.post("/accounts", status_code=201)
def create(
    body: NewAccount,
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict:
    try:
        account, token = accounts.create_account(session, body.name, clock)
    except accounts.NameTaken:
        raise HTTPException(status_code=409, detail="nom déjà pris") from None
    return {"id": account.id, "name": account.name, "token": token}


@router.get("/me")
def me(account: Annotated[Account, Depends(current_account)]) -> dict:
    return {
        "id": account.id,
        "name": account.name,
        "available": account.balance_available,
        "locked": account.balance_locked,
    }
