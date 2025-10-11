#!/usr/bin/env python3
"""
Master Test Runner - Runs all manual test suites
"""
import subprocess
import sys
import os
from datetime import datetime

def run_test_suite(script_name, description):
    """Run a test suite and return results"""
    print(f"\n{'='*80}")
    print(f"  Running: {description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            ["poetry", "run", "python", script_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(result.stdout)
        if result.stderr and "UserWarning" not in result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ❌ Test suite timed out")
        return False
    except Exception as e:
        print(f"  ❌ Error running test suite: {e}")
        return False

def main():
    """Run all test suites"""
    print("="*80)
    print("  MAESTRO ML PLATFORM - COMPREHENSIVE TEST EXECUTION")
    print("="*80)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Location: {os.getcwd()}")
    print("="*80)
    
    test_suites = [
        ("tests/manual_test_config.py", "Configuration & Settings Tests"),
        ("tests/manual_test_database.py", "Database Integration Tests"),
        ("tests/manual_test_security.py", "Security Features Tests"),
    ]
    
    results = {}
    for script, description in test_suites:
        results[description] = run_test_suite(script, description)
    
    # Final Summary
    print("\n" + "="*80)
    print("  FINAL TEST SUMMARY")
    print("="*80)
    
    passed_suites = sum(results.values())
    total_suites = len(results)
    
    for description, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {description}")
    
    print("\n" + "-"*80)
    print(f"  Total Suites: {total_suites}")
    print(f"  Passed: {passed_suites}")
    print(f"  Failed: {total_suites - passed_suites}")
    print(f"  Success Rate: {(passed_suites/total_suites)*100:.1f}%")
    print("="*80)
    
    if passed_suites == total_suites:
        print("\n  🎉 ALL TEST SUITES PASSED!")
        return 0
    else:
        print(f"\n  ⚠️  {total_suites - passed_suites} test suite(s) failed")
        print("  Review individual test output above for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())
