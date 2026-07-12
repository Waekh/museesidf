from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Event
from app.schemas import EventListOut, EventOut

router = APIRouter(prefix="/api/events", tags=["events"])


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("", response_model=EventListOut)
async def list_events(
    date_from: date | None = Query(None, description="Défaut : aujourd'hui"),
    date_to: date | None = None,
    department: str | None = Query(None, description="Liste CSV, ex: Paris,Hauts-de-Seine"),
    event_type: str | None = Query(None, description="Liste CSV, ex: exposition,atelier"),
    museum_id: int | None = None,
    keyword: str | None = Query(None, description="Recherche dans titre + description"),
    audience: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> EventListOut:
    from app.models import Museum

    if date_from is None:
        date_from = date.today()

    query = select(Event).where(Event.is_duplicate.is_(False))

    # Événement encore en cours OU commençant après date_from
    query = query.where(
        or_(
            Event.date_end >= date_from,
            and_(Event.date_end.is_(None), Event.date_start >= date_from),
            Event.is_permanent.is_(True),
        )
    )
    if date_to is not None:
        query = query.where(Event.date_start <= date_to)

    departments = _split_csv(department)
    if departments:
        query = query.join(Museum, Event.museum_id == Museum.id).where(
            Museum.department.in_(departments)
        )

    event_types = _split_csv(event_type)
    if event_types:
        query = query.where(Event.event_type.in_(event_types))

    if museum_id is not None:
        query = query.where(Event.museum_id == museum_id)

    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(Event.title.ilike(pattern), Event.description.ilike(pattern))
        )

    if audience:
        query = query.where(Event.audience == audience)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()

    result = await db.execute(
        query.options(selectinload(Event.museum))
        .order_by(Event.date_start, Event.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    events = result.scalars().all()

    return EventListOut(
        total=total,
        page=page,
        page_size=page_size,
        events=[EventOut.model_validate(e) for e in events],
    )


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)) -> EventOut:
    result = await db.execute(
        select(Event).options(selectinload(Event.museum)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return EventOut.model_validate(event)
