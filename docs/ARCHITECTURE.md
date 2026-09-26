# CCTV Forensic Analyzer — Architecture

## 1. System Overview

A client-server application with a React SPA frontend and a modular FastAPI backend. Background processing uses Celery + Redis for long-running video analysis. PostgreSQL stores all metadata, analysis results, anomalies, reports, and audit logs. Original evidence files are stored read-only on disk; all analysis operates on working copies.

```
┌──────────────────────────────┐        ┌────────────────────────────────────┐
│         Frontend (React)     │        │           Backend (FastAPI)        │
│                              │  HTTPS │                                    │
│  Dashboard ────────────────► │ ─────► │  /api/v1/*                         │
│  Cases / Evidence / Upload   │        │                                    │
│  Analysis / Comparison       │        │  Services                          │
│  Timeline / Reports          │        │   ├─ EvidenceService               │
│  Audit Logs / Users          │        │   ├─ StorageService                │
│                              │        │   ├─ HashingService                │
│  (TanStack Query cache)      │        │   ├─ MetadataService (FFprobe)     │
│                              │        │   ├─ VideoAnalysisService          │
│                              │        │   ├─ FrameAnalysisService (OpenCV) │
│                              │        │   ├─ ComparisonService             │
│                              │        │   ├─ AnomalyService                │
│                              │        │   ├─ ReportService (ReportLab)     │
│                              │        │   └─ AuditService                  │
└──────────────────────────────┘        └───────────────┬────────────────────┘
                                                        │ Celery
                                                        ▼
                                           ┌──────────────────────────┐
                                           │      Workers             │
                                           │  video_tasks             │
                                           │  frame_tasks             │
                                           │  metadata_tasks          │
                                           └──────────┬───────────────┘
                                                      │
                              ┌───────────────────────┼───────────────────────┐
                              │                       │                       │
                     ┌────────▼────────┐     ┌────────▼───────┐     ┌─────────▼────────┐
                     │   PostgreSQL    │     │   Redis        │     │   Storage        │
                     │   (metadata,    │     │   (broker /    │     │   originals/     │
                     │    analysis,    │     │    result       │     │   processed/     │
                     │    audit)       │     │    backend)    │     │   quarantine/    │
                     └─────────────────┘     └────────────────┘     └──────────────────┘
```

## 2. Directory Structure

