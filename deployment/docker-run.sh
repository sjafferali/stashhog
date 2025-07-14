#!/bin/bash
set -euo pipefail

# Docker run script for StashHog
# Usage: ./deployment/docker-run.sh [options]

# Default values
CONTAINER_NAME="stashhog"
IMAGE_NAME="stashhog/stashhog"
IMAGE_TAG="latest"
PORT="80"
DATA_DIR="$(pwd)/data"
LOG_DIR="$(pwd)/logs"
ENV_FILE=".env.production"
RESTART_POLICY="unless-stopped"
DETACH="-d"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --no-detach)
            DETACH=""
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --name NAME        Container name (default: stashhog)"
            echo "  --port PORT        Host port to bind (default: 80)"
            echo "  --data-dir DIR     Data directory (default: ./data)"
            echo "  --log-dir DIR      Log directory (default: ./logs)"
            echo "  --env-file FILE    Environment file (default: .env.production)"
            echo "  --tag TAG          Image tag (default: latest)"
            echo "  --no-detach        Run in foreground"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting StashHog container...${NC}"

# Check if container already exists
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo -e "${YELLOW}Container '$CONTAINER_NAME' already exists${NC}"
    read -p "Do you want to remove it and create a new one? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping and removing existing container..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
    else
        echo "Exiting..."
        exit 1
    fi
fi

# Create directories if they don't exist
mkdir -p "$DATA_DIR" "$LOG_DIR"

# Check if environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${YELLOW}Warning: Environment file '$ENV_FILE' not found${NC}"
    echo "Creating from template..."
    if [[ -f ".env.production" ]]; then
        cp .env.production "$ENV_FILE"
        echo -e "${GREEN}Created $ENV_FILE from template${NC}"
        echo -e "${YELLOW}Please edit $ENV_FILE and set your configuration values${NC}"
        exit 1
    else
        echo -e "${RED}Error: No environment template found${NC}"
        exit 1
    fi
fi

# Run the container
echo "Starting container with:"
echo "  Name: $CONTAINER_NAME"
echo "  Image: $IMAGE_NAME:$IMAGE_TAG"
echo "  Port: $PORT"
echo "  Data: $DATA_DIR"
echo "  Logs: $LOG_DIR"
echo "  Env: $ENV_FILE"
echo ""

docker run $DETACH \
    --name "$CONTAINER_NAME" \
    --restart "$RESTART_POLICY" \
    -p "${PORT}:80" \
    -v "$DATA_DIR:/data" \
    -v "$LOG_DIR:/logs" \
    --env-file "$ENV_FILE" \
    --health-cmd "/usr/local/bin/healthcheck.sh" \
    --health-interval 30s \
    --health-timeout 10s \
    --health-retries 3 \
    --health-start-period 60s \
    "$IMAGE_NAME:$IMAGE_TAG"

if [[ -n "$DETACH" ]]; then
    # Wait a moment for container to start
    sleep 3
    
    # Check if container is running
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}Container started successfully!${NC}"
        echo ""
        echo "Container status:"
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        echo "To view logs: docker logs -f $CONTAINER_NAME"
        echo "To stop: docker stop $CONTAINER_NAME"
        echo "To remove: docker rm $CONTAINER_NAME"
        echo ""
        echo -e "${GREEN}StashHog is available at: http://localhost:${PORT}${NC}"
    else
        echo -e "${RED}Container failed to start!${NC}"
        echo "Check logs with: docker logs $CONTAINER_NAME"
        exit 1
    fi
fi