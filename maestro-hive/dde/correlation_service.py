"""
DDE-BDV Correlation Service (MD-2023)

Synchronizes DDE contract fulfillment results with BDV validation results.
Enables correlated quality assessment and prevents duplicate validation.

Features:
- Track DDE contract fulfillment status
- Correlate with BDV validation scenarios
- Detect agreement/disagreement between systems
- Provide unified contract status view

Author: Claude Code Implementation
Date: 2025-12-02
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum

logger = logging.getLogger(__name__)


class FulfillmentSource(str, Enum):
    """Source of fulfillment information"""
    DDE = "dde"
    BDV = "bdv"
    CORRELATED = "correlated"


class CorrelationStatus(str, Enum):
    """Status of DDE-BDV correlation"""
    AGREEMENT = "agreement"       # Both DDE and BDV agree on fulfillment
    DISAGREEMENT = "disagreement" # DDE and BDV disagree
    DDE_ONLY = "dde_only"        # Only DDE has data
    BDV_ONLY = "bdv_only"        # Only BDV has data
    UNKNOWN = "unknown"          # No data from either


@dataclass
class ContractFulfillmentStatus:
    """Fulfillment status for a single contract from both systems"""
    contract_id: str
    contract_name: str

    # DDE status
    dde_fulfilled: Optional[bool] = None
    dde_quality_score: float = 0.0
    dde_deliverables: List[str] = field(default_factory=list)

    # BDV status
    bdv_fulfilled: Optional[bool] = None
    bdv_pass_rate: float = 0.0
    bdv_scenarios_passed: int = 0
    bdv_scenarios_failed: int = 0
    bdv_scenarios_total: int = 0

    # Correlation
    correlation_status: CorrelationStatus = CorrelationStatus.UNKNOWN
    confidence_score: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'contract_id': self.contract_id,
            'contract_name': self.contract_name,
            'dde': {
                'fulfilled': self.dde_fulfilled,
                'quality_score': round(self.dde_quality_score, 4),
                'deliverables': self.dde_deliverables
            },
            'bdv': {
                'fulfilled': self.bdv_fulfilled,
                'pass_rate': round(self.bdv_pass_rate, 4),
                'scenarios': {
                    'passed': self.bdv_scenarios_passed,
                    'failed': self.bdv_scenarios_failed,
                    'total': self.bdv_scenarios_total
                }
            },
            'correlation': {
                'status': self.correlation_status.value,
                'confidence': round(self.confidence_score, 4)
            },
            'notes': self.notes
        }


@dataclass
class CorrelatedValidationResult:
    """Combined result from DDE-BDV correlation"""
    execution_id: str
    iteration_id: str

    # Contract statuses
    contracts: List[ContractFulfillmentStatus]

    # Summary metrics
    total_contracts: int = 0
    contracts_in_agreement: int = 0
    contracts_in_disagreement: int = 0
    dde_only_contracts: int = 0
    bdv_only_contracts: int = 0

    # Overall scores
    correlation_confidence: float = 0.0
    combined_fulfillment_rate: float = 0.0

    correlated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'iteration_id': self.iteration_id,
            'summary': {
                'total_contracts': self.total_contracts,
                'in_agreement': self.contracts_in_agreement,
                'in_disagreement': self.contracts_in_disagreement,
                'dde_only': self.dde_only_contracts,
                'bdv_only': self.bdv_only_contracts,
                'correlation_confidence': round(self.correlation_confidence, 4),
                'combined_fulfillment_rate': round(self.combined_fulfillment_rate, 4)
            },
            'contracts': [c.to_dict() for c in self.contracts],
            'correlated_at': self.correlated_at.isoformat()
        }


class DDEBDVCorrelationService:
    """
    Correlation Service for DDE and BDV Results

    Synchronizes contract fulfillment information between
    DDE (Dependency-Driven Execution) and BDV (Behavior-Driven Validation).
    """

    def __init__(self):
        """Initialize correlation service."""
        # Store DDE results by execution_id -> contract_id -> status
        self._dde_results: Dict[str, Dict[str, ContractFulfillmentStatus]] = {}

        # Store BDV results similarly
        self._bdv_results: Dict[str, Dict[str, ContractFulfillmentStatus]] = {}

        # Correlated results
        self._correlated_results: Dict[str, CorrelatedValidationResult] = {}

        logger.info("✅ DDEBDVCorrelationService initialized")

    def record_dde_result(
        self,
        execution_id: str,
        contract_id: str,
        contract_name: str,
        fulfilled: bool,
        quality_score: float = 0.0,
        deliverables: Optional[List[str]] = None
    ):
        """
        Record DDE contract fulfillment result.

        Args:
            execution_id: Execution identifier
            contract_id: Contract identifier
            contract_name: Human-readable contract name
            fulfilled: Whether DDE considers contract fulfilled
            quality_score: Quality score from DDE (0.0 - 1.0)
            deliverables: List of deliverables produced
        """
        if execution_id not in self._dde_results:
            self._dde_results[execution_id] = {}

        if contract_id in self._dde_results[execution_id]:
            # Update existing
            status = self._dde_results[execution_id][contract_id]
            status.dde_fulfilled = fulfilled
            status.dde_quality_score = quality_score
            status.dde_deliverables = deliverables or []
        else:
            # Create new
            self._dde_results[execution_id][contract_id] = ContractFulfillmentStatus(
                contract_id=contract_id,
                contract_name=contract_name,
                dde_fulfilled=fulfilled,
                dde_quality_score=quality_score,
                dde_deliverables=deliverables or []
            )

        logger.debug(f"Recorded DDE result: {contract_id} = {fulfilled}")

    def record_bdv_result(
        self,
        execution_id: str,
        contract_id: str,
        contract_name: str,
        fulfilled: bool,
        pass_rate: float = 0.0,
        scenarios_passed: int = 0,
        scenarios_failed: int = 0
    ):
        """
        Record BDV contract validation result.

        Args:
            execution_id: Execution identifier
            contract_id: Contract identifier
            contract_name: Human-readable contract name
            fulfilled: Whether BDV considers contract fulfilled (all scenarios pass)
            pass_rate: Scenario pass rate
            scenarios_passed: Number of passed scenarios
            scenarios_failed: Number of failed scenarios
        """
        if execution_id not in self._bdv_results:
            self._bdv_results[execution_id] = {}

        if contract_id in self._bdv_results[execution_id]:
            # Update existing
            status = self._bdv_results[execution_id][contract_id]
            status.bdv_fulfilled = fulfilled
            status.bdv_pass_rate = pass_rate
            status.bdv_scenarios_passed = scenarios_passed
            status.bdv_scenarios_failed = scenarios_failed
            status.bdv_scenarios_total = scenarios_passed + scenarios_failed
        else:
            # Create new
            self._bdv_results[execution_id][contract_id] = ContractFulfillmentStatus(
                contract_id=contract_id,
                contract_name=contract_name,
                bdv_fulfilled=fulfilled,
                bdv_pass_rate=pass_rate,
                bdv_scenarios_passed=scenarios_passed,
                bdv_scenarios_failed=scenarios_failed,
                bdv_scenarios_total=scenarios_passed + scenarios_failed
            )

        logger.debug(f"Recorded BDV result: {contract_id} = {fulfilled}")

    def get_dde_fulfillment_status(
        self,
        execution_id: str
    ) -> Dict[str, bool]:
        """
        Get DDE fulfillment status for all contracts in an execution.

        Use this to pass DDE results to BDV before validation.

        Args:
            execution_id: Execution identifier

        Returns:
            Dict mapping contract_id to fulfillment status
        """
        if execution_id not in self._dde_results:
            return {}

        return {
            contract_id: status.dde_fulfilled
            for contract_id, status in self._dde_results[execution_id].items()
            if status.dde_fulfilled is not None
        }

    def correlate_results(
        self,
        execution_id: str,
        iteration_id: Optional[str] = None
    ) -> CorrelatedValidationResult:
        """
        Correlate DDE and BDV results for an execution.

        Args:
            execution_id: Execution identifier
            iteration_id: Optional iteration identifier

        Returns:
            CorrelatedValidationResult with combined analysis
        """
        iteration_id = iteration_id or f"corr-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        logger.info(f"🔄 Correlating DDE-BDV results for {execution_id}")

        # Get all contracts from both systems
        dde_contracts = self._dde_results.get(execution_id, {})
        bdv_contracts = self._bdv_results.get(execution_id, {})

        all_contract_ids = set(dde_contracts.keys()) | set(bdv_contracts.keys())

        # Merge and correlate
        correlated_contracts = []
        agreements = 0
        disagreements = 0
        dde_only = 0
        bdv_only = 0

        for contract_id in all_contract_ids:
            dde_status = dde_contracts.get(contract_id)
            bdv_status = bdv_contracts.get(contract_id)

            # Create merged status
            merged = ContractFulfillmentStatus(
                contract_id=contract_id,
                contract_name=dde_status.contract_name if dde_status else
                             (bdv_status.contract_name if bdv_status else "Unknown")
            )

            # Copy DDE data
            if dde_status:
                merged.dde_fulfilled = dde_status.dde_fulfilled
                merged.dde_quality_score = dde_status.dde_quality_score
                merged.dde_deliverables = dde_status.dde_deliverables

            # Copy BDV data
            if bdv_status:
                merged.bdv_fulfilled = bdv_status.bdv_fulfilled
                merged.bdv_pass_rate = bdv_status.bdv_pass_rate
                merged.bdv_scenarios_passed = bdv_status.bdv_scenarios_passed
                merged.bdv_scenarios_failed = bdv_status.bdv_scenarios_failed
                merged.bdv_scenarios_total = bdv_status.bdv_scenarios_total

            # Determine correlation status
            merged.correlation_status, merged.confidence_score, merged.notes = \
                self._determine_correlation(merged)

            # Count by status
            if merged.correlation_status == CorrelationStatus.AGREEMENT:
                agreements += 1
            elif merged.correlation_status == CorrelationStatus.DISAGREEMENT:
                disagreements += 1
            elif merged.correlation_status == CorrelationStatus.DDE_ONLY:
                dde_only += 1
            elif merged.correlation_status == CorrelationStatus.BDV_ONLY:
                bdv_only += 1

            correlated_contracts.append(merged)

        # Calculate overall metrics
        total = len(correlated_contracts)
        correlation_confidence = agreements / total if total > 0 else 0.0

        # Combined fulfillment rate (conservative - both must agree)
        fulfilled_count = sum(
            1 for c in correlated_contracts
            if c.correlation_status == CorrelationStatus.AGREEMENT
            and c.dde_fulfilled
        )
        combined_rate = fulfilled_count / total if total > 0 else 0.0

        result = CorrelatedValidationResult(
            execution_id=execution_id,
            iteration_id=iteration_id,
            contracts=correlated_contracts,
            total_contracts=total,
            contracts_in_agreement=agreements,
            contracts_in_disagreement=disagreements,
            dde_only_contracts=dde_only,
            bdv_only_contracts=bdv_only,
            correlation_confidence=correlation_confidence,
            combined_fulfillment_rate=combined_rate
        )

        # Store result
        self._correlated_results[execution_id] = result

        logger.info(f"✅ Correlation complete: {agreements}/{total} in agreement, "
                   f"confidence: {correlation_confidence:.1%}")

        return result

    def _determine_correlation(
        self,
        status: ContractFulfillmentStatus
    ) -> tuple:
        """
        Determine correlation status, confidence, and notes.

        Returns:
            Tuple of (CorrelationStatus, confidence_score, notes)
        """
        notes = []

        # Check data availability
        has_dde = status.dde_fulfilled is not None
        has_bdv = status.bdv_fulfilled is not None

        if not has_dde and not has_bdv:
            return CorrelationStatus.UNKNOWN, 0.0, ["No data from either system"]

        if has_dde and not has_bdv:
            notes.append("Only DDE data available")
            return CorrelationStatus.DDE_ONLY, 0.5, notes

        if has_bdv and not has_dde:
            notes.append("Only BDV data available")
            return CorrelationStatus.BDV_ONLY, 0.5, notes

        # Both have data - check agreement
        if status.dde_fulfilled == status.bdv_fulfilled:
            # Agreement
            if status.dde_fulfilled:
                notes.append("Both systems confirm fulfillment")
            else:
                notes.append("Both systems agree contract is not fulfilled")

            # Calculate confidence based on quality metrics
            confidence = 0.8
            if status.dde_quality_score >= 0.9:
                confidence += 0.1
            if status.bdv_pass_rate >= 0.9:
                confidence += 0.1

            return CorrelationStatus.AGREEMENT, min(1.0, confidence), notes

        else:
            # Disagreement
            if status.dde_fulfilled and not status.bdv_fulfilled:
                notes.append("DDE says fulfilled, but BDV tests failed")
                if status.bdv_scenarios_failed > 0:
                    notes.append(f"BDV: {status.bdv_scenarios_failed} scenarios failed")
            else:
                notes.append("BDV says fulfilled, but DDE says not fulfilled")
                if status.dde_quality_score < 0.5:
                    notes.append(f"DDE quality score is low: {status.dde_quality_score:.1%}")

            # Lower confidence for disagreements
            return CorrelationStatus.DISAGREEMENT, 0.3, notes

    def get_correlated_metrics_for_verdict(
        self,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get correlated metrics formatted for VerdictAggregator.

        Args:
            execution_id: Execution identifier

        Returns:
            Metrics dictionary for verdict generation
        """
        if execution_id not in self._correlated_results:
            # Try to correlate if not already done
            if execution_id in self._dde_results or execution_id in self._bdv_results:
                self.correlate_results(execution_id)
            else:
                return None

        result = self._correlated_results.get(execution_id)
        if not result:
            return None

        return {
            'correlation_confidence': result.correlation_confidence,
            'combined_fulfillment_rate': result.combined_fulfillment_rate,
            'contracts_in_agreement': result.contracts_in_agreement,
            'contracts_in_disagreement': result.contracts_in_disagreement,
            'total_contracts': result.total_contracts,
            'has_disagreements': result.contracts_in_disagreement > 0
        }

    def should_bdv_validate_contract(
        self,
        execution_id: str,
        contract_id: str,
        skip_fulfilled: bool = False
    ) -> tuple:
        """
        Determine if BDV should validate a contract.

        Used to optionally skip validation for DDE-fulfilled contracts.

        Args:
            execution_id: Execution identifier
            contract_id: Contract identifier
            skip_fulfilled: Whether to skip DDE-fulfilled contracts

        Returns:
            Tuple of (should_validate, reason)
        """
        if not skip_fulfilled:
            return True, "Full validation mode"

        if execution_id not in self._dde_results:
            return True, "No DDE data available"

        if contract_id not in self._dde_results[execution_id]:
            return True, "Contract not in DDE results"

        status = self._dde_results[execution_id][contract_id]

        if status.dde_fulfilled and status.dde_quality_score >= 0.9:
            return False, f"DDE fulfilled with high quality ({status.dde_quality_score:.1%})"

        return True, "DDE not fulfilled or quality below threshold"

    def clear_execution(self, execution_id: str):
        """Clear all data for an execution."""
        self._dde_results.pop(execution_id, None)
        self._bdv_results.pop(execution_id, None)
        self._correlated_results.pop(execution_id, None)


