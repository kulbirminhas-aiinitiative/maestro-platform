#!/bin/bash
# Load Testing Execution Script for Maestro ML Platform
#
# Usage:
#   ./run_load_tests.sh [test_type] [target_url]
#
# Test types: baseline, stress, spike, endurance, all
#
# Example:
#   ./run_load_tests.sh baseline http://localhost:8000
#   ./run_load_tests.sh all https://api.maestro-ml.com

set -e

# Configuration
TEST_TYPE="${1:-baseline}"
TARGET_URL="${2:-http://localhost:8000}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="./load_test_results_${TIMESTAMP}"

# Colors
GREEN='\033[0.32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Maestro ML Load Testing Suite${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Target: $TARGET_URL"
echo "Test Type: $TEST_TYPE"
echo "Results Directory: $RESULTS_DIR"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# ============================================================================
# Pre-flight Checks
# ============================================================================

echo -e "${YELLOW}Running pre-flight checks...${NC}"

# Check if target is accessible
if ! curl -s -o /dev/null -w "%{http_code}" "$TARGET_URL/health" | grep -q "200"; then
    echo -e "${RED}ERROR: Target URL $TARGET_URL/health is not accessible${NC}"
    exit 1
fi

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo -e "${RED}ERROR: Locust is not installed${NC}"
    echo "Install with: pip install locust"
    exit 1
fi

# Check if required Python packages are available
python3 -c "import httpx, psutil" 2>/dev/null || {
    echo -e "${RED}ERROR: Required Python packages not found${NC}"
    echo "Install with: pip install httpx psutil"
    exit 1
}

echo -e "${GREEN}✓ Pre-flight checks passed${NC}"
echo ""

# ============================================================================
# Test Functions
# ============================================================================

run_baseline_test() {
    echo -e "${YELLOW}Running Baseline Test (50 users, 10 min)...${NC}"

    locust -f ../security_testing/load_testing.py \
        --host="$TARGET_URL" \
        --users 50 \
        --spawn-rate 10 \
        --run-time 10m \
        --headless \
        --html "$RESULTS_DIR/baseline_report.html" \
        --csv "$RESULTS_DIR/baseline" \
        --loglevel INFO

    echo -e "${GREEN}✓ Baseline test complete${NC}"
}

run_stress_test() {
    echo -e "${YELLOW}Running Stress Test (1000 users, 30 min)...${NC}"

    locust -f ../security_testing/load_testing.py \
        --host="$TARGET_URL" \
        --users 1000 \
        --spawn-rate 50 \
        --run-time 30m \
        --headless \
        --html "$RESULTS_DIR/stress_report.html" \
        --csv "$RESULTS_DIR/stress" \
        --loglevel INFO

    echo -e "${GREEN}✓ Stress test complete${NC}"
}

run_spike_test() {
    echo -e "${YELLOW}Running Spike Test (500 users, rapid ramp)...${NC}"

    locust -f ../security_testing/load_testing.py \
        --host="$TARGET_URL" \
        --users 500 \
        --spawn-rate 100 \
        --run-time 5m \
        --headless \
        --html "$RESULTS_DIR/spike_report.html" \
        --csv "$RESULTS_DIR/spike" \
        --loglevel INFO

    echo -e "${GREEN}✓ Spike test complete${NC}"
}

run_endurance_test() {
    echo -e "${YELLOW}Running Endurance Test (200 users, 60 min)...${NC}"

    locust -f ../security_testing/load_testing.py \
        --host="$TARGET_URL" \
        --users 200 \
        --spawn-rate 20 \
        --run-time 60m \
        --headless \
        --html "$RESULTS_DIR/endurance_report.html" \
        --csv "$RESULTS_DIR/endurance" \
        --loglevel INFO

    echo -e "${GREEN}✓ Endurance test complete${NC}"
}

run_rate_limit_test() {
    echo -e "${YELLOW}Running Rate Limit Test...${NC}"

    locust -f ../security_testing/load_testing.py \
        --host="$TARGET_URL" \
        --users 100 \
        --spawn-rate 20 \
        --run-time 5m \
        --headless \
        --html "$RESULTS_DIR/ratelimit_report.html" \
        --csv "$RESULTS_DIR/ratelimit" \
        RateLimitTestUser \
        --loglevel INFO

    echo -e "${GREEN}✓ Rate limit test complete${NC}"
}

