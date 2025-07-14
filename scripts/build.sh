#!/bin/bash
set -euo pipefail

# Build script for StashHog Docker image
# Usage: ./scripts/build.sh [version] [--push] [--no-cache]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
VERSION=${1:-latest}
PUSH=false
NO_CACHE=""
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
IMAGE_NAME="stashhog/stashhog"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --push)
            PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
    esac
done

echo -e "${GREEN}Building StashHog Docker image...${NC}"
echo "Version: $VERSION"
echo "Git ref: $VCS_REF"
echo "Build date: $BUILD_DATE"
echo ""

# Check if required files exist
echo -e "${YELLOW}Checking required files...${NC}"
required_files=(
    "Dockerfile.production"
    "nginx/nginx.conf"
    "supervisord.conf"
    "scripts/entrypoint.sh"
    "scripts/healthcheck.sh"
    "backend/requirements.txt"
    "frontend/package.json"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo -e "${RED}Error: Required file $file not found${NC}"
        exit 1
    fi
done
echo -e "${GREEN}All required files found${NC}"

# Run tests (optional)
if [[ -z "${SKIP_TESTS:-}" ]]; then
    echo -e "\n${YELLOW}Running tests...${NC}"
    
    # Backend tests
    if command -v pytest &> /dev/null; then
        echo "Running backend tests..."
        cd backend && pytest -v --tb=short || { echo -e "${RED}Backend tests failed${NC}"; exit 1; }
        cd ..
    else
        echo -e "${YELLOW}Warning: pytest not found, skipping backend tests${NC}"
    fi
    
    # Frontend tests
    if [[ -f "frontend/package.json" ]] && grep -q "test" frontend/package.json; then
        echo "Running frontend tests..."
        cd frontend && npm test -- --watchAll=false || { echo -e "${RED}Frontend tests failed${NC}"; exit 1; }
        cd ..
    else
        echo -e "${YELLOW}Warning: No frontend tests configured${NC}"
    fi
else
    echo -e "${YELLOW}Skipping tests (SKIP_TESTS is set)${NC}"
fi

# Build the Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build \
    $NO_CACHE \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg VCS_REF="$VCS_REF" \
    -t "$IMAGE_NAME:$VERSION" \
    -t "$IMAGE_NAME:latest" \
    -f Dockerfile.production \
    .

if [[ $? -ne 0 ]]; then
    echo -e "${RED}Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}Docker image built successfully${NC}"

# Run security scan
if command -v trivy &> /dev/null; then
    echo -e "\n${YELLOW}Running security scan...${NC}"
    trivy image --severity CRITICAL,HIGH "$IMAGE_NAME:$VERSION"
else
    echo -e "${YELLOW}Warning: trivy not found, skipping security scan${NC}"
fi

# Tag additional versions
if [[ "$VERSION" != "latest" ]]; then
    # Tag with major version (e.g., 1.2.3 -> 1)
    MAJOR_VERSION=$(echo "$VERSION" | cut -d. -f1)
    if [[ "$MAJOR_VERSION" =~ ^[0-9]+$ ]]; then
        docker tag "$IMAGE_NAME:$VERSION" "$IMAGE_NAME:$MAJOR_VERSION"
    fi
    
    # Tag with minor version (e.g., 1.2.3 -> 1.2)
    MINOR_VERSION=$(echo "$VERSION" | cut -d. -f1,2)
    if [[ "$MINOR_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
        docker tag "$IMAGE_NAME:$VERSION" "$IMAGE_NAME:$MINOR_VERSION"
    fi
fi

# Show image info
echo -e "\n${GREEN}Image built successfully:${NC}"
docker images "$IMAGE_NAME"

# Push to registry if requested
if [[ "$PUSH" == true ]]; then
    echo -e "\n${YELLOW}Pushing to Docker registry...${NC}"
    
    # Push all tags
    docker push "$IMAGE_NAME:$VERSION"
    docker push "$IMAGE_NAME:latest"
    
    if [[ -n "${MAJOR_VERSION:-}" ]]; then
        docker push "$IMAGE_NAME:$MAJOR_VERSION"
    fi
    if [[ -n "${MINOR_VERSION:-}" ]]; then
        docker push "$IMAGE_NAME:$MINOR_VERSION"
    fi
    
    echo -e "${GREEN}Images pushed successfully${NC}"
else
    echo -e "\n${YELLOW}To push the image, run: $0 $VERSION --push${NC}"
fi

# Output example run command
echo -e "\n${GREEN}To run the container:${NC}"
echo "docker run -d \\"
echo "  --name stashhog \\"
echo "  -p 80:80 \\"
echo "  -v \$(pwd)/data:/data \\"
echo "  -v \$(pwd)/logs:/logs \\"
echo "  --env-file .env.production \\"
echo "  $IMAGE_NAME:$VERSION"

echo -e "\n${GREEN}Build completed successfully!${NC}"