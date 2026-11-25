"""La transaction doit être validée AVANT la réponse : jamais de « succès » non enregistré."""

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from tracks import db
from tracks.main import app


def test_failed_commit_is_not_reported_as_success(engine, monkeypatch):
    monkeypatch.setattr(db, "get_engine", lambda: engine)  # le vrai get_session, base de test

    def fail(_session):
        raise RuntimeError("commit impossible")

    event.listen(Session, "before_commit", fail)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.post("/accounts", json={"name": "fantome"}).status_code == 500
    finally:
        event.remove(Session, "before_commit", fail)
