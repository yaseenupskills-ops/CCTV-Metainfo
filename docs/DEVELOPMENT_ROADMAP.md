# CCTV Forensic Analyzer — Development Roadmap

This document is the authoritative task list for building the system. Each phase lists: goal, tasks, affected files, verification steps, and Definition of Done. Phases must be implemented in order.

## Global Conventions

- All backend code is inside `backend/app/`.
- All frontend code is inside `frontend/src/`.
- Every mutating endpoint writes an audit log entry.
- Every analysis output stores raw + normalized data.
- Never modify original evidence files.
- Run tests before declaring a phase complete.

---

## PHASE 1 — Repository Inspection + Architecture + Documentation

**Status:** Complete

**Goal:** Repository structure, docs, and development conventions in place.

### Tasks
1. Inspect repository state; confirm empty/starting from scratch.
2. Create top-level directories: `docs`, `backend`, `frontend`, `storage`.
3. Write `PROJECT_PLAN.md`, `ARCHITECTURE.md`, `SETUP_GUIDE.md`, `SECURITY.md`, `FORENSIC_METHODOLOGY.md`.
4. Write root `README.md`.
5. Create `.env.example` and `.gitignore`.
6. Create initial `DEVELOPMENT_ROADMAP.md` (this file).
7. Set up editor config: `.editorconfig` (indent 4 spaces Python, 2 spaces TS).

### Affected Files
- All documentation files
- `.env.example`, `.gitignore`, `.editorconfig`

### Definition of Done
- [ ] Docs exist and are internally consistent
- [ ] Directory skeleton created
- [ ] `.env.example` contains all planned variables
- [ ] `.gitignore` covers Python, Node, env, storage
- [ ] No code written yet (docs only)

---

## PHASE 2 — Backend Skeleton + Database

**Status:** Complete (10 tests passing, ruff + mypy clean)

**Goal:** Runable FastAPI app with PostgreSQL schema and Alembic migrations.

### Tasks
1. Create `backend/` package layout (app/api, core, db, models, schemas, services, workers, utils).
2. Define `app/core/config.py` (Pydantic Settings reading `.env`).
3. Define SQLAlchemy `Base`, engine, session factory in `app/db/`.
4. Define models: User, Case, Evidence, VideoMetadata, Analysis, Anomaly, Comparison, Report, AuditLog.
5. Define Pydantic schemas for each model (at least base CRUD).
6. Configure Alembic; generate initial migration.
7. Create `app/main.py` with FastAPI app, CORS, health endpoint `GET /api/v1/health`.
8. Create `app/db/seed.py` for admin user + demo data.
9. Write basic pytest fixture using a test database (or SQLite for unit tests).
10. Add `requirements.txt` and `requirements-dev.txt`.

### Affected Files
- `backend/app/**` (skeleton)
- `backend/alembic/**`, `backend/alembic.ini`
- `backend/requirements*.txt`, `backend/pyproject.toml`
- `backend/tests/conftest.py`

### Verification
- `uvicorn app.main:app` starts without error.
- `alembic upgrade head` applies migration.
- `pytest backend/tests` passes (health test).

### Definition of Done
- [ ] App boots; `/api/v1/health` returns 200
- [ ] All 9 tables created via migration
- [ ] Seed script creates admin + demo case
- [ ] Unit tests for config and health exist and pass

---

## PHASE 3 — Evidence Upload + Secure Storage

**Status:** Complete (29 tests passing, ruff + mypy clean, live HTTP smoke test verified)

**Goal:** Upload, validate, and store evidence files without touching originals.

### Tasks
1. Implement `app/utils/file_utils.py`: safe filename generation, extension allowlist, size formatting.
2. Implement `app/services/storage_service.py`: secure write to `storage/evidence/originals/{case_id}/`, set read-only, never overwrite.
3. Implement `app/services/evidence_service.py`: orchestrate validation + storage + DB row creation.
4. Implement `POST /api/v1/evidence/upload` (multipart, case_id, optional notes).
5. Upload validation: extension allowlist, MAX_UPLOAD_SIZE, magic-bytes MIME detection, empty-file check.
6. Write audit log entry on upload.
7. Tests: valid upload, invalid extension, oversized, empty file, invalid magic bytes, path traversal attempt.

