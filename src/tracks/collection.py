from sqlalchemy import select
from sqlalchemy.orm import Session

from tracks.models import CollectionItem, Track


def list_collection(
    session: Session, account_id: int, limit: int, offset: int
) -> list[tuple[Track, int]]:
    rows = session.execute(
        select(Track, CollectionItem.quantity)
        .join(CollectionItem, CollectionItem.recording_mbid == Track.recording_mbid)
        .where(CollectionItem.account_id == account_id)
        .order_by(Track.artist, Track.album, Track.title, Track.recording_mbid)
        .limit(limit)
        .offset(offset)
    )
    return [(t, q) for t, q in rows]
