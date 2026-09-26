# CCTV Forensic Analyzer — Setup Guide (Windows)

This guide covers installing every prerequisite and starting the development environment on Windows. Follow it in order. Each section explains why each tool is needed.

## 1. Prerequisites Overview

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ (LTS) | Frontend runtime |
| PostgreSQL | 16.x | Main database |
| FFmpeg / FFprobe | latest | Video metadata + processing |
| Redis | 7.x | Celery broker (background jobs) |
| Git | latest | Version control |
| PowerShell 7 | current | Shell (this guide assumes pwsh) |

---

## 2. Python

### Install

1. Download from https://www.python.org/downloads/
2. Run installer.
3. Check "Add python.exe to PATH" during install.
4. Optional: install via winget:
   ```powershell
   winget install -e --id Python.Python.3.11
   ```

### Verify

```powershell
python --version
pip --version
```

### Create a virtual environment

Always work inside a virtual environment for this project.

```powershell
# from the project root
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks scripts (execution policy), run once:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 3. Node.js

### Install

```powershell
winget install -e --id OpenJS.NodeJS.LTS
```

Or download from https://nodejs.org/

### Verify

```powershell
node --version
npm --version
```

---

## 4. PostgreSQL

### Install

```powershell
winget install -e --id PostgreSQL.PostgreSQL.16
```

Or download the installer from https://www.postgresql.org/download/windows/

During install:
- Set a postgres superuser password (remember it; put it in `.env` later).
- Keep default port 5432.
- The installer registers PostgreSQL as a Windows service.

### Create the application database and user

Open the SQL shell (psql) or use pgAdmin query tool, and run:

```sql
CREATE ROLE cctv_user WITH LOGIN PASSWORD 'change-me-strong';
CREATE DATABASE cctv_forensics OWNER cctv_user;
```

### Verify the service is running

```powershell
Get-Service postgresql*
```

The status should be Running.

---

## 5. FFmpeg and FFprobe

FFmpeg is the backbone of video processing. FFprobe reads metadata.

### Option A: WinGet (recommended)

```powershell
winget install --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
```

Restart the terminal after install. Gyan's is a full build with all codecs.

### Option B: Chocolatey

```powershell
choco install ffmpeg
```

### Option C: Manual (full build, no codecs skipped)

1. Download the "ffmpeg-release-full" zip from https://www.gyan.dev/ffmpeg/builds/
2. Extract to `C:\ffmpeg`.
3. Add `C:\ffmpeg\bin` to the system PATH:
   - Win+R -> sysdm.cpl -> Advanced -> Environment Variables
   - Under System variables, select Path -> Edit -> New
   - Add `C:\ffmpeg\bin`
   - OK on all dialogs. Restart any open terminals.

### Verify

```powershell
ffmpeg -version
ffprobe -version
```

Both should print version info. If you see "not recognized", the PATH is not set.

### Troubleshooting

- Some builds ship a bare-bones ffmpeg without codecs. Use the gyan "full" build or the BtbN "ffmpeg-master-latest-win64-gpl" build from GitHub.
- If ffprobe is missing separately, it ships inside the same ffmpeg bin folder.

---

## 6. Redis

Redis is only needed from Phase 16 onward (Celery background workers). You can skip it until then.

### Option A: Docker Desktop (recommended if you will use Docker)

```powershell
docker run -d --name redis -p 6379:6379 redis:7
```

### Option B: Native Windows

Redis does not officially support native Windows. Use:
- Memurai (Redis-compatible for Windows): https://www.memurai.com/
- Or the tporadowski redis builds: https://github.com/tporadowski/redis/releases (download the msi, install as a service)

### Verify

```powershell
redis-cli ping
```

Should return `PONG`.

---

## 7. Git

### Install

```powershell
winget install -e --id Git.Git
```

### Verify

```powershell
git --version
```

---

## 8. Project Bootstrap

```powershell
# 1. Clone or navigate into the project folder
cd "CCTV MetaInfo"

# 2. Copy environment templates
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env

# 3. Backend dependencies
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### Apply database migrations

```powershell
alembic upgrade head
```

### Seed initial data (admin user, demo case)

```powershell
python -m app.db.seed
```

### Start the backend

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for the interactive API docs.

### Start the frontend

```powershell
cd ..\frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## 9. Environment Variables

Copy `.env.example` to `.env` (see section 8) and edit values. Key variables:

| Variable | Example | Notes |
|----------|---------|-------|
| DATABASE_URL | postgresql+psycopg://cctv_user:pass@localhost:5432/cctv_forensics | Use psycopg (v3) driver |
| JWT_SECRET | generate-a-long-random-string | Use at least 32 random chars |
| STORAGE_PATH | ./storage | Evidence storage root |
| MAX_UPLOAD_SIZE | 5368709120 | 5 GB in bytes |
| FFMPEG_PATH | ffmpeg | Binary name or full path |
| FFPROBE_PATH | ffprobe | Binary name or full path |
| REDIS_URL | redis://localhost:6379/0 | Used from Phase 16 |
| ALLOWED_EXTENSIONS | `[".mp4",".mov"]` | List values must be JSON arrays (pydantic-settings v2.15+) |
| CORS_ORIGINS | `["http://localhost:5173"]` | JSON array, same rule applies |

Generate a JWT secret:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 10. Common Windows Issues

| Problem | Fix |
|---------|-----|
| Scripts blocked by execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| ffmpeg not recognized | Add `C:\ffmpeg\bin` to PATH, restart terminal |
| Port 5432 in use | Check `Get-NetTCPConnection -LocalPort 5432`; adjust DATABASE_URL port |
| Port 8000 in use | Change uvicorn port, or kill the process `Get-NetTCPConnection -LocalPort 8000 \| Select-Object OwningProcess` |
| OneDrive path too long | Enable long paths, or move project out of OneDrive folder |
| pip install fails on wheels | Upgrade pip first: `python -m pip install --upgrade pip` |
| OpenCV needs FFmpeg codecs | Use `pip install opencv-python-headless`; rely on FFmpeg binary for processing instead of cv2.VideoCapture for exotic formats |

---

## 11. Optional: Windows Services Checklist

To run everything as Windows services:

| Service | Check |
|---------|-------|
| PostgreSQL | `Get-Service postgresql*` |
| Redis (Memurai or tporadowski) | `Get-Service *redis*` or `Get-Service *memurai*` |
| Backend | Run via NSSM, or simply keep terminal open |
| Frontend | Run via terminal (dev), or build + serve statically |

---

## 12. Next Steps

After the environment is up, continue to docs/DEVELOPMENT_ROADMAP.md to begin Phase-by-phase implementation.
