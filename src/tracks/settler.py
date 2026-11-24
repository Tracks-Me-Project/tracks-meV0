"""Petite boucle serveur qui règle les enchères échues, même si personne ne les consulte."""

import asyncio
import logging

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from tracks import auctions
from tracks.clock import Clock

log = logging.getLogger(__name__)


def settle_once(engine: Engine, clock: Clock) -> int:
    with Session(engine) as session:
        return auctions.settle_due(session, clock)


async def settle_loop(engine: Engine, clock: Clock, interval_seconds: int) -> None:
    while True:
        try:
            await asyncio.to_thread(settle_once, engine, clock)
        except Exception:  # la boucle ne doit jamais s'arrêter
            log.exception("règlement des enchères échoué")
        await asyncio.sleep(interval_seconds)
