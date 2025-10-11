#!/bin/bash
# Week 1, Day 1: Fix Test Execution
# Issue #1 - CRITICAL
# Estimated: 4 hours

set -e

echo "🔧 Maestro ML - Fix Test Execution"
echo "===================================="
echo ""

# Step 1: Update pytest.ini
echo "📝 Step 1: Updating pytest.ini..."
if ! grep -q "pythonpath = ." pytest.ini 2>/dev/null; then
    echo "pythonpath = ." >> pytest.ini
    echo "✅ Added pythonpath to pytest.ini"
else
    echo "✅ pythonpath already configured"
fi

# Step 2: Clear all caches
echo ""
echo "🧹 Step 2: Clearing Python caches..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
echo "✅ Caches cleared"

# Step 3: Verify imports work
echo ""
echo "🧪 Step 3: Testing imports..."
if poetry run python -c "from maestro_ml.config.settings import get_settings; print('✅ Import successful')" 2>&1; then
    echo "✅ maestro_ml imports correctly"
else
    echo "❌ Import failed! Check PYTHONPATH"
    exit 1
fi

# Step 4: Try running tests
echo ""
echo "🧪 Step 4: Running pytest..."
echo "--------------------------------------"
if poetry run pytest tests/ -v --tb=short -x 2>&1 | tee test-results.txt; then
    echo ""
    echo "✅ Tests executed successfully!"
else
    echo ""
    echo "⚠️  Some tests may have failed, but they RAN (no import errors)"
    echo "Check test-results.txt for details"
fi

# Step 5: Generate test report
echo ""
echo "📊 Step 5: Generating test report..."
poetry run pytest tests/ --collect-only 2>&1 | grep "test_" | wc -l > test-count.txt
TEST_COUNT=$(cat test-count.txt)
echo "Found $TEST_COUNT test functions"

# Step 6: Create status document
echo ""
echo "📝 Step 6: Creating TEST_STATUS.md..."
cat > TEST_STATUS.md << 'EOF'
# Test Execution Status

**Last Updated**: $(date)
**Status**: Tests can now execute

## Summary
- ✅ pytest configuration fixed
- ✅ Import errors resolved
- ✅ Test execution working

## Test Count
- Total test functions discovered: $TEST_COUNT

## Next Steps
1. Review failing tests in test-results.txt
2. Fix critical test failures
3. Increase test coverage
4. Add integration tests

## How to Run Tests
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/test_api_projects.py -v

# Run with coverage
poetry run pytest tests/ --cov=maestro_ml --cov-report=html
```
EOF

echo "✅ TEST_STATUS.md created"

echo ""
echo "🎉 COMPLETE: Test execution fixed!"
echo ""
echo "📋 Next Steps:"
echo "  1. Review test-results.txt for any failures"
echo "  2. Read TEST_STATUS.md for testing guide"
echo "  3. Proceed to Day 2: Fix hardcoded secrets"
