"""
Model Evaluation and Validation Framework for BrayoForexBot
Comprehensive evaluation of ML models for trading applications
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional, Any
import logging
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score, precision_score, 
    recall_score, f1_score, roc_auc_score, precision_recall_curve, roc_curve
)
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score, mean_absolute_percentage_error
)
import shap
import joblib

logger = logging.getLogger(__name__)

class ModelEvaluator:
    """
    Comprehensive model evaluation framework
    Evaluates ML models specifically for trading applications
    """
    
    def __init__(self):
        self.evaluation_results = {}
        self.backtest_results = {}
        self.comparison_results = {}
        
    def evaluate_classification_model(self, model, X_test: pd.DataFrame, y_test: pd.Series, 
                                   model_name: str = "model") -> Dict:
        """
        Comprehensive evaluation of classification model
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test targets
            model_name: Model name for reporting
            
        Returns:
            Comprehensive evaluation results
        """
        try:
            logger.info(f"Evaluating classification model: {model_name}")
            
            # Get predictions
            y_pred = model.predict(X_test)
            y_pred_proba = None
            
            if hasattr(model, 'predict_proba'):
                y_pred_proba = model.predict_proba(X_test)
            
            # Basic metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted')
            recall = recall_score(y_test, y_pred, average='weighted')
            f1 = f1_score(y_test, y_pred, average='weighted')
            
            # Detailed classification report
            class_report = classification_report(y_test, y_pred, output_dict=True)
            
            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            
            # ROC AUC (if binary classification)
            roc_auc = None
            if len(np.unique(y_test)) == 2 and y_pred_proba is not None:
                roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
            
            # Trading-specific metrics
            trading_metrics = self._calculate_trading_metrics(y_test, y_pred, y_pred_proba)
            
            results = {
                'model_name': model_name,
                'model_type': 'classification',
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'roc_auc': roc_auc,
                'classification_report': class_report,
                'confusion_matrix': cm,
                'trading_metrics': trading_metrics,
                'evaluation_date': datetime.now()
            }
            
            self.evaluation_results[model_name] = results
            
            logger.info(f"{model_name} - Accuracy: {accuracy:.3f}, F1: {f1:.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error evaluating classification model: {e}")
            return {}
    
    def evaluate_regression_model(self, model, X_test: pd.DataFrame, y_test: pd.Series, 
                               model_name: str = "model") -> Dict:
        """
        Comprehensive evaluation of regression model
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test targets
            model_name: Model name for reporting
            
        Returns:
            Comprehensive evaluation results
        """
        try:
            logger.info(f"Evaluating regression model: {model_name}")
            
            # Get predictions
            y_pred = model.predict(X_test)
            
            # Basic regression metrics
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            mape = mean_absolute_percentage_error(y_test, y_pred)
            
            # Trading-specific metrics
            trading_metrics = self._calculate_regression_trading_metrics(y_test, y_pred)
            
            results = {
                'model_name': model_name,
                'model_type': 'regression',
                'mse': mse,
                'mae': mae,
                'rmse': rmse,
                'r2_score': r2,
                'mape': mape,
                'trading_metrics': trading_metrics,
                'evaluation_date': datetime.now()
            }
            
            self.evaluation_results[model_name] = results
            
            logger.info(f"{model_name} - R2: {r2:.3f}, RMSE: {rmse:.6f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error evaluating regression model: {e}")
            return {}
    
    def _calculate_trading_metrics(self, y_true: pd.Series, y_pred: np.ndarray, 
                                 y_pred_proba: np.ndarray = None) -> Dict:
        """Calculate trading-specific metrics"""
        try:
            metrics = {}
            
            # Signal accuracy
            if len(np.unique(y_true)) == 3:  # Multi-class (BUY/HOLD/SELL)
                # Convert to signals
                true_signals = y_true.values
                pred_signals = y_pred
                
                # Calculate directional accuracy
                buy_correct = np.sum((true_signals == 2) & (pred_signals == 2))
                sell_correct = np.sum((true_signals == 0) & (pred_signals == 0))
                total_trading_signals = np.sum((true_signals == 2) | (true_signals == 0))
                
                if total_trading_signals > 0:
                    metrics['trading_accuracy'] = (buy_correct + sell_correct) / total_trading_signals
                    metrics['buy_accuracy'] = buy_correct / max(1, np.sum(true_signals == 2))
                    metrics['sell_accuracy'] = sell_correct / max(1, np.sum(true_signals == 0))
                else:
                    metrics['trading_accuracy'] = 0.0
                    metrics['buy_accuracy'] = 0.0
                    metrics['sell_accuracy'] = 0.0
                
                # Signal distribution
                metrics['buy_signal_ratio'] = np.sum(pred_signals == 2) / len(pred_signals)
                metrics['sell_signal_ratio'] = np.sum(pred_signals == 0) / len(pred_signals)
                metrics['hold_signal_ratio'] = np.sum(pred_signals == 1) / len(pred_signals)
                
            # Profit-based metrics (if we have actual returns)
            if y_pred_proba is not None and len(np.unique(y_true)) == 3:
                # Calculate expected profit based on prediction confidence
                confidence = np.max(y_pred_proba, axis=1)
                high_confidence_mask = confidence > 0.7
                
                if np.sum(high_confidence_mask) > 0:
                    high_conf_returns = []
                    for i in range(len(y_true)):
                        if high_confidence_mask[i]:
                            if y_pred[i] == 2 and y_true.iloc[i] == 2:  # Correct buy
                                high_conf_returns.append(0.01)  # 1% profit
                            elif y_pred[i] == 0 and y_true.iloc[i] == 0:  # Correct sell
                                high_conf_returns.append(0.01)  # 1% profit
                            elif y_pred[i] == 2 and y_true.iloc[i] != 2:  # Wrong buy
                                high_conf_returns.append(-0.005)  # 0.5% loss
                            elif y_pred[i] == 0 and y_true.iloc[i] != 0:  # Wrong sell
                                high_conf_returns.append(-0.005)  # 0.5% loss
                    
                    if high_conf_returns:
                        metrics['high_confidence_expected_return'] = np.mean(high_conf_returns)
                        metrics['high_confidence_win_rate'] = np.mean(np.array(high_conf_returns) > 0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating trading metrics: {e}")
            return {}
    
    def _calculate_regression_trading_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict:
        """Calculate trading-specific metrics for regression"""
        try:
            metrics = {}
            
            # Directional accuracy
            true_direction = np.sign(y_true.values)
            pred_direction = np.sign(y_pred)
            
            # Remove zeros (neutral positions)
            non_zero_mask = (true_direction != 0) & (pred_direction != 0)
            
            if np.sum(non_zero_mask) > 0:
                directional_accuracy = np.mean(true_direction[non_zero_mask] == pred_direction[non_zero_mask])
                metrics['directional_accuracy'] = directional_accuracy
            else:
                metrics['directional_accuracy'] = 0.0
            
            # Return prediction accuracy
            return_threshold = 0.001  # 0.1% return threshold
            
            actual_returns = y_true.values
            predicted_returns = y_pred
            
            # Calculate if predicted direction was correct
            correct_direction = (actual_returns * predicted_returns) > 0
            
            # Only count significant predictions
            significant_predictions = np.abs(predicted_returns) > return_threshold
            
            if np.sum(significant_predictions) > 0:
                metrics['significant_prediction_accuracy'] = np.mean(correct_direction[significant_predictions])
            else:
                metrics['significant_prediction_accuracy'] = 0.0
            
            # Expected value calculation
            win_rate = np.mean(correct_direction)
            avg_win = np.mean(actual_returns[correct_direction & (actual_returns > 0)]) if np.any(correct_direction & (actual_returns > 0)) else 0
            avg_loss = np.mean(np.abs(actual_returns[~correct_direction & (actual_returns < 0)])) if np.any(~correct_direction & (actual_returns < 0)) else 0
            
            if avg_loss > 0:
                metrics['expected_value'] = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
                metrics['profit_factor'] = (win_rate * avg_win) / ((1 - win_rate) * avg_loss)
            else:
                metrics['expected_value'] = 0.0
                metrics['profit_factor'] = 0.0
            
            # Signal quality metrics
            metrics['signal_frequency'] = np.mean(np.abs(predicted_returns) > return_threshold)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating regression trading metrics: {e}")
            return {}
    
    def compare_models(self, model_results: Dict[str, Dict]) -> Dict:
        """
        Compare multiple models
        
        Args:
            model_results: Dictionary of model evaluation results
            
        Returns:
            Comparison results
        """
        try:
            logger.info("Comparing models...")
            
            comparison = {
                'model_rankings': {},
                'metric_comparison': {},
                'best_models': {},
                'comparison_date': datetime.now()
            }
            
            # Separate classification and regression models
            classification_models = {}
            regression_models = {}
            
            for model_name, results in model_results.items():
                if results.get('model_type') == 'classification':
                    classification_models[model_name] = results
                elif results.get('model_type') == 'regression':
                    regression_models[model_name] = results
            
            # Compare classification models
            if classification_models:
                class_comparison = self._compare_classification_models(classification_models)
                comparison.update(class_comparison)
            
            # Compare regression models
            if regression_models:
                reg_comparison = self._compare_regression_models(regression_models)
                comparison.update(reg_comparison)
            
            self.comparison_results = comparison
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing models: {e}")
            return {}
    
    def _compare_classification_models(self, models: Dict) -> Dict:
        """Compare classification models"""
        try:
            metrics = ['accuracy', 'precision', 'recall', 'f1_score']
            
            # Create comparison DataFrame
            comparison_data = {}
            for model_name, results in models.items():
                comparison_data[model_name] = {metric: results.get(metric, 0) for metric in metrics}
                
                # Add trading metrics
                trading_metrics = results.get('trading_metrics', {})
                comparison_data[model_name].update({
                    'trading_accuracy': trading_metrics.get('trading_accuracy', 0),
                    'buy_accuracy': trading_metrics.get('buy_accuracy', 0),
                    'sell_accuracy': trading_metrics.get('sell_accuracy', 0)
                })
            
            comparison_df = pd.DataFrame(comparison_data).T
            
            # Rank models by different metrics
            rankings = {}
            for metric in comparison_df.columns:
                rankings[metric] = comparison_df[metric].rank(ascending=False).to_dict()
            
            # Overall ranking (average rank)
            overall_ranking = {}
            for model in comparison_df.index:
                ranks = [rankings[metric][model] for metric in comparison_df.columns]
                overall_ranking[model] = np.mean(ranks)
            
            # Sort by overall ranking
            sorted_overall = sorted(overall_ranking.items(), key=lambda x: x[1])
            
            return {
                'classification_comparison': comparison_df.to_dict(),
                'classification_rankings': rankings,
                'classification_overall_ranking': dict(sorted_overall),
                'best_classification_model': sorted_overall[0][0] if sorted_overall else None
            }
            
        except Exception as e:
            logger.error(f"Error comparing classification models: {e}")
            return {}
    
    def _compare_regression_models(self, models: Dict) -> Dict:
        """Compare regression models"""
        try:
            metrics = ['r2_score', 'rmse', 'mae', 'mape']
            
            # Create comparison DataFrame
            comparison_data = {}
            for model_name, results in models.items():
                comparison_data[model_name] = {metric: results.get(metric, 0) for metric in metrics}
                
                # Add trading metrics
                trading_metrics = results.get('trading_metrics', {})
                comparison_data[model_name].update({
                    'directional_accuracy': trading_metrics.get('directional_accuracy', 0),
                    'expected_value': trading_metrics.get('expected_value', 0),
                    'profit_factor': trading_metrics.get('profit_factor', 0)
                })
            
            comparison_df = pd.DataFrame(comparison_data).T
            
            # For RMSE and MAE, lower is better (invert ranking)
            rankings = {}
            for metric in comparison_df.columns:
                if metric in ['rmse', 'mae', 'mape']:
                    rankings[metric] = comparison_df[metric].rank(ascending=True).to_dict()
                else:
                    rankings[metric] = comparison_df[metric].rank(ascending=False).to_dict()
            
            # Overall ranking (average rank)
            overall_ranking = {}
            for model in comparison_df.index:
                ranks = [rankings[metric][model] for metric in comparison_df.columns]
                overall_ranking[model] = np.mean(ranks)
            
            # Sort by overall ranking
            sorted_overall = sorted(overall_ranking.items(), key=lambda x: x[1])
            
            return {
                'regression_comparison': comparison_df.to_dict(),
                'regression_rankings': rankings,
                'regression_overall_ranking': dict(sorted_overall),
                'best_regression_model': sorted_overall[0][0] if sorted_overall else None
            }
            
        except Exception as e:
            logger.error(f"Error comparing regression models: {e}")
            return {}
    
    def backtest_predictions(self, predictions: pd.Series, actual_returns: pd.Series, 
                           transaction_costs: float = 0.0002) -> Dict:
        """
        Backtest model predictions
        
        Args:
            predictions: Model predictions (BUY/SELL/HOLD or returns)
            actual_returns: Actual returns
            transaction_costs: Transaction cost per trade
            
        Returns:
            Backtest results
        """
        try:
            logger.info("Backtesting predictions...")
            
            # Convert predictions to trading signals
            if predictions.dtype == 'object':
                # Classification predictions
                signals = predictions.map({'BUY': 1, 'SELL': -1, 'WAIT': 0})
            else:
                # Regression predictions
                signals = np.sign(predictions)
                signals[np.abs(signals) < 0.001] = 0  # Neutral zone
            
            # Calculate returns
            trading_returns = []
            positions = []
            
            for i in range(len(signals)):
                if i == 0:
                    positions.append(0)
                    trading_returns.append(0)
                    continue
                
                signal = signals.iloc[i]
                prev_position = positions[-1]
                
                # Apply transaction costs for position changes
                if signal != prev_position:
                    if prev_position != 0:  # Close previous position
                        trading_returns.append(actual_returns.iloc[i] - transaction_costs)
                    else:
                        trading_returns.append(0)  # Transaction cost for opening
                    
                    positions.append(signal)
                else:
                    # Hold position
                    if prev_position != 0:
                        trading_returns.append(actual_returns.iloc[i] * prev_position)
                    else:
                        trading_returns.append(0)
                    
                    positions.append(prev_position)
            
            # Calculate performance metrics
            total_return = np.sum(trading_returns)
            cumulative_returns = np.cumprod(1 + np.array(trading_returns)) - 1
            
            # Calculate drawdown
            peak = np.maximum.accumulate(cumulative_returns)
            drawdown = cumulative_returns - peak
            max_drawdown = np.min(drawdown)
            
            # Calculate Sharpe ratio
            excess_returns = np.array(trading_returns) - 0.02/252  # Risk-free rate
            sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0
            
            # Calculate win rate
            trades = [ret for ret, pos in zip(trading_returns, positions) if pos != 0]
            winning_trades = [ret for ret in trades if ret > 0]
            win_rate = len(winning_trades) / len(trades) if trades else 0
            
            results = {
                'total_return': total_return,
                'cumulative_return': cumulative_returns[-1] if len(cumulative_returns) > 0 else 0,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'win_rate': win_rate,
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'trading_returns': trading_returns,
                'cumulative_returns': cumulative_returns,
                'positions': positions,
                'backtest_date': datetime.now()
            }
            
            self.backtest_results['default'] = results
            
            logger.info(f"Backtest - Total Return: {total_return:.3f}, Sharpe: {sharpe_ratio:.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error backtesting predictions: {e}")
            return {}
    
    def generate_evaluation_report(self, model_name: str = None) -> str:
        """
        Generate comprehensive evaluation report
        
        Args:
            model_name: Specific model to report on (None for all)
            
        Returns:
            Evaluation report text
        """
        try:
            if model_name and model_name in self.evaluation_results:
                return self._generate_single_model_report(model_name)
            else:
                return self._generate_comprehensive_report()
                
        except Exception as e:
            logger.error(f"Error generating evaluation report: {e}")
            return f"Error generating report: {str(e)}"
    
    def _generate_single_model_report(self, model_name: str) -> str:
        """Generate report for single model"""
        try:
            results = self.evaluation_results[model_name]
            
            report = f"""
