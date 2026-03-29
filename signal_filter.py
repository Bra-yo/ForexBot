"""
SIGNAL FILTER - Professional Multi-Timeframe Confirmation
Handles MTF alignment, priority scoring, and signal quality validation
"""

import MetaTrader5 as mt5
from config import *

class SignalFilter:
    """Professional signal filtering and confirmation"""
    
    def __init__(self):
        self.signal_queue = []  # Queue of pending signals
        self.last_cycle_time = 0
        
    def validate_mtf_alignment(self, symbol, signals):
        """Validate multi-timeframe signal alignment"""
        if not ENABLE_MTF_CONFIRMATION:
            return True, "MTF confirmation disabled"
            
        # Extract signals for each timeframe
        m15_signal = signals.get('M15')
        m30_signal = signals.get('M30')
        h1_signal = signals.get('H1')
        
        if not all([m15_signal, m30_signal, h1_signal]):
            return False, "Incomplete MTF signals"
            
        alignment_score = 0
        alignment_reasons = []
        
        # Check M15 + M30 alignment
        if MTF_ALIGNMENT_RULES['M15_M30_ALIGN']:
            if m15_signal['signal'] == m30_signal['signal']:
                alignment_score += 1
                alignment_reasons.append(f"M15+M30 aligned ({m15_signal['signal']})")
            else:
                alignment_reasons.append(f"M15+M30 misaligned ({m15_signal['signal']} vs {m30_signal['signal']})")
                
        # Check M30 + H1 alignment
        if MTF_ALIGNMENT_RULES['M30_H1_ALIGN']:
            if m30_signal['signal'] == h1_signal['signal']:
                alignment_score += 1
                alignment_reasons.append(f"M30+H1 aligned ({m30_signal['signal']})")
            else:
                alignment_reasons.append(f"M30+H1 misaligned ({m30_signal['signal']} vs {h1_signal['signal']})")
                
        # H1 override rule
        h1_confidence = h1_signal.get('confidence', 0)
        if h1_confidence > MTF_ALIGNMENT_RULES['H1_OVERRIDE']:
            alignment_score += 1
            alignment_reasons.append(f"H1 override (confidence: {h1_confidence:.1f}%)")
            
        # Minimum alignment score required
        min_alignment = 2  # Require at least 2 alignment conditions
        if alignment_score >= min_alignment:
            return True, f"MTF aligned ({alignment_score}/3): {'; '.join(alignment_reasons)}"
        else:
            return False, f"MTF misaligned ({alignment_score}/3): {'; '.join(alignment_reasons)}"
            
    def calculate_signal_priority(self, symbol, signal, confidence, trend_strength, volatility_quality):
        """Calculate priority score for signal"""
        if not ENABLE_PRIORITY_ENGINE:
            return 100, "Priority engine disabled"
            
        weights = PRIORITY_FACTORS
        
        # Normalize inputs to 0-100 scale
        norm_confidence = min(confidence, 100)
        norm_trend = min(trend_strength * 20, 100)  # Assuming trend strength 0-5
        norm_volatility = min(volatility_quality * 25, 100)  # Assuming volatility quality 0-4
        
        # Calculate weighted score
        priority_score = (
            norm_confidence * weights['confidence_weight'] +
            norm_trend * weights['trend_weight'] +
            norm_volatility * weights['volatility_weight']
        )
        
        # Add symbol-specific bonuses
        symbol_bonus = self.get_symbol_bonus(symbol)
        priority_score += symbol_bonus
        
        return priority_score, f"Score: {priority_score:.1f} (Conf:{norm_confidence:.0f}, Trend:{norm_trend:.0f}, Vol:{norm_volatility:.0f}, Bonus:{symbol_bonus:.0f})"
        
    def get_symbol_bonus(self, symbol):
        """Get symbol-specific priority bonus"""
        # Major pairs get higher priority
        if symbol in SYMBOL_GROUPS['MAJORS']:
            return 10
        elif symbol in SYMBOL_GROUPS['CROSSES']:
            return 5
        else:
            return 0
            
    def rank_signals(self, signals):
        """Rank signals by priority and return top N"""
        if not ENABLE_PRIORITY_ENGINE:
            return list(signals.values())[:MAX_TRADES_PER_CYCLE]
            
        # Calculate priority scores for all signals
        scored_signals = []
        for symbol, signal_data in signals.items():
            if signal_data.get('confidence', 0) < MTF_MIN_CONFIDENCE:
                continue
                
            score, reason = self.calculate_signal_priority(
                symbol,
                signal_data['signal'],
                signal_data['confidence'],
                signal_data.get('trend_strength', 2.5),
                signal_data.get('volatility_quality', 2.5)
            )
            
            scored_signals.append({
                'symbol': symbol,
                'signal': signal_data['signal'],
                'confidence': signal_data['confidence'],
                'score': score,
                'reason': reason,
                'timeframes': signal_data.get('timeframes', [])
            })
            
        # Sort by score (highest first)
        scored_signals.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top N signals
        top_signals = scored_signals[:MAX_TRADES_PER_CYCLE]
        
        if ENABLE_ADVANCED_LOGGING:
            print(f"\nSIGNAL RANKING:")
            for i, sig in enumerate(scored_signals[:5]):  # Show top 5
                status = "SELECTED" if i < len(top_signals) else "REJECTED"
                print(f"  {i+1}. {sig['symbol']} {sig['signal']} - Score: {sig['score']:.1f} - {status}")
                print(f"      {sig['reason']}")
                
        return top_signals
        
    def filter_signal_quality(self, symbol, signal_data):
        """Apply basic signal quality filters"""
        confidence = signal_data.get('confidence', 0)
        
        # Minimum confidence filter
        if confidence < MTF_MIN_CONFIDENCE:
            return False, f"Low confidence ({confidence:.1f}% < {MTF_MIN_CONFIDENCE:.1f}%)"
            
        # Additional quality checks can be added here
        # For example: trend consistency, volatility patterns, etc.
        
        return True, "Signal quality acceptable"
        
    def should_skip_symbol(self, symbol, reason):
        """Check if symbol should be skipped due to recent losses or other factors"""
        # This can be enhanced with:
        # - Recent loss tracking per symbol
        # - Volatility pattern analysis
        # - Correlation with recent losses
        # - Market regime detection
        
        # For now, implement basic loss tracking
        positions = mt5.positions_get()
        if positions:
            symbol_positions = [pos for pos in positions if pos.symbol == symbol]
            losing_positions = [pos for pos in symbol_positions if pos.profit < 0]
            
            # If symbol has 3+ losing positions, skip new trades
            if len(losing_positions) >= 3:
                return True, f"Symbol {symbol} has {len(losing_positions)} losing positions"
                
        return False, "Symbol allowed"
        
    def log_signal_decision(self, symbol, signal_data, decision, reason):
        """Log signal filtering decisions"""
        if not ENABLE_ADVANCED_LOGGING or not LOG_ENTRY_REASONS:
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S')
        signal = signal_data.get('signal', 'UNKNOWN')
        confidence = signal_data.get('confidence', 0)
        status = "ACCEPTED" if decision else "REJECTED"
        
        print(f"[{timestamp}] SIGNAL FILTER: {symbol} {signal} ({confidence:.1f}%) - {status} - {reason}")
        
    def get_signal_summary(self, all_signals):
        """Get summary of all current signals"""
        if not all_signals:
            return "No signals available"
            
        summary = f"""
SIGNAL SUMMARY
===============
Total Signals: {len(all_signals)}
Timeframes: {', '.join(set([tf for sig in all_signals.values() for tf in sig.get('timeframes', [])]))}

Signal Breakdown:"""
        
        for symbol, signal_data in all_signals.items():
            signal = signal_data.get('signal', 'UNKNOWN')
            confidence = signal_data.get('confidence', 0)
            timeframes = ', '.join(signal_data.get('timeframes', []))
            summary += f"\n  {symbol}: {signal} ({confidence:.1f}%) [{timeframes}]"
            
        return summary
