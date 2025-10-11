"""
Unit Tests for Validator Framework
Version: 1.0.0

Comprehensive tests for all validators.
"""

import pytest
import asyncio
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime

from contracts.validators.base import BaseValidator, ValidationResult, ValidationError
from contracts.validators.screenshot_diff import ScreenshotDiffValidator
from contracts.validators.openapi import OpenAPIValidator
from contracts.validators.axe_core import AxeCoreValidator
from contracts.validators.performance import PerformanceValidator
from contracts.validators.security import SecurityValidator


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    import shutil
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_openapi_spec(temp_dir):
    """Create sample OpenAPI spec"""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    spec_path = os.path.join(temp_dir, "openapi.json")
    with open(spec_path, 'w') as f:
        json.dump(spec, f)

    return spec_path


@pytest.fixture
def sample_performance_metrics(temp_dir):
    """Create sample performance metrics"""
    metrics = {
        "load_time_ms": 2500,
        "ttfb_ms": 500,
        "fcp_ms": 1500,
        "lcp_ms": 2200,
        "tti_ms": 3000,
        "cls": 0.05,
        "api_response_ms": 300
    }

    metrics_path = os.path.join(temp_dir, "metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f)

    return metrics_path


@pytest.fixture
def sample_security_scan(temp_dir):
    """Create sample security scan results"""
    scan = {
        "vulnerabilities": [
            {
                "cve_id": "CVE-2021-1234",
                "severity": "high",
                "description": "SQL Injection vulnerability",
                "package": "test-package",
                "fixed_in": "1.2.3"
            }
        ]
    }

    scan_path = os.path.join(temp_dir, "security_scan.json")
    with open(scan_path, 'w') as f:
        json.dump(scan, f)

    return scan_path


# ============================================================================
# Test ValidationResult
# ============================================================================

class TestValidationResult:
    """Tests for ValidationResult dataclass"""

    def test_validation_result_creation(self):
        """Test basic ValidationResult creation"""
        result = ValidationResult(
            passed=True,
            score=0.95,
            message="Test passed",
            details="All checks passed"
        )

        assert result.passed is True
        assert result.score == 0.95
        assert result.message == "Test passed"
        assert result.details == "All checks passed"

    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization"""
        result = ValidationResult(
            passed=True,
            score=1.0,
            message="Success",
            validator_name="TestValidator",
            errors=[],
            warnings=[]
        )

        data = result.to_dict()

        assert data["passed"] is True
        assert data["score"] == 1.0
        assert data["message"] == "Success"
        assert data["validator_name"] == "TestValidator"

    def test_validation_result_from_dict(self):
        """Test ValidationResult deserialization"""
        data = {
            "passed": False,
            "score": 0.5,
            "message": "Failed",
            "details": "Some checks failed",
            "errors": ["Error 1"],
            "warnings": ["Warning 1"]
        }

        result = ValidationResult.from_dict(data)

        assert result.passed is False
        assert result.score == 0.5
        assert result.message == "Failed"
        assert result.errors == ["Error 1"]
        assert result.warnings == ["Warning 1"]


# ============================================================================
# Test BaseValidator
# ============================================================================

class ConcreteValidator(BaseValidator):
    """Concrete validator for testing"""

    async def validate(self, artifacts, config):
        await asyncio.sleep(0.1)  # Simulate work
        return ValidationResult(
            passed=True,
            score=1.0,
            message="Validation successful"
        )


class SlowValidator(BaseValidator):
    """Slow validator for timeout testing"""

    async def validate(self, artifacts, config):
        await asyncio.sleep(5.0)  # Exceeds default timeout
        return ValidationResult(passed=True, score=1.0, message="Done")


class ErrorValidator(BaseValidator):
    """Validator that raises errors"""

    async def validate(self, artifacts, config):
        raise ValidationError("Intentional error for testing")


class TestBaseValidator:
    """Tests for BaseValidator"""

    @pytest.mark.asyncio
    async def test_validator_initialization(self):
        """Test validator initialization"""
        validator = ConcreteValidator(
            validator_name="TestValidator",
            validator_version="1.0.0",
            timeout_seconds=30.0
        )

        assert validator.validator_name == "TestValidator"
        assert validator.validator_version == "1.0.0"
        assert validator.timeout_seconds == 30.0

    @pytest.mark.asyncio
    async def test_validator_execute_success(self):
        """Test successful validation execution"""
        validator = ConcreteValidator("TestValidator")

        result = await validator.execute({}, {})

        assert result.passed is True
        assert result.score == 1.0
        assert result.validator_name == "TestValidator"
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_validator_timeout(self):
        """Test validator timeout handling"""
        validator = SlowValidator("SlowValidator", timeout_seconds=0.5)

        result = await validator.execute({}, {})

        assert result.passed is False
        assert result.score == 0.0
        assert "timeout" in result.message.lower()
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validator_error_handling(self):
        """Test validation error handling"""
        validator = ErrorValidator("ErrorValidator")

        result = await validator.execute({}, {})

        assert result.passed is False
        assert result.score == 0.0
        assert len(result.errors) > 0


# ============================================================================
# Test ScreenshotDiffValidator
# ============================================================================

class TestScreenshotDiffValidator:
    """Tests for ScreenshotDiffValidator"""

    @pytest.mark.asyncio
    async def test_screenshot_validator_initialization(self):
        """Test ScreenshotDiffValidator initialization"""
        validator = ScreenshotDiffValidator(timeout_seconds=60.0)

        assert validator.validator_name == "ScreenshotDiffValidator"
        assert validator.timeout_seconds == 60.0

    @pytest.mark.asyncio
    async def test_screenshot_validator_missing_artifacts(self):
        """Test error when artifacts are missing"""
        validator = ScreenshotDiffValidator()

        result = await validator.execute({}, {})

        assert result.passed is False
        assert "missing" in result.message.lower() or len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_screenshot_validator_nonexistent_files(self):
        """Test error when files don't exist"""
        validator = ScreenshotDiffValidator()

        artifacts = {
            "actual": "/nonexistent/actual.png",
            "expected": "/nonexistent/expected.png"
        }

        result = await validator.execute(artifacts, {})

        assert result.passed is False


# ============================================================================
# Test OpenAPIValidator
# ============================================================================

class TestOpenAPIValidator:
    """Tests for OpenAPIValidator"""

    @pytest.mark.asyncio
    async def test_openapi_validator_initialization(self):
        """Test OpenAPIValidator initialization"""
        validator = OpenAPIValidator()

        assert validator.validator_name == "OpenAPIValidator"

    @pytest.mark.asyncio
    async def test_openapi_validator_valid_spec(self, sample_openapi_spec):
        """Test validation with valid OpenAPI spec"""
        validator = OpenAPIValidator()

        artifacts = {"spec": sample_openapi_spec}
        config = {"strict": True}

        result = await validator.execute(artifacts, config)

        assert result.passed is True
        assert result.score > 0.0
        assert result.evidence["total_endpoints"] == 1

    @pytest.mark.asyncio
    async def test_openapi_validator_missing_spec(self):
        """Test error when spec is missing"""
        validator = OpenAPIValidator()

        result = await validator.execute({}, {})

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_openapi_validator_invalid_spec_path(self):
        """Test error with invalid spec path"""
        validator = OpenAPIValidator()

        artifacts = {"spec": "/nonexistent/spec.json"}

        result = await validator.execute(artifacts, {})

        assert result.passed is False


# ============================================================================
# Test AxeCoreValidator
# ============================================================================

class TestAxeCoreValidator:
    """Tests for AxeCoreValidator"""

    @pytest.mark.asyncio
    async def test_axe_validator_initialization(self):
        """Test AxeCoreValidator initialization"""
        validator = AxeCoreValidator()

        assert validator.validator_name == "AxeCoreValidator"

    @pytest.mark.asyncio
    async def test_axe_validator_simulated_mode(self):
        """Test AxeCoreValidator in simulated mode"""
        validator = AxeCoreValidator()

        artifacts = {"html": "/test/page.html"}
        config = {"level": "AA"}

        result = await validator.execute(artifacts, config)

        # Simulated mode returns no violations
        assert result.passed is True
        assert result.evidence["wcag_level"] == "AA"

    @pytest.mark.asyncio
    async def test_axe_validator_invalid_wcag_level(self):
        """Test error with invalid WCAG level"""
        validator = AxeCoreValidator()

        artifacts = {"html": "/test/page.html"}
        config = {"level": "INVALID"}

        result = await validator.execute(artifacts, config)

        assert result.passed is False


# ============================================================================
# Test PerformanceValidator
# ============================================================================

class TestPerformanceValidator:
    """Tests for PerformanceValidator"""

    @pytest.mark.asyncio
    async def test_performance_validator_initialization(self):
        """Test PerformanceValidator initialization"""
        validator = PerformanceValidator()

        assert validator.validator_name == "PerformanceValidator"

    @pytest.mark.asyncio
    async def test_performance_validator_pass(self, sample_performance_metrics):
        """Test performance validation that passes"""
        validator = PerformanceValidator()

        artifacts = {"metrics": sample_performance_metrics}
        config = {
            "max_load_time_ms": 3000,
            "max_lcp_ms": 2500
        }

        result = await validator.execute(artifacts, config)

        assert result.passed is True
        assert result.score > 0.0

    @pytest.mark.asyncio
    async def test_performance_validator_fail(self, sample_performance_metrics):
        """Test performance validation that fails"""
        validator = PerformanceValidator()

        artifacts = {"metrics": sample_performance_metrics}
        config = {
            "max_load_time_ms": 1000,  # Very strict
            "max_lcp_ms": 1000
        }

        result = await validator.execute(artifacts, config)

        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_performance_validator_metrics_dict(self):
        """Test with metrics as dictionary"""
        validator = PerformanceValidator()

        artifacts = {
            "metrics": {
                "load_time_ms": 2000,
                "lcp_ms": 1800
            }
        }
        config = {"max_load_time_ms": 3000}

        result = await validator.execute(artifacts, config)

        assert result.passed is True


# ============================================================================
# Test SecurityValidator
# ============================================================================

class TestSecurityValidator:
    """Tests for SecurityValidator"""

    @pytest.mark.asyncio
    async def test_security_validator_initialization(self):
        """Test SecurityValidator initialization"""
        validator = SecurityValidator()

        assert validator.validator_name == "SecurityValidator"

    @pytest.mark.asyncio
    async def test_security_validator_with_vulnerabilities(self, sample_security_scan):
        """Test security validation with vulnerabilities"""
        validator = SecurityValidator()

        artifacts = {"scan_results": sample_security_scan}
        config = {"severity_threshold": "high"}

        result = await validator.execute(artifacts, config)

        assert result.passed is False  # Has high severity vuln
        assert result.evidence["high_count"] == 1

    @pytest.mark.asyncio
    async def test_security_validator_threshold(self, sample_security_scan):
        """Test security validation with different threshold"""
        validator = SecurityValidator()

        artifacts = {"scan_results": sample_security_scan}
        config = {"severity_threshold": "critical"}  # Higher threshold

        result = await validator.execute(artifacts, config)

        # High severity vuln should not fail with critical threshold
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_security_validator_allowed_vulns(self, sample_security_scan):
        """Test allowing specific vulnerabilities"""
        validator = SecurityValidator()

        artifacts = {"scan_results": sample_security_scan}
        config = {
            "severity_threshold": "high",
            "allowed_vulnerabilities": ["CVE-2021-1234"]
        }

        result = await validator.execute(artifacts, config)

        assert result.passed is True  # Vuln is allowed

    @pytest.mark.asyncio
    async def test_security_validator_invalid_threshold(self):
        """Test error with invalid threshold"""
        validator = SecurityValidator()

        artifacts = {"scan_results": "/test/scan.json"}
        config = {"severity_threshold": "invalid"}

        result = await validator.execute(artifacts, config)

        assert result.passed is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestValidatorIntegration:
    """Integration tests for validator framework"""

    @pytest.mark.asyncio
    async def test_multiple_validators_execution(self, sample_openapi_spec, sample_performance_metrics):
        """Test executing multiple validators"""
        validators = [
            OpenAPIValidator(),
            PerformanceValidator()
        ]

        results = []

        # Execute OpenAPI validation
        result1 = await validators[0].execute(
            {"spec": sample_openapi_spec},
            {"strict": True}
        )
        results.append(result1)

        # Execute Performance validation
        result2 = await validators[1].execute(
            {"metrics": sample_performance_metrics},
            {"max_load_time_ms": 3000}
        )
        results.append(result2)

        assert len(results) == 2
        assert all(r.execution_time_ms > 0 for r in results)

    @pytest.mark.asyncio
    async def test_validation_result_persistence(self):
        """Test ValidationResult serialization and deserialization"""
        validator = ConcreteValidator("TestValidator")

        result = await validator.execute({}, {})

        # Serialize
        data = result.to_dict()

        # Deserialize
        restored = ValidationResult.from_dict(data)

        assert restored.passed == result.passed
        assert restored.score == result.score
        assert restored.message == result.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
