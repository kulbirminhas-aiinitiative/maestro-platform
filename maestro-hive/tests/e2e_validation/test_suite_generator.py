#!/usr/bin/env python3
"""
Comprehensive Test Suite Generator - Phase 2

Generates 20 test cases covering the full complexity spectrum:
- Simple workflows (5 tests)
- Medium complexity (7 tests)
- Complex workflows (5 tests)
- Edge cases (3 tests)

Each test programmatically creates a DAG workflow with realistic scenarios
and validates the complete integration stack.
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    NodeType,
    RetryPolicy,
    ExecutionMode
)
from dag_executor import DAGExecutor, WorkflowContextStore

logger = logging.getLogger(__name__)


# =============================================================================
# TEST DATA MODELS
# =============================================================================

@dataclass
class TestCase:
    """Represents a single test case"""
    test_id: str
    name: str
    category: str  # simple, medium, complex, edge
    description: str
    workflow: WorkflowDAG
    expected_outcome: str  # pass, fail, partial
    expected_failures: List[str]  # Node IDs expected to fail
    complexity_score: int  # 1-10
    validates: List[str]  # What this test validates


@dataclass
class TestResult:
    """Result of running a test case"""
    test_id: str
    passed: bool
    execution_time_seconds: float
    nodes_executed: int
    nodes_passed: int
    nodes_failed: int
    validation_results: Dict[str, Any]
    error_message: str = ""


# =============================================================================
# MOCK EXECUTORS WITH VARIED BEHAVIORS
# =============================================================================

async def mock_executor_pass(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock executor that always passes with good metrics"""
    await asyncio.sleep(0.1)
    node_id = node_input['node_id']

    return {
        'status': 'completed',
        'phase': node_id,
        'build_success_rate': 0.98,
        'code_quality_score': 8.5,
        'test_coverage': 0.85,
        'security_vulnerabilities': 0,
        'code_review_completion': 1.0,
        'documentation_coverage': 0.75,
        'completeness': 0.95,
        'message': f'{node_id} completed successfully'
    }


