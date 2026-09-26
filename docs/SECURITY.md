# CCTV Forensic Analyzer — Security

## 1. Security Objectives

1. Preserve evidence integrity (original files never modified).
2. Protect confidentiality of evidence and case data.
3. Ensure accountability via append-only audit logging.
4. Enforce least-privilege access via role-based access control.
5. Defend the platform against common web attacks.

## 2. Threat Model

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Evidence tampering | Malicious/accidental file modification | Read-only originals, working copies for analysis, hash verification |
| Unauthorized access | Weak credentials, token theft | bcrypt hashing, JWT with expiry, rate limiting |
| Privilege escalation | IDOR, missing RBAC checks | require_role dependencies, object-ownership checks |
| Malicious upload | Executable disguised as video | Extension allowlist, size cap, magic-byte MIME validation, never execute |
| Path traversal | Filename with `../` | Generated server-side filenames; original filename never used on disk |
| SQL injection | Unsanitized input | ORM parameterized queries only; no raw SQL from user input |
| XSS | Stored user content | React escapes by default; no dangerouslySetInnerHTML; CSP headers |
| CSRF | Forged cross-site requests | SameSite cookies (if cookie-based), Bearer tokens in Authorization header |
| Audit log tampering | DB compromise / insider | Append-only rules, hashing of audit entries (Phase 15+), separate audit user |
| DoS | Large uploads, brute force | MAX_UPLOAD_SIZE, rate limiting on auth, pagination |
| Internal path disclosure | API error messages | Sanitize responses; never expose storage_path to clients |

## 3. Evidence Integrity

- Original evidence is written once and set read-only.
- `chmod(stat.S_IREAD)` on Windows; removal of write access.
- All analysis reads from `storage/evidence/processed/` working copies.
- SHA-256 and SHA-512 calculated from the actual stored bytes at upload time and on demand.
- A hash that changes between two calculations is a hard integrity mismatch and must be surfaced to the user.

## 4. Authentication

- Passwords hashed with bcrypt (cost factor 12+). Never store plaintext.
- JWT access tokens with short expiry (e.g., 30 min) + optional refresh token.
- Tokens signed with a long, random `JWT_SECRET` from environment (never committed).
- Login endpoints rate-limited to slow brute-force attempts.
- On logout/invalid token: reject with 401; client clears tokens.

## 5. Authorization (RBAC)

| Action | Admin | Investigator | Viewer |
|--------|-------|--------------|--------|
| Manage users | Yes | No | No |
| Create/edit cases | Yes | Yes | No |
| Upload evidence | Yes | Yes | No |
| Analyze evidence | Yes | Yes | No |
| Compare videos | Yes | Yes | No |
| Generate reports | Yes | Yes | No |
| View cases/evidence/reports | Yes | Yes | Assigned only |
| View audit logs | Yes | No | No |
| View users list | Yes | No | No |

Implementation: FastAPI dependencies `require_roles(...)` applied per endpoint, plus ownership/assignment checks for viewer access. Never rely on frontend-only guards.

## 4a. Request Hardening

- **Login rate limiting:** `/auth/login` is rate-limited per client IP using a sliding-window counter (`LOGIN_RATE_LIMIT`, default `5/minute`); excess attempts return `429`. Implemented in `app/core/rate_limit.py`.
- **Request body size limit:** non-multipart request bodies are capped (`MAX_REQUEST_BODY_SIZE`, default 1 MB) by `app/core/middleware.py`, returning `413`. Multipart uploads are exempt — the upload endpoint enforces its own `MAX_UPLOAD_SIZE` while streaming to disk.
- **CORS tightening:** origins limited to the configured allow-list; methods and headers restricted to a fixed set (no wildcards).
- **Strict schemas:** all input schemas use `extra="forbid"` so unknown fields are rejected with `422`.
- **Path safety:** internal storage paths never appear in API responses (verified by tests); all DB access is ORM-parameterized (no raw SQL from user input).

## 6. Upload Security

1. Filename extension allowlist: `.mp4`, `.mov`, `.avi`, `.mkv` (configurable).
2. Size limit: `MAX_UPLOAD_SIZE` (default 5 GB).
3. Magic-byte MIME detection (e.g., `python-magic` / `filetype`) — never trust the Content-Type header alone.
4. Empty-file and truncated-upload detection.
5. Server-generated stored filename: `{sha256_first_16}_{uuid4}{ext}`.
6. Store under `storage/evidence/originals/{case_id}/` — no user-supplied path components.
7. Quarantine directory for files that fail validation (retained for review, never executed).
8. Streaming writes to avoid loading huge files fully into memory.

## 7. Audit Logging

- Every mutating action: upload, hash, metadata extraction, analysis start/complete/fail, comparison, report, case/user changes, failed login attempts.
- Fields: user_id, action, entity_type, entity_id, timestamp, ip_address, user_agent, request_id, metadata JSON.
- Append-only enforced via PostgreSQL rules (block UPDATE/DELETE on audit_logs).
- Optional integrity: chain audit entries by storing hash of previous entry (Phase 15 enhancement).

## 8. Data Protection

- `.env` files git-ignored; secrets never committed.
- Evidence files never served directly through the API without authorization.
- Reports generated on demand and access-controlled.
- Database credentials from environment, scoped DB user (least privilege).
- For production: HTTPS, encrypted volumes (BitLocker), backups with retention policy. See [Deployment Guide](DEPLOYMENT.md) for containerized backup/restore.
- In Docker deployments, evidence and the database live in named volumes; a documented `pg_dump` + volume-tar backup strategy is provided.

## 9. Dependencies and Maintenance

- Pin dependency versions; review `pip-audit` / `npm audit` output.
- Keep FFmpeg/OpenCV updated for security fixes.
- Document the security review checklist before any production deployment.

## 10. Security Testing (in CI)

- Upload security tests: invalid extension, oversized, empty, bad magic bytes, path traversal.
- Auth/RBAC tests: wrong password, expired token, invalid signature, role matrix.
- API validation tests: malformed JSON, missing fields, wrong types, unknown fields rejected.
- Rate-limit tests: login brute-force exhaustion returns 429; counters reset between tests.
- Request-hardening tests: oversized JSON body returns 413; multipart uploads remain allowed; CORS preflight honours the configured origin and rejects others.
- Path-disclosure tests: no internal storage paths in any API response.
- SQL-injection tests: injection payloads in search/filters are parameterized and cannot drop tables.
- Dependency vulnerability scanning: `pip-audit` and `npm audit`.
- Lint: ruff (or flake8); type check: mypy; coverage threshold enforced in `pyproject.toml`.

## 11. Known Limitations (Honest Disclosure)

- JWT secret management (rotation) is documented but not automated in POC.
- Stored evidence is not encrypted at rest in the POC (documented as production hardening).
- Viewer "assigned cases" enforcement requires an assignment model (deferred; POC viewer scope is advisory).
- Audit-log hash chaining is a Phase 15 enhancement.
- The in-memory rate limiter is single-process only; a Redis-backed limiter is required for multi-worker deployments.
- The request-size middleware trusts the `Content-Length` header; HTTP/1.0 or chunked requests without it are bounded by Starlette's server default.
- CORS is permissive at the method/header level for API simplicity; production should further narrow allowed headers if needed.