# 📊 MODEL EVALUATION REPORT: {model_name.upper()}

## 📈 BASIC METRICS
"""
            
            if results['model_type'] == 'classification':
                report += f"""
- **Accuracy**: {results['accuracy']:.3f}
- **Precision**: {results['precision']:.3f}
- **Recall**: {results['recall']:.3f}
- **F1 Score**: {results['f1_score']:.3f}
- **ROC AUC**: {results.get('roc_auc', 'N/A')}

## 📊 TRADING METRICS
"""
                trading_metrics = results.get('trading_metrics', {})
                report += f"""
- **Trading Accuracy**: {trading_metrics.get('trading_accuracy', 0):.3f}
- **Buy Accuracy**: {trading_metrics.get('buy_accuracy', 0):.3f}
- **Sell Accuracy**: {trading_metrics.get('sell_accuracy', 0):.3f}
- **Buy Signal Ratio**: {trading_metrics.get('buy_signal_ratio', 0):.3f}
- **Sell Signal Ratio**: {trading_metrics.get('sell_signal_ratio', 0):.3f}
"""
                
            else:  # Regression
                report += f"""
- **R² Score**: {results['r2_score']:.3f}
- **RMSE**: {results['rmse']:.6f}
- **MAE**: {results['mae']:.6f}
- **MAPE**: {results.get('mape', 0):.3f}

