"""Contrôles de cohérence, calculés directement dans la base. Renvoie la liste des anomalies.

Après une partie à la main, serveur lancé : `python -m tracks.simulation.checks` (lecture seule,
base désignée par TRACKS_DATABASE_URL)."""

import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from tracks.config import get_rules
from tracks.db import get_engine


def check_invariants(
    engine: Engine, now: datetime, boosters_opened: int | None, injected_cards: int
) -> list[str]:
    """boosters_opened=None (nombre inconnu après une partie réelle) : cartes non comptées."""
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

        if boosters_opened is not None:
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


def main() -> int:
    # Une seule photo de la base pour tous les contrôles : sinon une mise passée entre deux
    # requêtes donnerait une fausse anomalie.
    engine = get_engine().execution_options(
        isolation_level="REPEATABLE READ", postgresql_readonly=True
    )
    # Marge : une enchère tout juste échue attend le prochain passage de la boucle de règlement.
    margin = timedelta(seconds=get_rules().auction.settle_interval_seconds + 5)
    problems = check_invariants(engine, datetime.now(UTC) - margin, None, 0)
    print("\n".join(f"ÉCHEC : {p}" for p in problems) or "OK : soldes et enchères cohérents")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
