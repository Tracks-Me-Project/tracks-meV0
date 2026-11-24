"""Contrôles de cohérence, calculés directement dans la base. Renvoie la liste des anomalies."""

from datetime import datetime

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from tracks.config import get_rules


def check_invariants(
    engine: Engine, now: datetime, boosters_opened: int, injected_cards: int
) -> list[str]:
    rules = get_rules()
    problems: list[str] = []
    with Session(engine) as s:

        def one(sql: str) -> int:
            return s.execute(text(sql)).scalar_one()

        n = one("SELECT count(*) FROM accounts")
        mismatched = one("""
            SELECT count(*) FROM accounts a LEFT JOIN (
                SELECT account_id, sum(available_delta) av, sum(locked_delta) lk
                FROM ledger GROUP BY account_id) l ON l.account_id = a.id
            WHERE a.balance_available <> coalesce(l.av, 0) OR a.balance_locked <> coalesce(l.lk, 0)
        """)
        if mismatched:
            problems.append(f"{mismatched} compte(s) dont le solde diffère du journal")

        if one("SELECT count(*) FROM accounts WHERE balance_available < 0 OR balance_locked < 0"):
            problems.append("solde négatif")

        locked = one("SELECT coalesce(sum(balance_locked), 0) FROM accounts")
        open_bids = one("""
            SELECT coalesce(sum(m.amount), 0) FROM auctions a
            JOIN LATERAL (SELECT amount FROM bids WHERE auction_id = a.id
                          ORDER BY amount DESC LIMIT 1) m ON true
            WHERE a.status = 'open'""")
        open_stakes = one("""
            SELECT coalesce(sum(b.stake), 0) FROM bets b JOIN auctions a ON a.id = b.auction_id
            WHERE a.status = 'open'""")
        if locked != open_bids + open_stakes:
            problems.append(
                f"monnaie bloquée {locked} ≠ mises ouvertes {open_bids} + paris ouverts "
                f"{open_stakes}"
            )

        total = one("SELECT coalesce(sum(balance_available + balance_locked), 0) FROM accounts")
        recycled = one("SELECT coalesce(sum(available_delta), 0) FROM ledger WHERE kind='recycle'")
        destroyed = one(
            "SELECT coalesce(sum(stake - payout), 0) FROM bets WHERE payout IS NOT NULL"
        )
        expected = n * rules.account.starting_coins + recycled - destroyed
        if total != expected:
            problems.append(f"monnaie totale {total} ≠ attendue {expected}")

        cards = one("SELECT coalesce(sum(quantity), 0) FROM collection") + one(
            "SELECT count(*) FROM auctions WHERE status = 'open'"
        )
        expected_cards = (
            boosters_opened * rules.booster.tracks_per_booster
            + injected_cards
            - recycled // rules.recycling.coins_per_track
        )
        if cards != expected_cards:
            problems.append(f"{cards} cartes comptées ≠ {expected_cards} attendues")

        due = s.execute(
            text("SELECT count(*) FROM auctions WHERE status='open' AND ends_at <= :now"),
            {"now": now},
        ).scalar_one()
        if due:
            problems.append(f"{due} enchère(s) échue(s) jamais réglée(s)")

        unsettled = one("""
            SELECT count(*) FROM bets b JOIN auctions a ON a.id = b.auction_id
            WHERE (a.status <> 'open' AND b.payout IS NULL)
               OR (a.status = 'open' AND b.payout IS NOT NULL)""")
        if unsettled:
            problems.append(f"{unsettled} pari(s) dont l'état ne suit pas celui de l'enchère")
    return problems
