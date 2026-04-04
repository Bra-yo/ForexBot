"""
RISK MANAGER - Professional Risk Control
Handles correlation, exposure, session filtering, and volatility checks
"""

import time
import MetaTrader5 as mt5
from datetime import datetime
from config import *

class RiskManager:
    """Professional risk management and exposure control"""
    
    def __init__(self):
        self.average_spreads = {}  # Track average spreads for each symbol
        self.last_atr_values = {}  # Cache ATR values
        
    def check_session_filter(self):
        """Check if current time is within allowed trading sessions"""
        if not ENABLE_SESSION_FILTER:
            return True, "Session filter disabled"
            
        current_hour = datetime.now().hour
        
        # Check Asian session (00:00-08:00 UTC)
        asian_active = ASIAN_SESSION_START <= current_hour < ASIAN_SESSION_END
        # Check London session (08:00-17:00 UTC)
        london_active = LONDON_SESSION_START <= current_hour < LONDON_SESSION_END
        # Check New York session (13:00-22:00 UTC)
        ny_active = NEW_YORK_SESSION_START <= current_hour < NEW_YORK_SESSION_END
        
        if asian_active or london_active or ny_active:
            session_info = []
            if asian_active:
                session_info.append("Asian")
            if london_active:
                session_info.append("London")
            if ny_active:
                session_info.append("New York")
            return True, f"Allowed: {', '.join(session_info)} session"
        else:
            return False, f"Blocked: Outside trading hours (Asian: {ASIAN_SESSION_START}-{ASIAN_SESSION_END}, London: {LONDON_SESSION_START}-{LONDON_SESSION_END}, NY: {NEW_YORK_SESSION_START}-{NEW_YORK_SESSION_END} UTC)"
            
    def check_volatility_filter(self, symbol):
        """Check for news volatility and spread expansion"""
        if not ENABLE_NEWS_FILTER:
            return True, "Volatility filter disabled"
            
        try:
            # Get current candle data
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 2)
            if not rates or len(rates) < 2:
                return True, "No candle data"
                
            current_candle = rates[-1]
            previous_candle = rates[-2]
            
            # Calculate candle range
            candle_range = abs(current_candle['high'] - current_candle['low'])
            
            # Get ATR for comparison
            atr_value = self.get_atr_value(symbol)
            # 🔧 LEVEL 10.2: ROBUST ARRAY HANDLING
            if atr_value is not None:
                # Convert to scalar if it's an array
                try:
                    if hasattr(atr_value, '__len__') and len(atr_value) > 0:
                        atr_value = atr_value[-1]  # Use last value
                    elif hasattr(atr_value, 'item'):
                        atr_value = atr_value.item()  # Convert numpy scalar
                    elif hasattr(atr_value, 'any'):  # numpy array
                        if atr_value.any():  # Use .any() instead of direct boolean
                            atr_value = float(atr_value[-1])
                        else:
                            atr_value = 0.0
                    else:
                        atr_value = float(atr_value)  # Force convert to float
                except (ValueError, TypeError, AttributeError) as e:
                    print(f"ATR conversion error: {e}")
                    atr_value = 0.001  # Safe fallback
                    
                if atr_value > 0:  # Ensure scalar and valid
                    # Check if current range > 2× ATR (news spike)
                    if candle_range > atr_value * VOLATILITY_SPIKE_MULTIPLIER:
                        return False, f"Volatility spike ({candle_range:.5f} > {atr_value * VOLATILITY_SPIKE_MULTIPLIER:.5f})"
            
            # Check spread expansion
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                current_spread = tick.ask - tick.bid
                avg_spread = self.get_average_spread(symbol)
                
                if avg_spread and current_spread > avg_spread * SPREAD_EXPANSION_MULTIPLIER:
                    return False, f"Blocked: Spread expansion ({current_spread*10000:.1f} > {avg_spread*10000*SPREAD_EXPANSION_MULTIPLIER:.1f} pips)"
                    
            return True, "Volatility check passed"
            
        except Exception as e:
            print(f"Volatility filter error: {e}")
            return True, "Volatility filter error"
            
    def check_correlation_control(self, symbol, signal):
        """Check correlation and exposure limits"""
        if not ENABLE_CORRELATION_CONTROL:
            return True, "Correlation control disabled"
            
        positions = mt5.positions_get()
        if not positions:
            return True, "No open positions"
            
        # Count current exposures
        usd_direction_count = 0
        jpy_related_count = 0
        
        for pos in positions:
            pos_signal = "BUY" if pos.type == 0 else "SELL"
            
            # Count USD-direction trades
            if pos.symbol in CORRELATED_PAIRS['USD_BASE']:
                if pos_signal == "BUY":
                    usd_direction_count += 1
            elif pos.symbol in CORRELATED_PAIRS['USD_QUOTE']:
                if pos_signal == "SELL":
                    usd_direction_count += 1
                    
            # Count JPY-related trades
            if pos.symbol in CORRELATED_PAIRS['JPY_RELATED']:
                jpy_related_count += 1
                
        # Check new trade would exceed limits
        new_usd_direction = 0
        new_jpy_related = 0
        
        if symbol in CORRELATED_PAIRS['USD_BASE'] and signal == "BUY":
            new_usd_direction = 1
        elif symbol in CORRELATED_PAIRS['USD_QUOTE'] and signal == "SELL":
            new_usd_direction = 1
            
        if symbol in CORRELATED_PAIRS['JPY_RELATED']:
            new_jpy_related = 1
            
        # Check limits
        if usd_direction_count + new_usd_direction > MAX_USD_DIRECTION_TRADES:
            return False, f"Blocked: USD direction limit ({usd_direction_count + new_usd_direction} > {MAX_USD_DIRECTION_TRADES})"
            
        if jpy_related_count + new_jpy_related > MAX_JPY_RELATED_TRADES:
            return False, f"Blocked: JPY-related limit ({jpy_related_count + new_jpy_related} > {MAX_JPY_RELATED_TRADES})"
            
        return True, "Correlation check passed"
        
    def check_global_risk(self):
        """Check if global risk limits are exceeded"""
        positions = mt5.positions_get()
        if not positions:
            return True, 0.0, "No open positions"
            
        account_info = mt5.account_info()
        if not account_info:
            return True, 0.0, "No account info"
            
        # Calculate total risk based on SL distances
        total_risk_amount = 0.0
        for pos in positions:
            if pos.profit < 0:  # Only count losing positions
                risk_distance = abs(pos.price_open - pos.sl)
                position_risk = risk_distance * pos.volume * 100000  # Approximate pip value
                total_risk_amount += position_risk
                
        risk_percentage = (total_risk_amount / account_info.balance) * 100 if account_info.balance > 0 else 0
        
        if risk_percentage > MAX_GLOBAL_RISK * 100:
            return False, risk_percentage, f"Global risk limit exceeded ({risk_percentage:.1f}% > {MAX_GLOBAL_RISK*100:.1f}%)"
            
        return True, risk_percentage, f"Global risk acceptable ({risk_percentage:.1f}% <= {MAX_GLOBAL_RISK*100:.1f}%)"
        
    def get_atr_value(self, symbol):
        """Get ATR value for symbol"""
        if symbol in self.last_atr_values:
            return self.last_atr_values[symbol]
            
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, ATR_PERIOD + 1)
            if not rates or len(rates) < ATR_PERIOD:
                return None
                
            # Calculate ATR (simplified)
            true_ranges = []
            for i in range(1, len(rates)):
                high_low = rates[i]['high'] - rates[i]['low']
                high_close = abs(rates[i]['high'] - rates[i-1]['close'])
                low_close = abs(rates[i]['low'] - rates[i-1]['close'])
                true_ranges.append(max(high_low, high_close, low_close))
                
            # Use the LAST value, not the array
            atr = sum(true_ranges[-ATR_PERIOD:]) / ATR_PERIOD
            self.last_atr_values[symbol] = atr
            return atr  # Return scalar value, not array
            
        except Exception as e:
            print(f"ATR calculation error for {symbol}: {e}")
            return None
            
    def get_average_spread(self, symbol):
        """Get average spread for symbol"""
        if symbol in self.average_spreads:
            return self.average_spreads[symbol]
            
        # For now, return a reasonable default
        # In production, this would track historical spreads
        default_spreads = {
            'EURUSD': 0.0001,  # 1 pip
            'GBPUSD': 0.0001,  # 1 pip
            'USDJPY': 0.01,     # 1 pip
            'AUDUSD': 0.0001,  # 1 pip
            'USDCAD': 0.0001,  # 1 pip
            'EURGBP': 0.0001,  # 1 pip
            'EURJPY': 0.01,     # 1 pip
            'GBPJPY': 0.01,     # 1 pip
            'NZDUSD': 0.0001,  # 1 pip
            'EURCHF': 0.0001,  # 1 pip
        }
        return default_spreads.get(symbol, 0.0001)
        
    def update_average_spread(self, symbol, spread):
        """Update running average spread for symbol"""
        if symbol not in self.average_spreads:
            self.average_spreads[symbol] = spread
        else:
            # Simple exponential moving average
            alpha = 0.1  # Smoothing factor
            self.average_spreads[symbol] = alpha * spread + (1 - alpha) * self.average_spreads[symbol]
            
    def log_risk_decision(self, symbol, signal, reason, allowed):
        """Log risk management decisions"""
        if not ENABLE_ADVANCED_LOGGING:
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S')
        status = "ALLOWED" if allowed else "BLOCKED"
        print(f"[{timestamp}] RISK MANAGER: {symbol} {signal} - {status} - {reason}")
        
    def get_portfolio_summary(self):
        """Get current portfolio risk summary"""
        positions = mt5.positions_get()
        if not positions:
            return "No open positions"
            
        total_exposure = 0.0
        total_risk = 0.0
        symbol_counts = {}
        direction_counts = {"BUY": 0, "SELL": 0}
        
        for pos in positions:
            total_exposure += pos.volume * 100000  # Approximate
            total_risk += abs(pos.price_open - pos.sl) * pos.volume * 100000
            
            symbol_counts[pos.symbol] = symbol_counts.get(pos.symbol, 0) + 1
            direction_counts["BUY" if pos.type == 0 else "SELL"] += 1
            
        account_info = mt5.account_info()
        risk_percentage = (total_risk / account_info.balance) * 100 if account_info.balance > 0 else 0
        
        summary = f"""
PORTFOLIO RISK SUMMARY
========================
Total Positions: {len(positions)}
Total Exposure: ${total_exposure:,.0f}
Total Risk: ${total_risk:,.0f}
Risk Percentage: {risk_percentage:.2f}%

Direction Breakdown:
  BUY: {direction_counts['BUY']}
  SELL: {direction_counts['SELL']}

Symbol Breakdown:"""
        
        for symbol, count in symbol_counts.items():
            summary += f"\n  {symbol}: {count}"
            
        return summary
