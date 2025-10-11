# Contract Types Reference
## Comprehensive Catalog of Universal Contracts

**Version:** 1.1.0
**Date:** 2025-10-11
**Status:** Phase 1 Corrections Applied

---

## Overview

This document catalogs all supported contract types in the Universal Contract Protocol (ACP). Each contract type includes:
- **Purpose**: What it specifies
- **Schema**: Data structure
- **Validators**: How it's verified
- **Examples**: Real-world usage

---

## Canonical Data Model Definitions

**IMPORTANT**: This section contains the **single source of truth** for core data models used across all contract types. **DO NOT duplicate these definitions elsewhere.** Import them instead.

### Import Path

```python
# Always import from this canonical location
from contract_protocol.types import (
    AcceptanceCriterion,
    CriterionResult,
    VerificationResult,
    ContractEvent,
    ContractProposedEvent,
    ContractAcceptedEvent,
    ContractFulfilledEvent,
    ContractVerifiedEvent,
    ContractBreachedEvent,
    ValidationPolicy
)
```

### AcceptanceCriterion

```python
@dataclass
class AcceptanceCriterion:
    """
    A single acceptance criterion for a contract.
    This is the CANONICAL definition - do not duplicate.
    """
    # Identity
    criterion_id: str  # Unique identifier for this criterion

    # Definition
    description: str  # Human-readable description of what must be met
    validator_type: str  # Type of validator to use (e.g., "screenshot_diff", "openapi_validator")
    validation_config: Dict[str, Any]  # Validator-specific configuration

    # Enforcement
    required: bool = True  # Must pass for contract to be fulfilled
    blocking: bool = True  # Blocks dependent contracts if failed
    timeout_seconds: int = 300  # Maximum time allowed for validation

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)


@dataclass
class CriterionResult:
    """
    Result of evaluating a single acceptance criterion.
    This is the CANONICAL definition - do not duplicate.
    """
    # Identity
    criterion_id: str  # References AcceptanceCriterion.criterion_id

    # Result
    passed: bool  # Did this criterion pass?
    actual_value: Any  # Actual value measured
    expected_value: Any  # Expected value or threshold
    message: str  # Human-readable result message

    # Evidence
    evidence: Dict[str, Any] = field(default_factory=dict)  # Supporting evidence

    # Metadata
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    evaluator: str = "system"  # Validator that evaluated this
    duration_ms: int = 0  # Time taken to evaluate
```

### VerificationResult

```python
@dataclass
class VerificationResult:
    """
    Result of verifying an entire contract.
    This is the CANONICAL definition - do not duplicate.
    """
    # Identity
    contract_id: str  # Contract that was verified

    # Overall Result
    passed: bool  # Did the contract pass verification?
    overall_message: str  # Summary message

    # Per-Criterion Results
    criteria_results: List[CriterionResult]  # Results for each criterion

    # Artifacts and Evidence
    artifacts: List[str] = field(default_factory=list)  # Paths to artifact manifests (see ARTIFACT_STANDARD.md)
    evidence_manifest: Optional[str] = None  # Path to evidence manifest

    # Metadata
    verified_at: datetime = field(default_factory=datetime.utcnow)
    verified_by: str = "system"  # Validator or human
    total_duration_ms: int = 0  # Total verification time

    # Versioning (for caching/memoization)
    validator_versions: Dict[str, str] = field(default_factory=dict)  # {"openapi": "0.18.0", "axe": "4.4.0"}
    environment: Dict[str, str] = field(default_factory=dict)  # {"python": "3.11", "node": "20.0"}

    def cache_key(self) -> str:
        """Generate deterministic cache key including validator versions"""
        key_components = [
            self.contract_id,
            json.dumps(self.validator_versions, sort_keys=True),
            json.dumps(self.environment, sort_keys=True)
        ]
        return hashlib.sha256("|".join(key_components).encode()).hexdigest()
```

### Contract Events

