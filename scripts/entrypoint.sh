#!/bin/bash
set -euo pipefail

# StashHog container entrypoint script
# Handles initialization, migrations, and startup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DATA_DIR="${APP_DATA_DIR:-/data}"
LOG_DIR="${APP_LOG_DIR:-/logs}"
BACKEND_DIR="/app/backend"

echo -e "${BLUE}=== StashHog Container Startup ===${NC}"
echo "Version: ${VERSION:-unknown}"
echo "Environment: ${APP_ENV:-production}"
echo "Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Function to create directories
create_directories() {
    echo -e "${YELLOW}Creating required directories...${NC}"
    
    directories=(
        "$DATA_DIR"
        "$DATA_DIR/uploads"
        "$DATA_DIR/backups"
        "$LOG_DIR"
        "/run/nginx"
        "/var/log/supervisor"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            echo "  Created: $dir"
        fi
    done
    
    # Set permissions
    chown -R appuser:appuser "$DATA_DIR" "$LOG_DIR" /run/nginx /var/log/supervisor
    chmod -R 755 "$DATA_DIR" "$LOG_DIR"
    
    echo -e "${GREEN}Directories ready${NC}"
}

# Function to validate environment
validate_environment() {
    echo -e "${YELLOW}Validating environment...${NC}"
    
    # Required environment variables
    required_vars=(
        "SECRET_KEY"
        "JWT_SECRET_KEY"
    )
    
    missing_vars=0
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo -e "  ${RED}Missing required variable: $var${NC}"
            ((missing_vars++))
        fi
    done
    
    if [[ $missing_vars -gt 0 ]]; then
        echo -e "${RED}Environment validation failed!${NC}"
        echo "Please set all required environment variables."
        exit 1
    fi
    
    # Warn about default values
    if [[ "${SECRET_KEY}" == *"please-change"* ]]; then
        echo -e "  ${YELLOW}WARNING: Using default SECRET_KEY - change in production!${NC}"
    fi
    
    if [[ "${JWT_SECRET_KEY}" == *"please-change"* ]]; then
        echo -e "  ${YELLOW}WARNING: Using default JWT_SECRET_KEY - change in production!${NC}"
    fi
    
    # Optional but recommended variables
    optional_vars=(
        "STASH_URL"
        "OPENAI_API_KEY"
    )
    
    for var in "${optional_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo -e "  ${YELLOW}Optional variable not set: $var${NC}"
        fi
    done
    
    echo -e "${GREEN}Environment validated${NC}"
}

# Function to initialize database
initialize_database() {
    echo -e "${YELLOW}Initializing database...${NC}"
    
    cd "$BACKEND_DIR"
    
    # Check if database exists
    if [[ -f "$DATA_DIR/stashhog.db" ]]; then
        echo "  Database exists at $DATA_DIR/stashhog.db"
        
        # Backup existing database
        backup_file="$DATA_DIR/backups/stashhog_$(date +%Y%m%d_%H%M%S).db"
        cp "$DATA_DIR/stashhog.db" "$backup_file"
        echo "  Created backup: $backup_file"
    else
        echo "  Creating new database..."
    fi
    
    # Update database URL to use the data directory
    export DATABASE_URL="sqlite:///$DATA_DIR/stashhog.db"
    
    # Run migrations
    echo "  Running database migrations..."
    python -m alembic upgrade head
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}Database initialized successfully${NC}"
    else
        echo -e "${RED}Database initialization failed!${NC}"
        exit 1
    fi
}

# Function to create default admin user
create_admin_user() {
    if [[ -n "${ADMIN_USERNAME:-}" && -n "${ADMIN_PASSWORD:-}" && -n "${ADMIN_EMAIL:-}" ]]; then
        echo -e "${YELLOW}Creating admin user...${NC}"
        
        cd "$BACKEND_DIR"
        python -c "
from app.core.database import get_db
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy.orm import Session

db = next(get_db())
existing = db.query(User).filter_by(username='${ADMIN_USERNAME}').first()
if not existing:
    admin = User(
        username='${ADMIN_USERNAME}',
        email='${ADMIN_EMAIL}',
        hashed_password=get_password_hash('${ADMIN_PASSWORD}'),
        is_admin=True,
        is_active=True
    )
    db.add(admin)
    db.commit()
    print('Admin user created successfully')
else:
    print('Admin user already exists')
"
    fi
}

# Function to generate configs
generate_configs() {
    echo -e "${YELLOW}Generating configuration files...${NC}"
    
    # Generate logging configuration if not exists
    if [[ ! -f "$BACKEND_DIR/logging.json" ]]; then
        cat > "$BACKEND_DIR/logging.json" << EOF
{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "${LOG_LEVEL:-INFO}",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "${LOG_LEVEL:-INFO}",
            "formatter": "json",
            "filename": "$LOG_DIR/stashhog.log",
            "maxBytes": 104857600,
            "backupCount": 10
        }
    },
    "root": {
        "level": "${LOG_LEVEL:-INFO}",
        "handlers": ["console", "file"]
    }
}
EOF
        echo "  Generated logging configuration"
    fi
    
    # Create log rotation script
    cat > /usr/local/bin/log-rotate.sh << 'EOF'
#!/bin/bash
# Simple log rotation script
find /logs -name "*.log" -size +100M -exec mv {} {}.old \;
find /logs -name "*.log.old" -mtime +7 -delete
EOF
    chmod +x /usr/local/bin/log-rotate.sh
    
    echo -e "${GREEN}Configurations generated${NC}"
}

# Function to set up monitoring
setup_monitoring() {
    if [[ "${ENABLE_METRICS:-true}" == "true" ]]; then
        echo -e "${YELLOW}Setting up monitoring...${NC}"
        
        # Create simple monitoring scripts
        cat > "$BACKEND_DIR/app/monitor.py" << 'EOF'
#!/usr/bin/env python3
import sys
import logging
from supervisor.childutils import listener

def main():
    while True:
        headers, payload = listener.wait()
        if headers['eventname'] in ['PROCESS_STATE_FATAL', 'PROCESS_STATE_EXITED']:
            logging.error(f"Process event: {headers['eventname']} - {payload}")
        listener.ok()

if __name__ == '__main__':
    main()
EOF
        chmod +x "$BACKEND_DIR/app/monitor.py"
        
        echo -e "${GREEN}Monitoring configured${NC}"
    fi
}

# Function to wait for services
wait_for_services() {
    echo -e "${YELLOW}Waiting for services to start...${NC}"
    
    # Wait for backend
    max_attempts=30
    attempt=0
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s -f http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}Backend is ready${NC}"
            break
        fi
        ((attempt++))
        echo -n "."
        sleep 2
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        echo -e "${RED}Backend failed to start!${NC}"
        exit 1
    fi
}

# Main execution
main() {
    # Trap signals for graceful shutdown
    trap 'echo -e "${YELLOW}Shutting down...${NC}"; supervisorctl stop all; exit 0' SIGTERM SIGINT
    
    # Run initialization steps
    create_directories
    validate_environment
    initialize_database
    create_admin_user
    generate_configs
    setup_monitoring
    
    echo -e "${BLUE}Starting services...${NC}"
    
    # Start supervisord
    exec "$@"
}

# Run main function
main "$@"