```
CCTV MetaInfo/
├── docs/                         # Project documentation
│   ├── PROJECT_PLAN.md
│   ├── ARCHITECTURE.md           # (this file)
│   ├── SETUP_GUIDE.md
│   ├── DEVELOPMENT_ROADMAP.md
│   ├── SECURITY.md
│   ├── FORENSIC_METHODOLOGY.md
│   └── API.md                    # API reference (written per-phase)
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py           # Shared dependencies (DB, auth)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py     # Aggregates all endpoint routers
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           ├── auth.py
│   │   │           ├── users.py
│   │   │           ├── cases.py
│   │   │           ├── evidence.py
│   │   │           ├── analysis.py
│   │   │           ├── comparison.py
│   │   │           ├── reports.py
│   │   │           └── audit.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py         # Pydantic Settings (.env)
│   │   │   ├── security.py       # Password hash, JWT, RBAC helpers
│   │   │   ├── logging.py        # Structured logging setup
│   │   │   └── exceptions.py     # Custom exceptions + handlers
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Declarative Base
│   │   │   ├── session.py        # engine + SessionLocal
│   │   │   └── seed.py           # Initial admin user, roles, cases
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── case.py
│   │   │   ├── evidence.py
│   │   │   ├── video_metadata.py
│   │   │   ├── analysis.py
│   │   │   ├── anomaly.py
│   │   │   ├── comparison.py
│   │   │   ├── report.py
│   │   │   └── audit_log.py
│   │   ├── schemas/              # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── case.py
│   │   │   ├── evidence.py
│   │   │   ├── video_metadata.py
│   │   │   ├── analysis.py
│   │   │   ├── anomaly.py
│   │   │   ├── comparison.py
│   │   │   ├── report.py
│   │   │   └── audit_log.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── evidence_service.py
│   │   │   ├── storage_service.py
│   │   │   ├── hashing_service.py
│   │   │   ├── metadata_service.py      # FFprobe
│   │   │   ├── structure_service.py     # video structure
│   │   │   ├── frame_analysis_service.py
│   │   │   ├── comparison_service.py
│   │   │   ├── anomaly_service.py
│   │   │   ├── report_service.py
│   │   │   ├── audit_service.py
│   │   │   └── auth_service.py
│   │   ├── forensic/
│   │   │   ├── __init__.py
│   │   │   ├── media.py           # FFmpeg/FFprobe wrappers
│   │   │   ├── frames.py          # OpenCV extraction + stats
│   │   │   ├── scene_diff.py      # Frame-difference algorithms
│   │   │   ├── perceptual.py      # Perceptual hashing
│   │   │   ├── scoring.py         # Explainable anomaly scoring
│   │   │   └── constants.py       # Severity levels, thresholds
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py           # analysis, metadata, frame tasks
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── file_utils.py      # safe filenames, size formatting
│   │       └── time_utils.py      # timestamps, duration formatting
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_hash_service.py
│   │   │   ├── test_metadata_parser.py
│   │   │   ├── test_scene_diff.py
│   │   │   └── test_scoring.py
│   │   ├── api/
│   │   │   ├── test_auth.py
│   │   │   ├── test_cases.py
│   │   │   ├── test_evidence.py
│   │   │   └── test_security.py
│   │   └── fixtures/
│   │       └── sample_videos/     # generated small test videos
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── api/
│   │   │   ├── client.ts         # axios/fetch wrapper + interceptors
│   │   │   └── endpoints.ts
│   │   ├── types/                # Shared TS types (mirror schemas)
│   │   │   └── index.ts
│   │   ├── hooks/                # TanStack Query hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useCases.ts
│   │   │   ├── useEvidence.ts
│   │   │   └── useAnalysis.ts
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Topbar.tsx
│   │   │   │   └── StatusBadge.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── StatCard.tsx
│   │   │   │   └── Charts.tsx
│   │   │   ├── evidence/
│   │   │   │   ├── UploadForm.tsx
│   │   │   │   ├── EvidenceTable.tsx
│   │   │   │   └── IntegrityCard.tsx
│   │   │   ├── analysis/
│   │   │   │   ├── AnomalyList.tsx
│   │   │   │   ├── AnomalyDetail.tsx
│   │   │   │   └── ScoreGauge.tsx
│   │   │   ├── timeline/
│   │   │   │   └── Timeline.tsx
│   │   │   └── comparison/
│   │   │       └── CompareView.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Cases.tsx
│   │   │   ├── CaseDetail.tsx
│   │   │   ├── Evidence.tsx
│   │   │   ├── EvidenceDetail.tsx
│   │   │   ├── Upload.tsx
│   │   │   ├── Analysis.tsx
│   │   │   ├── Comparison.tsx
│   │   │   ├── Timeline.tsx
│   │   │   ├── Reports.tsx
│   │   │   ├── AuditLogs.tsx
│   │   │   ├── Users.tsx
│   │   │   └── Settings.tsx
│   │   ├── router.tsx
│   │   └── utils/
│   │       ├── format.ts
│   │       └── severity.ts
│   └── tests/                    # Vitest component/integration tests
│
├── storage/                      # Git-ignored
│   ├── evidence/
│   │   ├── originals/            # Immutable original files
│   │   ├── processed/            # Working copies for analysis
│   │   └── quarantine/           # Failed validation
│   └── reports/                  # Generated PDFs
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── Dockerfile.worker
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── scripts/
    ├── setup_dev.ps1
    ├── run_backend.ps1
    └── run_frontend.ps1
```

## 3. Technology Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI + Pydantic | Native async, automatic OpenAPI docs, request validation |
| SQLAlchemy 2.0 + Alembic | Mature ORM, declarative models, migration management |
| PostgreSQL | JSONB for metadata, robust audit support, production-grade |
| Celery + Redis | Standard background job stack; decouples analysis from HTTP |
| FFmpeg/FFprobe | Industry-standard for video processing and metadata |
| OpenCV | Frame extraction, difference analysis, image statistics |
| ReportLab | Pure-Python PDF generation, deterministic reports |
| React + TanStack Query | Server-state caching, polling for job status |
| Tailwind CSS | Rapid, consistent dark-forensics theming |

## 4. Database Design

All entities use UUID primary keys. See per-model files for exact columns.

### relationships
- User 1—N Case (investigator_id)
- Case 1—N Evidence
- Evidence 1—1 VideoMetadata
- Evidence 1—N Analysis
- Analysis 1—N Anomaly
- Evidence 1—N Comparison (original_evidence_id / suspected_evidence_id)
- Evidence 1—N Report
- User 1—N AuditLog

### Key design notes
- `evidence.storage_path` is an internal path, never exposed to normal users.
- `video_metadata.metadata_json` stores the full raw FFprobe JSON.
- `analysis.result` is JSONB so results can evolve without schema churn.
- `anomaly.evidence_data` stores the frame-level evidence (paths, scores).
- `audit_logs` are append-only; protected by DB rules against UPDATE/DELETE.
- `comparison.result` stores the structured diff between two videos.

## 5. Evidence Preservation Workflow

1. Validate upload (extension, size, magic-bytes MIME).
2. Generate secure stored filename: `{sha256_prefix}_{uuid}{ext}`.
3. Write bytes once to `storage/evidence/originals/{case_id}/`.
4. Set file read-only (Windows: remove write permission).
5. Compute SHA-256 and SHA-512 from the stored bytes.
6. Record file size, MIME, upload timestamp, uploading user.
7. Never write to the original path again.
8. All analysis operates on a copy in `storage/evidence/processed/`.
9. Every step is written to the audit log.

## 6. Forensic Processing Pipeline

