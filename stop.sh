#!/bin/bash

# STOP SCRIPT
# Stops MT5 and Python bot processes

PROJECT_DIR="/home/ubuntu/nyx-ai"

echo "Stopping Nyx AI System..."

# Stop Python bot
if [ -f "$PROJECT_DIR/bot.pid" ]; then
    pid=$(cat "$PROJECT_DIR/bot.pid")
    if kill -0 $pid 2>/dev/null; then
        echo "Stopping Python bot (PID: $pid)..."
        kill $pid
        rm -f "$PROJECT_DIR/bot.pid"
    fi
fi

# Stop MT5
if [ -f "$PROJECT_DIR/mt5.pid" ]; then
    pid=$(cat "$PROJECT_DIR/mt5.pid")
    if kill -0 $pid 2>/dev/null; then
        echo "Stopping MT5 (PID: $pid)..."
        kill $pid
        rm -f "$PROJECT_DIR/mt5.pid"
    fi
fi

echo "Nyx AI System stopped"
