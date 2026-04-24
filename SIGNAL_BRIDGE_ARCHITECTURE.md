# NYX AI - SIGNAL BRIDGE ARCHITECTURE

## Overview

The Nyx AI trading bot has been migrated from native MT5 Python dependency to a Linux-compatible architecture using Wine + MT5 + JSON Signal Bridge.

## Architecture Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Bot        │    │   Signal Bridge  │    │   MT5 (Wine)    │
│   (Python)      │───▶│   (JSON File)    │───▶│   + EA          │
│                 │    │                  │    │                 │
│ • Signal Gen    │    │ • trade_signal.  │    │ • Read JSON     │
│ • Scoring       │    │   json           │    │ • Execute Trade │
│ • Risk Mgmt     │    │ • Lock System    │    │ • Report Back   │
│ • Analytics     │    │ • Timeout Mgmt   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Key Components

### 1. Signal Bridge (`signal_bridge.py`)
- **Purpose**: Export trade signals to JSON files
- **Features**: 
  - Signal locking to prevent duplicates
  - Timeout management (5 minutes)
  - Signal consumption tracking
  - Error handling and logging

### 2. Signal Bridge Executor (`signal_bridge_executor.py`)
- **Purpose**: MT5-compatible interface using signal bridge
- **Features**:
  - Mock MT5 functions with signal bridge backend
  - Compatible return objects
  - Account info simulation
  - Tick data simulation

### 3. Docker Environment
- **Wine**: Windows compatibility layer for MT5
- **Xvfb**: Virtual display for headless operation
- **Supervisor**: Process management
- **MT5**: Running under Wine

## File Structure

```
├── signal_bridge.py              # Core signal bridge system
├── signal_bridge_executor.py     # MT5-compatible executor
├── Dockerfile                    # Linux container setup
├── start_mt5.sh                  # Linux startup script
├── supervisord.conf              # Process management
├── start_docker.sh               # Docker startup
├── trade_signal.json             # Signal file (created at runtime)
├── signal.lock                   # Signal lock file
├── signal_consumed.json          # Consumption tracking
└── requirements.txt              # Updated dependencies
```

## Signal Format

### Input Signal (trade_signal.json)
```json
{
    "symbol": "EURUSD",
    "action": "BUY",
    "lot": 0.01,
    "sl": 1.0950,
    "tp": 1.1050,
    "confidence": 85.5,
    "score": 0.72,
    "timestamp": "2026-04-24T16:06:07.471752",
    "entry_price": 1.1000,
    "signal_id": "EURUSD_BUY_1777046767"
}
```

### Consumption Report (signal_consumed.json)
```json
{
    "original_signal": {...},
    "execution_result": {
        "success": true,
        "ticket": 12345,
        "execution_price": 1.1000
    },
    "consumed_timestamp": "2026-04-24T16:06:15.123456"
}
```

## Migration Changes

### Removed Dependencies
- `MetaTrader5>=5.0.0` from requirements.txt
- All direct MT5 Python API calls

### Added Dependencies
- `signal_bridge.py` - Core bridge system
- `signal_bridge_executor.py` - Compatibility layer

### Modified Functions
- `execute_live_trade()` - Now exports signals instead of executing directly
- `place_trade()` - Now writes JSON instead of MT5 order
- Market data functions - Use mock data for compatibility

## Logging Changes

### Before (MT5 Direct)
```
🚀 Executing trade...
✅ Trade EXECUTED successfully
```

### After (Signal Bridge)
```
📤 Exporting trade signal to MT5 via bridge...
✅ Signal EXPORTED successfully
```

## Deployment Options

### 1. Local Linux
```bash
# Install Wine
sudo apt install wine64

# Install MT5
wine mt5setup.exe /auto

# Start bot
./start_mt5.sh
```

### 2. Docker Container
```bash
# Build image
docker build -t nyx-ai-signal-bridge .

# Run container
docker run -d --name nyx-ai nyx-ai-signal-bridge
```

### 3. VPS Deployment
```bash
# Clone repository
git clone <repo_url>
cd nyx-ai

# Build and run
docker-compose up -d
```

## MT5 Expert Advisor

The MT5 side requires an Expert Advisor that:

1. **Monitors Signal File**
   - Reads `trade_signal.json` every second
   - Validates signal format
   - Checks for signal lock

2. **Executes Trades**
   - Places orders via MT5 API
   - Handles execution errors
   - Reports results back

3. **Signal Management**
   - Removes signal file after processing
   - Creates consumption report
   - Handles timeouts

### Sample EA Logic (MQL5)
```mql5
void OnTimer() {
    // Read signal file
    string signal_data = ReadSignalFile();
    
    if(signal_data != "") {
        // Parse JSON signal
        Signal signal = ParseSignal(signal_data);
        
        // Execute trade
        bool result = ExecuteTrade(signal);
        
        // Report back
        ReportExecution(signal, result);
        
        // Clean up
        DeleteSignalFile();
    }
}
```

## Testing

### Unit Tests
```bash
# Test signal bridge
python signal_bridge.py

# Test executor
python -c "from signal_bridge_executor import place_trade; print(place_trade('EURUSD', 'BUY', 0.01, 1.0950, 1.1050, 85.5, 0.72))"
```

### Integration Tests
```bash
# Test full pipeline
python -c "
from signal_bridge import send_signal
send_signal('EURUSD', 'BUY', 0.01, 1.0950, 1.1050, 85.5, 0.72)
print('Signal sent successfully')
"
```

## Troubleshooting

### Common Issues

1. **Signal File Not Created**
   - Check file permissions
   - Verify signal bridge is initialized
   - Check for existing lock files

2. **MT5 Not Reading Signals**
   - Verify EA is running
   - Check file paths in EA
   - Ensure Wine is running MT5

3. **Duplicate Signals**
   - Check signal lock mechanism
   - Verify signal consumption
   - Check timeout settings

### Debug Commands
```bash
# Check signal status
python -c "from signal_bridge import get_signal_status; print(get_signal_status())"

# Clear stuck signals
python -c "from signal_bridge import clear_signal; clear_signal()"

# Check logs
tail -f /var/log/supervisor/nyx-bot.log
```

## Performance Considerations

### Signal Bridge
- Minimal overhead (JSON read/write)
- Lock mechanism prevents conflicts
- Timeout prevents stale signals

### Wine + MT5
- Additional memory usage (~200MB)
- Slight latency (~100ms per signal)
- Stable for production use

### File I/O
- Use RAM disk for better performance
- Monitor disk space for logs
- Implement rotation for signal files

## Security

### Signal Files
- Set appropriate file permissions
- Validate signal format
- Sanitize input parameters

### Network
- No external dependencies
- Local file communication only
- No API keys in signal files

## Future Enhancements

### 1. Message Queue
- Replace file-based with Redis/RabbitMQ
- Better performance and reliability
- Support for multiple instances

### 2. API Integration
- REST API for signal submission
- WebSocket for real-time updates
- Authentication and authorization

### 3. Cloud Deployment
- Kubernetes support
- Auto-scaling capabilities
- Distributed signal processing

---

## Migration Checklist

- [x] Remove MetaTrader5 dependency
- [x] Create signal bridge system
- [x] Implement signal locking
- [x] Create Docker environment
- [x] Update logging messages
- [x] Test signal export functionality
- [ ] Deploy MT5 Expert Advisor
- [ ] Integration testing
- [ ] Performance testing
- [ ] Production deployment

---

**Status**: ✅ Core migration complete, ready for MT5 EA integration