```
Evidence (read-only original)
   │
   ├─► HashingService ──► sha256, sha512 (from original)
   │
   ├─► MetadataService ──► ffprobe -print_format json ──► normalized fields + raw JSON
   │
   ├─► StructureService ──► ffprobe streams, packets, GOP, keyframes
   │
   ├─► FrameAnalysisService ──► OpenCV on working copy
   │       sampling: 1, 2, or 5 fps (configurable)
   │       per frame: number, timestamp, perceptual hash, stats, histogram
   │       frames stored ONLY for anomalies (evidence frames)
   │
   ├─► SceneDiffService ──► frame differences (MAD, histogram, SSIM, pHash)
   │       threshold configurable; output = difference events
   │
   ├─► AnomalyService ──► explainable indicator score from contributing factors
   │
   ├─► ComparisonService ──► original vs suspected metadata/frame diff
   │
   └─► ReportService ──► ReportLab PDF (facts / interpretations / conclusions)
```

## 7. API Design

Versioned under `/api/v1`. All endpoints require JWT (except `/api/v1/auth/login`). Every mutating action is audited.

```
POST   /api/v1/auth/login
GET    /api/v1/auth/me

GET    /api/v1/users                (admin)
POST   /api/v1/users                (admin)
GET    /api/v1/users/{id}           (admin)
PATCH  /api/v1/users/{id}           (admin)

GET    /api/v1/cases
POST   /api/v1/cases                (investigator+)
GET    /api/v1/cases/{id}
PUT    /api/v1/cases/{id}

POST   /api/v1/evidence/upload
GET    /api/v1/evidence
GET    /api/v1/evidence/{id}
POST   /api/v1/evidence/{id}/hash
POST   /api/v1/evidence/{id}/metadata
POST   /api/v1/evidence/{id}/analyze
GET    /api/v1/evidence/{id}/analysis
GET    /api/v1/evidence/{id}/timeline
GET    /api/v1/evidence/{id}/audit-trail

POST   /api/v1/comparisons
GET    /api/v1/comparisons/{id}

POST   /api/v1/reports
GET    /api/v1/reports/{id}

GET    /api/v1/audit-logs           (admin)

GET    /api/v1/dashboard/stats      (admin/investigator)
```

### Background job status flow

```
POST /evidence/{id}/analyze
  → creates Analysis(status=QUEUED)
  → enqueues Celery task → returns {analysis_id}
  → worker: PROCESSING → runs pipeline → COMPLETED | FAILED
Frontend polls GET /evidence/{id}/analysis until terminal state.
```

## 8. Anomaly Scoring Model

Explainable indicator score (0–100), NOT a tampering probability.

| Factor | Weight |
|--------|--------|
| Metadata inconsistency | +15 |
| Duration difference (comparison) | +20 |
| Frame discontinuity | +25 |
| Encoding difference (comparison) | +15 |
| Frame-difference cluster (unnatural density) | +15 |
| Single scene-change events (natural, low weight) | +5 max |

Categories:

| Score | Label |
|-------|-------|
| 0–20 | Low indicators |
| 21–50 | Moderate indicators |
| 51–75 | High indicators |
| 76–100 | Very high indicators |

Every score stores its contributing factors so the UI can show reasons.

## 9. Security Architecture

See SECURITY.md for full threat model. Highlights:

- Passwords via `bcrypt` (or `passlib`+`bcrypt`), JWT for sessions.
- RBAC: admin / investigator / viewer.
- Upload validation: extension allowlist, size cap, magic-byte MIME check.
- Secure storage: generated filenames, no path traversal, read-only originals.
- Audit logging: append-only, DB rules block UPDATE/DELETE.
- Never execute uploaded files.
- Never expose internal storage paths in API responses.
- Rate limiting on auth endpoints.

## 10. Windows-Specific Notes

- Use `pathlib.Path` everywhere; avoid raw string concatenation.
- File read-only via `os.chmod(path, stat.S_IREAD)`.
- Celery on Windows: use `--pool=solo` (dev) or eventlet.
- FFmpeg/FFprobe located via env vars or `shutil.which`; add to PATH.
- OneDrive sync: keep `storage/` outside OneDrive-managed folders or exclude it.
- Long path support: enable via Windows registry if needed.

## 11. Configuration

All configuration via environment variables (see `.env.example`). Backend uses Pydantic Settings. Frontend uses Vite env vars (`VITE_API_URL`).

## 12. Testing Strategy

- Backend: pytest (unit + API + security), fixtures generate sample videos with FFmpeg.
- Sample videos: normal, trimmed, re-encoded, different resolution, different FPS, metadata-modified, joined.
- Frontend: Vitest + React Testing Library for components and workflows.
- CI-ready structure: `pytest backend/tests`, `npm run test`, `npm run lint`, `npm run build`.

## 13. Deployment (Production Readiness)

- Docker Compose: frontend, backend, worker, postgres, redis.
- Backend container includes FFmpeg/FFprobe.
- HTTPS termination via reverse proxy (documented, not required for local POC).
- Volume for `storage/` mounted read-only from host policy perspective.