### Affected Files
- `backend/app/utils/file_utils.py`
- `backend/app/services/storage_service.py`, `evidence_service.py`, `audit_service.py`
- `backend/app/api/v1/endpoints/evidence.py`
- `backend/tests/api/test_evidence.py`

### Verification
- Upload via `/docs` works; file stored read-only; DB row created.
- Re-uploading same filename creates a new, distinct stored file.

### Definition of Done
- [ ] Upload endpoint works end-to-end
- [ ] Original file is read-only on disk
- [ ] Security tests pass (invalid/oversized/path traversal)
- [ ] Audit log written on upload

---

## PHASE 4 — Hashing

**Status:** Complete (40 tests passing, ruff + mypy clean, live smoke test + Get-FileHash cross-check verified)

**Goal:** SHA-256 and SHA-512 calculation from the original file.

### Tasks
1. Implement `app/services/hashing_service.py`:
   - `compute_hashes(path)` returns sha256, sha512, file_size, calculated_at.
   - Streaming chunk read (1 MB) for large files.
2. Implement `POST /api/v1/evidence/{id}/hash`:
   - Reads actual stored file (never cache-only).
   - Updates/records hash values + calculation timestamp.
3. Response schema: algorithm, hash, file_size, calculated_at (per algorithm).
4. Tests: known-vector hash, large file, missing file error, API round-trip.

### Affected Files
- `backend/app/services/hashing_service.py`
- `backend/app/api/v1/endpoints/evidence.py`
- `backend/app/schemas/evidence.py`
- `backend/tests/unit/test_hash_service.py`

### Verification
- Hash of uploaded file matches `Get-FileHash -Algorithm SHA256`.

### Definition of Done
- [ ] SHA-256 and SHA-512 correct for known vectors
- [ ] API returns documented JSON shape
- [ ] Hash recorded on evidence row
- [ ] Tests pass

---

## PHASE 5 — FFprobe Metadata Extraction

**Status:** Complete (55 tests passing, ruff + mypy clean, live HTTP smoke test verified)

**Goal:** Extract comprehensive metadata from video files.

### Tasks
1. Implement `app/forensic/media.py`:
   - Locate ffprobe via `FFPROBE_PATH` env or `shutil.which`.
   - `probe(path)` returns parsed JSON (format + streams) with error handling.
2. Implement `app/services/metadata_service.py`:
   - Normalize: duration, width, height, fps, frame_count, codecs, bitrate, pixel_format, stream_count, creation_time, encoder, tags.
   - Store normalized fields in `video_metadata` row AND raw JSON in `metadata_json`.
3. Implement `POST /api/v1/evidence/{id}/metadata`:
   - Creates/updates VideoMetadata; sets evidence status.
4. Implement `app/services/structure_service.py`:
   - Stream-level details: keyframes, GOP info when available, packet info if cheap.
   - Store in `video_metadata.metadata_json` under `structure` key.
5. Tests: metadata parser unit tests with a fixture JSON, API test, ffprobe-not-found handling.

### Affected Files
- `backend/app/forensic/media.py`
- `backend/app/services/metadata_service.py`, `structure_service.py`
- `backend/app/api/v1/endpoints/evidence.py`
- `backend/tests/unit/test_metadata_parser.py`

### Verification
- Upload a real mp4; metadata endpoint returns matching ffprobe output.

### Definition of Done
- [ ] FFprobe wrapper returns JSON with error propagation
- [ ] Normalized fields + raw JSON stored
- [ ] API endpoint works
- [ ] Tests pass

---

## PHASE 6 — Evidence Details API

**Status:** Complete (71 tests passing, ruff + mypy clean, live HTTP smoke test verified)

**Goal:** Full evidence read API used by the frontend.

