"""
DDE Auditor

Provides audit and compliance checking for DDE (Dependency-Driven Execution).
Compares planned workflow manifests against execution logs to verify:
- Completeness (all nodes executed)
- Integrity (correct order, artifacts stamped, contracts locked)
- Policy compliance (gates passed, no violations)

Generates audit reports with detailed findings and recommendations.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class AuditResult(Enum):
    """Audit result status"""
    PASS = "PASS"
    FAIL = "FAIL"


class ViolationType(Enum):
    """Types of audit violations"""
    MISSING_NODE = "missing_node"
    FAILED_GATE = "failed_gate"
    MISSING_ARTIFACT = "missing_artifact"
    UNLOCKED_CONTRACT = "unlocked_contract"
    POLICY_VIOLATION = "policy_violation"
    ORDER_VIOLATION = "order_violation"
    INTEGRITY_FAILURE = "integrity_failure"


@dataclass
class AuditViolation:
    """Individual audit violation"""
    violation_type: ViolationType
    node_id: str
    severity: str  # "BLOCKING", "WARNING", "INFO"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletenessMetrics:
    """Metrics for workflow completeness"""
    total_nodes: int
    completed_nodes: int
    missing_nodes: List[str]
    failed_nodes: List[str]
    skipped_nodes: List[str]
    completeness_score: float  # complete_nodes / total_nodes


@dataclass
class IntegrityMetrics:
    """Metrics for workflow integrity"""
    total_gates: int
    passed_gates: int
    failed_gates: List[Dict[str, Any]]
    total_artifacts: int
    stamped_artifacts: int
    missing_artifacts: List[str]
    total_contracts: int
    locked_contracts: int
    unlocked_contracts: List[str]
    execution_order_valid: bool


@dataclass
class AuditReport:
    """Complete audit report"""
    iteration_id: str
    workflow_id: str
    audit_timestamp: str
    audit_result: AuditResult
    completeness: CompletenessMetrics
    integrity: IntegrityMetrics
    violations: List[AuditViolation]
    execution_duration: Optional[float] = None  # seconds
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "iteration_id": self.iteration_id,
            "workflow_id": self.workflow_id,
            "audit_timestamp": self.audit_timestamp,
            "audit_result": self.audit_result.value,
            "completeness": {
                "total_nodes": self.completeness.total_nodes,
                "completed_nodes": self.completeness.completed_nodes,
                "missing_nodes": self.completeness.missing_nodes,
                "failed_nodes": self.completeness.failed_nodes,
                "skipped_nodes": self.completeness.skipped_nodes,
                "completeness_score": self.completeness.completeness_score
            },
            "integrity": {
                "total_gates": self.integrity.total_gates,
                "passed_gates": self.integrity.passed_gates,
                "failed_gates": self.integrity.failed_gates,
                "total_artifacts": self.integrity.total_artifacts,
                "stamped_artifacts": self.integrity.stamped_artifacts,
                "missing_artifacts": self.integrity.missing_artifacts,
                "total_contracts": self.integrity.total_contracts,
                "locked_contracts": self.integrity.locked_contracts,
                "unlocked_contracts": self.integrity.unlocked_contracts,
                "execution_order_valid": self.integrity.execution_order_valid
            },
            "violations": [
                {
                    "violation_type": v.violation_type.value,
                    "node_id": v.node_id,
                    "severity": v.severity,
                    "message": v.message,
                    "details": v.details
                }
                for v in self.violations
            ],
            "execution_duration": self.execution_duration,
            "recommendations": self.recommendations
        }


class DDEAuditor:
    """
    Audits DDE workflow execution for completeness and integrity.

    Compares workflow manifest (plan) against execution log (actual) to identify:
    - Missing nodes
    - Failed quality gates
    - Missing artifacts
    - Unlocked contracts
    - Policy violations
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize DDE auditor.

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default 5 minutes)
        """
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Tuple[AuditReport, datetime]] = {}
        self._audit_history: Dict[str, List[AuditReport]] = {}

    async def audit_workflow(
        self,
        iteration_id: str,
        manifest: Dict[str, Any],
        execution_log: Dict[str, Any]
    ) -> AuditReport:
        """
        Audit workflow execution against manifest.

        Args:
            iteration_id: Iteration identifier
            manifest: Workflow manifest (planned nodes, gates, artifacts)
            execution_log: Execution log (actual execution events)

        Returns:
            AuditReport with completeness, integrity, and violations
        """
        # Check cache
        cached = self._get_cached_report(iteration_id)
        if cached:
            return cached

        # Perform audit
        violations: List[AuditViolation] = []

        # 1. Completeness checks
        completeness = self._check_completeness(manifest, execution_log, violations)

        # 2. Integrity checks
        integrity = self._check_integrity(manifest, execution_log, violations)

        # 3. Determine audit result
        audit_result = AuditResult.PASS if completeness.completeness_score == 1.0 else AuditResult.FAIL

        # Check for blocking violations
        blocking_violations = [v for v in violations if v.severity == "BLOCKING"]
        if blocking_violations:
            audit_result = AuditResult.FAIL

        # 4. Calculate execution duration
        duration = self._calculate_duration(execution_log)

        # 5. Generate recommendations
        recommendations = self._generate_recommendations(completeness, integrity, violations)

        # Build report
        report = AuditReport(
            iteration_id=iteration_id,
            workflow_id=manifest.get("workflow_id", "unknown"),
            audit_timestamp=datetime.utcnow().isoformat() + "Z",
            audit_result=audit_result,
            completeness=completeness,
            integrity=integrity,
            violations=violations,
            execution_duration=duration,
            recommendations=recommendations
        )

        # Cache report
        self._cache_report(iteration_id, report)

        # Add to history
        if iteration_id not in self._audit_history:
            self._audit_history[iteration_id] = []
        self._audit_history[iteration_id].append(report)

        return report

    def _check_completeness(
        self,
        manifest: Dict[str, Any],
        execution_log: Dict[str, Any],
        violations: List[AuditViolation]
    ) -> CompletenessMetrics:
        """Check workflow completeness"""
        # Get all nodes from manifest
        manifest_nodes = set(manifest.get("nodes", {}).keys())
        total_nodes = len(manifest_nodes)

        # Get completed nodes from execution log
        executed_nodes = set(execution_log.get("node_states", {}).keys())
        completed_nodes = set()
        failed_nodes = []
        skipped_nodes = []

        for node_id, state in execution_log.get("node_states", {}).items():
            status = state.get("status", "").lower()
            if status == "completed":
                completed_nodes.add(node_id)
            elif status == "failed":
                failed_nodes.append(node_id)
            elif status == "skipped":
                skipped_nodes.append(node_id)

        # Find missing nodes
        missing_nodes = list(manifest_nodes - executed_nodes)

        # Add violations for missing nodes
        for node_id in missing_nodes:
            violations.append(AuditViolation(
                violation_type=ViolationType.MISSING_NODE,
                node_id=node_id,
                severity="BLOCKING",
                message=f"Node {node_id} was not executed",
                details={"expected": True, "executed": False}
            ))

        # Calculate completeness score
        completeness_score = len(completed_nodes) / total_nodes if total_nodes > 0 else 0.0

        return CompletenessMetrics(
            total_nodes=total_nodes,
            completed_nodes=len(completed_nodes),
            missing_nodes=missing_nodes,
            failed_nodes=failed_nodes,
            skipped_nodes=skipped_nodes,
            completeness_score=completeness_score
        )

    def _check_integrity(
        self,
        manifest: Dict[str, Any],
        execution_log: Dict[str, Any],
        violations: List[AuditViolation]
    ) -> IntegrityMetrics:
        """Check workflow integrity"""
        # Check quality gates
        total_gates = 0
        passed_gates = 0
        failed_gates = []

        for node_id, node_config in manifest.get("nodes", {}).items():
            node_gates = node_config.get("gates", [])
            total_gates += len(node_gates)

            node_state = execution_log.get("node_states", {}).get(node_id, {})
            gate_results = node_state.get("gate_results", {})

            for gate_name in node_gates:
                gate_result = gate_results.get(gate_name, {})
                if gate_result.get("status") == "passed":
                    passed_gates += 1
                else:
                    failed_gates.append({
                        "node_id": node_id,
                        "gate_name": gate_name,
                        "status": gate_result.get("status", "unknown")
                    })

                    violations.append(AuditViolation(
                        violation_type=ViolationType.FAILED_GATE,
                        node_id=node_id,
                        severity=gate_result.get("severity", "WARNING"),
                        message=f"Gate {gate_name} failed for node {node_id}",
                        details=gate_result
                    ))

        # Check artifacts
        total_artifacts = 0
        stamped_artifacts = 0
        missing_artifacts = []

        for node_id, node_config in manifest.get("nodes", {}).items():
            expected_artifacts = node_config.get("expected_artifacts", [])
            total_artifacts += len(expected_artifacts)

            node_state = execution_log.get("node_states", {}).get(node_id, {})
            actual_artifacts = node_state.get("artifacts", [])

            for artifact_name in expected_artifacts:
                # Check if artifact was stamped
                artifact_found = any(
                    artifact_name in str(artifact)
                    for artifact in actual_artifacts
                )

                if artifact_found:
                    stamped_artifacts += 1
                else:
                    missing_artifacts.append(f"{node_id}:{artifact_name}")

                    violations.append(AuditViolation(
                        violation_type=ViolationType.MISSING_ARTIFACT,
                        node_id=node_id,
                        severity="WARNING",
                        message=f"Artifact {artifact_name} not stamped for node {node_id}",
                        details={"artifact_name": artifact_name}
                    ))

        # Check contract locks
        total_contracts = 0
        locked_contracts = 0
        unlocked_contracts = []

        for node_id, node_config in manifest.get("nodes", {}).items():
            if node_config.get("type") == "INTERFACE":
                total_contracts += 1

                node_state = execution_log.get("node_states", {}).get(node_id, {})
                is_locked = node_state.get("contract_locked", False)

                if is_locked:
                    locked_contracts += 1
                else:
                    unlocked_contracts.append(node_id)

                    violations.append(AuditViolation(
                        violation_type=ViolationType.UNLOCKED_CONTRACT,
                        node_id=node_id,
                        severity="BLOCKING",
                        message=f"Contract for node {node_id} not locked",
                        details={"contract_version": node_config.get("contract_version")}
                    ))

        # Check execution order
        execution_order_valid = self._validate_execution_order(manifest, execution_log)

        if not execution_order_valid:
            violations.append(AuditViolation(
                violation_type=ViolationType.ORDER_VIOLATION,
                node_id="WORKFLOW",
                severity="WARNING",
                message="Execution order violated dependency constraints",
                details={}
            ))

        return IntegrityMetrics(
            total_gates=total_gates,
            passed_gates=passed_gates,
            failed_gates=failed_gates,
            total_artifacts=total_artifacts,
            stamped_artifacts=stamped_artifacts,
            missing_artifacts=missing_artifacts,
            total_contracts=total_contracts,
            locked_contracts=locked_contracts,
            unlocked_contracts=unlocked_contracts,
            execution_order_valid=execution_order_valid
        )

    def _validate_execution_order(
        self,
        manifest: Dict[str, Any],
        execution_log: Dict[str, Any]
    ) -> bool:
        """Validate that execution order respects dependencies"""
        # Build dependency graph
        dependencies: Dict[str, List[str]] = {}
        for node_id, node_config in manifest.get("nodes", {}).items():
            dependencies[node_id] = node_config.get("dependencies", [])

        # Get execution timestamps
        execution_times: Dict[str, datetime] = {}
        for node_id, node_state in execution_log.get("node_states", {}).items():
            start_time = node_state.get("start_time")
            if start_time:
                try:
                    execution_times[node_id] = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                except:
                    pass

        # Check that each node started after its dependencies completed
        for node_id, deps in dependencies.items():
            if node_id not in execution_times:
                continue

            node_start = execution_times[node_id]

            for dep_id in deps:
                if dep_id not in execution_log.get("node_states", {}):
                    continue

                dep_state = execution_log["node_states"][dep_id]
                dep_end = dep_state.get("end_time")

                if dep_end:
                    try:
                        dep_end_dt = datetime.fromisoformat(dep_end.replace("Z", "+00:00"))
                        if node_start < dep_end_dt:
                            return False
                    except:
                        pass

        return True

    def _calculate_duration(self, execution_log: Dict[str, Any]) -> Optional[float]:
        """Calculate total execution duration in seconds"""
        started_at = execution_log.get("started_at")
        completed_at = execution_log.get("completed_at")

        if not started_at or not completed_at:
            return None

        try:
            start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            return (end_dt - start_dt).total_seconds()
        except:
            return None

    def _generate_recommendations(
        self,
        completeness: CompletenessMetrics,
        integrity: IntegrityMetrics,
        violations: List[AuditViolation]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Completeness recommendations
        if completeness.completeness_score < 1.0:
            recommendations.append(
                f"Workflow incomplete: {completeness.completed_nodes}/{completeness.total_nodes} nodes completed. "
                f"Investigate missing nodes: {', '.join(completeness.missing_nodes)}"
            )

        if completeness.failed_nodes:
            recommendations.append(
                f"Failed nodes detected: {', '.join(completeness.failed_nodes)}. "
                "Review error logs and implement retry logic."
            )

        # Integrity recommendations
        if integrity.failed_gates:
            recommendations.append(
                f"{len(integrity.failed_gates)} quality gates failed. "
                "Review gate criteria and ensure quality standards are met."
            )

        if integrity.missing_artifacts:
            recommendations.append(
                f"{len(integrity.missing_artifacts)} artifacts not stamped. "
                "Verify artifact generation and stamping logic."
            )

        if integrity.unlocked_contracts:
            recommendations.append(
                f"{len(integrity.unlocked_contracts)} contracts not locked. "
                "Ensure interface nodes complete successfully to lock contracts."
            )

        if not integrity.execution_order_valid:
            recommendations.append(
                "Execution order violation detected. "
                "Review dependency graph and ensure proper sequencing."
            )

        # General recommendations
        if not recommendations:
            recommendations.append("All checks passed. Workflow executed successfully.")

        return recommendations

    def _get_cached_report(self, iteration_id: str) -> Optional[AuditReport]:
        """Get cached audit report if valid"""
        if iteration_id not in self._cache:
            return None

        report, cached_at = self._cache[iteration_id]

        # Check if cache is still valid
        if datetime.utcnow() - cached_at > timedelta(seconds=self.cache_ttl):
            del self._cache[iteration_id]
            return None

        return report

    def _cache_report(self, iteration_id: str, report: AuditReport):
        """Cache audit report"""
        self._cache[iteration_id] = (report, datetime.utcnow())

    def get_audit_history(self, iteration_id: str) -> List[AuditReport]:
        """Get audit history for an iteration"""
        return self._audit_history.get(iteration_id, [])

    def compare_audits(
        self,
        iteration_id: str,
        previous_index: int = -2,
        current_index: int = -1
    ) -> Dict[str, Any]:
        """
        Compare two audit reports from history.

        Args:
            iteration_id: Iteration identifier
            previous_index: Index of previous report (default -2)
            current_index: Index of current report (default -1)

        Returns:
            Comparison dict with deltas and improvements
        """
        history = self.get_audit_history(iteration_id)

        if len(history) < 2:
            return {"error": "Insufficient audit history for comparison"}

        prev_report = history[previous_index]
        curr_report = history[current_index]

        return {
            "iteration_id": iteration_id,
            "previous_audit": prev_report.audit_timestamp,
            "current_audit": curr_report.audit_timestamp,
            "completeness_delta": curr_report.completeness.completeness_score - prev_report.completeness.completeness_score,
            "violations_delta": len(curr_report.violations) - len(prev_report.violations),
            "gates_passed_delta": curr_report.integrity.passed_gates - prev_report.integrity.passed_gates,
            "artifacts_stamped_delta": curr_report.integrity.stamped_artifacts - prev_report.integrity.stamped_artifacts,
            "improved": curr_report.completeness.completeness_score > prev_report.completeness.completeness_score,
            "summary": self._generate_comparison_summary(prev_report, curr_report)
        }

    def _generate_comparison_summary(
        self,
        prev_report: AuditReport,
        curr_report: AuditReport
    ) -> str:
        """Generate human-readable comparison summary"""
        if curr_report.completeness.completeness_score > prev_report.completeness.completeness_score:
            return "Workflow execution improved compared to previous audit"
        elif curr_report.completeness.completeness_score < prev_report.completeness.completeness_score:
            return "Workflow execution degraded compared to previous audit"
        else:
            return "Workflow execution quality unchanged compared to previous audit"

    def clear_cache(self):
        """Clear audit cache"""
        self._cache.clear()

    def export_report_json(self, report: AuditReport, output_path: str):
        """Export audit report as JSON"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(report.to_dict(), f, indent=2)


# Example usage
if __name__ == "__main__":
    auditor = DDEAuditor()
    print("DDEAuditor initialized")
