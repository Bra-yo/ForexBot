# MT5 SETUP GUIDE
## Nyx AI Signal Bridge - Expert Advisor Installation

This guide covers the complete setup of MT5 under Wine and installation of the Nyx AI Expert Advisor for Linux compatibility.

## 📋 PREREQUISITES

### System Requirements
- **Linux OS**: Ubuntu 20.04+ or compatible
- **Wine**: 6.0+ (latest stable recommended)
- **Memory**: 4GB+ RAM
- **Storage**: 10GB+ free space
- **Display**: X11 server (for GUI) or headless setup

### Software Installation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Wine
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install -y wine64 wine32 winetricks

# Install X11 (if headless)
sudo apt install -y xvfb
```

---

## 🍷 WINE CONFIGURATION

### Initialize Wine
```bash
# Initialize Wine configuration
winecfg --auto

# Set Windows version to Windows 10
# Tools → Winecfg → Windows Version → Windows 10
```

### Install Required Components
```bash
# Install .NET Framework (required by MT5)
winetricks dotnet48

# Install Visual C++ runtimes
winetricks vcrun2019 vcrun2022

# Install fonts (for better display)
winetricks corefonts
```

---

## 📥 MT5 INSTALLATION

### Download MT5
```bash
# Create download directory
mkdir -p ~/downloads
cd ~/downloads

# Download MT5 installer
wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
```

### Install MT5
```bash
# Silent installation
wine mt5setup.exe /auto /quiet

# Or interactive installation
wine mt5setup.exe
```

### Verify Installation
```bash
# Check if MT5 is installed
ls -la ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/terminal64.exe
```

---

## 🤖 NYX AI EXPERT ADVISOR SETUP

### Copy EA to MT5
```bash
# Copy EA to MT5 Experts folder
cp NyxEA.mq5 ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/MQL5/Experts/

# Copy any necessary libraries (if present)
cp *.mqh ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/MQL5/Include/ 2>/dev/null || true
```

### Start MT5
```bash
# Start MT5 (with GUI)
wine ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/terminal64.exe

# Or headless (for production)
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &
wine ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/terminal64.exe &
```

---

## ⚙️ MT5 CONFIGURATION

### Enable AutoTrading
1. **Open MT5**
2. **Click AutoTrading button** (green play icon)
3. **Or**: Tools → Options → Expert Advisors → Enable AutoTrading

### Enable DLL Imports
1. **Tools → Options**
2. **Expert Advisors tab**
3. **Check "Allow DLL imports"**
4. **Check "Allow external experts"**

### Configure Expert Advisor
1. **Navigate to Navigator → Expert Advisors**
2. **Find "NyxEA"**
3. **Right-click → Properties**
4. **Common tab**:
   - Allow live trading: ✅
   - Allow DLL imports: ✅
5. **Parameters tab**:
   - SignalFilePath: `/home/ubuntu/nyx-ai/trade_signal.json`
   - MaxRetries: 3
   - RetryDelayMs: 1000
   - MaxLotSize: 0.5
   - MagicNumber: 123456

---

## 📊 ATTACH EA TO CHARTS

### Method 1: Manual Attachment
1. **Open desired currency pair chart** (e.g., EURUSD)
2. **Drag NyxEA from Navigator to chart**
3. **Configure parameters in popup window**
4. **Click OK**

### Method 2: Template Attachment
1. **Configure one chart with EA**
2. **Save as Template**: Right-click → Template → Save Template
3. **Apply to other charts**: Right-click → Template → Load Template

### Recommended Charts
Attach EA to these major currency pairs:
- **EURUSD** - Primary
- **GBPUSD** - Secondary
- **USDJPY** - Tertiary
- **AUDUSD** - Additional
- **USDCAD** - Additional

---

## 🔧 SIGNAL FILE CONFIGURATION

### Create Signal Directory
```bash
# Create signal directory
mkdir -p /home/ubuntu/nyx-ai

# Set permissions
chmod 755 /home/ubuntu/nyx-ai
chmod 666 /home/ubuntu/nyx-ai/trade_signal.json 2>/dev/null || true
```

### Verify File Access
```bash
# Test file creation
echo '{"test": "signal"}' > /home/ubuntu/nyx-ai/trade_signal.json

# Check permissions
ls -la /home/ubuntu/nyx-ai/trade_signal.json
```

---

## 🧪 TESTING THE SETUP

### Test Signal Creation
```bash
# Use the test script
cd /home/ubuntu/nyx-ai
python3 test_signal.py create

# Check signal file
cat /home/ubuntu/nyx-ai/trade_signal.json
```

### Test EA Response
1. **Ensure MT5 is running**
2. **Ensure EA is attached to chart**
3. **Create test signal**
4. **Check MT5 Experts tab for messages**
5. **Check if trade executes**

### Debug EA Issues
1. **Open MT5 → Tools → Options → Expert Advisors**
2. **Check "Enable logging"**
3. **Set log level to "Detailed"**
4. **Restart MT5**
5. **Check logs**: `~/.wine/drive_c/Program Files/MetaTrader 5/logs/`

---

## 🚨 TROUBLESHOOTING

### Common Issues

#### EA Not Loading
**Problem**: EA doesn't appear in Navigator
**Solution**:
```bash
# Verify EA file exists
ls -la ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/MQL5/Experts/NyxEA.mq5

