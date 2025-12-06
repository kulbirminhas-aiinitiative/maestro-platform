"""
BDV Integration Service (MD-892)

Connects BDV validation with team_execution_v2.py.
Validates contracts through Gherkin feature tests.

Features:
- Auto-generate feature files from contracts
- Run BDV tests after artifact generation
- Collect test results and update quality scores
- Map scenario status to contract fulfillment

ML Integration Points:
- Test failure pattern recognition
- Quality prediction from test results
"""

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from bdv.bdv_runner import BDVRunner, BDVResult, ScenarioResult

logger = logging.getLogger(__name__)


@dataclass
class ContractTestMapping:
    """Maps contract to BDV test results"""
    contract_id: str
    contract_name: str
    feature_file: str
    scenarios: List[str]
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    @property
    def is_fulfilled(self) -> bool:
        return self.failed == 0 and self.passed > 0


@dataclass
class BDVValidationResult:
    """Result of BDV validation for an execution"""
    execution_id: str
    iteration_id: str
    total_contracts: int
    contracts_fulfilled: int
    total_scenarios: int
    scenarios_passed: int
    scenarios_failed: int
    overall_pass_rate: float
    contract_mappings: List[ContractTestMapping]
    bdv_result: Optional[BDVResult] = None
    validated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'iteration_id': self.iteration_id,
            'total_contracts': self.total_contracts,
            'contracts_fulfilled': self.contracts_fulfilled,
            'total_scenarios': self.total_scenarios,
            'scenarios_passed': self.scenarios_passed,
            'scenarios_failed': self.scenarios_failed,
            'overall_pass_rate': round(self.overall_pass_rate, 4),
            'contract_mappings': [
                {
                    'contract_id': m.contract_id,
                    'contract_name': m.contract_name,
                    'feature_file': m.feature_file,
                    'passed': m.passed,
                    'failed': m.failed,
                    'pass_rate': round(m.pass_rate, 4),
                    'is_fulfilled': m.is_fulfilled
                }
                for m in self.contract_mappings
            ],
            'validated_at': self.validated_at.isoformat()
        }


