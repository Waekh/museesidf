"""CLI d'administration : collectes manuelles, nettoyage, alertes.

Exemples :
    python -m app.cli collect all
    python -m app.cli collect openagenda
    python -m app.cli cleanup
    python -m app.cli send-alerts weekly
"""

import argparse
import asyncio
import logging

from app.collectors.culture_gouv import sync_museums
from app.collectors.openagenda import OpenAgendaCollector
from app.collectors.paris_opendata import ParisOpenDataCollector
from app.collectors.scraper import run_all_scrapers
from app.services.scheduler import cleanup_old_events, send_alerts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="Administration Musées IDF"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Lancer une collecte immédiatement")
    collect.add_argument(
        "source",
        choices=["openagenda", "paris", "scrapers", "museums", "all"],
        help="Source à collecter (museums = référentiel data.culture.gouv.fr)",
    )

    sub.add_parser("cleanup", help="Purger événements passés et abonnements inactifs")

    alerts = sub.add_parser("send-alerts", help="Envoyer les alertes email maintenant")
    alerts.add_argument("frequency", choices=["daily", "weekly"])

    return parser


async def run(args: argparse.Namespace) -> None:
    if args.command == "collect":
        if args.source in ("museums", "all"):
            await sync_museums()
        if args.source in ("openagenda", "all"):
            await OpenAgendaCollector().run()
        if args.source in ("paris", "all"):
            await ParisOpenDataCollector().run()
        if args.source in ("scrapers", "all"):
            await run_all_scrapers()
    elif args.command == "cleanup":
        await cleanup_old_events()
    elif args.command == "send-alerts":
        await send_alerts(args.frequency)


def main() -> None:
    asyncio.run(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
