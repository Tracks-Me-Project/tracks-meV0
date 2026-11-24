"""Tests sur un vrai Postgres (docker compose up -d) : les verrous ne se simulent pas."""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from tracks.config import get_settings

TEST_URL = os.environ.get(
    "TRACKS_TEST_DATABASE_URL", "postgresql+psycopg://tracks:tracks@localhost:5442/tracks_test"
)


@pytest.fixture(scope="session")
def engine():
    admin = create_engine(
        make_url(TEST_URL).set(database=make_url(get_settings().database_url).database),
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as conn:
        name = make_url(TEST_URL).database
        if not conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}):
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    eng = create_engine(TEST_URL)
    with eng.begin() as conn:  # base propre, puis le vrai schéma via les migrations
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(cfg, "head")
    return eng


@pytest.fixture
def session(engine) -> Iterator[Session]:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE ledger, accounts RESTART IDENTITY CASCADE"))
    with Session(engine) as s:
        yield s
