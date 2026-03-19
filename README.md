# 🤖 BrayoForexBot

A Forex AI Trading Bot that analyzes market data and makes automated trading decisions.

## 📋 What This Bot Does

- **Reads market data** (price charts)
- **Analyzes it** (like a trader)
- **Makes decisions**: BUY 📈, SELL 📉, WAIT ⏸️
- **Sends alerts** and manages positions automatically

## 🎯 Why This Bot

### 🧍 Humans are emotional
- Panic 😭
- Greedy 😤  
- Overtrade 😵
- **Result**: losses

### 🤖 Bots are disciplined
- Follow rules only
- No emotions
- No guessing
- Works 24/7
- **Result**: consistent decisions

### ⚡ Speed & Skills
- Analyzes in milliseconds
- Monitor multiple pairs at once
- Learn Python 🐍, Data analysis 📊, Automation 🤖, AI/ML 🧠

## 🚀 Quick Start

### 1. **Install and Setup**
```bash
python setup.py
```
This will:
- Install all dependencies
- Create `.env` file from template
- Set up necessary directories

### 2. **Configure Environment**
Edit `.env` file with your settings:
```bash
# Trading Configuration
TRADING_MODE=paper          # Start with paper trading!
RISK_PERCENTAGE=2.0         # Risk 2% per trade
MAX_POSITIONS=5              # Max 5 open positions

# Optional: Telegram Notifications
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. **Test the Bot**
```bash
# Test notifications (optional)
python cli.py test --notifications

# Test basic setup
python cli.py test
```

### 4. **Run Backtest First**
```bash
# Backtest EUR/USD for 2024
python cli.py backtest EUR/USD 2024-01-01 2024-12-31

# Backtest with different timeframe
python cli.py backtest GBP/USD 2024-01-01 2024-12-31 --timeframe 4h
```

### 5. **Start Trading**
```bash
# Start in paper trading mode (SAFE!)
python cli.py run

# Or run directly
python main.py
```

### 6. **Check Status**
```bash
python cli.py status
```

## 📁 Project Structure

```
BrayoForexBot/
├── main.py              # Main bot execution
├── cli.py               # Command line interface
├── setup.py             # Setup script
├── config.py            # Configuration settings
├── market_data.py       # Market data reader
├── technical_analysis.py # Technical indicators
├── trading_engine.py    # Trading decisions
├── risk_management.py   # Risk management
├── notifications.py     # Alert system
├── backtesting.py       # Backtesting module
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md           # This file
```

## ⚙️ Configuration

Edit `.env` file:

- `TRADING_MODE`: `paper` (demo) or `live` (real money)
- `RISK_PERCENTAGE`: Risk per trade (1-10%)
- `MAX_POSITIONS`: Maximum open positions
- `API_KEY`: Your broker API key
- `TELEGRAM_BOT_TOKEN`: For notifications

## 📊 Features

- **Technical Analysis**: RSI, Moving Averages, MACD
- **Risk Management**: Stop loss, position sizing
- **Multi-timeframe Analysis**: 1m to 1d charts
- **8 Major Currency Pairs**: EUR/USD, GBP/USD, etc.
- **Telegram Notifications**: Real-time alerts
- **Backtesting**: Test strategies before going live

## ⚠️ Risk Warning

**FOREX TRADING IS RISKY**. Never trade with money you can't afford to lose. This bot is for educational purposes. Start with paper trading!

## 🤝 Contributing

1. Fork the project
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📝 License

This project is for educational purposes only. Use at your own risk.

---

**Happy Trading! 📈**
