from fastapi.testclient import TestClient

from tracks.main import app, get_db_check


def _client(check) -> TestClient:
    app.dependency_overrides[get_db_check] = lambda: check
    return TestClient(app)


def test_health_ok():
    assert _client(lambda: None).get("/health").json() == {"status": "ok"}
    app.dependency_overrides.clear()


def test_health_db_down():
    def down() -> None:
        raise ConnectionError

    assert _client(down).get("/health").status_code == 503
    app.dependency_overrides.clear()
