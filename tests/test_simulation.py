import asyncio

import pytest

from tracks.models import Track
from tracks.simulation import abuse
from tracks.simulation.bots import PROFILES, Bot
from tracks.simulation.checks import check_invariants
from tracks.simulation.world import World


@pytest.fixture
def catalogue(session):
    session.add_all(
        Track(
            recording_mbid=f"r{i:02}",
            title=f"t{i}",
            album_mbid="a",
            album="A",
            artist_mbid="x",
            artist="X",
            album_year=None,
        )
        for i in range(30)
    )
    session.commit()


@pytest.mark.parametrize("scenario", abuse.SCENARIOS, ids=lambda s: s.__name__)
def test_abuse_is_resisted(engine, catalogue, scenario):
    async def run():
        async with World(engine) as world:
            result = await scenario(world)
            problems = check_invariants(
                engine, world.clock.now(), world.boosters_opened, world.injected_cards
            )
            return result, problems

    result, problems = asyncio.run(run())
    assert result.resisted, result.detail
    assert problems == []


def test_small_simulation_is_consistent(engine, catalogue):
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    from tracks.models import Auction
    from tracks.simulation.run import simulate

    async def run():
        async with World(engine, seed=7) as world:
            players = [await world.signup(f"bot-{i}") for i in range(8)]
            bots = [Bot(p, PROFILES[i % len(PROFILES)]) for i, p in enumerate(players)]
            await simulate(world, bots, days=1, tick_minutes=30)
            return world

    world = asyncio.run(run())
    assert world.server_errors == 0
    assert check_invariants(engine, world.clock.now(), world.boosters_opened, 0) == []
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Auction)) > 0


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("UPDATE accounts SET balance_available = balance_available + 1 WHERE id = 1", "journal"),
        (
            "UPDATE accounts SET balance_locked = balance_locked + 1, "
            "balance_available = balance_available - 1 WHERE id = 1",
            "journal",
        ),
        ("UPDATE collection SET quantity = quantity + 1", "cartes"),
        (
            "UPDATE auctions SET status = 'open' "
            "WHERE id = (SELECT min(id) FROM auctions WHERE status = 'unsold')",
            "échue",
        ),
        ("UPDATE bets SET payout = NULL WHERE payout IS NOT NULL", "pari"),
    ],
    ids=["solde", "bloqué", "carte", "enchère rouverte", "pari non réglé"],
)
def test_checks_detect_corruption(engine, catalogue, sql, expected):
    """Les contrôles ne sont utiles que s'ils échouent quand la base est corrompue."""
    from sqlalchemy import text

    from tracks.simulation.run import simulate

    async def run():
        async with World(engine, seed=3) as world:
            players = [await world.signup(f"bot-{i}") for i in range(8)]
            bots = [Bot(p, PROFILES[i % len(PROFILES)]) for i, p in enumerate(players)]
            await simulate(world, bots, days=1, tick_minutes=30)
            return world

    world = asyncio.run(run())
    args = (engine, world.clock.now(), world.boosters_opened, 0)
    assert check_invariants(*args) == []
    with engine.begin() as conn:
        affected = conn.execute(text(sql)).rowcount
    assert affected, "la simulation n'a produit aucune ligne à corrompre"
    assert expected in " | ".join(check_invariants(*args))
