"""Boosters : stock calculé à la demande (pas de planificateur)."""

import random
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from tracks.clock import Clock
from tracks.config import get_rules
from tracks.models import BoosterState, CollectionItem, Track


class NoBoosterAvailable(Exception):
    pass


class EmptyCatalogue(Exception):
    pass


def new_state(account_id: int, now: datetime) -> BoosterState:
    """Un nouveau compte démarre avec le stock plein."""
    max_stock = get_rules().booster.max_stock
    return BoosterState(account_id=account_id, stock=max_stock, last_credited_at=now)


def refill(session: Session, account_id: int, now: datetime) -> BoosterState:
    """Verrouille l'état du compte et lui ajoute les boosters écoulés depuis le dernier crédit."""
    rules = get_rules().booster
    state = session.execute(
        select(BoosterState).where(BoosterState.account_id == account_id).with_for_update()
    ).scalar_one()
    period = timedelta(minutes=rules.minutes_per_booster)
    earned = int((now - state.last_credited_at) / period)
    state.stock = min(rules.max_stock, state.stock + earned)
    if state.stock >= rules.max_stock:
        state.last_credited_at = now  # stock plein : le chrono repart à la prochaine ouverture
    else:
        state.last_credited_at += earned * period  # on garde les minutes déjà écoulées
    return state


def seconds_until_next(state: BoosterState, now: datetime) -> int | None:
    """None si le stock est plein."""
    rules = get_rules().booster
    if state.stock >= rules.max_stock:
        return None
    due = state.last_credited_at + timedelta(minutes=rules.minutes_per_booster)
    return max(0, int((due - now).total_seconds()))


def open_booster(
    session: Session, account_id: int, clock: Clock, rng: random.Random
) -> list[Track]:
    """Ouvre un booster : retire 1 du stock, tire les titres (uniforme, avec remise)
    et les ajoute à la collection."""
    rules = get_rules().booster
    state = refill(session, account_id, clock.now())
    if state.stock < 1:
        raise NoBoosterAvailable
    # shortcut: charge tous les identifiants à chaque ouverture, à revoir au-delà de 100 000 titres.
    ids = list(session.scalars(select(Track.recording_mbid).order_by(Track.recording_mbid)))
    if not ids:
        raise EmptyCatalogue
    state.stock -= 1
    drawn = Counter(rng.choices(ids, k=rules.tracks_per_booster))
    for mbid, n in drawn.items():
        stmt = insert(CollectionItem).values(account_id=account_id, recording_mbid=mbid, quantity=n)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["account_id", "recording_mbid"],
                set_={"quantity": CollectionItem.quantity + n},
            )
        )
    found = session.scalars(select(Track).where(Track.recording_mbid.in_(drawn)))
    by_id = {t.recording_mbid: t for t in found}
    return [by_id[m] for m in drawn]
