import asyncio
import random

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from tracks.models import Track
from tracks.simulation import checks, live
from tracks.simulation.world import START, World


@pytest.fixture
def catalogue(session):
    session.add_all(
        Track(recording_mbid=f"r{i}", title=f"t{i}", album_mbid="a", album="A", artist_mbid="x",
              artist="X", album_year=None)
        for i in range(30)
    )
    session.commit()


def test_live_bots_play_through_the_api(engine, catalogue):
    async def run():
        async with World(engine) as server:  # l'application, sur la base de test
            world = live.LiveWorld(server.client, random.Random(3))
            await live.play(world, n_bots=6, every=0, rounds=25)
            return world

    world = asyncio.run(run())
    assert world.server_errors == 0
    assert world.done["boosters"] and world.done["ventes"] and world.done["mises"]
    # START : l'horloge simulée n'a pas avancé, aucune enchère n'est échue
    assert checks.check_invariants(engine, START, None, 0) == []


def test_live_bots_refuse_other_rules(engine, catalogue, monkeypatch):
    rules = live.get_rules()
    other = rules.model_copy(update={"account": rules.account.model_copy(
        update={"starting_coins": 1})})
    monkeypatch.setattr(live, "get_rules", lambda: other)

    async def run():
        async with World(engine) as server:
            await live.play(live.LiveWorld(server.client, random.Random(1)), 1, 0, rounds=1)

    with pytest.raises(SystemExit, match="TRACKS_RULES_PATH"):
        asyncio.run(run())


def test_checks_command(engine, catalogue, monkeypatch, capsys):
    monkeypatch.setattr(checks, "get_engine", lambda: engine)
    assert checks.main() == 0
    with Session(engine) as s, s.begin():
        s.execute(text(
            "INSERT INTO accounts (name, token_hash, balance_available, balance_locked, "
            "created_at) VALUES ('fraude', 'x', 5, 0, now())"
        ))
    assert checks.main() == 1
    assert "journal" in capsys.readouterr().out
