FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Railway passes service variables as build args when declared here. The
# browser DSN and PostHog project key are public by design (write-only).
ARG VITE_SENTRY_DSN
ARG VITE_SENTRY_ENVIRONMENT
ARG VITE_POSTHOG_KEY
ARG VITE_POSTHOG_HOST
RUN npm run build

FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the RAG embedding model into the image so containers never download it
# at runtime. Must match settings.EMBED_MODEL; readable by the non-root user.
ARG EMBED_MODEL=BAAI/bge-small-en-v1.5
# Official ONNX Runtime builds send usage telemetry to Microsoft unless disabled.
ENV FASTEMBED_CACHE_PATH=/opt/fastembed ORT_DISABLE_TELEMETRY=1
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('${EMBED_MODEL}')" \
    && chmod -R a+rX /opt/fastembed
ENV HF_HUB_OFFLINE=1

COPY . .

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN DJANGO_DEBUG=False python manage.py collectstatic --noinput

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

# Migrations run before each deploy, in Railway's pre-deploy command (predeploy.sh).
CMD sh -c "gunicorn pca_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --threads 2 \
    --timeout 60"
