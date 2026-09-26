# CCTV Forensic Analyzer — API Reference

Base URL: `/api/v1`

Interactive docs (Swagger UI): http://localhost:8000/docs

## Current Status

Authentication and RBAC are enforced (Phase 14 complete). All mutating endpoints
require a valid Bearer token and are audited. Role model: admin (full access),
investigator (create cases, upload/analyze evidence, compare, generate reports),
viewer (read-only). `storage_path` is never exposed in responses.

## Health

### GET /health

Service and database health.

```json
{ "status": "ok", "database": "connected" }
```

- `database`: `connected` or `unavailable`

---

## Evidence

### POST /evidence/upload

Upload an evidence file (multipart form-data).

**Form fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| case_id | UUID | yes | Target case |
| file | file | yes | Video file (mp4/mov/avi/mkv) |

**Validation (failures return 4xx):**
- 422 — disallowed extension, undetectable/non-video content, empty file
- 413 — exceeds `MAX_UPLOAD_SIZE`
- 404 — case not found

**Behavior:** stores the original read-only under `storage/evidence/originals/`,
computes SHA-256/SHA-512, records an audit entry.

**Response 201 — `EvidenceRead`:**
```json
{
  "id": "c4ffd073-7045-45fc-814b-b567c19e269e",
  "case_id": "d1d1d02a-50a4-4058-a41a-99ddd38bbc8f",
  "evidence_number": "EVD-20260810-44F2C9",
  "original_filename": "smoke_clip.mp4",
  "file_size": 124,
  "mime_type": "video/mp4",
  "sha256": "0904910d20f9616a586b2c2440ffe3a74fcd9c1691820a66c93acacf7e253c68",
  "sha512": "235c297b39132efa5a8fc4eb48691916e123b173b36bf971d30a742b33c2a904...",
  "hash_calculated_at": "2026-08-10T10:44:43.244162Z",
  "status": "uploaded",
  "uploaded_by": "3cb96742-3cc4-41da-9cc7-ae3b640b5416",
  "uploaded_at": "2026-08-10T10:27:23"
}
```

### POST /evidence/{id}/hash

Recompute SHA-256 and SHA-512 from the actual stored bytes. Updates the recorded
integrity values and writes an audit entry.

**Response 200 — `HashResponse`:**
```json
{
  "evidence_id": "c4ffd073-7045-45fc-814b-b567c19e269e",
  "calculations": [
    {
      "algorithm": "SHA-256",
      "hash": "0904910d20f9616a586b2c2440ffe3a74fcd9c1691820a66c93acacf7e253c68",
      "file_size": 124,
      "calculated_at": "2026-08-10T10:44:43.244162Z"
    },
    {
      "algorithm": "SHA-512",
      "hash": "235c297b39132efa5a8fc4eb48691916e123b173b36bf971d30a742b33c2a904...",
      "file_size": 124,
      "calculated_at": "2026-08-10T10:44:43.244162Z"
    }
  ]
}
```

**Errors:** 404 — evidence not found, or the stored file is missing from disk.

### POST /evidence/{id}/metadata

Extract technical metadata with FFprobe. Normalized fields are stored on the
`video_metadata` row; the raw probe JSON plus a derived `structure` section
(keyframes, keyframe interval) is stored in `metadata_json`.

**Response 200 — `VideoMetadataDetail`:**
```json
{
  "evidence_id": "657a9aa1-6baf-4f04-8cbf-fac1dcc43178",
  "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
  "duration": 1.0,
  "width": 320,
  "height": 240,
  "frame_rate": 10.0,
  "frame_count": 10,
  "video_codec": "h264",
  "audio_codec": null,
  "bitrate": 58840,
  "pixel_format": "yuv420p",
  "stream_count": 1,
  "creation_time": null,
  "encoder": "Lavc63.1.100 libx264",
  "analyzed_at": "2026-08-10T11:30:00",
  "metadata_json": {
    "format": { "...": "raw ffprobe format data" },
    "streams": [ "...raw ffprobe stream data..." ],
    "structure": {
      "keyframe_count": 1,
      "keyframes": [ { "time": 0.0, "pict_type": "I" } ],
      "frame_count_probed": 10,
      "avg_keyframe_interval": null,
      "first_keyframe_time": 0.0
    }
  }
}
```

