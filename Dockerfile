# Multi-stage Dockerfile for StashHog

# Stage 1: Build frontend
FROM node:24-alpine AS frontend-builder

WORKDIR /app/frontend

# Install build dependencies for native modules
RUN apk add --no-cache python3 make g++

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (including dev dependencies for build)
# Use npm ci if package-lock.json exists, otherwise use npm install
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

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
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt ./

# Install Python dependencies
RUN pip install --user --no-warn-script-location -r requirements.txt

# Stage 4: Final production image
FROM python-base AS production

# Install runtime dependencies for PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies globally so any user can access them
COPY backend/requirements.txt ./
RUN pip install --no-warn-script-location -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy frontend build to static directory
COPY --from=frontend-builder /app/frontend/dist ./static

# Create a group for the app and set permissions
RUN groupadd -g 1000 appgroup && \
    chmod -R 755 /app && \
    # Make the app directory writable for any user in the group
    chmod -R 775 /app && \
    # Ensure Python can write bytecode if needed
    mkdir -p /app/__pycache__ && \
    chmod 777 /app/__pycache__

# Set up environment
ENV PYTHONPATH=/app

# Don't switch to a specific user - let Docker Compose handle it

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
