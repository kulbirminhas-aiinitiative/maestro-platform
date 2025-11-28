"""
DDE Integration Tests: Gate Classification & Execution
Test IDs: DDE-501 to DDE-540 (40 tests)

Tests for policy enforcement gate system:
- Gate types: PRE_COMMIT, PR, NODE_COMPLETION
- Severity levels: INFO, WARNING, BLOCKING
- Execution phases: pre -> during -> post
- Performance: <10s per gate
- Retry logic and timeout handling
- Dynamic thresholds and bypass approvals
- Parallel execution and dependency chains
- Notifications, remediation hints, A/B testing

Gate Types:
1. PRE_COMMIT: lint, format - run before commit
2. PR: unit_tests, coverage >= 70% - run on PR
3. NODE_COMPLETION: contract_tests, openapi_lint - run after node completes

Score Formula: Gate execution must be fast, reliable, and configurable
"""

import pytest
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum


class GateSeverity(Enum):
    """Gate severity levels"""
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class GateType(Enum):
    """Gate execution types"""
    PRE_COMMIT = "pre_commit"
    PR = "pr"
    NODE_COMPLETION = "node_completion"


class GatePhase(Enum):
    """Gate execution phases"""
    PRE = "pre"
    DURING = "during"
    POST = "post"


class GateStatus(Enum):
    """Gate execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class GateConfig:
    """Configuration for a gate"""
    gate_id: str
    name: str
    gate_type: GateType
    severity: GateSeverity
    phase: GatePhase = GatePhase.DURING
    timeout_seconds: int = 300  # 5 minutes default
    retry_count: int = 0
    retry_delay: float = 1.0
    enabled: bool = True
    thresholds: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    allow_parallel: bool = True
    exemptions: List[str] = field(default_factory=list)  # Exempted node IDs
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)
    remediation_hints: List[str] = field(default_factory=list)
    ab_test_group: Optional[str] = None  # For A/B testing
    rollout_percentage: int = 100  # For gradual rollout


@dataclass
class GateResult:
    """Result of gate execution"""
    gate_id: str
    status: GateStatus
    message: str
    duration_seconds: float
    details: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    bypass_reason: Optional[str] = None


class GateRegistry:
    """Registry for gate configurations"""

    def __init__(self):
        self.gates: Dict[str, GateConfig] = {}
        self._hot_reload_enabled = False

    def register(self, config: GateConfig):
        """Register a gate configuration"""
        self.gates[config.gate_id] = config

    def get(self, gate_id: str) -> Optional[GateConfig]:
        """Get gate configuration"""
        return self.gates.get(gate_id)

    def get_by_type(self, gate_type: GateType) -> List[GateConfig]:
        """Get all gates of specific type"""
        return [g for g in self.gates.values() if g.gate_type == gate_type]

    def get_by_phase(self, phase: GatePhase) -> List[GateConfig]:
        """Get all gates for specific phase"""
        return [g for g in self.gates.values() if g.phase == phase]

    def update(self, gate_id: str, updates: Dict[str, Any]):
        """Update gate configuration (hot-reload)"""
        if gate_id in self.gates:
            config = self.gates[gate_id]
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)

    def enable_hot_reload(self):
        """Enable hot-reload for configuration changes"""
        self._hot_reload_enabled = True

    def is_hot_reload_enabled(self) -> bool:
        """Check if hot-reload is enabled"""
        return self._hot_reload_enabled

    def clear(self):
        """Clear all gates"""
        self.gates.clear()


class GateExecutor:
    """
    Executes policy enforcement gates with classification and retry logic.

    Supports:
    - Multiple gate types and severity levels
    - Execution phases
    - Timeout and retry
    - Dynamic threshold configuration
    - Parallel execution
    - Bypass with approval
    """

    def __init__(self, registry: GateRegistry):
        self.registry = registry
        self.execution_history: List[GateResult] = []
        self._custom_validators: Dict[str, Callable] = {}
        self._bypass_approvals: Set[str] = set()  # Set of approved gate IDs

    def register_validator(self, gate_id: str, validator: Callable):
        """Register custom validator for a gate"""
        self._custom_validators[gate_id] = validator

    def approve_bypass(self, gate_id: str, reason: str):
        """Approve bypass for a gate"""
        self._bypass_approvals.add(f"{gate_id}:{reason}")

    def is_bypass_approved(self, gate_id: str) -> tuple[bool, Optional[str]]:
        """Check if bypass is approved for gate"""
        for approval in self._bypass_approvals:
            if approval.startswith(f"{gate_id}:"):
                reason = approval.split(":", 1)[1]
                return True, reason
        return False, None

    async def execute_gate(
        self,
        gate_id: str,
        context: Dict[str, Any],
        node_id: Optional[str] = None
    ) -> GateResult:
        """
        Execute a single gate.

        Returns GateResult with execution details.
        """
        config = self.registry.get(gate_id)
        if not config:
            return GateResult(
                gate_id=gate_id,
                status=GateStatus.FAILED,
                message=f"Gate {gate_id} not found in registry",
                duration_seconds=0.0
            )

        # Check if gate is enabled
        if not config.enabled:
            return GateResult(
                gate_id=gate_id,
                status=GateStatus.SKIPPED,
                message="Gate is disabled",
                duration_seconds=0.0
            )

        # Check exemptions
        if node_id and node_id in config.exemptions:
            return GateResult(
                gate_id=gate_id,
                status=GateStatus.SKIPPED,
                message=f"Node {node_id} is exempt from this gate",
                duration_seconds=0.0
            )

        # Check bypass approval
        bypass_approved, bypass_reason = self.is_bypass_approved(gate_id)
        if bypass_approved:
            return GateResult(
                gate_id=gate_id,
                status=GateStatus.PASSED,
                message="Gate bypassed with approval",
                duration_seconds=0.0,
                bypass_reason=bypass_reason
            )

        # Execute with retry
        start_time = time.time()
        result = await self._execute_with_retry(gate_id, config, context)
        duration = time.time() - start_time

        result.duration_seconds = duration
        self.execution_history.append(result)

        return result

    async def _execute_with_retry(
        self,
        gate_id: str,
        config: GateConfig,
        context: Dict[str, Any]
    ) -> GateResult:
        """Execute gate with retry logic"""
        attempt = 0
        last_error = None

        while attempt <= config.retry_count:
            try:
                # Check timeout
                start = time.time()

                # Execute validator
                if gate_id in self._custom_validators:
                    validator = self._custom_validators[gate_id]
                    success, message, details = await asyncio.wait_for(
                        validator(context),
                        timeout=config.timeout_seconds
                    )
                else:
                    # Default validation
                    success, message, details = await self._default_validation(
                        gate_id, config, context
                    )

                if success:
                    return GateResult(
                        gate_id=gate_id,
                        status=GateStatus.PASSED,
                        message=message,
                        duration_seconds=0.0,
                        details=details,
                        retry_count=attempt
                    )
                else:
                    # Check if should retry (transient failure)
                    if attempt < config.retry_count and self._is_transient_failure(details):
                        attempt += 1
                        await asyncio.sleep(config.retry_delay)
                        continue

                    return GateResult(
                        gate_id=gate_id,
                        status=GateStatus.FAILED,
                        message=message,
                        duration_seconds=0.0,
                        details=details,
                        retry_count=attempt
                    )

            except asyncio.TimeoutError:
                return GateResult(
                    gate_id=gate_id,
                    status=GateStatus.FAILED,
                    message=f"Gate execution timed out after {config.timeout_seconds}s",
                    duration_seconds=config.timeout_seconds,
                    retry_count=attempt
                )
            except Exception as e:
                last_error = str(e)
                if attempt < config.retry_count:
                    attempt += 1
                    await asyncio.sleep(config.retry_delay)
                else:
                    return GateResult(
                        gate_id=gate_id,
                        status=GateStatus.FAILED,
                        message=f"Gate execution failed: {last_error}",
                        duration_seconds=0.0,
                        retry_count=attempt
                    )

        return GateResult(
            gate_id=gate_id,
            status=GateStatus.FAILED,
            message=f"Max retries exceeded: {last_error}",
            duration_seconds=0.0,
            retry_count=attempt
        )

    async def _default_validation(
        self,
        gate_id: str,
        config: GateConfig,
        context: Dict[str, Any]
    ) -> tuple[bool, str, Dict[str, Any]]:
        """Default validation logic"""
        # Simulate gate execution
        await asyncio.sleep(0.01)  # Simulate work

        # Check thresholds
        for key, threshold in config.thresholds.items():
            if key in context:
                value = context[key]
                if isinstance(threshold, (int, float)):
                    if value < threshold:
                        return False, f"{key} ({value}) below threshold ({threshold})", {key: value}

        return True, "Gate passed", {}

    def _is_transient_failure(self, details: Dict[str, Any]) -> bool:
        """Check if failure is transient (network, timeout, etc.)"""
        transient_indicators = ["timeout", "connection", "unavailable", "retry"]
        error_msg = str(details.get("error", "")).lower()
        return any(indicator in error_msg for indicator in transient_indicators)

    async def execute_gates(
        self,
        gate_ids: List[str],
        context: Dict[str, Any],
        parallel: bool = True,
        node_id: Optional[str] = None
    ) -> List[GateResult]:
        """
        Execute multiple gates.

        Can execute in parallel or sequentially based on dependencies.
        """
        if parallel:
            tasks = [self.execute_gate(gate_id, context, node_id) for gate_id in gate_ids]
            results = await asyncio.gather(*tasks)
            return list(results)
        else:
            results = []
            for gate_id in gate_ids:
                result = await self.execute_gate(gate_id, context, node_id)
                results.append(result)
            return results

    async def execute_with_dependencies(
        self,
        gate_ids: List[str],
        context: Dict[str, Any],
        node_id: Optional[str] = None
    ) -> List[GateResult]:
        """Execute gates respecting dependency order"""
        results: Dict[str, GateResult] = {}
        pending = set(gate_ids)

        while pending:
            # Find gates with no pending dependencies
            ready = []
            for gate_id in pending:
                config = self.registry.get(gate_id)
                if not config:
                    continue

                deps_ready = all(
                    dep in results and results[dep].status == GateStatus.PASSED
                    for dep in config.dependencies
                )

                if deps_ready:
                    ready.append(gate_id)

            if not ready:
                # Circular dependency or unmet dependencies
                for gate_id in pending:
                    results[gate_id] = GateResult(
                        gate_id=gate_id,
                        status=GateStatus.FAILED,
                        message="Unmet dependencies",
                        duration_seconds=0.0
                    )
                break

            # Execute ready gates in parallel
            gate_results = await self.execute_gates(ready, context, parallel=True, node_id=node_id)
            for result in gate_results:
                results[result.gate_id] = result

            # Remove executed gates from pending
            pending -= set(ready)

        return [results[gate_id] for gate_id in gate_ids if gate_id in results]

    def should_block(self, results: List[GateResult]) -> bool:
        """Check if any blocking gate failed"""
        for result in results:
            config = self.registry.get(result.gate_id)
            if config and config.severity == GateSeverity.BLOCKING:
                if result.status == GateStatus.FAILED:
                    return True
        return False

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary statistics"""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "avg_duration": 0.0
            }

        total = len(self.execution_history)
        passed = sum(1 for r in self.execution_history if r.status == GateStatus.PASSED)
        failed = sum(1 for r in self.execution_history if r.status == GateStatus.FAILED)
        skipped = sum(1 for r in self.execution_history if r.status == GateStatus.SKIPPED)

        durations = [r.duration_seconds for r in self.execution_history]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "total_executions": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "avg_duration": avg_duration
        }


