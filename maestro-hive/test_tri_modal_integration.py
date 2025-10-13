#!/usr/bin/env python3
"""
Integration Test for Tri-Modal Mission Control APIs

Tests all 4 API modules to ensure they integrate correctly with the main server
and return expected data structures.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dde.api import get_dde_graph, get_artifact_lineage, get_contract_points
from bdv.api import get_bdv_graph, get_contract_linkages, get_flake_report
from acc.api import get_acc_graph, get_violations, get_cycles
from tri_audit.api import get_convergence_graph, get_verdict, get_contract_stars


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


async def test_dde_api():
    """Test DDE API endpoints."""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}Testing DDE API{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

    try:
        # Test get_dde_graph
        print(f"  Testing get_dde_graph...", end=" ")
        result = await get_dde_graph(
            iteration_id="test-iteration-001",
            show_retries=True,
            include_metrics=True
        )
        assert result is not None
        assert "nodes" in result
        assert "edges" in result
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - Found {len(result['nodes'])} nodes")
        print(f"    - Found {len(result['edges'])} edges")

        # Test get_artifact_lineage
        print(f"  Testing get_artifact_lineage...", end=" ")
        result = await get_artifact_lineage(
            artifact_id="requirements_doc",
            iteration_id="test-iteration-001"
        )
        assert result is not None
        print(f"{Colors.GREEN}✓{Colors.END}")

        # Test get_contract_points
        print(f"  Testing get_contract_points...", end=" ")
        result = await get_contract_points(iteration_id="test-iteration-001")
        assert result is not None
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - Found {len(result)} contract points")

        return True
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.END}")
        print(f"    Error: {e}")
        return False


async def test_bdv_api():
    """Test BDV API endpoints."""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}Testing BDV API{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

    try:
        # Test get_bdv_graph
        print(f"  Testing get_bdv_graph...", end=" ")
        result = await get_bdv_graph(
            iteration_id="test-iteration-001",
            show_flakes=True,
            include_coverage=True
        )
        assert result is not None
        assert "nodes" in result
        assert "edges" in result
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - Found {len(result['nodes'])} nodes")
        print(f"    - Found {len(result['edges'])} edges")

        # Test get_contract_linkages
        print(f"  Testing get_contract_linkages...", end=" ")
        result = await get_contract_linkages(
            contract_id="AuthAPI:v1.0",
            iteration_id="test-iteration-001"
        )
        assert result is not None
        print(f"{Colors.GREEN}✓{Colors.END}")

        # Test get_flake_report
        print(f"  Testing get_flake_report...", end=" ")
        result = await get_flake_report(
            iteration_id="test-iteration-001",
            min_flake_rate=0.1
        )
        assert result is not None
        print(f"{Colors.GREEN}✓{Colors.END}")

        return True
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.END}")
        print(f"    Error: {e}")
        return False


async def test_acc_api():
    """Test ACC API endpoints."""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}Testing ACC API{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

    try:
        # Test get_acc_graph
        print(f"  Testing get_acc_graph...", end=" ")
        result = await get_acc_graph(
            iteration_id="test-iteration-001",
            show_violations=True,
            layout="hierarchical"
        )
        assert result is not None
        assert "nodes" in result
        assert "edges" in result
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - Found {len(result['nodes'])} nodes")
        print(f"    - Found {len(result['edges'])} edges")

        # Test get_violations
        print(f"  Testing get_violations...", end=" ")
        result = await get_violations(
            iteration_id="test-iteration-001",
            severity="BLOCKING"
        )
        assert result is not None
        print(f"{Colors.GREEN}✓{Colors.END}")

        # Test get_cycles
        print(f"  Testing get_cycles...", end=" ")
        result = await get_cycles(
            iteration_id="test-iteration-001",
            manifest_name="maestro.yaml"
        )
        assert result is not None
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - Found {len(result)} cycles")

        return True
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.END}")
        print(f"    Error: {e}")
        return False


async def test_convergence_api():
    """Test Convergence API endpoints."""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}Testing Convergence API{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

    try:
        # Test get_convergence_graph
        print(f"  Testing get_convergence_graph...", end=" ")
        result = await get_convergence_graph(
            iteration_id="test-iteration-001",
            highlight_contracts=True,
            show_confidence=True
        )
        assert result is not None
        assert "nodes" in result
        assert "edges" in result
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - Found {len(result['nodes'])} nodes")
        print(f"    - Found {len(result['edges'])} edges")

        # Test get_verdict
        print(f"  Testing get_verdict...", end=" ")
        result = await get_verdict(iteration_id="test-iteration-001")
        assert result is not None
        assert "dde_status" in result
        assert "bdv_status" in result
        assert "acc_status" in result
        assert "deployment_approved" in result
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - DDE Status: {result['dde_status']}")
        print(f"    - BDV Status: {result['bdv_status']}")
        print(f"    - ACC Status: {result['acc_status']}")
        print(f"    - Deployment: {Colors.GREEN if result['deployment_approved'] else Colors.RED}{result['deployment_approved']}{Colors.END}")

        # Test get_contract_stars
        print(f"  Testing get_contract_stars...", end=" ")
        result = await get_contract_stars(iteration_id="test-iteration-001")
        assert result is not None
        print(f"{Colors.GREEN}✓{Colors.END}")
        print(f"    - Found {len(result)} contract stars")

        return True
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.END}")
        print(f"    Error: {e}")
        return False


async def main():
    """Run all integration tests."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}Tri-Modal Mission Control - Integration Tests{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")

    results = []

    # Test all APIs
    results.append(("DDE API", await test_dde_api()))
    results.append(("BDV API", await test_bdv_api()))
    results.append(("ACC API", await test_acc_api()))
    results.append(("Convergence API", await test_convergence_api()))

    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}Test Summary{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if result else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  {status} - {name}")

    print(f"\n{Colors.BLUE}Results: {passed}/{total} API modules passed{Colors.END}\n")

    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All Tri-Modal APIs are functional!{Colors.END}")
        print(f"\n{Colors.BLUE}Phase 1 Status: {Colors.GREEN}✅ COMPLETE{Colors.END}")
        print(f"\n{Colors.BLUE}Next Steps:{Colors.END}")
        print(f"  1. {Colors.CYAN}Review:{Colors.END} Stakeholder review of architecture and documentation")
        print(f"  2. {Colors.CYAN}Approval:{Colors.END} Budget ($36K + $2.25K/month) and timeline (12 weeks)")
        print(f"  3. {Colors.CYAN}Sprint 1:{Colors.END} Event-driven foundation (Kafka, ICS, Neo4j)")
        print(f"\n{Colors.YELLOW}Documentation:{Colors.END}")
        print(f"  📖 README_TRIMODAL_VISUALIZATION.md - Project index")
        print(f"  📊 FINAL_PROJECT_STATUS.md - Executive summary")
        print(f"  🏗️  MISSION_CONTROL_ARCHITECTURE.md - Production architecture")
        print(f"  🚀 GRAPH_API_QUICK_START.md - Quick start guide\n")
        return 0
    else:
        print(f"{Colors.RED}⚠ Some APIs have issues. Please review errors above.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
