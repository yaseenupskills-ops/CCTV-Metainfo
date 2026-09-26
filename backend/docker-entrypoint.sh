#!/usr/bin/env sh
# Container entrypoint: apply migrations, seed bootstrap data only when it is
# missing, then run the container command (uvicorn for the API, celery for the
# worker).
set -e

echo "[entrypoint] Applying database migrations..."
alembic upgrade head

# --if-absent makes this a no-op once an admin exists, so a container restart
# can never reset a password an operator has since changed. The admin password
# is never printed; a generated one lands in storage/.admin_credentials.
echo "[entrypoint] Ensuring bootstrap data..."
python -m app.db.seed --if-absent

exec "$@"
