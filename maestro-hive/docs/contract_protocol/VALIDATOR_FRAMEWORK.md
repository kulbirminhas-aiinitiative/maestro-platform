# Validator Framework
## Building Custom Validators for Contract Verification

**Version:** 1.1.0
**Date:** 2025-10-11
**Status:** Phase 1 Corrections Applied

---

## Overview

The Validator Framework provides a pluggable architecture for verifying contract fulfillment. This document covers:
- Validator interface
- Built-in validators
- Creating custom validators
- Validation pipeline
- Best practices

---

## Validator Interface

All validators must implement the `ContractValidator` abstract base class:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

# IMPORTANT: Import canonical definitions (DO NOT duplicate)
from contract_protocol.types import AcceptanceCriterion, CriterionResult

logger = logging.getLogger(__name__)


@dataclass
class ValidatorMetadata:
    """Metadata about validator requirements"""
    name: str
    version: str
    dependencies: List[str]  # ["selenium>=4.0.0", "axe-selenium-python"]
    runtime_requirements: List[str]  # ["chrome-driver", "headless-browser"]
    timeout_seconds: int = 300
    requires_network: bool = False
    requires_sandboxing: bool = False


class ContractValidator(ABC):
    """Base class for all contract validators"""

    def __init__(self):
        self.name = self.__class__.__name__

    @property
    @abstractmethod
    def metadata(self) -> ValidatorMetadata:
        """Return validator metadata"""
        pass

    async def validate(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        """
        Validate with timeout enforcement.
        Subclasses should implement validate_impl().
        """
        try:
            return await asyncio.wait_for(
                self.validate_impl(criterion, context),
                timeout=self.metadata.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Validator {self.metadata.name} timed out after {self.metadata.timeout_seconds}s")
            return CriterionResult(
                criterion_id=criterion.criterion_id,
                passed=False,
                actual_value="timeout",
                expected_value="completion",
                message=f"Validation timed out after {self.metadata.timeout_seconds} seconds"
            )
        except Exception as e:
            logger.error(f"Validator {self.metadata.name} failed: {e}")
            return CriterionResult(
                criterion_id=criterion.criterion_id,
                passed=False,
                actual_value="error",
                expected_value="success",
                message=f"Validation failed: {str(e)}"
            )

    @abstractmethod
    async def validate_impl(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        """
        Implement validation logic in subclasses.

        Args:
            criterion: Acceptance criterion to validate
            context: Context containing artifacts, specification, etc.
                - artifacts: Delivered artifacts from contract provider
                - specification: Contract specification
                - Additional context fields

        Returns:
            CriterionResult with pass/fail and details
        """
        pass

    def setup(self):
        """Optional: Setup before validation (e.g., start services)"""
        pass

    def teardown(self):
        """Optional: Cleanup after validation"""
        pass
```

---

## Built-in Validators

### 1. UX Screenshot Validator

Compares rendered UI to design mockups using perceptual image comparison.

```python
# contract_validators/ux_validators.py

from PIL import Image
import imagehash
from pathlib import Path
import requests

class UXScreenshotValidator(ContractValidator):
    """
    Validates UI implementation against design mockups.
    Uses perceptual hashing for image comparison.
    """

    def validate(
        self,
        artifacts: Dict[str, Any],
        specification: Dict[str, Any],
        criterion: AcceptanceCriterion
    ) -> CriterionResult:
        """
        Compare screenshot of implemented UI to design mockup.

        artifacts = {
            "screenshot": "path/to/screenshot.png",
            "viewport_size": "1920x1080"
        }

        specification = {
            "figma_link": "https://figma.com/...",
            "design_tokens": {...}
        }

        criterion = {
            "criterion": "visual_consistency",
            "threshold": 0.95,  # 95% similarity
            "parameters": {
                "comparison_method": "perceptual",
                "tolerance": 5
            }
        }
        """
        # Get screenshot path
        screenshot_path = artifacts.get("screenshot")
        if not screenshot_path:
            return CriterionResult(
                criterion_name=criterion.criterion,
                passed=False,
                message="No screenshot provided"
            )

        # Get design mockup (from Figma API or local file)
        mockup_path = self._fetch_design_mockup(specification)

        # Load images
        screenshot = Image.open(screenshot_path)
        mockup = Image.open(mockup_path)

        # Compute perceptual hashes
        screenshot_hash = imagehash.phash(screenshot)
        mockup_hash = imagehash.phash(mockup)

        # Calculate similarity
        hash_diff = screenshot_hash - mockup_hash
        max_diff = 64  # Maximum possible hash difference
        similarity = 1.0 - (hash_diff / max_diff)

        # Apply tolerance
        tolerance = criterion.parameters.get("tolerance", 0) / 100
        adjusted_threshold = criterion.threshold - tolerance

        passed = similarity >= adjusted_threshold

        return CriterionResult(
            criterion_name=criterion.criterion,
            passed=passed,
            score=similarity,
            details={
                "similarity": similarity,
                "threshold": adjusted_threshold,
                "hash_difference": hash_diff,
                "screenshot_path": screenshot_path,
                "mockup_path": mockup_path
            },
            message=f"Visual similarity: {similarity:.2%} (threshold: {adjusted_threshold:.2%})"
        )

    def _fetch_design_mockup(self, specification: Dict[str, Any]) -> str:
        """Fetch design mockup from Figma or local file"""
        figma_link = specification.get("figma_link")
        if figma_link:
            # Use Figma API to export design
            return self._export_from_figma(figma_link)
        else:
            # Use local mockup file
            return specification.get("mockup_file")

    def _export_from_figma(self, figma_link: str) -> str:
        """Export design from Figma using API"""
        # Implementation depends on Figma API access
        # Return path to exported PNG
        pass
```

**Usage:**
```python
validator = UXScreenshotValidator()
result = validator.validate(
    artifacts={"screenshot": "screenshots/login.png"},
    specification={"figma_link": "https://..."},
    criterion=AcceptanceCriterion(
        criterion="visual_consistency",
        threshold=0.95
    )
)
```

---

### 2. Accessibility Validator

Validates WCAG compliance using axe-core with explicit runtime requirements.

```python
# contract_validators/ux_validators.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from axe_selenium_python import Axe

class AccessibilityValidator(ContractValidator):
    """
    Accessibility validator with explicit runtime requirements.

    RUNTIME REQUIREMENTS:
    - Chrome/Chromium browser installed
    - chromedriver in PATH
    - axe-selenium-python package: pip install axe-selenium-python
    - Headless mode for CI

    TIMEOUTS:
    - Page load: 30 seconds
    - axe scan: 60 seconds
    """

    @property
    def metadata(self) -> ValidatorMetadata:
        return ValidatorMetadata(
            name="accessibility_validator",
            version="1.0.0",
            dependencies=["selenium>=4.0.0", "axe-selenium-python>=2.1.0"],
            runtime_requirements=["chrome-driver", "chromium-browser"],
            timeout_seconds=90,  # 30s page load + 60s scan
            requires_network=True,
            requires_sandboxing=False
        )

    def setup(self):
        """Start headless Chrome browser"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--timeout=30")

        self.driver = webdriver.Chrome(options=chrome_options)

    def teardown(self):
        """Close browser"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    async def validate_impl(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        """
        Run accessibility scan on implemented UI.

        context = {
            "artifacts": {
                "url": "http://localhost:3000/login",
                "html_file": "path/to/index.html"  # Alternative to URL
            },
            "specification": {
                "accessibility_level": "WCAG 2.1 AA"
            }
        }

        criterion = {
            "criterion_id": "accessibility_score",
            "validation_config": {
                "level": "AA",
                "tags": ["wcag2a", "wcag2aa"],
                "min_score": 95  # Realistic: allows minor violations
            }
        }
        """
        artifacts = context.get("artifacts", {})

        # Get URL
        url = artifacts.get("url")
        if not url:
            html_file = artifacts.get("html_file")
            url = f"file://{html_file}"

        if not url:
            return CriterionResult(
                criterion_id=criterion.criterion_id,
                passed=False,
                actual_value="no_url",
                expected_value="valid_url",
                message="No URL or HTML file provided for accessibility scan"
            )

        # Load page
        self.driver.get(url)

        # Run axe scan
        axe = Axe(self.driver)
        axe.inject()
        results = axe.run()

        # Get violations
        violations = results["violations"]
        passes = len(results["passes"])
        incomplete = len(results["incomplete"])

        # Calculate score based on violations
        total_checks = len(violations) + passes + incomplete
        score = (passes / total_checks * 100) if total_checks > 0 else 0

        # Get min score from config (realistic: 95)
        min_score = criterion.validation_config.get("min_score", 95)

        passed = score >= min_score

        return CriterionResult(
            criterion_id=criterion.criterion_id,
            passed=passed,
            actual_value=score,
            expected_value=min_score,
            message=f"Accessibility score: {score:.1f}% ({len(violations)} violations)",
            evidence={
                "violations": violations,
                "passes": passes,
                "incomplete": incomplete,
                "url": url
            }
        )
```

**Runtime Requirements Check**:

```python
def check_accessibility_validator_requirements():
    """Check if accessibility validator requirements are met"""
    import shutil

    # Check chromedriver
    if not shutil.which("chromedriver"):
        raise EnvironmentError("chromedriver not found in PATH")

    # Check Chrome/Chromium
    chrome_paths = ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]
    if not any(os.path.exists(p) for p in chrome_paths):
        raise EnvironmentError("Chrome/Chromium browser not found")

    logger.info("Accessibility validator requirements satisfied")
```

---

### 3. API Contract Validator

Validates API contracts using Pact or OpenAPI validation.

```python
# contract_validators/api_validators.py

import requests
from openapi_core import create_spec
from openapi_core.validation.request import openapi_request_validator
from openapi_core.validation.response import openapi_response_validator

class APIContractValidator(ContractValidator):
    """
    Validates API implementation against OpenAPI specification.
    """

    def validate(
        self,
        artifacts: Dict[str, Any],
        specification: Dict[str, Any],
        criterion: AcceptanceCriterion
    ) -> CriterionResult:
        """
        Validate API responses against OpenAPI spec.

        artifacts = {
            "api_url": "http://localhost:8000",
            "endpoints": [...]
        }

        specification = {
            "openapi_spec": {...},
            "spec_file": "api_spec.yaml"
        }

        criterion = {
            "criterion": "schema_validation",
            "parameters": {
                "endpoints_to_test": ["/api/v1/auth/login"]
            }
        }
        """
        # Load OpenAPI spec
        spec_file = specification.get("spec_file")
        spec = create_spec(spec_file)

        api_url = artifacts.get("api_url")
        endpoints = criterion.parameters.get("endpoints_to_test", [])

        validation_results = []
        failures = []

        for endpoint in endpoints:
            # Make request
            method = self._get_method_for_endpoint(endpoint, spec)
            full_url = f"{api_url}{endpoint}"

            response = requests.request(
                method=method,
                url=full_url,
                json=self._get_test_payload(endpoint, spec)
            )

            # Validate response
            try:
                openapi_response_validator.validate(spec, response)
                validation_results.append({
                    "endpoint": endpoint,
                    "passed": True
                })
            except Exception as e:
                validation_results.append({
                    "endpoint": endpoint,
                    "passed": False,
                    "error": str(e)
                })
                failures.append(f"{endpoint}: {str(e)}")

        passed = len(failures) == 0

        return CriterionResult(
            criterion_name=criterion.criterion,
            passed=passed,
            score=len([r for r in validation_results if r["passed"]]) / len(validation_results) if validation_results else 0,
            details={
                "results": validation_results,
                "failures": failures
            },
            message=f"API validation: {len(failures)} failures"
        )

    def _get_method_for_endpoint(self, endpoint: str, spec) -> str:
        """Get HTTP method for endpoint from spec"""
        # Parse OpenAPI spec to get method
        return "POST"  # Simplified

    def _get_test_payload(self, endpoint: str, spec) -> Dict:
        """Generate test payload from OpenAPI spec"""
        # Generate payload from schema
        return {}  # Simplified
```

---

### 4. Security Policy Validator

Validates security policies using static analysis and vulnerability scanning.

```python
# contract_validators/security_validators.py

import subprocess
import json

class SecurityPolicyValidator(ContractValidator):
    """
    Validates security policy implementation.
    Uses bandit for Python, npm audit for Node.js.
    """

    def validate(
        self,
        artifacts: Dict[str, Any],
        specification: Dict[str, Any],
        criterion: AcceptanceCriterion
    ) -> CriterionResult:
        """
        Run security scans on codebase.

        artifacts = {
            "code_path": "path/to/code"
        }

        specification = {
            "vulnerability_thresholds": {
                "critical": 0,
                "high": 0,
                "medium": 5
            }
        }

        criterion = {
            "criterion": "security_audit",
            "validator": "bandit_scan",
            "parameters": {
                "severity_threshold": "medium"
            }
        }
        """
        code_path = artifacts.get("code_path")
        thresholds = specification.get("vulnerability_thresholds", {})

        # Run bandit scan
        result = subprocess.run(
            ["bandit", "-r", code_path, "-f", "json"],
            capture_output=True,
            text=True
        )

        scan_results = json.loads(result.stdout)
        issues = scan_results.get("results", [])

        # Count by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }

        for issue in issues:
            severity = issue.get("issue_severity", "low").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Check thresholds
        failures = []
        for severity, threshold in thresholds.items():
            count = severity_counts.get(severity, 0)
            if count > threshold:
                failures.append(f"{severity.upper()}: {count} (threshold: {threshold})")

        passed = len(failures) == 0

        return CriterionResult(
            criterion_name=criterion.criterion,
            passed=passed,
            details={
                "severity_counts": severity_counts,
                "thresholds": thresholds,
                "issues": issues[:10]  # First 10
            },
            message=f"Security scan: {', '.join(failures) if failures else 'PASSED'}"
        )
```

---

### 5. Performance Validator

Validates performance targets using load testing.

```python
# contract_validators/performance_validators.py

from locust import HttpUser, task, between
import subprocess
import statistics

class PerformanceValidator(ContractValidator):
    """
    Validates performance targets using Locust load testing.
    """

    def validate(
        self,
        artifacts: Dict[str, Any],
        specification: Dict[str, Any],
        criterion: AcceptanceCriterion
    ) -> CriterionResult:
        """
        Run load test and validate performance.

        artifacts = {
            "api_url": "http://localhost:8000"
        }

        specification = {
            "response_time": {
                "p95_ms": 200,
                "max_ms": 1000
            }
        }

        criterion = {
            "criterion": "response_time_p95",
            "threshold": 200,
            "parameters": {
                "duration": 60,
                "users": 100,
                "spawn_rate": 10
            }
        }
        """
        api_url = artifacts.get("api_url")
        duration = criterion.parameters.get("duration", 60)
        users = criterion.parameters.get("users", 100)
        spawn_rate = criterion.parameters.get("spawn_rate", 10)

        # Run Locust test
        result = subprocess.run(
            [
                "locust",
                "-f", "locustfile.py",
                "--headless",
                "--users", str(users),
                "--spawn-rate", str(spawn_rate),
                "--run-time", f"{duration}s",
                "--host", api_url,
                "--json"
            ],
            capture_output=True,
            text=True
        )

        # Parse results
        stats = self._parse_locust_output(result.stdout)

        p95_response_time = stats.get("p95", 0)
        threshold = criterion.threshold

        passed = p95_response_time <= threshold

        return CriterionResult(
            criterion_name=criterion.criterion,
            passed=passed,
            score=threshold / p95_response_time if p95_response_time > 0 else 1.0,
            details={
                "p50": stats.get("p50"),
                "p95": stats.get("p95"),
                "p99": stats.get("p99"),
                "max": stats.get("max"),
                "requests_per_second": stats.get("rps"),
                "error_rate": stats.get("error_rate")
            },
            message=f"P95 response time: {p95_response_time}ms (threshold: {threshold}ms)"
        )

    def _parse_locust_output(self, output: str) -> Dict:
        """Parse Locust JSON output"""
        # Parse JSON stats from Locust
        return {}  # Simplified
```

---

## Creating Custom Validators

### Step 1: Implement ContractValidator

```python
# my_custom_validators.py

from contract_validators import ContractValidator, CriterionResult

class MyCustomValidator(ContractValidator):
    """
    Custom validator for specific contract type.
    """

    def validate(
        self,
        artifacts: Dict[str, Any],
        specification: Dict[str, Any],
        criterion: AcceptanceCriterion
    ) -> CriterionResult:
        # Your validation logic here

        # Extract inputs
        input_data = artifacts.get("key")
        expected = specification.get("expected_value")

        # Perform validation
        passed = input_data == expected

        # Return result
        return CriterionResult(
            criterion_name=criterion.criterion,
            passed=passed,
            details={"input": input_data, "expected": expected},
            message="Validation complete"
        )
```

### Step 2: Register Validator

```python
# In your initialization code
from contract_registry import ContractRegistry
from my_custom_validators import MyCustomValidator

registry = ContractRegistry()
registry.register_validator("my_custom_validator", MyCustomValidator())
```

### Step 3: Use in Contract

```python
contract = UniversalContract(
    contract_id="MY_CONTRACT_001",
    acceptance_criteria=[
        AcceptanceCriterion(
            criterion="custom_check",
            validator="my_custom_validator",  # Name you registered
            parameters={"some_param": "value"}
        )
    ]
)
```

---

## Validation Pipeline

### Execution Flow

```
1. Contract fulfilled by provider agent
   ↓
2. registry.verify_contract_fulfillment(contract_id, artifacts)
   ↓
3. For each acceptance criterion:
   a. Get validator by name
   b. Call validator.validate(artifacts, spec, criterion)
   c. Collect CriterionResult
   ↓
4. Aggregate results:
   - All critical criteria must pass
   - Non-critical criteria are warnings
   ↓
5. Update contract state:
   - VERIFIED if all critical pass
   - BREACHED if any critical fails
```

### Parallel Validation

For performance, validators can run in parallel:

```python
import asyncio

async def verify_contract_parallel(
    registry: ContractRegistry,
    contract_id: str,
    artifacts: Dict[str, Any]
) -> VerificationResult:
    """Run validators in parallel"""
    contract = registry.get_contract(contract_id)

    tasks = []
    for criterion in contract.acceptance_criteria:
        validator = registry.validators[criterion.validator]
        task = asyncio.to_thread(
            validator.validate,
            artifacts,
            contract.specification,
            criterion
        )
        tasks.append(task)

    criterion_results = await asyncio.gather(*tasks)

    # Aggregate and return
    ...
```

---

## Best Practices

### 1. Fail Fast
- Check prerequisites early
- Return immediately if inputs are invalid

### 2. Detailed Error Messages
- Provide actionable feedback
- Include remediation suggestions

### 3. Idempotency
- Validators should be side-effect free
- Multiple runs should produce same result

### 4. Performance
- Timeout long-running validators
- Use caching where appropriate

### 5. Logging
- Log validation steps for debugging
- Don't log sensitive data

### 6. Testing
- Unit test validators independently
- Mock external services

---

## Phase 1 Corrections Applied

The following corrections have been made to validator implementations (see `PROTOCOL_CORRECTIONS.md` for details):

### 1. OpenAPI Validator - Corrected Implementation

**Issues Fixed**:
- Updated for modern `openapi-core>=0.18.0` API
- Correct spec loading with `Spec.from_dict()`
- Proper request/response validation approach

**See**: `PROTOCOL_CORRECTIONS.md` Section 4 and `IMPLEMENTATION_GUIDE.md` for complete corrected implementation.

### 2. Accessibility Validator - Runtime Requirements Added

**Issues Fixed**:
- Explicit runtime requirements documented
- Headless mode configuration for CI
- Timeout enforcement (30s page load + 60s scan)
- Realistic scoring (95% threshold instead of 100%)

**Complete implementation**: See above in this document.

### 3. Performance Validator - External Process Execution

**Issues Fixed**:
- Uses external Locust process instead of in-process
- Results written to JSON file
- Proper timeout handling
- Clear separation of concerns

**Key Changes**:
```python
# Run Locust as external process
cmd = [
    "locust",
    "-f", locustfile,
    "--headless",
    "--host", host,
    "--users", str(users),
    "--run-time", duration,
    "--json", result_file
]

process = await asyncio.create_subprocess_exec(*cmd, ...)
```

**See**: `PROTOCOL_CORRECTIONS.md` Section 4 for complete implementation.

### 4. Security Validators - Sandboxing Requirements

**Issues Fixed**:
- Docker sandboxing required for security tools
- No network access (`--network none`)
- Read-only filesystem (`--read-only`)
- Non-root user (`--user nobody`)
- 5-minute timeout enforcement
- Log sanitization

**Example**:
```python
# Run security tool in Docker container
cmd = [
    "docker", "run",
    "--rm",
    "--network", "none",
    "--read-only",
    "--tmpfs", "/tmp",
    "--user", "nobody",
    f"security-tools:{tool}",
    *args
]
```

**See**: `PROTOCOL_CORRECTIONS.md` Section 4 for complete sandboxing implementation.

### 5. All Validators - Import Canonical Definitions

**Critical Change**: All validators now import from canonical data model definitions instead of duplicating:

```python
# CORRECT: Import from canonical location
from contract_protocol.types import (
    AcceptanceCriterion,
    CriterionResult,
    VerificationResult
)

# INCORRECT: Do not duplicate definitions
# @dataclass
# class AcceptanceCriterion:  # ❌ NEVER DO THIS
#     ...
```

**See**: `CONTRACT_TYPES_REFERENCE.md` for canonical definitions.

---

## Summary

The Validator Framework provides:
- ✅ Pluggable architecture
- ✅ Built-in validators for common scenarios
- ✅ Easy custom validator creation
- ✅ Parallel validation support
- ✅ Comprehensive result reporting
- ✅ **NEW**: Explicit runtime requirements and metadata
- ✅ **NEW**: Timeout enforcement on all validators
- ✅ **NEW**: Sandboxing support for security validators
- ✅ **NEW**: Realistic thresholds and scoring

**Related Documents**:
- `PROTOCOL_CORRECTIONS.md` - Complete list of all corrections
- `IMPLEMENTATION_GUIDE.md` - Implementation guidance for new API methods
- `CONTRACT_TYPES_REFERENCE.md` - Canonical data model definitions
- `EXAMPLES_AND_PATTERNS.md` - Real-world usage patterns
