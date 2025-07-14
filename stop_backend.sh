#!/bin/bash

# Script to stop the backend server

BACKEND_DIR="/Users/sjafferali/github/personal/stashhog/backend"
PID_FILE="$BACKEND_DIR/server.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping backend server (PID: $PID)..."
        kill "$PID"
        sleep 2
        
        # Force kill if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Force killing server..."
            kill -9 "$PID"
        fi
        
        echo "Backend server stopped."
    else
        echo "Server process not found (PID: $PID)"
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found. Server may not be running."
    echo "Checking for uvicorn processes..."
    
    # Try to find and kill any uvicorn processes
    PIDS=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | awk '{print $2}')
    if [ -n "$PIDS" ]; then
        echo "Found uvicorn processes: $PIDS"
        echo "$PIDS" | xargs kill
        echo "Processes killed."
    else
        echo "No uvicorn processes found."
    fi
fi