"""
Quick Setup and Test for BrayoForexBot
Install dependencies and run basic tests
"""

import subprocess
import sys
from pathlib import Path

def install_basic_deps():
    """Install basic dependencies needed for testing"""
    print("📦 Installing basic dependencies for testing...")
    
    basic_deps = [
        'pandas>=2.0.0',
        'numpy>=1.24.0', 
        'matplotlib>=3.7.0',
        'seaborn>=0.12.0'
    ]
    
    try:
        for dep in basic_deps:
            print(f"📦 Installing {dep}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {dep} installed successfully")
            else:
                print(f"❌ Failed to install {dep}: {result.stderr}")
        
        print("✅ Basic dependencies installation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def run_basic_test():
    """Run a basic test to verify setup"""
    print("\n🧪 Running Basic Setup Test...")
    
    test_code = '''
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import pandas as pd
    import numpy as np
    print("✅ Pandas and NumPy imported successfully")
    
    # Test basic functionality
    dates = pd.date_range(start='2023-01-01', periods=10, freq='H')
    data = pd.DataFrame({
        'timestamp': dates,
        'open': 1.1000 + np.random.randn(10) * 0.001,
        'high': 1.1000 + np.random.randn(10) * 0.002,
        'low': 1.1000 + np.random.randn(10) * 0.002,
        'close': 1.1000 + np.random.randn(10) * 0.001,
        'volume': np.random.randint(1000, 10000, 10)
    })
    data.set_index('timestamp', inplace=True)
    
    print(f"✅ Sample data created: {len(data)} rows")
    print(f"✅ Data columns: {list(data.columns)}")
    print(f"✅ Price range: {data['close'].min():.5f} - {data['close'].max():.5f}")
    
    print("\\n🎉 BASIC SETUP TEST PASSED!")
    print("🚀 Your Python environment is ready for BrayoForexBot!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📦 Please run: python -m pip install pandas numpy matplotlib")
except Exception as e:
    print(f"❌ Error: {e}")
'''
    
    # Write test code to temporary file
    test_file = Path("basic_test.py")
    with open(test_file, 'w') as f:
        f.write(test_code)
    
    try:
        # Run basic test
        result = subprocess.run([
            sys.executable, str(test_file)
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(f"❌ Test errors: {result.stderr}")
        
        # Clean up
        test_file.unlink()
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running basic test: {e}")
        return False

def show_next_steps():
    """Show next steps for full testing"""
    print("\n" + "="*60)
    print("📋 NEXT STEPS FOR FULL TESTING")
    print("="*60)
    
    print("\n📦 1. Install All Dependencies:")
    print("   python -m pip install pandas numpy matplotlib seaborn yfinance requests python-dotenv")
    print("   python -m pip install scikit-learn xgboost lightgbm joblib optuna")
    
    print("\n🧪 2. Run Full Test Suite:")
    print("   python testing/run_all_tests.py")
    
    print("\n🔧 3. Individual Tests:")
    print("   python testing/test_suite.py          # Unit tests")
    print("   python testing/integration_test.py     # Integration tests") 
    print("   python testing/mt5_connection_test.py # MT5 tests")
    
    print("\n🌐 4. Launch Dashboard:")
    print("   python dashboard/run_dashboard.py")
    
    print("\n🏦 5. Test MT5 Connection:")
    print("   - Open MetaTrader 5")
    print("   - Enable 'Algo Trading'")
    print("   - Login to DEMO account")
    print("   - Run: python testing/mt5_connection_test.py")
    
    print("\n🤖 6. Train AI Models:")
    print("   - Collect historical data")
    print("   - Run: python ai/train_models.py")
    
    print("="*60)

def main():
    """Main setup and test function"""
    print("🚀 BrayoForexBot - Quick Setup & Test")
    print("="*60)
    
    # Step 1: Install basic dependencies
    if install_basic_deps():
        # Step 2: Run basic test
        if run_basic_test():
            # Step 3: Show next steps
            show_next_steps()
        else:
            print("\n❌ Basic test failed. Check your Python setup.")
    else:
        print("\n❌ Dependency installation failed. Check your internet connection.")

if __name__ == "__main__":
    main()
