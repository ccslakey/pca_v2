# ── Stage 1: build the React frontend ─────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# psycopg2-binary bundles libpq; only need gcc for any source builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Copy built React bundle from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Collect Django admin static files (does not touch the DB)
RUN DJANGO_DEBUG=False python manage.py collectstatic --noinput

EXPOSE 8000

# Migrate then start — runs on every deploy so schema stays in sync
CMD sh -c "python manage.py migrate --noinput && \
    gunicorn pca_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --threads 2 \
    --timeout 60"
