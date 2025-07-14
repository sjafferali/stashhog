# Task 15: Docker Deployment Configuration

## Current State
- Backend and frontend applications are complete
- No containerization configured
- No production deployment setup
- Development uses separate servers

## Objective
Create a production-ready Docker configuration that builds and serves both frontend and backend in a single container with proper optimization and security.

## Requirements

### Multi-Stage Dockerfile

1. **Dockerfile** - Main container definition:
   ```dockerfile
   # Stage 1: Frontend Builder
   FROM node:20-alpine as frontend-builder
   # Install dependencies
   # Build React app
   # Output to /app/dist
   
   # Stage 2: Backend Builder
   FROM python:3.11-slim as backend-builder
   # Install system dependencies
   # Copy and install Python deps
   # Compile Python files
   
   # Stage 3: Production Image
   FROM python:3.11-slim
   # Copy built frontend
   # Copy backend application
   # Install production dependencies
   # Configure Nginx
   # Set up supervisord
   ```

### Nginx Configuration

2. **nginx/nginx.conf** - Web server config:
   ```nginx
   # Features:
   - Serve static frontend files
   - Proxy /api to backend
   - WebSocket proxy for /ws
   - Gzip compression
   - Security headers
   - Cache control
   - Rate limiting
   ```

### Supervisor Configuration

3. **supervisord.conf** - Process manager:
   ```ini
   # Manage multiple processes:
   - Nginx web server
   - FastAPI backend
   - APScheduler daemon
   - Log rotation
   ```

### Environment Configuration

4. **.env.production** - Production defaults:
   ```bash
   # Application
   APP_ENV=production
   DEBUG=false
   
   # Database
   DATABASE_URL=sqlite:///data/stashhog.db
   
   # API
   API_WORKERS=4
   API_PORT=8000
   
   # Frontend
   VITE_API_URL=/api
   ```

### Docker Compose (Development)

5. **docker-compose.yml** - Development setup:
   ```yaml
   # Services:
   - backend (with hot reload)
   - frontend (with hot reload)
   - nginx (optional)
   
   # Volumes:
   - Source code
   - Database
   - Uploaded files
   ```

### Build Scripts

6. **scripts/build.sh** - Build script:
   ```bash
   #!/bin/bash
   # Build steps:
   - Run tests
   - Build frontend
   - Build backend
   - Create Docker image
   - Tag appropriately
   ```

### Health Checks

7. **scripts/healthcheck.sh** - Container health:
   ```bash
   #!/bin/bash
   # Check:
   - Backend API responds
   - Frontend assets load
   - Database accessible
   - Critical services running
   ```

### Production Optimizations

8. **Frontend optimizations**:
   - Code splitting
   - Tree shaking
   - Asset compression
   - CDN-ready paths
   - Service worker
   - Bundle analysis

9. **Backend optimizations**:
   - Compiled Python files
   - Connection pooling
   - Response caching
   - Static file serving
   - Async workers

### Security Hardening

10. **Security measures**:
    - Non-root user
    - Read-only filesystem
    - Minimal base image
    - No dev dependencies
    - Environment validation
    - Secret management

### Startup Script

11. **scripts/entrypoint.sh** - Container entry:
    ```bash
    #!/bin/bash
    # Startup tasks:
    - Validate environment
    - Run migrations
    - Create directories
    - Set permissions
    - Start supervisord
    ```

### Database Management

12. **Database considerations**:
    - Volume mounting
    - Backup strategy
    - Migration on startup
    - Connection pooling
    - WAL mode for SQLite

### Logging Configuration

13. **Logging setup**:
    - Centralized logging
    - Log rotation
    - Error aggregation
    - Performance metrics
    - Access logs

### Deployment Examples

14. **deployment/docker-run.sh**:
    ```bash
    # Example run commands
    # Basic run
    docker run -d \
      -p 80:80 \
      -v $(pwd)/data:/data \
      -e STASH_URL=http://stash:9999 \
      stashhog:latest
    ```

15. **deployment/kubernetes.yaml**:
    ```yaml
    # Kubernetes deployment
    # Resources:
    - Deployment
    - Service
    - ConfigMap
    - PersistentVolume
    - Ingress
    ```

### CI/CD Integration

16. **.github/workflows/docker.yml**:
    ```yaml
    # Build and push Docker image
    # Steps:
    - Run tests
    - Build image
    - Security scan
    - Push to registry
    - Deploy notification
    ```

### Documentation

17. **docs/deployment.md**:
    - System requirements
    - Installation steps
    - Configuration options
    - Upgrade procedures
    - Troubleshooting
    - Performance tuning

### Monitoring

18. **monitoring/prometheus.yml**:
    - Metrics endpoints
    - Scrape configs
    - Alert rules
    - Grafana dashboards

## Expected Outcome

After completing this task:
- Single Docker image serves entire app
- Production-ready configuration
- Optimized for performance
- Secure by default
- Easy deployment process
- Monitoring capabilities

## Integration Points
- All application components
- External services (Stash, OpenAI)
- Volume mounts for data
- Environment configuration
- Health monitoring

## Success Criteria
1. Docker image builds successfully
2. Container starts without errors
3. All services are accessible
4. Health checks pass
5. Performance is optimized
6. Security best practices
7. Logs are accessible
8. Graceful shutdown works
9. Documentation is complete