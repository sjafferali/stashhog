#!/bin/bash
# Script to verify ffmpeg is available in Docker containers

echo "Verifying ffmpeg installation in Docker containers..."
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check ffmpeg in a container
check_ffmpeg() {
    local container_name=$1
    local service_name=$2
    
    echo -n "Checking $service_name... "
    
    # Check if ffmpeg and ffprobe are available
    if docker compose exec -T $container_name which ffmpeg > /dev/null 2>&1; then
        ffmpeg_version=$(docker compose exec -T $container_name ffmpeg -version 2>&1 | head -n1)
        echo -e "${GREEN}✓ ffmpeg found${NC}"
        echo "  Version: $ffmpeg_version"
    else
        echo -e "${RED}✗ ffmpeg not found${NC}"
        return 1
    fi
    
    if docker compose exec -T $container_name which ffprobe > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ ffprobe available${NC}"
    else
        echo -e "  ${RED}✗ ffprobe not found${NC}"
        return 1
    fi
    
    return 0
}

# Check which docker-compose file to use
if [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
elif [ -f "docker-compose.prod.yml" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    echo -e "${RED}No docker-compose file found${NC}"
    exit 1
fi

echo "Using $COMPOSE_FILE"
echo ""

# Check if containers are running
if ! docker compose ps | grep -q "Up"; then
    echo -e "${RED}Docker containers are not running. Please start them first.${NC}"
    echo "Run: docker compose up -d"
    exit 1
fi

# Check backend container
check_ffmpeg "backend" "Backend container"

echo ""
echo "=================================================="
echo "Verification complete!"