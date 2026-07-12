import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AlertSubscription
from app.schemas import AlertCreate, AlertOut
from app.services import mailer

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    payload: AlertCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AlertOut:
    # Réactive une souscription existante pour le même email plutôt que dupliquer
    existing = (
        await db.execute(
            select(AlertSubscription).where(AlertSubscription.email == payload.email)
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.filters = payload.filters.model_dump()
        existing.frequency = payload.frequency
        existing.is_active = True
        subscription = existing
    else:
        subscription = AlertSubscription(
            email=payload.email,
            filters=payload.filters.model_dump(),
            frequency=payload.frequency,
        )
        db.add(subscription)

    await db.commit()
    await db.refresh(subscription)

    background_tasks.add_task(mailer.send_confirmation, subscription)
    return AlertOut.model_validate(subscription)


async def _deactivate(token: uuid.UUID, db: AsyncSession) -> AlertSubscription:
    subscription = (
        await db.execute(
            select(AlertSubscription).where(AlertSubscription.token == token)
        )
    ).scalar_one_or_none()
    if subscription is None:
        raise HTTPException(status_code=404, detail="Souscription introuvable")
    subscription.is_active = False
    await db.commit()
    return subscription


@router.delete("/{token}", status_code=204)
async def delete_alert(token: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await _deactivate(token, db)


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe(token: uuid.UUID, db: AsyncSession = Depends(get_db)) -> str:
    """Lien de désinscription cliquable depuis les emails."""
    await _deactivate(token, db)
    return (
        "<html><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
        "<h2>Désinscription confirmée</h2>"
        "<p>Vous ne recevrez plus d'alertes Musées d'Île-de-France.</p>"
        "</body></html>"
    )