**Behavior:** sets evidence status to `metadata_extracted`, writes an audit entry.
**Errors:** 404 — evidence not found / file missing; 500 — FFprobe unavailable or
the file is not a readable video.

### GET /evidence

List evidence. Soft-deleted evidence is hidden unless `status=deleted` is passed.

**Query parameters:**
| Param | Type | Description |
|-------|------|-------------|
| page | int ≥ 1 | Page number (default 1) |
| page_size | int 1-100 | Page size (default 20) |
| case_id | UUID | Filter by case |
| status | enum | uploaded / hashed / metadata_extracted / analyzed / archived / deleted |
| search | str | Case-insensitive match on evidence number, filename, case number, case title |

**Response 200 — `PaginatedResponse<EvidenceListItem>`:**
```json
{
  "items": [
    {
      "id": "21c50862-cb03-4f0f-822b-5f6af67dd694",
      "evidence_number": "EVD-20260810-E6A61B",
      "case_id": "f59a0a31-1126-4551-8ebb-63aea88dc807",
      "case_number": "CASE-SMOKE",
      "case_title": "Smoke",
      "original_filename": "smoke_clip.mp4",
      "file_size": 124,
      "mime_type": "video/mp4",
      "sha256": "0904910d20f9616a...",
      "status": "uploaded",
      "uploaded_at": "2026-08-10T12:00:45"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "total_pages": 1
}
```

### GET /evidence/{id}

Full evidence detail: base fields + `video_metadata` (or null) + `analyses` history.

**Response 200 — `EvidenceDetail`** (extends `EvidenceRead`):
```json
{
  "...": "evidence fields as above",
  "video_metadata": { "evidence_id": "...", "width": 320, "height": 240, "...": "..." },
  "analyses": [ { "id": "...", "analysis_type": "frame_sampling", "status": "completed", "...": "..." } ]
}
```

### GET /evidence/{id}/analysis

List the analysis history for an evidence (newest first).

**Response 200:** array of `AnalysisRead` objects.

### DELETE /evidence/{id}

Soft-delete evidence. The stored file and all history are preserved for chain of
custody; the record is hidden from the default list. Writes an audit entry.

**Response 204** — No Content.
**Errors:** 404 — evidence not found.

---

## Analysis

### POST /evidence/{id}/analyze

Run an analysis on an evidence. Currently synchronous (queued in Phase 16).

**Request body — `AnalysisStart`:**
| Field | Type | Description |
|-------|------|-------------|
| analysis_type | enum | `frame_sampling` (default) or `scene_change` |
| sampling_rate | int | 1, 2, or 5 fps (default 1) |
| threshold | float | scene_change only, 0-1 (default 0.35) |

**Behavior:** records QUEUED → PROCESSING → COMPLETED/FAILED transitions on the
`Analysis` row and sets evidence status to `analyzed` on success. Writes an
audit entry.

**Response 200 — `AnalysisDetail`** (extends `AnalysisRead`):
```json
{
  "id": "b2e0f12a-7b71-4f83-9e6a-8a4f1c3d9e0a",
  "evidence_id": "657a9aa1-6baf-4f04-8cbf-fac1dcc43178",
  "analysis_type": "frame_sampling",
  "status": "completed",
  "params": { "sampling_rate": 1 },
  "started_at": "2026-08-10T11:30:00",
  "completed_at": "2026-08-10T11:30:05",
  "error_message": null,
  "result": { "frames_sampled": 3, "sampling_rate": 1, "...": "..." }
}
```

For `scene_change`, `result` contains `events` — each a "Potential anomaly" with
`timestamp`, `prev_frame`, `current_frame`, `diff_score`, `detection_method`,
`severity`, and the underlying `metrics` (MAD, histogram_diff, SSIM, phash).