async def mock_executor_quality_fail(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock executor that fails quality gates"""
    await asyncio.sleep(0.1)
    node_id = node_input['node_id']

    return {
        'status': 'completed',
        'phase': node_id,
        'build_success_rate': 0.98,
        'code_quality_score': 6.0,  # FAILS threshold
        'test_coverage': 0.60,  # FAILS threshold
        'security_vulnerabilities': 0,
        'code_review_completion': 1.0,
        'documentation_coverage': 0.50,
        'completeness': 0.70,
        'message': f'{node_id} completed with quality issues'
    }


async def mock_executor_security_fail(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock executor that fails security gates"""
    await asyncio.sleep(0.1)
    node_id = node_input['node_id']

    return {
        'status': 'completed',
        'phase': node_id,
        'build_success_rate': 0.98,
        'code_quality_score': 8.5,
        'test_coverage': 0.85,
        'security_vulnerabilities': 5,  # FAILS - has vulnerabilities
        'code_review_completion': 1.0,
        'documentation_coverage': 0.75,
        'completeness': 0.95,
        'message': f'{node_id} completed with security issues'
    }


async def mock_executor_warning_only(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock executor with warning-level issues (non-blocking)"""
    await asyncio.sleep(0.1)
    node_id = node_input['node_id']

    return {
        'status': 'completed',
        'phase': node_id,
        'build_success_rate': 0.98,
        'code_quality_score': 8.5,
        'test_coverage': 0.85,
        'security_vulnerabilities': 0,
        'code_review_completion': 1.0,
        'documentation_coverage': 0.55,  # WARNING - below 70%
        'completeness': 0.90,
        'message': f'{node_id} completed with warnings'
    }


async def mock_executor_slow(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock executor that takes longer (tests timeouts)"""
    await asyncio.sleep(2.0)  # Simulates slow operation
    return await mock_executor_pass(node_input)


async def mock_executor_exception(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock executor that throws an exception"""
    raise Exception("Simulated executor failure")


# =============================================================================
# TEST CASE GENERATORS
# =============================================================================

class TestSuiteGenerator:
    """Generates comprehensive test suite"""

    def __init__(self):
        self.test_cases: List[TestCase] = []

    def generate_all_tests(self) -> List[TestCase]:
        """Generate all 20 test cases"""
        logger.info("Generating comprehensive test suite...")

        # Category 1: Simple workflows (5 tests)
        self.test_cases.extend(self._generate_simple_tests())

        # Category 2: Medium complexity (7 tests)
        self.test_cases.extend(self._generate_medium_tests())

        # Category 3: Complex workflows (5 tests)
        self.test_cases.extend(self._generate_complex_tests())

        # Category 4: Edge cases (3 tests)
        self.test_cases.extend(self._generate_edge_tests())

        logger.info(f"Generated {len(self.test_cases)} test cases")
        return self.test_cases

    def _generate_simple_tests(self) -> List[TestCase]:
        """Generate 5 simple workflow tests"""
        tests = []

        # Test 1: Single phase - pass
        workflow = WorkflowDAG(workflow_id="test-simple-1", name="Single Phase Pass")
        workflow.add_node(WorkflowNode(
            node_id="implementation",
            name="Implementation",
            node_type=NodeType.PHASE,
            executor=mock_executor_pass,
            retry_policy=RetryPolicy(max_attempts=1)
        ))
        tests.append(TestCase(
            test_id="simple-01",
            name="Single Phase - Pass",
            category="simple",
            description="Single implementation phase that passes all gates",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=1,
            validates=["basic_execution", "policy_validation_pass"]
        ))

        # Test 2: Single phase - quality fail
        workflow = WorkflowDAG(workflow_id="test-simple-2", name="Single Phase Fail")
        workflow.add_node(WorkflowNode(
            node_id="implementation",
            name="Implementation",
            node_type=NodeType.PHASE,
            executor=mock_executor_quality_fail,
            retry_policy=RetryPolicy(max_attempts=1)
        ))
        tests.append(TestCase(
            test_id="simple-02",
            name="Single Phase - Quality Fail",
            category="simple",
            description="Single phase fails due to code quality",
            workflow=workflow,
            expected_outcome="fail",
            expected_failures=["implementation"],
            complexity_score=1,
            validates=["blocking_gate_enforcement", "quality_validation"]
        ))

        # Test 3: Single phase - security fail
        workflow = WorkflowDAG(workflow_id="test-simple-3", name="Single Phase Security Fail")
        workflow.add_node(WorkflowNode(
            node_id="implementation",
            name="Implementation",
            node_type=NodeType.PHASE,
            executor=mock_executor_security_fail,
            retry_policy=RetryPolicy(max_attempts=1)
        ))
        tests.append(TestCase(
            test_id="simple-03",
            name="Single Phase - Security Fail",
            category="simple",
            description="Single phase fails due to security vulnerabilities",
            workflow=workflow,
            expected_outcome="fail",
            expected_failures=["implementation"],
            complexity_score=1,
            validates=["security_gate_enforcement"]
        ))

        # Test 4: Single phase - warning only
        workflow = WorkflowDAG(workflow_id="test-simple-4", name="Single Phase Warning")
        workflow.add_node(WorkflowNode(
            node_id="implementation",
            name="Implementation",
            node_type=NodeType.PHASE,
            executor=mock_executor_warning_only,
            retry_policy=RetryPolicy(max_attempts=1)
        ))
        tests.append(TestCase(
            test_id="simple-04",
            name="Single Phase - Warning Only",
            category="simple",
            description="Single phase with non-blocking warnings",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=1,
            validates=["warning_gate_non_blocking"]
        ))

        # Test 5: Two sequential phases - both pass
        workflow = WorkflowDAG(workflow_id="test-simple-5", name="Two Sequential Phases")
        req_node = WorkflowNode(
            node_id="requirements",
            name="Requirements",
            node_type=NodeType.PHASE,
            executor=mock_executor_pass,
            retry_policy=RetryPolicy(max_attempts=1)
        )
        impl_node = WorkflowNode(
            node_id="implementation",
            name="Implementation",
            node_type=NodeType.PHASE,
            executor=mock_executor_pass,
            dependencies=["requirements"],
            retry_policy=RetryPolicy(max_attempts=1)
        )
        workflow.add_node(req_node)
        workflow.add_node(impl_node)
        workflow.add_edge("requirements", "implementation")
        tests.append(TestCase(
            test_id="simple-05",
            name="Two Sequential Phases - Pass",
            category="simple",
            description="Two phases in sequence, both pass",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=2,
            validates=["sequential_execution", "dependency_chaining"]
        ))

        return tests

    def _generate_medium_tests(self) -> List[TestCase]:
        """Generate 7 medium complexity tests"""
        tests = []

        # Test 6: Full 3-phase workflow (req → design → impl)
        workflow = WorkflowDAG(workflow_id="test-medium-1", name="Three Phase Pipeline")
        nodes = [
            WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="design", name="Design", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["requirements"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="implementation", name="Implementation", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["design"],
                        retry_policy=RetryPolicy(max_attempts=1))
        ]
        for node in nodes:
            workflow.add_node(node)
        workflow.add_edge("requirements", "design")
        workflow.add_edge("design", "implementation")
        tests.append(TestCase(
            test_id="medium-01",
            name="Three Phase Pipeline - All Pass",
            category="medium",
            description="Requirements → Design → Implementation pipeline",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=3,
            validates=["multi_phase_workflow", "phase_transitions"]
        ))

        # Test 7: Three phase, middle fails
        workflow = WorkflowDAG(workflow_id="test-medium-2", name="Three Phase Middle Fail")
        nodes = [
            WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="design", name="Design", node_type=NodeType.PHASE,
                        executor=mock_executor_quality_fail, dependencies=["requirements"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="implementation", name="Implementation", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["design"],
                        retry_policy=RetryPolicy(max_attempts=1))
        ]
        for node in nodes:
            workflow.add_node(node)
        workflow.add_edge("requirements", "design")
        workflow.add_edge("design", "implementation")
        tests.append(TestCase(
            test_id="medium-02",
            name="Three Phase - Middle Fails",
            category="medium",
            description="Design phase fails, blocks implementation",
            workflow=workflow,
            expected_outcome="fail",
            expected_failures=["design"],
            complexity_score=3,
            validates=["failure_propagation", "dependency_blocking"]
        ))

        # Test 8: Parallel execution (2 independent phases)
        workflow = WorkflowDAG(workflow_id="test-medium-3", name="Parallel Execution")
        req_node = WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                               executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1))
        backend_node = WorkflowNode(node_id="backend", name="Backend", node_type=NodeType.PHASE,
                                   executor=mock_executor_pass, dependencies=["requirements"],
                                   retry_policy=RetryPolicy(max_attempts=1))
        frontend_node = WorkflowNode(node_id="frontend", name="Frontend", node_type=NodeType.PHASE,
                                    executor=mock_executor_pass, dependencies=["requirements"],
                                    retry_policy=RetryPolicy(max_attempts=1))
        workflow.add_node(req_node)
        workflow.add_node(backend_node)
        workflow.add_node(frontend_node)
        workflow.add_edge("requirements", "backend")
        workflow.add_edge("requirements", "frontend")
        tests.append(TestCase(
            test_id="medium-03",
            name="Parallel Execution - Backend + Frontend",
            category="medium",
            description="Backend and frontend execute in parallel after requirements",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=4,
            validates=["parallel_execution", "concurrent_validation"]
        ))

        # Test 9: Parallel execution, one branch fails
        workflow = WorkflowDAG(workflow_id="test-medium-4", name="Parallel One Fails")
        req_node = WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                               executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1))
        backend_node = WorkflowNode(node_id="backend", name="Backend", node_type=NodeType.PHASE,
                                   executor=mock_executor_pass, dependencies=["requirements"],
                                   retry_policy=RetryPolicy(max_attempts=1))
        frontend_node = WorkflowNode(node_id="frontend", name="Frontend", node_type=NodeType.PHASE,
                                    executor=mock_executor_quality_fail, dependencies=["requirements"],
                                    retry_policy=RetryPolicy(max_attempts=1))
        workflow.add_node(req_node)
        workflow.add_node(backend_node)
        workflow.add_node(frontend_node)
        workflow.add_edge("requirements", "backend")
        workflow.add_edge("requirements", "frontend")
        tests.append(TestCase(
            test_id="medium-04",
            name="Parallel Execution - One Branch Fails",
            category="medium",
            description="Frontend fails while backend succeeds",
            workflow=workflow,
            expected_outcome="fail",
            expected_failures=["frontend"],
            complexity_score=4,
            validates=["parallel_failure_handling"]
        ))

        # Test 10: Four phase workflow
        workflow = WorkflowDAG(workflow_id="test-medium-5", name="Four Phase Workflow")
        nodes = [
            WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="design", name="Design", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["requirements"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="implementation", name="Implementation", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["design"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="testing", name="Testing", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["implementation"],
                        retry_policy=RetryPolicy(max_attempts=1))
        ]
        for node in nodes:
            workflow.add_node(node)
        workflow.add_edge("requirements", "design")
        workflow.add_edge("design", "implementation")
        workflow.add_edge("implementation", "testing")
        tests.append(TestCase(
            test_id="medium-05",
            name="Four Phase Sequential",
            category="medium",
            description="Requirements → Design → Implementation → Testing",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=4,
            validates=["extended_pipeline"]
        ))

        # Test 11: Mixed warnings and passes
        workflow = WorkflowDAG(workflow_id="test-medium-6", name="Mixed Warnings")
        nodes = [
            WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                        executor=mock_executor_warning_only, retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="implementation", name="Implementation", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["requirements"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="testing", name="Testing", node_type=NodeType.PHASE,
                        executor=mock_executor_warning_only, dependencies=["implementation"],
                        retry_policy=RetryPolicy(max_attempts=1))
        ]
        for node in nodes:
            workflow.add_node(node)
        workflow.add_edge("requirements", "implementation")
        workflow.add_edge("implementation", "testing")
        tests.append(TestCase(
            test_id="medium-06",
            name="Mixed Warnings and Passes",
            category="medium",
            description="Multiple phases with non-blocking warnings",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=3,
            validates=["warning_accumulation"]
        ))

        # Test 12: Retry logic test
        workflow = WorkflowDAG(workflow_id="test-medium-7", name="Retry Logic")
        impl_node = WorkflowNode(
            node_id="implementation",
            name="Implementation",
            node_type=NodeType.PHASE,
            executor=mock_executor_quality_fail,  # Will fail and retry
            retry_policy=RetryPolicy(max_attempts=3, retry_on_failure=True, retry_delay_seconds=0)
        )
        workflow.add_node(impl_node)
        tests.append(TestCase(
            test_id="medium-07",
            name="Retry Logic - Multiple Attempts",
            category="medium",
            description="Node fails, retries 3 times",
            workflow=workflow,
            expected_outcome="fail",
            expected_failures=["implementation"],
            complexity_score=2,
            validates=["retry_mechanism"]
        ))

        return tests

    def _generate_complex_tests(self) -> List[TestCase]:
        """Generate 5 complex workflow tests"""
        tests = []

        # Test 13: Full SDLC (6 phases)
        workflow = WorkflowDAG(workflow_id="test-complex-1", name="Full SDLC Pipeline")
        nodes = [
            WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="design", name="Design", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["requirements"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="implementation", name="Implementation", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["design"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="testing", name="Testing", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["implementation"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="deployment", name="Deployment", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["testing"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="monitoring", name="Monitoring", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["deployment"],
                        retry_policy=RetryPolicy(max_attempts=1))
        ]
        for node in nodes:
            workflow.add_node(node)
        workflow.add_edge("requirements", "design")
        workflow.add_edge("design", "implementation")
        workflow.add_edge("implementation", "testing")
        workflow.add_edge("testing", "deployment")
        workflow.add_edge("deployment", "monitoring")
        tests.append(TestCase(
            test_id="complex-01",
            name="Full SDLC - 6 Phases",
            category="complex",
            description="Complete SDLC: Req → Design → Impl → Test → Deploy → Monitor",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=6,
            validates=["full_sdlc_pipeline", "end_to_end_validation"]
        ))

        # Test 14: Diamond pattern (req → design + arch → impl)
        workflow = WorkflowDAG(workflow_id="test-complex-2", name="Diamond Pattern")
        req_node = WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                               executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1))
        design_node = WorkflowNode(node_id="design", name="Design", node_type=NodeType.PHASE,
                                  executor=mock_executor_pass, dependencies=["requirements"],
                                  retry_policy=RetryPolicy(max_attempts=1))
        arch_node = WorkflowNode(node_id="architecture", name="Architecture", node_type=NodeType.PHASE,
                                executor=mock_executor_pass, dependencies=["requirements"],
                                retry_policy=RetryPolicy(max_attempts=1))
        impl_node = WorkflowNode(node_id="implementation", name="Implementation", node_type=NodeType.PHASE,
                                executor=mock_executor_pass, dependencies=["design", "architecture"],
                                retry_policy=RetryPolicy(max_attempts=1))
        workflow.add_node(req_node)
        workflow.add_node(design_node)
        workflow.add_node(arch_node)
        workflow.add_node(impl_node)
        workflow.add_edge("requirements", "design")
        workflow.add_edge("requirements", "architecture")
        workflow.add_edge("design", "implementation")
        workflow.add_edge("architecture", "implementation")
        tests.append(TestCase(
            test_id="complex-02",
            name="Diamond Pattern",
            category="complex",
            description="Diamond dependency: Req → (Design + Arch) → Impl",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=5,
            validates=["diamond_pattern", "multi_dependency_merge"]
        ))

        # Test 15: Parallel branches with merge (backend + frontend → integration)
        workflow = WorkflowDAG(workflow_id="test-complex-3", name="Parallel with Merge")
        req_node = WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                               executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1))
        backend_node = WorkflowNode(node_id="backend", name="Backend", node_type=NodeType.PHASE,
                                   executor=mock_executor_pass, dependencies=["requirements"],
                                   retry_policy=RetryPolicy(max_attempts=1))
        frontend_node = WorkflowNode(node_id="frontend", name="Frontend", node_type=NodeType.PHASE,
                                    executor=mock_executor_pass, dependencies=["requirements"],
                                    retry_policy=RetryPolicy(max_attempts=1))
        integration_node = WorkflowNode(node_id="integration", name="Integration", node_type=NodeType.PHASE,
                                       executor=mock_executor_pass, dependencies=["backend", "frontend"],
                                       retry_policy=RetryPolicy(max_attempts=1))
        workflow.add_node(req_node)
        workflow.add_node(backend_node)
        workflow.add_node(frontend_node)
        workflow.add_node(integration_node)
        workflow.add_edge("requirements", "backend")
        workflow.add_edge("requirements", "frontend")
        workflow.add_edge("backend", "integration")
        workflow.add_edge("frontend", "integration")
        tests.append(TestCase(
            test_id="complex-03",
            name="Parallel Branches with Merge",
            category="complex",
            description="Req → (Backend || Frontend) → Integration",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=5,
            validates=["parallel_merge_point"]
        ))

        # Test 16: Complex with multiple failures
        workflow = WorkflowDAG(workflow_id="test-complex-4", name="Multiple Failures")
        nodes = [
            WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="backend", name="Backend", node_type=NodeType.PHASE,
                        executor=mock_executor_quality_fail, dependencies=["requirements"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="frontend", name="Frontend", node_type=NodeType.PHASE,
                        executor=mock_executor_security_fail, dependencies=["requirements"],
                        retry_policy=RetryPolicy(max_attempts=1)),
            WorkflowNode(node_id="integration", name="Integration", node_type=NodeType.PHASE,
                        executor=mock_executor_pass, dependencies=["backend", "frontend"],
                        retry_policy=RetryPolicy(max_attempts=1))
        ]
        for node in nodes:
            workflow.add_node(node)
        workflow.add_edge("requirements", "backend")
        workflow.add_edge("requirements", "frontend")
        workflow.add_edge("backend", "integration")
        workflow.add_edge("frontend", "integration")
        tests.append(TestCase(
            test_id="complex-04",
            name="Multiple Parallel Failures",
            category="complex",
            description="Both backend and frontend fail different gates",
            workflow=workflow,
            expected_outcome="fail",
            expected_failures=["backend", "frontend"],
            complexity_score=6,
            validates=["multiple_failure_handling"]
        ))

        # Test 17: Wide DAG (many parallel branches)
        workflow = WorkflowDAG(workflow_id="test-complex-5", name="Wide DAG")
        req_node = WorkflowNode(node_id="requirements", name="Requirements", node_type=NodeType.PHASE,
                               executor=mock_executor_pass, retry_policy=RetryPolicy(max_attempts=1))
        workflow.add_node(req_node)

        # Add 5 parallel branches
        for i in range(1, 6):
            node = WorkflowNode(
                node_id=f"service_{i}",
                name=f"Service {i}",
                node_type=NodeType.PHASE,
                executor=mock_executor_pass,
                dependencies=["requirements"],
                retry_policy=RetryPolicy(max_attempts=1)
            )
            workflow.add_node(node)
            workflow.add_edge("requirements", f"service_{i}")

        tests.append(TestCase(
            test_id="complex-05",
            name="Wide DAG - 5 Parallel Services",
            category="complex",
            description="Req → 5 parallel service implementations",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=7,
            validates=["wide_parallelism", "scalability"]
        ))

        return tests

    def _generate_edge_tests(self) -> List[TestCase]:
        """Generate 3 edge case tests"""
        tests = []

        # Test 18: Slow execution (tests timeout handling)
        workflow = WorkflowDAG(workflow_id="test-edge-1", name="Slow Execution")
        slow_node = WorkflowNode(
            node_id="slow_phase",
            name="Slow Phase",
            node_type=NodeType.PHASE,
            executor=mock_executor_slow,
            retry_policy=RetryPolicy(max_attempts=1)
        )
        workflow.add_node(slow_node)
        tests.append(TestCase(
            test_id="edge-01",
            name="Slow Execution",
            category="edge",
            description="Phase takes longer to execute (2 seconds)",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=2,
            validates=["timeout_handling", "performance"]
        ))

        # Test 19: Empty workflow (no nodes)
        workflow = WorkflowDAG(workflow_id="test-edge-2", name="Empty Workflow")
        # Intentionally no nodes added
        tests.append(TestCase(
            test_id="edge-02",
            name="Empty Workflow",
            category="edge",
            description="Workflow with no nodes",
            workflow=workflow,
            expected_outcome="pass",  # Should complete immediately
            expected_failures=[],
            complexity_score=1,
            validates=["empty_workflow_handling"]
        ))

        # Test 20: Non-phase node (custom node type)
        workflow = WorkflowDAG(workflow_id="test-edge-3", name="Non-Phase Node")
        custom_node = WorkflowNode(
            node_id="custom_task",
            name="Custom Task",
            node_type=NodeType.CUSTOM,  # NOT a phase
            executor=mock_executor_pass,
            retry_policy=RetryPolicy(max_attempts=1)
        )
        workflow.add_node(custom_node)
        tests.append(TestCase(
            test_id="edge-03",
            name="Non-Phase Node",
            category="edge",
            description="Custom node type (no contract validation)",
            workflow=workflow,
            expected_outcome="pass",
            expected_failures=[],
            complexity_score=1,
            validates=["custom_node_handling", "validation_skipping"]
        ))

        return tests


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    generator = TestSuiteGenerator()
    test_cases = generator.generate_all_tests()

    print("\n" + "=" * 80)
    print("TEST SUITE GENERATED")
    print("=" * 80)
    print(f"Total test cases: {len(test_cases)}")
    print()

    # Summary by category
    categories = {}
    for test in test_cases:
        categories[test.category] = categories.get(test.category, 0) + 1

    print("By Category:")
    for category, count in sorted(categories.items()):
        print(f"  {category.capitalize()}: {count} tests")

    print()
    print("Test Details:")
    print("-" * 80)
    for test in test_cases:
        print(f"{test.test_id}: {test.name}")
        print(f"   Category: {test.category} | Complexity: {test.complexity_score}/10")
        print(f"   {test.description}")
        print(f"   Validates: {', '.join(test.validates)}")
        print()
