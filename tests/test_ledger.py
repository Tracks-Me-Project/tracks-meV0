import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracks import accounts, ledger
from tracks.models import Account, LedgerEntry


def _acc(session: Session, name: str = "a") -> Account:
    account, _ = accounts.create_account(session, name)
    session.commit()
    return account


def test_signup_grants_starting_coins(session):
    a = _acc(session)
    assert (a.balance_available, a.balance_locked) == (1000, 0)


def test_lock_unlock_spend(session):
    a = _acc(session)
    ledger.lock(session, a.id, 300)
    assert (a.balance_available, a.balance_locked) == (700, 300)
    ledger.unlock(session, a.id, 100)
    assert (a.balance_available, a.balance_locked) == (800, 200)
    ledger.spend_locked(session, a.id, 200)
    assert (a.balance_available, a.balance_locked) == (800, 0)


def test_credit(session):
    a = _acc(session)
    ledger.credit(session, a.id, 5, "recycle")
    assert a.balance_available == 1005


def test_cannot_overspend(session):
    a = _acc(session)
    with pytest.raises(ledger.InsufficientFunds):
        ledger.lock(session, a.id, 1001)
    with pytest.raises(ledger.InsufficientFunds):
        ledger.unlock(session, a.id, 1)
    with pytest.raises(ledger.InsufficientFunds):
        ledger.spend_locked(session, a.id, 1)


@pytest.mark.parametrize("amount", [0, -5])
def test_amount_must_be_positive(session, amount):
    a = _acc(session)
    with pytest.raises(ValueError):
        ledger.lock(session, a.id, amount)


def test_balance_equals_ledger_sum(session):
    a = _acc(session)
    ledger.lock(session, a.id, 300)
    ledger.unlock(session, a.id, 50)
    ledger.credit(session, a.id, 7, "payout")
    ledger.spend_locked(session, a.id, 100)
    session.commit()
    sums = session.execute(
        select(func.sum(LedgerEntry.available_delta), func.sum(LedgerEntry.locked_delta)).where(
            LedgerEntry.account_id == a.id
        )
    ).one()
    session.refresh(a)
    assert sums == (a.balance_available, a.balance_locked)


def test_concurrent_locks_cannot_double_spend(engine, session):
    a = _acc(session)
    barrier, results = threading.Barrier(2), []

    def worker() -> None:
        with Session(engine) as s:
            barrier.wait()
            try:
                ledger.lock(s, a.id, 600)
                s.commit()
                results.append("ok")
            except ledger.InsufficientFunds:
                results.append("refused")

    threads = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == ["ok", "refused"]
