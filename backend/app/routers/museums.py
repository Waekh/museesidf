from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event, Museum
from app.schemas import MuseumOut

router = APIRouter(prefix="/api/museums", tags=["museums"])


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("", response_model=list[MuseumOut])
async def list_museums(
    department: str | None = Query(None, description="Liste CSV, ex: Paris,Val-de-Marne"),
    event_type: str | None = Query(None, description="Liste CSV, ex: exposition,atelier"),
    date_from: date | None = None,
    date_to: date | None = None,
    audience: str | None = None,
    keyword: str | None = None,
    has_upcoming_events: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> list[MuseumOut]:
    """Liste des musées + nombre d'événements à venir correspondant aux filtres.

    Les filtres d'événements (type, période, public, mot-clé) rendent le
    compteur — et donc la carte — cohérents avec la vue liste : un musée
    n'est retenu (quand un filtre événement est actif) que s'il a au moins
    un événement correspondant.
    """
    if date_from is None:
        date_from = date.today()

    # Sous-requête : événements à venir correspondant aux filtres, par musée
    event_conditions = [
        Event.is_duplicate.is_(False),
        or_(
            Event.date_end >= date_from,
            and_(Event.date_end.is_(None), Event.date_start >= date_from),
            Event.is_permanent.is_(True),
        ),
    ]
    if date_to is not None:
        event_conditions.append(Event.date_start <= date_to)

    event_types = _split_csv(event_type)
    if event_types:
        event_conditions.append(Event.event_type.in_(event_types))
    if audience:
        event_conditions.append(Event.audience == audience)
    if keyword:
        pattern = f"%{keyword}%"
        event_conditions.append(
            or_(Event.title.ilike(pattern), Event.description.ilike(pattern))
        )

    upcoming = (
        select(Event.museum_id, func.count(Event.id).label("upcoming_count"))
        .where(*event_conditions)
        .group_by(Event.museum_id)
        .subquery()
    )

    query = (
        select(Museum, func.coalesce(upcoming.c.upcoming_count, 0))
        .outerjoin(upcoming, Museum.id == upcoming.c.museum_id)
        .where(Museum.is_active.is_(True))
        .order_by(Museum.name)
    )

    departments = _split_csv(department)
    if departments:
        query = query.where(Museum.department.in_(departments))

    # Si un filtre d'événement est actif, ne montrer que les musées concernés
    event_filter_active = bool(event_types or audience or keyword or date_to)
    if has_upcoming_events or event_filter_active:
        query = query.where(func.coalesce(upcoming.c.upcoming_count, 0) > 0)

    rows = (await db.execute(query)).all()
    museums = []
    for museum, count in rows:
        out = MuseumOut.model_validate(museum)
        out.upcoming_events_count = count
        museums.append(out)
    return museums
