# Docker Build Documentation

## Overview

StashHog uses Docker for both development and production deployments. The Docker images include all necessary dependencies, including FFmpeg for video processing.

## Dockerfiles

### Production (`Dockerfile`)
Multi-stage build optimized for production:
- **Stage 1**: Frontend build (Node.js Alpine)
- **Stage 2**: Python base setup
- **Stage 3**: Backend dependencies
- **Stage 4**: Final production image with FFmpeg

### Development
- **Backend** (`backend/Dockerfile.dev`): Python 3.11 slim with FFmpeg
- **Frontend** (`frontend/Dockerfile.dev`): Node.js 18 Alpine

## FFmpeg Installation

FFmpeg is installed in both production and development images to support video duration detection in the Process Downloads job.

### Production Image
```dockerfile
# Install runtime dependencies for PostgreSQL and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

### Development Image
```dockerfile
# Install runtime dependencies including ffmpeg for video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

## Building Images

### Development
```bash
# Using docker-compose (recommended)
docker compose build

# Or build individually
docker build -f backend/Dockerfile.dev -t stashhog-backend-dev ./backend
docker build -f frontend/Dockerfile.dev -t stashhog-frontend-dev ./frontend
```

### Production
```bash
# Build production image
docker build -t stashhog:latest .

# Or with build arguments
docker build \
  --build-arg VERSION=1.0.0 \
  --build-arg BUILDTIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  --build-arg REVISION="$(git rev-parse --short HEAD)" \
  -t stashhog:latest .
```

## Verifying FFmpeg

After building, verify FFmpeg is available in your containers:

```bash
# Using the verification script
./scripts/verify-ffmpeg.sh

# Or manually
docker compose exec backend ffmpeg -version
docker compose exec backend ffprobe -version
```

## Running Containers

### Development
```bash
# Start all services
docker compose up -d

# Start with rebuild
docker compose up -d --build
```

### Production
```bash
# Using docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d

# Or run directly
docker run -d \
  --name stashhog \
  -p 8000:8000 \
  -v $(pwd)/data:/data \
  --env-file .env \
  stashhog:latest
```

## Video Processing Features

With FFmpeg installed, the following features are available:

1. **Video Duration Detection**: Automatically detect video file durations
2. **Small Video Filtering**: Option to skip videos under 30 seconds
3. **Statistics Tracking**: Track files by duration categories

### Process Downloads Job

The Process Downloads job uses FFmpeg to:
- Detect video files by extension
- Get accurate duration using `ffprobe`
- Track files under 30 seconds
- Optionally skip short videos when `exclude_small_vids` is enabled

## Troubleshooting

### FFmpeg Not Found
If FFmpeg is not available after building:

1. **Rebuild without cache**:
   ```bash
   docker compose build --no-cache backend
   ```

2. **Check installation**:
   ```bash
   docker compose exec backend which ffmpeg
   docker compose exec backend ffmpeg -version
   ```

3. **Verify in running container**:
   ```bash
   docker compose exec backend apt list --installed | grep ffmpeg
   ```

### Permission Issues
Ensure FFmpeg has execute permissions:
```bash
docker compose exec backend ls -la $(which ffmpeg)
```

## Resource Considerations

- FFmpeg adds approximately 60-80MB to the image size
- `ffprobe` operations are lightweight and fast
- Video analysis timeout is set to 10 seconds per file
- Processing continues even if FFmpeg fails for specific files