# BrayoForexBot Dashboard

Professional web-based trading interface for the AI-powered forex trading bot.

## 🚀 Quick Start

### Method 1: Easy Launcher
```bash
python dashboard/run_dashboard.py
```

### Method 2: Manual Start
```bash
# Install requirements
pip install -r dashboard/requirements.txt

# Run dashboard
streamlit run dashboard/app.py
```

## 🌐 Features

### 📊 Real-time Monitoring
- **Live Price Charts**: Candlestick charts with technical indicators
- **Equity Curve**: Track your account performance over time
- **Open Positions**: Monitor active trades with P&L
- **Recent Activity**: Latest trading actions and results

### 🤖 AI Integration
- **AI Performance**: Track ML model predictions and accuracy
- **Model Comparison**: Compare different AI models
- **Confidence Metrics**: Monitor AI decision confidence
- **Hybrid Decisions**: AI + Traditional signal combination

### 🎛️ Trading Controls
- **Start/Stop Trading**: Control bot operation
- **Symbol Selection**: Choose which pairs to trade
- **AI Settings**: Adjust confidence thresholds and weights
- **Risk Management**: Configure position sizing and limits

### 📈 Analytics
- **Performance Metrics**: Win rate, profit factor, Sharpe ratio
- **Account Overview**: Balance, equity, margin status
- **Trading History**: Complete trade log with results
- **Real-time Updates**: Live data streaming

## 🔧 Setup

### Prerequisites
- Python 3.8+
- MetaTrader 5 terminal
- MT5 demo or live account

### Configuration
1. **MT5 Connection**: Enter your MT5 credentials in the sidebar
2. **Symbol Selection**: Choose forex pairs to trade
3. **AI Settings**: Configure confidence thresholds
4. **Risk Limits**: Set maximum position size and risk

## 📱 Interface

### Sidebar Controls
- Connection status indicator
- Trading start/stop buttons
- Symbol selection
- AI configuration
- Risk management settings

### Main Dashboard
- **Status Bar**: Trading status, last update, positions
- **Metrics Row**: Balance, equity, margin, win rate
- **Charts**: Price chart with indicators, equity curve
- **Activity Panel**: Open positions, recent trades
- **AI Performance**: Model metrics and statistics

## 🛡️ Safety Features

### Risk Management
- Maximum position size limits
- Daily loss limits
- Stop loss and take profit
- Margin monitoring

### AI Safeguards
- Confidence thresholds
- Ensemble decision making
- Model validation
- Fallback to traditional signals

### Monitoring
- Real-time connection status
- Trade execution tracking
- Performance alerts
- Error handling

## 🎯 Usage Tips

1. **Start with Demo**: Always test with demo account first
2. **Monitor Closely**: Watch the bot initially
3. **Adjust Settings**: Fine-tune AI confidence thresholds
4. **Review Performance**: Regularly check AI accuracy
5. **Keep Logs**: Monitor trading decisions and results

## 📊 Dashboard Sections

### Connection Status
- MT5 connection indicator
- Account balance and equity
- Server status

### Trading Controls
- Start/stop trading
- Symbol selection
- AI enable/disable
- Risk management toggle

### Performance Metrics
- Real-time P&L
- Win rate percentage
- Number of trades
- AI decision count

### Charts
- **Price Chart**: Live candlestick chart with MA indicators
- **Equity Curve**: Account value over time
- **Performance**: AI model comparison charts

### Positions
- Open positions table
- Entry/exit prices
- Current P&L
- Stop loss/take profit levels

### Activity Log
- Recent trades
- Trading actions
- AI predictions
- Performance results

## 🔧 Technical Details

### Architecture
- **Frontend**: Streamlit web interface
- **Backend**: Python trading engine
- **Data**: Real-time MT5 connection
- **AI**: Machine learning predictions

### Data Flow
1. MT5 provides real-time price data
2. AI models generate trading signals
3. Risk manager validates decisions
4. Orders executed through MT5
5. Results displayed in dashboard

### Performance
- **Update Frequency**: Every 1-5 seconds
- **Data Sources**: MT5 real-time feed
- **Latency**: <100ms for most operations
- **Scalability**: Supports multiple symbols

## 🚨 Important Notes

- **Demo First**: Always start with demo account
- **Monitor**: Keep an eye on the bot initially
- **Backup**: Save your trading data regularly
- **Security**: Never share your MT5 credentials
- **Risk**: Only trade what you can afford to lose

## 📞 Support

For issues or questions:
1. Check the logs for error messages
2. Verify MT5 connection and credentials
3. Ensure all dependencies are installed
4. Review trading configuration

## 🔄 Updates

The dashboard automatically updates in real-time:
- Price data: Every second
- Positions: Every 5 seconds
- Performance: Every 10 seconds
- AI metrics: Every 30 seconds

---

**Built with ❤️ for professional forex trading**
