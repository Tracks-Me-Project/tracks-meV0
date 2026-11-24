from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from tracks.models import CollectionItem, Track


def add_copies(session: Session, account_id: int, recording_mbid: str, n: int) -> None:
    stmt = insert(CollectionItem).values(
        account_id=account_id, recording_mbid=recording_mbid, quantity=n
    )
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["account_id", "recording_mbid"],
            set_={"quantity": CollectionItem.quantity + n},
        )
    )


def take_copy(session: Session, account_id: int, recording_mbid: str) -> bool:
    """Retire un exemplaire ; False si le joueur n'en a aucun. Deux ordres SQL atomiques, pour
    ne pas écraser un ajout simultané (la quantité ne peut pas valoir 0 : la ligne disparaît)."""
    key = (CollectionItem.account_id == account_id, CollectionItem.recording_mbid == recording_mbid)
    if session.execute(delete(CollectionItem).where(*key, CollectionItem.quantity == 1)).rowcount:
        return True
    updated = session.execute(
        update(CollectionItem)
        .where(*key, CollectionItem.quantity > 1)
        .values(quantity=CollectionItem.quantity - 1)
    )
    return updated.rowcount == 1


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