# Global instance
_correlation_service: Optional[DDEBDVCorrelationService] = None


def get_correlation_service() -> DDEBDVCorrelationService:
    """Get or create global correlation service instance."""
    global _correlation_service
    if _correlation_service is None:
        _correlation_service = DDEBDVCorrelationService()
    return _correlation_service


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize service
    service = get_correlation_service()

    execution_id = "exec-001"

    # Record DDE results
    service.record_dde_result(
        execution_id=execution_id,
        contract_id="contract-001",
        contract_name="User Authentication",
        fulfilled=True,
        quality_score=0.95,
        deliverables=["auth_service.py", "auth_tests.py"]
    )

    service.record_dde_result(
        execution_id=execution_id,
        contract_id="contract-002",
        contract_name="Profile API",
        fulfilled=True,
        quality_score=0.85,
        deliverables=["profile_routes.py"]
    )

    # Record BDV results
    service.record_bdv_result(
        execution_id=execution_id,
        contract_id="contract-001",
        contract_name="User Authentication",
        fulfilled=True,
        pass_rate=0.90,
        scenarios_passed=9,
        scenarios_failed=1
    )

    service.record_bdv_result(
        execution_id=execution_id,
        contract_id="contract-002",
        contract_name="Profile API",
        fulfilled=False,  # Disagrees with DDE
        pass_rate=0.60,
        scenarios_passed=3,
        scenarios_failed=2
    )

    # Correlate results
    result = service.correlate_results(execution_id)

    print("\n=== DDE-BDV Correlation Result ===")
    print(f"Execution: {result.execution_id}")
    print(f"Total Contracts: {result.total_contracts}")
    print(f"In Agreement: {result.contracts_in_agreement}")
    print(f"In Disagreement: {result.contracts_in_disagreement}")
    print(f"Correlation Confidence: {result.correlation_confidence:.1%}")
    print(f"Combined Fulfillment Rate: {result.combined_fulfillment_rate:.1%}")

    print("\nContract Details:")
    for contract in result.contracts:
        print(f"\n  {contract.contract_name} ({contract.contract_id}):")
        print(f"    DDE: fulfilled={contract.dde_fulfilled}, quality={contract.dde_quality_score:.1%}")
        print(f"    BDV: fulfilled={contract.bdv_fulfilled}, pass_rate={contract.bdv_pass_rate:.1%}")
        print(f"    Correlation: {contract.correlation_status.value} (confidence: {contract.confidence_score:.1%})")
        for note in contract.notes:
            print(f"      - {note}")
