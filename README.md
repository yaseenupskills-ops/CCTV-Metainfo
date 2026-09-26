# CCTV Forensic Analyzer

A secure digital video-forensics platform that allows investigators to upload CCTV footage, preserve its integrity, extract technical metadata, calculate cryptographic hashes, analyze video structure and frames, compare original and suspected copies, identify potential technical anomalies, and generate forensic reports.

> **Important:** The system never claims a video is definitely "fake" or "tampered" based only on automated analysis. It reports **potential indicators** that require expert interpretation.

## Core Workflow

```
UPLOAD EVIDENCE → PRESERVE ORIGINAL → CALCULATE HASH → EXTRACT METADATA
→ VIDEO STRUCTURE ANALYSIS → FRAME ANALYSIS → ANOMALY DETECTION
→ OPTIONAL VIDEO COMPARISON → TIMELINE VISUALIZATION
→ FORENSIC REPORT → AUDIT LOG
```

## Technology Stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Recharts, Lucide React
**Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Celery, Redis
**Video:** FFmpeg, FFprobe, OpenCV, NumPy
**Database:** PostgreSQL 16
**Reporting:** ReportLab

## Documentation

| Document | Description |
|----------|-------------|
| [Project Plan](docs/PROJECT_PLAN.md) | Goals, timeline, phases, risks |
| [Architecture](docs/ARCHITECTURE.md) | System design, structure, DB schema |
| [Setup Guide](docs/SETUP_GUIDE.md) | Windows installation instructions |
| [Deployment Guide](docs/DEPLOYMENT.md) | Docker Compose deployment, persistence, backup |
| [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md) | Phase-by-phase implementation tasks |
| [Forensic Methodology](docs/FORENSIC_METHODOLOGY.md) | Analysis methods and limitations |
| [Security](docs/SECURITY.md) | Threat model and hardening |

## Quick Start (Windows)

Prerequisites: Python 3.11+, Node.js 18+, PostgreSQL 16, FFmpeg. See [Setup Guide](docs/SETUP_GUIDE.md).

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env   # then edit .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

- Backend API docs: http://localhost:8000/docs
- Frontend app: http://localhost:5173

## Docker Deployment

The whole stack (PostgreSQL, Redis, backend, worker, nginx-fronted frontend) can be
run with Docker Compose — no local Python/Node/FFmpeg/PostgreSQL required.

```powershell
Copy-Item .env.example .env   # then set JWT_SECRET
docker compose up --build -d
```

- Frontend: http://localhost  (configurable via `WEB_PORT`)
- API docs: http://localhost:8000/docs

See [Deployment Guide](docs/DEPLOYMENT.md) for environment variables, data
persistence, backup/restore, and production notes.

## Project Structure

```
CCTV MetaInfo/
├── docs/          # All project documentation
├── backend/       # FastAPI application (Dockerfile + Celery worker image)
├── frontend/      # React application (Dockerfile + nginx config)
├── storage/       # Evidence files (git-ignored)
│   ├── evidence/originals/    # Immutable original uploads
│   ├── evidence/processed/    # Working copies for analysis
│   ├── evidence/quarantine/   # Failed validation
│   └── reports/               # Generated PDFs
├── scripts/       # PowerShell helper scripts
└── docker-compose.yml  # Full-stack containerized deployment
```

## Development Status

