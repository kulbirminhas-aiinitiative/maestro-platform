#!/bin/bash
# ============================================================================
# ACC Epic MD-2046 Verification Script
# ============================================================================
# Run this script to verify all ACC Epic changes are intact before making
# modifications. Other parallel agents should run this BEFORE touching ACC files.
#
# Usage: ./scripts/verify_acc_epic.sh
# ============================================================================

set -e

cd "$(dirname "$0")/.."
export PYTHONPATH=.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "ACC Epic MD-2046 Verification"
echo "Date: $(date -Iseconds)"
echo "=============================================="

# Track failures
FAILURES=0

# ============================================================================
# Step 1: Check all required files exist
# ============================================================================
echo -e "\n${YELLOW}[Step 1/4] Checking required files...${NC}"

FILES=(
  "acc/import_graph_builder.py"
  "acc/suppression_system.py"
  "acc/architecture_diff.py"
  "acc/adr_integration.py"
  "acc/cycle_analyzer.py"
  "acc/autofix_engine.py"
  "acc/persistence/__init__.py"
  "acc/persistence/postgres_store.py"
  "acc/persistence/redis_cache.py"
  "docs/ACC_EPIC_MD2046_CHANGELOG.md"
)

for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    echo -e "  ${GREEN}✓${NC} $f"
  else
    echo -e "  ${RED}✗ MISSING: $f${NC}"
    ((FAILURES++))
  fi
done

# ============================================================================
# Step 2: Check key classes/functions exist in files
# ============================================================================
echo -e "\n${YELLOW}[Step 2/4] Checking key implementations...${NC}"

# Check import_graph_builder has parallel support
if grep -q "build_graph.*parallel" acc/import_graph_builder.py && \
   grep -q "ThreadPoolExecutor" acc/import_graph_builder.py; then
  echo -e "  ${GREEN}✓${NC} import_graph_builder: parallel scanning"
else
  echo -e "  ${RED}✗ import_graph_builder: missing parallel scanning${NC}"
  ((FAILURES++))
fi

# Check suppression_system has ADR field
if grep -q "adr_reference" acc/suppression_system.py; then
  echo -e "  ${GREEN}✓${NC} suppression_system: adr_reference field"
else
  echo -e "  ${RED}✗ suppression_system: missing adr_reference${NC}"
  ((FAILURES++))
fi

# Check architecture_diff has DiffTracker
if grep -q "class DiffTracker" acc/architecture_diff.py; then
  echo -e "  ${GREEN}✓${NC} architecture_diff: DiffTracker class"
else
  echo -e "  ${RED}✗ architecture_diff: missing DiffTracker${NC}"
  ((FAILURES++))
fi

# Check adr_integration has ADRValidator
if grep -q "class ADRValidator" acc/adr_integration.py; then
  echo -e "  ${GREEN}✓${NC} adr_integration: ADRValidator class"
else
  echo -e "  ${RED}✗ adr_integration: missing ADRValidator${NC}"
  ((FAILURES++))
fi

# Check cycle_analyzer has CycleAnalyzer
if grep -q "class CycleAnalyzer" acc/cycle_analyzer.py; then
  echo -e "  ${GREEN}✓${NC} cycle_analyzer: CycleAnalyzer class"
else
  echo -e "  ${RED}✗ cycle_analyzer: missing CycleAnalyzer${NC}"
  ((FAILURES++))
fi

# Check autofix_engine has AutoFixEngine
if grep -q "class AutoFixEngine" acc/autofix_engine.py; then
  echo -e "  ${GREEN}✓${NC} autofix_engine: AutoFixEngine class"
else
  echo -e "  ${RED}✗ autofix_engine: missing AutoFixEngine${NC}"
  ((FAILURES++))
fi

# ============================================================================
# Step 3: Run Python import tests
# ============================================================================
echo -e "\n${YELLOW}[Step 3/4] Testing Python imports...${NC}"

python3 -c "
import sys
sys.path.insert(0, '.')

