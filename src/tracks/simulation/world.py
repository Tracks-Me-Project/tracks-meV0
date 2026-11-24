"""Banc d'essai : l'application FastAPI tourne dans ce processus, appelée par HTTP (httpx, mode
ASGI) avec une horloge simulée. Les joueurs n'utilisent jamais le code métier directement."""

import asyncio
import random
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from tracks import collection
from tracks.api.boosters import get_rng
from tracks.api.deps import get_clock
from tracks.clock import FakeClock
from tracks.db import get_session
from tracks.main import app
from tracks.models import Track
from tracks.settler import settle_once

START = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Player:
    id: int
    name: str
    headers: dict[str, str]


class World:
    def __init__(self, engine: Engine, seed: int = 1) -> None:
        self.engine = engine
        self.clock = FakeClock(START)
        self.rng = random.Random(seed)
        self.stats: Counter[tuple[str, int]] = Counter()  # (route, code HTTP) -> nombre
        self.boosters_opened = 0
        self._names = 0
        self.injected_cards = 0  # cartes données par la préparation d'un scénario (pas par l'API)

    def _session(self) -> Iterator[Session]:
        # Même comportement que db.get_session, sur le moteur du banc d'essai.
        with Session(self.engine) as session, session.begin():
            yield session

    async def __aenter__(self) -> "World":
        app.dependency_overrides[get_session] = self._session
        app.dependency_overrides[get_clock] = lambda: self.clock
        app.dependency_overrides[get_rng] = lambda: self.rng
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)  # exception => 500
        self.client = httpx.AsyncClient(transport=transport, base_url="http://sim")
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()

    async def call(
        self, player: Player | None, method: str, path: str, **kwargs: object
    ) -> httpx.Response:
        headers = player.headers if player else kwargs.pop("headers", None)
        response = await self.client.request(method, path, headers=headers, **kwargs)
        route = re.sub(r"/-?\d+", "/{id}", path)
        self.stats[(f"{method} {route}", response.status_code)] += 1
        if route == "/boosters/open" and response.status_code == 200:
            self.boosters_opened += 1
        return response

    def unique_name(self, tag: str) -> str:
        self._names += 1
        return f"{tag}-{self._names}"

    async def signup(self, name: str) -> Player:
        r = await self.call(None, "POST", "/accounts", json={"name": name})
        assert r.status_code == 201, r.text
        data = r.json()
        return Player(data["id"], name, {"Authorization": f"Bearer {data['token']}"})

    async def settle(self) -> int:
        """Ce que fait la boucle serveur (non lancée ici : pas de cycle de vie ASGI)."""
        return await asyncio.to_thread(settle_once, self.engine, self.clock)

    def any_track(self) -> str:
        with Session(self.engine) as s:
            return s.scalars(select(Track.recording_mbid).order_by(Track.recording_mbid)).first()

    def give_cards(self, player: Player, recording_mbid: str, n: int) -> None:
        """Préparation d'un scénario (hors API) : donne n exemplaires, comptés au contrôle."""
        with Session(self.engine) as s, s.begin():
            collection.add_copies(s, player.id, recording_mbid, n)
        self.injected_cards += n

    @property
    def server_errors(self) -> int:
        return sum(n for (_, code), n in self.stats.items() if code >= 500)