```python
@dataclass
class ContractEvent:
    """
    Base class for all contract lifecycle events.
    This is the CANONICAL definition - do not duplicate.
    """
    event_id: str  # Unique event identifier
    event_type: str  # Type of event
    contract_id: str  # Contract this event relates to
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractProposedEvent(ContractEvent):
    """Emitted when a contract is proposed"""
    proposer: str  # Agent who proposed the contract
    contract: 'UniversalContract'  # The proposed contract


@dataclass
class ContractAcceptedEvent(ContractEvent):
    """Emitted when a contract is accepted"""
    acceptor: str  # Agent who accepted the contract
    acceptance_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContractFulfilledEvent(ContractEvent):
    """Emitted when a contract is fulfilled (claimed complete)"""
    fulfiller: str  # Agent who fulfilled the contract
    deliverables: List[str] = field(default_factory=list)  # Artifact IDs


@dataclass
class ContractVerifiedEvent(ContractEvent):
    """Emitted when a contract is verified"""
    verifier: str  # Validator or agent who verified
    verification_result: VerificationResult  # Verification result


@dataclass
class ContractBreachedEvent(ContractEvent):
    """Emitted when a contract is breached"""
    breach: 'ContractBreach'  # Details of the breach
    severity: str  # "critical", "major", "minor"
```

### ValidationPolicy

```python
@dataclass
class ValidationPolicy:
    """
    Configurable validation thresholds for different environments.
    Allows realistic defaults with stretch targets.
    """
    # Environment
    environment: str  # "development", "staging", "production"

    # Accessibility Thresholds
    accessibility_min_score: int = 95  # Realistic: minor violations allowed
    accessibility_target_score: int = 98  # Stretch: minimal violations
    accessibility_world_class: int = 100  # Aspirational: zero violations

    # Performance Thresholds (milliseconds)
    response_time_p95_ms: int = 500  # Realistic: acceptable UX
    response_time_p95_target_ms: int = 300  # Stretch: good UX
    response_time_p95_world_class_ms: int = 200  # Aspirational: excellent UX

    response_time_p99_ms: int = 1000
    response_time_p99_target_ms: int = 500
    response_time_p99_world_class_ms: int = 300

    # Test Coverage Thresholds (percentage)
    test_coverage_min: int = 80  # Realistic: good coverage
    test_coverage_target: int = 90  # Stretch: excellent coverage
    test_coverage_world_class: int = 95  # Aspirational: near-complete

    # Security Vulnerability Thresholds
    critical_vulnerabilities: int = 0  # Always zero
    high_vulnerabilities: int = 2  # Realistic
    medium_vulnerabilities: int = 10  # Realistic
    low_vulnerabilities: int = 50  # Informational

    # Code Quality Thresholds
    code_quality_score: int = 8  # Out of 10
    type_coverage_min: int = 70  # Type annotation coverage
    complexity_max: int = 10  # Cyclomatic complexity

    @staticmethod
    def for_environment(env: str) -> 'ValidationPolicy':
        """Get appropriate policy for environment"""
        policies = {
            "development": ValidationPolicy(
                environment="development",
                accessibility_min_score=90,  # More lenient
                response_time_p95_ms=1000,  # More lenient
                test_coverage_min=70
            ),
            "staging": ValidationPolicy(
                environment="staging",
                accessibility_min_score=95,
                response_time_p95_ms=500,
                test_coverage_min=80
            ),
            "production": ValidationPolicy(
                environment="production",
                accessibility_min_score=98,  # Strict
                response_time_p95_ms=300,  # Strict
                test_coverage_min=85
            )
        }
        return policies.get(env, ValidationPolicy(environment=env))
```

---

## Contract Type Index

