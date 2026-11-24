from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tracks import accounts
from tracks.db import get_session
from tracks.models import Account

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


class NewAccount(BaseModel):
    name: str = Field(min_length=1, max_length=50)


def current_account(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> Account:
    account = accounts.find_by_token(session, creds.credentials) if creds else None
    if account is None:
        raise HTTPException(status_code=401, detail="jeton invalide")
    return account


@router.post("/accounts", status_code=201)
def create(body: NewAccount, session: Annotated[Session, Depends(get_session)]) -> dict:
    try:
        account, token = accounts.create_account(session, body.name)
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
