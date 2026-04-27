#!/bin/bash

# MONITOR SCRIPT
# Monitors MT5 and Python bot processes

PROJECT_DIR="/home/ubuntu/nyx-ai"

check_process() {
    local pid_file=$1
    local process_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo "$process_name is running (PID: $pid)"
        else
            echo "$process_name is NOT running"
            rm -f "$pid_file"
        fi
    else
        echo "$process_name PID file not found"
    fi
}

echo "=== Nyx AI System Status ==="
echo "Time: $(date)"
echo

check_process "$PROJECT_DIR/mt5.pid" "MT5"
check_process "$PROJECT_DIR/bot.pid" "Python Bot"

echo
echo "Signal file: $(ls -la /home/ubuntu/nyx-ai/trade_signal.json 2>/dev/null || echo 'Not found')"
echo "Log directory: $PROJECT_DIR/logs"
