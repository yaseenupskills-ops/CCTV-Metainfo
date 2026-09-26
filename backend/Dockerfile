# Backend image for the CCTV Forensic Analyzer.
# Includes Python runtime, FFmpeg/FFprobe, the FastAPI app and Alembic migrations.
# Same image is used for the Celery worker (command overridden in compose).

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# FFmpeg ships ffprobe, required for metadata extraction. libglib2.0-0 and
# libgomp1 are runtime deps of opencv-python-headless on slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user; /app/storage is owned by it so the named volume
# mounted there (docker's copy-up) is writable by the container.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/storage \
    && chown -R appuser:appuser /app

# Install Python dependencies first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