**Errors:** 422 — unsupported type / sampling rate / threshold; 404 — evidence
not found; 500 — analysis failed (e.g. corrupt or unreadable file).

---

## Dashboard

### GET /dashboard/stats

Aggregate statistics for the dashboard.

**Response 200:**
```json
{
  "total_cases": 1,
  "total_evidence": 3,
  "analyses_completed": 2,
  "analyses_pending": 1,
  "analysis_status_distribution": { "completed": 2, "queued": 1 },
  "anomaly_distribution": { "low": 1 },
  "recent_evidence": [ { "id": "...", "original_filename": "...", "status": "uploaded" } ]
}
```

---

## Comparisons

### POST /comparisons

Compare an original evidence against a suspected copy.

**Request body — `ComparisonCreate`:**
| Field | Type | Description |
|-------|------|-------------|
| original_evidence_id | UUID | The preserved original |
| suspected_evidence_id | UUID | The suspected copy |

**Behavior:** compares file size, SHA-256/SHA-512 hashes, and technical
properties (duration, width, height, frame rate, frame count, bitrate, codecs,
pixel format, creation time, encoder) from the stored `video_metadata`. Run
metadata extraction on both evidence items first so technical fields are
available. A difference never implies tampering — it is a factual observation.

**Response 201 — `ComparisonRead`:**
```json
{
  "id": "3aa2d9dd-2cd6-4c34-a58b-c07d97ebaf26",
  "original_evidence_id": "9628b2b0-6c24-43a4-9ed3-efc2e24f7d58",
  "suspected_evidence_id": "d61b7446-ae95-4298-b138-14100895649f",
  "result": {
    "fields": [
      { "field": "sha256", "label": "SHA-256 hash", "status": "difference",
        "original": "50fe...", "suspected": "38dc...", "note": "SHA-256 hash differs between the two files" },
      { "field": "width", "label": "Width", "status": "difference", "original": 320, "suspected": 640, "note": "Width differs between the two files" }
    ],
    "summary": { "matches": 5, "differences": 8, "not_available": 2, "identical": false }
  },
  "created_by": "3cb96742-3cc4-41da-9cc7-ae3b640b5416",
  "created_at": "2026-08-10T12:05:00"
}
```

Per-field `status` is `match`, `difference`, or `not_available` (value missing on
one or both sides). `summary.identical` is only true when a cryptographic hash
matches and no differences are observed.

**Errors:** 404 — either evidence not found.

### GET /comparisons/{id}

Return a previously stored comparison with its structured result.

**Response 200 — `ComparisonRead`.**
**Errors:** 404 — comparison not found.

---

### GET /evidence/{id}/timeline

Build a suspicious timeline for an evidence item from its most recent completed
`scene_change` analysis.

**Response 200 — `TimelineResponse`:**

```json
{
  "evidence_id": "0b538cce-0c6b-436e-b77e-6743c1ccd447",
  "duration": 4.0,
  "analysis_id": "cb8d58cc-9b01-49c8-b1c1-f19328edbffe",
  "analysis_status": "completed",
  "segments": [
    { "kind": "normal", "start": 0.0, "end": 2.0, "severity": null, "event_index": null },
    { "kind": "anomaly", "start": 2.0, "end": 2.0, "severity": "high", "event_index": 0 }
  ],
  "events": [
    {
      "timestamp": 2.0,
      "severity": "high",
      "detection_method": "frame_difference",
      "diff_score": 1.0,
      "prev_frame": 11,
      "current_frame": 21,
      "metrics": { "mad": 1.0, "histogram_diff": 1.0, "ssim": 0.0001 },
      "analysis_id": "cb8d58cc-9b01-49c8-b1c1-f19328edbffe",
      "analysis_type": "scene_change"
    }
  ]
}
```

`normal` segments tile the full duration; `anomaly` segments are zero-width
markers (`start == end` = event timestamp) whose `event_index` points into
`events`. `duration` comes from `evidence.video_metadata.duration` (null if no
metadata). If the most recent scene-change analysis is not completed,
`segments`/`events` are empty. If none exists, `analysis_id` is null and status
is `"none"`.

