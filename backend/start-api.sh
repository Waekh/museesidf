#!/bin/sh
set -e

# Render fournit une URL postgresql:// ou postgres://, on la convertit en asyncpg
export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|^postgres://|postgresql+asyncpg://|; s|^postgresql://|postgresql+asyncpg://|')

# Applique les migrations Alembic
echo "Running Alembic migrations..."
alembic upgrade head

# Démarre l'API — Render injecte $PORT
echo "Starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
