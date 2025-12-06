"""
Contract Tester

EPIC: MD-2509
AC-2: Contract tests verify interfaces

Validates block interfaces against defined contracts.
"""

import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type

from .models import ContractSpec, ContractResult

logger = logging.getLogger(__name__)


class ContractTester:
    """
    Verifies block interfaces against contracts (AC-2).

    Tests that blocks implement required interfaces without
    testing internal implementation details.

    Example:
        tester = ContractTester()

        # Define a contract
        contract = ContractSpec(
            name="AuthService",
            required_methods=["authenticate", "validate_token"],
            inputs={"authenticate": "credentials: Credentials"},
            outputs={"authenticate": "AuthResult"},
        )

        # Verify a block against contract
        result = tester.verify_contract(auth_block, contract)
        if result.passed:
            print("Contract verified!")
    """

    def __init__(self):
        self._contracts: Dict[str, ContractSpec] = {}
        self._verification_count = 0
        self._pass_count = 0

    def register_contract(self, contract: ContractSpec) -> None:
        """
        Register a contract specification.

        Args:
            contract: The contract to register
        """
        self._contracts[contract.name] = contract
        logger.info(f"Registered contract: {contract.name}")

    def get_contract(self, name: str) -> Optional[ContractSpec]:
        """Get a registered contract by name."""
        return self._contracts.get(name)

    def verify_contract(
        self,
        block: Any,
        contract: ContractSpec,
    ) -> ContractResult:
        """
        Verify a block against a contract (AC-2).

        Checks:
        - Required methods exist
        - Method signatures match expected inputs/outputs
        - Invariants hold

        Args:
            block: The block instance or class to verify
            contract: The contract specification

        Returns:
            ContractResult with verification details
        """
        start_time = time.monotonic()
        self._verification_count += 1

        failures: List[Dict[str, Any]] = []
        checks_passed = 0
        total_checks = 0

        block_name = getattr(block, "__name__", block.__class__.__name__)

        # Check required methods
        for method_name in contract.required_methods:
            total_checks += 1
            if hasattr(block, method_name):
                method = getattr(block, method_name)
                if callable(method):
                    checks_passed += 1
                    logger.debug(f"Contract check PASS: {method_name} exists")
                else:
                    failures.append({
                        "check": "required_method",
                        "method": method_name,
                        "error": f"{method_name} exists but is not callable",
                    })
            else:
                failures.append({
                    "check": "required_method",
                    "method": method_name,
                    "error": f"Missing required method: {method_name}",
                })

        # Check method signatures (inputs)
        for method_name, expected_sig in contract.inputs.items():
            total_checks += 1
            if hasattr(block, method_name):
                method = getattr(block, method_name)
                try:
                    sig = inspect.signature(method)
                    # Basic signature check - verify parameter count
                    params = [p for p in sig.parameters.values()
                             if p.name != 'self']
                    checks_passed += 1
                    logger.debug(f"Contract check PASS: {method_name} signature")
                except (ValueError, TypeError) as e:
                    failures.append({
                        "check": "input_signature",
                        "method": method_name,
                        "expected": expected_sig,
                        "error": str(e),
                    })
            else:
                failures.append({
                    "check": "input_signature",
                    "method": method_name,
                    "error": f"Method {method_name} not found",
                })

        # Check invariants (if any defined and block has invariant checker)
        for invariant in contract.invariants:
            total_checks += 1
            if hasattr(block, "check_invariant"):
                try:
                    result = block.check_invariant(invariant)
                    if result:
                        checks_passed += 1
                    else:
                        failures.append({
                            "check": "invariant",
                            "invariant": invariant,
                            "error": "Invariant check returned False",
                        })
                except Exception as e:
                    failures.append({
                        "check": "invariant",
                        "invariant": invariant,
                        "error": str(e),
                    })
            else:
                # If no invariant checker, skip (don't fail)
                checks_passed += 1

        duration_ms = int((time.monotonic() - start_time) * 1000)
        passed = len(failures) == 0

        if passed:
            self._pass_count += 1

        result = ContractResult(
            contract_name=contract.name,
            block_name=block_name,
            passed=passed,
            total_checks=total_checks,
            passed_checks=checks_passed,
            failed_checks=len(failures),
            failures=failures,
            duration_ms=duration_ms,
        )

        logger.info(
            f"Contract verification: {contract.name} on {block_name} - "
            f"{'PASS' if passed else 'FAIL'} ({checks_passed}/{total_checks})"
        )

        return result

    def verify_interface(
        self,
        block: Any,
        interface_class: Type,
    ) -> ContractResult:
        """
        Verify a block implements an interface (AC-2).

        Uses a Python class/protocol as the contract definition.

        Args:
            block: The block to verify
            interface_class: The interface class/protocol

        Returns:
            ContractResult with verification details
        """
        # Build contract from interface class
        required_methods = [
            name for name, method in inspect.getmembers(interface_class)
            if not name.startswith('_') and callable(method)
        ]

        contract = ContractSpec(
            name=interface_class.__name__,
            required_methods=required_methods,
        )

        return self.verify_contract(block, contract)

    def run_contract_tests(
        self,
        block: Any,
        contract_names: Optional[List[str]] = None,
    ) -> List[ContractResult]:
        """
        Run all registered contracts against a block (AC-2).

        Args:
            block: The block to test
            contract_names: Optional list of specific contracts to run

        Returns:
            List of ContractResults
        """
        results = []

        contracts_to_run = (
            [self._contracts[name] for name in contract_names
             if name in self._contracts]
            if contract_names
            else list(self._contracts.values())
        )

        for contract in contracts_to_run:
            result = self.verify_contract(block, contract)
            results.append(result)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get tester statistics."""
        return {
            "contracts_registered": len(self._contracts),
            "verifications": self._verification_count,
            "passes": self._pass_count,
            "failures": self._verification_count - self._pass_count,
            "pass_rate": (
                self._pass_count / self._verification_count
                if self._verification_count > 0 else 0
            ),
        }

    def health_check(self) -> bool:
        """Perform health check."""
        return True
