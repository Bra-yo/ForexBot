"""
AI-Powered Trading Engine for BrayoForexBot
Integrates machine learning predictions with professional trading execution
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Import existing components
from trading_engine import TradingEngine
from technical_analysis import TechnicalAnalysis
from risk_management import RiskManager
from notifications import NotificationManager

# Import MT5 components
from brokers.mt5_connector import MT5Connector
from brokers.mt5_data_reader import MT5DataReader
from brokers.mt5_order_executor import MT5OrderExecutor, OrderRequest, OrderType
from brokers.mt5_streaming import MT5Streamer

# Import AI components
from ai.feature_engineering import FeatureEngineer
from ai.model_trainer import ModelTrainer
from ai.prediction_engine import TradingPredictor, RealTimePredictor
from ai.evaluation_framework import ModelEvaluator

logger = logging.getLogger(__name__)

@dataclass
class AITradingDecision:
    """AI-powered trading decision"""
    symbol: str
    action: str  # BUY, SELL, WAIT
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    reasons: List[str]
    timestamp: datetime
    model_predictions: Dict
    ai_confidence: float
    ensemble_prediction: float
    market_conditions: Dict

class AITradingEngine(TradingEngine):
    """
    AI-Powered Trading Engine
    Combines machine learning predictions with professional trading execution
    """
    
    def __init__(self, risk_manager: RiskManager = None, 
                 mt5_login: int = None, mt5_password: str = None, 
                 mt5_server: str = None):
        # Initialize parent class
        super().__init__(risk_manager)
        
        # MT5 components
        self.mt5_connector = MT5Connector()
        self.mt5_data_reader = None
        self.mt5_order_executor = None
        self.mt5_streamer = None
        
        # MT5 credentials
        self.mt5_login = mt5_login
        self.mt5_password = mt5_password
        self.mt5_server = mt5_server
        
        # AI components
        self.feature_engineer = FeatureEngineer()
        self.model_trainer = ModelTrainer()
        self.ai_predictor = TradingPredictor()
        self.model_evaluator = ModelEvaluator()
        self.realtime_predictor = None
        
        # AI configuration
        self.ai_enabled = True
        self.ai_confidence_threshold = 0.65
        self.ensemble_weight = 0.7  # Weight for AI vs traditional signals
        self.prediction_cache = {}
        self.model_paths = {}
        
        # Performance tracking
        self.ai_performance = {
            'ai_predictions': 0,
            'ai_correct': 0,
            'hybrid_decisions': 0,
            'ai_only_decisions': 0,
            'traditional_only_decisions': 0
        }
        
    def initialize_ai_system(self, model_paths: Dict[str, str], model_types: Dict[str, str]):
        """
        Initialize AI system with trained models
        
        Args:
            model_paths: Dictionary of model names to file paths
            model_types: Dictionary of model names to types
        """
        try:
            logger.info("Initializing AI trading system...")
            
            # Load trained models
            self.ai_predictor.load_trained_models(model_paths, model_types)
            self.model_paths = model_paths
            
            # Initialize real-time predictor
            self.realtime_predictor = RealTimePredictor(self.ai_predictor)
            
            # Set up prediction callbacks
            self.realtime_predictor.add_prediction_callback(self._on_ai_prediction)
            
            logger.info(f"AI system initialized with {len(self.ai_predictor.models)} models")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing AI system: {e}")
            return False
    
    def initialize_mt5(self) -> bool:
        """Initialize MT5 connection and components"""
        try:
            # Connect to MT5
            success = self.mt5_connector.initialize(
                login=self.mt5_login,
                password=self.mt5_password,
                server=self.mt5_server
            )
            
            if not success:
                logger.error("Failed to initialize MT5 connection")
                return False
            
            # Initialize components
            self.mt5_data_reader = MT5DataReader(self.mt5_connector)
            self.mt5_order_executor = MT5OrderExecutor(self.mt5_connector)
            self.mt5_streamer = MT5Streamer(self.mt5_connector)
            
            # Start order execution thread
            self.mt5_order_executor.start_execution_thread()
            
            logger.info("MT5 components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MT5: {e}")
            return False
    
    def start_ai_trading(self, symbols: List[str], timeframes: List[str] = None):
        """Start AI-powered trading with real-time predictions"""
        try:
            if not self.mt5_connector.connected:
                logger.error("MT5 not connected")
                return False
            
            if not self.ai_enabled or not self.ai_predictor.models:
                logger.warning("AI not enabled or no models loaded")
                return False
            
            if timeframes is None:
                timeframes = ['M1', 'M5', 'M15', 'H1']
            
            # Start MT5 streaming
            self.mt5_streamer.start_streaming(symbols, timeframes)
            
            # Start real-time AI predictions
            self.realtime_predictor.start_real_time_prediction(symbols, update_interval=30)
            
            # Subscribe to data updates
            for symbol in symbols:
                self.mt5_streamer.subscribe_to_ticks(symbol, self._on_tick_update)
                
                for timeframe in timeframes:
                    self.mt5_streamer.subscribe_to_bars(symbol, timeframe, self._on_bar_update)
            
            logger.info(f"Started AI trading for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Error starting AI trading: {e}")
            return False
    
    def analyze_symbol_with_ai(self, symbol: str, timeframe: str = 'M1') -> Optional[AITradingDecision]:
        """
        Analyze a symbol using AI predictions
        
        Args:
            symbol: Currency pair
            timeframe: Analysis timeframe
            
        Returns:
            AI trading decision
        """
        try:
            # Get latest data
            latest_data = self._get_latest_data(symbol, timeframe, bars=200)
            
            if latest_data.empty:
                logger.warning(f"No data available for {symbol}")
                return None
            
            # Get AI predictions
            ai_prediction = self.ai_predictor.predict_direction(latest_data)
            
            # Get traditional signals
            traditional_signals = self.technical_analysis.analyze_signals(latest_data)
            
            # Get market conditions
            market_conditions = self._get_market_conditions(symbol)
            
            # Combine AI and traditional signals
            decision = self._combine_signals(
                symbol, latest_data, ai_prediction, traditional_signals, market_conditions
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with AI: {e}")
            return None
    
    def _combine_signals(self, symbol: str, data: pd.DataFrame, ai_prediction: Dict,
                        traditional_signals: Dict, market_conditions: Dict) -> AITradingDecision:
        """Combine AI and traditional signals"""
        try:
            # Extract AI signal
            ai_signal = ai_prediction['signal']
            ai_confidence = ai_prediction['confidence']
            ensemble_prediction = ai_prediction['ensemble_prediction']
            
            # Extract traditional signal
            traditional_signal = traditional_signals.get('signal', 'WAIT')
            traditional_strength = traditional_signals.get('strength', 0)
            
            # Weighted decision
            if ai_signal != 'WAIT' and ai_confidence >= self.ai_confidence_threshold:
                # AI signal is strong
                final_signal = ai_signal
                final_confidence = ai_confidence * self.ensemble_weight + traditional_strength * (1 - self.ensemble_weight)
                decision_type = 'AI'
            elif traditional_signal != 'WAIT' and traditional_strength >= 60:
                # Traditional signal is strong
                final_signal = traditional_signal
                final_confidence = traditional_strength
                decision_type = 'Traditional'
            else:
                # No strong signals
                final_signal = 'WAIT'
                final_confidence = max(ai_confidence, traditional_strength) * 0.5
                decision_type = 'Weak'
            
            # Get current price
            current_price = data['close'].iloc[-1]
            
            # Calculate position size based on confidence and decision type
            position_size = self._calculate_ai_position_size(symbol, current_price, final_confidence, decision_type)
            
            # Calculate stop loss and take profit
            if final_signal == 'BUY':
                stop_loss = current_price * 0.998  # 20 pips
                take_profit = current_price * 1.002  # 20 pips
            elif final_signal == 'SELL':
                stop_loss = current_price * 1.002  # 20 pips
                take_profit = current_price * 0.998  # 20 pips
            else:
                stop_loss = take_profit = 0
                position_size = 0
            
            # Build reasons
            reasons = []
            if decision_type == 'AI':
                reasons.append(f"AI signal: {ai_signal} (confidence: {ai_confidence:.2f})")
                reasons.extend([f"AI model: {model}" for model in ai_prediction['individual_predictions'].keys()])
            elif decision_type == 'Traditional':
                reasons.append(f"Traditional signal: {traditional_signal} (strength: {traditional_strength:.1f})")
                reasons.extend(traditional_signals.get('reasons', []))
            else:
                reasons.append("Weak signals - waiting for better opportunity")
            
            return AITradingDecision(
                symbol=symbol,
                action=final_signal,
                confidence=final_confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                reasons=reasons,
                timestamp=datetime.now(),
                model_predictions=ai_prediction['individual_predictions'],
                ai_confidence=ai_confidence,
                ensemble_prediction=ensemble_prediction,
                market_conditions=market_conditions
            )
            
        except Exception as e:
            logger.error(f"Error combining signals: {e}")
            return None
    
    def execute_ai_trade(self, decision: AITradingDecision) -> Dict:
        """
        Execute AI-powered trade
        
        Args:
            decision: AI trading decision
            
        Returns:
            Execution result
        """
        try:
            if decision.action == 'WAIT':
                return {'success': True, 'action': 'WAIT', 'reason': 'No AI trading signal'}
            
            # Validate with risk manager
            if self.risk_manager:
                risk_check = self.risk_manager.can_open_position(decision.symbol, decision.action)
                if not risk_check['allowed']:
                    return {
                        'success': False,
                        'action': decision.action,
                        'reason': f'Risk check failed: {risk_check["reasons"]}'
                    }
            
            # Create order request
            order_type = OrderType.BUY if decision.action == 'BUY' else OrderType.SELL
            order_request = OrderRequest(
                symbol=decision.symbol,
                order_type=order_type,
                volume=decision.position_size,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                comment=f"AI-Bot-{decision.confidence:.0f}%"
            )
            
            # Execute order
            result = self.mt5_order_executor.place_market_order(order_request)
            
            # Update AI performance tracking
            self.ai_performance['ai_predictions'] += 1
            if decision.ai_confidence >= self.ai_confidence_threshold:
                self.ai_performance['ai_only_decisions'] += 1
            else:
                self.ai_performance['hybrid_decisions'] += 1
            
            if result['success']:
                # Update risk manager
                if self.risk_manager:
                    exposure = decision.position_size * decision.entry_price
                    self.risk_manager.update_pair_exposure(decision.symbol, exposure)
                
                # Record position
                self._record_ai_position(decision, result)
                
                logger.info(f"AI Trade executed: {decision.action} {decision.symbol} at {decision.entry_price}")
            else:
                logger.error(f"AI Trade failed: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing AI trade: {e}")
            return {'success': False, 'error': str(e)}
    
    def manage_ai_positions(self):
        """Manage positions with AI insights"""
        try:
            # Get open positions
            positions = self.mt5_order_executor.get_open_positions()
            
            for position in positions:
                # Get current price
                current_price_data = self.mt5_streamer.get_latest_tick(position.symbol)
                if current_price_data is None:
                    continue
                
                current_price = current_price_data.bid if position.type == 0 else current_price_data.ask
                
                # Calculate P&L
                if position.type == 0:  # BUY
                    pnl = (current_price - position.price_open) * position.volume
                    should_close = current_price <= position.sl or current_price >= position.tp
                else:  # SELL
                    pnl = (position.price_open - current_price) * position.volume
                    should_close = current_price >= position.sl or current_price <= position.tp
                
                # AI-enhanced decision making
                if should_close:
                    # Get AI prediction for current market
                    latest_data = self._get_latest_data(position.symbol, 'M1', bars=100)
                    if not latest_data.empty:
                        ai_prediction = self.ai_predictor.predict_direction(latest_data)
                        
                        # Consider AI confidence in closing decision
                        if ai_prediction['confidence'] < 0.3:  # Low confidence, be cautious
                            logger.info(f"Low AI confidence ({ai_prediction['confidence']:.2f}), keeping position {position.ticket}")
                            continue
                    
                    close_result = self.mt5_order_executor.close_position(position.ticket)
                    
                    if close_result['success']:
                        # Update risk manager
                        if self.risk_manager:
                            self.risk_manager.update_pair_exposure(position.symbol, -position.volume * position.price_open)
                        
                        # Record in history
                        self._record_ai_close(position, current_price, close_result, ai_prediction)
                        
                        logger.info(f"AI Position closed: {position.symbol} - PnL: {pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error managing AI positions: {e}")
    
    def get_ai_performance_report(self) -> Dict:
        """Get AI performance report"""
        try:
            # Basic AI stats
            ai_stats = self.ai_performance.copy()
            
            if ai_stats['ai_predictions'] > 0:
                ai_stats['ai_accuracy'] = ai_stats['ai_correct'] / ai_stats['ai_predictions']
                ai_stats['ai_decision_ratio'] = ai_stats['ai_only_decisions'] / ai_stats['ai_predictions']
            else:
                ai_stats['ai_accuracy'] = 0.0
                ai_stats['ai_decision_ratio'] = 0.0
            
            # Model performance
            model_stats = self.ai_predictor.get_prediction_statistics()
            
            # Get position summary
            position_summary = self.get_position_summary()
            
            return {
                'ai_performance': ai_stats,
                'model_performance': model_stats,
                'position_summary': position_summary,
                'loaded_models': list(self.ai_predictor.models.keys()),
                'ai_enabled': self.ai_enabled,
                'confidence_threshold': self.ai_confidence_threshold,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting AI performance report: {e}")
            return {}
    
    def _get_latest_data(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        """Get latest data for analysis"""
        try:
            if self.mt5_streamer:
                # Use streaming data if available
                bars_data = self.mt5_streamer.get_bar_history(symbol, timeframe, limit=bars)
                if bars_data:
                    return self._bars_to_dataframe(bars_data)
            
            # Fallback to MT5 data reader
            return self.mt5_data_reader.get_latest_data(symbol, timeframe, bars)
            
        except Exception as e:
            logger.error(f"Error getting latest data: {e}")
            return pd.DataFrame()
    
    def _bars_to_dataframe(self, bars) -> pd.DataFrame:
        """Convert bar data to DataFrame"""
        try:
            data = []
            for bar in bars:
                data.append({
                    'timestamp': bar.time,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Error converting bars to DataFrame: {e}")
            return pd.DataFrame()
    
    def _get_market_conditions(self, symbol: str) -> Dict:
        """Get current market conditions"""
        try:
            if self.mt5_streamer:
                tick = self.mt5_streamer.get_latest_tick(symbol)
                if tick:
                    return {
                        'spread': tick.spread,
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'volume': tick.volume,
                        'time': tick.time
                    }
            
            # Fallback to MT5 connector
            return self.mt5_connector.get_current_price(symbol)
            
        except Exception as e:
            logger.error(f"Error getting market conditions: {e}")
            return {}
    
    def _calculate_ai_position_size(self, symbol: str, price: float, confidence: float, 
                                 decision_type: str) -> float:
        """Calculate position size based on AI confidence"""
        try:
            # Base position size
            base_size = 0.01  # Minimum 0.01 lots
            
            if self.risk_manager:
                risk_amount = self.risk_manager.account_balance * 0.02  # 2% risk
                stop_distance = price * 0.002  # 20 pips
                size = self.mt5_order_executor.calculate_position_size(symbol, risk_amount, stop_distance)
            else:
                size = base_size
            
            # Adjust based on AI confidence and decision type
            if decision_type == 'AI':
                ai_multiplier = 0.5 + (confidence / 100) * 0.5  # 0.5 to 1.0 based on confidence
            else:
                ai_multiplier = 0.7  # Lower multiplier for traditional decisions
            
            adjusted_size = size * ai_multiplier
            
            # Ensure minimum and maximum
            return max(base_size, min(adjusted_size, 1.0))  # Max 1 lot
            
        except Exception as e:
            logger.error(f"Error calculating AI position size: {e}")
            return 0.01
    
    def _on_ai_prediction(self, symbol: str, prediction: Dict):
        """Handle AI prediction updates"""
        try:
            # Cache prediction
            self.prediction_cache[symbol] = {
                'prediction': prediction,
                'timestamp': datetime.now()
            }
            
            # Log significant predictions
            if prediction['signal'] != 'WAIT' and prediction['confidence'] > 0.8:
                logger.info(f"High confidence AI signal: {prediction['signal']} {symbol} ({prediction['confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"Error handling AI prediction: {e}")
    
    def _on_tick_update(self, tick):
        """Handle tick updates"""
        try:
            # Manage positions
            self.manage_ai_positions()
            
        except Exception as e:
            logger.error(f"Error handling tick update: {e}")
    
    def _on_bar_update(self, bar):
        """Handle bar updates"""
        try:
            # Analyze for new AI opportunities
            decision = self.analyze_symbol_with_ai(bar.symbol, bar.timeframe)
            
            if decision and decision.action in ['BUY', 'SELL']:
                # Check if we already have position for this symbol
                if bar.symbol not in self.positions:
                    # Execute AI trade
                    result = self.execute_ai_trade(decision)
                    
                    if result['success']:
                        logger.info(f"AI Trade executed: {decision.action} {bar.symbol}")
                    else:
                        logger.warning(f"AI Trade failed: {result['error']}")
            
        except Exception as e:
            logger.error(f"Error handling bar update: {e}")
    
    def _record_ai_position(self, decision: AITradingDecision, result: Dict):
        """Record AI position"""
        try:
            position = {
                'symbol': decision.symbol,
                'action': decision.action,
                'entry_price': decision.entry_price,
                'stop_loss': decision.stop_loss,
                'take_profit': decision.take_profit,
                'position_size': decision.position_size,
                'order_id': result.get('order'),
                'entry_time': decision.timestamp,
                'status': 'OPEN',
                'unrealized_pnl': 0,
                'realized_pnl': 0,
                'ai_confidence': decision.ai_confidence,
                'ensemble_prediction': decision.ensemble_prediction,
                'decision_type': 'AI' if decision.ai_confidence >= self.ai_confidence_threshold else 'Hybrid',
                'reasons': decision.reasons
            }
            
            self.positions[decision.symbol] = position
            
            # Add to trading history
            self.trading_history.append({
                'type': 'OPEN',
                'position': position.copy(),
                'timestamp': decision.timestamp
            })
            
        except Exception as e:
            logger.error(f"Error recording AI position: {e}")
    
    def _record_ai_close(self, position, exit_price: float, result: Dict, ai_prediction: Dict = None):
        """Record AI position close"""
        try:
            # Calculate P&L
            if position.type == 0:  # BUY
                pnl = (exit_price - position.price_open) * position.volume
            else:  # SELL
                pnl = (position.price_open - exit_price) * position.volume
            
            # Update position
            if position.symbol in self.positions:
                self.positions[position.symbol]['status'] = 'CLOSED'
                self.positions[position.symbol]['exit_price'] = exit_price
                self.positions[position.symbol]['exit_time'] = datetime.now()
                self.positions[position.symbol]['realized_pnl'] = pnl
                
                # Update AI performance
                if pnl > 0:
                    self.ai_performance['ai_correct'] += 1
                
                # Add AI prediction info if available
                if ai_prediction:
                    self.positions[position.symbol]['ai_prediction_at_exit'] = ai_prediction
                
                # Add to trading history
                self.trading_history.append({
                    'type': 'CLOSE',
                    'position': self.positions[position.symbol].copy(),
                    'timestamp': datetime.now()
                })
                
                # Remove from active positions
                del self.positions[position.symbol]
            
        except Exception as e:
            logger.error(f"Error recording AI close: {e}")
    
    def run_ai_trading_loop(self, symbols: List[str], duration_minutes: int = 60):
        """Run AI trading loop"""
        try:
            logger.info(f"Starting AI trading loop for {duration_minutes} minutes")
            
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            while datetime.now() < end_time:
                try:
                    # Check each symbol for AI opportunities
                    for symbol in symbols:
                        decision = self.analyze_symbol_with_ai(symbol)
                        
                        if decision and decision.action in ['BUY', 'SELL']:
                            # Execute AI trade
                            result = self.execute_ai_trade(decision)
                            
                            if result['success']:
                                logger.info(f"AI Trade executed: {decision.action} {symbol}")
                            else:
                                logger.warning(f"AI Trade failed: {result['error']}")
                    
                    # Manage positions
                    self.manage_ai_positions()
                    
                    # Small delay
                    time.sleep(5)
                    
                except KeyboardInterrupt:
                    logger.info("AI trading loop interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error in AI trading loop: {e}")
                    time.sleep(10)
            
            logger.info("AI trading loop completed")
            
        except Exception as e:
            logger.error(f"Error in AI trading loop: {e}")
    
    def update_ai_settings(self, confidence_threshold: float = None, 
                         ensemble_weight: float = None, ai_enabled: bool = None):
        """Update AI settings"""
        try:
            if confidence_threshold is not None:
                self.ai_confidence_threshold = confidence_threshold
                self.ai_predictor.update_confidence_thresholds(buy_threshold=confidence_threshold, 
                                                              sell_threshold=confidence_threshold)
            
            if ensemble_weight is not None:
                self.ensemble_weight = max(0, min(1, ensemble_weight))
            
            if ai_enabled is not None:
                self.ai_enabled = ai_enabled
            
            logger.info(f"AI settings updated: confidence={self.ai_confidence_threshold}, "
                       f"ensemble_weight={self.ensemble_weight}, enabled={self.ai_enabled}")
            
        except Exception as e:
            logger.error(f"Error updating AI settings: {e}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if self.realtime_predictor:
                self.realtime_predictor.stop_real_time_prediction()
            if self.mt5_connector:
                self.mt5_connector.disconnect()
        except:
            pass