class BDVIntegrationService:
    """
    BDV Integration Service

    Connects BDV validation with the execution pipeline.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        features_path: str = "features/",
        generated_features_path: str = "features/generated/"
    ):
        """
        Initialize BDV integration service.

        Args:
            base_url: Base URL for API testing
            features_path: Path to feature files
            generated_features_path: Path for auto-generated features
        """
        self.base_url = base_url
        self.features_path = Path(features_path)
        self.generated_features_path = Path(generated_features_path)
        self.runner = BDVRunner(base_url, features_path)

        # Create directories
        self.features_path.mkdir(parents=True, exist_ok=True)
        self.generated_features_path.mkdir(parents=True, exist_ok=True)

        # Results storage
        self._validation_results: List[BDVValidationResult] = []

        logger.info("✅ BDVIntegrationService initialized")

    def validate_contracts(
        self,
        execution_id: str,
        contracts: List[Dict[str, Any]],
        iteration_id: Optional[str] = None,
        correlation_id: Optional[str] = None  # MD-2024: Correlation ID for logging
    ) -> BDVValidationResult:
        """
        Validate contracts through BDV tests.

        Args:
            execution_id: Execution identifier
            contracts: List of contracts to validate
            iteration_id: Optional iteration identifier
            correlation_id: Optional correlation ID for log tracking (MD-2024)

        Returns:
            BDVValidationResult with test outcomes
        """
        iteration_id = iteration_id or f"iter-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        corr_prefix = f"[{correlation_id}] " if correlation_id else ""

        # MD-2024: Enhanced logging with context
        logger.info(f"{corr_prefix}🧪 BDV validation starting")
        logger.info(f"{corr_prefix}  Contracts: {len(contracts)}")
        logger.info(f"{corr_prefix}  Execution ID: {execution_id}")
        logger.info(f"{corr_prefix}  Iteration ID: {iteration_id}")

        # Generate feature files from contracts
        feature_files = []
        contract_mappings = []

        for contract in contracts:
            feature_file = self._generate_feature_file(contract, iteration_id)
            if feature_file:
                feature_files.append(str(feature_file))

                # Create mapping
                mapping = ContractTestMapping(
                    contract_id=contract.get('id', 'unknown'),
                    contract_name=contract.get('name', 'Unknown Contract'),
                    feature_file=str(feature_file),
                    scenarios=self._extract_scenario_names(contract)
                )
                contract_mappings.append(mapping)

        # Run BDV tests
        if feature_files:
            logger.debug(f"{corr_prefix}Running BDV on {len(feature_files)} feature files")
            bdv_result = self.runner.run(
                feature_files=feature_files,
                iteration_id=iteration_id
            )

            # Map results to contracts
            self._map_results_to_contracts(bdv_result, contract_mappings)

            # MD-2024: Log detailed results for failures
            for mapping in contract_mappings:
                if mapping.failed > 0:
                    logger.warning(f"{corr_prefix}⚠️ Contract '{mapping.contract_name}' ({mapping.contract_id}): "
                                  f"{mapping.failed} scenarios failed out of {mapping.total}")
        else:
            # MD-2024: Log reason for empty results
            logger.warning(f"{corr_prefix}⚠️ BDV: No feature files generated - validation skipped")
            if not contracts:
                logger.warning(f"{corr_prefix}  Reason: No contracts provided")
            else:
                logger.warning(f"{corr_prefix}  Reason: Feature generation failed for all {len(contracts)} contracts")
                for contract in contracts:
                    criteria_count = len(contract.get('acceptance_criteria', []))
                    logger.debug(f"{corr_prefix}    - {contract.get('name', 'Unknown')}: {criteria_count} acceptance criteria")
            bdv_result = None

        # Calculate totals
        total_passed = sum(m.passed for m in contract_mappings)
        total_failed = sum(m.failed for m in contract_mappings)
        total_scenarios = sum(m.total for m in contract_mappings)
        contracts_fulfilled = sum(1 for m in contract_mappings if m.is_fulfilled)

        result = BDVValidationResult(
            execution_id=execution_id,
            iteration_id=iteration_id,
            total_contracts=len(contracts),
            contracts_fulfilled=contracts_fulfilled,
            total_scenarios=total_scenarios,
            scenarios_passed=total_passed,
            scenarios_failed=total_failed,
            overall_pass_rate=total_passed / total_scenarios if total_scenarios > 0 else 0.0,
            contract_mappings=contract_mappings,
            bdv_result=bdv_result
        )

        # Store result
        self._validation_results.append(result)

        # Save to file
        self._save_validation_result(result, iteration_id)

        # MD-2024: Enhanced completion logging
        logger.info(f"{corr_prefix}✅ BDV validation complete:")
        logger.info(f"{corr_prefix}  Contracts: {contracts_fulfilled}/{len(contracts)} fulfilled")
        logger.info(f"{corr_prefix}  Scenarios: {total_passed}/{total_scenarios} passed ({result.overall_pass_rate:.1%})")
        if total_failed > 0:
            logger.warning(f"{corr_prefix}  ⚠️ {total_failed} scenarios failed - review required")

        return result

    def _generate_feature_file(
        self,
        contract: Dict[str, Any],
        iteration_id: str
    ) -> Optional[Path]:
        """
        Generate Gherkin feature file from contract.

        Args:
            contract: Contract definition
            iteration_id: Iteration identifier

        Returns:
            Path to generated feature file
        """
        contract_id = contract.get('id', 'unknown')
        contract_name = contract.get('name', 'Unknown Contract')

        # Generate feature content
        feature_content = self._contract_to_feature(contract)

        # Write feature file
        safe_name = contract_name.replace(' ', '_').lower()
        feature_file = self.generated_features_path / f"{iteration_id}_{safe_name}.feature"

        try:
            with open(feature_file, 'w') as f:
                f.write(feature_content)

            logger.debug(f"Generated feature file: {feature_file}")
            return feature_file

        except Exception as e:
            logger.error(f"Failed to generate feature file for {contract_id}: {e}")
            return None

    def _contract_to_feature(self, contract: Dict[str, Any]) -> str:
        """
        Convert contract to Gherkin feature format.

        Args:
            contract: Contract definition

        Returns:
            Gherkin feature content
        """
        contract_id = contract.get('id', 'unknown')
        contract_name = contract.get('name', 'Unknown Contract')
        description = contract.get('description', '')
        acceptance_criteria = contract.get('acceptance_criteria', [])
        deliverables = contract.get('deliverables', [])

        # Build feature
        lines = [
            f"@contract:{contract_id}:v1.0",
            f"Feature: {contract_name}",
            f"  {description}",
            ""
        ]

        # Generate scenarios from acceptance criteria
        for i, criterion in enumerate(acceptance_criteria, 1):
            scenario_name = f"Acceptance Criterion {i}"

            # Parse criterion into Given/When/Then
            given, when, then = self._parse_criterion(criterion)

            lines.extend([
                f"  @criterion_{i}",
                f"  Scenario: {scenario_name}",
                f"    Given {given}",
                f"    When {when}",
                f"    Then {then}",
                ""
            ])

        # Generate scenarios from deliverables
        for deliverable in deliverables:
            # Handle both string deliverables (filenames) and dict deliverables
            if isinstance(deliverable, str):
                deliverable_name = deliverable
                deliverable_type = 'file'
            else:
                deliverable_name = deliverable.get('name', 'Deliverable')
                deliverable_type = deliverable.get('type', 'file')

            lines.extend([
                f"  @deliverable",
                f"  Scenario: Deliverable - {deliverable_name}",
                f"    Given the contract execution is complete",
                f"    When I check for deliverable \"{deliverable_name}\"",
                f"    Then the deliverable should exist as a {deliverable_type}",
                ""
            ])

        return '\n'.join(lines)

    def _parse_criterion(self, criterion: str) -> tuple:
        """
        Parse acceptance criterion into Given/When/Then.

        Args:
            criterion: Acceptance criterion text

        Returns:
            Tuple of (given, when, then)
        """
        # Simple parsing - can be enhanced with NLP
        criterion = criterion.strip()

        # Default structure
        given = "the system is in initial state"
        when = "the criterion is evaluated"
        then = f"it should satisfy: {criterion}"

        # Try to parse common patterns
        lower = criterion.lower()

        if "should" in lower:
            parts = criterion.split("should", 1)
            if len(parts) == 2:
                given = f"the {parts[0].strip()} exists"
                when = "the validation runs"
                then = f"it should {parts[1].strip()}"

        elif "must" in lower:
            parts = criterion.split("must", 1)
            if len(parts) == 2:
                given = f"the {parts[0].strip()} is defined"
                when = "the constraint is checked"
                then = f"it must {parts[1].strip()}"

        elif "when" in lower:
            parts = criterion.split("when", 1)
            if len(parts) == 2:
                given = parts[0].strip() or "the system is ready"
                rest = parts[1]
                if "then" in rest.lower():
                    when_then = rest.split("then", 1)
                    when = when_then[0].strip()
                    then = when_then[1].strip() if len(when_then) > 1 else "the criterion is met"
                else:
                    when = rest.strip()
                    then = "the criterion is satisfied"

        return (given, when, then)

    def _extract_scenario_names(self, contract: Dict[str, Any]) -> List[str]:
        """Extract expected scenario names from contract."""
        scenarios = []

        acceptance_criteria = contract.get('acceptance_criteria', [])
        for i in range(len(acceptance_criteria)):
            scenarios.append(f"Acceptance Criterion {i + 1}")

        deliverables = contract.get('deliverables', [])
        for deliverable in deliverables:
            # Handle both string deliverables (filenames) and dict deliverables
            if isinstance(deliverable, str):
                name = deliverable
            else:
                name = deliverable.get('name', 'Deliverable')
            scenarios.append(f"Deliverable - {name}")

        return scenarios

    def _map_results_to_contracts(
        self,
        bdv_result: BDVResult,
        contract_mappings: List[ContractTestMapping]
    ):
        """
        Map BDV test results to contract mappings.

        Args:
            bdv_result: BDV test execution result
            contract_mappings: List of contract mappings to update
        """
        if not bdv_result or not bdv_result.scenarios:
            # No detailed results - use summary
            if bdv_result:
                total = len(contract_mappings)
                if total > 0:
                    per_contract = bdv_result.passed // total
                    remainder = bdv_result.passed % total

                    for i, mapping in enumerate(contract_mappings):
                        mapping.passed = per_contract + (1 if i < remainder else 0)
                        mapping.failed = 0
            return

        # Map by feature file
        for scenario in bdv_result.scenarios:
            for mapping in contract_mappings:
                if mapping.feature_file in scenario.feature_file:
                    if scenario.status == 'passed':
                        mapping.passed += 1
                    elif scenario.status == 'failed':
                        mapping.failed += 1
                    else:
                        mapping.skipped += 1
                    break

    def _save_validation_result(self, result: BDVValidationResult, iteration_id: str):
        """Save validation result to file."""
        output_dir = Path(f"reports/bdv/{iteration_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "validation_result.json"
        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        logger.debug(f"Saved BDV validation result to {output_file}")

    def get_validation_metrics(
        self,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get validation metrics for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Metrics dictionary or None
        """
        for result in reversed(self._validation_results):
            if result.execution_id == execution_id:
                return {
                    'bdv_pass_rate': result.overall_pass_rate,
                    'contracts_fulfilled': result.contracts_fulfilled,
                    'total_contracts': result.total_contracts,
                    'scenarios_passed': result.scenarios_passed,
                    'scenarios_failed': result.scenarios_failed,
                    'fulfillment_rate': result.contracts_fulfilled / result.total_contracts
                        if result.total_contracts > 0 else 0.0
                }

        return None

    def calculate_quality_score_contribution(
        self,
        result: BDVValidationResult
    ) -> float:
        """
        Calculate BDV contribution to overall quality score.

        Args:
            result: BDV validation result

        Returns:
            Quality score contribution (0.0 to 1.0)
        """
        # Weighted factors
        pass_rate_weight = 0.6
        fulfillment_weight = 0.4

        pass_rate = result.overall_pass_rate
        fulfillment_rate = (result.contracts_fulfilled / result.total_contracts
                          if result.total_contracts > 0 else 0.0)

        score = (pass_rate * pass_rate_weight) + (fulfillment_rate * fulfillment_weight)

        return min(1.0, max(0.0, score))

    def get_ml_training_data(self) -> List[Dict[str, Any]]:
        """
        Get validation data formatted for ML training.

        Returns:
            List of feature dictionaries for ML
        """
        training_data = []

        for result in self._validation_results:
            for mapping in result.contract_mappings:
                training_data.append({
                    'execution_id': result.execution_id,
                    'contract_id': mapping.contract_id,
                    'contract_name': mapping.contract_name,
                    'total_scenarios': mapping.total,
                    'passed': mapping.passed,
                    'failed': mapping.failed,
                    'skipped': mapping.skipped,
                    'pass_rate': mapping.pass_rate,
                    'is_fulfilled': 1 if mapping.is_fulfilled else 0,
                    'timestamp': result.validated_at.isoformat()
                })

        return training_data


