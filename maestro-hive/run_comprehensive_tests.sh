#!/bin/bash
#
# Comprehensive Test Runner for Team Execution V2
#
# This script:
# 1. Runs extensive test scenarios
# 2. Analyzes results and identifies gaps
# 3. Generates improvement proposals
#

set -e

echo "========================================================================"
echo "  COMPREHENSIVE TEST SUITE - TEAM EXECUTION V2"
echo "========================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python environment
echo "🔍 Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ Found: $PYTHON_VERSION"
echo ""

# Check dependencies
echo "🔍 Checking dependencies..."
REQUIRED_MODULES=("asyncio" "dataclasses" "pathlib")
for module in "${REQUIRED_MODULES[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        echo "  ✅ $module"
    else
        echo "  ❌ $module (missing)"
        exit 1
    fi
done
echo ""

# Create output directory
OUTPUT_DIR="./test_comprehensive_output"
mkdir -p "$OUTPUT_DIR"
echo "📁 Output directory: $OUTPUT_DIR"
echo ""

# Run comprehensive tests
echo "========================================================================"
echo "  PHASE 1: RUNNING TEST SCENARIOS"
echo "========================================================================"
echo ""

python3 comprehensive_test_scenarios.py
TEST_EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "  PHASE 2: ANALYZING RESULTS AND IDENTIFYING GAPS"
echo "========================================================================"
echo ""

# Run gap analysis
python3 test_gap_analyzer.py "$OUTPUT_DIR"
GAP_EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "  RESULTS SUMMARY"
echo "========================================================================"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All test scenarios passed"
else
    echo "❌ Some test scenarios failed (exit code: $TEST_EXIT_CODE)"
fi

if [ $GAP_EXIT_CODE -eq 0 ]; then
    echo "✅ No critical gaps identified"
elif [ $GAP_EXIT_CODE -eq 1 ]; then
    echo "⚠️  High priority gaps found"
elif [ $GAP_EXIT_CODE -eq 2 ]; then
    echo "🚨 Critical gaps found - must fix before proceeding"
fi

echo ""
echo "📊 Detailed reports available in: $OUTPUT_DIR"
echo "  - test_suite_summary.json - Full test results"
echo "  - gap_analysis_report.json - Gap analysis and improvement proposals"
echo "  - *_execution_result.json - Individual scenario results"
echo ""

# Final exit code
if [ $TEST_EXIT_CODE -ne 0 ] || [ $GAP_EXIT_CODE -eq 2 ]; then
    echo "❌ TESTS FAILED - Review reports and fix issues"
    exit 1
else
    echo "✅ TESTS COMPLETE - Check reports for recommendations"
    exit 0
fi
