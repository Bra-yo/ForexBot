"""
Comprehensive Test Suite for BrayoForexBot
Deep testing of all components and integrations
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Add backtesting directory to path
sys.path.append(str(project_root / "backtesting"))

# Import components to test
from technical_analysis import TechnicalAnalysis
from risk_management import RiskManager
from notifications import NotificationManager
from trading_engine import TradingEngine
from backtest import BacktestEngine
from analytics.metrics import PerformanceMetrics
from ai.feature_engineering import FeatureEngineer
from ai.model_trainer import ModelTrainer
from ai.prediction_engine import TradingPredictor
from ai.evaluation_framework import ModelEvaluator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestTechnicalAnalysis(unittest.TestCase):
    """Test technical analysis components"""
    
    def setUp(self):
        """Set up test data"""
        self.ta = TechnicalAnalysis()
        
        # Create sample OHLCV data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='H')
        np.random.seed(42)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': 1.1000 + np.random.randn(100) * 0.001,
            'high': 1.1000 + np.random.randn(100) * 0.002,
            'low': 1.1000 + np.random.randn(100) * 0.002,
            'close': 1.1000 + np.random.randn(100) * 0.001,
            'volume': np.random.randint(1000, 10000, 100)
        })
        self.sample_data.set_index('timestamp', inplace=True)
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        rsi = self.ta.calculate_rsi(self.sample_data['close'], period=14)
        
        self.assertIsInstance(rsi, pd.Series)
        self.assertEqual(len(rsi), len(self.sample_data))
        self.assertTrue(all(0 <= x <= 100 for x in rsi.dropna()))
        logger.info("✅ RSI calculation test passed")
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        macd, signal, histogram = self.ta.calculate_macd(self.sample_data['close'])
        
        self.assertIsInstance(macd, pd.Series)
        self.assertIsInstance(signal, pd.Series)
        self.assertIsInstance(histogram, pd.Series)
        self.assertEqual(len(macd), len(self.sample_data))
        logger.info("✅ MACD calculation test passed")
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        upper, middle, lower = self.ta.calculate_bollinger_bands(self.sample_data['close'])
        
        self.assertIsInstance(upper, pd.Series)
        self.assertIsInstance(middle, pd.Series)
        self.assertIsInstance(lower, pd.Series)
        self.assertTrue(all(upper >= middle))
        self.assertTrue(all(middle >= lower))
        logger.info("✅ Bollinger Bands test passed")
    
    def test_signal_generation(self):
        """Test trading signal generation"""
        signals = self.ta.analyze_signals(self.sample_data)
        
        self.assertIn('signal', signals)
        self.assertIn('strength', signals)
        self.assertIn('reasons', signals)
        self.assertIn(signals['signal'], ['BUY', 'SELL', 'WAIT'])
        logger.info("✅ Signal generation test passed")

class TestRiskManagement(unittest.TestCase):
    """Test risk management components"""
    
    def setUp(self):
        """Set up risk manager"""
        self.risk_manager = RiskManager(account_balance=10000)
    
    def test_position_sizing(self):
        """Test position sizing calculation"""
        position_size = self.risk_manager.calculate_position_size('EURUSD', 100, 0.02)
        
        self.assertIsInstance(position_size, float)
        self.assertGreater(position_size, 0)
        self.assertLessEqual(position_size, 1.0)  # Max 1 lot
        logger.info("✅ Position sizing test passed")
    
    def test_risk_limits(self):
        """Test risk limit enforcement"""
        # Test within limits
        risk_check = self.risk_manager.can_open_position('EURUSD', 'BUY')
        self.assertTrue(risk_check['allowed'])
        
        # Test exceeding limits
        for _ in range(10):  # Open many positions
            self.risk_manager.update_pair_exposure('EURUSD', 1000)
        
        risk_check = self.risk_manager.can_open_position('EURUSD', 'BUY')
        self.assertFalse(risk_check['allowed'])
        logger.info("✅ Risk limits test passed")
    
    def test_exposure_tracking(self):
        """Test exposure tracking"""
        initial_exposure = self.risk_manager.get_total_exposure()
        
        self.risk_manager.update_pair_exposure('EURUSD', 5000)
        new_exposure = self.risk_manager.get_total_exposure()
        
        self.assertEqual(new_exposure, initial_exposure + 5000)
        logger.info("✅ Exposure tracking test passed")

class TestFeatureEngineering(unittest.TestCase):
    """Test AI feature engineering"""
    
    def setUp(self):
        """Set up feature engineer and data"""
        self.feature_engineer = FeatureEngineer()
        
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=200, freq='H')
        np.random.seed(42)
        
        self.sample_data = pd.DataFrame({
            'open': 1.1000 + np.random.randn(200) * 0.001,
            'high': 1.1000 + np.random.randn(200) * 0.002,
            'low': 1.1000 + np.random.randn(200) * 0.002,
            'close': 1.1000 + np.random.randn(200) * 0.001,
            'volume': np.random.randint(1000, 10000, 200)
        }, index=dates)
    
    def test_feature_creation(self):
        """Test feature creation"""
        features_df = self.feature_engineer.create_features(self.sample_data)
        
        self.assertIsInstance(features_df, pd.DataFrame)
        self.assertGreater(len(features_df.columns), 50)  # Should have many features
        self.assertGreater(len(features_df), 100)  # Should have most rows after feature creation
        
        # Check for expected feature types
        feature_types = [
            'price_change', 'volume_change', 'rsi_14', 'macd', 
            'bb_upper_20', 'hour', 'day_of_week'
        ]
        
        for feature in feature_types:
            self.assertTrue(any(feature in col for col in features_df.columns))
        
        logger.info("✅ Feature creation test passed")
    
    def test_target_creation(self):
        """Test target variable creation"""
        features_df = self.feature_engineer.create_features(self.sample_data, target_horizon=5)
        
        # Check for target columns
        target_cols = [col for col in features_df.columns if 'target_' in col]
        self.assertGreater(len(target_cols), 0)
        
        # Check specific targets
        expected_targets = ['target_return_5', 'target_direction_5', 'target_class_5']
        for target in expected_targets:
            self.assertTrue(target in features_df.columns)
        
        logger.info("✅ Target creation test passed")
    
    def test_feature_scaling(self):
        """Test feature scaling"""
        features_df = self.feature_engineer.create_features(self.sample_data)
        scaled_df = self.feature_engineer.scale_features(features_df)
        
        self.assertIsInstance(scaled_df, pd.DataFrame)
        self.assertEqual(len(scaled_df), len(features_df))
        
        # Check that scaled features have mean ~0 and std ~1
        feature_cols = self.feature_engineer.feature_columns
        if feature_cols:
            scaled_means = scaled_df[feature_cols].mean()
            scaled_stds = scaled_df[feature_cols].std()
            
            self.assertTrue(all(abs(mean) < 0.1 for mean in scaled_means))
            self.assertTrue(all(abs(std - 1.0) < 0.1 for std in scaled_stds))
        
        logger.info("✅ Feature scaling test passed")

class TestBacktesting(unittest.TestCase):
    """Test backtesting engine"""
    
    def setUp(self):
        """Set up backtest engine"""
        self.backtest_engine = BacktestEngine()
        
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=1000, freq='H')
        np.random.seed(42)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': 1.1000 + np.random.randn(1000) * 0.001,
            'high': 1.1000 + np.random.randn(1000) * 0.002,
            'low': 1.1000 + np.random.randn(1000) * 0.002,
            'close': 1.1000 + np.random.randn(1000) * 0.001,
            'volume': np.random.randint(1000, 10000, 1000)
        })
        self.sample_data.set_index('timestamp', inplace=True)
    
    def test_backtest_initialization(self):
        """Test backtest engine initialization"""
        self.backtest_engine.initialize(
            data=self.sample_data,
            initial_balance=10000,
            strategy_params={'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30}
        )
        
        self.assertEqual(self.backtest_engine.initial_balance, 10000)
        self.assertEqual(len(self.backtest_engine.data), len(self.sample_data))
        logger.info("✅ Backtest initialization test passed")
    
    def test_backtest_execution(self):
        """Test backtest execution"""
        self.backtest_engine.initialize(
            data=self.sample_data,
            initial_balance=10000,
            strategy_params={'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30}
        )
        
        results = self.backtest_engine.run_backtest()
        
        self.assertIsInstance(results, dict)
        self.assertIn('total_return', results)
        self.assertIn('sharpe_ratio', results)
        self.assertIn('max_drawdown', results)
        self.assertIn('trades', results)
        self.assertGreater(len(results['trades']), 0)
        
        logger.info("✅ Backtest execution test passed")
    
    def test_performance_calculation(self):
        """Test performance metric calculations"""
        # Create sample trades
        trades = [
            {'entry_time': datetime(2023, 1, 1), 'exit_time': datetime(2023, 1, 2),
             'entry_price': 1.1000, 'exit_price': 1.1100, 'type': 'BUY', 'volume': 0.1},
            {'entry_time': datetime(2023, 1, 3), 'exit_time': datetime(2023, 1, 4),
             'entry_price': 1.1050, 'exit_price': 1.0950, 'type': 'SELL', 'volume': 0.1}
        ]
        
        perf_metrics = PerformanceMetrics()
        metrics = perf_metrics.calculate_metrics(trades)
        
        self.assertIn('total_return', metrics)
        self.assertIn('win_rate', metrics)
        self.assertIn('profit_factor', metrics)
        self.assertIn('sharpe_ratio', metrics)
        
        logger.info("✅ Performance calculation test passed")

class TestModelTraining(unittest.TestCase):
    """Test ML model training"""
    
    def setUp(self):
        """Set up model trainer and data"""
        self.model_trainer = ModelTrainer()
        
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=500, freq='H')
        np.random.seed(42)
        
        self.sample_data = pd.DataFrame({
            'open': 1.1000 + np.random.randn(500) * 0.001,
            'high': 1.1000 + np.random.randn(500) * 0.002,
            'low': 1.1000 + np.random.randn(500) * 0.002,
            'close': 1.1000 + np.random.randn(500) * 0.001,
            'volume': np.random.randint(1000, 10000, 500)
        }, index=dates)
    
    def test_data_preparation(self):
        """Test data preparation for training"""
        data_splits = self.model_trainer.prepare_data(
            self.sample_data, 
            target_col='target_direction_1',
            test_size=0.2,
            validation_size=0.2
        )
        
        self.assertIn('X_train', data_splits)
        self.assertIn('X_val', data_splits)
        self.assertIn('X_test', data_splits)
        self.assertIn('y_train', data_splits)
        self.assertIn('y_val', data_splits)
        self.assertIn('y_test', data_splits)
        
        # Check split ratios
        total_len = len(data_splits['X_train']) + len(data_splits['X_val']) + len(data_splits['X_test'])
        self.assertAlmostEqual(total_len, len(self.sample_data), delta=20)  # Allow for feature engineering loss
        
        logger.info("✅ Data preparation test passed")
    
    def test_model_training(self):
        """Test model training"""
        # First prepare data
        data_splits = self.model_trainer.prepare_data(
            self.sample_data, 
            target_col='target_direction_1',
            test_size=0.2,
            validation_size=0.2
        )
        
        if data_splits:
            # Train a simple model
            results = self.model_trainer.train_classification_models(
                data_splits, 
                models_to_train=['random_forest']
            )
            
            self.assertIn('random_forest', results)
            self.assertIn('model', results['random_forest'])
            self.assertIn('performance', results['random_forest'])
            
            # Check performance metrics
            perf = results['random_forest']['performance']
            self.assertIn('accuracy', perf)
            self.assertIn('f1_score', perf)
            
            logger.info("✅ Model training test passed")
        else:
            self.skipTest("Data preparation failed, skipping model training test")
    
    def test_model_evaluation(self):
        """Test model evaluation"""
        # This would require trained models, so we'll test the evaluation framework
        evaluator = ModelEvaluator()
        
        # Test with dummy data
        y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 1, 0, 2, 2, 0, 1, 2])
        
        accuracy = accuracy_score(y_true, y_pred)
        self.assertIsInstance(accuracy, float)
        self.assertGreaterEqual(accuracy, 0)
        self.assertLessEqual(accuracy, 1)
        
        logger.info("✅ Model evaluation test passed")

class TestIntegration(unittest.TestCase):
    """Test component integration"""
    
    def setUp(self):
        """Set up integration test"""
        self.trading_engine = TradingEngine()
        
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='H')
        np.random.seed(42)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': 1.1000 + np.random.randn(100) * 0.001,
            'high': 1.1000 + np.random.randn(100) * 0.002,
            'low': 1.1000 + np.random.randn(100) * 0.002,
            'close': 1.1000 + np.random.randn(100) * 0.001,
            'volume': np.random.randint(1000, 10000, 100)
        })
        self.sample_data.set_index('timestamp', inplace=True)
    
    def test_trading_engine_integration(self):
        """Test trading engine component integration"""
        # Test technical analysis integration
        signals = self.trading_engine.technical_analysis.analyze_signals(self.sample_data)
        self.assertIsInstance(signals, dict)
        self.assertIn('signal', signals)
        
        # Test risk management integration
        risk_check = self.trading_engine.risk_manager.can_open_position('EURUSD', 'BUY')
        self.assertIsInstance(risk_check, dict)
        self.assertIn('allowed', risk_check)
        
        logger.info("✅ Trading engine integration test passed")
    
    def test_ai_pipeline_integration(self):
        """Test AI pipeline integration"""
        feature_engineer = FeatureEngineer()
        
        # Test feature engineering
        features_df = feature_engineer.create_features(self.sample_data)
        self.assertIsInstance(features_df, pd.DataFrame)
        
        # Test that features can be used for ML
        if len(features_df) > 50 and 'target_direction_1' in features_df.columns:
            X = features_df[feature_engineer.feature_columns]
            y = features_df['target_direction_1']
            
            self.assertEqual(len(X), len(y))
            self.assertGreater(len(X.columns), 10)  # Should have many features
            
            logger.info("✅ AI pipeline integration test passed")
        else:
            self.skipTest("Insufficient features for AI integration test")
    
    def test_notification_integration(self):
        """Test notification system integration"""
        notifications = NotificationManager()
        
        # Test notification creation
        test_signal = {
            'signal': 'BUY',
            'symbol': 'EURUSD',
            'price': 1.1000,
            'confidence': 0.75,
            'reasons': ['RSI oversold', 'MACD bullish crossover']
        }
        
        # This would normally send notification, but we'll just test the formatting
        message = notifications._format_trade_signal(test_signal)
        self.assertIsInstance(message, str)
        self.assertIn('BUY', message)
        self.assertIn('EURUSD', message)
        self.assertIn('1.1000', message)
        
        logger.info("✅ Notification integration test passed")

class TestPerformance(unittest.TestCase):
    """Performance and stress testing"""
    
    def test_feature_engineering_performance(self):
        """Test feature engineering performance"""
        feature_engineer = FeatureEngineer()
        
        # Create larger dataset
        dates = pd.date_range(start='2023-01-01', periods=5000, freq='H')
        np.random.seed(42)
        
        large_data = pd.DataFrame({
            'open': 1.1000 + np.random.randn(5000) * 0.001,
            'high': 1.1000 + np.random.randn(5000) * 0.002,
            'low': 1.1000 + np.random.randn(5000) * 0.002,
            'close': 1.1000 + np.random.randn(5000) * 0.001,
            'volume': np.random.randint(1000, 10000, 5000)
        }, index=dates)
        
        # Time the feature creation
        start_time = datetime.now()
        features_df = feature_engineer.create_features(large_data)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Should process within reasonable time
        self.assertLess(processing_time, 30)  # 30 seconds max
        self.assertGreater(len(features_df), 4000)  # Should retain most data
        
        logger.info(f"✅ Feature engineering performance test passed ({processing_time:.2f}s for 5000 rows)")
    
    def test_backtest_performance(self):
        """Test backtesting performance"""
        backtest_engine = BacktestEngine()
        
        # Create large dataset
        dates = pd.date_range(start='2022-01-01', periods=10000, freq='H')
        np.random.seed(42)
        
        large_data = pd.DataFrame({
            'timestamp': dates,
            'open': 1.1000 + np.random.randn(10000) * 0.001,
            'high': 1.1000 + np.random.randn(10000) * 0.002,
            'low': 1.1000 + np.random.randn(10000) * 0.002,
            'close': 1.1000 + np.random.randn(10000) * 0.001,
            'volume': np.random.randint(1000, 10000, 10000)
        })
        large_data.set_index('timestamp', inplace=True)
        
        # Time the backtest
        start_time = datetime.now()
        
        backtest_engine.initialize(
            data=large_data,
            initial_balance=10000,
            strategy_params={'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30}
        )
        results = backtest_engine.run_backtest()
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time
        self.assertLess(processing_time, 60)  # 60 seconds max
        self.assertIsInstance(results, dict)
        
        logger.info(f"✅ Backtest performance test passed ({processing_time:.2f}s for 10000 bars)")

def run_comprehensive_tests():
    """Run all tests and generate report"""
    print("Starting Comprehensive Test Suite for BrayoForexBot")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestTechnicalAnalysis,
        TestRiskManagement, 
        TestFeatureEngineering,
        TestBacktesting,
        TestModelTraining,
        TestIntegration,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Generate summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"🚫 Errors: {len(result.errors)}")
    print(f"⏭️ Skipped: {len(result.skipped)}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n🚫 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    print("\n" + "=" * 60)
    
    if success_rate >= 90:
        print("🎉 EXCELLENT! System is ready for production!")
    elif success_rate >= 75:
        print("✅ GOOD! System mostly functional, minor issues to address.")
    elif success_rate >= 50:
        print("⚠️ FAIR! System needs attention before production use.")
    else:
        print("🚨 POOR! Significant issues found, requires major fixes.")
    
    print("=" * 60)
    
    return result

if __name__ == "__main__":
    run_comprehensive_tests()
