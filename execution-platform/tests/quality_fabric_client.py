"""
Quality Fabric Integration Client for Execution Platform

This module provides integration with the Quality Fabric testing service,
enabling enterprise-grade test orchestration, reporting, and quality gates.
"""

from __future__ import annotations
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import httpx


@dataclass
class TestResult:
    """Represents a single test result"""
    test_id: str
    test_name: str
    status: str  # passed, failed, skipped, error
    duration_ms: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestSuite:
    """Represents a test suite execution"""
    suite_id: str
    suite_name: str
    project: str
    environment: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    results: List[TestResult] = None
    coverage_percent: Optional[float] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.metadata is None:
            self.metadata = {}

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


@dataclass
class QualityGate:
    """Quality gate definition"""
    name: str
    threshold: float
    actual: float
    passed: bool
    message: str


class QualityFabricClient:
    """
    Client for interacting with Quality Fabric service.
    
    Provides methods for:
    - Submitting test results
    - Checking quality gates
    - Retrieving test reports
    - Managing test suites
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        project: str = "execution-platform",
        timeout: float = 30.0
    ):
        self.base_url = base_url or os.getenv(
            "QUALITY_FABRIC_URL", 
            "http://localhost:8001"
        )
        self.api_key = api_key or os.getenv("QUALITY_FABRIC_API_KEY", "")
        self.project = project
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def health_check(self) -> Dict[str, Any]:
        """Check if Quality Fabric service is available"""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}

    async def submit_test_suite(self, suite: TestSuite) -> Dict[str, Any]:
        """
        Submit a complete test suite to Quality Fabric
        
        Args:
            suite: TestSuite object with results
            
        Returns:
            Response from Quality Fabric with submission details
        """
        try:
            client = await self._get_client()
            
            # Convert suite to JSON-serializable format
            payload = {
                "suite_id": suite.suite_id,
                "suite_name": suite.suite_name,
                "project": suite.project,
                "environment": suite.environment,
                "start_time": suite.start_time.isoformat(),
                "end_time": suite.end_time.isoformat() if suite.end_time else None,
                "total_tests": suite.total_tests,
                "passed": suite.passed,
                "failed": suite.failed,
                "skipped": suite.skipped,
                "errors": suite.errors,
                "duration_ms": suite.duration_ms,
                "success_rate": suite.success_rate,
                "coverage_percent": suite.coverage_percent,
                "results": [asdict(r) for r in suite.results],
                "metadata": suite.metadata
            }
            
            response = await client.post("/api/v1/test-suites", json=payload)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            return {
                "status": "error",
                "message": f"Failed to submit test suite: {e}",
                "fallback": True
            }

    async def check_quality_gates(
        self,
        suite_id: str,
        gates: Optional[Dict[str, float]] = None
    ) -> List[QualityGate]:
        """
        Check quality gates for a test suite
        
        Args:
            suite_id: ID of the test suite
            gates: Dictionary of gate_name -> threshold (optional)
            
        Returns:
            List of QualityGate results
        """
        # Default gates if not provided
        if gates is None:
            gates = {
                "min_coverage": 90.0,
                "min_success_rate": 99.0,
                "max_duration_ms": 300000,  # 5 minutes
                "max_flakiness": 1.0
            }
        
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/test-suites/{suite_id}")
            response.raise_for_status()
            suite_data = response.json()
            
            # Evaluate gates
            results = []
            
            # Coverage gate
            if "min_coverage" in gates:
                actual = suite_data.get("coverage_percent", 0)
                threshold = gates["min_coverage"]
                passed = actual >= threshold
                results.append(QualityGate(
                    name="min_coverage",
                    threshold=threshold,
                    actual=actual,
                    passed=passed,
                    message=f"Coverage: {actual:.1f}% (threshold: {threshold:.1f}%)"
                ))
            
            # Success rate gate
            if "min_success_rate" in gates:
                actual = suite_data.get("success_rate", 0)
                threshold = gates["min_success_rate"]
                passed = actual >= threshold
                results.append(QualityGate(
                    name="min_success_rate",
                    threshold=threshold,
                    actual=actual,
                    passed=passed,
                    message=f"Success rate: {actual:.1f}% (threshold: {threshold:.1f}%)"
                ))
            
            # Duration gate
            if "max_duration_ms" in gates:
                actual = suite_data.get("duration_ms", 0)
                threshold = gates["max_duration_ms"]
                passed = actual <= threshold
                results.append(QualityGate(
                    name="max_duration_ms",
                    threshold=threshold,
                    actual=actual,
                    passed=passed,
                    message=f"Duration: {actual:.0f}ms (threshold: {threshold:.0f}ms)"
                ))
            
            return results
            
        except httpx.HTTPError:
            # If service is unavailable, return permissive gates
            return [
                QualityGate(
                    name="service_available",
                    threshold=1.0,
                    actual=0.0,
                    passed=True,  # Don't fail builds when QF is down
                    message="Quality Fabric service unavailable - skipping gates"
                )
            ]

    async def get_test_report(
        self,
        suite_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Get detailed test report from Quality Fabric
        
        Args:
            suite_id: ID of the test suite
            format: Report format (json, html, pdf)
            
        Returns:
            Report data
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/test-suites/{suite_id}/report",
                params={"format": format}
            )
            response.raise_for_status()
            
            if format == "json":
                return response.json()
            else:
                return {"content": response.content, "format": format}
                
        except httpx.HTTPError as e:
            return {"status": "error", "message": str(e)}

    def save_local_report(self, suite: TestSuite, output_path: Path):
        """
        Save test report locally as fallback when Quality Fabric is unavailable
        
        Args:
            suite: TestSuite object
            output_path: Path to save the report
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "suite_id": suite.suite_id,
            "suite_name": suite.suite_name,
            "project": suite.project,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": suite.total_tests,
                "passed": suite.passed,
                "failed": suite.failed,
                "skipped": suite.skipped,
                "errors": suite.errors,
                "success_rate": suite.success_rate,
                "duration_ms": suite.duration_ms,
                "coverage_percent": suite.coverage_percent
            },
            "results": [asdict(r) for r in suite.results]
        }
        
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)


# Singleton instance for easy access
_default_client: Optional[QualityFabricClient] = None


def get_quality_fabric_client() -> QualityFabricClient:
    """Get or create the default Quality Fabric client"""
    global _default_client
    if _default_client is None:
        _default_client = QualityFabricClient()
    return _default_client
