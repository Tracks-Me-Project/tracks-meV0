import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tracks import boosters, ledger
from tracks.clock import Clock, SystemClock
from tracks.config import get_rules
from tracks.models import Account


class NameTaken(Exception):
    pass


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_account(
    session: Session, name: str, clock: Clock | None = None
) -> tuple[Account, str]:
    """Crée le compte et crédite la monnaie de départ. Renvoie le jeton (jamais stocké en clair)."""
    clock = clock or SystemClock()
    token = secrets.token_urlsafe(32)
    account = Account(name=name, token_hash=hash_token(token))
    session.add(account)
    try:
        session.flush()
    except IntegrityError as exc:
        raise NameTaken(name) from exc
    ledger.credit(session, account.id, get_rules().account.starting_coins, "grant", "signup")
    session.add(boosters.new_state(account.id, clock.now()))
    return account, token


def find_by_token(session: Session, token: str) -> Account | None:
    return session.scalar(select(Account).where(Account.token_hash == hash_token(token)))
