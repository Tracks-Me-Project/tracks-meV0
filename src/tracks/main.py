import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from tracks.api import accounts, auctions, boosters, recycling
from tracks.clock import SystemClock
from tracks.config import get_rules, get_settings
from tracks.db import check_db, get_engine
from tracks.settler import settle_loop

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(_: FastAPI):
    interval = get_rules().auction.settle_interval_seconds
    task = asyncio.create_task(settle_loop(get_engine(), SystemClock(), interval))
    yield
    task.cancel()


app = FastAPI(title="tracks", lifespan=lifespan)
app.include_router(accounts.router)
app.include_router(boosters.router)
app.include_router(recycling.router)
app.include_router(auctions.router)


def get_db_check() -> Callable[[], None]:
    # Indirection pour que les tests puissent remplacer la base par une fausse.
    return check_db


@app.get("/health")
def health(db_check: Annotated[Callable[[], None], Depends(get_db_check)]) -> dict[str, str]:
    try:
        db_check()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="base indisponible") from exc
    return {"status": "ok"}


@app.get("/rules")
def rules() -> dict:
    # Le front affiche le mode actif (normal ou essai) et lira les durées et pourcentages ici.
    return {"file": get_settings().rules_path.name, "rules": get_rules().model_dump()}


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/app/")


# Monté en dernier : les routes de l'API sont testées avant. Dossier absent = erreur au démarrage.
app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="app")