### Tasks
1. `GET /api/v1/evidence` — list with filters (case_id, status), pagination.
2. `GET /api/v1/evidence/{id}` — full detail: overview, integrity, video info, metadata, analyses, anomalies, audit trail.
3. `GET /api/v1/evidence/{id}/analysis` — list analyses with status.
4. `GET /api/v1/evidence/{id}/audit-trail` — audit entries for the evidence.
5. Ensure no internal storage paths leak into responses.
6. Tests: list/detail/404/permission scenarios (auth stubbed until Phase 14).

### Affected Files
- `backend/app/api/v1/endpoints/evidence.py`
- `backend/app/schemas/evidence.py`, `analysis.py`, `audit_log.py`
- `backend/tests/api/test_evidence.py`

### Definition of Done
- [ ] All read endpoints implemented with pagination
- [ ] Detail aggregates related data
- [ ] No storage paths exposed
- [ ] Tests pass

---

## PHASE 7 — React Dashboard

**Status:** Complete (76 backend tests, ruff + mypy clean; 10 frontend tests, lint + build clean; live HTTP smoke test verified)

**Goal:** Professional dark forensic dashboard wired to the API.

### Tasks
1. Scaffold Vite + React + TS + Tailwind. Configure dark theme tokens (navy/black bg, blue primary, green/yellow/red/purple semantic colors).
2. Set up React Router with all routes and a protected layout.
3. Set up TanStack Query client + axios wrapper (`frontend/src/api/client.ts`).
4. Create types mirroring backend schemas.
5. Implement pages: Login (stub auth), Dashboard, Cases, Evidence, EvidenceDetail, Upload, Analysis, Timeline, Reports, AuditLogs, Users, Settings.
6. Dashboard: stat cards (Total Cases, Total Evidence, Analyses Completed, Pending Analyses), charts (analysis status, anomaly distribution, trends), recent evidence table, quick actions.
7. Evidence detail page sections: Overview, Integrity, Video Information, Metadata, Analysis, Anomalies, Audit Trail.
8. Component tests for StatCard, EvidenceTable, StatusBadge.

### Affected Files
- `frontend/**` (scaffold + pages + components)
- `frontend/src/api/client.ts`, `frontend/src/types/index.ts`

### Verification
- `npm run dev` renders dashboard; data loads from backend (evidence list).
- `npm run build` and `npm run lint` pass.

### Definition of Done
- [x] App boots with dark theme
- [x] Dashboard shows real API data
- [x] Evidence detail page renders all sections
- [x] Type/lint/build pass
- [x] Component tests pass

---

## PHASE 8 — OpenCV Frame Extraction

**Status:** Complete (93 backend tests, ruff + mypy clean; live HTTP smoke test verified: 3s@10fps → 3 frames at 1fps)

**Goal:** Configurable frame sampling without storing unnecessary images.

### Tasks
1. Implement `app/forensic/frames.py`:
   - `extract_frames(path, sampling_rate)` streaming via OpenCV (working copy).
   - Compute per-frame: number, timestamp, perceptual hash (pHash), stats (mean, std), histogram (luma).
   - Sampling rates: 1, 2, or 5 fps (configurable; store sampling rate on Analysis).
   - Store results in DB (Analysis JSON) — NOT images, except anomaly frames.
2. Implement `POST /api/v1/evidence/{id}/analyze` with `analysis_type=frame_sampling` (synchronous for now; job wiring Phase 16).
3. Store analysis status transitions QUEUED→PROCESSING→COMPLETED/FAILED.
4. Tests: tiny generated video (FFmpeg fixture), sampling correctness, timestamp math, failure on corrupt file.

### Affected Files
- `backend/app/forensic/frames.py`
- `backend/app/services/frame_analysis_service.py`
- `backend/app/api/v1/endpoints/analysis.py`
- `backend/tests/fixtures/` (video generation script)
- `backend/tests/unit/test_frame_analysis.py`

### Verification
- Analyzing a 10s video at 1fps yields ~10 frame entries.

### Definition of Done
- [x] Frame sampling works with correct counts/timestamps
- [x] pHash + stats + histogram computed per frame
- [x] No bulk image storage
- [x] Tests pass

---

## PHASE 9 — Scene / Frame Difference Analysis

**Status:** Complete (107 backend tests, ruff + mypy clean)

**Goal:** Deterministic frame-difference analysis with configurable thresholds.

