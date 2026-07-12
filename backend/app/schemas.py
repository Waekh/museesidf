import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MuseumLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str | None = None
    city: str | None = None
    department: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    website_url: str | None = None
    logo_url: str | None = None


class MuseumOut(MuseumLite):
    address: str | None = None
    postal_code: str | None = None
    openagenda_uid: str | None = None
    is_active: bool = True
    upcoming_events_count: int = 0


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    museum_id: int | None = None
    source: str
    title: str
    description: str | None = None
    event_type: str | None = None
    date_start: date
    date_end: date | None = None
    time_start: time | None = None
    time_end: time | None = None
    is_permanent: bool = False
    price_info: str | None = None
    image_url: str | None = None
    event_url: str | None = None
    audience: str | None = None
    museum: MuseumLite | None = None


class EventListOut(BaseModel):
    total: int
    page: int
    page_size: int
    events: list[EventOut]


class StatsOut(BaseModel):
    total_museums: int
    total_upcoming_events: int
    by_department: dict[str, int]
    by_event_type: dict[str, int]


class AlertFilters(BaseModel):
    departments: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    audience: str | None = None
    museum_ids: list[int] = Field(default_factory=list)


class AlertCreate(BaseModel):
    email: EmailStr
    filters: AlertFilters = Field(default_factory=AlertFilters)
    frequency: str = Field(default="weekly", pattern="^(daily|weekly)$")


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    filters: dict | None = None
    frequency: str
    is_active: bool
    token: uuid.UUID
    created_at: datetime
