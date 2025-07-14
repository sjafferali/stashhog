#!/bin/bash
set -e

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

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ] || [ ! -f "frontend/package.json" ]; then
    print_error "Please run this script from the root of the stashhog repository"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_header "Creating Python virtual environment"
    python3 -m venv venv
fi

# Activate virtual environment
print_header "Activating virtual environment"
source venv/bin/activate

# Install/upgrade pip
print_header "Upgrading pip"
python -m pip install --upgrade pip

# Install backend dependencies
print_header "Installing backend dependencies"
cd backend
pip install -r requirements.txt
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
fi
cd ..

# Install testing and linting tools
print_header "Installing Python testing and linting tools"
pip install pytest black isort flake8 mypy safety

# Install frontend dependencies
print_header "Installing frontend dependencies"
cd frontend
npm ci
cd ..

# Run backend tests
print_header "Running backend tests"
cd backend
if python -m pytest -v; then
    print_success "Backend tests passed"
else
    print_error "Backend tests failed"
    deactivate
    exit 1
fi
cd ..

# Run frontend tests
print_header "Running frontend tests"
cd frontend
if npm test -- --watchAll=false; then
    print_success "Frontend tests passed"
else
    print_error "Frontend tests failed"
    deactivate
    exit 1
fi
cd ..

# Backend linting - Black
print_header "Checking Python code formatting (Black)"
cd backend
if black --check .; then
    print_success "Python formatting check passed"
else
    print_error "Python formatting check failed"
    echo "Run 'black backend/' to fix formatting issues"
    deactivate
    exit 1
fi
cd ..

# Backend linting - isort
print_header "Checking Python import sorting (isort)"
cd backend
if isort --check-only .; then
    print_success "Python import sorting check passed"
else
    print_error "Python import sorting check failed"
    echo "Run 'isort backend/' to fix import sorting"
    deactivate
    exit 1
fi
cd ..

# Backend linting - Flake8
print_header "Running Python linter (Flake8)"
cd backend
if flake8 . --max-line-length=88; then
    print_success "Python linting passed"
else
    print_error "Python linting failed"
    deactivate
    exit 1
fi
cd ..

# Backend type checking - MyPy
print_header "Running Python type checker (MyPy)"
cd backend
if mypy app/ --ignore-missing-imports; then
    print_success "Python type checking passed"
else
    print_error "Python type checking failed"
    deactivate
    exit 1
fi
cd ..

# Frontend linting - ESLint
print_header "Running ESLint"
cd frontend
if npm run lint; then
    print_success "ESLint passed"
else
    print_error "ESLint failed (non-blocking)"
    # Don't exit - this is non-critical like in meditrack
fi
cd ..

# Frontend formatting - Prettier
print_header "Checking code formatting (Prettier)"
cd frontend
if npm run format:check; then
    print_success "Prettier formatting check passed"
else
    print_error "Prettier formatting check failed (non-blocking)"
    echo "Run 'npm run format' in frontend/ to fix formatting issues"
    # Don't exit - this is non-critical
fi
cd ..

# Frontend type checking - TypeScript
print_header "Running TypeScript type checker"
cd frontend
if npm run type-check; then
    print_success "TypeScript type checking passed"
else
    print_error "TypeScript type checking failed (non-blocking)"
    # Don't exit - this is non-critical like in meditrack
fi
cd ..

# Security check - Python dependencies
print_header "Checking Python dependencies for vulnerabilities"
cd backend
if safety check -r requirements.txt --json; then
    print_success "No vulnerabilities found in Python dependencies"
else
    print_error "Vulnerabilities found in Python dependencies (non-blocking)"
    # Don't exit - this is non-critical like in meditrack
fi
cd ..

# Security check - npm dependencies
print_header "Checking npm dependencies for vulnerabilities"
cd frontend
if npm audit --json; then
    print_success "No vulnerabilities found in npm dependencies"
else
    print_error "Vulnerabilities found in npm dependencies (non-blocking)"
    # Don't exit - this is non-critical like in meditrack
fi
cd ..

# Docker build test
print_header "Testing Docker build"
if [ -f "Dockerfile.production" ]; then
    if docker build -f Dockerfile.production -t stashhog:test .; then
        print_success "Docker build succeeded"
    else
        print_error "Docker build failed"
        deactivate
        exit 1
    fi
elif [ -f "Dockerfile" ]; then
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