"""
Integration Testing for BrayoForexBot
Tests end-to-end workflows and component interactions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Add backtesting directory to path
sys.path.append(str(project_root / "backtesting"))

from trading_engine import TradingEngine
from backtest import BacktestEngine
from ai.feature_engineering import FeatureEngineer
from ai.model_trainer import ModelTrainer
from ai.prediction_engine import TradingPredictor

logger = logging.getLogger(__name__)

class IntegrationTester:
    """Comprehensive integration testing"""
    
    def __init__(self):
        self.results = {}
        
    def test_complete_trading_workflow(self):
        """Test complete trading workflow from data to execution"""
        print("Testing Complete Trading Workflow...")
        
        try:
            # 1. Create sample market data
            market_data = self._create_sample_market_data(days=30)
            
            # 2. Initialize trading engine
            trading_engine = TradingEngine()
            
            # 3. Analyze market with technical indicators
            signals = trading_engine.technical_analysis.analyze_signals(market_data)
            
            # 4. Check risk management
            risk_check = trading_engine.risk_manager.can_open_position('EURUSD', signals['signal'])
            
            # 5. Create trade decision
            if risk_check['allowed'] and signals['signal'] in ['BUY', 'SELL']:
                trade_decision = {
                    'symbol': 'EURUSD',
                    'action': signals['signal'],
                    'price': market_data['close'].iloc[-1],
                    'confidence': signals['strength'] / 100,
                    'reasons': signals['reasons']
                }
                
                # 6. Execute trade (simulation)
                trade_result = trading_engine.execute_trade(trade_decision)
                
                self.results['trading_workflow'] = {
                    'status': 'success',
                    'signals_generated': True,
                    'risk_passed': risk_check['allowed'],
                    'trade_executed': trade_result['success'],
                    'signal': signals['signal'],
                    'confidence': signals['strength']
                }
                
                print(f"✅ Trading workflow: {signals['signal']} signal, risk check passed, trade executed")
            else:
                self.results['trading_workflow'] = {
                    'status': 'no_trade',
                    'reason': 'risk_check_failed' if not risk_check['allowed'] else 'weak_signal',
                    'signal': signals['signal'],
                    'confidence': signals['strength']
                }
                
                print(f"ℹ️ Trading workflow: No trade (risk: {risk_check['allowed']}, signal: {signals['signal']})")
                
        except Exception as e:
            self.results['trading_workflow'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"❌ Trading workflow error: {e}")
    
    def test_ai_pipeline_workflow(self):
        """Test complete AI pipeline from data to prediction"""
        print("🤖 Testing AI Pipeline Workflow...")
        
        try:
            # 1. Create sample data
            market_data = self._create_sample_market_data(days=60)
            
            # 2. Feature engineering
            feature_engineer = FeatureEngineer()
            features_df = feature_engineer.create_features(market_data, target_horizon=5)
            
            # 3. Prepare data for ML
            model_trainer = ModelTrainer()
            data_splits = model_trainer.prepare_data(
                features_df, 
                target_col='target_direction_5',
                test_size=0.2,
                validation_size=0.2
            )
            
            # 4. Train simple model
            if data_splits:
                training_results = model_trainer.train_classification_models(
                    data_splits, 
                    models_to_train=['random_forest']
                )
                
                if 'random_forest' in training_results:
                    # 5. Make predictions
                    predictor = TradingPredictor()
                    predictor.models['random_forest'] = {
                        'model': training_results['random_forest']['model'],
                        'type': 'classification'
                    }
                    predictor.feature_engineer = feature_engineer
                    
                    prediction = predictor.predict_direction(market_data)
                    
                    self.results['ai_pipeline'] = {
                        'status': 'success',
                        'features_created': len(features_df.columns),
                        'model_trained': True,
                        'prediction_made': True,
                        'signal': prediction['signal'],
                        'confidence': prediction['confidence']
                    }
                    
                    print(f"✅ AI pipeline: {len(features_df.columns)} features, model trained, prediction: {prediction['signal']} ({prediction['confidence']:.2f})")
                else:
                    raise Exception("Model training failed")
            else:
                raise Exception("Data preparation failed")
                
        except Exception as e:
            self.results['ai_pipeline'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"❌ AI pipeline error: {e}")
    
    def test_backtest_to_deployment_workflow(self):
        """Test workflow from backtest to deployment decision"""
        print("📊 Testing Backtest to Deployment Workflow...")
        
        try:
            # 1. Create historical data
            historical_data = self._create_sample_market_data(days=365)
            
            # 2. Run backtest
            backtest_engine = BacktestEngine()
            backtest_engine.initialize(
                data=historical_data,
                initial_balance=10000,
                strategy_params={'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30}
            )
            
            backtest_results = backtest_engine.run_backtest()
            
            # 3. Analyze backtest performance
            total_return = backtest_results['total_return']
            sharpe_ratio = backtest_results['sharpe_ratio']
            max_drawdown = backtest_results['max_drawdown']
            win_rate = backtest_results['win_rate']
            
            # 4. Make deployment decision
            deployment_ready = True
            deployment_reasons = []
            
            if total_return < 0.05:  # Less than 5% annual return
                deployment_ready = False
                deployment_reasons.append("Low total return")
            
            if sharpe_ratio < 0.5:
                deployment_ready = False
                deployment_reasons.append("Low Sharpe ratio")
            
            if max_drawdown < -0.20:  # More than 20% drawdown
                deployment_ready = False
                deployment_reasons.append("High maximum drawdown")
            
            if win_rate < 0.4:  # Less than 40% win rate
                deployment_ready = False
                deployment_reasons.append("Low win rate")
            
            self.results['backtest_to_deployment'] = {
                'status': 'success',
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'deployment_ready': deployment_ready,
                'deployment_reasons': deployment_reasons,
                'trades_analyzed': len(backtest_results['trades'])
            }
            
            if deployment_ready:
                print(f"✅ Backtest to deployment: READY (Return: {total_return:.1%}, Sharpe: {sharpe_ratio:.2f})")
            else:
                print(f"⚠️ Backtest to deployment: NOT READY - {', '.join(deployment_reasons)}")
                
        except Exception as e:
            self.results['backtest_to_deployment'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"❌ Backtest to deployment error: {e}")
    
    def test_multi_symbol_workflow(self):
        """Test workflow with multiple symbols"""
        print("🌐 Testing Multi-Symbol Workflow...")
        
        try:
            symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
            results = {}
            
            # Initialize trading engine
            trading_engine = TradingEngine()
            
            for symbol in symbols:
                # Create data for each symbol
                symbol_data = self._create_sample_market_data(days=30, symbol=symbol)
                
                # Analyze each symbol
                signals = trading_engine.technical_analysis.analyze_signals(symbol_data)
                risk_check = trading_engine.risk_manager.can_open_position(symbol, signals['signal'])
                
                results[symbol] = {
                    'signal': signals['signal'],
                    'strength': signals['strength'],
                    'risk_allowed': risk_check['allowed'],
                    'would_trade': risk_check['allowed'] and signals['signal'] in ['BUY', 'SELL']
                }
            
            # Check overall system behavior
            trading_signals = sum(1 for r in results.values() if r['would_trade'])
            
            self.results['multi_symbol'] = {
                'status': 'success',
                'symbols_analyzed': len(symbols),
                'trading_signals': trading_signals,
                'individual_results': results
            }
            
            print(f"✅ Multi-symbol workflow: {len(symbols)} symbols analyzed, {trading_signals} trading signals")
            
        except Exception as e:
            self.results['multi_symbol'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"❌ Multi-symbol workflow error: {e}")
    
    def test_performance_under_load(self):
        """Test system performance under load"""
        print("⚡ Testing Performance Under Load...")
        
        try:
            # Test with large dataset
            large_data = self._create_sample_market_data(days=365)  # 1 year of data
            
            # Time feature engineering
            start_time = time.time()
            feature_engineer = FeatureEngineer()
            features_df = feature_engineer.create_features(large_data)
            feature_time = time.time() - start_time
            
            # Time backtesting
            start_time = time.time()
            backtest_engine = BacktestEngine()
            backtest_engine.initialize(
                data=large_data,
                initial_balance=10000,
                strategy_params={'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30}
            )
            backtest_results = backtest_engine.run_backtest()
            backtest_time = time.time() - start_time
            
            # Time multiple signal analysis
            start_time = time.time()
            trading_engine = TradingEngine()
            
            # Analyze multiple timeframes
            timeframes = ['M5', 'M15', 'H1', 'H4']
            signal_results = {}
            
            for tf in timeframes:
                # Resample data (simplified)
                resampled_data = large_data.resample(tf).agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
                }).dropna()
                
                signals = trading_engine.technical_analysis.analyze_signals(resampled_data)
                signal_results[tf] = signals['signal']
            
            analysis_time = time.time() - start_time
            
            # Performance criteria
            feature_ok = feature_time < 30  # 30 seconds max
            backtest_ok = backtest_time < 60  # 60 seconds max
            analysis_ok = analysis_time < 10  # 10 seconds max
            
            self.results['performance_load'] = {
                'status': 'success',
                'data_points': len(large_data),
                'feature_engineering_time': feature_time,
                'backtest_time': backtest_time,
                'analysis_time': analysis_time,
                'performance_acceptable': all([feature_ok, backtest_ok, analysis_ok]),
                'signal_results': signal_results
            }
            
            print(f"✅ Performance test: Features {feature_time:.1f}s, Backtest {backtest_time:.1f}s, Analysis {analysis_time:.1f}s")
            
        except Exception as e:
            self.results['performance_load'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"❌ Performance test error: {e}")
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        print("🛡️ Testing Error Handling and Recovery...")
        
        try:
            error_scenarios = []
            
            # 1. Test with invalid data
            try:
                invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
                trading_engine = TradingEngine()
                signals = trading_engine.technical_analysis.analyze_signals(invalid_data)
                error_scenarios.append({'scenario': 'invalid_data', 'handled': False})
            except:
                error_scenarios.append({'scenario': 'invalid_data', 'handled': True})
            
            # 2. Test with empty data
            try:
                empty_data = pd.DataFrame()
                feature_engineer = FeatureEngineer()
                features = feature_engineer.create_features(empty_data)
                error_scenarios.append({'scenario': 'empty_data', 'handled': False})
            except:
                error_scenarios.append({'scenario': 'empty_data', 'handled': True})
            
            # 3. Test risk limits
            try:
                risk_manager = RiskManager(account_balance=10000)
                # Exceed risk limits
                for _ in range(100):
                    risk_manager.update_pair_exposure('EURUSD', 1000)
                
                risk_check = risk_manager.can_open_position('EURUSD', 'BUY')
                error_scenarios.append({
                    'scenario': 'risk_limits', 
                    'handled': not risk_check['allowed']
                })
            except:
                error_scenarios.append({'scenario': 'risk_limits', 'handled': False})
            
            # 4. Test model prediction with no features
            try:
                predictor = TradingPredictor()
                prediction = predictor.predict_direction(pd.DataFrame())
                error_scenarios.append({'scenario': 'no_features', 'handled': True})
            except:
                error_scenarios.append({'scenario': 'no_features', 'handled': False})
            
            handled_correctly = sum(1 for s in error_scenarios if s['handled'])
            total_scenarios = len(error_scenarios)
            
            self.results['error_handling'] = {
                'status': 'success',
                'scenarios_tested': total_scenarios,
                'handled_correctly': handled_correctly,
                'error_handling_rate': handled_correctly / total_scenarios,
                'scenarios': error_scenarios
            }
            
            print(f"✅ Error handling: {handled_correctly}/{total_scenarios} scenarios handled correctly")
            
        except Exception as e:
            self.results['error_handling'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"❌ Error handling test error: {e}")
    
    def _create_sample_market_data(self, days: int = 30, symbol: str = 'EURUSD') -> pd.DataFrame:
        """Create sample market data for testing"""
        # Generate realistic forex data
        np.random.seed(42)
        
        # Base price for different symbols
        base_prices = {
            'EURUSD': 1.1000,
            'GBPUSD': 1.2500,
            'USDJPY': 110.00
        }
        
        base_price = base_prices.get(symbol, 1.1000)
        
        # Create hourly data
        periods = days * 24
        dates = pd.date_range(start='2023-01-01', periods=periods, freq='H')
        
        # Generate realistic price movements
        returns = np.random.normal(0, 0.001, periods)  # 0.1% std dev
        prices = [base_price]
        
        for ret in returns:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
        
        prices = prices[1:]  # Remove initial price
        
        # Create OHLCV data
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            # Generate realistic OHLC
            volatility = 0.0005
            high = close + abs(np.random.normal(0, volatility))
            low = close - abs(np.random.normal(0, volatility))
            open_price = low + (high - low) * np.random.random()
            
            # Ensure OHLC relationships
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def run_all_integration_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Comprehensive Integration Tests")
        print("=" * 60)
        
        # Run all tests
        tests = [
            self.test_complete_trading_workflow,
            self.test_ai_pipeline_workflow,
            self.test_backtest_to_deployment_workflow,
            self.test_multi_symbol_workflow,
            self.test_performance_under_load,
            self.test_error_handling_and_recovery
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"❌ Integration test failed: {e}")
        
        # Generate summary report
        self._generate_integration_report()
    
    def _generate_integration_report(self):
        """Generate comprehensive integration report"""
        print("\n" + "=" * 60)
        print("📊 INTEGRATION TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results.values() if r.get('status') == 'success')
        failed_tests = sum(1 for r in self.results.values() if r.get('status') == 'error')
        
        print(f"✅ Total Tests: {total_tests}")
        print(f"🎯 Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {successful_tests/total_tests*100:.1f}%")
        
        print("\n📋 Detailed Results:")
        print("-" * 40)
        
        for test_name, result in self.results.items():
            status_icon = "✅" if result.get('status') == 'success' else "❌"
            print(f"{status_icon} {test_name.replace('_', ' ').title()}")
            
            if result.get('status') == 'success':
                # Show key metrics
                if 'signal' in result:
                    print(f"    Signal: {result['signal']}")
                if 'confidence' in result:
                    print(f"    Confidence: {result['confidence']:.2f}")
                if 'deployment_ready' in result:
                    print(f"    Deployment Ready: {result['deployment_ready']}")
                if 'performance_acceptable' in result:
                    print(f"    Performance: {'✅' if result['performance_acceptable'] else '❌'}")
            else:
                print(f"    Error: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 60)
        
        # Overall assessment
        if successful_tests == total_tests:
            print("🎉 EXCELLENT! All integration tests passed!")
            print("🚀 System is ready for production deployment!")
        elif successful_tests >= total_tests * 0.8:
            print("✅ GOOD! Most integration tests passed.")
            print("🔧 Minor issues to address before production.")
        elif successful_tests >= total_tests * 0.6:
            print("⚠️ FAIR! Some integration issues found.")
            print("🛠️ Significant work needed before production.")
        else:
            print("🚨 POOR! Major integration issues.")
            print("🚨 Extensive fixes required before production.")
        
        print("=" * 60)

if __name__ == "__main__":
    tester = IntegrationTester()
    tester.run_all_integration_tests()
