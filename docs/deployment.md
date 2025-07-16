# StashHog Deployment Guide

This guide covers deploying StashHog in production using Docker.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment Methods](#deployment-methods)
- [Security Considerations](#security-considerations)
- [Performance Tuning](#performance-tuning)
- [Monitoring](#monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Upgrade Procedures](#upgrade-procedures)

## System Requirements

### Minimum Requirements
- CPU: 2 cores
- RAM: 2GB
- Storage: 10GB (plus space for your media files)
- Docker: 20.10+ or Docker Compose: 1.29+

### Recommended Requirements
- CPU: 4+ cores
- RAM: 4GB+
- Storage: 50GB+ SSD
- Network: 100Mbps+

### Supported Platforms
- Linux (Ubuntu 20.04+, Debian 10+, CentOS 8+)
- macOS (with Docker Desktop)
- Windows (with Docker Desktop/WSL2)

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/stashhog/stashhog.git
cd stashhog
```

### 2. Configure Environment
```bash
# Copy the production environment template
cp .env.production .env

# Edit the configuration
nano .env
```

**Required configurations:**
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `JWT_SECRET_KEY`: Generate with `openssl rand -hex 32`
- `STASH_URL`: Your Stash instance URL
- `STASH_API_KEY`: Your Stash API key
- `OPENAI_API_KEY`: Your OpenAI API key (for AI features)

### 3. Build the Docker Image
```bash
./scripts/build.sh
```

### 4. Run the Container
```bash
./deployment/docker-run.sh
```

Access StashHog at http://localhost

## Configuration

### Environment Variables

#### Core Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_ENV` | Application environment | `production` | No |
| `DEBUG` | Debug mode | `false` | No |
| `LOG_LEVEL` | Logging level (deprecated - use `LOGGING__LEVEL`) | `info` | No |
| `LOGGING__LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |
| `SECRET_KEY` | Application secret key | - | **Yes** |
| `JWT_SECRET_KEY` | JWT signing key | - | **Yes** |

#### Database
| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection URL | `sqlite:////data/stashhog.db` |
| `DATABASE_POOL_SIZE` | Connection pool size | `20` |

#### Stash Integration
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `STASH_URL` | Stash server URL | - | **Yes** |
| `STASH_API_KEY` | Stash API key | - | **Yes** |
| `STASH_VERIFY_SSL` | Verify SSL certificates | `true` | No |

#### OpenAI Integration
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | For AI features |
| `OPENAI_MODEL` | Model to use | `gpt-4-vision-preview` | No |

### Volume Mounts

| Path | Purpose | Permissions |
|------|---------|-------------|
| `/data` | Database and uploads | Read/Write |
| `/logs` | Application logs | Read/Write |

## Deployment Methods

### Docker Run

Basic deployment:
```bash
docker run -d \
  --name stashhog \
  -p 80:80 \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/logs \
  --env-file .env \
  stashhog/stashhog:latest
```

With custom settings:
```bash
./deployment/docker-run.sh \
  --name my-stashhog \
  --port 8080 \
  --data-dir /opt/stashhog/data \
  --log-dir /opt/stashhog/logs
```

### Docker Compose

Production deployment:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

With monitoring:
```bash
docker-compose -f docker-compose.prod.yml --profile monitoring up -d
```

### Kubernetes

Deploy to Kubernetes:
```bash
# Create namespace and secrets
kubectl create namespace stashhog
kubectl create secret generic stashhog-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=JWT_SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=STASH_API_KEY=your-api-key \
  --from-literal=OPENAI_API_KEY=your-openai-key \
  -n stashhog

# Apply configuration
kubectl apply -f deployment/kubernetes.yaml

# Check status
kubectl get pods -n stashhog
```

### Systemd Service

Create a systemd service:
```bash
sudo tee /etc/systemd/system/stashhog.service << EOF
[Unit]
Description=StashHog
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/docker run --rm \
  --name stashhog \
  -p 80:80 \
  -v /opt/stashhog/data:/data \
  -v /opt/stashhog/logs:/logs \
  --env-file /opt/stashhog/.env \
  stashhog/stashhog:latest
ExecStop=/usr/bin/docker stop stashhog

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable stashhog
sudo systemctl start stashhog
```

## Security Considerations

### 1. Secret Management
- **Never** use default secret keys in production
- Store secrets in environment variables or secret management systems
- Rotate keys periodically

### 2. Network Security
- Use HTTPS with a reverse proxy (nginx, Traefik, Caddy)
- Implement rate limiting
- Configure firewall rules

### 3. Container Security
- Run as non-root user (default)
- Use read-only root filesystem where possible
- Scan images for vulnerabilities

### 4. Example HTTPS Setup with nginx

```nginx
server {
    listen 443 ssl http2;
    server_name stashhog.example.com;

    ssl_certificate /etc/ssl/certs/stashhog.crt;
    ssl_certificate_key /etc/ssl/private/stashhog.key;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Performance Tuning

### 1. API Workers
Adjust based on CPU cores:
```bash
API_WORKERS=4  # Default, good for 4+ cores
```

### 2. Database Optimization
For SQLite (default):
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;
```

### 3. Resource Limits
Docker Compose:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

### 4. Caching
Enable Redis for better performance:
```bash
CACHE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
```

## Monitoring

### Health Checks
- Main health endpoint: `http://localhost/health`
- Nginx health: `http://localhost/nginx-health`
- Metrics: `http://localhost/metrics` (if enabled)

### Logs
View logs:
```bash
# All logs
docker logs stashhog

# Follow logs
docker logs -f stashhog

# Specific component
tail -f logs/backend_stdout.log
```

### Prometheus Metrics
Enable metrics collection:
```yaml
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Backup and Recovery

### Automated Backups
Enable in docker-compose:
```bash
docker-compose -f docker-compose.prod.yml --profile backup up -d
```

### Manual Backup
```bash
# Backup database
docker exec stashhog sqlite3 /data/stashhog.db ".backup /data/backup.db"

# Copy to host
docker cp stashhog:/data/backup.db ./backups/stashhog_$(date +%Y%m%d).db
```

### Restore
```bash
# Stop the container
docker stop stashhog

# Restore database
docker run --rm -v $(pwd)/data:/data alpine \
  cp /data/backup.db /data/stashhog.db

# Start container
docker start stashhog
```

## Troubleshooting

### Enable Debug Logging
To see detailed debug information including GraphQL requests/responses:

```bash
# Set the environment variable
export LOGGING__LEVEL=DEBUG

# Or in docker-compose.yml:
environment:
  - LOGGING__LEVEL=DEBUG

# Or when running Docker:
docker run -e LOGGING__LEVEL=DEBUG ...
```

This will show:
- Full GraphQL queries and variables
- API response data
- Detailed sync operation logs
- Database query information

### Container Won't Start
1. Check logs: `docker logs stashhog`
2. Verify environment variables
3. Check disk space: `df -h`
4. Verify permissions on volumes

### Database Issues
```bash
# Check database integrity
docker exec stashhog sqlite3 /data/stashhog.db "PRAGMA integrity_check;"

# Repair database
docker exec stashhog sqlite3 /data/stashhog.db "VACUUM;"
```

### Performance Issues
1. Check resource usage: `docker stats stashhog`
2. Review logs for errors
3. Increase worker count
4. Enable caching

### Connection Issues
1. Verify Stash URL is accessible
2. Check API key validity
3. Review firewall rules
4. Test connectivity: `curl http://localhost/health`

## Upgrade Procedures

### 1. Backup Current Installation
```bash
./scripts/backup.sh
```

### 2. Pull New Image
```bash
docker pull stashhog/stashhog:latest
```

### 3. Stop Current Container
```bash
docker stop stashhog
```

### 4. Start New Container
```bash
./deployment/docker-run.sh
```

### 5. Verify Upgrade
- Check health endpoint
- Review logs for errors
- Test functionality

### Rollback Procedure
If issues occur:
```bash
# Stop new container
docker stop stashhog

# Restore previous version
docker run -d \
  --name stashhog \
  -p 80:80 \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/logs \
  --env-file .env \
  stashhog/stashhog:previous-version

# Restore database if needed
docker cp ./backups/pre-upgrade.db stashhog:/data/stashhog.db
```

## Additional Resources

- [GitHub Repository](https://github.com/stashhog/stashhog)
- [Issue Tracker](https://github.com/stashhog/stashhog/issues)
- [Docker Hub](https://hub.docker.com/r/stashhog/stashhog)
- [API Documentation](/api/docs)

## Support

For issues or questions:
1. Check the [FAQ](faq.md)
2. Search [existing issues](https://github.com/stashhog/stashhog/issues)
3. Create a [new issue](https://github.com/stashhog/stashhog/issues/new)
4. Join our [Discord community](https://discord.gg/stashhog)