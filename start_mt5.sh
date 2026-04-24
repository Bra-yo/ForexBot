#!/bin/bash

# NYX AI - MT5 START SCRIPT FOR LINUX
# Starts MT5 under Wine and launches the Python bot

set -e

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if Wine is working
check_wine() {
    if ! wine --version > /dev/null 2>&1; then
        log "ERROR: Wine is not installed or not working"
        exit 1
    fi
    log "Wine version: $(wine --version)"
}

# Function to check if MT5 is installed
check_mt5() {
    local mt5_path="$HOME/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
    if [ ! -f "$mt5_path" ]; then
        log "ERROR: MT5 not found at $mt5_path"
        log "Please install MT5 first using: wine mt5setup.exe"
        exit 1
    fi
    log "MT5 found at: $mt5_path"
}

# Function to start Xvfb (virtual display)
start_xvfb() {
    if [ -z "$DISPLAY" ]; then
        export DISPLAY=:99
        log "Starting virtual display on $DISPLAY"
        Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
        sleep 2
    fi
}

# Function to start MT5
start_mt5() {
    local mt5_path="$HOME/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
    log "Starting MT5 under Wine..."
    
    # Start MT5 in background
    wine "$mt5_path" > /dev/null 2>&1 &
    local mt5_pid=$!
    
    log "MT5 started with PID: $mt5_pid"
    
    # Wait a bit for MT5 to initialize
    sleep 10
    
    # Check if MT5 is still running
    if ! kill -0 $mt5_pid 2>/dev/null; then
        log "WARNING: MT5 process died during startup"
    else
        log "MT5 is running successfully"
    fi
    
    echo $mt5_pid > /tmp/mt5.pid
}

# Function to start Python bot
start_bot() {
    log "Starting Nyx AI Python bot..."
    
    # Set environment variables
    export PYTHONIOENCODING=utf-8
    export SIGNAL_BRIDGE_MODE=true
    export WINE_MODE=true
    
    # Start the bot
    python3 main.py > /dev/null 2>&1 &
    local bot_pid=$!
    
    log "Python bot started with PID: $bot_pid"
    echo $bot_pid > /tmp/bot.pid
}

# Function to cleanup on exit
cleanup() {
    log "Cleaning up processes..."
    
    # Kill MT5 if running
    if [ -f /tmp/mt5.pid ]; then
        local mt5_pid=$(cat /tmp/mt5.pid)
        if kill -0 $mt5_pid 2>/dev/null; then
            log "Stopping MT5 (PID: $mt5_pid)"
            kill $mt5_pid
        fi
        rm -f /tmp/mt5.pid
    fi
    
    # Kill Python bot if running
    if [ -f /tmp/bot.pid ]; then
        local bot_pid=$(cat /tmp/bot.pid)
        if kill -0 $bot_pid 2>/dev/null; then
            log "Stopping Python bot (PID: $bot_pid)"
            kill $bot_pid
        fi
        rm -f /tmp/bot.pid
    fi
    
    log "Cleanup completed"
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    log "=== NYX AI LINUX STARTUP ==="
    log "Starting Nyx AI with Wine + MT5 + Signal Bridge"
    
    # Check prerequisites
    check_wine
    check_mt5
    
    # Start virtual display
    start_xvfb
    
    # Start MT5
    start_mt5
    
    # Start Python bot
    start_bot
    
    log "=== ALL SYSTEMS STARTED ==="
    log "MT5 and Python bot are running"
    log "Signal bridge is active"
    log "Press Ctrl+C to stop all services"
    
    # Monitor processes
    while true; do
        # Check if MT5 is running
        if [ -f /tmp/mt5.pid ]; then
            local mt5_pid=$(cat /tmp/mt5.pid)
            if ! kill -0 $mt5_pid 2>/dev/null; then
                log "WARNING: MT5 process died, restarting..."
                start_mt5
            fi
        fi
        
        # Check if Python bot is running
        if [ -f /tmp/bot.pid ]; then
            local bot_pid=$(cat /tmp/bot.pid)
            if ! kill -0 $bot_pid 2>/dev/null; then
                log "WARNING: Python bot died, restarting..."
                start_bot
            fi
        fi
        
        sleep 30  # Check every 30 seconds
    done
}

# Run main function
main "$@"
