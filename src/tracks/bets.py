"""Paris au podium : calcul des gains et règlement. Les règles viennent de la simulation
(sim/marche.py de track-auction-poc) ; les paramètres sont dans config/rules.toml."""

import math
from fractions import Fraction

from sqlalchemy import select
from sqlalchemy.orm import Session

from tracks import ledger
from tracks.config import get_rules
from tracks.models import Bet


def stake_for(start_price: int) -> int:
    """Mise fixe : un pourcentage du prix de départ, arrondi au supérieur, au moins 1."""
    pct = get_rules().bet.stake_percent_of_start_price
    return max(1, (start_price * pct + 99) // 100)


def compute_payouts(stake: int, distances: list[int]) -> list[int]:
    """Gain de chaque parieur, dans l'ordre de `distances` (écart au prix final).

    - 1 parieur : remboursé. 2 parieurs : 70 / 30 de la cagnotte.
    - 3 parieurs : toute la cagnotte est partagée 50 / 30 / 20.
    - Plus de 3 : 80 % de la cagnotte au podium (50 / 30 / 20), le reste à parts égales entre les
      autres. À 4, la part du podium monte juste assez pour que le 4e ne touche jamais plus que
      le 3e.
    - Des écarts égaux se partagent à parts égales les places qu'ils occupent.
    - Chaque gain est arrondi à l'inférieur et plafonné à `payout_cap_multiple` x la mise ;
      arrondis et surplus sont détruits.
    """
    rules = get_rules().bet
    n = len(distances)
    pot = stake * n
    if n == 1:
        return [stake]
    if n == 2:
        amounts = [Fraction(pot * share, 100) for share in rules.two_bettors_split_percent]
    else:
        third = Fraction(rules.podium_split_percent[2], 100)
        podium = max(Fraction(pot * rules.podium_share_percent, 100), pot / (1 + (n - 3) * third))
        amounts = [podium * share / 100 for share in rules.podium_split_percent]
        if n > 3:
            amounts += [(pot - podium) / (n - 3)] * (n - 3)
    cap = rules.payout_cap_multiple * stake
    order = sorted(range(n), key=lambda i: distances[i])
    payouts = [0] * n
    start = 0
    while start < n:
        end = start
        while end + 1 < n and distances[order[end + 1]] == distances[order[start]]:
            end += 1
        average = sum(amounts[start : end + 1]) / (end - start + 1)
        for rank in range(start, end + 1):
            payouts[order[rank]] = min(math.floor(average), cap)
        start = end + 1
    return payouts


def bettor_ids(session: Session, auction_id: int) -> list[int]:
    return list(session.scalars(select(Bet.account_id).where(Bet.auction_id == auction_id)))


def _bets(session: Session, auction_id: int) -> list[Bet]:
    return list(
        session.scalars(select(Bet).where(Bet.auction_id == auction_id).order_by(Bet.account_id))
    )


def refund_bets(session: Session, auction_id: int) -> None:
    """Enchère annulée ou invendue, ou parieur seul : les mises sont rendues."""
    for bet in _bets(session, auction_id):
        ledger.unlock(session, bet.account_id, bet.stake, f"bet:auction:{auction_id}")
        bet.payout = bet.stake


def settle_bets(session: Session, auction_id: int, final_price: int) -> None:
    """Enchère vendue : répartit la cagnotte. L'appelant a déjà verrouillé les comptes."""
    bets = _bets(session, auction_id)
    if len(bets) < 2:
        refund_bets(session, auction_id)
        return
    ref = f"bet:auction:{auction_id}"
    payouts = compute_payouts(bets[0].stake, [abs(b.prediction - final_price) for b in bets])
    for bet, payout in zip(bets, payouts, strict=True):
        ledger.spend_locked(session, bet.account_id, bet.stake, ref)
        if payout:
            ledger.credit(session, bet.account_id, payout, "payout", ref)
        bet.payout = payout
