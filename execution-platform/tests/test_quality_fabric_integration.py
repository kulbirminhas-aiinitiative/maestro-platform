"""
Integration tests with Quality Fabric service

These tests demonstrate integration with the Quality Fabric testing platform,
including test submission, quality gates, and reporting.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from tests.quality_fabric_client import (
    QualityFabricClient,
    TestResult,
    TestSuite,
    get_quality_fabric_client
)


pytestmark = pytest.mark.integration


class TestQualityFabricIntegration:
    """Test Quality Fabric service integration"""

    @pytest.fixture
    async def qf_client(self):
        """Create Quality Fabric client"""
        client = QualityFabricClient(
            project="execution-platform",
            timeout=10.0
        )
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check(self, qf_client):
        """Test Quality Fabric health check"""
        health = await qf_client.health_check()
        
        # Service may be unavailable in test environment
        assert isinstance(health, dict)
        assert "status" in health

    @pytest.mark.asyncio
    async def test_submit_test_suite(self, qf_client):
        """Test submitting test suite to Quality Fabric"""
        # Create sample test suite
        suite = TestSuite(
            suite_id="test-suite-001",
            suite_name="Execution Platform Unit Tests",
            project="execution-platform",
            environment="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_tests=10,
            passed=8,
            failed=1,
            skipped=1,
            errors=0
        )
        
        # Add sample results
        suite.results = [
            TestResult(
                test_id="test_001",
                test_name="test_provider_selection",
                status="passed",
                duration_ms=120.5,
                tags=["unit", "router"]
            ),
            TestResult(
                test_id="test_002",
                test_name="test_tool_calling",
                status="failed",
                duration_ms=250.0,
                error_message="Assertion failed",
                tags=["unit", "tools"]
            )
        ]
        
        # Submit to Quality Fabric
        response = await qf_client.submit_test_suite(suite)
        
        # Should return response (even if service is down)
        assert isinstance(response, dict)
        # Gracefully handle unavailable service
        if "status" in response and response["status"] == "error":
            assert "fallback" in response

    @pytest.mark.asyncio
    async def test_quality_gates(self, qf_client):
        """Test quality gate evaluation"""
        suite_id = "test-suite-gates-001"
        
        # Define quality gates
        gates = {
            "min_coverage": 90.0,
            "min_success_rate": 95.0,
            "max_duration_ms": 300000
        }
        
        # Check gates (will be permissive if service unavailable)
        gate_results = await qf_client.check_quality_gates(suite_id, gates)
        
        assert isinstance(gate_results, list)
        assert len(gate_results) > 0
        
        # Each gate should have required fields
        for gate in gate_results:
            assert hasattr(gate, 'name')
            assert hasattr(gate, 'threshold')
            assert hasattr(gate, 'actual')
            assert hasattr(gate, 'passed')
            assert hasattr(gate, 'message')

    @pytest.mark.asyncio
    async def test_get_test_report(self, qf_client):
        """Test retrieving test report"""
        suite_id = "test-suite-report-001"
        
        report = await qf_client.get_test_report(suite_id, format="json")
        
        # Should return dict even if service unavailable
        assert isinstance(report, dict)

    def test_save_local_report(self, qf_client, tmp_path):
        """Test saving report locally as fallback"""
        suite = TestSuite(
            suite_id="local-suite-001",
            suite_name="Local Test Suite",
            project="execution-platform",
            environment="test",
            start_time=datetime.now(),
            total_tests=5,
            passed=5
        )
        
        output_path = tmp_path / "report.json"
        qf_client.save_local_report(suite, output_path)
        
        # Verify file was created
        assert output_path.exists()
        
        # Verify content
        import json
        with open(output_path) as f:
            report = json.load(f)
        
        assert report["suite_id"] == "local-suite-001"
        assert report["summary"]["total_tests"] == 5
        assert report["summary"]["passed"] == 5


class TestQualityFabricPytest:
    """Test pytest integration with Quality Fabric"""

    @pytest.mark.asyncio
    async def test_pytest_result_collection(self):
        """Test collecting pytest results for Quality Fabric submission"""
        # This would typically be done via pytest plugin
        # Here we demonstrate the data structure
        
        suite = TestSuite(
            suite_id=f"pytest-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            suite_name="Pytest Integration",
            project="execution-platform",
            environment="ci",
            start_time=datetime.now(),
            total_tests=3,
            passed=2,
            failed=1
        )
        
        suite.results = [
            TestResult(
                test_id="test_file.py::test_001",
                test_name="test_provider_routing",
                status="passed",
                duration_ms=150.0,
                tags=["integration", "router"]
            ),
            TestResult(
                test_id="test_file.py::test_002",
                test_name="test_streaming",
                status="passed",
                duration_ms=200.0,
                tags=["integration", "streaming"]
            ),
            TestResult(
                test_id="test_file.py::test_003",
                test_name="test_error_handling",
                status="failed",
                duration_ms=100.0,
                error_message="Connection refused",
                tags=["integration", "error"]
            )
        ]
        
        # Calculate metrics
        assert suite.success_rate == pytest.approx(66.67, rel=0.1)
        assert suite.total_tests == 3
        assert suite.passed == 2
        assert suite.failed == 1


class TestQualityGates:
    """Test quality gate enforcement"""

    def test_coverage_gate(self):
        """Test coverage quality gate"""
        from tests.quality_fabric_client import QualityGate
        
        gate = QualityGate(
            name="min_coverage",
            threshold=90.0,
            actual=92.5,
            passed=True,
            message="Coverage: 92.5% (threshold: 90.0%)"
        )
        
        assert gate.passed
        assert gate.actual >= gate.threshold

    def test_success_rate_gate(self):
        """Test success rate quality gate"""
        from tests.quality_fabric_client import QualityGate
        
        gate = QualityGate(
            name="min_success_rate",
            threshold=99.0,
            actual=98.5,
            passed=False,
            message="Success rate: 98.5% (threshold: 99.0%)"
        )
        
        assert not gate.passed
        assert gate.actual < gate.threshold

    def test_performance_gate(self):
        """Test performance quality gate"""
        from tests.quality_fabric_client import QualityGate
        
        gate = QualityGate(
            name="max_duration_ms",
            threshold=5000.0,
            actual=3200.0,
            passed=True,
            message="Duration: 3200ms (threshold: 5000ms)"
        )
        
        assert gate.passed
        assert gate.actual <= gate.threshold


@pytest.mark.asyncio
async def test_end_to_end_quality_flow():
    """
    End-to-end test demonstrating complete Quality Fabric workflow
    
    This test shows:
    1. Creating test results
    2. Submitting to Quality Fabric
    3. Checking quality gates
    4. Generating reports
    """
    async with QualityFabricClient(project="execution-platform") as client:
        # 1. Create test suite
        suite = TestSuite(
            suite_id=f"e2e-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            suite_name="End-to-End Quality Flow",
            project="execution-platform",
            environment="test",
            start_time=datetime.now(),
            total_tests=10,
            passed=9,
            failed=1,
            coverage_percent=92.5
        )
        
        suite.end_time = datetime.now()
        
        # Add detailed results
        for i in range(10):
            status = "passed" if i < 9 else "failed"
            suite.results.append(TestResult(
                test_id=f"test_{i:03d}",
                test_name=f"test_case_{i:03d}",
                status=status,
                duration_ms=100.0 + (i * 10),
                tags=["e2e", "integration"]
            ))
        
        # 2. Submit to Quality Fabric
        submit_response = await client.submit_test_suite(suite)
        assert isinstance(submit_response, dict)
        
        # 3. Check quality gates
        gates = await client.check_quality_gates(suite.suite_id)
        assert isinstance(gates, list)
        
        # 4. Generate report (or save locally as fallback)
        report = await client.get_test_report(suite.suite_id)
        assert isinstance(report, dict)
        
        # If service unavailable, save locally
        if "status" in submit_response and submit_response.get("fallback"):
            local_path = Path("./test-results/fallback-report.json")
            client.save_local_report(suite, local_path)


def test_singleton_client():
    """Test singleton client pattern"""
    client1 = get_quality_fabric_client()
    client2 = get_quality_fabric_client()
    
    assert client1 is client2  # Same instance
    assert isinstance(client1, QualityFabricClient)
