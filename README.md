# Musées d'Île-de-France — Agrégateur d'événements

Application web full-stack qui agrège automatiquement les événements (expositions,
conférences, ateliers, visites guidées, nocturnes…) des musées d'Île-de-France, en
combinant plusieurs sources de données ouvertes et du scraping assisté par IA.

## Sources de données

| Source | Type | Priorité |
|---|---|---|
| [OpenAgenda](https://openagenda.com) (Paris Musées, IDF…) | API | haute |
| [Que Faire à Paris ?](https://opendata.paris.fr) | API (sans clé) | haute |
| [data.culture.gouv.fr](https://data.culture.gouv.fr) | Référentiel des ~200 Musées de France IDF | moyenne |
| Sites officiels (Louvre, Orsay, Pompidou, Versailles…) | Scraping + extraction Claude API | moyenne |

## Stack

- **Backend** : Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL
- **Scheduler** : APScheduler (collectes quotidiennes à 6h, alertes à 8h, nettoyage à 2h)
- **Scraping** : httpx + BeautifulSoup4 + Playwright (pages JS) + Claude API (`claude-sonnet-4-6`)
- **Frontend** : React 18, Vite, TailwindCSS, Leaflet (carte)
- **Tests** : pytest (backend, 59 tests) + Vitest (frontend, 13 tests) — CI GitHub Actions

## Démarrage rapide

```bash
cp .env.example .env      # renseigner OPENAGENDA_API_KEY et ANTHROPIC_API_KEY
docker compose up --build
```

- Frontend : http://localhost:5173
- API + docs interactives : http://localhost:8000/docs

Pour déclencher une collecte manuellement (sans attendre le cron de 6h) :

```bash
docker compose exec worker python -m app.cli collect all      # tout
docker compose exec worker python -m app.cli collect museums  # référentiel seul
docker compose exec worker python -m app.cli collect paris    # Que Faire à Paris ?
docker compose exec worker python -m app.cli cleanup          # purge manuelle
docker compose exec worker python -m app.cli send-alerts weekly
```

## Déploiement production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Le frontend est buildé (Vite) puis servi par **Nginx** sur le port 80, qui fait
aussi office de reverse proxy `/api` vers FastAPI. PostgreSQL n'est pas exposé
sur l'hôte et utilise un volume persistant dédié (`pgdata_prod`). Tous les
services redémarrent automatiquement (`restart: unless-stopped`).

## Architecture

```
backend/
├── alembic/                 # migrations (alembic upgrade head)
└── app/
    ├── main.py              # FastAPI + CORS
    ├── worker.py            # processus APScheduler (container `worker`)
    ├── models.py            # museums / events / alert_subscriptions
    ├── routers/             # /api/events, /api/museums, /api/stats, /api/alerts
    ├── collectors/
    │   ├── base.py          # BaseCollector : normalisation -> upsert -> dédup
    │   ├── openagenda.py
    │   ├── paris_opendata.py
    │   ├── culture_gouv.py  # référentiel musées
    │   └── scraper.py       # robots.txt + cache 24h + extraction Claude
    ├── services/
    │   ├── scheduler.py     # jobs cron
    │   ├── deduplicator.py  # Levenshtein >= 85% + même date + même musée
    │   └── mailer.py        # alertes email SMTP
    └── utils/normalizer.py  # dates, types, départements, hash stables

frontend/src/
├── pages/          # Home (liste/carte + filtres), EventDetail, Subscribe
├── components/     # EventCard, EventList, FilterPanel, MapView, AlertForm, Navbar
├── hooks/          # useEvents, useMuseums
└── api/client.ts
```

## API

| Endpoint | Description |
|---|---|
| `GET /api/events` | Liste filtrable : `date_from`, `date_to`, `department`, `event_type`, `museum_id`, `keyword`, `audience`, `page`, `page_size` |
| `GET /api/events/{id}` | Détail d'un événement |
| `GET /api/museums` | Musées + nombre d'événements à venir (`department`, `has_upcoming_events`) |
| `GET /api/stats` | Totaux + répartition par département et par type |
| `POST /api/alerts` | Créer une alerte email (`{email, filters, frequency}`) |
| `DELETE /api/alerts/{token}` | Désinscription par token |
| `GET /api/alerts/unsubscribe/{token}` | Lien de désinscription cliquable (emails) |

## Tests

```bash
# Backend
cd backend && pip install -r requirements-dev.txt && pytest

# Frontend
cd frontend && npm install && npm test
```

## Notes d'exploitation

- **Scraping responsable** : robots.txt respecté, User-Agent `MuseesIDF-Bot/1.0`,
  délai de 2 s entre requêtes, HTML mis en cache 24 h (limite aussi le coût Claude API).
- **Coût IA maîtrisé** : si une page publie des données structurées JSON-LD
  (schema.org, ex. Château de Versailles), elles sont parsées directement —
  Claude n'est appelé que pour les pages sans données structurées.
- **Playwright** : requis uniquement pour le Centre Pompidou (page JS). Décommenter
  `playwright install` dans `backend/Dockerfile` pour l'activer ; sinon la cible est
  ignorée proprement.
- **Fuseaux** : horodatages système en UTC ; dates/heures d'événements en Europe/Paris.
- **RGPD** : désinscription en un clic ; abonnements inactifs purgés après un an.
- **CI** : GitHub Actions exécute pytest, Vitest et le build TypeScript à chaque push.
