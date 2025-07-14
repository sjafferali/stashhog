#!/bin/bash

# Script to start the backend server in the background

BACKEND_DIR="/Users/sjafferali/github/personal/stashhog/backend"
LOG_FILE="$BACKEND_DIR/server.log"
PID_FILE="$BACKEND_DIR/server.pid"

# Change to backend directory
cd "$BACKEND_DIR" || exit 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Kill any existing server process
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Stopping existing server (PID: $OLD_PID)..."
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# Start the server in the background
echo "Starting backend server..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

echo "Backend server started with PID: $SERVER_PID"
echo "Log file: $LOG_FILE"

# Wait for server to start
echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "Server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Server failed to start within 30 seconds"
        echo "Check the log file for errors: $LOG_FILE"
        tail -n 20 "$LOG_FILE"
        exit 1
    fi
    sleep 1
done

# Test the health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool