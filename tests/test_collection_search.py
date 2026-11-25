import pytest

from tracks import accounts, collection
from tracks.clock import SystemClock
from tracks.models import Track

TRACKS = [  # (id, titre, artiste, album)
    ("r1", "Little Cloud", "Steve Hackett", "Budapest"),
    ("r2", "Earth Sign", "Andy McKee", "One World"),
    ("r3", "100% Pure", "Beyoncé", "B_Sides"),
]


@pytest.fixture
def owner(session):
    for mbid, title, artist, album in TRACKS:
        session.add(Track(recording_mbid=mbid, title=title, artist=artist, album=album,
                          album_mbid="a", artist_mbid="x", album_year=2000))
    account, _ = accounts.create_account(session, "chercheur", SystemClock())
    for mbid, *_ in TRACKS:
        collection.add_copies(session, account.id, mbid, 1)
    return account


def _search(session, account, query):
    rows = collection.list_collection(session, account.id, 50, 0, query)
    return sorted(t.recording_mbid for t, _ in rows)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", ["r1", "r2", "r3"]),
        ("cloud", ["r1"]),  # titre, casse ignorée
        ("MCKEE", ["r2"]),  # artiste
        ("one wor", ["r2"]),  # album
        ("%", ["r3"]),  # texte, pas joker
        ("_", ["r3"]),
        ("beyonce", []),  # les accents comptent
        ("introuvable", []),
    ],
)
def test_search(session, owner, query, expected):
    assert _search(session, owner, query) == expected


def test_search_only_own_collection(session, owner):
    other, _ = accounts.create_account(session, "autre", SystemClock())
    assert _search(session, other, "cloud") == []
