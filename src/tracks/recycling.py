"""Recyclage : un doublon rendu = de la monnaie, dans la limite d'un plafond par jour."""

from datetime import UTC
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import ledger
from tracks.clock import Clock
from tracks.config import get_rules
from tracks.models import Account, CollectionItem, LedgerEntry


class NotEnoughDuplicates(Exception):
    def __init__(self, available: int) -> None:
        self.available = available


class DailyCapExceeded(Exception):
    def __init__(self, remaining: int) -> None:
        self.remaining = remaining


class Recycled(NamedTuple):
    count: int
    coins: int
    remaining_cap: int


def _earned_today(session: Session, account_id: int, day_start) -> int:
    return session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.available_delta), 0)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.kind == "recycle",
            LedgerEntry.created_at >= day_start,
        )
    )


def recycle(
    session: Session, account_id: int, recording_mbid: str, quantity: int, clock: Clock
) -> Recycled:
    if quantity < 1:
        raise ValueError("la quantité doit être positive")
    rules = get_rules().recycling
    now = clock.now()
    day_start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)  # jour UTC

    # Verrou du compte d'abord : deux recyclages simultanés ne peuvent pas dépasser le plafond.
    session.execute(select(Account.id).where(Account.id == account_id).with_for_update()).one()

    item = session.get(CollectionItem, (account_id, recording_mbid))
    duplicates = item.quantity - 1 if item else 0
    if quantity > duplicates:
        raise NotEnoughDuplicates(duplicates)

    remaining = rules.daily_cap - _earned_today(session, account_id, day_start)
    coins = quantity * rules.coins_per_track
    if coins > remaining:
        raise DailyCapExceeded(max(0, remaining))

    item.quantity -= quantity
    ledger.credit(session, account_id, coins, "recycle", f"recycle:{recording_mbid}", at=now)
    return Recycled(quantity, coins, remaining - coins)
