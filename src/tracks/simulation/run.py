"""Lanceur : python -m tracks.simulation.run --bots 20 --days 3 --seed 1

Vide et recrée la base de simulation à chaque exécution : refuse toute base dont le nom ne
contient pas « sim »."""

import argparse
import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

SIM_URL = os.environ.get(
    "TRACKS_SIM_DATABASE_URL", "postgresql+psycopg://tracks:tracks@localhost:5442/tracks_sim"
)
os.environ["TRACKS_DATABASE_URL"] = SIM_URL  # avant tout import de tracks : la config le lit

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from tracks.catalogue import import_catalogue  # noqa: E402
from tracks.config import get_settings  # noqa: E402
from tracks.simulation import abuse  # noqa: E402
from tracks.simulation.bots import PROFILES, Bot  # noqa: E402
from tracks.simulation.checks import check_invariants  # noqa: E402
from tracks.simulation.world import World  # noqa: E402


def prepare_database(catalogue: Path):
    url = make_url(SIM_URL)
    if "sim" not in (url.database or ""):
        sys.exit(f"Refus : la base « {url.database} » ne contient pas « sim » dans son nom.")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", SIM_URL)
    command.upgrade(cfg, "head")
    with Session(engine) as s, s.begin():
        added = import_catalogue(s, catalogue)
    return engine, added


async def simulate(world: World, bots: list[Bot], days: int, tick_minutes: int) -> None:
    for _ in range(days * 24 * 60 // tick_minutes):
        world.clock.advance(timedelta(minutes=tick_minutes))
        await world.settle()
        r = await world.call(bots[0].player, "GET", "/auctions", params={"limit": 100})
        auctions = r.json() if r.status_code == 200 else []
        order = bots[:]
        world.rng.shuffle(order)
        for bot in order:
            await bot.act(world, auctions)
    world.clock.advance(timedelta(hours=13))  # laisse finir les dernières enchères (12 h max)
    await world.settle()


def _scalar(engine, sql: str) -> int:
    with Session(engine) as s:
        return s.execute(text(sql)).scalar_one() or 0


def report(engine, world: World, n_bots: int, days: int) -> None:
    by_status = dict(
        Session(engine).execute(text("SELECT status, count(*) FROM auctions GROUP BY status")).all()
    )
    created = sum(by_status.values())
    sold = by_status.get("sold", 0)
    won = _scalar(engine, "SELECT count(*) FROM bets WHERE payout > stake")
    lost = _scalar(engine, "SELECT count(*) FROM bets WHERE payout < stake")
    staked = _scalar(engine, "SELECT sum(stake) FROM bets WHERE payout IS NOT NULL")
    paid = _scalar(engine, "SELECT sum(payout) FROM bets WHERE payout IS NOT NULL")
    recycled = _scalar(engine, "SELECT sum(available_delta) FROM ledger WHERE kind = 'recycle'")
    volume = _scalar(engine, "SELECT sum(final_price) FROM auctions WHERE status = 'sold'")
    print(f"\n=== Simulation : {n_bots} joueurs virtuels, {days} jour(s) ===")
    print(f"Boosters ouverts : {world.boosters_opened}")
    print(
        f"Enchères : {created} créées, {sold} vendues ({100 * sold // max(created, 1)} %), "
        f"{by_status.get('unsold', 0)} invendues, {by_status.get('cancelled', 0)} annulées"
    )
    print(f"Monnaie échangée sur les ventes : {volume} ; créée par le recyclage : {recycled}")
    print(
        f"Paris réglés : {won} gagnants, {lost} perdants ; rendement moyen "
        f"{(100 * (paid - staked) / staked if staked else 0):+.1f} %"
    )
    print(f"Monnaie détruite par les paris (arrondis, plafond) : {staked - paid}")
    errors = [(r, c, n) for (r, c), n in sorted(world.stats.items()) if c >= 500]
    print(f"Erreurs serveur (500) : {sum(n for *_, n in errors)}")
    refused = sum(n for (_, c), n in world.stats.items() if 400 <= c < 500)
    total = sum(world.stats.values())
    print(f"Requêtes : {total}, dont {refused} refusées par les règles (normal)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bots", type=int, default=20)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--tick-minutes", type=int, default=15)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--catalogue", type=Path, default=get_settings().catalogue_path)
    parser.add_argument("--skip-abuse", action="store_true")
    args = parser.parse_args()

    engine, added = prepare_database(args.catalogue)
    print(f"Base de simulation prête ({added} titres).")

    async def run() -> tuple[World, list[abuse.AbuseResult]]:
        async with World(engine, seed=args.seed) as world:
            players = [await world.signup(f"bot-{i}") for i in range(args.bots)]
            bots = [Bot(p, PROFILES[i % len(PROFILES)]) for i, p in enumerate(players)]
            await simulate(world, bots, args.days, args.tick_minutes)
            results = [] if args.skip_abuse else await abuse.run_all(world)
            return world, results

    world, results = asyncio.run(run())
    report(engine, world, args.bots, args.days)

    problems = check_invariants(
        engine, world.clock.now(), world.boosters_opened, world.injected_cards
    )
    print("\n--- Contrôles de cohérence ---")
    print("OK : tout est cohérent" if not problems else "\n".join(f"ÉCHEC : {p}" for p in problems))
    print("\n--- Tentatives d'abus ---")
    for r in results:
        print(f"{'RÉSISTE' if r.resisted else 'ÉCHEC  '} {r.name} ({r.detail})")
    failed = bool(problems) or world.server_errors or any(not r.resisted for r in results)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
