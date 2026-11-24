from pathlib import Path

from sqlalchemy import func, select

from tracks.catalogue import import_catalogue
from tracks.models import Track

HEADER = "recording_mbid,titre,album_mbid,album,annee_album,disque,rang,artiste_mbid,artiste\n"


def _csv(tmp_path: Path, *rows: str) -> Path:
    p = tmp_path / "c.csv"
    p.write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def test_import_dedups_and_is_rerunnable(session, tmp_path):
    p = _csv(
        tmp_path,
        "r1,Un,a1,Album,2004,1,1,x1,Artiste",
        'r2,"Deux, virgule",a1,Album,,1,2,x1,Artiste',
        "r1,Un,a1,Album,2004,1,1,x1,Artiste",  # doublon exact
        "r2,Deux autre album,a2,Autre,1999,1,1,x2,Autre artiste",  # même titre, autre album
    )
    assert import_catalogue(session, p) == 2
    assert import_catalogue(session, p) == 0
    session.commit()
    assert session.scalar(select(func.count()).select_from(Track)) == 2
    r2 = session.get(Track, "r2")
    assert (r2.title, r2.album_year) == ("Deux, virgule", None)  # première ligne gardée