# Global instance
_bdv_service: Optional[BDVIntegrationService] = None


def get_bdv_integration_service() -> BDVIntegrationService:
    """Get or create global BDV integration service instance."""
    global _bdv_service
    if _bdv_service is None:
        _bdv_service = BDVIntegrationService()
    return _bdv_service


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize service
    service = get_bdv_integration_service()

    # Sample contracts
    contracts = [
        {
            'id': 'contract-001',
            'name': 'User Authentication',
            'description': 'Authentication contract for user login',
            'acceptance_criteria': [
                'Users should be able to login with valid credentials',
                'Invalid credentials should return 401 error',
                'Session token must be returned on successful login'
            ],
            'deliverables': [
                {'name': 'auth_service.py', 'type': 'file'},
                {'name': 'auth_tests.py', 'type': 'file'}
            ]
        },
        {
            'id': 'contract-002',
            'name': 'User Profile API',
            'description': 'API contract for user profile management',
            'acceptance_criteria': [
                'GET /profile should return user data',
                'PUT /profile should update user data',
                'Profile updates must be validated'
            ],
            'deliverables': [
                {'name': 'profile_routes.py', 'type': 'file'}
            ]
        }
    ]

    # Validate contracts
    result = service.validate_contracts(
        execution_id="exec-001",
        contracts=contracts,
        iteration_id="iter-test-001"
    )

    print("\n=== BDV Validation Result ===")
    print(f"Contracts: {result.contracts_fulfilled}/{result.total_contracts} fulfilled")
    print(f"Scenarios: {result.scenarios_passed}/{result.total_scenarios} passed")
    print(f"Pass Rate: {result.overall_pass_rate:.1%}")
    print(f"\nQuality Contribution: {service.calculate_quality_score_contribution(result):.2f}")