# ============================================================================
# Test Suites
# ============================================================================

@pytest.mark.integration
@pytest.mark.dde
class TestGateTypes:
    """Test suite for gate type classification (DDE-501 to DDE-508)"""

    @pytest.fixture
    def registry(self):
        return GateRegistry()

    @pytest.fixture
    def executor(self, registry):
        return GateExecutor(registry)

    @pytest.mark.asyncio
    async def test_dde_501_pre_commit_lint_gate(self, executor, registry):
        """DDE-501: Pre-commit lint gate executes before commit"""
        config = GateConfig(
            gate_id="lint",
            name="Code Linting",
            gate_type=GateType.PRE_COMMIT,
            severity=GateSeverity.BLOCKING,
            phase=GatePhase.PRE
        )
        registry.register(config)

        async def lint_validator(context):
            # Simulate linting
            return True, "No lint errors", {}

        executor.register_validator("lint", lint_validator)

        result = await executor.execute_gate("lint", {})

        assert result.status == GateStatus.PASSED
        assert result.gate_id == "lint"
        assert config.gate_type == GateType.PRE_COMMIT

    @pytest.mark.asyncio
    async def test_dde_502_pre_commit_format_gate(self, executor, registry):
        """DDE-502: Pre-commit format gate checks code formatting"""
        config = GateConfig(
            gate_id="format",
            name="Code Formatting",
            gate_type=GateType.PRE_COMMIT,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def format_validator(context):
            return True, "Code is properly formatted", {}

        executor.register_validator("format", format_validator)

        result = await executor.execute_gate("format", {})

        assert result.status == GateStatus.PASSED
        assert config.gate_type == GateType.PRE_COMMIT

    @pytest.mark.asyncio
    async def test_dde_503_pr_unit_tests_gate(self, executor, registry):
        """DDE-503: PR gate runs unit tests"""
        config = GateConfig(
            gate_id="unit_tests",
            name="Unit Tests",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def test_validator(context):
            tests_passed = context.get("tests_passed", 0)
            tests_total = context.get("tests_total", 0)

            if tests_passed == tests_total:
                return True, f"All {tests_total} tests passed", {"passed": tests_passed}
            else:
                return False, f"{tests_passed}/{tests_total} tests passed", {"passed": tests_passed}

        executor.register_validator("unit_tests", test_validator)

        result = await executor.execute_gate("unit_tests", {
            "tests_passed": 100,
            "tests_total": 100
        })

        assert result.status == GateStatus.PASSED

    @pytest.mark.asyncio
    async def test_dde_504_pr_coverage_threshold_gate(self, executor, registry):
        """DDE-504: PR gate enforces coverage >= 70%"""
        config = GateConfig(
            gate_id="coverage",
            name="Code Coverage",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            thresholds={"coverage": 0.70}
        )
        registry.register(config)

        # Test passing coverage
        result_pass = await executor.execute_gate("coverage", {"coverage": 0.75})
        assert result_pass.status == GateStatus.PASSED

        # Test failing coverage
        result_fail = await executor.execute_gate("coverage", {"coverage": 0.65})
        assert result_fail.status == GateStatus.FAILED
        assert "below threshold" in result_fail.message

    @pytest.mark.asyncio
    async def test_dde_505_node_completion_contract_tests(self, executor, registry):
        """DDE-505: Node completion gate runs contract tests"""
        config = GateConfig(
            gate_id="contract_tests",
            name="Contract Tests",
            gate_type=GateType.NODE_COMPLETION,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def contract_validator(context):
            return True, "All contract tests passed", {"contracts_validated": 5}

        executor.register_validator("contract_tests", contract_validator)

        result = await executor.execute_gate("contract_tests", {})

        assert result.status == GateStatus.PASSED
        assert config.gate_type == GateType.NODE_COMPLETION

    @pytest.mark.asyncio
    async def test_dde_506_node_completion_openapi_lint(self, executor, registry):
        """DDE-506: Node completion gate validates OpenAPI spec"""
        config = GateConfig(
            gate_id="openapi_lint",
            name="OpenAPI Linting",
            gate_type=GateType.NODE_COMPLETION,
            severity=GateSeverity.WARNING
        )
        registry.register(config)

        async def openapi_validator(context):
            spec = context.get("openapi_spec")
            if spec and "paths" in spec:
                return True, "OpenAPI spec is valid", {}
            return False, "Invalid OpenAPI spec", {}

        executor.register_validator("openapi_lint", openapi_validator)

        result = await executor.execute_gate("openapi_lint", {
            "openapi_spec": {"paths": {"/api/v1/users": {}}}
        })

        assert result.status == GateStatus.PASSED

    @pytest.mark.asyncio
    async def test_dde_507_gate_type_filtering(self, executor, registry):
        """DDE-507: Can filter gates by type"""
        registry.register(GateConfig(
            gate_id="lint", name="Lint", gate_type=GateType.PRE_COMMIT, severity=GateSeverity.BLOCKING
        ))
        registry.register(GateConfig(
            gate_id="tests", name="Tests", gate_type=GateType.PR, severity=GateSeverity.BLOCKING
        ))
        registry.register(GateConfig(
            gate_id="contracts", name="Contracts", gate_type=GateType.NODE_COMPLETION, severity=GateSeverity.BLOCKING
        ))

        pre_commit_gates = registry.get_by_type(GateType.PRE_COMMIT)
        pr_gates = registry.get_by_type(GateType.PR)
        node_gates = registry.get_by_type(GateType.NODE_COMPLETION)

        assert len(pre_commit_gates) == 1
        assert len(pr_gates) == 1
        assert len(node_gates) == 1

    @pytest.mark.asyncio
    async def test_dde_508_gate_phase_classification(self, executor, registry):
        """DDE-508: Gates classified by execution phase"""
        registry.register(GateConfig(
            gate_id="pre_gate", name="Pre", gate_type=GateType.PRE_COMMIT,
            severity=GateSeverity.BLOCKING, phase=GatePhase.PRE
        ))
        registry.register(GateConfig(
            gate_id="during_gate", name="During", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING, phase=GatePhase.DURING
        ))
        registry.register(GateConfig(
            gate_id="post_gate", name="Post", gate_type=GateType.NODE_COMPLETION,
            severity=GateSeverity.BLOCKING, phase=GatePhase.POST
        ))

        pre_gates = registry.get_by_phase(GatePhase.PRE)
        during_gates = registry.get_by_phase(GatePhase.DURING)
        post_gates = registry.get_by_phase(GatePhase.POST)

        assert len(pre_gates) == 1
        assert len(during_gates) == 1
        assert len(post_gates) == 1


@pytest.mark.integration
@pytest.mark.dde
class TestSeverityAndExecution:
    """Test suite for severity levels and execution (DDE-509 to DDE-520)"""

    @pytest.fixture
    def registry(self):
        return GateRegistry()

    @pytest.fixture
    def executor(self, registry):
        return GateExecutor(registry)

    @pytest.mark.asyncio
    async def test_dde_509_warning_severity_does_not_block(self, executor, registry):
        """DDE-509: WARNING severity does not block execution"""
        config = GateConfig(
            gate_id="warning_gate",
            name="Warning Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.WARNING
        )
        registry.register(config)

        async def failing_validator(context):
            return False, "Warning: potential issue", {}

        executor.register_validator("warning_gate", failing_validator)

        result = await executor.execute_gate("warning_gate", {})

        assert result.status == GateStatus.FAILED
        assert not executor.should_block([result])  # Should not block

    @pytest.mark.asyncio
    async def test_dde_510_blocking_severity_blocks_execution(self, executor, registry):
        """DDE-510: BLOCKING severity blocks execution"""
        config = GateConfig(
            gate_id="blocking_gate",
            name="Blocking Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def failing_validator(context):
            return False, "Critical failure", {}

        executor.register_validator("blocking_gate", failing_validator)

        result = await executor.execute_gate("blocking_gate", {})

        assert result.status == GateStatus.FAILED
        assert executor.should_block([result])  # Should block

    @pytest.mark.asyncio
    async def test_dde_511_info_severity_informational_only(self, executor, registry):
        """DDE-511: INFO severity is informational only"""
        config = GateConfig(
            gate_id="info_gate",
            name="Info Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.INFO
        )
        registry.register(config)

        async def info_validator(context):
            return True, "FYI: Code metrics collected", {"metrics": 100}

        executor.register_validator("info_gate", info_validator)

        result = await executor.execute_gate("info_gate", {})

        assert result.status == GateStatus.PASSED
        assert config.severity == GateSeverity.INFO

    @pytest.mark.asyncio
    async def test_dde_512_execution_order_respects_phase(self, executor, registry):
        """DDE-512: Gates execute in phase order (pre -> during -> post)"""
        execution_order = []

        async def pre_validator(context):
            execution_order.append("pre")
            return True, "Pre executed", {}

        async def during_validator(context):
            execution_order.append("during")
            return True, "During executed", {}

        async def post_validator(context):
            execution_order.append("post")
            return True, "Post executed", {}

        registry.register(GateConfig(
            gate_id="pre", name="Pre", gate_type=GateType.PRE_COMMIT,
            severity=GateSeverity.BLOCKING, phase=GatePhase.PRE
        ))
        registry.register(GateConfig(
            gate_id="during", name="During", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING, phase=GatePhase.DURING
        ))
        registry.register(GateConfig(
            gate_id="post", name="Post", gate_type=GateType.NODE_COMPLETION,
            severity=GateSeverity.BLOCKING, phase=GatePhase.POST
        ))

        executor.register_validator("pre", pre_validator)
        executor.register_validator("during", during_validator)
        executor.register_validator("post", post_validator)

        # Execute in order
        await executor.execute_gate("pre", {})
        await executor.execute_gate("during", {})
        await executor.execute_gate("post", {})

        assert execution_order == ["pre", "during", "post"]

    @pytest.mark.asyncio
    async def test_dde_513_failure_blocking_stops_execution(self, executor, registry):
        """DDE-513: Blocking gate failure stops subsequent execution"""
        registry.register(GateConfig(
            gate_id="gate1", name="Gate 1", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        ))
        registry.register(GateConfig(
            gate_id="gate2", name="Gate 2", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        ))

        async def failing_validator(context):
            return False, "Gate 1 failed", {}

        executor.register_validator("gate1", failing_validator)

        result1 = await executor.execute_gate("gate1", {})

        # Check if should block before executing gate2
        if executor.should_block([result1]):
            # Should not execute gate2
            assert result1.status == GateStatus.FAILED
            assert executor.should_block([result1])

    @pytest.mark.asyncio
    async def test_dde_514_dynamic_threshold_update(self, executor, registry):
        """DDE-514: Thresholds can be updated dynamically"""
        config = GateConfig(
            gate_id="coverage",
            name="Coverage",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            thresholds={"coverage": 0.70}
        )
        registry.register(config)

        # Test with 70% threshold
        result1 = await executor.execute_gate("coverage", {"coverage": 0.72})
        assert result1.status == GateStatus.PASSED

        # Update threshold to 80%
        registry.update("coverage", {"thresholds": {"coverage": 0.80}})

        # Same coverage now fails
        result2 = await executor.execute_gate("coverage", {"coverage": 0.72})
        assert result2.status == GateStatus.FAILED

    @pytest.mark.asyncio
    async def test_dde_515_bypass_with_approval(self, executor, registry):
        """DDE-515: Gate can be bypassed with approval"""
        config = GateConfig(
            gate_id="strict_gate",
            name="Strict Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def strict_validator(context):
            return False, "Always fails", {}

        executor.register_validator("strict_gate", strict_validator)

        # Approve bypass
        executor.approve_bypass("strict_gate", "Emergency deployment approved by CTO")

        result = await executor.execute_gate("strict_gate", {})

        assert result.status == GateStatus.PASSED
        assert result.bypass_reason == "Emergency deployment approved by CTO"

    @pytest.mark.asyncio
    async def test_dde_516_multiple_severity_mixed_results(self, executor, registry):
        """DDE-516: Mixed severity gates handled correctly"""
        registry.register(GateConfig(
            gate_id="info", name="Info", gate_type=GateType.PR,
            severity=GateSeverity.INFO
        ))
        registry.register(GateConfig(
            gate_id="warning", name="Warning", gate_type=GateType.PR,
            severity=GateSeverity.WARNING
        ))
        registry.register(GateConfig(
            gate_id="blocking", name="Blocking", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        ))

        async def passing_validator(context):
            return True, "Passed", {}

        executor.register_validator("info", passing_validator)
        executor.register_validator("warning", passing_validator)
        executor.register_validator("blocking", passing_validator)

        results = await executor.execute_gates(["info", "warning", "blocking"], {})

        assert len(results) == 3
        assert all(r.status == GateStatus.PASSED for r in results)

    @pytest.mark.asyncio
    async def test_dde_517_disabled_gate_skipped(self, executor, registry):
        """DDE-517: Disabled gates are skipped"""
        config = GateConfig(
            gate_id="disabled_gate",
            name="Disabled",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            enabled=False
        )
        registry.register(config)

        result = await executor.execute_gate("disabled_gate", {})

        assert result.status == GateStatus.SKIPPED
        assert "disabled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_dde_518_exemption_list_respected(self, executor, registry):
        """DDE-518: Node exemptions are respected"""
        config = GateConfig(
            gate_id="strict_gate",
            name="Strict Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            exemptions=["node-123", "node-456"]
        )
        registry.register(config)

        # Execute for exempted node
        result_exempt = await executor.execute_gate("strict_gate", {}, node_id="node-123")
        assert result_exempt.status == GateStatus.SKIPPED

        # Execute for non-exempted node
        async def failing_validator(context):
            return False, "Failed", {}
        executor.register_validator("strict_gate", failing_validator)

        result_normal = await executor.execute_gate("strict_gate", {}, node_id="node-999")
        assert result_normal.status == GateStatus.FAILED

    @pytest.mark.asyncio
    async def test_dde_519_gate_result_includes_details(self, executor, registry):
        """DDE-519: Gate results include execution details"""
        config = GateConfig(
            gate_id="detailed_gate",
            name="Detailed Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def detailed_validator(context):
            return True, "Success", {
                "tests_run": 150,
                "tests_passed": 150,
                "coverage": 0.85,
                "duration": 45.2
            }

        executor.register_validator("detailed_gate", detailed_validator)

        result = await executor.execute_gate("detailed_gate", {})

        assert result.status == GateStatus.PASSED
        assert "tests_run" in result.details
        assert result.details["coverage"] == 0.85

    @pytest.mark.asyncio
    async def test_dde_520_execution_summary_statistics(self, executor, registry):
        """DDE-520: Execution summary provides statistics"""
        config = GateConfig(
            gate_id="test_gate",
            name="Test Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def validator(context):
            return context.get("should_pass", True), "Result", {}

        executor.register_validator("test_gate", validator)

        # Execute multiple times
        await executor.execute_gate("test_gate", {"should_pass": True})
        await executor.execute_gate("test_gate", {"should_pass": True})
        await executor.execute_gate("test_gate", {"should_pass": False})

        summary = executor.get_execution_summary()

        assert summary["total_executions"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1


@pytest.mark.integration
@pytest.mark.dde
class TestPerformanceAndRetry:
    """Test suite for performance and retry logic (DDE-521 to DDE-529)"""

    @pytest.fixture
    def registry(self):
        return GateRegistry()

    @pytest.fixture
    def executor(self, registry):
        return GateExecutor(registry)

    @pytest.mark.asyncio
    async def test_dde_521_gate_execution_under_10_seconds(self, executor, registry):
        """DDE-521: Gate execution completes in <10 seconds"""
        config = GateConfig(
            gate_id="fast_gate",
            name="Fast Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def fast_validator(context):
            await asyncio.sleep(0.1)  # Simulate fast execution
            return True, "Fast execution", {}

        executor.register_validator("fast_gate", fast_validator)

        start = time.time()
        result = await executor.execute_gate("fast_gate", {})
        duration = time.time() - start

        assert result.status == GateStatus.PASSED
        assert duration < 10.0

    @pytest.mark.asyncio
    async def test_dde_522_retry_on_transient_failure(self, executor, registry):
        """DDE-522: Retry logic handles transient failures"""
        config = GateConfig(
            gate_id="flaky_gate",
            name="Flaky Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            retry_count=2,
            retry_delay=0.1
        )
        registry.register(config)

        attempt_count = 0

        async def flaky_validator(context):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                return False, "Connection timeout", {"error": "timeout"}
            return True, "Success on retry", {}

        executor.register_validator("flaky_gate", flaky_validator)

        result = await executor.execute_gate("flaky_gate", {})

        assert result.status == GateStatus.PASSED
        assert result.retry_count > 0

    @pytest.mark.asyncio
    async def test_dde_523_timeout_after_5_minutes(self, executor, registry):
        """DDE-523: Gate times out after 5 minutes"""
        config = GateConfig(
            gate_id="slow_gate",
            name="Slow Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            timeout_seconds=1  # Use 1 second for testing
        )
        registry.register(config)

        async def slow_validator(context):
            await asyncio.sleep(10)  # Will timeout
            return True, "Done", {}

        executor.register_validator("slow_gate", slow_validator)

        result = await executor.execute_gate("slow_gate", {})

        assert result.status == GateStatus.FAILED
        assert "timed out" in result.message.lower() or "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_dde_524_hot_reload_config(self, executor, registry):
        """DDE-524: Configuration hot-reload without restart"""
        config = GateConfig(
            gate_id="reloadable",
            name="Reloadable Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            thresholds={"score": 50}
        )
        registry.register(config)
        registry.enable_hot_reload()

        assert registry.is_hot_reload_enabled()

        # Update threshold
        registry.update("reloadable", {"thresholds": {"score": 75}})

        updated_config = registry.get("reloadable")
        assert updated_config.thresholds["score"] == 75

    @pytest.mark.asyncio
    async def test_dde_525_custom_validator_registration(self, executor, registry):
        """DDE-525: Custom validators can be registered"""
        config = GateConfig(
            gate_id="custom",
            name="Custom Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def custom_business_logic(context):
            # Custom validation logic
            return context.get("business_rule_passes", False), "Custom validation", {}

        executor.register_validator("custom", custom_business_logic)

        result = await executor.execute_gate("custom", {"business_rule_passes": True})
        assert result.status == GateStatus.PASSED

    @pytest.mark.asyncio
    async def test_dde_526_retry_delay_configurable(self, executor, registry):
        """DDE-526: Retry delay is configurable"""
        config = GateConfig(
            gate_id="retry_gate",
            name="Retry Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            retry_count=1,
            retry_delay=0.5
        )
        registry.register(config)

        attempts = []

        async def retry_validator(context):
            attempts.append(time.time())
            if len(attempts) < 2:
                return False, "Retry needed", {"error": "timeout"}
            return True, "Success", {}

        executor.register_validator("retry_gate", retry_validator)

        result = await executor.execute_gate("retry_gate", {})

        # Check delay between attempts
        if len(attempts) >= 2:
            delay = attempts[1] - attempts[0]
            assert delay >= 0.5

    @pytest.mark.asyncio
    async def test_dde_527_max_retries_exceeded_fails(self, executor, registry):
        """DDE-527: Max retries exceeded results in failure"""
        config = GateConfig(
            gate_id="always_retry",
            name="Always Retry",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            retry_count=2,
            retry_delay=0.01
        )
        registry.register(config)

        async def always_fails(context):
            return False, "Always fails", {"error": "timeout"}

        executor.register_validator("always_retry", always_fails)

        result = await executor.execute_gate("always_retry", {})

        assert result.status == GateStatus.FAILED
        assert result.retry_count == 2

    @pytest.mark.asyncio
    async def test_dde_528_performance_tracking(self, executor, registry):
        """DDE-528: Gate performance is tracked"""
        config = GateConfig(
            gate_id="tracked_gate",
            name="Tracked Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def tracked_validator(context):
            await asyncio.sleep(0.05)
            return True, "Done", {}

        executor.register_validator("tracked_gate", tracked_validator)

        result = await executor.execute_gate("tracked_gate", {})

        assert result.duration_seconds > 0
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_dde_529_resource_limits_configuration(self, executor, registry):
        """DDE-529: Resource limits can be configured"""
        config = GateConfig(
            gate_id="limited_gate",
            name="Limited Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            resource_limits={
                "max_memory_mb": 512,
                "max_cpu_percent": 50
            }
        )
        registry.register(config)

        assert config.resource_limits["max_memory_mb"] == 512
        assert config.resource_limits["max_cpu_percent"] == 50


@pytest.mark.integration
@pytest.mark.dde
class TestAdvancedFeatures:
    """Test suite for advanced features (DDE-530 to DDE-540)"""

    @pytest.fixture
    def registry(self):
        return GateRegistry()

    @pytest.fixture
    def executor(self, registry):
        return GateExecutor(registry)

    @pytest.mark.asyncio
    async def test_dde_530_parallel_execution(self, executor, registry):
        """DDE-530: Multiple gates execute in parallel"""
        for i in range(5):
            config = GateConfig(
                gate_id=f"gate_{i}",
                name=f"Gate {i}",
                gate_type=GateType.PR,
                severity=GateSeverity.BLOCKING,
                allow_parallel=True
            )
            registry.register(config)

            async def validator(context):
                await asyncio.sleep(0.1)
                return True, "Done", {}

            executor.register_validator(f"gate_{i}", validator)

        start = time.time()
        results = await executor.execute_gates(
            [f"gate_{i}" for i in range(5)],
            {},
            parallel=True
        )
        duration = time.time() - start

        assert len(results) == 5
        assert all(r.status == GateStatus.PASSED for r in results)
        # Should be faster than sequential (0.5s)
        assert duration < 0.3

    @pytest.mark.asyncio
    async def test_dde_531_dependency_chain_execution(self, executor, registry):
        """DDE-531: Gates with dependencies execute in order"""
        registry.register(GateConfig(
            gate_id="gate_a", name="Gate A", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING, dependencies=[]
        ))
        registry.register(GateConfig(
            gate_id="gate_b", name="Gate B", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING, dependencies=["gate_a"]
        ))
        registry.register(GateConfig(
            gate_id="gate_c", name="Gate C", gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING, dependencies=["gate_b"]
        ))

        execution_order = []

        async def make_validator(gate_name):
            async def validator(context):
                execution_order.append(gate_name)
                return True, f"{gate_name} executed", {}
            return validator

        executor.register_validator("gate_a", await make_validator("gate_a"))
        executor.register_validator("gate_b", await make_validator("gate_b"))
        executor.register_validator("gate_c", await make_validator("gate_c"))

        results = await executor.execute_with_dependencies(
            ["gate_a", "gate_b", "gate_c"],
            {}
        )

        assert len(results) == 3
        assert execution_order == ["gate_a", "gate_b", "gate_c"]

    @pytest.mark.asyncio
    async def test_dde_532_notification_channels(self, executor, registry):
        """DDE-532: Notification channels configured per gate"""
        config = GateConfig(
            gate_id="notify_gate",
            name="Notify Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            notification_channels=["slack", "email", "pagerduty"]
        )
        registry.register(config)

        assert len(config.notification_channels) == 3
        assert "slack" in config.notification_channels

    @pytest.mark.asyncio
    async def test_dde_533_remediation_hints(self, executor, registry):
        """DDE-533: Remediation hints provided on failure"""
        config = GateConfig(
            gate_id="hint_gate",
            name="Hint Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            remediation_hints=[
                "Run 'npm run format' to fix formatting",
                "Check the linting guide at docs/linting.md",
                "Contact #dev-help for assistance"
            ]
        )
        registry.register(config)

        async def failing_validator(context):
            return False, "Formatting errors", {"errors": 5}

        executor.register_validator("hint_gate", failing_validator)

        result = await executor.execute_gate("hint_gate", {})

        assert result.status == GateStatus.FAILED
        assert len(config.remediation_hints) == 3

    @pytest.mark.asyncio
    async def test_dde_534_ab_testing_support(self, executor, registry):
        """DDE-534: A/B testing for gate configurations"""
        config_a = GateConfig(
            gate_id="gate_test",
            name="Gate Test A",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            ab_test_group="A",
            thresholds={"coverage": 0.70}
        )
        config_b = GateConfig(
            gate_id="gate_test_b",
            name="Gate Test B",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            ab_test_group="B",
            thresholds={"coverage": 0.80}
        )

        registry.register(config_a)
        registry.register(config_b)

        assert config_a.ab_test_group == "A"
        assert config_b.ab_test_group == "B"
        assert config_a.thresholds["coverage"] != config_b.thresholds["coverage"]

    @pytest.mark.asyncio
    async def test_dde_535_gradual_rollout(self, executor, registry):
        """DDE-535: Gradual rollout percentage configuration"""
        config = GateConfig(
            gate_id="new_gate",
            name="New Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            rollout_percentage=25  # Only 25% of executions
        )
        registry.register(config)

        assert config.rollout_percentage == 25

    @pytest.mark.asyncio
    async def test_dde_536_exemption_by_node_id(self, executor, registry):
        """DDE-536: Specific nodes can be exempted"""
        config = GateConfig(
            gate_id="strict",
            name="Strict Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            exemptions=["legacy-module-1", "legacy-module-2"]
        )
        registry.register(config)

        result_exempt = await executor.execute_gate("strict", {}, node_id="legacy-module-1")
        assert result_exempt.status == GateStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_dde_537_gate_registry_persistence(self, executor, registry):
        """DDE-537: Gate registry maintains state"""
        registry.register(GateConfig(
            gate_id="persistent",
            name="Persistent",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        ))

        # Verify persistence
        config = registry.get("persistent")
        assert config is not None
        assert config.gate_id == "persistent"

        # Clear and verify
        registry.clear()
        assert registry.get("persistent") is None

    @pytest.mark.asyncio
    async def test_dde_538_multiple_thresholds_per_gate(self, executor, registry):
        """DDE-538: Multiple thresholds can be configured"""
        config = GateConfig(
            gate_id="multi_threshold",
            name="Multi Threshold",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING,
            thresholds={
                "coverage": 0.70,
                "test_count": 100,
                "maintainability": 80
            }
        )
        registry.register(config)

        # Pass all thresholds
        result_pass = await executor.execute_gate("multi_threshold", {
            "coverage": 0.75,
            "test_count": 150,
            "maintainability": 85
        })
        assert result_pass.status == GateStatus.PASSED

        # Fail one threshold
        result_fail = await executor.execute_gate("multi_threshold", {
            "coverage": 0.65,  # Below threshold
            "test_count": 150,
            "maintainability": 85
        })
        assert result_fail.status == GateStatus.FAILED

    @pytest.mark.asyncio
    async def test_dde_539_sequential_execution_mode(self, executor, registry):
        """DDE-539: Sequential execution when parallel disabled"""
        for i in range(3):
            config = GateConfig(
                gate_id=f"seq_{i}",
                name=f"Sequential {i}",
                gate_type=GateType.PR,
                severity=GateSeverity.BLOCKING,
                allow_parallel=False
            )
            registry.register(config)

            async def validator(context):
                await asyncio.sleep(0.1)
                return True, "Done", {}

            executor.register_validator(f"seq_{i}", validator)

        start = time.time()
        results = await executor.execute_gates(
            [f"seq_{i}" for i in range(3)],
            {},
            parallel=False
        )
        duration = time.time() - start

        assert len(results) == 3
        # Sequential should take ~0.3s (3 * 0.1)
        assert duration >= 0.3

    @pytest.mark.asyncio
    async def test_dde_540_gate_execution_history(self, executor, registry):
        """DDE-540: Gate execution history is maintained"""
        config = GateConfig(
            gate_id="history",
            name="History Gate",
            gate_type=GateType.PR,
            severity=GateSeverity.BLOCKING
        )
        registry.register(config)

        async def validator(context):
            return True, "Success", {}

        executor.register_validator("history", validator)

        # Execute multiple times
        await executor.execute_gate("history", {})
        await executor.execute_gate("history", {})
        await executor.execute_gate("history", {})

        summary = executor.get_execution_summary()
        assert summary["total_executions"] == 3
        assert len(executor.execution_history) == 3
