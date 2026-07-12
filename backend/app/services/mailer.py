"""Envoi des emails d'alerte via SMTP (aiosmtplib).

En développement (SMTP_USER vide), les envois sont journalisés et ignorés.
"""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings
from app.models import AlertSubscription, Event

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str) -> bool:
    settings = get_settings()
    if not settings.smtp_user:
        logger.info("SMTP non configuré — email '%s' pour %s non envoyé", subject, to)
        return False

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content("Votre client mail ne supporte pas le HTML.")
    message.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        return True
    except aiosmtplib.SMTPException as exc:
        logger.error("Envoi email à %s en échec : %s", to, exc)
        return False


def unsubscribe_url(subscription: AlertSubscription) -> str:
    settings = get_settings()
    return f"{settings.api_url}/api/alerts/unsubscribe/{subscription.token}"


async def send_confirmation(subscription: AlertSubscription) -> bool:
    html = f"""
    <h2>Bienvenue sur Musées d'Île-de-France !</h2>
    <p>Votre alerte <strong>{subscription.frequency}</strong> est bien enregistrée
    pour l'adresse {subscription.email}.</p>
    <p>Vous recevrez les nouveaux événements correspondant à vos filtres.</p>
    <p><a href="{unsubscribe_url(subscription)}">Se désinscrire</a></p>
    """
    return await send_email(
        subscription.email, "Confirmation de votre alerte Musées IDF", html
    )


async def send_event_alert(subscription: AlertSubscription, events: list[Event]) -> bool:
    items = "".join(
        f"""<li>
            <strong>{e.title}</strong> — {e.event_type or 'événement'}
            {f"au {e.museum.name}" if e.museum else ""}
            (à partir du {e.date_start.strftime('%d/%m/%Y')})
            {f'<br><a href="{e.event_url}">En savoir plus</a>' if e.event_url else ""}
        </li>"""
        for e in events
    )
    html = f"""
    <h2>Nouveaux événements dans les musées d'Île-de-France</h2>
    <ul>{items}</ul>
    <p><a href="{unsubscribe_url(subscription)}">Se désinscrire</a></p>
    """
    return await send_email(
        subscription.email,
        f"{len(events)} nouveau(x) événement(s) dans les musées IDF",
        html,
    )
