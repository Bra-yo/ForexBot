#!/bin/bash

# NYX AI DEPLOYMENT SCRIPT
# Linux-compatible deployment for Wine + MT5 + Signal Bridge

set -e

# Configuration
PROJECT_DIR="/home/ubuntu/nyx-ai"
MT5_WINE_PATH="$HOME/.wine/drive_c/Program Files/MetaTrader 5"
SIGNAL_FILE="/home/ubuntu/nyx-ai/trade_signal.json"
LOG_DIR="/home/ubuntu/nyx-ai/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root is not recommended"
        log_warning "Please run as regular user with sudo privileges"
        exit 1
    fi
}

# Function to create project directory
create_project_structure() {
    log "Creating project directory structure..."
    
    mkdir -p "$PROJECT_DIR"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$PROJECT_DIR/signals"
    mkdir -p "$PROJECT_DIR/mt5"
    
    # Set permissions
    chmod 755 "$PROJECT_DIR"
    chmod 755 "$PROJECT_DIR/logs"
    chmod 755 "$PROJECT_DIR/data"
    chmod 755 "$PROJECT_DIR/signals"
    chmod 755 "$PROJECT_DIR/mt5"
    
    log_success "Project structure created"
}

# Function to check Wine installation
check_wine() {
    log "Checking Wine installation..."
    
    if ! command -v wine &> /dev/null; then
        log_error "Wine is not installed"
        log "Installing Wine..."
        
        # Update package list
        sudo apt update
        
        # Install Wine
        sudo apt install -y wine64 wine32 winetricks
        
        log_success "Wine installed"
    else
        log_success "Wine is already installed: $(wine --version)"
    fi
    
    # Initialize Wine if needed
    if [ ! -d "$HOME/.wine" ]; then
        log "Initializing Wine..."
        winecfg --auto
        log_success "Wine initialized"
    fi
}

# Function to check MT5 installation
check_mt5() {
    log "Checking MT5 installation..."
    
    if [ ! -f "$MT5_WINE_PATH/terminal64.exe" ]; then
        log_error "MT5 not found at: $MT5_WINE_PATH/terminal64.exe"
        log "Please install MT5 first:"
        log "1. Download MT5: https://www.metatrader5.com/en/download"
        log "2. Install with: wine mt5setup.exe /auto"
        log "3. Re-run this script"
        exit 1
    else
        log_success "MT5 found at: $MT5_WINE_PATH"
    fi
}

# Function to check Python dependencies
check_python_deps() {
    log "Checking Python dependencies..."
    
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        cd "$PROJECT_DIR"
        python3 -m pip install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_warning "requirements.txt not found"
    fi
}

