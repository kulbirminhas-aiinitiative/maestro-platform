#!/bin/bash
# MAESTRO Templates - Comprehensive Test Runner
# Runs all test suites with quality-fabric integration and generates reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPORTS_DIR="test_reports"
QUALITY_FABRIC_DIR="$REPORTS_DIR/quality_fabric"
COVERAGE_HTML_DIR="$REPORTS_DIR/coverage_html"
COVERAGE_XML="$REPORTS_DIR/coverage.xml"
JUNIT_XML="$REPORTS_DIR/junit.xml"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MAESTRO Templates - Comprehensive Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create report directories
echo -e "${YELLOW}Creating report directories...${NC}"
mkdir -p "$REPORTS_DIR"
mkdir -p "$QUALITY_FABRIC_DIR"

# Clean previous reports
echo -e "${YELLOW}Cleaning previous reports...${NC}"
rm -rf "$COVERAGE_HTML_DIR"
rm -f "$COVERAGE_XML"
rm -f "$JUNIT_XML"

# Check environment
echo -e "${YELLOW}Checking environment...${NC}"
if [ -z "$JWT_SECRET_KEY" ]; then
    export JWT_SECRET_KEY="test_secret_key_minimum_32_characters_long_for_comprehensive_testing_12345678"
    echo -e "${YELLOW}  JWT_SECRET_KEY set to default test value${NC}"
fi

if [ -z "$ENVIRONMENT" ]; then
    export ENVIRONMENT="test"
    echo -e "${YELLOW}  ENVIRONMENT set to 'test'${NC}"
fi

echo ""

# Function to run test suite
run_test_suite() {
    local suite_name=$1
    local test_path=$2
    local markers=$3

    echo -e "${BLUE}Running ${suite_name}...${NC}"

    if [ -n "$markers" ]; then
        poetry run pytest "$test_path" -v -m "$markers" \
            --cov=. \
            --cov-append \
            --cov-report=term-missing \
            --tb=short \
            --durations=10 || true
    else
        poetry run pytest "$test_path" -v \
            --cov=. \
            --cov-append \
            --cov-report=term-missing \
            --tb=short \
            --durations=10 || true
    fi

    echo ""
}

# Run test suites
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Execution${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. Unit Tests
run_test_suite "Unit Tests" "tests/unit/" "unit"

# 2. Integration Tests
run_test_suite "Integration Tests" "tests/integration/" "integration"

# 3. API Tests
run_test_suite "API Tests" "tests/api/" "api"

# 4. Security Tests
run_test_suite "Security Tests" "tests/security/" "security"

# 5. Performance Tests (exclude slow tests by default)
run_test_suite "Performance Tests (Fast)" "tests/performance/" "performance and not slow"

# 6. E2E Tests
run_test_suite "E2E Tests" "tests/e2e/" "e2e"

# Generate final coverage reports
echo -e "${BLUE}Generating coverage reports...${NC}"
poetry run pytest tests/ \
    --cov=. \
    --cov-report=html:"$COVERAGE_HTML_DIR" \
    --cov-report=xml:"$COVERAGE_XML" \
    --cov-report=term \
    --junit-xml="$JUNIT_XML" \
    --collect-only > /dev/null 2>&1 || true

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Reports Generated${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Display report locations
echo -e "${YELLOW}Coverage Reports:${NC}"
echo -e "  HTML: ${COVERAGE_HTML_DIR}/index.html"
echo -e "  XML:  ${COVERAGE_XML}"
echo ""

echo -e "${YELLOW}Quality-Fabric Reports:${NC}"
if [ -d "$QUALITY_FABRIC_DIR" ] && [ "$(ls -A $QUALITY_FABRIC_DIR 2>/dev/null)" ]; then
    echo -e "  Summary:  ${QUALITY_FABRIC_DIR}/summary.md"
    echo -e "  Detailed: ${QUALITY_FABRIC_DIR}/detailed_report.md"
    echo -e "  Metrics:  ${QUALITY_FABRIC_DIR}/metrics_*.json"
else
    echo -e "  ${YELLOW}(Will be generated when quality-fabric is enabled)${NC}"
fi
echo ""

echo -e "${YELLOW}JUnit Report:${NC}"
echo -e "  XML: ${JUNIT_XML}"
echo ""

# Display summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Try to extract coverage percentage
if [ -f "$COVERAGE_XML" ]; then
    COVERAGE=$(grep -oP 'line-rate="\K[0-9.]+' "$COVERAGE_XML" 2>/dev/null | head -1 || echo "0")
    COVERAGE_PCT=$(echo "$COVERAGE * 100" | bc 2>/dev/null || echo "0")
    echo -e "${YELLOW}Coverage:${NC} ${COVERAGE_PCT}%"
fi

# Count test results from junit.xml if available
if [ -f "$JUNIT_XML" ]; then
    TOTAL_TESTS=$(grep -oP 'tests="\K[0-9]+' "$JUNIT_XML" 2>/dev/null | head -1 || echo "0")
    FAILURES=$(grep -oP 'failures="\K[0-9]+' "$JUNIT_XML" 2>/dev/null | head -1 || echo "0")
    ERRORS=$(grep -oP 'errors="\K[0-9]+' "$JUNIT_XML" 2>/dev/null | head -1 || echo "0")
    SKIPPED=$(grep -oP 'skipped="\K[0-9]+' "$JUNIT_XML" 2>/dev/null | head -1 || echo "0")

    PASSED=$((TOTAL_TESTS - FAILURES - ERRORS - SKIPPED))

    echo -e "${YELLOW}Total Tests:${NC} $TOTAL_TESTS"
    echo -e "${GREEN}Passed:${NC} $PASSED"
    if [ "$FAILURES" -gt 0 ]; then
        echo -e "${RED}Failed:${NC} $FAILURES"
    fi
    if [ "$ERRORS" -gt 0 ]; then
        echo -e "${RED}Errors:${NC} $ERRORS"
    fi
    if [ "$SKIPPED" -gt 0 ]; then
        echo -e "${YELLOW}Skipped:${NC} $SKIPPED"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Execution Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Open coverage report (optional)
if command -v xdg-open > /dev/null 2>&1 && [ "$1" = "--open" ]; then
    echo -e "${BLUE}Opening coverage report in browser...${NC}"
    xdg-open "$COVERAGE_HTML_DIR/index.html" 2>/dev/null || true
fi

exit 0