- **Phase 1** (repository setup + documentation) — complete
- **Phase 2** (backend skeleton + database) — complete: FastAPI app boots, 9-table schema via Alembic, 10 tests passing, ruff/mypy clean
- **Phase 3** (evidence upload + secure storage) — complete: validated upload (extension/MIME/size/path-traversal), read-only original storage, quarantine, audit logging; 29 tests passing
- **Phase 4** (SHA-256/SHA-512 hashing) — complete: hashes computed at upload + recalculation endpoint, verified against `Get-FileHash`; 40 tests passing, ruff/mypy clean
- **Phase 5** (FFprobe metadata extraction) — complete: FFmpeg 9.0 installed, normalized metadata (codecs/dimensions/fps/duration) + keyframe structure extraction via FFprobe; 55 tests passing, ruff/mypy clean
- **Phase 6** (evidence list/detail/analysis/delete) — complete: paginated + filtered listing, detail with metadata & analysis history, soft delete with audit trail; 71 tests passing, ruff/mypy clean
- **Phase 7** (React dashboard) — complete: dark forensic dashboard, protected routing, dashboard with real API data, evidence detail page; 76 backend + 10 frontend tests, lint + build clean
- **Phase 8** (OpenCV frame extraction) — complete: streaming frame sampling at 1/2/5 fps with pHash + stats per frame, no bulk image storage; 93 backend tests, ruff/mypy clean
- **Phase 9** (scene/frame difference analysis) — complete: MAD, histogram, SSIM, pHash distance methods; configurable threshold; "Potential anomaly" events with severity; 107 backend tests, ruff/mypy clean
- **Phase 10** (original vs suspected comparison) — complete: field-by-field hash + metadata comparison with MATCH/DIFFERENCE/NOT_AVAILABLE verdicts, POST/GET comparison API, audit logged; 125 backend tests, ruff/mypy clean, live HTTP smoke test verified
- **Phase 11** (timeline visualization) — complete: `GET /evidence/{id}/timeline` builds normal segments + "Potential anomaly" markers from scene-change results; interactive timeline UI with severity-colored markers, click-for-detail drawer, evidence selector, and run/poll analysis; 129 backend tests + 13 frontend tests, lint + build clean, live HTTP smoke test verified
- **Phase 12** (anomaly scoring) — complete: explainable "Anomaly Indicator Score" (0–100) from 6 weighted factors (metadata inconsistency, duration difference, frame discontinuity, encoding difference, unnatural frame-diff cluster, single scene changes) with reasons; Anomaly rows persisted per scene-change event; score recomputed when a comparison is created; `GET /evidence/{id}/anomaly-score`; ScoreGauge UI with factor breakdown; 158 backend tests + 17 frontend tests, lint + build clean, live HTTP smoke test verified
- **Phase 13** (PDF forensic reports) — complete: ReportLab PDF with 13 sections that clearly separate OBSERVED FACTS from AUTOMATED INTERPRETATIONS and reserve space for INVESTIGATOR CONCLUSIONS; create/list/download report API with audit logging; Reports UI page with case/evidence selection and authenticated PDF download
- **Phase 14** (authentication + RBAC) — complete: JWT auth with admin/investigator/viewer roles, bcrypt password hashing, protected endpoints via role dependencies, login UI with token storage, RBAC test matrix
- **Phase 15** (audit logging) — complete: append-only audit trail with immutability rules (UPDATE/DELETE blocked), audit recording on upload/hash/metadata/analyze/comparison/report/case/user/login events, admin `GET /audit-logs` with filters (user/entity/action/date) + pagination, Audit Logs UI page with filter + table; 199 backend tests + 20 frontend tests, ruff/mypy clean, lint + build clean
- **Phase 16** (background workers) — complete: analysis + metadata extraction run as Celery tasks with QUEUED→PROCESSING→COMPLETED/FAILED transitions, frontend auto-polls for completion, eager-mode task tests; 209 backend tests, ruff/mypy clean
- **Phase 17** (testing + security hardening) — complete: sample-video family fixtures (trimmed/re-encoded/diff-res/diff-fps/metadata-modified/joined), expanded metadata + comparison integration tests, login rate limiting (429), JSON body-size cap (413), CORS tightening, strict Pydantic schemas, no-path-leak + SQL-injection safety tests, coverage threshold configured; 246 backend tests at ~95% coverage + 20 frontend tests, ruff/mypy clean, lint + build clean
- **Phase 18** (Docker + deployment) — complete: backend image (FFmpeg + migrations + seed entrypoint), Celery worker on the same image, multi-stage frontend image with nginx reverse proxy, `docker-compose.yml` (postgres/redis/backend/worker/frontend) with healthchecks + persistent volumes, deployment + backup documentation

See [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md) for current phase and task list.

## Testing

```powershell
cd backend && pytest          # backend unit + API tests
cd frontend && npm run test   # frontend component/integration tests
cd frontend && npm run lint   # lint
cd frontend && npm run build  # type-check + production build
```

## Status

This is a **portfolio / demonstration project**. It is published for review and
learning purposes. It has not been through an independent security audit, and it
must not be treated as production-ready forensic tooling or relied on for
evidence in a real proceeding.

## License

No license has been granted. The code is published for viewing and portfolio
review only. All rights reserved by the author. If you want to reuse any part
of it, get in touch first.
