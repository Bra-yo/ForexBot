"""
AI Prediction Engine for BrayoForexBot
Real-time inference and prediction using trained ML models
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import joblib
from typing import Dict, List, Tuple, Optional, Any
import logging
from collections import deque
import threading
import time

# Import AI components
from feature_engineering import FeatureEngineer
from model_trainer import ModelTrainer

logger = logging.getLogger(__name__)

class TradingPredictor:
    """
    Real-time AI prediction engine for trading
    Handles model inference, confidence scoring, and decision making
    """
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.models = {}
        self.ensemble_models = {}
        self.prediction_history = {}
        self.confidence_thresholds = {
            'buy': 0.65,
            'sell': 0.65,
            'hold': 0.5
        }
        
        # Prediction cache
        self.prediction_cache = {}
        self.cache_timeout = 300  # 5 minutes
        
        # Performance tracking
        self.prediction_stats = {
            'total_predictions': 0,
            'correct_predictions': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0
        }
        
        # Model weights for ensemble
        self.model_weights = {}
        
    def load_trained_models(self, model_paths: Dict[str, str], model_types: Dict[str, str]):
        """
        Load pre-trained models
        
        Args:
            model_paths: Dictionary of model names to file paths
            model_types: Dictionary of model names to types ('classification' or 'regression')
        """
        try:
            logger.info("Loading trained models...")
            
            for model_name, filepath in model_paths.items():
                try:
                    # Load model
                    model = joblib.load(filepath)
                    
                    # Load feature config
                    config_path = filepath.replace('.pkl', '_config.json')
                    self.feature_engineer.load_feature_config(config_path)
                    
                    self.models[model_name] = {
                        'model': model,
                        'type': model_types[model_name],
                        'loaded_at': datetime.now()
                    }
                    
                    logger.info(f"Loaded {model_name} ({model_types[model_name]})")
                    
                except Exception as e:
                    logger.error(f"Error loading {model_name}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.models)} models")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def predict_direction(self, data: pd.DataFrame, model_names: List[str] = None) -> Dict:
        """
        Predict price direction using classification models
        
        Args:
            data: OHLCV data
            model_names: List of models to use (None for all)
            
        Returns:
            Prediction dictionary with probabilities and confidence
        """
        try:
            if model_names is None:
                model_names = [name for name, info in self.models.items() if info['type'] == 'classification']
            
            if not model_names:
                logger.warning("No classification models available")
                return self._empty_prediction()
            
            # Create features
            features_df = self.feature_engineer.create_features(data)
            
            if features_df.empty:
                logger.warning("Feature engineering failed")
                return self._empty_prediction()
            
            # Get latest features
            latest_features = features_df.iloc[-1:].copy()
            
            # Scale features
            latest_features = self.feature_engineer.apply_scaling(latest_features, method='standard')
            
            # Collect predictions
            predictions = {}
            confidences = {}
            
            for model_name in model_names:
                if model_name not in self.models:
                    continue
                
                try:
                    model = self.models[model_name]['model']
                    
                    # Get prediction probabilities
                    if hasattr(model, 'predict_proba'):
                        probas = model.predict_proba(latest_features[self.feature_engineer.feature_columns])
                        pred_class = np.argmax(probas[0])
                        confidence = np.max(probas[0])
                    else:
                        pred_class = model.predict(latest_features[self.feature_engineer.feature_columns])[0]
                        confidence = 0.5  # Default confidence
                    
                    predictions[model_name] = pred_class
                    confidences[model_name] = confidence
                    
                except Exception as e:
                    logger.error(f"Error predicting with {model_name}: {e}")
                    continue
            
            if not predictions:
                return self._empty_prediction()
            
            # Ensemble prediction
            ensemble_prediction, ensemble_confidence = self._ensemble_predictions(predictions, confidences)
            
            # Map to trading signals
            signal, signal_confidence = self._map_to_trading_signal(ensemble_prediction, ensemble_confidence)
            
            # Create prediction result
            result = {
                'signal': signal,
                'confidence': signal_confidence,
                'individual_predictions': predictions,
                'individual_confidences': confidences,
                'ensemble_prediction': ensemble_prediction,
                'ensemble_confidence': ensemble_confidence,
                'timestamp': datetime.now(),
                'features_used': len(self.feature_engineer.feature_columns)
            }
            
            # Update statistics
            self.prediction_stats['total_predictions'] += 1
            if signal == 'BUY':
                self.prediction_stats['buy_signals'] += 1
            elif signal == 'SELL':
                self.prediction_stats['sell_signals'] += 1
            else:
                self.prediction_stats['hold_signals'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting direction: {e}")
            return self._empty_prediction()
    
    def predict_return(self, data: pd.DataFrame, model_names: List[str] = None, horizon: int = 1) -> Dict:
        """
        Predict price return using regression models
        
        Args:
            data: OHLCV data
            model_names: List of models to use
            horizon: Prediction horizon
            
        Returns:
            Prediction dictionary with return values
        """
        try:
            if model_names is None:
                model_names = [name for name, info in self.models.items() if info['type'] == 'regression']
            
            if not model_names:
                logger.warning("No regression models available")
                return self._empty_return_prediction()
            
            # Create features
            features_df = self.feature_engineer.create_features(data)
            
            if features_df.empty:
                return self._empty_return_prediction()
            
            # Get latest features
            latest_features = features_df.iloc[-1:].copy()
            
            # Scale features
            latest_features = self.feature_engineer.apply_scaling(latest_features, method='standard')
            
            # Collect predictions
            predictions = {}
            
            for model_name in model_names:
                if model_name not in self.models:
                    continue
                
                try:
                    model = self.models[model_name]['model']
                    pred_return = model.predict(latest_features[self.feature_engineer.feature_columns])[0]
                    predictions[model_name] = pred_return
                    
                except Exception as e:
                    logger.error(f"Error predicting return with {model_name}: {e}")
                    continue
            
            if not predictions:
                return self._empty_return_prediction()
            
            # Ensemble prediction
            ensemble_return = np.mean(list(predictions.values()))
            
            # Calculate confidence based on prediction variance
            prediction_variance = np.var(list(predictions.values()))
            confidence = max(0, 1 - prediction_variance * 100)  # Simple confidence calculation
            
            # Map to trading signal
            signal, signal_confidence = self._map_return_to_signal(ensemble_return, confidence)
            
            result = {
                'signal': signal,
                'confidence': signal_confidence,
                'predicted_return': ensemble_return,
                'individual_returns': predictions,
                'return_variance': prediction_variance,
                'horizon': horizon,
                'timestamp': datetime.now(),
                'features_used': len(self.feature_engineer.feature_columns)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting return: {e}")
            return self._empty_return_prediction()
    
    def predict_multi_horizon(self, data: pd.DataFrame, horizons: List[int] = [1, 5, 10]) -> Dict:
        """
        Predict across multiple time horizons
        
        Args:
            data: OHLCV data
            horizons: List of prediction horizons
            
        Returns:
            Multi-horizon predictions
        """
        try:
            results = {}
            
            for horizon in horizons:
                # Create features with specific target horizon
                features_df = self.feature_engineer.create_features(data, target_horizon=horizon)
                
                if features_df.empty:
                    continue
                
                # Get latest features
                latest_features = features_df.iloc[-1:].copy()
                latest_features = self.feature_engineer.apply_scaling(latest_features, method='standard')
                
                # Get classification models
                classification_models = [name for name, info in self.models.items() if info['type'] == 'classification']
                
                if classification_models:
                    direction_result = self.predict_direction(data, classification_models)
                    results[f'horizon_{horizon}'] = {
                        'direction': direction_result['signal'],
                        'direction_confidence': direction_result['confidence'],
                        'horizon': horizon
                    }
                
                # Get regression models
                regression_models = [name for name, info in self.models.items() if info['type'] == 'regression']
                
                if regression_models:
                    return_result = self.predict_return(data, regression_models, horizon)
                    results[f'horizon_{horizon}'].update({
                        'predicted_return': return_result['predicted_return'],
                        'return_confidence': return_result['confidence']
                    })
            
            # Aggregate signals
            consensus_signal = self._aggregate_multi_horizon_signals(results)
            
            return {
                'multi_horizon': results,
                'consensus_signal': consensus_signal,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error in multi-horizon prediction: {e}")
            return {}
    
    def predict_with_confidence_bands(self, data: pd.DataFrame, confidence_level: float = 0.95) -> Dict:
        """
        Predict with confidence bands using ensemble methods
        
        Args:
            data: OHLCV data
            confidence_level: Confidence level for bands
            
        Returns:
            Prediction with confidence intervals
        """
        try:
            # Get base prediction
            prediction = self.predict_direction(data)
            
            if prediction['signal'] == 'WAIT':
                return prediction
            
            # Calculate confidence bands using model variance
            individual_preds = list(prediction['individual_predictions'].values())
            individual_confidences = list(prediction['individual_confidences'].values())
            
            # Calculate statistics
            mean_prediction = np.mean(individual_preds)
            std_prediction = np.std(individual_preds)
            
            # Calculate confidence bands
            z_score = 1.96 if confidence_level == 0.95 else 1.645  # 90% confidence
            
            lower_bound = mean_prediction - z_score * std_prediction
            upper_bound = mean_prediction + z_score * std_prediction
            
            # Adjust confidence based on band width
            band_width = upper_bound - lower_bound
            adjusted_confidence = prediction['confidence'] * (1 - band_width / 2)
            adjusted_confidence = max(0, min(1, adjusted_confidence))
            
            result = prediction.copy()
            result.update({
                'confidence_lower': lower_bound,
                'confidence_upper': upper_bound,
                'band_width': band_width,
                'adjusted_confidence': adjusted_confidence,
                'confidence_level': confidence_level
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in confidence band prediction: {e}")
            return self._empty_prediction()
    
    def _ensemble_predictions(self, predictions: Dict, confidences: Dict) -> Tuple[int, float]:
        """Ensemble predictions with confidence weighting"""
        try:
            if not predictions:
                return 1, 0.5  # Default to hold
            
            # Weight predictions by confidence
            weighted_votes = {}
            total_weight = 0
            
            for model_name, pred_class in predictions.items():
                weight = confidences.get(model_name, 0.5)
                weighted_votes[pred_class] = weighted_votes.get(pred_class, 0) + weight
                total_weight += weight
            
            # Find class with highest weighted vote
            best_class = max(weighted_votes.keys(), key=lambda k: weighted_votes[k])
            best_confidence = weighted_votes[best_class] / total_weight if total_weight > 0 else 0.5
            
            return best_class, best_confidence
            
        except Exception as e:
            logger.error(f"Error in ensemble prediction: {e}")
            return 1, 0.5
    
    def _map_to_trading_signal(self, prediction: int, confidence: float) -> Tuple[str, float]:
        """Map ML prediction to trading signal"""
        try:
            if prediction == 2:  # Strong buy
                if confidence >= self.confidence_thresholds['buy']:
                    return 'BUY', confidence
                else:
                    return 'WAIT', confidence
            elif prediction == 1:  # Neutral/hold
                return 'WAIT', confidence
            elif prediction == 0:  # Strong sell
                if confidence >= self.confidence_thresholds['sell']:
                    return 'SELL', confidence
                else:
                    return 'WAIT', confidence
            else:
                return 'WAIT', 0.5
                
        except Exception as e:
            logger.error(f"Error mapping to trading signal: {e}")
            return 'WAIT', 0.5
    
    def _map_return_to_signal(self, predicted_return: float, confidence: float) -> Tuple[str, float]:
        """Map predicted return to trading signal"""
        try:
            # Define thresholds
            buy_threshold = 0.001  # 0.1% return
            sell_threshold = -0.001  # -0.1% return
            
            if predicted_return > buy_threshold and confidence >= self.confidence_thresholds['buy']:
                return 'BUY', confidence
            elif predicted_return < sell_threshold and confidence >= self.confidence_thresholds['sell']:
                return 'SELL', confidence
            else:
                return 'WAIT', confidence
                
        except Exception as e:
            logger.error(f"Error mapping return to signal: {e}")
            return 'WAIT', 0.5
    
    def _aggregate_multi_horizon_signals(self, multi_horizon_results: Dict) -> Dict:
        """Aggregate signals across multiple horizons"""
        try:
            if not multi_horizon_results:
                return {'signal': 'WAIT', 'confidence': 0.5}
            
            signals = []
            confidences = []
            weights = []
            
            for horizon_key, result in multi_horizon_results.items():
                signals.append(result.get('direction', 'WAIT'))
                confidences.append(result.get('direction_confidence', 0.5))
                # Weight shorter horizons more heavily
                horizon = result.get('horizon', 1)
                weight = 1.0 / horizon
                weights.append(weight)
            
            # Weighted voting
            signal_counts = {'BUY': 0, 'SELL': 0, 'WAIT': 0}
            total_weight = 0
            
            for signal, confidence, weight in zip(signals, confidences, weights):
                signal_counts[signal] += confidence * weight
                total_weight += weight
            
            # Find best signal
            best_signal = max(signal_counts.keys(), key=lambda k: signal_counts[k])
            best_confidence = signal_counts[best_signal] / total_weight if total_weight > 0 else 0.5
            
            return {
                'signal': best_signal,
                'confidence': best_confidence,
                'signal_distribution': signal_counts
            }
            
        except Exception as e:
            logger.error(f"Error aggregating multi-horizon signals: {e}")
            return {'signal': 'WAIT', 'confidence': 0.5}
    
    def _empty_prediction(self) -> Dict:
        """Return empty prediction"""
        return {
            'signal': 'WAIT',
            'confidence': 0.0,
            'individual_predictions': {},
            'individual_confidences': {},
            'ensemble_prediction': 1,
            'ensemble_confidence': 0.5,
            'timestamp': datetime.now(),
            'features_used': 0
        }
    
    def _empty_return_prediction(self) -> Dict:
        """Return empty return prediction"""
        return {
            'signal': 'WAIT',
            'confidence': 0.0,
            'predicted_return': 0.0,
            'individual_returns': {},
            'return_variance': 0.0,
            'horizon': 1,
            'timestamp': datetime.now(),
            'features_used': 0
        }
    
    def update_confidence_thresholds(self, buy_threshold: float = None, sell_threshold: float = None, hold_threshold: float = None):
        """Update confidence thresholds"""
        try:
            if buy_threshold is not None:
                self.confidence_thresholds['buy'] = buy_threshold
            if sell_threshold is not None:
                self.confidence_thresholds['sell'] = sell_threshold
            if hold_threshold is not None:
                self.confidence_thresholds['hold'] = hold_threshold
                
            logger.info(f"Updated confidence thresholds: {self.confidence_thresholds}")
            
        except Exception as e:
            logger.error(f"Error updating confidence thresholds: {e}")
    
    def get_prediction_statistics(self) -> Dict:
        """Get prediction performance statistics"""
        try:
            stats = self.prediction_stats.copy()
            
            # Calculate accuracy if we have tracked results
            if stats['total_predictions'] > 0:
                stats['accuracy'] = stats['correct_predictions'] / stats['total_predictions']
                stats['buy_signal_ratio'] = stats['buy_signals'] / stats['total_predictions']
                stats['sell_signal_ratio'] = stats['sell_signals'] / stats['total_predictions']
                stats['hold_signal_ratio'] = stats['hold_signals'] / stats['total_predictions']
            else:
                stats['accuracy'] = 0.0
                stats['buy_signal_ratio'] = 0.0
                stats['sell_signal_ratio'] = 0.0
                stats['hold_signal_ratio'] = 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting prediction statistics: {e}")
            return {}
    
    def record_prediction_result(self, prediction: Dict, actual_result: str):
        """Record actual result for performance tracking"""
        try:
            # Update statistics
            self.prediction_stats['total_predictions'] += 1
            
            if prediction['signal'] == actual_result:
                self.prediction_stats['correct_predictions'] += 1
            
            # Store in history
            timestamp = prediction['timestamp']
            if timestamp not in self.prediction_history:
                self.prediction_history[timestamp] = []
            
            self.prediction_history[timestamp].append({
                'predicted': prediction['signal'],
                'actual': actual_result,
                'confidence': prediction['confidence']
            })
            
            # Keep only recent history
            if len(self.prediction_history) > 1000:
                oldest_key = min(self.prediction_history.keys())
                del self.prediction_history[oldest_key]
            
        except Exception as e:
            logger.error(f"Error recording prediction result: {e}")
    
    def get_model_explainability(self, data: pd.DataFrame, model_name: str) -> Dict:
        """
        Get model explainability information
        
        Args:
            data: OHLCV data
            model_name: Model to explain
            
        Returns:
            Explainability information
        """
        try:
            if model_name not in self.models:
                return {'error': f'Model {model_name} not found'}
            
            # Create features
            features_df = self.feature_engineer.create_features(data)
            
            if features_df.empty:
                return {'error': 'Feature engineering failed'}
            
            # Get latest features
            latest_features = features_df.iloc[-1:].copy()
            latest_features = self.feature_engineer.apply_scaling(latest_features, method='standard')
            
            # Get feature importance
            model = self.models[model_name]['model']
            
            if hasattr(model, 'feature_importances_'):
                importance = pd.Series(
                    model.feature_importances_, 
                    index=self.feature_engineer.feature_columns
                ).sort_values(ascending=False)
                
                return {
                    'model_type': self.models[model_name]['type'],
                    'top_features': importance.head(10).to_dict(),
                    'feature_importance': importance.to_dict()
                }
            else:
                return {'error': 'Model does not support feature importance'}
                
        except Exception as e:
            logger.error(f"Error getting model explainability: {e}")
            return {'error': str(e)}
    
    def save_prediction_engine(self, filepath: str):
        """Save prediction engine state"""
        try:
            state = {
                'models': self.models,
                'confidence_thresholds': self.confidence_thresholds,
                'prediction_stats': self.prediction_stats,
                'feature_engineer': self.feature_engineer
            }
            
            joblib.dump(state, filepath)
            logger.info(f"Prediction engine saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving prediction engine: {e}")
    
    def load_prediction_engine(self, filepath: str):
        """Load prediction engine state"""
        try:
            state = joblib.load(filepath)
            
            self.models = state['models']
            self.confidence_thresholds = state['confidence_thresholds']
            self.prediction_stats = state['prediction_stats']
            self.feature_engineer = state['feature_engineer']
            
            logger.info(f"Prediction engine loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading prediction engine: {e}")


class RealTimePredictor:
    """
    Real-time prediction system with streaming capabilities
    """
    
    def __init__(self, trading_predictor: TradingPredictor):
        self.predictor = trading_predictor
        self.prediction_queue = {}
        self.last_predictions = {}
        self.update_callbacks = []
        self.running = False
        self.prediction_thread = None
        
    def start_real_time_prediction(self, symbols: List[str], update_interval: int = 60):
        """Start real-time prediction for symbols"""
        try:
            self.running = True
            self.prediction_thread = threading.Thread(
                target=self._prediction_loop,
                args=(symbols, update_interval),
                daemon=True
            )
            self.prediction_thread.start()
            
            logger.info(f"Started real-time prediction for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error starting real-time prediction: {e}")
    
    def stop_real_time_prediction(self):
        """Stop real-time prediction"""
        try:
            self.running = False
            if self.prediction_thread:
                self.prediction_thread.join(timeout=5)
            
            logger.info("Stopped real-time prediction")
            
        except Exception as e:
            logger.error(f"Error stopping real-time prediction: {e}")
    
    def _prediction_loop(self, symbols: List[str], update_interval: int):
        """Main prediction loop"""
        while self.running:
            try:
                for symbol in symbols:
                    # Get latest data (this would need to be connected to data source)
                    # For now, we'll simulate with placeholder
                    prediction = self.predictor.predict_direction(pd.DataFrame())  # Placeholder
                    
                    if prediction['signal'] != 'WAIT':
                        # Store prediction
                        self.last_predictions[symbol] = prediction
                        
                        # Notify callbacks
                        for callback in self.update_callbacks:
                            try:
                                callback(symbol, prediction)
                            except Exception as e:
                                logger.error(f"Error in prediction callback: {e}")
                
                time.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
                time.sleep(update_interval)
    
    def add_prediction_callback(self, callback):
        """Add callback for new predictions"""
        self.update_callbacks.append(callback)
    
    def get_latest_prediction(self, symbol: str) -> Optional[Dict]:
        """Get latest prediction for symbol"""
        return self.last_predictions.get(symbol)
