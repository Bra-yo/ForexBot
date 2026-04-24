# NYX AI - LOCAL STARTUP GUIDE

## Quick Start (3 Steps)

### Step 1: Open MetaTrader 5
- Launch MT5 on your computer
- Login to your demo account
- Keep MT5 running in the background

### Step 2: Start the Bot
```bash
cd c:\Users\ESSENCE\CascadeProjects\windsurf-project
python start_local_bot.py
```

### Step 3: Monitor the Bot
- Watch the console output
- Check `local_bot.log` for detailed logs
- Use Ctrl+C to stop safely

## What the Bot Does

### Safety Checks First
- Verifies MT5 is connected
- Checks account balance and equity
- Validates all required files exist

### Trading Parameters (Local)
- **Max 10 trades per day** (conservative)
- **Max 5 concurrent trades** (safe)
- **Lot size: 0.01** (minimum risk)
- **Max spread: 10 pips** (local broker friendly)
- **Trading hours: 1:00-21:00 UTC** (all sessions)

### Pairs Traded
- EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD
- EURGBP, EURJPY, NZDUSD (if available)

### Safety Features
- Weekend protection (no Saturday/Sunday trading)
- Market open verification
- Spread validation
- Volatility filter
- Correlation control
- Drawdown protection

## Monitoring

### Console Output Shows:
```
=== NYX AI LOCAL BOT STARTING ===
Time: 2026-04-13 18:14:00
Connected to account: 5048146647
Server: MetaQuotes-Demo
Balance: $99,938.00
Starting multi-pair trading...
EURUSD | SELL | Conf: 67.6% | Score: 0.48 | ATTEMPTING
EURUSD | SELL | Conf: 67.6% | Score: 0.48 | EXECUTED
```

### Log File:
- All detailed logs saved to `local_bot.log`
- Check for errors or trade details

## Troubleshooting

### MT5 Connection Issues
- Make sure MT5 is running
- Check you're logged into a demo account
- Try restarting MT5

### No Trades Executing
- Check if market is open (not weekend)
- Verify spread is below 10 pips
- Ensure trading session is active

### Bot Crashes
- Check `local_bot.log` for error details
- Ensure all Python packages are installed
- Verify internet connection

## Stopping the Bot

### Safe Stop
- Press `Ctrl+C` in the console
- Bot will close all open positions
- Wait for "Bot stopped safely" message

### Emergency Stop
- Create `stop.txt` file in the bot directory
- Bot will detect and stop immediately

## Configuration

### Edit Settings
- Modify `.env` file to change parameters
- Adjust lot sizes, trading hours, etc.
- Restart bot after changes

### Telegram Notifications (Optional)
- Set `ENABLE_TELEGRAM_NOTIFICATIONS=True` in `.env`
- Add your bot token and chat ID
- Get trade alerts on your phone

## Performance Tips

### For Local Machine
- Close unnecessary applications
- Ensure stable internet connection
- Keep MT5 in background (don't minimize)

### For Better Performance
- Use SSD for faster I/O
- Ensure good RAM (8GB+ recommended)
- Stable internet connection crucial

## Support

### Check Status
- Console shows real-time status
- Log file has detailed information
- Trade memory saved in `trade_history.json`

### Common Issues
1. **"MT5 not connected"** - Launch MT5 and login
2. **"Weekend protection"** - Wait for market open
3. **"High spread"** - Normal for local brokers
4. **"No trades"** - Check market conditions

---

**Ready to start? Run: `python start_local_bot.py`**