### Tasks
1. Implement `app/forensic/scene_diff.py`:
   - Mean absolute difference (MAD), histogram difference, SSIM (via `skimage` or cv2), pHash distance.
   - Configurable threshold for "significant difference".
2. Implement `app/forensic/scoring.py` factor hooks used later (Phase 12).
3. Record events: timestamp, prev frame, current frame, diff score, detection method, severity.
4. Frame difference does NOT imply tampering — severity labeled "Potential anomaly".
5. Implement `POST /api/v1/evidence/{id}/analyze` with `analysis_type=scene_change`.
6. Tests: normal video produces expected minimal events; forced scene change produces a large-diff event; threshold tuning test.

### Affected Files
- `backend/app/forensic/scene_diff.py`, `perceptual.py`
- `backend/app/services/frame_analysis_service.py`
- `backend/tests/unit/test_scene_diff.py`

### Definition of Done
- [x] Multiple detection methods implemented
- [x] Events recorded with all required fields
- [x] Wording uses "Potential anomaly"
- [x] Tests pass

---

## PHASE 10 — Original vs Suspected Comparison

**Status:** Complete (125 backend tests, ruff + mypy clean, live HTTP smoke test verified)

**Goal:** Metadata + hash comparison between two videos.

### Tasks
1. Implement `app/services/comparison_service.py`:
   - Compare file size, duration, resolution, fps, codec, bitrate, frame count, metadata, hashes, timestamps.
   - Produce structured differences with status per field (MATCH/DIFFERENCE/NOT_AVAILABLE).
2. `POST /api/v1/comparisons` (original_evidence_id, suspected_evidence_id); `GET /api/v1/comparisons/{id}`.
3. Comparison UI placeholder with two panels (full UI Phase 10b / within Phase 10).
4. Frame-level comparison deferred (documented as future work).
5. Tests: same-file, trimmed, re-encoded, different resolution/fps copies.

### Affected Files
- `backend/app/services/comparison_service.py`
- `backend/app/api/v1/endpoints/comparison.py`
- `backend/tests/unit/test_comparison.py`

### Definition of Done
- [x] Comparison API returns structured diff
- [x] Status labels MATCH/DIFFERENCE/NOT_AVAILABLE
- [x] Tests cover sample-video types

---

## PHASE 11 — Timeline Visualization

**Status:** Complete (129 backend tests, ruff + mypy clean; 13 frontend tests, lint + build clean; live HTTP smoke test verified)

**Goal:** Suspicious timeline UI with clickable anomalies.

### Tasks
1. `GET /api/v1/evidence/{id}/timeline` — ordered events: normal segments + anomalies.
2. Timeline component: horizontal segments colored by status; click anomaly → detail drawer (timestamp, detection reason, diff score, relevant frames, metadata).
3. Integration with TanStack Query for polling analysis completion.
4. Tests: component test for timeline rendering + click handler.

### Affected Files
- `backend/app/api/v1/endpoints/evidence.py` (timeline endpoint)
- `frontend/src/components/timeline/Timeline.tsx`
- `frontend/src/pages/Timeline.tsx`

### Definition of Done
- [x] Timeline endpoint returns segments
- [x] Timeline renders and is interactive
- [x] Anomaly detail shows all required fields

---

## PHASE 12 — Anomaly Scoring

**Status:** Complete (158 backend tests, ruff + mypy clean; 17 frontend tests, lint + build clean; live HTTP smoke test verified)

**Goal:** Explainable anomaly indicator score (0–100).

### Tasks
1. Implement `app/forensic/scoring.py`:
   - Factors: metadata inconsistency (+15), duration difference (+20), frame discontinuity (+25), encoding difference (+15), unnatural frame-diff cluster (+15), single scene changes (+5 max).
   - Output score + list of contributing factors with weights and reasons.
2. Categories: 0-20 low, 21-50 moderate, 51-75 high, 76-100 very high.
3. Label: "Anomaly Indicator Score" (not "probability of tampering").
4. Persist score + factors on Analysis result.
5. ScoreGauge UI component showing breakdown.
6. Tests: each factor isolated, combined score, category boundaries.

