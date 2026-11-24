from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from tracks.api import accounts, boosters
from tracks.db import check_db

app = FastAPI(title="tracks")
app.include_router(accounts.router)
app.include_router(boosters.router)


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