# Check file permissions
chmod 644 ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/MQL5/Experts/NyxEA.mq5

# Restart MT5
```

#### AutoTrading Disabled
**Problem**: "AutoTrading is disabled" message
**Solution**:
1. Click AutoTrading button in MT5
2. Enable in Tools → Options → Expert Advisors
3. Check account permissions with broker

#### File Access Issues
**Problem**: EA cannot read signal file
**Solution**:
```bash
# Check file path in EA parameters
# Ensure absolute path: /home/ubuntu/nyx-ai/trade_signal.json

# Set proper permissions
chmod 666 /home/ubuntu/nyx-ai/trade_signal.json

# Test file access from Wine
wine cmd /c "type /home/ubuntu/nyx-ai/trade_signal.json"
```

#### Trade Execution Fails
**Problem**: Signal received but trade doesn't execute
**Solution**:
1. Check account balance
2. Verify symbol is tradable
3. Check trading hours
4. Verify lot size limits
5. Check broker restrictions

#### Wine Performance Issues
**Problem**: MT5 runs slowly under Wine
**Solution**:
```bash
# Optimize Wine settings
winecfg

# In WineCfg:
# - Graphics: Disable vertex shaders
# - Windows: Set to Windows 10
# - Audio: Disable if not needed

# Use virtual display for headless
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &
```

---

## 📝 LOGGING AND MONITORING

### EA Logs Location
```
~/.wine/drive_c/Program Files/MetaTrader 5/logs/
├── 2024/
│   ├── 20240424.log
│   └── experts.log
```

### Python Bot Logs
```
/home/ubuntu/nyx-ai/logs/
├── bot.log
├── signal_bridge.log
└── analytics.log
```

### Real-time Monitoring
```bash
# Monitor signal file
tail -f /home/ubuntu/nyx-ai/trade_signal.json

# Monitor Python logs
tail -f /home/ubuntu/nyx-ai/logs/bot.log

# Monitor MT5 logs
tail -f ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/logs/experts.log
```

---

## 🔒 SECURITY CONSIDERATIONS

### File Permissions
```bash
# Secure signal directory
chmod 755 /home/ubuntu/nyx-ai
chmod 644 /home/ubuntu/nyx-ai/*.json

# Restrict access to sensitive files
chmod 600 ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/config/terminal.ini
```

### Network Security
- MT5 runs under Wine isolation
- No direct network access from EA
- Signal files are local only
- No API keys in signal files

---

## 📈 PERFORMANCE OPTIMIZATION

### MT5 Optimization
1. **Disable unnecessary features**:
   - News feed
   - Economic calendar
   - Market depth

2. **Optimize chart settings**:
   - Limit history bars
   - Disable indicators on non-trading charts
   - Use M15 timeframe for signal processing

3. **Wine performance**:
   - Use virtual display for headless
   - Allocate sufficient memory
   - Monitor CPU usage

### Signal Processing
- EA processes signals every tick
- File I/O is minimal
- No network latency
- Local processing only

---

## 🔄 MAINTENANCE

### Daily Tasks
1. **Check log files for errors**
2. **Verify signal file permissions**
3. **Monitor trade execution**
4. **Check system resources**

### Weekly Tasks
1. **Backup configuration files**
2. **Clean old log files**
3. **Update EA if needed**
4. **Review trade performance**

### Monthly Tasks
1. **Update Wine if needed**
2. **Update MT5 if available**
3. **Security audit**
4. **Performance review**

---

## 📞 SUPPORT

### Common Debug Commands
```bash
# Check if MT5 is running
ps aux | grep terminal64.exe

# Check Wine processes
ps aux | grep wine

# Test signal file creation
echo '{"test": "signal"}' > /home/ubuntu/nyx-ai/trade_signal.json

# Check file permissions
ls -la /home/ubuntu/nyx-ai/

# Monitor system resources
htop
```

### Log Analysis
```bash
# Find EA errors in MT5 logs
grep -i error ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/logs/experts.log

# Find signal bridge errors
grep -i error /home/ubuntu/nyx-ai/logs/bot.log

# Check recent trades
grep "SIGNAL SENT" /home/ubuntu/nyx-ai/logs/bot.log | tail -10
```

---

## ✅ VALIDATION CHECKLIST

Before going live, verify:

- [ ] Wine is properly installed and configured
- [ ] MT5 installs and runs under Wine
- [ ] NyxEA.mq5 is copied to Experts folder
- [ ] EA compiles without errors
- [ ] AutoTrading is enabled
- [ ] DLL imports are allowed
- [ ] Signal file path is correct
- [ ] File permissions are set
- [ ] Test signal executes successfully
- [ ] Logs show no critical errors
- [ ] System resources are adequate
- [ ] Backup procedures are in place

---

**Status**: Ready for production deployment once all validation checks pass.
