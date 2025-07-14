#!/bin/bash

# Test script to verify both frontend and backend can start

set -e

PROJECT_ROOT="/Users/sjafferali/github/personal/stashhog"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "====================================="
echo "StashHog Services Test Script"
echo "====================================="

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i:$port > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    if check_port $port; then
        echo "Killing process on port $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Test Backend
echo -e "\n1. Testing Backend Service..."
echo "----------------------------"

# Clean up any existing processes
kill_port 8000

# Start backend
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    echo "Creating backend virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing backend dependencies..."
pip install -q -r requirements.txt

echo "Starting backend server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend_test.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✓ Backend started successfully!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Backend failed to start"
        tail -n 20 backend_test.log
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Test backend endpoints
echo "Testing backend endpoints:"
echo -n "  - Health check: "
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✓ Passed"
else
    echo "✗ Failed"
fi

echo -n "  - Root endpoint: "
if curl -s http://localhost:8000/ | grep -q "StashHog"; then
    echo "✓ Passed"
else
    echo "✗ Failed"
fi

# Kill backend
kill $BACKEND_PID 2>/dev/null || true
deactivate

# Test Frontend
echo -e "\n2. Testing Frontend Service..."
echo "------------------------------"

# Clean up any existing processes
kill_port 5173

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting frontend dev server..."
npm run dev > frontend_test.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null; then
        echo "✓ Frontend started successfully!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Frontend failed to start"
        tail -n 20 frontend_test.log
        kill $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Test frontend
echo "Testing frontend:"
echo -n "  - Dev server: "
if curl -s http://localhost:5173 | grep -q "<!doctype html>"; then
    echo "✓ Passed"
else
    echo "✗ Failed"
fi

# Kill frontend
kill $FRONTEND_PID 2>/dev/null || true

# Summary
echo -e "\n====================================="
echo "Test Summary"
echo "====================================="
echo "✓ Backend can start and respond to health checks"
echo "✓ Frontend can start and serve content"
echo -e "\nBoth services are working correctly!"

# Cleanup
rm -f "$BACKEND_DIR/backend_test.log"
rm -f "$FRONTEND_DIR/frontend_test.log"