#!/bin/bash
set -e

# CI checks script for StashHog with Claude integration
# This script runs all checks in order and uses Claude to fix failures

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
print_running() {
    echo -e "\n${BLUE}Running: $1${NC}"
}

print_passed() {
    echo -e "${GREEN}✓ Passed: $1${NC}"
}

print_fixed() {
    echo -e "${YELLOW}✓ Resolved automatically: $1${NC}"
}

print_error() {
    echo -e "${RED}✗ Failed: $1${NC}"
}

# Function to send failure to Claude and wait for fix
send_to_claude() {
    local failure_output="$1"
    local check_name="$2"
    echo -e "${YELLOW}Sending failure to Claude for investigation...${NC}"
    claude --model opus --permission-mode acceptEdits -p "Investigate and fix the below failures from $check_name. Do not attempt to run any tests or checks to verify if your changes were successful.

$failure_output"
}

# Main check runner function
run_all_checks() {
    local all_passed=true

    # Check if we're in the right directory
    if [ ! -f "backend/requirements.txt" ] || [ ! -f "frontend/package.json" ]; then
        print_error "Please run this script from the root of the stashhog repository"
        exit 1
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_running "Creating Python virtual environment"
        python3 -m venv venv
        print_passed "Virtual environment created"
    fi

    # Activate virtual environment
    print_running "Activating virtual environment"
    source venv/bin/activate
    print_passed "Virtual environment activated"

    # Upgrade pip
    print_running "Upgrading pip"
    if output=$(python -m pip install --upgrade pip 2>&1); then
        print_passed "pip upgraded"
    else
        send_to_claude "$output" "pip upgrade"
        all_passed=false
        deactivate
        return 1
    fi

    # Install backend dependencies (skip if frontend-only)
    if [ "$FRONTEND_ONLY" = false ]; then
        print_running "Installing backend dependencies"
        cd backend
        if output=$(pip install -r requirements.txt 2>&1); then
            print_passed "Backend dependencies installed"
        else
            cd ..
            send_to_claude "$output" "backend dependencies installation"
            all_passed=false
            deactivate
            return 1
        fi

        if [ -f "requirements-dev.txt" ]; then
            if output=$(pip install -r requirements-dev.txt 2>&1); then
                print_passed "Backend dev dependencies installed"
            else
                cd ..
                send_to_claude "$output" "backend dev dependencies installation"
                all_passed=false
                deactivate
                return 1
            fi
        fi
        cd ..

        # Install testing and linting tools
        print_running "Installing Python testing and linting tools"
        if output=$(pip install pytest black isort flake8 mypy pip-audit 2>&1); then
            print_passed "Python tools installed"
        else
            send_to_claude "$output" "Python tools installation"
            all_passed=false
            deactivate
            return 1
        fi
    fi

    # Install frontend dependencies (skip if backend-only)
    if [ "$BACKEND_ONLY" = false ]; then
        print_running "Installing frontend dependencies"
        cd frontend
        if output=$(npm ci 2>&1); then
            print_passed "Frontend dependencies installed"
        else
            cd ..
            send_to_claude "$output" "frontend dependencies installation"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Run backend tests (skip if frontend-only)
    if [ "$FRONTEND_ONLY" = false ]; then
        print_running "Backend tests"
        cd backend
        if output=$(python -m pytest -v 2>&1); then
            print_passed "Backend tests"
        else
            # Extract the short test summary section more precisely
            short_summary=""
            
            # Method 1: Extract from "short test summary info" to the end summary line
            if echo "$output" | grep -q "short test summary info"; then
                short_summary=$(echo "$output" | awk '/short test summary info/{flag=1} flag; /^=+ .* in .* =+$/{if(flag) exit}')
            fi
            
            # Method 2: If method 1 didn't work, try to extract FAILED lines
            if [ -z "$short_summary" ] || [ "$(echo "$short_summary" | wc -l)" -lt 2 ]; then
                failed_lines=$(echo "$output" | grep "^FAILED " || true)
                if [ -n "$failed_lines" ]; then
                    short_summary="=========================== short test summary info ============================
$failed_lines"
                fi
            fi
            
            # Method 3: If still no summary, extract last 20 lines which usually contain the summary
            if [ -z "$short_summary" ]; then
                short_summary=$(echo "$output" | tail -n 20)
                # Prepend a note that this is a fallback
                short_summary="[Note: Full short summary not found, showing last 20 lines of output]
$short_summary"
            fi

            cd ..
            send_to_claude "$short_summary" "backend tests"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Run frontend tests (skip if backend-only)
    if [ "$BACKEND_ONLY" = false ]; then
        print_running "Frontend tests"
        cd frontend
        if output=$(npm run test:coverage -- --ci --maxWorkers=2 2>&1); then
            print_passed "Frontend tests"
        else
            cd ..
            send_to_claude "$output" "frontend tests"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Backend linting - Black (skip if frontend-only)
    if [ "$FRONTEND_ONLY" = false ]; then
        print_running "Python code formatting (Black)"
        cd backend
        if black --check . &>/dev/null; then
            print_passed "Python formatting"
        else
            if black . &>/dev/null; then
                print_fixed "Python formatting"
            else
                output=$(black . 2>&1)
                cd ..
                send_to_claude "$output" "Black formatting"
                all_passed=false
                deactivate
                return 1
            fi
        fi
        cd ..
    fi

    # Backend linting - isort (skip if frontend-only)
    if [ "$FRONTEND_ONLY" = false ]; then
        print_running "Python import sorting (isort)"
        cd backend
        if isort --check-only . &>/dev/null; then
            print_passed "Python import sorting"
        else
            if isort . &>/dev/null; then
                print_fixed "Python import sorting"
            else
                output=$(isort . 2>&1)
                cd ..
                send_to_claude "$output" "isort"
                all_passed=false
                deactivate
                return 1
            fi
        fi
        cd ..
    fi

    # Backend linting - Flake8 (skip if frontend-only)
    if [ "$FRONTEND_ONLY" = false ]; then
        print_running "Python linter (Flake8)"
        cd backend
        if output=$(flake8 . 2>&1); then
            print_passed "Python linting"
        else
            cd ..
            send_to_claude "$output" "Flake8 linting"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Backend type checking - MyPy (skip if frontend-only)
    if [ "$FRONTEND_ONLY" = false ]; then
        print_running "Python type checker (MyPy)"
        cd backend
        if output=$(mypy app/ --ignore-missing-imports 2>&1); then
            print_passed "Python type checking"
        else
            cd ..
            send_to_claude "$output" "MyPy type checking"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Frontend linting - ESLint (skip if backend-only)
    if [ "$BACKEND_ONLY" = false ]; then
        print_running "ESLint"
        cd frontend
        if output=$(npm run lint 2>&1); then
            print_passed "ESLint"
        else
            cd ..
            send_to_claude "$output" "ESLint"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Frontend formatting - Prettier (skip if backend-only)
    if [ "$BACKEND_ONLY" = false ]; then
        print_running "Code formatting (Prettier)"
        cd frontend
        if npm run format:check &>/dev/null; then
            print_passed "Prettier formatting"
        else
            if npm run format &>/dev/null; then
                print_fixed "Prettier formatting"
            else
                output=$(npm run format 2>&1)
                cd ..
                send_to_claude "$output" "Prettier formatting"
                all_passed=false
                deactivate
                return 1
            fi
        fi
        cd ..
    fi

    # Frontend type checking - TypeScript (skip if backend-only)
    if [ "$BACKEND_ONLY" = false ]; then
        print_running "TypeScript type checker"
        cd frontend
        if output=$(npm run type-check 2>&1); then
            print_passed "TypeScript type checking"
        else
            cd ..
            send_to_claude "$output" "TypeScript type checking"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Security check - Python dependencies (skip if frontend-only)
    if [ "$FRONTEND_ONLY" = false ]; then
        print_running "Python dependencies vulnerability check"
        cd backend
        if output=$(pip-audit -r requirements.txt 2>&1); then
            print_passed "Python security check"
        else
            cd ..
            send_to_claude "$output" "Python security audit"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Security check - npm dependencies (skip if backend-only)
    if [ "$BACKEND_ONLY" = false ]; then
        print_running "npm dependencies vulnerability check"
        cd frontend
        if output=$(npm audit 2>&1); then
            print_passed "npm security check"
        else
            cd ..
            send_to_claude "$output" "npm security audit"
            all_passed=false
            deactivate
            return 1
        fi
        cd ..
    fi

    # Docker build test (only if flag is set)
    if [ "$DOCKER_BUILD" = true ]; then
        print_running "Docker build test"
        if [ -f "Dockerfile" ]; then
            if output=$(docker build -t stashhog:test . 2>&1); then
                print_passed "Docker build"
            else
                send_to_claude "$output" "Docker build"
                all_passed=false
                deactivate
                return 1
            fi
        else
            print_error "No Dockerfile found"
            all_passed=false
            deactivate
            return 1
        fi
    fi

    # Deactivate virtual environment
    deactivate

    if [ "$all_passed" = true ]; then
        echo -e "\n${GREEN}All CI checks completed successfully! 🎉${NC}"
        return 0
    else
        return 1
    fi
}

# Main loop - keep running until all checks pass or max attempts reached
MAX_ATTEMPTS=10
attempt=1

while [ $attempt -le $MAX_ATTEMPTS ]; do
    echo -e "\n${YELLOW}=== CI Check Attempt #$attempt of $MAX_ATTEMPTS ===${NC}"

    if run_all_checks; then
        break
    else
        if [ $attempt -eq $MAX_ATTEMPTS ]; then
            echo -e "\n${RED}Maximum attempts ($MAX_ATTEMPTS) reached. CI checks failed.${NC}"
            exit 1
        fi
        echo -e "\n${YELLOW}Restarting checks after Claude fixes...${NC}"
        ((attempt++))
        sleep 2
    fi
done