run_tenant_isolation_test() {
    echo -e "${YELLOW}Running Tenant Isolation Test...${NC}"

    locust -f ../security_testing/load_testing.py \
        --host="$TARGET_URL" \
        --users 50 \
        --spawn-rate 10 \
        --run-time 10m \
        --headless \
        --html "$RESULTS_DIR/tenant_isolation_report.html" \
        --csv "$RESULTS_DIR/tenant_isolation" \
        TenantIsolationTestUser \
        --loglevel INFO

    echo -e "${GREEN}✓ Tenant isolation test complete${NC}"
}

# ============================================================================
# Performance Analysis
# ============================================================================

analyze_results() {
    echo ""
    echo -e "${YELLOW}Analyzing results...${NC}"

    python3 << EOF
import pandas as pd
import json
from pathlib import Path

results_dir = Path("$RESULTS_DIR")

# Analyze CSV results
for csv_file in results_dir.glob("*_stats.csv"):
    print(f"\n{'='*60}")
    print(f"Analysis: {csv_file.stem}")
    print('='*60)

    df = pd.read_csv(csv_file)

    # Calculate key metrics
    total_requests = df['Request Count'].sum()
    failed_requests = df['Failure Count'].sum()
    error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

    avg_response = df['Average Response Time'].mean()
    p95_response = df['95%'].mean()
    p99_response = df['99%'].mean()

    rps = df['Requests/s'].mean()

    print(f"Total Requests: {total_requests:,.0f}")
    print(f"Failed Requests: {failed_requests:,.0f}")
    print(f"Error Rate: {error_rate:.2f}%")
    print(f"Average Response Time: {avg_response:.0f}ms")
    print(f"P95 Response Time: {p95_response:.0f}ms")
    print(f"P99 Response Time: {p99_response:.0f}ms")
    print(f"Requests/Second: {rps:.1f}")

    # Check SLO compliance
    print("\nSLO Compliance:")
    print(f"  P95 < 500ms: {'✓ PASS' if p95_response < 500 else '✗ FAIL'}")
    print(f"  P99 < 1000ms: {'✓ PASS' if p99_response < 1000 else '✗ FAIL'}")
    print(f"  Error Rate < 0.1%: {'✓ PASS' if error_rate < 0.1 else '✗ FAIL'}")

    # Save summary
    summary = {
        "total_requests": int(total_requests),
        "failed_requests": int(failed_requests),
        "error_rate": float(error_rate),
        "avg_response_time_ms": float(avg_response),
        "p95_response_time_ms": float(p95_response),
        "p99_response_time_ms": float(p99_response),
        "requests_per_second": float(rps),
        "slo_compliance": {
            "p95_under_500ms": p95_response < 500,
            "p99_under_1000ms": p99_response < 1000,
            "error_rate_under_0_1": error_rate < 0.1
        }
    }

    summary_file = csv_file.parent / f"{csv_file.stem}_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

print("\n✓ Analysis complete")
EOF

    echo -e "${GREEN}✓ Analysis complete${NC}"
}

# ============================================================================
# Main Execution
# ============================================================================

case "$TEST_TYPE" in
    baseline)
        run_baseline_test
        ;;
    stress)
        run_stress_test
        ;;
    spike)
        run_spike_test
        ;;
    endurance)
        run_endurance_test
        ;;
    ratelimit)
        run_rate_limit_test
        ;;
    tenant)
        run_tenant_isolation_test
        ;;
    all)
        echo -e "${YELLOW}Running complete test suite...${NC}"
        run_baseline_test
        sleep 30
        run_stress_test
        sleep 30
        run_spike_test
        sleep 30
        run_rate_limit_test
        sleep 30
        run_tenant_isolation_test
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Valid types: baseline, stress, spike, endurance, ratelimit, tenant, all"
        exit 1
        ;;
esac

# Analyze results
analyze_results

# ============================================================================
# Summary Report
# ============================================================================

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Load Testing Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "HTML Reports:"
ls -1 "$RESULTS_DIR"/*.html 2>/dev/null | while read file; do
    echo "  - $(basename $file)"
done
echo ""
echo "Summary Files:"
ls -1 "$RESULTS_DIR"/*_summary.json 2>/dev/null | while read file; do
    echo "  - $(basename $file)"
done
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review HTML reports in $RESULTS_DIR"
echo "2. Check summary JSON files for SLO compliance"
echo "3. Compare with previous test runs"
echo "4. Optimize any endpoints with P95 > 500ms"
echo ""

# Open HTML report if running on desktop
if [[ -n "$DISPLAY" ]] && command -v xdg-open &> /dev/null; then
    echo "Opening baseline report..."
    xdg-open "$RESULTS_DIR/baseline_report.html" 2>/dev/null &
fi

echo -e "${GREEN}Done!${NC}"
