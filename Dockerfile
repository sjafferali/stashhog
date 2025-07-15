# Multi-stage Dockerfile for StashHog

# Stage 1: Build frontend
FROM node:24-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (including dev dependencies for build)
RUN npm ci

# Copy source code
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Stage 2: Python base
FROM python:3.13-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Stage 3: Build backend dependencies
FROM python-base AS backend-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt ./

# Install Python dependencies
RUN pip install --user --no-warn-script-location -r requirements.txt

# Stage 4: Final production image
FROM python-base AS production

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=backend-builder /root/.local /home/appuser/.local

# Copy backend code
COPY --chown=appuser:appuser backend/ ./

# Copy frontend build to static directory
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist ./static

# Set up environment
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Set build arguments for labels
ARG BUILDTIME
ARG VERSION
ARG REVISION

# Labels
LABEL org.opencontainers.image.created="${BUILDTIME}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.title="StashHog" \
      org.opencontainers.image.description="AI-powered content tagging for Stash" \
      org.opencontainers.image.vendor="StashHog Project" \
      org.opencontainers.image.licenses="MIT"

# Start the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]