1. [UX Design Contracts](#ux-design-contracts)
2. [API Specification Contracts](#api-specification-contracts)
3. [Security Policy Contracts](#security-policy-contracts)
4. [Performance Target Contracts](#performance-target-contracts)
5. [Work Package Contracts (Phase Handoffs)](#work-package-contracts)
6. [Database Schema Contracts](#database-schema-contracts)
7. [Accessibility Contracts](#accessibility-contracts)
8. [Test Coverage Contracts](#test-coverage-contracts)
9. [Code Quality Contracts](#code-quality-contracts)
10. [Documentation Contracts](#documentation-contracts)
11. [Deployment Configuration Contracts](#deployment-configuration-contracts)

---

## UX Design Contracts

### Purpose
Specifies user interface design, visual consistency, and user experience requirements that frontend developers must implement.

### Schema

```python
{
    "contract_type": "UX_DESIGN",
    "specification": {
        # Design Assets
        "figma_link": str,  # Link to Figma design
        "figma_file_key": str,  # Figma file key for API access
        "design_tokens": dict,  # Design system tokens

        # Component Specification
        "component_name": str,  # Component identifier
        "component_type": str,  # Form, page, widget, etc.

        # Design System
        "design_system": str,  # Material-UI, Ant Design, custom
        "design_system_version": str,

        # Visual Properties
        "color_palette": {
            "primary": str,  # Hex color
            "secondary": str,
            "error": str,
            "success": str
        },
        "typography": {
            "heading": str,  # Font family, size, weight
            "body": str,
            "caption": str
        },
        "spacing_system": str,  # 4px, 8px grid

        # Responsive Design
        "breakpoints": list,  # [mobile, tablet, desktop]
        "responsive_behavior": dict,  # Per-breakpoint specifications

        # Interactions
        "interactions": {
            "hover_states": bool,
            "focus_states": bool,
            "loading_states": bool,
            "error_states": bool,
            "animations": list
        },

        # Accessibility
        "accessibility_level": str,  # WCAG 2.1 AA, AAA
        "aria_labels": dict,
        "keyboard_navigation": bool,
        "screen_reader_support": bool
    },

    "acceptance_criteria": [
        {
            "criterion": "visual_consistency",
            "validator": "screenshot_diff",
            "threshold": 0.95,  # 95% similarity
            "parameters": {
                "viewport_sizes": ["375x667", "1920x1080"],
                "comparison_method": "perceptual"
            }
        },
        {
            "criterion": "design_token_compliance",
            "validator": "css_variable_check",
            "parameters": {
                "required_tokens": ["primary-color", "font-family-base"]
            }
        },
        {
            "criterion": "accessibility_score",
            "validator": "axe_core",
            "threshold": 100,  # No violations
            "parameters": {
                "level": "AA",
                "tags": ["wcag2a", "wcag2aa"]
            }
        },
        {
            "criterion": "responsive_layout",
            "validator": "viewport_tests",
            "parameters": {
                "breakpoints": ["320px", "768px", "1024px", "1920px"],
                "elements_to_check": [".login-form", ".submit-button"]
            }
        }
    ]
}
```

### Example: Login Form UX Contract

```python
UX_LOGIN_FORM = UniversalContract(
    contract_id="UX_LOGIN_001",
    contract_type="UX_DESIGN",
    name="Login Form UI Design",
    description="Material-UI based login form with accessibility",

    provider_agent="ux_designer",
    consumer_agents=["frontend_developer"],

    specification={
        "figma_link": "https://figma.com/file/abc123/LoginForm",
        "figma_file_key": "abc123",

        "component_name": "LoginForm",
        "component_type": "form",

        "design_system": "Material-UI",
        "design_system_version": "5.14.0",

        "color_palette": {
            "primary": "#1976d2",
            "secondary": "#dc004e",
            "error": "#f44336",
            "success": "#4caf50"
        },

        "typography": {
            "heading": "Roboto, 24px, 500",
            "body": "Roboto, 16px, 400",
            "caption": "Roboto, 12px, 400"
        },

        "spacing_system": "8px",

        "breakpoints": ["mobile", "tablet", "desktop"],
        "responsive_behavior": {
            "mobile": {"width": "100%", "padding": "16px"},
            "tablet": {"width": "400px", "padding": "24px"},
            "desktop": {"width": "400px", "padding": "32px"}
        },

        "interactions": {
            "hover_states": True,
            "focus_states": True,
            "loading_states": True,
            "error_states": True,
            "animations": ["fade-in", "shake-on-error"],
            "password_reveal_toggle": True,
            "remember_me_checkbox": True
        },

        "accessibility_level": "WCAG 2.1 AA",
        "aria_labels": {
            "email_input": "Email address",
            "password_input": "Password",
            "submit_button": "Log in to your account",
            "password_toggle": "Show password"
        },
        "keyboard_navigation": True,
        "screen_reader_support": True
    },

    acceptance_criteria=[
        AcceptanceCriterion(
            criterion="visual_consistency",
            validator="screenshot_diff",
            threshold=0.95,
            parameters={
                "viewport_sizes": ["375x667", "1920x1080"],
                "comparison_method": "perceptual",
                "tolerance": 5  # 5% tolerance for anti-aliasing
            },
            is_critical=True,
            description="Visual appearance must match Figma design within 95% similarity"
        ),
        AcceptanceCriterion(
            criterion="accessibility_score",
            validator="axe_core",
            threshold=100,
            parameters={"level": "AA"},
            is_critical=True,
            description="Must have zero accessibility violations at WCAG 2.1 AA level"
        ),
        AcceptanceCriterion(
            criterion="responsive_layout",
            validator="viewport_tests",
            threshold=1.0,
            parameters={"breakpoints": ["320px", "768px", "1024px"]},
            is_critical=True,
            description="Must render correctly on all specified breakpoints"
        )
    ],

    is_blocking=True,
    priority="CRITICAL"
)
```

### Validators
- **screenshot_diff**: Compares rendered component to Figma export
- **css_variable_check**: Verifies design tokens are used
- **axe_core**: Accessibility scanning
- **viewport_tests**: Responsive behavior verification

---

## API Specification Contracts

### Purpose
Specifies API endpoints, request/response schemas, error handling, and integration contracts between backend and frontend.

### Schema

```python
{
    "contract_type": "API_SPECIFICATION",
    "specification": {
        # API Definition
        "api_name": str,
        "version": str,
        "base_url": str,

        # Specification Format
        "spec_format": str,  # openapi, graphql, grpc
        "spec_file": str,  # Path to spec file
        "openapi_spec": dict,  # OpenAPI 3.0 specification

        # Endpoint Details
        "endpoint": str,  # /api/v1/auth/login
        "method": str,  # GET, POST, PUT, DELETE

        # Request Schema
        "request_schema": dict,  # JSON schema
        "request_content_type": str,  # application/json
        "required_headers": list,

        # Response Schema
        "response_schema": dict,  # JSON schema per status code
        "response_content_type": str,
        "status_codes": {
            200: {"description": str, "schema": dict},
            400: {"description": str, "schema": dict},
            401: {"description": str, "schema": dict}
        },

        # Authentication
        "authentication": str,  # JWT, OAuth2, API Key
        "authentication_scheme": dict,

        # Rate Limiting
        "rate_limiting": {
            "requests_per_minute": int,
            "burst_limit": int
        },

        # Performance
        "max_response_time_ms": int,

        # Mock Server
        "mock_server_url": str,
        "mock_available": bool
    },

    "acceptance_criteria": [
        {
            "criterion": "contract_tests_pass",
            "validator": "pact_verification",
            "parameters": {"pact_file": "contracts/auth_pact.json"}
        },
        {
            "criterion": "response_time",
            "validator": "performance_test",
            "threshold": 200,  # milliseconds
            "parameters": {"percentile": 95}
        },
        {
            "criterion": "schema_validation",
            "validator": "openapi_validator",
            "parameters": {"spec_file": "api_spec.yaml"}
        },
        {
            "criterion": "security_scan",
            "validator": "owasp_zap",
            "parameters": {"severity_threshold": "medium"}
        }
    ]
}
```

### Example: Authentication API Contract

```python
API_AUTH = UniversalContract(
    contract_id="API_AUTH_001",
    contract_type="API_SPECIFICATION",
    name="User Authentication API",
    description="JWT-based authentication endpoint",

    provider_agent="backend_developer",
    consumer_agents=["frontend_developer", "qa_engineer"],

    depends_on=["SECURITY_POLICY_001"],  # Must follow security policy

    specification={
        "api_name": "Authentication Service",
        "version": "v1",
        "base_url": "https://api.example.com/v1",

        "spec_format": "openapi",
        "spec_file": "contracts/auth_api_spec.yaml",

        "endpoint": "/api/v1/auth/login",
        "method": "POST",

        "request_schema": {
            "type": "object",
            "required": ["email", "password"],
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "example": "user@example.com"
                },
                "password": {
                    "type": "string",
                    "minLength": 12,
                    "example": "SecurePass123!"
                },
                "remember_me": {
                    "type": "boolean",
                    "default": False
                }
            }
        },

        "response_schema": {
            200: {
                "description": "Successful authentication",
                "schema": {
                    "type": "object",
                    "properties": {
                        "access_token": {"type": "string"},
                        "refresh_token": {"type": "string"},
                        "expires_in": {"type": "integer"},
                        "user": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "email": {"type": "string"},
                                "name": {"type": "string"}
                            }
                        }
                    }
                }
            },
            400: {
                "description": "Invalid request",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"}
                    }
                }
            },
            401: {
                "description": "Invalid credentials",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"}
                    }
                }
            }
        },

        "authentication": "JWT",
        "authentication_scheme": {
            "type": "bearer",
            "format": "JWT"
        },

        "rate_limiting": {
            "requests_per_minute": 100,
            "burst_limit": 10
        },

        "max_response_time_ms": 200,

        "mock_server_url": "http://localhost:3001",
        "mock_available": True
    },

    acceptance_criteria=[
        AcceptanceCriterion(
            criterion="contract_tests_pass",
            validator="pact_verification",
            parameters={
                "pact_file": "contracts/auth_pact.json",
                "provider_url": "http://localhost:8000"
            },
            is_critical=True,
            description="All contract tests must pass"
        ),
        AcceptanceCriterion(
            criterion="response_time",
            validator="performance_test",
            threshold=200,
            parameters={
                "percentile": 95,
                "duration_seconds": 60,
                "concurrent_users": 10
            },
            is_critical=True,
            description="95th percentile response time must be under 200ms"
        ),
        AcceptanceCriterion(
            criterion="schema_validation",
            validator="openapi_validator",
            parameters={"spec_file": "contracts/auth_api_spec.yaml"},
            is_critical=True,
            description="Responses must match OpenAPI schema"
        ),
        AcceptanceCriterion(
            criterion="security_scan",
            validator="owasp_zap",
            parameters={"severity_threshold": "medium"},
            is_critical=True,
            description="No medium or high severity vulnerabilities"
        )
    ],

    is_blocking=True,
    priority="CRITICAL"
)
```

### Validators
- **pact_verification**: Consumer-driven contract testing
- **performance_test**: Load testing with response time checks
- **openapi_validator**: Schema validation against OpenAPI spec
- **owasp_zap**: Security vulnerability scanning

---

## Security Policy Contracts

### Purpose
Specifies security requirements that all agents must follow, including authentication, encryption, data protection, and vulnerability thresholds.

### Schema

```python
{
    "contract_type": "SECURITY_POLICY",
    "specification": {
        # Authentication
        "authentication": {
            "method": str,  # JWT, OAuth2, SAML
            "token_expiry": str,  # 15m, 1h, 24h
            "refresh_token_expiry": str,
            "multi_factor_auth": bool
        },

        # Password Policy
        "password_requirements": {
            "min_length": int,
            "max_length": int,
            "require_uppercase": bool,
            "require_lowercase": bool,
            "require_numbers": bool,
            "require_special_chars": bool,
            "forbidden_patterns": list
        },

        # Encryption
        "encryption": {
            "data_at_rest": str,  # AES-256
            "data_in_transit": str,  # TLS 1.3
            "password_hashing": str,  # bcrypt, argon2
            "hashing_rounds": int
        },

        # Session Management
        "session_management": {
            "session_timeout": str,
            "secure_cookies": bool,
            "http_only": bool,
            "same_site": str  # strict, lax, none
        },

        # Input Validation
        "input_validation": {
            "sanitize_html": bool,
            "sql_injection_prevention": bool,
            "xss_prevention": bool,
            "csrf_protection": bool
        },

        # Vulnerability Thresholds
        "vulnerability_thresholds": {
            "critical": 0,  # No critical vulnerabilities
            "high": 0,
            "medium": 5
        },

        # Compliance
        "compliance_frameworks": list  # GDPR, HIPAA, PCI-DSS
    },

    "acceptance_criteria": [
        {
            "criterion": "security_audit",
            "validator": "bandit_scan",
            "parameters": {"severity_threshold": "low"}
        },
        {
            "criterion": "dependency_vulnerabilities",
            "validator": "snyk_scan",
            "parameters": {"severity_threshold": "medium"}
        },
        {
            "criterion": "penetration_test",
            "validator": "owasp_zap",
            "parameters": {"attack_strength": "medium"}
        }
    ]
}
```

### Example: Application Security Policy

```python
SECURITY_POLICY = UniversalContract(
    contract_id="SECURITY_POLICY_001",
    contract_type="SECURITY_POLICY",
    name="Application Security Policy",
    description="Security requirements for all application components",

    provider_agent="security_specialist",
    consumer_agents=["backend_developer", "frontend_developer", "qa_engineer"],

    specification={
        "authentication": {
            "method": "JWT",
            "token_expiry": "15m",
            "refresh_token_expiry": "7d",
            "multi_factor_auth": False
        },

        "password_requirements": {
            "min_length": 12,
            "max_length": 128,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special_chars": True,
            "forbidden_patterns": ["password", "12345", "qwerty"]
        },

        "encryption": {
            "data_at_rest": "AES-256-GCM",
            "data_in_transit": "TLS 1.3",
            "password_hashing": "bcrypt",
            "hashing_rounds": 12
        },

        "session_management": {
            "session_timeout": "30m",
            "secure_cookies": True,
            "http_only": True,
            "same_site": "strict"
        },

        "input_validation": {
            "sanitize_html": True,
            "sql_injection_prevention": True,
            "xss_prevention": True,
            "csrf_protection": True
        },

        "vulnerability_thresholds": {
            "critical": 0,
            "high": 0,
            "medium": 5,
            "low": 20
        },

        "compliance_frameworks": ["OWASP Top 10", "CWE Top 25"]
    },

    acceptance_criteria=[
        AcceptanceCriterion(
            criterion="security_audit",
            validator="bandit_scan",
            parameters={
                "severity_threshold": "low",
                "excluded_tests": []
            },
            is_critical=True,
            description="Static code analysis must show no critical/high issues"
        ),
        AcceptanceCriterion(
            criterion="dependency_vulnerabilities",
            validator="snyk_scan",
            parameters={
                "severity_threshold": "medium",
                "fail_on": "all"
            },
            is_critical=True,
            description="No known vulnerabilities in dependencies (medium or higher)"
        ),
        AcceptanceCriterion(
            criterion="tls_configuration",
            validator="sslyze",
            parameters={
                "min_version": "1.3",
                "cipher_suites": ["TLS_AES_256_GCM_SHA384"]
            },
            is_critical=True,
            description="TLS 1.3 with strong cipher suites"
        )
    ],

    is_blocking=True,
    priority="CRITICAL",
    breach_consequences=[
        "security_review_required",
        "deployment_blocked",
        "incident_reported"
    ]
)
```

### Validators
- **bandit_scan**: Python static security analysis
- **snyk_scan**: Dependency vulnerability scanning
- **owasp_zap**: Dynamic application security testing
- **sslyze**: TLS/SSL configuration analysis

---

## Performance Target Contracts

### Purpose
Specifies performance requirements including response times, throughput, resource usage, and scalability targets.

### Schema

```python
{
    "contract_type": "PERFORMANCE_TARGET",
    "specification": {
        # Response Time
        "response_time": {
            "avg_ms": int,
            "p50_ms": int,
            "p95_ms": int,
            "p99_ms": int,
            "max_ms": int
        },

        # Throughput
        "throughput": {
            "requests_per_second": int,
            "transactions_per_minute": int
        },

        # Resource Usage
        "resource_limits": {
            "cpu_percent": int,
            "memory_mb": int,
            "disk_io_mbps": int
        },

        # Scalability
        "scalability": {
            "concurrent_users": int,
            "max_connections": int,
            "horizontal_scaling": bool
        },

        # Load Testing
        "load_test_scenarios": [
            {
                "name": str,
                "duration_seconds": int,
                "ramp_up_seconds": int,
                "concurrent_users": int,
                "target_rps": int
            }
        ]
    },

    "acceptance_criteria": [
        {
            "criterion": "response_time_p95",
            "validator": "load_test",
            "threshold": 200,
            "parameters": {"duration": 300, "users": 100}
        },
        {
            "criterion": "resource_usage",
            "validator": "resource_monitor",
            "threshold": 0.8,  # 80% max
            "parameters": {"metrics": ["cpu", "memory"]}
        }
    ]
}
```

### Example: API Performance Contract

```python
PERFORMANCE_API = UniversalContract(
    contract_id="PERF_API_001",
    contract_type="PERFORMANCE_TARGET",
    name="API Performance Requirements",
    description="Performance targets for authentication API",

    provider_agent="backend_developer",
    consumer_agents=["qa_engineer", "devops_engineer"],

    depends_on=["API_AUTH_001"],

    specification={
        "response_time": {
            "avg_ms": 100,
            "p50_ms": 80,
            "p95_ms": 200,
            "p99_ms": 500,
            "max_ms": 1000
        },

        "throughput": {
            "requests_per_second": 1000,
            "transactions_per_minute": 60000
        },

        "resource_limits": {
            "cpu_percent": 70,
            "memory_mb": 512,
            "disk_io_mbps": 100
        },

        "scalability": {
            "concurrent_users": 10000,
            "max_connections": 20000,
            "horizontal_scaling": True
        },

        "load_test_scenarios": [
            {
                "name": "normal_load",
                "duration_seconds": 300,
                "ramp_up_seconds": 60,
                "concurrent_users": 100,
                "target_rps": 500
            },
            {
                "name": "peak_load",
                "duration_seconds": 600,
                "ramp_up_seconds": 120,
                "concurrent_users": 1000,
                "target_rps": 5000
            },
            {
                "name": "stress_test",
                "duration_seconds": 300,
                "ramp_up_seconds": 60,
                "concurrent_users": 5000,
                "target_rps": 10000
            }
        ]
    },

    acceptance_criteria=[
        AcceptanceCriterion(
            criterion="response_time_p95",
            validator="locust_load_test",
            threshold=200,
            parameters={
                "duration": 300,
                "users": 100,
                "spawn_rate": 10
            },
            is_critical=True,
            description="95th percentile response time under 200ms"
        ),
        AcceptanceCriterion(
            criterion="error_rate",
            validator="load_test",
            threshold=0.01,  # 1% max error rate
            parameters={"duration": 300},
            is_critical=True,
            description="Error rate under 1% during load test"
        ),
        AcceptanceCriterion(
            criterion="resource_usage",
            validator="prometheus_metrics",
            threshold=0.8,
            parameters={"metrics": ["cpu", "memory"], "duration": 300},
            is_critical=False,
            description="Resource usage stays under 80%"
        )
    ],

    is_blocking=False,  # Performance is important but not blocking
    priority="HIGH"
)
```

### Validators
- **locust_load_test**: Load testing with Locust
- **prometheus_metrics**: Resource monitoring
- **jmeter**: JMeter load tests

---

## Work Package Contracts

### Purpose
Specifies phase-to-phase work packages that define exact tasks, artifacts, and acceptance criteria for the next phase. This contract type enables clear handoffs between workflow phases.

### Schema

```python
{
    "contract_type": "WORK_PACKAGE",
    "specification": {
        # Phase Information
        "from_phase": str,  # Source phase
        "to_phase": str,  # Destination phase
        "handoff_id": str,  # Unique handoff identifier

        # Work Definition
        "tasks": [
            {
                "task_id": str,
                "description": str,
                "assignee": str,  # Persona or agent
                "estimated_duration_minutes": int,
                "priority": int,  # 1 (highest) to 10 (lowest)
                "related_artifacts": list,  # Artifact IDs
                "related_contracts": list  # Contract IDs
            }
        ],

        # Input Artifacts
        "input_artifacts": {
            "manifest_id": str,
            "artifacts": [
                {
                    "artifact_id": str,
                    "path": str,
                    "digest": str,  # SHA-256
                    "size_bytes": int,
                    "media_type": str,
                    "role": str  # "evidence", "deliverable", "report"
                }
            ]
        },

        # Context
        "context": dict,  # Additional context for next phase

        # Dependencies
        "dependencies": list,  # Other handoffs or contracts required
        "constraints": dict  # Constraints on execution
    },

    "acceptance_criteria": [
        {
            "criterion": "handoff_completeness",
            "validator": "handoff_validator",
            "parameters": {
                "required_artifacts": list,
                "required_tasks": int
            }
        },
        {
            "criterion": "artifact_integrity",
            "validator": "artifact_verifier",
            "parameters": {
                "verify_digests": True
            }
        }
    ]
}
```

### Example: Design to Implementation Handoff

```python
HANDOFF_DESIGN_TO_IMPL = UniversalContract(
    contract_id="HANDOFF_001",
    contract_type="WORK_PACKAGE",
    name="Design → Implementation Handoff",
    description="Work package for implementing designs from design phase",

    provider_agent="design_phase",
    consumer_agents=["implementation_phase"],

    depends_on=["UX_LOGIN_001", "API_AUTH_001"],  # Design contracts must be verified

    specification={
        "from_phase": "design",
        "to_phase": "implementation",
        "handoff_id": "handoff_design_impl_001",

        "tasks": [
            {
                "task_id": "impl_001",
                "description": "Implement LoginForm component according to UX design",
                "assignee": "frontend_developer",
                "estimated_duration_minutes": 120,
                "priority": 1,
                "related_artifacts": ["artifact_ux_login_figma", "artifact_design_tokens"],
                "related_contracts": ["UX_LOGIN_001"]
            },
            {
                "task_id": "impl_002",
                "description": "Implement authentication API endpoint",
                "assignee": "backend_developer",
                "estimated_duration_minutes": 180,
                "priority": 1,
                "related_artifacts": ["artifact_api_spec"],
                "related_contracts": ["API_AUTH_001"]
            },
            {
                "task_id": "impl_003",
                "description": "Integrate frontend with backend API",
                "assignee": "frontend_developer",
                "estimated_duration_minutes": 90,
                "priority": 2,
                "related_artifacts": ["artifact_api_spec", "artifact_integration_guide"],
                "related_contracts": ["API_AUTH_001", "UX_LOGIN_001"]
            }
        ],

        "input_artifacts": {
            "manifest_id": "manifest_design_phase",
            "artifacts": [
                {
                    "artifact_id": "artifact_ux_login_figma",
                    "path": "artifacts/ac/f3/acf3d19b8...",  # Content-addressable path
                    "digest": "acf3d19b8c7e2f1a5b4d3c2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0",
                    "size_bytes": 245678,
                    "media_type": "application/json",
                    "role": "deliverable"
                },
                {
                    "artifact_id": "artifact_design_tokens",
                    "path": "artifacts/12/34/1234567...",
                    "digest": "1234567890abcdef...",
                    "size_bytes": 8456,
                    "media_type": "application/json",
                    "role": "deliverable"
                },
                {
                    "artifact_id": "artifact_api_spec",
                    "path": "artifacts/ab/cd/abcdef...",
                    "digest": "abcdef1234567890...",
                    "size_bytes": 15234,
                    "media_type": "application/yaml",
                    "role": "deliverable"
                }
            ]
        },

        "context": {
            "project_name": "Authentication System",
            "sprint": "Sprint 3",
            "target_completion": "2025-10-18",
            "tech_stack": {
                "frontend": "React 18 + TypeScript + Material-UI 5",
                "backend": "Python 3.11 + FastAPI",
                "database": "PostgreSQL 15"
            }
        },

        "dependencies": [],  # No other handoffs required
        "constraints": {
            "max_implementation_time_hours": 24,
            "must_pass_contracts": ["UX_LOGIN_001", "API_AUTH_001"]
        }
    },

    acceptance_criteria=[
        AcceptanceCriterion(
            criterion_id="handoff_completeness",
            description="Handoff includes all required artifacts and tasks",
            validator_type="handoff_validator",
            validation_config={
                "required_artifacts": ["figma_export", "api_spec", "design_tokens"],
                "min_tasks": 2
            },
            required=True,
            blocking=True
        ),
        AcceptanceCriterion(
            criterion_id="artifact_integrity",
            description="All artifacts have valid digests and are accessible",
            validator_type="artifact_verifier",
            validation_config={
                "verify_digests": True,
                "verify_accessibility": True
            },
            required=True,
            blocking=True
        ),
        AcceptanceCriterion(
            criterion_id="task_clarity",
            description="All tasks have clear descriptions and assignees",
            validator_type="task_validator",
            validation_config={
                "require_description": True,
                "require_assignee": True,
                "require_estimates": True
            },
            required=True,
            blocking=False
        )
    ],

    is_blocking=True,  # Implementation cannot start without valid handoff
    priority="CRITICAL"
)
```

### Validators
- **handoff_validator**: Validates completeness of handoff specification
- **artifact_verifier**: Verifies artifact integrity and accessibility
- **task_validator**: Validates task definitions are clear and actionable

### Benefits of Work Package Contracts
- **No Ambiguity**: Next phase knows exactly what to do
- **Complete Context**: All input artifacts explicitly referenced
- **Verifiable Handoffs**: Phase boundaries are contracts that can be verified
- **Traceability**: Complete audit trail of work packages

For detailed specification, see `HANDOFF_SPEC.md`.

---

## Summary Table

| Contract Type | Primary Validator | Blocking? | Common Use Cases |
|--------------|------------------|-----------|------------------|
| UX_DESIGN | screenshot_diff, axe_core | Yes | UI consistency, accessibility |
| API_SPECIFICATION | pact_verification | Yes | API contracts, integration |
| SECURITY_POLICY | bandit_scan, snyk_scan | Yes | Security requirements |
| PERFORMANCE_TARGET | load_test | No | Performance SLAs |
| WORK_PACKAGE | handoff_validator, artifact_verifier | Yes | Phase handoffs, work packages |
| DATABASE_SCHEMA | schema_validator | Yes | Data integrity |
| ACCESSIBILITY | axe_core, pa11y | Yes | WCAG compliance |
| TEST_COVERAGE | coverage.py | No | Code quality |
| CODE_QUALITY | pylint, mypy | No | Code standards |
| DOCUMENTATION | markdown_lint | No | Docs completeness |
| DEPLOYMENT_CONFIG | config_validator | Yes | Deployment specs |

---

## Creating Custom Contract Types

To create a new contract type:

1. Define the specification schema
2. Implement validators
3. Set acceptance criteria
4. Document examples
5. Register with ContractRegistry

See **VALIDATOR_FRAMEWORK.md** for details on building custom validators.
