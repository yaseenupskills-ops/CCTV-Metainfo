# Deployment Guide (Docker)

Containerized deployment of the full stack: PostgreSQL, Redis, the FastAPI
backend, the Celery worker, and the nginx-served React frontend.

## Prerequisites

- Docker Engine 24+ with Docker Compose v2 (included in Docker Desktop).
- FFmpeg is **not** required on the host — it is installed inside the backend/worker images.

## Quick Start

```powershell
# 1. Copy the environment template and set a strong JWT_SECRET.
Copy-Item .env.example .env

# 2. Edit .env — at minimum set JWT_SECRET (see comment in the template).

# 3. Build and start the stack.
docker compose up --build -d

# 4. Check status.
docker compose ps

# 5. Open the app.
#    Frontend: http://localhost          (WEB_PORT, default 80)
#    API docs: http://localhost:8000/docs
```

The backend entrypoint automatically runs `alembic upgrade head` and seeds an
admin user before starting the API. The worker waits for the backend to become
healthy before consuming jobs.

### Seeded admin credentials

| Field    | Value               |
|----------|---------------------|
| Email    | `admin@cctv.local`  |
| Password | `ChangeMe123!`      |

> **Change this password immediately after first login.**

## Services

| Service   | Image source                | Exposed port | Healthcheck                       |
|-----------|-----------------------------|--------------|-----------------------------------|
| postgres  | `postgres:16-alpine`        | none         | `pg_isready`                      |
| redis     | `redis:7-alpine`            | none         | `redis-cli ping`                  |
| backend   | `./backend/Dockerfile`      | `8000`       | `GET /api/v1/health` via urllib   |
| worker    | `./backend/Dockerfile`      | none         | none (depends on backend health)  |
| frontend  | `./frontend/Dockerfile`     | `80`         | none                              |

## Environment Variables

Configured in `.env` at the repository root (compose interpolates them):

| Variable          | Default        | Description                                    |
|-------------------|----------------|------------------------------------------------|
| `POSTGRES_USER`   | `cctv_user`    | PostgreSQL user                                |
| `POSTGRES_PASSWORD` | `cctv_password` | PostgreSQL password (change in production)   |
| `POSTGRES_DB`     | `cctv_forensics` | Database name                                |
| `JWT_SECRET`      | *(required)*   | Long random string signing JWTs                |
| `WEB_PORT`        | `80`           | Host port for the frontend                     |
| `BACKEND_PORT`    | `8000`         | Host port for the API                          |

The backend's application settings (`STORAGE_PATH`, `DATABASE_URL`,
`CELERY_BROKER_URL`, `CORS_ORIGINS`, ...) are set directly in
`docker-compose.yml`; you generally do not need to change them.

## Data Persistence

Two Docker named volumes retain all state across container restarts:

| Volume               | Mount point                     | Contents                              |
|----------------------|---------------------------------|---------------------------------------|
| `cctv-forensics_pgdata`      | `/var/lib/postgresql/data`      | PostgreSQL database                  |
| `cctv-forensics_evidence-storage` | `/app/storage`            | Original evidence, working copies, quarantine, PDF reports |

Evidence files are stored read-only and never modified; the volume preserves
them for the chain of custody.

## Backup Strategy

Run from the repository root:

```powershell
# 1. Database dump (PostgreSQL).
docker compose exec -T postgres pg_dump -U "$env:POSTGRES_USER" -d "$env:POSTGRES_DB" > backup_$(Get-Date -Format yyyyMMdd).sql

# 2. Evidence files — copy the named volume to a tar archive.
docker run --rm -v cctv-forensics_evidence-storage:/data -v "${PWD}:/backup" alpine tar czf /backup/evidence_$(Get-Date -Format yyyyMMdd).tar.gz -C /data .
```

Restore:

```powershell
# Database restore (stops dependent services first).
docker compose stop backend worker
docker compose exec -T postgres psql -U "$env:POSTGRES_USER" -d "$env:POSTGRES_DB" < backup_20260101.sql
docker compose start backend worker
```

> Document the rotation: keep the evidence archive and DB dump together (they
> reference each other via UUIDs), and test a restore at least once.

## Common Operations

```powershell
# View logs
docker compose logs -f backend
docker compose logs -f worker

# Rebuild after code changes
docker compose up --build -d

# Stop / remove containers (volumes are kept by default)
docker compose down

# Wipe everything, including evidence + database volumes (irreversible)
docker compose down -v
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `JWT_SECRET: Set JWT_SECRET in your .env file` | `.env` missing or incomplete | `Copy-Item .env.example .env`, set `JWT_SECRET` |
| Upload fails with 413 | nginx or backend size limit | Raise `client_max_body_size` in `frontend/nginx.conf` and/or `MAX_UPLOAD_SIZE` |
| Analysis stays `QUEUED` | Worker not running / can't reach Redis | `docker compose logs worker`; ensure Redis is healthy |
| CORS errors in the browser | Origin not in `CORS_ORIGINS` | Add your origin to `CORS_ORIGINS` in `docker-compose.yml` |

## Production Notes

- Front this stack with a TLS-terminating reverse proxy (Traefik, nginx, Caddy)
  and force HTTPS. The nginx container binds plain HTTP on `WEB_PORT`.
- Use strong `POSTGRES_PASSWORD` and `JWT_SECRET`; never ship the defaults.
- Enable audit-log retention and off-site backups per your organisation policy.
- See `docs/SECURITY.md` for the full hardening and known-limitations list.
