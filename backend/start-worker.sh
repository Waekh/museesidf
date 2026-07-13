#!/bin/sh
set -e

# Render fournit une URL postgresql:// ou postgres://, on la convertit en asyncpg
export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|^postgres://|postgresql+asyncpg://|; s|^postgresql://|postgresql+asyncpg://|')

echo "Starting worker..."
exec python -m app.worker
