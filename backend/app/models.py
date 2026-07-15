import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# JSONB sur PostgreSQL, JSON générique ailleurs (tests SQLite)
JsonVariant = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Museum(Base):
    __tablename__ = "museums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(255), unique=True)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    department: Mapped[str | None] = mapped_column(String(50))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    website_url: Mapped[str | None] = mapped_column(String(500))
    openagenda_uid: Mapped[str | None] = mapped_column(String(100))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    events: Mapped[list["Event"]] = relationship(back_populates="museum")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_events_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    museum_id: Mapped[int | None] = mapped_column(ForeignKey("museums.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str | None] = mapped_column(String(50), index=True)
    date_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_end: Mapped[date | None] = mapped_column(Date)
    time_start: Mapped[time | None] = mapped_column(Time)
    time_end: Mapped[time | None] = mapped_column(Time)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=False)
    price_info: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(500))
    event_url: Mapped[str | None] = mapped_column(String(500))
    audience: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JsonVariant)
    # Repli d'image : miniature (og:image) de la page source, récupérée à la
    # demande. og_image_checked évite de re-tenter un fetch qui a déjà échoué.
    og_image_url: Mapped[str | None] = mapped_column(String(500))
    og_image_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Déduplication cross-sources
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    museum: Mapped[Museum | None] = relationship(back_populates="events")


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[dict | None] = mapped_column(JsonVariant)
    frequency: Mapped[str] = mapped_column(String(20), default="weekly")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid.uuid4, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
