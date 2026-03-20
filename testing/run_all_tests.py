"""
Master Test Runner for BrayoForexBot
Runs all test suites and generates comprehensive report
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import subprocess
import time
from datetime import datetime

def run_test_suite(test_name, test_file):
    """Run a single test suite"""
    print("\nRunning", test_name, "...")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        success = result.returncode == 0
        
        return {
            'name': test_name,
            'file': test_file,
            'success': success,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {
            'name': test_name,
            'file': test_file,
            'success': False,
            'duration': 300,
            'stdout': '',
            'stderr': 'Test timed out after 5 minutes'
        }
    except Exception as e:
        return {
            'name': test_name,
            'file': test_file,
            'success': False,
            'duration': 0,
            'stdout': '',
            'stderr': str(e)
        }

def main():
    """Run all test suites"""
    print("BrayoForexBot - Comprehensive Testing Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Define test suites
    test_suites = [
        ("Unit Tests", "testing/test_suite.py"),
        ("Integration Tests", "testing/integration_test.py"),
        ("MT5 Connection Tests", "testing/mt5_simple_test.py")
    ]
    
    results = []
    
    # Run all test suites
    for test_name, test_file in test_suites:
        result = run_test_suite(test_name, test_file)
        results.append(result)
        
        # Show immediate result
        status_icon = "✅" if result['success'] else "❌"
        print(f"{status_icon} {test_name}: {result['duration']:.1f}s")
    
    # Generate comprehensive report
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    total_duration = sum(r['duration'] for r in results)
    
    print(f"📋 Test Suites Run: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {total_tests - successful_tests}")
    print(f"⏱️ Total Duration: {total_duration:.1f} seconds")
    print(f"📈 Success Rate: {successful_tests/total_tests*100:.1f}%")
    
    # Detailed results
    print("\n📋 Detailed Results:")
    print("-" * 50)
    
    for result in results:
        status_icon = "✅" if result['success'] else "❌"
        print(f"\n{status_icon} {result['name']}")
        print(f"   📁 File: {result['file']}")
        print(f"   ⏱️ Duration: {result['duration']:.1f}s")
        
        if not result['success']:
            print(f"   ❌ Error: {result['stderr'][:200]}...")
    
    # Overall assessment
    print("\n" + "=" * 60)
    print("🎯 OVERALL ASSESSMENT")
    print("=" * 60)
    
    if successful_tests == total_tests:
        print("🎉 EXCELLENT! All test suites passed!")
        print("🚀 System is PRODUCTION READY!")
        print("\n✅ Ready for:")
        print("   • Live trading with demo account")
        print("   • AI model deployment")
        print("   • Dashboard usage")
        print("   • Full system operation")
        
    elif successful_tests >= total_tests * 0.8:
        print("✅ GOOD! Most test suites passed.")
        print("🔧 Minor issues to address before production.")
        print("\n⚠️ Review failed tests and fix issues.")
        
    elif successful_tests >= total_tests * 0.6:
        print("⚠️ FAIR! Some test suites failed.")
        print("🛠️ Significant work needed before production.")
        print("\n🚨 Address critical issues before deployment.")
        
    else:
        print("🚨 POOR! Major test failures.")
        print("🚨 Extensive fixes required.")
        print("\n🛑 NOT READY for production use.")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 30)
    
    if successful_tests == total_tests:
        print("✅ Start with demo account trading")
        print("✅ Monitor system performance")
        print("✅ Train AI models with your data")
        print("✅ Launch dashboard for monitoring")
    else:
        print("🔧 Fix failed test suites")
        print("🔧 Review error messages above")
        print("🔧 Test components individually")
        print("🔧 Ensure dependencies are installed")
    
    print("\n📚 Next Steps:")
    print("1. Review detailed test outputs")
    print("2. Fix any failed tests")
    print("3. Test with demo account")
    print("4. Train AI models")
    print("5. Launch dashboard")
    print("6. Start paper trading")
    
    print("=" * 60)
    print(f"📅 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
