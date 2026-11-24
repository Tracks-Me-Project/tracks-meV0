"""Mouvements de monnaie. Aucune fonction ne commit : l'appelant maîtrise la transaction."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from tracks.models import Account, LedgerEntry


class InsufficientFunds(Exception):
    pass


def _apply(
    session: Session, account_id: int, kind: str, available: int, locked: int, ref: str | None
) -> None:
    # FOR UPDATE : deux opérations simultanées sur un compte passent l'une après l'autre.
    account = session.execute(
        select(Account).where(Account.id == account_id).with_for_update()
    ).scalar_one()
    if account.balance_available + available < 0 or account.balance_locked + locked < 0:
        raise InsufficientFunds(kind)
    account.balance_available += available
    account.balance_locked += locked
    session.add(
        LedgerEntry(
            account_id=account_id,
            kind=kind,
            available_delta=available,
            locked_delta=locked,
            ref=ref,
        )
    )
    session.flush()


def _positive(amount: int) -> int:
    if amount <= 0:
        raise ValueError("le montant doit être positif")
    return amount


def credit(session: Session, account_id: int, amount: int, kind: str, ref: str | None = None):
    """Monnaie créée ou gagnée : kind = grant, payout, recycle, refund..."""
    _apply(session, account_id, kind, _positive(amount), 0, ref)


def lock(session: Session, account_id: int, amount: int, ref: str | None = None) -> None:
    """Bloque une mise (enchère ou pari)."""
    _apply(session, account_id, "lock", -_positive(amount), _positive(amount), ref)


def unlock(session: Session, account_id: int, amount: int, ref: str | None = None) -> None:
    """Rend une mise bloquée (perdue ou annulée)."""
    _apply(session, account_id, "unlock", _positive(amount), -_positive(amount), ref)


def spend_locked(session: Session, account_id: int, amount: int, ref: str | None = None) -> None:
    """Retire définitivement une mise bloquée (enchère gagnée, pari perdu)."""
    _apply(session, account_id, "spend", 0, -_positive(amount), ref)