**Errors:** 404 — evidence not found.

### GET /evidence/{id}/anomaly-score

Return the explainable "Anomaly Indicator Score" (0–100) for an evidence,
computed from the most recent completed `scene_change` analysis and persisted on
its result. Every factor is reported with its weight and a human-readable
reason so the score is never a black-box number. The score is an *indicator* —
not a probability of tampering.

**Response 200 — `AnomalyScoreRead`:**

```json
{
  "evidence_id": "ca8ed565-4cc4-4ac7-b847-e13577d4e494",
  "analysis_id": "79e6406d-8cb2-476b-81b0-7c933c0ec3f1",
  "score": 10,
  "category": "low",
  "factors": [
    { "name": "frame_discontinuity", "label": "Frame discontinuity", "max_points": 25, "points": 5, "reason": "1 abrupt frame replacement(s) detected" },
    { "name": "single_scene_changes", "label": "Single scene changes", "max_points": 5, "points": 5, "reason": "1 frame-difference event(s) recorded" }
  ],
  "computed_at": "2026-08-11T16:49:08.941727Z"
}
```

Category bands: 0–20 `low`, 21–50 `moderate`, 51–75 `high`, 76–100 `very_high`.
Factors: `metadata_inconsistency` (+15), `duration_difference` (+20),
`frame_discontinuity` (+25), `encoding_difference` (+15),
`unnatural_frame_diff_cluster` (+15), `single_scene_changes` (+5 max). The
score is recomputed automatically whenever a comparison involving the evidence
is created, so duration/encoding deviations against a reference are reflected.

When no scene-change analysis has run, `analysis_id`/`score`/`category` are
null and `factors` is empty.

**Errors:** 404 — evidence not found.

---

## Planned Endpoints (future phases)

| Phase | Endpoint |
|-------|----------|
| 16 | POST /evidence/{id}/analyze becomes async (Celery QUEUED → PROCESSING → COMPLETED/FAILED) |

## Authentication (Phase 14)

### POST /auth/login

Authenticate with email + password and receive a JWT.

```json
{ "email": "admin@example.com", "password": "secret" }
```

**Response 200:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": { "id": "...", "name": "Admin", "email": "admin@example.com", "role": "admin" }
}
```

**Errors:** 401 — invalid credentials (audited as `auth.login_failed`).

### GET /auth/me

Return the current authenticated user (requires `Authorization: Bearer <token>`).

## Users (Phase 14)

### GET /users, POST /users (admin)

List (paginated) and create users. `POST /users` body:
`{ "name": ..., "email": ..., "password": ..., "role": "admin|investigator|viewer" }`.

### PATCH /users/{id} (admin)

Update name/role/password.

## Reports (Phase 13)

### POST /reports

Generate a PDF forensic report. Body:
`{ "case_id": "...", "evidence_id": "..." }`. Returns the report record (201).

### GET /reports

List generated reports (paginated, newest first), optional `case_id` filter.

### GET /reports/{id}

Report record detail.

### GET /reports/{id}/download

Download the PDF file (`application/pdf`). Requires the Bearer token in headers.

## Audit Logs (Phase 15)

### GET /audit-logs

Admin-only. List audit entries with filters and pagination.

**Query params:** `page`, `page_size`, `user_id`, `entity_type`, `action`,
`date_from`, `date_to`.

**Response:** standard paginated shape with `items`, `page`, `page_size`,
`total`, `total_pages`. Each item:
```json
{
  "id": "...",
  "user_id": "..." | null,
  "action": "evidence.upload",
  "entity_type": "evidence",
  "entity_id": "..." | null,
  "timestamp": "2026-08-14T12:00:00Z",
  "ip_address": "127.0.0.1" | null,
  "user_agent": "..." | null,
  "details": { }
}
```

Audit rows are append-only: UPDATE and DELETE are blocked at the database level.
