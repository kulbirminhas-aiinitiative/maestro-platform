#!/bin/bash
# MD-2043 Trimodal Convergence - Verification Script
# Run this before and after making changes to tri_audit/

echo "=================================="
echo "MD-2043 Verification Script"
echo "=================================="

cd /home/ec2-user/projects/maestro-platform/maestro-hive

echo ""
echo "1. Checking file modifications..."
echo "-----------------------------------"

# Check if real loaders are in place (not stubs)
if grep -q "metrics_file = Path" tri_audit/tri_audit.py; then
    echo "  [OK] load_dde_audit() - Real loader present"
else
    echo "  [FAIL] load_dde_audit() - May have been reverted to stub!"
fi

if grep -q "possible_paths = \[" tri_audit/tri_audit.py; then
    echo "  [OK] load_bdv_audit() - Real loader present"
else
    echo "  [FAIL] load_bdv_audit() - May have been reverted to stub!"
fi

if grep -q "reports/acc" tri_audit/tri_audit.py; then
    echo "  [OK] load_acc_audit() - Real loader present"
else
    echo "  [FAIL] load_acc_audit() - May have been reverted to stub!"
fi

echo ""
echo "2. Running unit tests..."
echo "-----------------------------------"

python -m pytest tests/tri_audit/test_truth_table.py -v --tb=short 2>&1 | tail -20

echo ""
echo "3. Running data loader tests..."
echo "-----------------------------------"

python -m pytest tests/tri_audit/test_data_loaders.py -v --tb=short 2>&1 | tail -20

echo ""
echo "4. Quick functional test..."
echo "-----------------------------------"

python -c "
from tri_audit.tri_audit import load_dde_audit, load_bdv_audit, load_acc_audit

test_id = 'sdlc_90d46aa4_20251201_171107'
dde = load_dde_audit(test_id)
bdv = load_bdv_audit(test_id)
acc = load_acc_audit(test_id)

print(f'DDE loaded: {dde is not None}')
print(f'BDV loaded: {bdv is not None}')
print(f'ACC loaded: {acc is not None}')

if dde and bdv and acc:
    print('[OK] All loaders working correctly')
else:
    print('[WARN] Some loaders returned None (data may not exist for test ID)')
"

echo ""
echo "=================================="
echo "Verification Complete"
echo "=================================="
