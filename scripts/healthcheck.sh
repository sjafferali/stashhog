#!/bin/bash
set -euo pipefail

# Health check script for StashHog container
# Returns 0 if healthy, 1 if unhealthy

# Configuration
TIMEOUT=5
BACKEND_URL="http://127.0.0.1:8000/health"
NGINX_URL="http://127.0.0.1/nginx-health"
FRONTEND_URL="http://127.0.0.1/"

# Colors for output (when running interactively)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Track failures
FAILURES=0

# Function to check a service
check_service() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    
    # Use curl with timeout
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")
    
    if [[ "$response" == "$expected_status" ]]; then
        echo -e "${GREEN}OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}FAIL${NC} (HTTP $response)"
        ((FAILURES++))
        return 1
    fi
}

# Function to check process
check_process() {
    local name=$1
    local pattern=$2
    
    echo -n "Checking process $name... "
    
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILURES++))
        return 1
    fi
}

# Function to check database
check_database() {
    echo -n "Checking database... "
    
    # Try to access the database file
    if [[ -f "/data/stashhog.db" ]]; then
        # Check if it's readable and has size > 0
        if [[ -r "/data/stashhog.db" && -s "/data/stashhog.db" ]]; then
            # Try to run a simple query via the API
            response=$(curl -s --connect-timeout $TIMEOUT --max-time $TIMEOUT "$BACKEND_URL" 2>/dev/null || echo "{}")
            if echo "$response" | grep -q "healthy"; then
                echo -e "${GREEN}OK${NC}"
                return 0
            else
                echo -e "${YELLOW}WARN${NC} (API check failed)"
                ((FAILURES++))
                return 1
            fi
        else
            echo -e "${RED}FAIL${NC} (Database file not accessible)"
            ((FAILURES++))
            return 1
        fi
    else
        echo -e "${YELLOW}WARN${NC} (Database not initialized)"
        # This might be OK on first startup
        return 0
    fi
}

# Function to check disk space
check_disk_space() {
    echo -n "Checking disk space... "
    
    # Check data directory
    usage=$(df -h /data 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ -n "$usage" ]]; then
        if [[ "$usage" -lt 90 ]]; then
            echo -e "${GREEN}OK${NC} ($usage% used)"
            return 0
        elif [[ "$usage" -lt 95 ]]; then
            echo -e "${YELLOW}WARN${NC} ($usage% used)"
            return 0
        else
            echo -e "${RED}FAIL${NC} ($usage% used)"
            ((FAILURES++))
            return 1
        fi
    else
        echo -e "${YELLOW}WARN${NC} (Unable to check)"
        return 0
    fi
}

# Function to check memory
check_memory() {
    echo -n "Checking memory... "
    
    # Get memory usage percentage
    if command -v free > /dev/null 2>&1; then
        mem_used=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
        
        if [[ "$mem_used" -lt 90 ]]; then
            echo -e "${GREEN}OK${NC} ($mem_used% used)"
            return 0
        elif [[ "$mem_used" -lt 95 ]]; then
            echo -e "${YELLOW}WARN${NC} ($mem_used% used)"
            return 0
        else
            echo -e "${RED}FAIL${NC} ($mem_used% used)"
            ((FAILURES++))
            return 1
        fi
    else
        echo -e "${YELLOW}WARN${NC} (Unable to check)"
        return 0
    fi
}

# Main health checks
echo "=== StashHog Health Check ==="
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Check services
check_service "Backend API" "$BACKEND_URL" 200
check_service "Nginx" "$NGINX_URL" 200
check_service "Frontend" "$FRONTEND_URL" 200

# Check processes
check_process "Supervisord" "supervisord"
check_process "Nginx" "nginx.*master"
check_process "Backend" "uvicorn.*backend"

# Check system resources
check_database
check_disk_space
check_memory

# Check for critical errors in logs
echo -n "Checking for critical errors... "
if [[ -f "/logs/backend_stderr.log" ]]; then
    recent_errors=$(tail -n 100 /logs/backend_stderr.log 2>/dev/null | grep -i "critical\|error" | wc -l)
    if [[ "$recent_errors" -eq 0 ]]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}WARN${NC} ($recent_errors errors in last 100 lines)"
    fi
else
    echo -e "${GREEN}OK${NC} (No error log)"
fi

# Summary
echo ""
echo "=== Summary ==="
if [[ "$FAILURES" -eq 0 ]]; then
    echo -e "${GREEN}All checks passed - Container is healthy${NC}"
    exit 0
else
    echo -e "${RED}$FAILURES check(s) failed - Container is unhealthy${NC}"
    exit 1
fi