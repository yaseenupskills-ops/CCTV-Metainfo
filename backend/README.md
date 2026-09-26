# CCTV Forensic Analyzer — Backend

FastAPI backend for the CCTV Forensic Analyzer.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env   # then edit values
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Layout

```
app/
├── api/          # FastAPI routers and dependencies
├── core/         # config, enums, security, logging, exceptions
├── db/           # engine, session, seed
├── models/       # SQLAlchemy ORM models
├── schemas/      # Pydantic request/response models
├── services/     # business logic (filled per phase)
├── workers/      # Celery tasks (Phase 16)
└── utils/        # shared helpers
alembic/          # migrations
tests/            # pytest suite (SQLite in-memory)
```

## Commands

| Task | Command |
|------|---------|
| Run tests | `python -m pytest` |
| Lint | `ruff check app tests` |
| Type check | `mypy app` |
| Create migration | `alembic revision --autogenerate -m "description"` |
| Apply migration | `alembic upgrade head` |
| Rollback | `alembic downgrade -1` |

## Phase Status

Phase 2 (backend skeleton + database) is complete. See `docs/DEVELOPMENT_ROADMAP.md`.