### Affected Files
- `backend/app/forensic/scoring.py`
- `backend/app/services/anomaly_service.py`
- `frontend/src/components/analysis/ScoreGauge.tsx`
- `backend/tests/unit/test_scoring.py`

### Definition of Done
- [x] Scores are deterministic and explainable
- [x] Categories correct
- [x] UI shows reasons, not a black-box number
- [x] Tests pass

---

## PHASE 13 — PDF Forensic Reports

**Status:** Complete

**Goal:** ReportLab PDF generation with clear fact/interpretation distinction.

### Tasks
1. Implement `app/services/report_service.py` with ReportLab:
   - Sections: Cover, Case info, Evidence info, Integrity, Metadata, Video analysis, Frame analysis, Anomalies, Timeline, Comparison, Audit trail, Technical conclusion, Disclaimer.
2. Clearly separate OBSERVED FACTS / AUTOMATED INTERPRETATIONS / INVESTIGATOR CONCLUSIONS.
3. `POST /api/v1/reports` (case_id, evidence_id, optional comparison_id); `GET /api/v1/reports/{id}` (download).
4. Store PDF in `storage/reports/`; record report row.
5. Tests: report generation returns valid PDF (header bytes), sections present.

### Affected Files
- `backend/app/services/report_service.py`
- `backend/app/api/v1/endpoints/reports.py`
- `backend/tests/unit/test_report_service.py`

### Definition of Done
- [x] PDF generates and downloads
- [x] All 13 sections present
- [x] Facts/interpretations/conclusions clearly labeled
- [x] Disclaimer included

---

## PHASE 14 — Authentication + RBAC

**Status:** Complete

**Goal:** JWT auth with admin/investigator/viewer roles.

### Tasks
1. Implement `app/core/security.py`: bcrypt password hashing, JWT create/verify.
2. `POST /api/v1/auth/login`, `GET /api/v1/auth/me`.
3. Dependency `get_current_user`, `require_role(role)`.
4. Enforce roles:
   - Admin: manage users, cases, evidence, view everything, generate reports, view audit logs.
   - Investigator: create cases, upload/analyze evidence, compare, generate reports.
   - Viewer: view assigned cases/evidence/reports, cannot modify.
5. Protect all endpoints; audit login/logout (if applicable) and access-denied events.
6. Login UI + token storage (httpOnly recommended; localStorage acceptable for POC with documented tradeoff).
7. Tests: login, wrong password, expired/invalid token, role restrictions matrix.

### Affected Files
- `backend/app/core/security.py`, `backend/app/api/deps.py`
- `backend/app/api/v1/endpoints/auth.py`, `users.py`
- `backend/app/services/auth_service.py`
- `frontend/src/pages/Login.tsx`, `frontend/src/api/client.ts`, `frontend/src/hooks/useAuth.ts`
- `backend/tests/api/test_auth.py`, `test_rbac.py`

### Definition of Done
- [x] Login/logout work; token verified on every request
- [x] RBAC matrix enforced (admin/investigator/viewer)
- [x] Security tests pass

---

## PHASE 15 — Audit Logging

**Status:** Complete

**Goal:** Append-only audit trail for all important actions.

### Tasks
1. Implement `app/services/audit_service.py`: record user, action, entity_type, entity_id, timestamp, metadata (IP, user-agent, request id).
2. Apply DB rules to make audit_logs immutable (block UPDATE/DELETE).
3. Wire audit calls into: upload, hash, metadata, analyze, comparison, report, case/user mutations, login failures.
4. `GET /api/v1/audit-logs` (admin) with filters (user, entity, date range) + pagination.
5. Audit Logs UI page with filter + table.
6. Tests: audit written per action, immutability rule, access control.

### Affected Files
- `backend/app/services/audit_service.py`
- `backend/app/models/audit_log.py`
- `backend/app/api/v1/endpoints/audit.py`
- Alembic migration (immutability rules)
- `frontend/src/pages/AuditLogs.tsx`
- `backend/tests/api/test_audit.py`

### Definition of Done
- [x] Every mutating action audited
- [x] Audit rows cannot be updated/deleted (verified by test)
- [x] Audit API + UI work