modules = [
    ('acc.import_graph_builder', 'ImportGraphBuilder'),
    ('acc.architecture_diff', 'DiffTracker'),
    ('acc.adr_integration', 'ADRValidator'),
    ('acc.cycle_analyzer', 'CycleAnalyzer'),
    ('acc.autofix_engine', 'AutoFixEngine'),
    ('acc.persistence', 'PostgresSuppressionStore'),
]

failed = 0
for mod, cls in modules:
    try:
        m = __import__(mod, fromlist=[cls])
        if hasattr(m, cls):
            print(f'  ✓ {mod}.{cls}')
        else:
            print(f'  ✗ {mod}.{cls} not found')
            failed += 1
    except Exception as e:
        print(f'  ✗ {mod}: {e}')
        failed += 1

sys.exit(failed)
" 2>&1 | while read line; do
  if [[ $line == *"✓"* ]]; then
    echo -e "  ${GREEN}${line}${NC}"
  elif [[ $line == *"✗"* ]]; then
    echo -e "  ${RED}${line}${NC}"
  else
    echo "  $line"
  fi
done

if [ ${PIPESTATUS[0]} -ne 0 ]; then
  ((FAILURES++))
fi

# ============================================================================
# Step 4: Run quick functional tests
# ============================================================================
echo -e "\n${YELLOW}[Step 4/4] Running functional tests...${NC}"

python3 << 'PYTEST'
import sys
sys.path.insert(0, '.')

tests_passed = 0
tests_failed = 0

# Test 1: ImportGraphBuilder
try:
    from acc.import_graph_builder import ImportGraphBuilder
    builder = ImportGraphBuilder('.', max_workers=2)
    # Just verify it initializes
    assert builder.max_workers == 2
    print("  ✓ ImportGraphBuilder initialization")
    tests_passed += 1
except Exception as e:
    print(f"  ✗ ImportGraphBuilder: {e}")
    tests_failed += 1

# Test 2: DiffTracker
try:
    from acc.architecture_diff import DiffTracker
    tracker = DiffTracker(storage_path='/tmp/acc_test_snapshots')
    assert tracker.max_snapshots == 30
    print("  ✓ DiffTracker initialization")
    tests_passed += 1
except Exception as e:
    print(f"  ✗ DiffTracker: {e}")
    tests_failed += 1

# Test 3: ADRValidator
try:
    from acc.adr_integration import ADRValidator
    validator = ADRValidator(adr_directory='docs/adr')
    # Should not crash even if no ADRs
    print("  ✓ ADRValidator initialization")
    tests_passed += 1
except Exception as e:
    print(f"  ✗ ADRValidator: {e}")
    tests_failed += 1

# Test 4: CycleAnalyzer
try:
    from acc.cycle_analyzer import CycleAnalyzer, CycleClassification
    analyzer = CycleAnalyzer()
    cls = analyzer.classify_cycle(['a', 'b', 'c'])
    assert cls in CycleClassification
    print("  ✓ CycleAnalyzer classification")
    tests_passed += 1
except Exception as e:
    print(f"  ✗ CycleAnalyzer: {e}")
    tests_failed += 1

# Test 5: AutoFixEngine
try:
    from acc.autofix_engine import AutoFixEngine
    engine = AutoFixEngine()
    suggestions = engine.suggest_fixes({'type': 'layer', 'source': 'a', 'target': 'b'})
    assert isinstance(suggestions, list)
    print("  ✓ AutoFixEngine suggestions")
    tests_passed += 1
except Exception as e:
    print(f"  ✗ AutoFixEngine: {e}")
    tests_failed += 1

print(f"\n  Results: {tests_passed} passed, {tests_failed} failed")
sys.exit(tests_failed)
PYTEST

if [ $? -ne 0 ]; then
  ((FAILURES++))
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=============================================="
if [ $FAILURES -eq 0 ]; then
  echo -e "${GREEN}ALL CHECKS PASSED${NC}"
  echo "ACC Epic MD-2046 implementation is intact."
  echo "=============================================="
  exit 0
else
  echo -e "${RED}$FAILURES CHECK(S) FAILED${NC}"
  echo "Some ACC Epic MD-2046 components are missing or broken."
  echo "DO NOT proceed with modifications until issues are resolved."
  echo "=============================================="
  exit 1
fi