## 📊 TRADING METRICS
"""
                trading_metrics = results.get('trading_metrics', {})
                report += f"""
- **Directional Accuracy**: {trading_metrics.get('directional_accuracy', 0):.3f}
- **Expected Value**: {trading_metrics.get('expected_value', 0):.6f}
- **Profit Factor**: {trading_metrics.get('profit_factor', 0):.3f}
- **Signal Frequency**: {trading_metrics.get('signal_frequency', 0):.3f}
"""
            
            report += f"""
## 📅 EVALUATION DATE
{results['evaluation_date']}

## 📋 CLASSIFICATION REPORT
{results.get('classification_report', 'N/A')}

---
*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating single model report: {e}")
            return f"Error generating report: {str(e)}"
    
    def _generate_comprehensive_report(self) -> str:
        """Generate comprehensive report for all models"""
        try:
            report = """
# 📊 COMPREHENSIVE MODEL EVALUATION REPORT

## 📈 MODEL COMPARISON
"""
            
            if self.comparison_results:
                if 'best_classification_model' in self.comparison_results:
                    report += f"""
### 🏆 Best Classification Model: {self.comparison_results['best_classification_model']}

### 🏆 Best Regression Model: {self.comparison_results.get('best_regression_model', 'N/A')}
"""
            
            report += f"""
## 📊 INDIVIDUAL MODEL RESULTS

"""
            
            for model_name, results in self.evaluation_results.items():
                report += f"### {model_name.upper()}\n"
                
                if results['model_type'] == 'classification':
                    report += f"- Accuracy: {results['accuracy']:.3f}\n"
                    report += f"- F1 Score: {results['f1_score']:.3f}\n"
                else:
                    report += f"- R² Score: {results['r2_score']:.3f}\n"
                    report += f"- RMSE: {results['rmse']:.6f}\n"
                
                report += "\n"
            
            report += f"""
## 📅 REPORT GENERATED
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
*Comprehensive evaluation report generated by BrayoForexBot AI Evaluation Framework*
"""
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return f"Error generating report: {str(e)}"
    
    def plot_evaluation_results(self, model_name: str = None, save_path: str = None):
        """
        Plot evaluation results
        
        Args:
            model_name: Specific model to plot (None for comparison)
            save_path: Path to save plot
        """
        try:
            if model_name and model_name in self.evaluation_results:
                self._plot_single_model_results(model_name, save_path)
            else:
                self._plot_model_comparison(save_path)
                
        except Exception as e:
            logger.error(f"Error plotting evaluation results: {e}")
    
    def _plot_single_model_results(self, model_name: str, save_path: str = None):
        """Plot results for single model"""
        try:
            results = self.evaluation_results[model_name]
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Model Evaluation: {model_name}', fontsize=16)
            
            if results['model_type'] == 'classification':
                # Confusion Matrix
                cm = results['confusion_matrix']
                sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0, 0])
                axes[0, 0].set_title('Confusion Matrix')
                
                # Metrics Bar Chart
                metrics = ['accuracy', 'precision', 'recall', 'f1_score']
                values = [results[metric] for metric in metrics]
                axes[0, 1].bar(metrics, values)
                axes[0, 1].set_title('Performance Metrics')
                axes[0, 1].set_ylabel('Score')
                
                # Trading Metrics
                trading_metrics = results.get('trading_metrics', {})
                if trading_metrics:
                    trading_keys = ['trading_accuracy', 'buy_accuracy', 'sell_accuracy']
                    trading_values = [trading_metrics.get(key, 0) for key in trading_keys]
                    axes[1, 0].bar(trading_keys, trading_values)
                    axes[1, 0].set_title('Trading Accuracy')
                    axes[1, 0].set_ylabel('Accuracy')
                
                # Signal Distribution
                signal_keys = ['buy_signal_ratio', 'sell_signal_ratio', 'hold_signal_ratio']
                signal_values = [trading_metrics.get(key, 0) for key in signal_keys]
                axes[1, 1].pie(signal_values, labels=['Buy', 'Sell', 'Hold'], autopct='%1.1f%%')
                axes[1, 1].set_title('Signal Distribution')
            
            else:  # Regression
                # Predictions vs Actual
                # This would need actual predictions - placeholder
                axes[0, 0].text(0.5, 0.5, 'Predictions vs Actual\n(Requires test data)', 
                              ha='center', va='center', transform=axes[0, 0].transAxes)
                axes[0, 0].set_title('Predictions vs Actual')
                
                # Metrics Bar Chart
                metrics = ['r2_score', 'rmse', 'mae']
                values = [results[metric] for metric in metrics]
                axes[0, 1].bar(metrics, values)
                axes[0, 1].set_title('Performance Metrics')
                axes[0, 1].set_ylabel('Score')
                
                # Trading Metrics
                trading_metrics = results.get('trading_metrics', {})
                if trading_metrics:
                    trading_keys = ['directional_accuracy', 'expected_value', 'profit_factor']
                    trading_values = [trading_metrics.get(key, 0) for key in trading_keys]
                    axes[1, 0].bar(trading_keys, trading_values)
                    axes[1, 0].set_title('Trading Metrics')
                
                # Residuals (placeholder)
                axes[1, 1].text(0.5, 0.5, 'Residual Plot\n(Requires test data)', 
                              ha='center', va='center', transform=axes[1, 1].transAxes)
                axes[1, 1].set_title('Residuals')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
            plt.show()
            
        except Exception as e:
            logger.error(f"Error plotting single model results: {e}")
    
    def _plot_model_comparison(self, save_path: str = None):
        """Plot model comparison"""
        try:
            if not self.comparison_results:
                logger.warning("No comparison results available")
                return
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Model Comparison', fontsize=16)
            
            # Classification comparison
            if 'classification_comparison' in self.comparison_results:
                class_data = self.comparison_results['classification_comparison']
                class_df = pd.DataFrame(class_data)
                
                # Accuracy comparison
                class_df['accuracy'].sort_values().plot(kind='bar', ax=axes[0, 0])
                axes[0, 0].set_title('Classification Accuracy')
                axes[0, 0].set_ylabel('Accuracy')
                axes[0, 0].tick_params(axis='x', rotation=45)
                
                # Trading accuracy comparison
                if 'trading_accuracy' in class_df.columns:
                    class_df['trading_accuracy'].sort_values().plot(kind='bar', ax=axes[0, 1])
                    axes[0, 1].set_title('Trading Accuracy')
                    axes[0, 1].set_ylabel('Accuracy')
                    axes[0, 1].tick_params(axis='x', rotation=45)
            
            # Regression comparison
            if 'regression_comparison' in self.comparison_results:
                reg_data = self.comparison_results['regression_comparison']
                reg_df = pd.DataFrame(reg_data)
                
                # R² comparison
                reg_df['r2_score'].sort_values().plot(kind='bar', ax=axes[1, 0])
                axes[1, 0].set_title('Regression R² Score')
                axes[1, 0].set_ylabel('R² Score')
                axes[1, 0].tick_params(axis='x', rotation=45)
                
                # RMSE comparison
                reg_df['rmse'].sort_values().plot(kind='bar', ax=axes[1, 1])
                axes[1, 1].set_title('RMSE')
                axes[1, 1].set_ylabel('RMSE')
                axes[1, 1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
            plt.show()
            
        except Exception as e:
            logger.error(f"Error plotting model comparison: {e}")
    
    def save_evaluation_results(self, filepath: str):
        """Save evaluation results"""
        try:
            results = {
                'evaluation_results': self.evaluation_results,
                'comparison_results': self.comparison_results,
                'backtest_results': self.backtest_results,
                'save_date': datetime.now()
            }
            
            joblib.dump(results, filepath)
            logger.info(f"Evaluation results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving evaluation results: {e}")
    
    def load_evaluation_results(self, filepath: str):
        """Load evaluation results"""
        try:
            results = joblib.load(filepath)
            
            self.evaluation_results = results['evaluation_results']
            self.comparison_results = results['comparison_results']
            self.backtest_results = results['backtest_results']
            
            logger.info(f"Evaluation results loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading evaluation results: {e}")
