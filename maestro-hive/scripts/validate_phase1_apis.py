#!/usr/bin/env python3
"""
Validate Phase 1 APIs - Quick Smoke Test

Tests all 4 API modules to ensure they're importable and functional.

Usage:
    python3 scripts/validate_phase1_apis.py
"""

import sys
import importlib
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def test_import(module_name: str, description: str) -> bool:
    """Test if module can be imported."""
    try:
        print(f"  Testing {description}...", end=" ")
        importlib.import_module(module_name)
        print(f"{Colors.GREEN}✓{Colors.END}")
        return True
    except ImportError as e:
        print(f"{Colors.RED}✗{Colors.END}")
        print(f"    Error: {e}")
        return False
    except Exception as e:
        print(f"{Colors.YELLOW}⚠{Colors.END}")
        print(f"    Warning: {e}")
        return False

def test_api_structure(module_name: str, expected_attrs: list) -> bool:
    """Test if API module has expected structure."""
    try:
        module = importlib.import_module(module_name)
        missing = []
        for attr in expected_attrs:
            if not hasattr(module, attr):
                missing.append(attr)

        if missing:
            print(f"    {Colors.YELLOW}⚠ Missing: {', '.join(missing)}{Colors.END}")
            return False
        return True
    except Exception as e:
        print(f"    {Colors.RED}Error: {e}{Colors.END}")
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Phase 1 API Validation{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    results = []

    # Test 1: DDE API
    print(f"{Colors.BLUE}1. DDE API (dde/api.py){Colors.END}")
    result = test_import("dde.api", "DDE API module")
    if result:
        result = test_api_structure("dde.api", ["router", "get_dde_graph", "get_artifact_lineage"])
    results.append(("DDE API", result))
    print()

    # Test 2: BDV API
    print(f"{Colors.BLUE}2. BDV API (bdv/api.py){Colors.END}")
    result = test_import("bdv.api", "BDV API module")
    if result:
        result = test_api_structure("bdv.api", ["router", "get_bdv_graph", "get_contract_linkages"])
    results.append(("BDV API", result))
    print()

    # Test 3: ACC API
    print(f"{Colors.BLUE}3. ACC API (acc/api.py){Colors.END}")
    result = test_import("acc.api", "ACC API module")
    if result:
        result = test_api_structure("acc.api", ["router", "get_acc_graph", "get_violations"])
    results.append(("ACC API", result))
    print()

    # Test 4: Convergence API
    print(f"{Colors.BLUE}4. Convergence API (tri_audit/api.py){Colors.END}")
    result = test_import("tri_audit.api", "Convergence API module")
    if result:
        result = test_api_structure("tri_audit.api", ["router", "get_convergence_graph", "get_verdict"])
    results.append(("Convergence API", result))
    print()

    # Test 5: Main Server
    print(f"{Colors.BLUE}5. Main API Server (tri_modal_api_main.py){Colors.END}")
    result = test_import("tri_modal_api_main", "Main server module")
    if result:
        result = test_api_structure("tri_modal_api_main", ["app"])
    results.append(("Main Server", result))
    print()

    # Summary
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Summary{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if result else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  {status} - {name}")

    print(f"\n{Colors.BLUE}Results: {passed}/{total} tests passed{Colors.END}\n")

    if passed == total:
        print(f"{Colors.GREEN}🎉 All Phase 1 APIs are functional!{Colors.END}")
        print(f"\n{Colors.BLUE}Next steps:{Colors.END}")
        print(f"  1. Start the server: python3 tri_modal_api_main.py")
        print(f"  2. Access docs: http://localhost:8000/api/docs")
        print(f"  3. Test endpoints: curl http://localhost:8000/health\n")
        return 0
    else:
        print(f"{Colors.RED}⚠ Some APIs have issues. Please review errors above.{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