---

## PHASE 16 — Background Workers

**Status:** Complete (209 backend tests, ruff + mypy clean; 20 frontend tests, lint + build clean)

**Goal:** Long-running analysis moved to Celery.

### Tasks
1. Install Celery + redis; create `app/workers/celery_app.py`.
2. Convert analysis pipelines (metadata, frame sampling, scene diff) into Celery tasks.
3. `POST /evidence/{id}/analyze` → create Analysis (QUEUED) → enqueue → return analysis_id.
4. Worker updates status PROCESSING→COMPLETED/FAILED with error_message.
5. Frontend polls `GET /evidence/{id}/analysis` until terminal status (TanStack Query refetchInterval).
6. Windows note: run worker with `--pool=solo` or eventlet.
7. Tests: task-level tests with eager mode (`task_always_eager=True`); API test verifies status flow.

### Affected Files
- `backend/app/workers/celery_app.py`, `tasks.py`
- `backend/app/api/v1/endpoints/analysis.py`, `evidence.py` (metadata enqueue)
- `backend/app/core/config.py` (REDIS_URL, CELERY_*)
- `frontend/src/hooks/useAnalysis.ts`
- `backend/tests/unit/test_tasks.py`

### Definition of Done
- [x] Analysis jobs run in background
- [x] Status transitions correct (incl. failure)
- [x] Metadata extraction also runs as a background task
- [x] Frontend reflects completion without blocking (auto-polling)
- [x] Tests pass in eager mode

---

## PHASE 17 — Testing + Security Hardening

**Status:** Complete (246 backend tests at ~95% coverage, ruff + mypy clean; 20 frontend tests, lint + build clean)

**Goal:** Full test suite + hardening pass.

### Tasks
1. Generate sample-video fixtures: normal, trimmed, re-encoded, different resolution, different fps, metadata-modified, joined (via `backend/tests/fixtures/generate_samples.py` using FFmpeg).
2. Expand tests: hash, metadata parser, frame analysis, scene diff, comparison, scoring, report, auth/RBAC, upload security.
3. Security hardening:
   - Rate limiting on auth endpoints.
   - Request size limits, CORS tightening.
   - SQL injection review (ORM-only), path traversal tests.
   - Ensure no internal paths in responses.
   - Validate all Pydantic schemas strictly.
4. Add flake8/ruff + mypy (or pyright) config; run lint/type checks.
5. Add `pyproject.toml` test/lint configuration.
6. Document known limitations.

### Affected Files
- `backend/tests/**`, `frontend/tests/**`
- `backend/pyproject.toml`
- Any fixes surfaced by lint/type checks

### Verification
- `pytest` green; `ruff check`; mypy clean; `npm run lint`; `npm run build`.

### Definition of Done
- [x] Full test suite passes
- [x] Lint + type checks pass
- [x] Security tests pass
- [x] Limitations documented

---

## PHASE 18 — Docker + Deployment Documentation

**Status:** Complete

**Goal:** Containerized deployment + operations docs.

### Tasks
1. Dockerfiles: backend (with FFmpeg installed), frontend (build + nginx static), worker.
2. `docker-compose.yml`: frontend, backend, worker, postgres, redis; volume for storage.
3. Healthchecks for postgres/redis/backend.
4. Document: `docker compose up --build`, env for containers, data volume persistence, backup strategy.
5. Update README with deployment section.

### Affected Files
- `docker/**`, `docker-compose.yml`
- `README.md`, `docs/SECURITY.md` (deployment notes)

### Definition of Done
- [x] `docker compose up --build` brings full stack up
- [x] FFmpeg available in backend/worker containers
- [x] Evidence storage persisted via volume
- [x] Deployment documented

---

## After Phase 18 — Maintenance Backlog (not in POC scope)

- Frame-level video comparison (per-frame diff between original and suspected).
- Statistical tampering model (requires validation; never ship unvalidated).
- TLS/HTTPS setup, BitLocker/disk encryption, S3-compatible storage.
- Multi-user case assignment and evidence sharing.
- Exif/container-timestamp cross-checks.
