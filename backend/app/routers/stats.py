from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event, Museum
from app.schemas import StatsOut

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsOut:
    today = date.today()
    upcoming = (Event.date_start >= today) & Event.is_duplicate.is_(False)

    total_museums = (
        await db.execute(
            select(func.count(Museum.id)).where(Museum.is_active.is_(True))
        )
    ).scalar_one()

    total_events = (
        await db.execute(select(func.count(Event.id)).where(upcoming))
    ).scalar_one()

    by_department_rows = (
        await db.execute(
            select(Museum.department, func.count(Event.id))
            .join(Event, Event.museum_id == Museum.id)
            .where(upcoming, Museum.department.is_not(None))
            .group_by(Museum.department)
        )
    ).all()

    by_type_rows = (
        await db.execute(
            select(Event.event_type, func.count(Event.id))
            .where(upcoming, Event.event_type.is_not(None))
            .group_by(Event.event_type)
        )
    ).all()

    return StatsOut(
        total_museums=total_museums,
        total_upcoming_events=total_events,
        by_department={dept: count for dept, count in by_department_rows},
        by_event_type={etype: count for etype, count in by_type_rows},
    )
