#!/bin/bash
#
# Maestro ML Platform - Comprehensive Test Suite
# Purpose: Run all platform tests and generate validation report
# Usage: ./tests/run_all_tests.sh [--verbose] [--report-file <path>]
#

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=false
REPORT_FILE="test_results_$(date +%Y%m%d_%H%M%S).txt"
TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$TESTS_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --report-file)
            REPORT_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Start test report
echo "=======================================" | tee "$REPORT_FILE"
echo "Maestro ML Platform - Test Report" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "Date: $(date)" | tee -a "$REPORT_FILE"
echo "Environment: ${ML_PLATFORM_ENV:-dev}" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Function to run a test suite
run_test_suite() {
    local test_name=$1
    local test_script=$2

    echo -e "${BLUE}[TEST]${NC} Running $test_name..." | tee -a "$REPORT_FILE"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ ! -f "$test_script" ]; then
        echo -e "${YELLOW}[SKIP]${NC} $test_name - Script not found: $test_script" | tee -a "$REPORT_FILE"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        return
    fi

    # Run test and capture output
    if [ "$VERBOSE" = true ]; then
        if bash "$test_script" 2>&1 | tee -a "$REPORT_FILE"; then
            echo -e "${GREEN}[PASS]${NC} $test_name" | tee -a "$REPORT_FILE"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}[FAIL]${NC} $test_name" | tee -a "$REPORT_FILE"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        if bash "$test_script" >> "$REPORT_FILE" 2>&1; then
            echo -e "${GREEN}[PASS]${NC} $test_name" | tee -a "$REPORT_FILE"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}[FAIL]${NC} $test_name" | tee -a "$REPORT_FILE"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi

    echo "" | tee -a "$REPORT_FILE"
}

# Function to run Python tests
run_python_test() {
    local test_name=$1
    local test_file=$2

    echo -e "${BLUE}[TEST]${NC} Running $test_name..." | tee -a "$REPORT_FILE"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ ! -f "$test_file" ]; then
        echo -e "${YELLOW}[SKIP]${NC} $test_name - Test file not found: $test_file" | tee -a "$REPORT_FILE"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        return
    fi

    # Run Python test
    if python3 "$test_file" >> "$REPORT_FILE" 2>&1; then
        echo -e "${GREEN}[PASS]${NC} $test_name" | tee -a "$REPORT_FILE"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}[FAIL]${NC} $test_name" | tee -a "$REPORT_FILE"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    echo "" | tee -a "$REPORT_FILE"
}

echo "=======================================" | tee -a "$REPORT_FILE"
echo "Phase 1: Configuration & Infrastructure" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Test 1: Configuration Loading
run_python_test "Configuration Loader" "$TESTS_DIR/test_config.py"

# Test 2: Kubernetes Connectivity
run_test_suite "Kubernetes Connectivity" "$TESTS_DIR/test_kubernetes.sh"

echo "=======================================" | tee -a "$REPORT_FILE"
echo "Phase 2: Training Infrastructure" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Test 3: Training Infrastructure
run_test_suite "Training Infrastructure" "$TESTS_DIR/test_training.sh"

# Test 4: MLflow Integration
run_python_test "MLflow Integration" "$TESTS_DIR/test_mlflow.py"

echo "=======================================" | tee -a "$REPORT_FILE"
echo "Phase 3: Model Serving" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Test 5: Model Serving
run_test_suite "Model Serving" "$TESTS_DIR/test_serving.sh"

# Test 6: Auto-scaling
run_test_suite "Auto-scaling Configuration" "$TESTS_DIR/test_autoscaling.sh"

echo "=======================================" | tee -a "$REPORT_FILE"
echo "Phase 4: Monitoring & Observability" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Test 7: Monitoring
run_test_suite "Monitoring Infrastructure" "$TESTS_DIR/test_monitoring.sh"

# Test 8: Security
run_test_suite "Security Configuration" "$TESTS_DIR/test_security.sh"

echo "=======================================" | tee -a "$REPORT_FILE"
echo "Integration Tests" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Test 9: End-to-End Integration
run_python_test "Integration Tests" "$TESTS_DIR/integration/test_phase1_smoke.py"

echo "=======================================" | tee -a "$REPORT_FILE"
echo "Code Quality & Hardcoding Audit" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Test 10: Hardcoding Audit
run_test_suite "Hardcoding Audit" "$TESTS_DIR/test_hardcoding_audit.sh"

# Test Summary
echo "" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "Test Summary" | tee -a "$REPORT_FILE"
echo "=======================================" | tee -a "$REPORT_FILE"
echo "Total Tests:   $TOTAL_TESTS" | tee -a "$REPORT_FILE"
echo -e "${GREEN}Passed:        $PASSED_TESTS${NC}" | tee -a "$REPORT_FILE"
echo -e "${RED}Failed:        $FAILED_TESTS${NC}" | tee -a "$REPORT_FILE"
echo -e "${YELLOW}Skipped:       $SKIPPED_TESTS${NC}" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Calculate success rate
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Success Rate:  $SUCCESS_RATE%" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"
echo "Report saved to: $REPORT_FILE" | tee -a "$REPORT_FILE"

# Exit with appropriate code
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
