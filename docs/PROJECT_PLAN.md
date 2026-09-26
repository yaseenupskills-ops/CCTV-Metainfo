# CCTV Forensic Analyzer — Project Plan

## 1. Overview

A secure digital video-forensics platform that allows investigators to upload CCTV footage, preserve its integrity, extract technical metadata, calculate cryptographic hashes, analyze video structure and frames, compare original and suspected copies, identify potential technical anomalies, and generate forensic reports.

**Critical principle:** The system must NEVER claim a video is definitely "fake" or "tampered" based only on automated analysis. All findings are presented as potential indicators requiring expert interpretation.

### Terminology Requirements

| Use this | Never use this |
|-----------|----------------|
| Potential anomaly | Definitely tampered |
| Possible modification indicator | Definitely fake |
| Suspicious transition | Proven manipulation |
| Integrity mismatch | Corrupted beyond doubt |
| Possible re-encoding | Maliciously re-encoded |

## 2. Goals

| Goal | Metric |
|------|--------|
| Professional proof-of-concept | Demonstrable end-to-end workflow in 6-8 weeks |
| Solid foundations | Complete architecture, auth, database, tests before features |
| Evidence integrity | Original files never modified; SHA-256/512 hashing |
| Explainability | Every anomaly score traceable to contributing factors |
| Security | RBAC, JWT auth, audit logging, secure file handling |

## 3. Non-Goals (for the POC)

- Face recognition / object detection / OCR
- Claims of statistical tampering probability
- Multi-server clustering
- End-to-end encryption of stored evidence (deferred to production hardening)

## 4. Core Workflow

```
UPLOAD EVIDENCE
      ↓
PRESERVE ORIGINAL
      ↓
CALCULATE HASH
      ↓
EXTRACT METADATA
      ↓
VIDEO STRUCTURE ANALYSIS
      ↓
FRAME ANALYSIS
      ↓
ANOMALY DETECTION
      ↓
OPTIONAL VIDEO COMPARISON
      ↓
TIMELINE VISUALIZATION
      ↓
FORENSIC REPORT
      ↓
AUDIT LOG
```

The original evidence file must NEVER be modified. All processing operates on a working copy or read-only representation.

## 5. Technology Stack

### Frontend
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router
- TanStack Query
- Recharts
- Lucide React icons

### Backend
- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- Alembic
- Celery + Redis (background workers)

### Video Forensics
- FFmpeg / FFprobe (external binaries)
- OpenCV (Python bindings)
- NumPy
- hashlib (SHA-256, SHA-512)

### Database
- PostgreSQL 16

### Reporting
- ReportLab (PDF generation)

## 6. Delivery Timeline

| Week | Phase(s) | Deliverable |
|------|----------|-------------|
| 1 | 1-3 | Repo, docs, backend skeleton, DB, upload + secure storage |
| 2 | 4-6 | Hashing, FFprobe metadata, evidence details API |
| 3 | 7 | React dashboard + evidence details UI |
| 4 | 8-9 | OpenCV frame extraction, scene-difference analysis |
| 5 | 10-11 | Comparison engine, timeline visualization |
| 6 | 12-13 | Anomaly scoring, PDF reports |
| 7 | 14-15 | Auth + RBAC, audit logging |
| 8 | 16-18 | Background workers, testing + hardening, Docker + docs |

## 7. Phase Definitions

Each phase has explicit tasks, affected files, tests, and a Definition of Done (see DEVELOPMENT_ROADMAP.md for full detail).

| Phase | Name |
|-------|------|
| 1 | Repository inspection + architecture + documentation |
| 2 | Backend skeleton + database |
| 3 | Evidence upload + secure storage |
| 4 | SHA-256 / SHA-512 hashing |
| 5 | FFprobe metadata extraction |
| 6 | Evidence details API |
| 7 | React dashboard |
| 8 | OpenCV frame extraction |
| 9 | Frame/scene difference analysis |
| 10 | Original vs suspected comparison |
| 11 | Timeline visualization |
| 12 | Anomaly scoring |
| 13 | PDF forensic reports |
| 14 | Authentication + RBAC |
| 15 | Audit logging |
| 16 | Background workers |
| 17 | Testing + security hardening |
| 18 | Docker + deployment documentation |

## 8. Definition of Done

A feature is complete only when:

- [ ] Code is implemented
- [ ] Error handling exists
- [ ] Input validation exists
- [ ] Tests exist
- [ ] Tests pass
- [ ] Lint/type checks pass
- [ ] API behavior is documented
- [ ] UI behavior is implemented where required
- [ ] Security implications are considered
- [ ] No fake/mock implementation is presented as production functionality

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| OpenCV lacks FFmpeg support in pip wheel | Install opencv-python-headless + ensure FFmpeg on PATH, or use conda |
| Celery on Windows needs eventlet/gevent pool | Use `--pool=solo` for dev, eventlet for Windows in production |
| Large video analysis blocks HTTP | Background workers (Celery) with status polling |
| FFmpeg/FFprobe path issues | Environment variables `FFMPEG_PATH` / `FFPROBE_PATH` with PATH fallback |
| Evidence file modification | Read-only permissions on originals; working copies for analysis |
| OneDrive sync interference | Store evidence under `storage/`; document exclusion from sync |

## 10. Open Questions / Assumptions

- PostgreSQL will run as a local Windows service during development.
- FFmpeg/FFprobe will be installed via chocolatey or manual install (see SETUP_GUIDE.md).
- Redis will be installed locally or run via Docker Desktop for Celery phases.
- The POC targets a single Windows workstation deployment.
