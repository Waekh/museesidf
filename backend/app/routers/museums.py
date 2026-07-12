from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event, Museum
from app.schemas import MuseumOut

router = APIRouter(prefix="/api/museums", tags=["museums"])


@router.get("", response_model=list[MuseumOut])
async def list_museums(
    department: str | None = None,
    has_upcoming_events: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> list[MuseumOut]:
    upcoming = (
        select(Event.museum_id, func.count(Event.id).label("upcoming_count"))
        .where(
            Event.date_start >= date.today(),
            Event.is_duplicate.is_(False),
        )
        .group_by(Event.museum_id)
        .subquery()
    )

    query = (
        select(Museum, func.coalesce(upcoming.c.upcoming_count, 0))
        .outerjoin(upcoming, Museum.id == upcoming.c.museum_id)
        .where(Museum.is_active.is_(True))
        .order_by(Museum.name)
    )
    if department:
        query = query.where(Museum.department == department)
    if has_upcoming_events:
        query = query.where(func.coalesce(upcoming.c.upcoming_count, 0) > 0)

    rows = (await db.execute(query)).all()
    museums = []
    for museum, count in rows:
        out = MuseumOut.model_validate(museum)
        out.upcoming_events_count = count
        museums.append(out)
    return museums
