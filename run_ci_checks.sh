#!/bin/bash
set -e

# Parse command line arguments
BACKEND_ONLY=false
FRONTEND_ONLY=false

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
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --backend-only   Run only backend checks"
            echo "  --frontend-only  Run only frontend checks"
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

print_command() {
    echo -e "${YELLOW}Running:${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ] || [ ! -f "frontend/package.json" ]; then
    print_error "Please run this script from the root of the stashhog repository"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_header "Creating Python virtual environment"
    print_command "python3 -m venv venv"
    python3 -m venv venv
fi

# Activate virtual environment
print_header "Activating virtual environment"
source venv/bin/activate

# Install/upgrade pip
print_header "Upgrading pip"
print_command "python -m pip install --upgrade pip"
python -m pip install --upgrade pip

# Install backend dependencies (skip if frontend-only)
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "Installing backend dependencies"
    cd backend
    print_command "pip install -r requirements.txt"
    pip install -r requirements.txt
    if [ -f "requirements-dev.txt" ]; then
        print_command "pip install -r requirements-dev.txt"
        pip install -r requirements-dev.txt
    fi
    cd ..

    # Install testing and linting tools
    print_header "Installing Python testing and linting tools"
    print_command "pip install pytest black isort flake8 mypy pip-audit"
    pip install pytest black isort flake8 mypy pip-audit
fi

# Install frontend dependencies (skip if backend-only)
if [ "$BACKEND_ONLY" = false ]; then
    print_header "Installing frontend dependencies"
    cd frontend
    print_command "npm ci"
    npm ci
    cd ..
fi

# Run backend tests (skip if frontend-only)
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "Running backend tests"
    cd backend
    print_command "python -m pytest -v"
    if python -m pytest -v; then
        print_success "Backend tests passed"
    else
        print_error "Backend tests failed"
        deactivate
        exit 1
    fi
    cd ..
fi

# Run frontend tests (skip if backend-only)
if [ "$BACKEND_ONLY" = false ]; then
    print_header "Running frontend tests"
    cd frontend
    print_command "npm run test:coverage -- --ci --maxWorkers=2"
    if npm run test:coverage -- --ci --maxWorkers=2; then
        print_success "Frontend tests passed"
    else
        print_error "Frontend tests failed"
        echo "Note: Tests may fail due to coverage thresholds not being met"
        deactivate
        exit 1
    fi
    cd ..
fi

# Backend linting - Black (skip if frontend-only)
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "Checking Python code formatting (Black)"
    cd backend
    print_command "black --check ."
    if black --check .; then
        print_success "Python formatting check passed"
    else
        print_error "Python formatting check failed"
        echo "Run 'cd backend && black .' to fix formatting issues"
        deactivate
        exit 1
    fi
    cd ..
fi

# Backend linting - isort (skip if frontend-only)
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "Checking Python import sorting (isort)"
    cd backend
    print_command "isort --check-only ."
    if isort --check-only .; then
        print_success "Python import sorting check passed"
    else
        print_error "Python import sorting check failed"
        echo "Run 'cd backend && isort .' to fix import sorting"
        deactivate
        exit 1
    fi
    cd ..
fi

# Backend linting - Flake8 (skip if frontend-only)
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "Running Python linter (Flake8)"
    cd backend
    print_command "flake8 ."
    if flake8 .; then
        print_success "Python linting passed"
    else
        print_error "Python linting failed"
        deactivate
        exit 1
    fi
    cd ..
fi

# Backend type checking - MyPy (skip if frontend-only)
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "Running Python type checker (MyPy)"
    cd backend
    print_command "mypy app/ --ignore-missing-imports"
    if mypy app/ --ignore-missing-imports; then
        print_success "Python type checking passed"
    else
        print_error "Python type checking failed"
        deactivate
        exit 1
    fi
    cd ..
fi

# Frontend linting - ESLint (skip if backend-only)
if [ "$BACKEND_ONLY" = false ]; then
    print_header "Running ESLint"
    cd frontend
    print_command "npm run lint"
    if npm run lint; then
        print_success "ESLint passed"
    else
        print_error "ESLint failed (non-blocking)"
        # Don't exit - this is non-critical like in meditrack
    fi
    cd ..
fi

# Frontend formatting - Prettier (skip if backend-only)
if [ "$BACKEND_ONLY" = false ]; then
    print_header "Checking code formatting (Prettier)"
    cd frontend
    print_command "npm run format:check"
    if npm run format:check; then
        print_success "Prettier formatting check passed"
    else
        print_error "Prettier formatting check failed (non-blocking)"
        echo "Run 'npm run format' in frontend/ to fix formatting issues"
        # Don't exit - this is non-critical
    fi
    cd ..
fi

# Frontend type checking - TypeScript (skip if backend-only)
if [ "$BACKEND_ONLY" = false ]; then
    print_header "Running TypeScript type checker"
    cd frontend
    print_command "npm run type-check"
    if npm run type-check; then
        print_success "TypeScript type checking passed"
    else
        print_error "TypeScript type checking failed (non-blocking)"
        # Don't exit - this is non-critical like in meditrack
    fi
    cd ..
fi

# Security check - Python dependencies (skip if frontend-only)
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "Checking Python dependencies for vulnerabilities"
    cd backend
    print_command "pip-audit -r requirements.txt"
    if pip-audit -r requirements.txt; then
        print_success "No vulnerabilities found in Python dependencies"
    else
        print_error "Vulnerabilities found in Python dependencies (non-blocking)"
        # Don't exit - this is non-critical like in meditrack
    fi
    cd ..
fi

# Security check - npm dependencies (skip if backend-only)
if [ "$BACKEND_ONLY" = false ]; then
    print_header "Checking npm dependencies for vulnerabilities"
    cd frontend
    print_command "npm audit --json"
    if npm audit --json; then
        print_success "No vulnerabilities found in npm dependencies"
    else
        print_error "Vulnerabilities found in npm dependencies (non-blocking)"
        # Don't exit - this is non-critical like in meditrack
    fi
    cd ..
fi

# Docker build test
print_header "Testing Docker build"
if [ -f "Dockerfile" ]; then
    print_command "docker build -t stashhog:test ."
    if docker build -t stashhog:test .; then
        print_success "Docker build succeeded"
    else
        print_error "Docker build failed"
        deactivate
        exit 1
    fi
else
    print_error "No Dockerfile found"
    deactivate
    exit 1
fi

# Deactivate virtual environment
deactivate

print_header "CI checks completed! 🎉"
print_success "All critical checks passed successfully!"