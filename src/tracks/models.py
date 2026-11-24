"""Tables. Le journal (ledger) est en ajout seul : jamais de UPDATE ni de DELETE dessus."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("balance_available >= 0", name="available_non_negative"),
        CheckConstraint("balance_locked >= 0", name="locked_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # Cache du solde : toujours égal à la somme du journal (vérifié par un test).
    balance_available: Mapped[int] = mapped_column(default=0)
    balance_locked: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerEntry(Base):
    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    available_delta: Mapped[int]
    locked_delta: Mapped[int]
    ref: Mapped[str | None] = mapped_column(String(100))  # ex. "auction:12"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Track(Base):
    """Une carte = un recording_mbid."""

    __tablename__ = "tracks"

    recording_mbid: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(400))
    album_mbid: Mapped[str] = mapped_column(String(36))
    album: Mapped[str] = mapped_column(String(300))
    album_year: Mapped[int | None]
    artist_mbid: Mapped[str] = mapped_column(String(36))
    artist: Mapped[str] = mapped_column(String(200))


class CollectionItem(Base):
    """Quantité d'exemplaires d'un titre ; quantity - 1 = doublons recyclables."""

    __tablename__ = "collection"
    __table_args__ = (CheckConstraint("quantity >= 1", name="quantity_positive"),)

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    recording_mbid: Mapped[str] = mapped_column(
        ForeignKey("tracks.recording_mbid"), primary_key=True
    )
    quantity: Mapped[int]


class BoosterState(Base):
    __tablename__ = "booster_state"
    __table_args__ = (CheckConstraint("stock >= 0", name="stock_non_negative"),)

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    stock: Mapped[int]
    last_credited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
