# Universal Contract Protocol - Runtime Modes and Environment Configuration

**Document Type:** Strategic Enhancement (Phase 2)
**Version:** 1.0.0
**Last Updated:** 2025-10-11
**Status:** Phase 2 - Production Feature
**Priority:** HIGH (needed for production deployments)
**Author:** Claude (Sonnet 4.5)

---

## Executive Summary

This guide provides comprehensive guidance on configuring the Universal Contract Protocol for different runtime environments (development, staging, production).

**Key Topics:**
- Runtime mode definitions and purposes
- Environment-specific thresholds and policies
- Validator selection per environment
- Performance optimization strategies
- Debug logging and monitoring
- Configuration management (YAML/JSON)

**Why This Matters:**
- Enables fast feedback loops in development without compromising production quality
- Optimizes validator execution for each environment
- Reduces costs by running expensive validators only where needed
- Provides appropriate logging verbosity per environment
- Supports compliance and audit requirements

---

## Table of Contents

1. [Runtime Mode Overview](#runtime-mode-overview)
2. [Development Mode](#development-mode)
3. [Staging Mode](#staging-mode)
4. [Production Mode](#production-mode)
5. [Custom Modes](#custom-modes)
6. [Validator Selection Strategy](#validator-selection-strategy)
7. [Performance Tuning](#performance-tuning)
8. [Debug Logging and Tracing](#debug-logging-and-tracing)
9. [Configuration Files](#configuration-files)
10. [Environment Detection](#environment-detection)
11. [Examples and Patterns](#examples-and-patterns)
12. [Best Practices](#best-practices)

---

## Runtime Mode Overview

### Three Core Modes

| Mode | Purpose | Speed | Strictness | Cost |
|------|---------|-------|------------|------|
| **Development** | Fast feedback, iteration | 🚀 Fastest | 🔓 Lenient | 💵 Lowest |
| **Staging** | Pre-production validation | 🏃 Moderate | 🔒 Realistic | 💵💵 Moderate |
| **Production** | Live system quality assurance | 🐢 Thorough | 🔐 Strict | 💵💵💵 Highest |

### Mode Selection Criteria

```python
from enum import Enum

class RuntimeMode(Enum):
    """Runtime environment modes"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"

# Detect runtime mode from environment
def detect_runtime_mode() -> RuntimeMode:
    """Detect current runtime mode from environment variables"""
    mode_str = os.getenv("MAESTRO_RUNTIME_MODE", "development").lower()

    try:
        return RuntimeMode(mode_str)
    except ValueError:
        print(f"Warning: Unknown runtime mode '{mode_str}', defaulting to DEVELOPMENT")
        return RuntimeMode.DEVELOPMENT

# Usage
current_mode = detect_runtime_mode()
print(f"Running in {current_mode.value} mode")
```

### Configuration Hierarchy

```
Environment Variable > Config File > Hardcoded Defaults
```

**Example:**
```python
# 1. Hardcoded default
default_threshold = 80

# 2. Config file override
config_threshold = config.get("accessibility_threshold", default_threshold)

# 3. Environment variable override (highest priority)
final_threshold = int(os.getenv("ACCESSIBILITY_THRESHOLD", config_threshold))
```

---

## Development Mode

### Purpose

**Goal:** Maximum developer productivity with fast feedback loops.

**Characteristics:**
- ✅ Fast validator execution (subset of validators)
- ✅ Lenient thresholds
- ✅ Verbose logging for debugging
- ✅ Auto-reload on code changes
- ✅ Minimal external dependencies
- ❌ Not suitable for quality gates

### Validation Policy

```python
from dataclasses import dataclass

@dataclass
class DevelopmentValidationPolicy:
    """Validation policy for development mode"""

    # Lenient thresholds
    accessibility_min_score: float = 80.0  # vs. 95 in production
    response_time_p95_ms: int = 1000  # vs. 500 in production
    test_coverage_min: float = 0.60  # vs. 0.80 in production
    security_vulnerability_max: int = 5  # Allow some low-severity issues

    # Reduced timeout (fail fast)
    validator_timeout_seconds: int = 30  # vs. 120 in production

    # Fail fast on critical issues only
    fail_on_warnings: bool = False
    fail_on_critical_only: bool = True

    # Enable debug features
    debug_mode: bool = True
    verbose_logging: bool = True
    save_debug_artifacts: bool = True

# Create policy
dev_policy = DevelopmentValidationPolicy()
```

### Validator Selection

**Run Only:**
- ✅ Fast unit-test-like validators (< 5 seconds)
- ✅ Syntax validators (linters, formatters)
- ✅ Static analysis (no network calls)
- ❌ Skip expensive validators (Lighthouse, load testing)
- ❌ Skip external service calls

**Example:**
```python
DEVELOPMENT_VALIDATORS = [
    "syntax_validator",      # Fast: < 1s
    "type_checker",          # Fast: < 2s
    "unit_test_runner",      # Fast: < 5s
    "accessibility_basic",   # Fast: < 3s (axe-core headless)
]

DEVELOPMENT_SKIP_VALIDATORS = [
    "lighthouse_validator",  # Slow: ~30s
    "load_test_validator",   # Slow: ~60s
    "security_scan_full",    # Slow: ~45s (runs in staging/prod)
    "visual_regression",     # Slow: ~20s (needs baseline screenshots)
]

def should_run_validator(validator_name: str, mode: RuntimeMode) -> bool:
    """Determine if validator should run in current mode"""
    if mode == RuntimeMode.DEVELOPMENT:
        return validator_name in DEVELOPMENT_VALIDATORS
    elif mode == RuntimeMode.STAGING:
        return validator_name not in ["load_test_validator"]  # Run most validators
    else:  # PRODUCTION
        return True  # Run all validators
```

### Configuration Example

```yaml
# config/development.yaml
runtime_mode: development

validation_policy:
  accessibility_min_score: 80
  response_time_p95_ms: 1000
  test_coverage_min: 0.60
  security_vulnerability_max: 5
  fail_on_warnings: false

validators:
  enabled:
    - syntax_validator
    - type_checker
    - unit_test_runner
    - accessibility_basic
  disabled:
    - lighthouse_validator
    - load_test_validator
    - security_scan_full

logging:
  level: DEBUG
  format: "detailed"
  output: "console"

performance:
  parallel_validators: true
  max_parallel: 4
  cache_enabled: true
  cache_ttl_seconds: 3600

debug:
  save_artifacts: true
  save_intermediate_results: true
  profiling_enabled: false
```

### Development Workflow

```python
# Development workflow example
def development_contract_validation(contract: UniversalContract) -> VerificationResult:
    """Fast validation for development"""

    mode = RuntimeMode.DEVELOPMENT
    policy = DevelopmentValidationPolicy()

    # Select fast validators only
    validators = [
        SyntaxValidator(),
        TypeChecker(),
        UnitTestRunner()
    ]

    # Run validators in parallel (fast feedback)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(validator.validate, contract, policy)
            for validator in validators
        ]

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result(timeout=30)  # Fail fast
                results.append(result)
            except TimeoutError:
                print(f"⏱️  Validator timed out (skipping in dev mode)")

    # Aggregate results (lenient - only fail on critical issues)
    passed = all(r.passed or not r.is_critical for r in results)

    return VerificationResult(
        passed=passed,
        criterion_results=results,
        mode=mode,
        execution_time_seconds=sum(r.execution_time for r in results)
    )
```

---

## Staging Mode

### Purpose

**Goal:** Realistic pre-production validation with production-like conditions.

**Characteristics:**
- ✅ Full validator suite (except load testing)
- ✅ Realistic thresholds (same as production)
- ✅ Moderate logging (errors + warnings)
- ✅ Integration with staging services
- ✅ Cost-optimized (fewer replicas than production)
- ✅ Suitable for quality gates

### Validation Policy

```python
@dataclass
class StagingValidationPolicy:
    """Validation policy for staging mode"""

    # Realistic thresholds (match production)
    accessibility_min_score: float = 95.0
    response_time_p95_ms: int = 500
    test_coverage_min: float = 0.80
    security_vulnerability_max: int = 0  # No critical/high vulnerabilities

    # Production-like timeout
    validator_timeout_seconds: int = 120

    # Fail on warnings (strict quality gate)
    fail_on_warnings: bool = True
    fail_on_critical_only: bool = False

    # Moderate debug features
    debug_mode: bool = False
    verbose_logging: bool = False
    save_debug_artifacts: bool = True  # Save for debugging

# Create policy
staging_policy = StagingValidationPolicy()
```

### Validator Selection

**Run:**
- ✅ All validators except full load testing
- ✅ Integration tests (staging APIs)
- ✅ Visual regression tests
- ✅ Accessibility audits
- ✅ Security scans
- ⚠️  Partial load testing (reduced scale)

**Example:**
```python
STAGING_VALIDATORS = [
    "syntax_validator",
    "type_checker",
    "unit_test_runner",
    "integration_test_runner",
    "accessibility_full",     # Full axe-core + manual checks
    "api_contract_validator",
    "security_scan_full",
    "performance_baseline",   # Baseline perf test
    "visual_regression",
]

STAGING_SKIP_VALIDATORS = [
    "load_test_full",  # Skip full load test (expensive)
]

STAGING_PARTIAL_VALIDATORS = {
    "load_test_partial": {
        "max_users": 100,      # vs. 10,000 in production
        "duration_minutes": 5   # vs. 30 in production
    }
}
```

### Configuration Example

```yaml
# config/staging.yaml
runtime_mode: staging

validation_policy:
  accessibility_min_score: 95
  response_time_p95_ms: 500
  test_coverage_min: 0.80
  security_vulnerability_max: 0
  fail_on_warnings: true

validators:
  enabled:
    - syntax_validator
    - type_checker
    - unit_test_runner
    - integration_test_runner
    - accessibility_full
    - api_contract_validator
    - security_scan_full
    - performance_baseline
    - visual_regression
  disabled:
    - load_test_full
  partial:
    load_test_partial:
      max_users: 100
      duration_minutes: 5

logging:
  level: INFO
  format: "json"
  output: "file"
  file_path: "/var/log/maestro/staging.log"

performance:
  parallel_validators: true
  max_parallel: 8
  cache_enabled: true
  cache_ttl_seconds: 1800

integrations:
  staging_api_base_url: "https://staging-api.example.com"
  staging_database_url: "postgresql://staging-db.example.com/contracts"
```

### Staging Workflow

```python
def staging_contract_validation(contract: UniversalContract) -> VerificationResult:
    """Full validation for staging (pre-production)"""

    mode = RuntimeMode.STAGING
    policy = StagingValidationPolicy()

    # Load full validator suite (except expensive load tests)
    validators = load_validators_for_mode(mode)

    # Run validators in parallel with production-like timeouts
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(validator.validate, contract, policy): validator
            for validator in validators
        }

        for future in concurrent.futures.as_completed(futures):
            validator = futures[future]
            try:
                result = future.result(timeout=policy.validator_timeout_seconds)
                results.append(result)
            except TimeoutError:
                print(f"❌ {validator.name} timed out (FAIL in staging)")
                results.append(CriterionResult(
                    passed=False,
                    message=f"{validator.name} exceeded timeout"
                ))

    # Strict aggregation (fail on any warnings)
    passed = all(r.passed for r in results)

    if not passed:
        # Log failure details for debugging
        failed_validators = [r.validator_name for r in results if not r.passed]
        print(f"❌ Staging validation failed: {', '.join(failed_validators)}")

    return VerificationResult(
        passed=passed,
        criterion_results=results,
        mode=mode,
        execution_time_seconds=sum(r.execution_time for r in results)
    )
```

---

## Production Mode

### Purpose

**Goal:** Maximum quality assurance and compliance for live system.

**Characteristics:**
- ✅ Full validator suite (all validators)
- ✅ Strictest thresholds
- ✅ Minimal logging (errors only)
- ✅ Integration with production monitoring
- ✅ Audit trail and compliance logging
- ✅ Highest cost (thorough validation)

### Validation Policy

```python
@dataclass
class ProductionValidationPolicy:
    """Validation policy for production mode"""

    # Strict thresholds
    accessibility_min_score: float = 95.0
    response_time_p95_ms: int = 500
    test_coverage_min: float = 0.80
    security_vulnerability_max: int = 0  # Zero tolerance for critical/high

    # Extended timeout for thorough validation
    validator_timeout_seconds: int = 180

    # Strict failure policy
    fail_on_warnings: bool = True
    fail_on_critical_only: bool = False

    # Minimal debug (production security)
    debug_mode: bool = False
    verbose_logging: bool = False
    save_debug_artifacts: bool = False

    # Compliance
    audit_logging: bool = True
    compliance_mode: bool = True

# Create policy
production_policy = ProductionValidationPolicy()
```

### Validator Selection

**Run:**
- ✅ All validators (complete suite)
- ✅ Full integration tests
- ✅ Full load tests (production scale)
- ✅ Security audits
- ✅ Compliance checks
- ✅ Performance profiling

**Example:**
```python
PRODUCTION_VALIDATORS = [
    # Syntax and type checking
    "syntax_validator",
    "type_checker",

    # Testing
    "unit_test_runner",
    "integration_test_runner",
    "end_to_end_test_runner",

    # Quality
    "accessibility_full",
    "api_contract_validator",
    "visual_regression",

    # Security
    "security_scan_full",
    "vulnerability_scan",
    "penetration_test",

    # Performance
    "performance_baseline",
    "load_test_full",
    "stress_test",

    # Compliance
    "compliance_checker",
    "audit_logger",
]

# No validators skipped in production
PRODUCTION_SKIP_VALIDATORS = []
```

### Configuration Example

```yaml
# config/production.yaml
runtime_mode: production

validation_policy:
  accessibility_min_score: 95
  response_time_p95_ms: 500
  test_coverage_min: 0.80
  security_vulnerability_max: 0
  fail_on_warnings: true
  fail_on_critical_only: false

validators:
  enabled:
    - syntax_validator
    - type_checker
    - unit_test_runner
    - integration_test_runner
    - end_to_end_test_runner
    - accessibility_full
    - api_contract_validator
    - visual_regression
    - security_scan_full
    - vulnerability_scan
    - performance_baseline
    - load_test_full
  disabled: []  # Run all validators

logging:
  level: ERROR
  format: "json"
  output: "both"  # Console + file
  file_path: "/var/log/maestro/production.log"
  syslog_enabled: true
  audit_logging: true

performance:
  parallel_validators: true
  max_parallel: 16  # More resources in production
  cache_enabled: true
  cache_ttl_seconds: 900  # Shorter TTL for freshness

monitoring:
  enabled: true
  metrics_endpoint: "https://metrics.example.com/api/v1/metrics"
  alert_on_failure: true
  alert_channels: ["pagerduty", "slack"]

compliance:
  enabled: true
  regulations: ["SOC2", "GDPR", "HIPAA"]
  audit_retention_days: 2555  # 7 years

integrations:
  production_api_base_url: "https://api.example.com"
  production_database_url: "postgresql://prod-db.example.com/contracts"
```

### Production Workflow

```python
def production_contract_validation(contract: UniversalContract) -> VerificationResult:
    """Maximum quality validation for production"""

    mode = RuntimeMode.PRODUCTION
    policy = ProductionValidationPolicy()

    # Load complete validator suite
    validators = load_all_validators()

    # Audit log start
    audit_log(f"Starting production validation for contract {contract.contract_id}")

    # Run validators with maximum parallelism
    results = []
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = {
            executor.submit(validator.validate, contract, policy): validator
            for validator in validators
        }

        for future in concurrent.futures.as_completed(futures):
            validator = futures[future]
            try:
                result = future.result(timeout=policy.validator_timeout_seconds)
                results.append(result)

                # Log validator completion
                audit_log(f"Validator {validator.name}: {'PASS' if result.passed else 'FAIL'}")

            except Exception as e:
                # Critical failure in production
                error_msg = f"CRITICAL: {validator.name} failed with exception: {e}"
                audit_log(error_msg)
                alert_monitoring_system(error_msg, severity="CRITICAL")

                results.append(CriterionResult(
                    passed=False,
                    message=error_msg,
                    is_critical=True
                ))

    # Strict aggregation
    passed = all(r.passed for r in results)
    execution_time = time.time() - start_time

    # Audit log completion
    audit_log(
        f"Production validation for {contract.contract_id}: "
        f"{'PASS' if passed else 'FAIL'} ({execution_time:.2f}s)"
    )

    # Alert on failure
    if not passed:
        alert_monitoring_system(
            f"Contract {contract.contract_id} FAILED production validation",
            severity="HIGH"
        )

    return VerificationResult(
        passed=passed,
        criterion_results=results,
        mode=mode,
        execution_time_seconds=execution_time,
        audit_trail_id=get_audit_trail_id()
    )

def audit_log(message: str):
    """Log to audit trail (compliance requirement)"""
    logger.info(f"[AUDIT] {message}", extra={
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "production",
        "compliance": True
    })

def alert_monitoring_system(message: str, severity: str):
    """Send alert to monitoring system (PagerDuty, Slack, etc.)"""
    # Send to monitoring system
    monitoring_client.send_alert({
        "message": message,
        "severity": severity,
        "source": "maestro-contract-protocol",
        "timestamp": datetime.utcnow().isoformat()
    })
```

---

## Custom Modes

### Defining Custom Modes

For specialized use cases (e.g., demo, training, compliance-audit):

```python
@dataclass
class CustomValidationPolicy:
    """Custom validation policy"""
    mode_name: str
    accessibility_min_score: float
    response_time_p95_ms: int
    test_coverage_min: float
    security_vulnerability_max: int
    validator_timeout_seconds: int
    fail_on_warnings: bool
    enabled_validators: List[str]
    disabled_validators: List[str]

# Example: Demo mode (fast, impressive, lenient)
demo_policy = CustomValidationPolicy(
    mode_name="demo",
    accessibility_min_score=85,
    response_time_p95_ms=1000,
    test_coverage_min=0.70,
    security_vulnerability_max=10,
    validator_timeout_seconds=30,
    fail_on_warnings=False,
    enabled_validators=["syntax_validator", "type_checker", "accessibility_basic"],
    disabled_validators=["load_test_full", "security_scan_full"]
)

# Example: Compliance audit mode (maximum strictness)
compliance_audit_policy = CustomValidationPolicy(
    mode_name="compliance_audit",
    accessibility_min_score=98,  # Stricter than production
    response_time_p95_ms=300,    # Stricter than production
    test_coverage_min=0.90,      # Stricter than production
    security_vulnerability_max=0,
    validator_timeout_seconds=300,
    fail_on_warnings=True,
    enabled_validators=[],  # Empty = all validators
    disabled_validators=[]
)
```

### Configuration for Custom Modes

```yaml
# config/custom/demo.yaml
runtime_mode: custom
custom_mode_name: demo

validation_policy:
  accessibility_min_score: 85
  response_time_p95_ms: 1000
  test_coverage_min: 0.70
  security_vulnerability_max: 10
  fail_on_warnings: false

validators:
  enabled:
    - syntax_validator
    - type_checker
    - accessibility_basic
  disabled:
    - load_test_full
    - security_scan_full
```

---

## Validator Selection Strategy

### Decision Matrix

| Validator | Development | Staging | Production | Cost | Duration |
|-----------|-------------|---------|------------|------|----------|
| Syntax | ✅ | ✅ | ✅ | 💵 Low | < 1s |
| Type Checker | ✅ | ✅ | ✅ | 💵 Low | < 2s |
| Unit Tests | ✅ | ✅ | ✅ | 💵 Low | < 5s |
| Integration Tests | ❌ | ✅ | ✅ | 💵💵 Med | 10-30s |
| Accessibility Basic | ✅ | ❌ | ❌ | 💵 Low | < 5s |
| Accessibility Full | ❌ | ✅ | ✅ | 💵💵 Med | 15-30s |
| API Contract | ❌ | ✅ | ✅ | 💵 Low | < 5s |
| Visual Regression | ❌ | ✅ | ✅ | 💵💵 Med | 20-40s |
| Security Scan | ❌ | ✅ | ✅ | 💵💵💵 High | 30-60s |
| Performance Baseline | ❌ | ✅ | ✅ | 💵💵 Med | 10-20s |
| Load Test Full | ❌ | ❌ | ✅ | 💵💵💵 High | 5-30min |

### Validator Priority Tiers

```python
class ValidatorPriority(Enum):
    """Priority tiers for validator selection"""
    CRITICAL = 1   # Must run in all modes
    HIGH = 2       # Run in staging + production
    MEDIUM = 3     # Run in production only
    LOW = 4        # Optional / expensive

# Assign priorities
VALIDATOR_PRIORITIES = {
    "syntax_validator": ValidatorPriority.CRITICAL,
    "type_checker": ValidatorPriority.CRITICAL,
    "unit_test_runner": ValidatorPriority.CRITICAL,
    "integration_test_runner": ValidatorPriority.HIGH,
    "accessibility_full": ValidatorPriority.HIGH,
    "api_contract_validator": ValidatorPriority.HIGH,
    "security_scan_full": ValidatorPriority.HIGH,
    "performance_baseline": ValidatorPriority.MEDIUM,
    "load_test_full": ValidatorPriority.MEDIUM,
    "visual_regression": ValidatorPriority.LOW,
}

def get_validators_for_mode(mode: RuntimeMode) -> List[str]:
    """Get validators to run for given mode"""

    if mode == RuntimeMode.DEVELOPMENT:
        # Only CRITICAL validators
        return [v for v, p in VALIDATOR_PRIORITIES.items()
                if p == ValidatorPriority.CRITICAL]

    elif mode == RuntimeMode.STAGING:
        # CRITICAL + HIGH validators
        return [v for v, p in VALIDATOR_PRIORITIES.items()
                if p in [ValidatorPriority.CRITICAL, ValidatorPriority.HIGH]]

    else:  # PRODUCTION
        # All validators
        return list(VALIDATOR_PRIORITIES.keys())
```

---

## Performance Tuning

### Parallel Validator Execution

```python
import concurrent.futures
from typing import List

class ParallelValidatorExecutor:
    """Execute validators in parallel for performance"""

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers

    def execute_validators(
        self,
        validators: List[ContractValidator],
        contract: UniversalContract,
        policy: ValidationPolicy
    ) -> List[CriterionResult]:
        """Execute validators in parallel"""

        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all validators
            future_to_validator = {
                executor.submit(validator.validate, contract, policy): validator
                for validator in validators
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_validator):
                validator = future_to_validator[future]
                try:
                    result = future.result(timeout=policy.validator_timeout_seconds)
                    results.append(result)
                except Exception as e:
                    results.append(CriterionResult(
                        passed=False,
                        validator_name=validator.name,
                        message=f"Exception: {e}"
                    ))

        return results

# Configure parallelism per mode
PARALLEL_WORKERS = {
    RuntimeMode.DEVELOPMENT: 4,   # Limited parallelism
    RuntimeMode.STAGING: 8,       # Moderate parallelism
    RuntimeMode.PRODUCTION: 16,   # Maximum parallelism
}

executor = ParallelValidatorExecutor(
    max_workers=PARALLEL_WORKERS[current_mode]
)
```

### Caching Strategy

```python
import hashlib
import pickle
from datetime import datetime, timedelta

class VerificationCache:
    """Cache verification results to avoid redundant validation"""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, CachedVerification] = {}
        self.ttl_seconds = ttl_seconds

    def get_cache_key(
        self,
        contract: UniversalContract,
        policy: ValidationPolicy
    ) -> str:
        """Generate cache key from contract and policy"""

        # Include contract content and policy settings
        content = f"{contract.contract_id}:{contract.schema_version}:{contract.contract_version}"
        policy_content = f"{policy.accessibility_min_score}:{policy.response_time_p95_ms}"

        return hashlib.sha256(f"{content}:{policy_content}".encode()).hexdigest()

    def get(self, cache_key: str) -> Optional[VerificationResult]:
        """Retrieve cached verification result"""

        cached = self.cache.get(cache_key)
        if not cached:
            return None

        # Check TTL
        if datetime.utcnow() > cached.expires_at:
            del self.cache[cache_key]
            return None

        return cached.result

    def set(
        self,
        cache_key: str,
        result: VerificationResult
    ):
        """Cache verification result"""

        self.cache[cache_key] = CachedVerification(
            result=result,
            cached_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        )

# Configure cache TTL per mode
CACHE_TTL = {
    RuntimeMode.DEVELOPMENT: 3600,   # 1 hour (aggressive caching)
    RuntimeMode.STAGING: 1800,       # 30 minutes
    RuntimeMode.PRODUCTION: 900,     # 15 minutes (fresh validation)
}

cache = VerificationCache(ttl_seconds=CACHE_TTL[current_mode])
```

---

## Debug Logging and Tracing

### Log Levels Per Mode

```python
import logging

# Configure logging per runtime mode
LOG_LEVELS = {
    RuntimeMode.DEVELOPMENT: logging.DEBUG,
    RuntimeMode.STAGING: logging.INFO,
    RuntimeMode.PRODUCTION: logging.ERROR,
}

def configure_logging(mode: RuntimeMode):
    """Configure logging for runtime mode"""

    logging.basicConfig(
        level=LOG_LEVELS[mode],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if mode == RuntimeMode.PRODUCTION:
        # Add syslog handler for production
        from logging.handlers import SysLogHandler
        syslog = SysLogHandler(address='/dev/log')
        logging.getLogger().addHandler(syslog)

# Usage
configure_logging(detect_runtime_mode())
```

### Distributed Tracing

```python
from dataclasses import dataclass
from typing import Optional
import uuid

@dataclass
class TraceContext:
    """Distributed tracing context"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None

def create_trace_context(parent: Optional[TraceContext] = None) -> TraceContext:
    """Create tracing context for validation"""
    return TraceContext(
        trace_id=parent.trace_id if parent else str(uuid.uuid4()),
        span_id=str(uuid.uuid4()),
        parent_span_id=parent.span_id if parent else None
    )

def validate_with_tracing(
    contract: UniversalContract,
    trace_context: TraceContext
) -> VerificationResult:
    """Validate contract with distributed tracing"""

    logger.info(f"[TRACE {trace_context.trace_id}] Starting validation for {contract.contract_id}")

    # Create child span for each validator
    for validator in validators:
        child_context = create_trace_context(parent=trace_context)
        logger.debug(f"[TRACE {child_context.trace_id}:{child_context.span_id}] Running {validator.name}")

        result = validator.validate(contract)

        logger.debug(f"[TRACE {child_context.trace_id}:{child_context.span_id}] "
                    f"{validator.name}: {'PASS' if result.passed else 'FAIL'}")

    logger.info(f"[TRACE {trace_context.trace_id}] Validation complete")
```

---

## Configuration Files

### Configuration File Format

**Recommended:** YAML (human-readable, supports comments)

**Alternative:** JSON (machine-readable, no comments)

### Example: Complete Configuration

```yaml
# config/production.yaml
# Production configuration for Universal Contract Protocol

# Runtime mode
runtime_mode: production

# Validation policy
validation_policy:
  accessibility_min_score: 95.0
  response_time_p95_ms: 500
  test_coverage_min: 0.80
  security_vulnerability_max: 0
  validator_timeout_seconds: 180
  fail_on_warnings: true
  fail_on_critical_only: false

# Validator configuration
validators:
  enabled:
    - syntax_validator
    - type_checker
    - unit_test_runner
    - integration_test_runner
    - accessibility_full
    - api_contract_validator
    - security_scan_full
    - performance_baseline
    - load_test_full
  disabled: []

  # Validator-specific settings
  settings:
    accessibility_full:
      browser: "chromium"
      viewport_width: 1920
      viewport_height: 1080
    load_test_full:
      max_users: 10000
      duration_minutes: 30
      ramp_up_minutes: 5

# Logging configuration
logging:
  level: ERROR
  format: json
  output: both
  file_path: /var/log/maestro/production.log
  max_file_size_mb: 100
  backup_count: 10
  syslog_enabled: true
  audit_logging: true

# Performance tuning
performance:
  parallel_validators: true
  max_parallel: 16
  cache_enabled: true
  cache_ttl_seconds: 900
  timeout_strategy: fail_fast

# Monitoring and alerting
monitoring:
  enabled: true
  metrics_endpoint: https://metrics.example.com/api/v1/metrics
  metrics_interval_seconds: 60
  alert_on_failure: true
  alert_channels:
    - pagerduty
    - slack
    - email

# Compliance
compliance:
  enabled: true
  regulations:
    - SOC2
    - GDPR
    - HIPAA
  audit_retention_days: 2555  # 7 years
  encryption_at_rest: true
  encryption_in_transit: true

# External integrations
integrations:
  api_base_url: https://api.example.com
  database_url: postgresql://prod-db.example.com:5432/contracts
  artifact_store_base_path: /var/maestro/artifacts
  cache_backend: redis
  cache_url: redis://prod-redis.example.com:6379/0

# Feature flags
feature_flags:
  enable_schema_v1_2: true
  enable_experimental_validators: false
  enable_ai_assisted_validation: false
```

### Loading Configuration

```python
import yaml
from pathlib import Path

def load_config(mode: RuntimeMode) -> dict:
    """Load configuration for runtime mode"""

    config_file = Path(f"config/{mode.value}.yaml")

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    # Validate configuration
    validate_config(config)

    return config

def validate_config(config: dict):
    """Validate configuration file"""

    required_keys = ["runtime_mode", "validation_policy", "validators"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")

# Usage
config = load_config(RuntimeMode.PRODUCTION)
```

---

## Environment Detection

### Automatic Detection

```python
import os
from typing import Optional

def detect_runtime_mode() -> RuntimeMode:
    """Automatically detect runtime mode from environment"""

    # 1. Check explicit environment variable
    mode_str = os.getenv("MAESTRO_RUNTIME_MODE")
    if mode_str:
        try:
            return RuntimeMode(mode_str.lower())
        except ValueError:
            print(f"Warning: Invalid MAESTRO_RUNTIME_MODE '{mode_str}'")

    # 2. Check Kubernetes environment
    k8s_namespace = os.getenv("KUBERNETES_NAMESPACE")
    if k8s_namespace:
        if "prod" in k8s_namespace:
            return RuntimeMode.PRODUCTION
        elif "staging" in k8s_namespace:
            return RuntimeMode.STAGING
        elif "dev" in k8s_namespace:
            return RuntimeMode.DEVELOPMENT

    # 3. Check hostname
    hostname = os.getenv("HOSTNAME", "")
    if "prod" in hostname:
        return RuntimeMode.PRODUCTION
    elif "staging" in hostname:
        return RuntimeMode.STAGING

    # 4. Check if running in CI/CD
    if os.getenv("CI") == "true":
        return RuntimeMode.STAGING  # CI/CD defaults to staging

    # 5. Default to development
    print("Warning: Could not detect runtime mode, defaulting to DEVELOPMENT")
    return RuntimeMode.DEVELOPMENT

# Usage
current_mode = detect_runtime_mode()
print(f"Running in {current_mode.value} mode")
```

---

## Examples and Patterns

### Example 1: Mode-Aware Contract Validation

```python
def validate_contract(contract: UniversalContract) -> VerificationResult:
    """Validate contract with mode-aware configuration"""

    # Detect runtime mode
    mode = detect_runtime_mode()

    # Load configuration
    config = load_config(mode)

    # Create policy
    policy = ValidationPolicy.from_config(config["validation_policy"])

    # Select validators
    validators = load_validators(config["validators"]["enabled"])

    # Execute validation
    if mode == RuntimeMode.DEVELOPMENT:
        return development_contract_validation(contract, validators, policy)
    elif mode == RuntimeMode.STAGING:
        return staging_contract_validation(contract, validators, policy)
    else:  # PRODUCTION
        return production_contract_validation(contract, validators, policy)

# Usage
contract = UniversalContract(...)
result = validate_contract(contract)
```

### Example 2: Environment-Specific Thresholds

```python
from typing import Dict

class ThresholdManager:
    """Manage thresholds per environment"""

    THRESHOLDS: Dict[RuntimeMode, dict] = {
        RuntimeMode.DEVELOPMENT: {
            "accessibility": 80,
            "response_time": 1000,
            "test_coverage": 60,
        },
        RuntimeMode.STAGING: {
            "accessibility": 95,
            "response_time": 500,
            "test_coverage": 80,
        },
        RuntimeMode.PRODUCTION: {
            "accessibility": 95,
            "response_time": 500,
            "test_coverage": 80,
        },
    }

    @classmethod
    def get_threshold(cls, mode: RuntimeMode, metric: str) -> float:
        """Get threshold for metric in given mode"""
        return cls.THRESHOLDS[mode][metric]

# Usage
mode = detect_runtime_mode()
accessibility_threshold = ThresholdManager.get_threshold(mode, "accessibility")
```

---

## Best Practices

### 1. Environment Parity

**✅ DO:**
- Keep staging and production configurations as similar as possible
- Use same validator versions across environments
- Test in staging before deploying to production

**❌ DON'T:**
- Make ad-hoc changes to production configuration
- Skip staging validation
- Use different thresholds without justification

### 2. Configuration as Code

**✅ DO:**
```yaml
# Store configuration in version control
git add config/
git commit -m "Update production thresholds"
```

**❌ DON'T:**
```python
# Hardcode configuration
THRESHOLD = 95  # Scattered throughout code
```

### 3. Gradual Rollout

**✅ DO:**
- Test new validators in development first
- Enable in staging after development validation
- Enable in production after staging validation
- Use feature flags for controlled rollout

**❌ DON'T:**
- Deploy untested validators to production
- Enable all validators at once
- Skip gradual rollout phases

### 4. Monitor and Alert

**✅ DO:**
```python
# Set up alerts for validation failures
if not result.passed and mode == RuntimeMode.PRODUCTION:
    alert_team("Contract validation failed in production")
```

**❌ DON'T:**
```python
# Silent failures
if not result.passed:
    pass  # Hope nobody notices
```

### 5. Document Configuration Changes

**✅ DO:**
```yaml
# config/production.yaml
# 2025-10-11: Increased accessibility threshold from 90 to 95 (compliance requirement)
validation_policy:
  accessibility_min_score: 95
```

**❌ DON'T:**
```yaml
# No comments, no history
validation_policy:
  accessibility_min_score: 95
```

---

## Conclusion

Runtime mode configuration is essential for balancing speed, quality, and cost across different environments. This guide provides:

- **Three core modes** (development, staging, production)
- **Environment-specific policies** (thresholds, validators, logging)
- **Performance optimization** (parallelism, caching)
- **Configuration management** (YAML/JSON files)
- **Best practices** for production deployments

**Key Takeaways:**

1. Use **development mode** for fast feedback during iteration
2. Use **staging mode** for realistic pre-production validation
3. Use **production mode** for maximum quality assurance
4. Configure via **YAML files** (version controlled)
5. **Automate detection** of runtime mode
6. **Monitor and alert** on failures in production
7. **Document configuration** changes

**Next Steps:**

- Create configuration files for each environment
- Implement automatic environment detection
- Set up monitoring and alerting
- Test configuration in staging before production
- Document your configuration decisions

---

**Document Version:** 1.0.0
**Protocol Version:** 1.1.0+
**Status:** Phase 2 Strategic Enhancement
**Author:** Claude (Sonnet 4.5)

This document is part of the Universal Contract Protocol (ACP) Phase 2 specification suite.

**See Also:**
- `VERSIONING_GUIDE.md` - Version management and compatibility
- `IMPLEMENTATION_GUIDE.md` - Core implementation guidance
- `VALIDATOR_FRAMEWORK.md` - Validator specifications
