#!/usr/bin/env sh
# Container entrypoint: apply migrations, seed idempotently, then run the
# container command (uvicorn for the API, celery for the worker).
set -e

echo "[entrypoint] Applying database migrations..."
alembic upgrade head

echo "[entrypoint] Seeding initial data..."
python -m app.db.seed

exec "$@"
