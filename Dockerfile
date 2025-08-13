# Multi-stage Dockerfile for StashHog - Optimized Version

# Stage 1: Frontend Builder
FROM node:24-alpine AS frontend-builder

WORKDIR /app/frontend

# Install build dependencies for native modules (combine layers)
RUN apk add --no-cache python3 make g++

# Copy only package files for better cache utilization
COPY frontend/package*.json ./

# Install dependencies with proper platform-specific handling
RUN npm ci --only=production && \
    npm install @rollup/rollup-linux-x64-musl

# Copy source and build
COPY frontend/ ./
RUN npm run build && \
    # Clean up unnecessary files after build
    rm -rf node_modules src tests *.config.* *.json

# Stage 2: Python Dependencies Builder
FROM python:3.13-slim AS python-builder

# Set environment for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies in single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt ./

# Create wheels for better caching and faster installs
RUN pip wheel --wheel-dir=/app/wheels -r requirements.txt

# Stage 3: Production Image
FROM python:3.13-slim AS production

# Set runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install runtime dependencies in single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Create app group and directories
    groupadd -g 1000 appgroup && \
    mkdir -p /app/__pycache__ && \
    chmod 777 /app/__pycache__

# Copy wheels from builder and install
COPY --from=python-builder /app/wheels /wheels
RUN pip install --no-deps /wheels/*.whl && \
    rm -rf /wheels

# Copy application code
COPY backend/ ./

# Copy frontend build
COPY --from=frontend-builder /app/frontend/dist ./static

# Set permissions in single layer
RUN chmod -R 755 /app && \
    chmod -R 775 /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Build arguments for labels
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

# Start application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]