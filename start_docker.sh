#!/bin/bash

# NYX AI - DOCKER STARTUP SCRIPT

set -e

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Main startup
main() {
    log "=== NYX AI DOCKER STARTUP ==="
    log "Starting Nyx AI in Docker container"
    
    # Create necessary directories
    mkdir -p /var/log/supervisor
    mkdir -p /app/logs
    mkdir -p /app/data
    mkdir -p /app/signals
    
    # Set permissions
    chmod 755 /app/logs /app/data /app/signals
    
    # Initialize Wine if needed
    if [ ! -d "/root/.wine" ]; then
        log "Initializing Wine..."
        winecfg --auto
    fi
    
    # Start supervisord
    log "Starting supervisord..."
    exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
}

# Run main function
main "$@"
