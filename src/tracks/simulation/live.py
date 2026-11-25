"""Joueurs virtuels « en direct » : ils jouent par l'API sur le serveur en cours, en temps réel,
pour affronter des joueurs humains.

    python -m tracks.simulation.live --bots 5 --every 5        (Ctrl+C pour arrêter)

Rien n'est vidé ni écrit directement en base : contrairement à `simulation.run`, ce lanceur
peut viser une base où l'on joue. À lancer avec le même TRACKS_RULES_PATH que le serveur."""

import argparse
import asyncio
import random
import secrets
import sys
from collections import Counter

import httpx

from tracks.config import get_rules
from tracks.simulation.bots import PROFILES, Bot
from tracks.simulation.world import Player

# Résumé à l'écran : seules les actions acceptées par le serveur.
ACTIONS = {
    "/boosters/open": "boosters",
    "/collection/recycle": "recyclages",
    "/auctions": "ventes",
    "/bids": "mises",
    "/bets": "paris",
    "/cancel": "annulations",
}


class LiveWorld:
    """Ce dont Bot a besoin (`rng`, `call`), branché sur un vrai serveur."""

    def __init__(self, client: httpx.AsyncClient, rng: random.Random) -> None:
        self.client = client
        self.rng = rng
        self.done: Counter[str] = Counter()
        self.server_errors = 0

    async def call(
        self, player: Player | None, method: str, path: str, **kwargs: object
    ) -> httpx.Response:
        headers = player.headers if player else None
        response = await self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code >= 500:
            self.server_errors += 1
            print(f"ERREUR SERVEUR {response.status_code} : {method} {path}")
        elif method == "POST" and response.is_success:
            for suffix, label in ACTIONS.items():
                if path.endswith(suffix):
                    self.done[label] += 1
        return response

    async def signup(self, name: str) -> Player:
        r = await self.call(None, "POST", "/accounts", json={"name": name})
        r.raise_for_status()
        data = r.json()
        return Player(data["id"], name, {"Authorization": f"Bearer {data['token']}"})


async def check_same_rules(client: httpx.AsyncClient) -> None:
    """Des règles différentes feraient refuser les actions des bots (durées, prix…)."""
    r = await client.get("/rules")
    r.raise_for_status()
    if r.json()["rules"] != get_rules().model_dump():
        sys.exit(
            f"Le serveur utilise {r.json()['file']} avec d'autres règles que ce terminal : "
            "définis le même TRACKS_RULES_PATH."
        )


async def play(world: LiveWorld, n_bots: int, every: float, rounds: int | None = None) -> None:
    """rounds=None : sans fin."""
    await check_same_rules(world.client)
    run = secrets.token_hex(2)  # pseudos neufs à chaque lancement
    bots = []
    for i in range(n_bots):
        profile = PROFILES[i % len(PROFILES)]
        bots.append(Bot(await world.signup(f"{profile.name}-{run}-{i + 1}"), profile))
    print(f"{n_bots} joueurs virtuels en jeu : " + ", ".join(b.player.name for b in bots))

    turn = 0
    while rounds is None or turn < rounds:
        turn += 1
        r = await world.call(bots[0].player, "GET", "/auctions", params={"limit": 100})
        auctions = r.json() if r.is_success else []
        before = world.done.copy()
        for bot in world.rng.sample(bots, len(bots)):
            await bot.act(world, auctions)
        new = world.done - before
        if new:
            print(f"tour {turn} : " + ", ".join(f"{n} {label}" for label, n in new.items()))
        await asyncio.sleep(every)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8001")
    parser.add_argument("--bots", type=int, default=5)
    parser.add_argument("--every", type=float, default=5, help="secondes entre deux tours")
    args = parser.parse_args()
    if args.bots < 1 or args.every <= 0:
        parser.error("--bots et --every doivent être positifs")

    async def run() -> None:
        async with httpx.AsyncClient(base_url=args.url, timeout=10) as client:
            await play(LiveWorld(client, random.Random()), args.bots, args.every)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nBots arrêtés.")
    except httpx.TransportError:
        sys.exit(f"Serveur injoignable sur {args.url} : est-il lancé ?")


if __name__ == "__main__":
    main()
