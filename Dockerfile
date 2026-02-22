# ╔══════════════════════════════════════════════════════════╗
# ║  CodeQuery API – Multi-stage Dockerfile                 ║
# ╚══════════════════════════════════════════════════════════╝

FROM python:3.12-slim AS base

# Prevent Python from buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system deps (git is required for GitPython cloning)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python dependencies ─────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application code ───────────────────────────────
COPY . .

# ── Create directories ──────────────────────────────────
RUN mkdir -p /tmp/codequery_repos

# ── Default command: run the API server ──────────────────
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
