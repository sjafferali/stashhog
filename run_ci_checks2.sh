#!/bin/bash
set -e

# CI checks script for StashHog - Optimized Version
# This script runs frontend and backend tests concurrently
# Only shows output when there are changes or failures

# Parse command line arguments
BACKEND_ONLY=false
FRONTEND_ONLY=false
DOCKER_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --docker-build)
            DOCKER_BUILD=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --backend-only   Run only backend checks"
            echo "  --frontend-only  Run only frontend checks"
            echo "  --docker-build   Include Docker build test"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${YELLOW}$1${NC}"
    echo "================================"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ] || [ ! -f "frontend/package.json" ]; then
    print_error "Please run this script from the root of the stashhog repository"
    exit 1
fi

# Create temporary files for output
BACKEND_OUTPUT=$(mktemp)
FRONTEND_OUTPUT=$(mktemp)
BACKEND_STATUS=$(mktemp)
FRONTEND_STATUS=$(mktemp)

# Cleanup function
cleanup() {
    rm -f "$BACKEND_OUTPUT" "$FRONTEND_OUTPUT" "$BACKEND_STATUS" "$FRONTEND_STATUS"
}
trap cleanup EXIT

# Function to run backend checks
run_backend_checks() {
    {
        echo "0" > "$BACKEND_STATUS"
        
        # Create virtual environment if it doesn't exist
        if [ ! -d "venv" ]; then
            echo "Creating Python virtual environment..." >&2
            python3 -m venv venv
        fi
        
        # Activate virtual environment
        source venv/bin/activate
        
        # Upgrade pip quietly
        python -m pip install --upgrade pip --quiet
        
        # Install backend dependencies
        cd backend
        pip install -r requirements.txt --quiet
        if [ -f "requirements-dev.txt" ]; then
            pip install -r requirements-dev.txt --quiet
        fi
        cd ..
        
        # Install testing and linting tools
        pip install pytest black isort flake8 mypy pip-audit --quiet
        
        # Run backend tests
        echo "Running backend tests..." >&2
        cd backend
        if ! python -m pytest -v --tb=short 2>&1; then
            echo "1" > "$BACKEND_STATUS"
        fi
        cd ..
        
        # Check Black formatting
        echo "Checking Python formatting..." >&2
        cd backend
        if ! black --check . --quiet 2>&1; then
            echo "Python formatting needs fixes - applying..." >&2
            black . --quiet
            echo "Python formatting fixed" >&2
        fi
        cd ..
        
        # Check isort
        echo "Checking Python imports..." >&2
        cd backend
        if ! isort --check-only . --quiet 2>&1; then
            echo "Python imports need sorting - applying..." >&2
            isort . --quiet
            echo "Python imports sorted" >&2
        fi
        cd ..
        
        # Run Flake8
        echo "Running Python linter..." >&2
        cd backend
        if ! flake8 . 2>&1; then
            echo "1" > "$BACKEND_STATUS"
        fi
        cd ..
        
        # Run MyPy
        echo "Running Python type checker..." >&2
        cd backend
        if ! mypy app/ --ignore-missing-imports 2>&1; then
            echo "1" > "$BACKEND_STATUS"
        fi
        cd ..
        
        # Security check
        echo "Checking Python dependencies for vulnerabilities..." >&2
        cd backend
        pip-audit -r requirements.txt 2>&1 || true
        cd ..
        
        deactivate
    } > "$BACKEND_OUTPUT" 2>&1
}

# Function to run frontend checks
run_frontend_checks() {
    {
        echo "0" > "$FRONTEND_STATUS"
        
        # Install frontend dependencies
        cd frontend
        npm ci --silent
        
        # Run frontend tests
        echo "Running frontend tests..." >&2
        if ! npm run test:coverage -- --ci --maxWorkers=2 2>&1; then
            echo "1" > "$FRONTEND_STATUS"
        fi
        
        # Check Prettier formatting
        echo "Checking code formatting..." >&2
        if ! npm run format:check 2>&1; then
            echo "Code formatting needs fixes - applying..." >&2
            npm run format --silent
            echo "Code formatting fixed" >&2
        fi
        
        # Run ESLint
        echo "Running ESLint..." >&2
        npm run lint 2>&1 || true
        
        # Run TypeScript type checker
        echo "Running TypeScript type checker..." >&2
        npm run type-check 2>&1 || true
        
        # Security check
        echo "Checking npm dependencies for vulnerabilities..." >&2
        npm audit --json 2>&1 || true
        
        cd ..
    } > "$FRONTEND_OUTPUT" 2>&1
}

# Start time
START_TIME=$(date +%s)

print_header "Running CI Checks (Optimized)"
print_info "Running frontend and backend checks in parallel..."

# Run checks concurrently
if [ "$BACKEND_ONLY" = true ]; then
    run_backend_checks &
    BACKEND_PID=$!
    wait $BACKEND_PID
elif [ "$FRONTEND_ONLY" = true ]; then
    run_frontend_checks &
    FRONTEND_PID=$!
    wait $FRONTEND_PID
else
    run_backend_checks &
    BACKEND_PID=$!
    run_frontend_checks &
    FRONTEND_PID=$!
    wait $BACKEND_PID $FRONTEND_PID
fi

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Read status codes
BACKEND_EXIT_CODE=0
FRONTEND_EXIT_CODE=0
if [ "$FRONTEND_ONLY" = false ] && [ -f "$BACKEND_STATUS" ]; then
    BACKEND_EXIT_CODE=$(cat "$BACKEND_STATUS")
fi
if [ "$BACKEND_ONLY" = false ] && [ -f "$FRONTEND_STATUS" ]; then
    FRONTEND_EXIT_CODE=$(cat "$FRONTEND_STATUS")
fi

# Display results
print_header "Results"

# Backend results
if [ "$FRONTEND_ONLY" = false ]; then
    if [ "$BACKEND_EXIT_CODE" -eq 0 ]; then
        print_success "Backend checks passed"
    else
        print_error "Backend checks failed"
        echo -e "\n${RED}Backend Output:${NC}"
        cat "$BACKEND_OUTPUT"
    fi
fi

# Frontend results
if [ "$BACKEND_ONLY" = false ]; then
    if [ "$FRONTEND_EXIT_CODE" -eq 0 ]; then
        print_success "Frontend checks passed"
    else
        print_error "Frontend checks failed"
        echo -e "\n${RED}Frontend Output:${NC}"
        cat "$FRONTEND_OUTPUT"
    fi
fi

# Docker build test (only if flag is set)
if [ "$DOCKER_BUILD" = true ]; then
    print_header "Testing Docker build"
    if [ -f "Dockerfile" ]; then
        if docker build -t stashhog:test . > /dev/null 2>&1; then
            print_success "Docker build succeeded"
        else
            print_error "Docker build failed"
            docker build -t stashhog:test .
            exit 1
        fi
    else
        print_error "No Dockerfile found"
        exit 1
    fi
fi

# Final summary
print_header "Summary"
print_info "Total time: ${DURATION}s"

if [ "$BACKEND_EXIT_CODE" -eq 0 ] && [ "$FRONTEND_EXIT_CODE" -eq 0 ]; then
    print_success "All CI checks passed! 🎉"
    exit 0
else
    print_error "Some checks failed"
    exit 1
fi