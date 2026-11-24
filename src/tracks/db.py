"""Accès à Postgres."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from tracks.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def check_db() -> None:
    """Lève une exception si la base ne répond pas."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))


def get_session() -> Iterator[Session]:
    """Une transaction par requête : commit si tout va bien, annulation sinon."""
    with Session(get_engine()) as session, session.begin():
        yield session
