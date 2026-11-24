"""Import du catalogue (CSV MusicBrainz) : une carte par recording_mbid."""

import csv
import sys
from itertools import batched
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from tracks.config import get_settings
from tracks.db import get_engine
from tracks.models import Track


def _row(r: dict[str, str]) -> dict:
    return {
        "recording_mbid": r["recording_mbid"],
        "title": r["titre"],
        "album_mbid": r["album_mbid"],
        "album": r["album"],
        "album_year": int(r["annee_album"]) if r["annee_album"] else None,
        "artist_mbid": r["artiste_mbid"],
        "artist": r["artiste"],
    }


def import_catalogue(session: Session, path: Path) -> int:
    """Renvoie le nombre de titres ajoutés. Relançable : les doublons sont ignorés
    (le premier rencontré gagne)."""
    added = 0
    with path.open(encoding="utf-8", newline="") as f:
        for chunk in batched(csv.DictReader(f), 1000):
            stmt = (
                insert(Track)
                .values([_row(r) for r in chunk])
                .on_conflict_do_nothing()
                .returning(Track.recording_mbid)
            )
            added += len(session.execute(stmt).all())
    return added


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else get_settings().catalogue_path
    with Session(get_engine()) as s, s.begin():
        print(f"{import_catalogue(s, path)} titres ajoutés")