# Function to copy files to project directory
copy_files() {
    log "Copying files to project directory..."
    
    # Copy Python files
    cp *.py "$PROJECT_DIR/" 2>/dev/null || true
    cp requirements.txt "$PROJECT_DIR/" 2>/dev/null || true
    cp *.md "$PROJECT_DIR/" 2>/dev/null || true
    
    # Copy MT5 files
    cp -r mt5/* "$PROJECT_DIR/mt5/" 2>/dev/null || true
    
    # Copy configuration files
    cp .env "$PROJECT_DIR/" 2>/dev/null || true
    cp config.py "$PROJECT_DIR/" 2>/dev/null || true
    
    log_success "Files copied to project directory"
}

# Function to setup signal file permissions
setup_signal_file() {
    log "Setting up signal file permissions..."
    
    # Create signal file if it doesn't exist
    if [ ! -f "$SIGNAL_FILE" ]; then
        touch "$SIGNAL_FILE"
    fi
    
    # Set permissions
    chmod 666 "$SIGNAL_FILE"
    
    log_success "Signal file permissions set"
}

# Function to start MT5
start_mt5() {
    log "Starting MT5 under Wine..."
    
    # Start MT5 in background
    wine "$MT5_WINE_PATH/terminal64.exe" &
    MT5_PID=$!
    
    # Save PID
    echo $MT5_PID > "$PROJECT_DIR/mt5.pid"
    
    log_success "MT5 started with PID: $MT5_PID"
    
    # Wait for MT5 to initialize
    log "Waiting for MT5 to initialize..."
    sleep 10
    
    # Check if MT5 is still running
    if kill -0 $MT5_PID 2>/dev/null; then
        log_success "MT5 is running"
    else
        log_error "MT5 failed to start"
        exit 1
    fi
}

# Function to start Python bot
start_bot() {
    log "Starting Nyx AI Python bot..."
    
    cd "$PROJECT_DIR"
    
    # Set environment variables
    export PYTHONIOENCODING=utf-8
    export SIGNAL_BRIDGE_MODE=true
    export WINE_MODE=true
    
    # Start bot in background
    python3 main.py > "$PROJECT_DIR/logs/bot.log" 2>&1 &
    BOT_PID=$!
    
    # Save PID
    echo $BOT_PID > "$PROJECT_DIR/bot.pid"
    
    log_success "Python bot started with PID: $BOT_PID"
}

# Function to create monitoring script
create_monitor_script() {
    log "Creating monitoring script..."
    
    cat > "$PROJECT_DIR/monitor.sh" << 'EOF'
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
EOF

    chmod +x "$PROJECT_DIR/monitor.sh"
    log_success "Monitor script created"
}

# Function to create stop script
create_stop_script() {
    log "Creating stop script..."
    
    cat > "$PROJECT_DIR/stop.sh" << 'EOF'
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
EOF

    chmod +x "$PROJECT_DIR/stop.sh"
    log_success "Stop script created"
}

# Function to show status
show_status() {
    log "System Status:"
    echo
    
    # Check processes
    if [ -f "$PROJECT_DIR/mt5.pid" ]; then
        MT5_PID=$(cat "$PROJECT_DIR/mt5.pid")
        if kill -0 $MT5_PID 2>/dev/null; then
            log_success "MT5: Running (PID: $MT5_PID)"
        else
            log_error "MT5: Not running"
        fi
    else
        log_error "MT5: Not started"
    fi
    
    if [ -f "$PROJECT_DIR/bot.pid" ]; then
        BOT_PID=$(cat "$PROJECT_DIR/bot.pid")
        if kill -0 $BOT_PID 2>/dev/null; then
            log_success "Python Bot: Running (PID: $BOT_PID)"
        else
            log_error "Python Bot: Not running"
        fi
    else
        log_error "Python Bot: Not started"
    fi
    
    echo
    log "Signal file: $SIGNAL_FILE"
    if [ -f "$SIGNAL_FILE" ]; then
        log "Signal file exists and size: $(wc -c < $SIGNAL_FILE) bytes"
    else
        log_warning "Signal file does not exist"
    fi
    
    echo
    log "Log directory: $PROJECT_DIR/logs"
    if [ -d "$PROJECT_DIR/logs" ]; then
        log "Log files:"
        ls -la "$PROJECT_DIR/logs/" 2>/dev/null || echo "No log files yet"
    fi
}

# Main deployment function
main() {
    log "=== NYX AI DEPLOYMENT STARTING ==="
    log "Deploying Nyx AI with Wine + MT5 + Signal Bridge"
    echo
    
    # Check prerequisites
    check_root
    
    # Create project structure
    create_project_structure
    
    # Check Wine
    check_wine
    
    # Check MT5
    check_mt5
    
    # Check Python dependencies
    check_python_deps
    
    # Copy files
    copy_files
    
    # Setup signal file
    setup_signal_file
    
    # Create utility scripts
    create_monitor_script
    create_stop_script
    
    echo
    log "=== DEPLOYMENT COMPLETE ==="
    log_success "Nyx AI system is ready to start"
    echo
    log "To start the system:"
    log "  cd $PROJECT_DIR"
    log "  ./deploy.sh start"
    echo
    log "To check status:"
    log "  cd $PROJECT_DIR"
    log "  ./monitor.sh"
    echo
    log "To stop the system:"
    log "  cd $PROJECT_DIR"
    log "  ./stop.sh"
    echo
    
    # Check if we should start now
    if [ "$1" = "start" ]; then
        log "=== STARTING SYSTEM ==="
        start_mt5
        start_bot
        show_status
    fi
}

# Handle command line arguments
case "$1" in
    "start")
        main "start"
        ;;
    "status")
        show_status
        ;;
    "")
        main
        ;;
    *)
        echo "Usage: $0 [start|status]"
        echo "  start   - Deploy and start the system"
        echo "  status  - Show system status"
        exit 1
        ;;
esac
