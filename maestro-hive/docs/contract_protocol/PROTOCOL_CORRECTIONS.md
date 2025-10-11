# Universal Contract Protocol - Corrections and Fixes

**Document Status**: Phase 1 Implementation
**Date**: 2025-10-11
**Purpose**: Document all corrections being made to the Universal Contract Protocol based on GPT5's practical feedback

---

## Executive Summary

This document details corrections to the Universal Contract Protocol (ACP) documentation to address inconsistencies, API mismatches, data model duplication, and implementation feasibility issues identified in GPT5's review. These corrections make the protocol internally consistent, practically implementable, and production-ready.

**Scope**: Documentation-only corrections. No code changes.

---

## 1. Lifecycle State Model Corrections

### Issue

**Problem**: Examples use `VERIFIED_WITH_WARNINGS` state, but `ContractLifecycle` enum does not include it. The `NEGOTIATING` state is defined but never used in flows or APIs.

**Impact**:
- Examples cannot be implemented as written
- State model is incomplete for real-world scenarios where verification finds non-blocking issues
- Unclear when negotiation should occur

### Resolution

**Action 1: Add VERIFIED_WITH_WARNINGS to ContractLifecycle enum**

```python
class ContractLifecycle(Enum):
    """Lifecycle states for contracts"""
    DRAFT = "draft"                           # Initial state
    PROPOSED = "proposed"                     # Submitted for review
    NEGOTIATING = "negotiating"               # Under negotiation
    ACCEPTED = "accepted"                     # Agreed upon, ready to execute
    IN_PROGRESS = "in_progress"              # Currently being fulfilled
    FULFILLED = "fulfilled"                   # Claimed as complete
    VERIFIED = "verified"                     # Verified as meeting all criteria
    VERIFIED_WITH_WARNINGS = "verified_with_warnings"  # NEW: Verified with non-blocking issues
    BREACHED = "breached"                     # Failed to meet criteria
```

**Action 2: Define allowed state transitions**

```
DRAFT → PROPOSED → NEGOTIATING → ACCEPTED → IN_PROGRESS → FULFILLED → VERIFIED | VERIFIED_WITH_WARNINGS | BREACHED

Special transitions:
- NEGOTIATING → DRAFT (renegotiation required)
- VERIFIED_WITH_WARNINGS → IN_PROGRESS (address warnings)
- BREACHED → IN_PROGRESS (remediation attempt)
- Any state → BREACHED (critical failure)
```

**Action 3: Wire NEGOTIATING into contract negotiation flow**

Add to ContractRegistry API:
- `negotiate_contract(contract_id: str, changes: List[ContractChange]) -> ContractNegotiation`
- `accept_negotiation(negotiation_id: str) -> UniversalContract`
- `reject_negotiation(negotiation_id: str, reason: str) -> None`

**Files Updated**:
- UNIVERSAL_CONTRACT_PROTOCOL.md: Section 3.3 (Lifecycle States)
- CONTRACT_TYPES_REFERENCE.md: ContractLifecycle enum definition
- EXAMPLES_AND_PATTERNS.md: All examples using VERIFIED_WITH_WARNINGS

---

## 2. API Surface Reconciliation

### Issue

**Problem**: Examples call methods not defined in ContractRegistry:
- `amend_contract()`
- `update_contract_with_clarification()`
- `can_execute_contract()`
- `get_contracts_blocked_by()`
- `log_contract_warning()`
- `handle_late_breach()`
- `get_execution_plan()`

Also, method naming inconsistencies:
- Example uses `get_contracts_blocked_by()` while implementation has `get_blocked_contracts()`

**Impact**: Examples cannot be run against documented API. Developers will be confused about which methods exist.

### Resolution

**Option A: Implement missing methods** (RECOMMENDED)

Add to ContractRegistry API specification:

```python
class ContractRegistry:
    """Core contract registry API"""

    # Existing methods (keep as-is)
    def register_contract(self, contract: UniversalContract) -> str: ...
    def get_executable_contracts(self) -> List[UniversalContract]: ...
    def verify_contract_fulfillment(self, contract_id: str, evidence: Dict[str, Any]) -> VerificationResult: ...
    def get_blocked_contracts(self) -> List[UniversalContract]: ...
    def update_contract_state(self, contract_id: str, new_state: ContractLifecycle) -> None: ...

    # NEW: Methods to add
    def amend_contract(
        self,
        contract_id: str,
        amendment: ContractAmendment
    ) -> UniversalContract:
        """Amend an existing contract with changes"""
        pass

    def update_contract_with_clarification(
        self,
        contract_id: str,
        clarification: ContractClarification
    ) -> UniversalContract:
        """Add clarification to contract without changing acceptance criteria"""
        pass

    def can_execute_contract(self, contract_id: str) -> Tuple[bool, Optional[str]]:
        """Check if contract can execute (dependencies satisfied)"""
        pass

    def get_contracts_blocked_by(self, contract_id: str) -> List[str]:
        """Get contracts blocked by this contract (inverse of get_blocked_contracts)"""
        # Alias to maintain consistency
        pass

    def log_contract_warning(
        self,
        contract_id: str,
        warning: ContractWarning
    ) -> None:
        """Log non-blocking warning for contract"""
        pass

    def handle_late_breach(
        self,
        contract_id: str,
        breach: ContractBreach
    ) -> BreachResolution:
        """Handle breach discovered after initial verification"""
        pass

    def get_execution_plan(self) -> ExecutionPlan:
        """Generate topologically sorted execution plan for all accepted contracts"""
        pass
```

**Option B: Remove methods from examples** (NOT RECOMMENDED)

Remove calls to undefined methods and simplify examples. This reduces expressiveness.

**Decision**: Implement Option A - add methods to API specification.

**Files Updated**:
- UNIVERSAL_CONTRACT_PROTOCOL.md: Section 4 (Core API)
- IMPLEMENTATION_GUIDE.md: Add implementation guidance for new methods
- EXAMPLES_AND_PATTERNS.md: Keep examples as-is (now valid)

---

## 3. Data Model Centralization

### Issue

**Problem**: `AcceptanceCriterion`, `CriterionResult`, and `VerificationResult` are defined in multiple places with slight variations. This causes drift and inconsistency.

**Impact**: Developers don't know which definition is canonical. Copy-paste leads to version skew.

### Resolution

**Action: Establish single source of truth in CONTRACT_TYPES_REFERENCE.md**

**Canonical Definitions**:

```python
# ============================================================================
# CANONICAL DATA MODELS - DO NOT DUPLICATE
# Import these definitions instead of redefining
# ============================================================================

@dataclass
class AcceptanceCriterion:
    """Single source of truth for acceptance criteria definition"""
    criterion_id: str
    description: str
    validator_type: str
    validation_config: Dict[str, Any]
    required: bool = True
    blocking: bool = True
    timeout_seconds: int = 300

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)


@dataclass
class CriterionResult:
    """Single source of truth for criterion result definition"""
    criterion_id: str
    passed: bool
    actual_value: Any
    expected_value: Any
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    evaluator: str = "system"
    duration_ms: int = 0


@dataclass
class VerificationResult:
    """Single source of truth for verification result definition"""
    contract_id: str
    passed: bool
    criteria_results: List[CriterionResult]
    overall_message: str

    # Artifacts and evidence
    artifacts: List[str] = field(default_factory=list)  # Paths to artifact manifests
    evidence_manifest: Optional[str] = None  # Path to evidence manifest

    # Metadata
    verified_at: datetime = field(default_factory=datetime.utcnow)
    verified_by: str = "system"
    total_duration_ms: int = 0

    # Versioning (for caching/memoization)
    validator_versions: Dict[str, str] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
```

**Import Pattern**:

```python
# In other files, import instead of redefining
from contract_protocol.types import (
    AcceptanceCriterion,
    CriterionResult,
    VerificationResult
)
```

**Files Updated**:
- CONTRACT_TYPES_REFERENCE.md: Add "Canonical Definitions" section at top
- UNIVERSAL_CONTRACT_PROTOCOL.md: Remove duplicate definitions, add imports
- EXAMPLES_AND_PATTERNS.md: Remove duplicate definitions, add imports
- VALIDATOR_FRAMEWORK.md: Remove duplicate definitions, add imports

---

## 4. Validator Implementation Corrections

### Issue

**Problem**: Several validator examples have implementation issues:

1. **OpenAPI Validator**: Likely incorrect for modern `openapi-core`
2. **Accessibility Validator**: Requires Selenium + axe-core without runtime requirements defined
3. **Performance Validator**: References Locust in-process (production uses separate process)
4. **Security Validators**: Require sandboxing, credentials, timeouts not documented

**Impact**: Validators cannot be implemented as written. Missing critical operational requirements.

### Resolution

**Action 1: Fix OpenAPI Validator**

```python
from openapi_core import Spec
from openapi_core.validation.request import openapi_request_validator
from openapi_core.validation.response import openapi_response_validator
from openapi_core.contrib.requests import RequestsOpenAPIRequest, RequestsOpenAPIResponse
import yaml

class OpenAPIValidator(BaseValidator):
    """Corrected OpenAPI validator using openapi-core v0.18+"""

    def __init__(self):
        super().__init__("openapi_specification")

    async def validate(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        # Load spec correctly
        spec_path = criterion.validation_config["spec_path"]
        with open(spec_path, 'r') as f:
            spec_dict = yaml.safe_load(f)

        spec = Spec.from_dict(spec_dict)

        # Validate request/response
        endpoint = criterion.validation_config["endpoint"]
        method = criterion.validation_config.get("method", "GET")

        # Create OpenAPI request/response objects
        request = RequestsOpenAPIRequest(context['request'])
        response = RequestsOpenAPIResponse(context['response'])

        # Validate
        request_result = openapi_request_validator.validate(spec, request)
        response_result = openapi_response_validator.validate(spec, response)

        passed = not (request_result.errors or response_result.errors)

        return CriterionResult(
            criterion_id=criterion.criterion_id,
            passed=passed,
            actual_value="valid" if passed else "invalid",
            expected_value="valid",
            message="OpenAPI validation passed" if passed else f"Errors: {request_result.errors + response_result.errors}",
            evidence={
                "request_errors": [str(e) for e in request_result.errors],
                "response_errors": [str(e) for e in response_result.errors]
            }
        )
```

**Action 2: Fix Accessibility Validator with runtime requirements**

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from axe_selenium_python import Axe

class AccessibilityValidator(BaseValidator):
    """Accessibility validator with explicit runtime requirements"""

    # RUNTIME REQUIREMENTS:
    # - Chrome/Chromium browser installed
    # - chromedriver in PATH
    # - axe-selenium-python package: pip install axe-selenium-python
    # - Headless mode for CI

    def __init__(self):
        super().__init__("accessibility_compliance")
        self.timeout_seconds = 30

    async def validate(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        url = criterion.validation_config["url"]

        # Setup headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--timeout={self.timeout_seconds}")

        driver = webdriver.Chrome(options=chrome_options)

        try:
            driver.get(url)
            axe = Axe(driver)
            axe.inject()
            results = axe.run()

            violations = results["violations"]
            passed = len(violations) == 0

            return CriterionResult(
                criterion_id=criterion.criterion_id,
                passed=passed,
                actual_value=len(violations),
                expected_value=0,
                message=f"Found {len(violations)} accessibility violations" if not passed else "No violations",
                evidence={
                    "violations": violations,
                    "passes": len(results["passes"]),
                    "incomplete": len(results["incomplete"]),
                    "url": url
                }
            )
        finally:
            driver.quit()
```

**Action 3: Document Performance Validator external execution**

```python
class PerformanceValidator(BaseValidator):
    """Performance validator using external Locust process"""

    # RUNTIME REQUIREMENTS:
    # - Locust installed: pip install locust
    # - Locustfile prepared at specified path
    # - Results written to JSON file
    # - Separate process execution (not in-process)

    async def validate(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        locustfile = criterion.validation_config["locustfile"]
        host = criterion.validation_config["host"]
        users = criterion.validation_config.get("users", 100)
        duration = criterion.validation_config.get("duration", "5m")

        # Run Locust as external process
        result_file = f"/tmp/locust_results_{criterion.criterion_id}.json"

        cmd = [
            "locust",
            "-f", locustfile,
            "--headless",
            "--host", host,
            "--users", str(users),
            "--run-time", duration,
            "--json", result_file
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        # Parse results from JSON file
        with open(result_file, 'r') as f:
            results = json.load(f)

        # Evaluate against thresholds
        threshold = criterion.validation_config["threshold_ms"]
        p95_latency = results["percentile_95"]

        passed = p95_latency < threshold

        return CriterionResult(
            criterion_id=criterion.criterion_id,
            passed=passed,
            actual_value=p95_latency,
            expected_value=f"< {threshold}ms",
            message=f"P95 latency: {p95_latency}ms",
            evidence={
                "results_file": result_file,
                "users": users,
                "duration": duration,
                "full_results": results
            }
        )
```

**Action 4: Document Security Validator sandboxing**

Add to all security validators (bandit, snyk, zap):

```python
# SECURITY REQUIREMENTS:
# - Run in sandboxed container (Docker/podman)
# - No access to production credentials
# - Timeout enforcement (max 5 minutes)
# - Sanitize logs before storage
# - Never store secrets in Context Store

# Example Docker execution
async def run_sandboxed_validator(tool: str, args: List[str]) -> Dict:
    """Run security tool in Docker container"""
    cmd = [
        "docker", "run",
        "--rm",
        "--network", "none",  # No network access
        "--read-only",        # Read-only filesystem
        "--tmpfs", "/tmp",    # Writable tmp
        "--user", "nobody",   # Non-root user
        f"security-tools:{tool}",
        *args
    ]

    # Execute with timeout
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=300  # 5 minute timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        raise ValidatorTimeoutError(f"{tool} exceeded 5 minute timeout")

    return parse_results(stdout)
```

**Files Updated**:
- VALIDATOR_FRAMEWORK.md: Replace all validator implementations with corrected versions
- IMPLEMENTATION_GUIDE.md: Add "Validator Runtime Requirements" section

---

## 5. Realistic Threshold Corrections

### Issue

**Problem**: Some examples use unrealistic thresholds:
- Accessibility: 100% compliance (zero violations)
- Response time: 200ms with bcrypt-12 password hashing
- Test coverage: 100%

**Impact**: Teams will immediately hit BREACHED state in normal production environments. Discourages adoption.

### Resolution

**Action: Update to realistic defaults with stretch targets documented**

```python
# BEFORE (unrealistic)
"accessibility_score": 100  # Zero violations
"response_time": 200        # 200ms with bcrypt
"test_coverage": 100        # 100% coverage

# AFTER (realistic with stretch targets)
"accessibility_score": {
    "default": 95,      # Realistic: minor violations allowed
    "target": 98,       # Stretch: minimal violations
    "world_class": 100  # Aspirational: zero violations
}

"response_time": {
    "default": 500,     # Realistic: acceptable UX
    "target": 300,      # Stretch: good UX
    "world_class": 200  # Aspirational: excellent UX (requires optimization)
}

"test_coverage": {
    "default": 80,      # Realistic: good coverage
    "target": 90,       # Stretch: excellent coverage
    "world_class": 95   # Aspirational: near-complete coverage
}
```

**Policy Configuration**:

```python
@dataclass
class ValidationPolicy:
    """Configurable validation thresholds"""
    environment: str  # "development", "staging", "production"

    # Accessibility
    accessibility_min_score: int = 95
    accessibility_target_score: int = 98

    # Performance
    response_time_p95_ms: int = 500
    response_time_p99_ms: int = 1000

    # Testing
    test_coverage_min: int = 80
    test_coverage_target: int = 90

    # Security
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 2
    medium_vulnerabilities: int = 10
```

**Files Updated**:
- EXAMPLES_AND_PATTERNS.md: Update all examples with realistic thresholds
- CONTRACT_TYPES_REFERENCE.md: Add ValidationPolicy class
- UNIVERSAL_CONTRACT_PROTOCOL.md: Add "Setting Realistic Thresholds" section

---

## 6. Artifact Standardization

### Issue

**Problem**: Examples pass arbitrary file paths for artifacts. No content-addressable storage, no manifest schema, no digest verification.

**Impact**:
- Cannot verify artifact integrity
- Cannot implement caching/memoization reliably
- No way to address artifacts in distributed system

### Resolution

**Action: Define Artifact type and manifest schema**

```python
@dataclass
class Artifact:
    """Content-addressable artifact with verification"""

    # Identity
    artifact_id: str                    # UUID
    path: str                           # Relative path in artifact store

    # Content verification
    digest: str                         # SHA-256 hash
    size_bytes: int                     # File size

    # Metadata
    media_type: str                     # MIME type (e.g., "application/json")
    role: str                           # "evidence", "deliverable", "report", "screenshot"
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"

    # Relationships
    related_contract_id: Optional[str] = None
    related_node_id: Optional[str] = None

    def verify(self) -> bool:
        """Verify artifact integrity by checking digest"""
        actual_digest = compute_sha256(self.path)
        return actual_digest == self.digest


@dataclass
class ArtifactManifest:
    """Manifest listing all artifacts for a contract or phase"""

    manifest_id: str
    contract_id: Optional[str] = None
    node_id: Optional[str] = None

    artifacts: List[Artifact] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    manifest_version: str = "1.0.0"

    def add_artifact(self, artifact: Artifact) -> None:
        """Add artifact to manifest"""
        self.artifacts.append(artifact)

    def verify_all(self) -> Tuple[bool, List[str]]:
        """Verify all artifacts in manifest"""
        failures = []
        for artifact in self.artifacts:
            if not artifact.verify():
                failures.append(artifact.artifact_id)
        return len(failures) == 0, failures

    def to_json(self) -> str:
        """Serialize manifest to JSON"""
        return json.dumps(asdict(self), default=str, indent=2)
```

**Artifact Store**:

```python
class ArtifactStore:
    """Content-addressable artifact storage"""

    def __init__(self, base_path: str = "/var/maestro/artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        file_path: str,
        role: str,
        media_type: str,
        related_contract_id: Optional[str] = None
    ) -> Artifact:
        """Store artifact with content-addressable path"""

        # Compute digest
        digest = compute_sha256(file_path)

        # Content-addressable path: {base}/{digest[:2]}/{digest[2:4]}/{digest}
        dest_dir = self.base_path / digest[:2] / digest[2:4]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / digest

        # Copy file
        shutil.copy2(file_path, dest_path)

        # Get file size
        size_bytes = os.path.getsize(dest_path)

        # Create artifact
        artifact = Artifact(
            artifact_id=str(uuid.uuid4()),
            path=str(dest_path.relative_to(self.base_path)),
            digest=digest,
            size_bytes=size_bytes,
            media_type=media_type,
            role=role,
            related_contract_id=related_contract_id
        )

        return artifact

    def retrieve(self, digest: str) -> Optional[Path]:
        """Retrieve artifact by digest"""
        artifact_path = self.base_path / digest[:2] / digest[2:4] / digest
        return artifact_path if artifact_path.exists() else None
```

**Files Updated**:
- New document: `ARTIFACT_STANDARD.md` (comprehensive specification)
- UNIVERSAL_CONTRACT_PROTOCOL.md: Replace artifact references with Artifact type
- EXAMPLES_AND_PATTERNS.md: Update examples to use ArtifactStore
- CONTRACT_TYPES_REFERENCE.md: Add Artifact and ArtifactManifest definitions

---

## 7. HandoffSpec Work Package Model

### Issue

**Problem**: No defined model for passing work packages between phases. Documentation doesn't specify how phase boundaries transfer exact instructions, resolved artifacts, and acceptance criteria to next phase.

**Impact**:
- Gap between "phase complete" and "next phase start"
- Unclear what information flows forward
- No contract type for handoff validation

### Resolution

**Action: Define HandoffSpec as first-class contract type**

```python
@dataclass
class HandoffSpec:
    """Work package specification for phase-to-phase transfer"""

    # Identity
    handoff_id: str
    from_phase: str
    to_phase: str

    # Work definition
    tasks: List[Task]                    # Exact tasks for next phase
    acceptance_criteria: List[AcceptanceCriterion]  # What must be met

    # Artifacts and context
    input_artifacts: ArtifactManifest    # Artifacts from previous phase
    context: Dict[str, Any]              # Additional context

    # Dependencies and constraints
    dependencies: List[str] = field(default_factory=list)  # Other handoffs required
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"

    # Validation
    validated: bool = False
    validation_result: Optional[VerificationResult] = None


@dataclass
class Task:
    """Individual task within handoff work package"""
    task_id: str
    description: str
    assignee: str                        # Persona or agent
    estimated_duration_minutes: int
    priority: int = 5                    # 1 (highest) to 10 (lowest)

    # References
    related_artifacts: List[str] = field(default_factory=list)  # Artifact IDs
    related_contracts: List[str] = field(default_factory=list)  # Contract IDs
```

**Handoff Contract Type**:

```python
# Add to ContractType enum
class ContractType(Enum):
    # ... existing types ...
    WORK_PACKAGE = "work_package"        # NEW: Phase-to-phase handoff


# Create handoff contract
handoff_contract = UniversalContract(
    contract_id=str(uuid.uuid4()),
    contract_type=ContractType.WORK_PACKAGE,
    title=f"Handoff: {from_phase} → {to_phase}",
    description=f"Work package transfer from {from_phase} to {to_phase}",
    responsible_party=to_phase,
    beneficiary_party="project",
    dependencies=[f"contract_{from_phase}_complete"],
    acceptance_criteria=[
        AcceptanceCriterion(
            criterion_id="handoff_validated",
            description="Handoff spec is complete and validated",
            validator_type="handoff_validator",
            validation_config={"handoff_id": handoff_spec.handoff_id}
        )
    ],
    metadata={
        "handoff_spec": handoff_spec,
        "phase_boundary": f"{from_phase}/{to_phase}"
    }
)
```

**Files Updated**:
- New document: `HANDOFF_SPEC.md` (comprehensive specification)
- CONTRACT_TYPES_REFERENCE.md: Add WORK_PACKAGE contract type
- UNIVERSAL_CONTRACT_PROTOCOL.md: Add section on phase boundaries
- EXAMPLES_AND_PATTERNS.md: Add handoff examples

---

## 8. State Machine and Event Definitions

### Issue

**Problem**: No formal state machine documentation showing allowed transitions and guard conditions. No event schemas for contract lifecycle events.

**Impact**: Implementations will differ in state transition logic. No standardized event notification.

### Resolution

**Action: Define state machine and event schemas**

```python
# State Transitions
ALLOWED_TRANSITIONS = {
    ContractLifecycle.DRAFT: [
        ContractLifecycle.PROPOSED,
    ],
    ContractLifecycle.PROPOSED: [
        ContractLifecycle.NEGOTIATING,
        ContractLifecycle.ACCEPTED,
        ContractLifecycle.DRAFT,  # Back to draft
    ],
    ContractLifecycle.NEGOTIATING: [
        ContractLifecycle.ACCEPTED,
        ContractLifecycle.DRAFT,  # Renegotiation required
    ],
    ContractLifecycle.ACCEPTED: [
        ContractLifecycle.IN_PROGRESS,
    ],
    ContractLifecycle.IN_PROGRESS: [
        ContractLifecycle.FULFILLED,
        ContractLifecycle.BREACHED,  # Critical failure during execution
    ],
    ContractLifecycle.FULFILLED: [
        ContractLifecycle.VERIFIED,
        ContractLifecycle.VERIFIED_WITH_WARNINGS,
        ContractLifecycle.BREACHED,
    ],
    ContractLifecycle.VERIFIED: [
        # Terminal state (success)
    ],
    ContractLifecycle.VERIFIED_WITH_WARNINGS: [
        ContractLifecycle.IN_PROGRESS,  # Address warnings
    ],
    ContractLifecycle.BREACHED: [
        ContractLifecycle.IN_PROGRESS,  # Remediation attempt
    ],
}

# Guard Conditions
@dataclass
class StateTransitionGuard:
    """Guard conditions for state transitions"""

    @staticmethod
    def can_transition(
        contract: UniversalContract,
        from_state: ContractLifecycle,
        to_state: ContractLifecycle
    ) -> Tuple[bool, Optional[str]]:
        """Check if transition is allowed"""

        # Check if transition exists
        if to_state not in ALLOWED_TRANSITIONS.get(from_state, []):
            return False, f"Transition {from_state.value} → {to_state.value} not allowed"

        # Additional guards
        if to_state == ContractLifecycle.IN_PROGRESS:
            # Check dependencies satisfied
            blocked = get_blocking_dependencies(contract)
            if blocked:
                return False, f"Blocked by dependencies: {blocked}"

        return True, None


# Event Schemas
@dataclass
class ContractEvent:
    """Base class for contract lifecycle events"""
    event_id: str
    event_type: str
    contract_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractProposedEvent(ContractEvent):
    """Contract proposed event"""
    proposer: str
    contract: UniversalContract


@dataclass
class ContractAcceptedEvent(ContractEvent):
    """Contract accepted event"""
    acceptor: str
    acceptance_timestamp: datetime


@dataclass
class ContractFulfilledEvent(ContractEvent):
    """Contract fulfilled event"""
    fulfiller: str
    deliverables: List[str]  # Artifact IDs


@dataclass
class ContractVerifiedEvent(ContractEvent):
    """Contract verified event"""
    verifier: str
    verification_result: VerificationResult


@dataclass
class ContractBreachedEvent(ContractEvent):
    """Contract breached event"""
    breach: ContractBreach
    severity: str  # "critical", "major", "minor"


@dataclass
class ContractAmendedEvent(ContractEvent):
    """Contract amended event"""
    amendment: ContractAmendment
    requires_reacceptance: bool
```

**Files Updated**:
- UNIVERSAL_CONTRACT_PROTOCOL.md: Add "State Machine" section
- IMPLEMENTATION_GUIDE.md: Add "Event Handling" section
- CONTRACT_TYPES_REFERENCE.md: Add event class definitions

---

## 9. Integration with Existing System

### Issue

**Problem**: Unclear how ACP integrates with existing ContractManager in conductor. Risk of creating two parallel contract systems.

**Impact**: Duplication of logic, confusion about which system to use.

### Resolution

**Action: Define integration strategy**

**Option A: Adapt ACP to wrap ContractManager** (RECOMMENDED)

```python
class UniversalContractAdapter:
    """Adapter wrapping existing ContractManager"""

    def __init__(self, contract_manager: ContractManager):
        self.contract_manager = contract_manager
        self.universal_contracts: Dict[str, UniversalContract] = {}

    def register_contract(self, contract: UniversalContract) -> str:
        """Register universal contract via existing manager"""
        # Convert to legacy format
        legacy_contract = self._to_legacy_contract(contract)

        # Register with existing manager
        contract_id = self.contract_manager.add_contract(legacy_contract)

        # Store universal contract
        self.universal_contracts[contract_id] = contract

        return contract_id

    def _to_legacy_contract(self, contract: UniversalContract) -> dict:
        """Convert universal contract to legacy format"""
        return {
            "id": contract.contract_id,
            "type": contract.contract_type.value,
            "requirements": [c.description for c in contract.acceptance_criteria],
            # ... map other fields
        }
```

**Option B: Implement thin adapter to avoid duplication**

Use composition pattern:
- ContractManager: Low-level contract storage/retrieval
- UniversalContractRegistry: High-level contract protocol (wraps ContractManager)

**Files Updated**:
- IMPLEMENTATION_GUIDE.md: Add "Integration with Existing Systems" section
- New document: `MIGRATION_FROM_LEGACY.md` (to be created in Phase 2)

---

## 10. Versioning and Caching

### Issue

**Problem**: No versioning for contract types and schemas. No guidance on caching keys for memoization (especially important for LLM-driven validators).

**Impact**:
- Breaking changes not detectable
- Cache invalidation unclear
- Non-deterministic results from LLM validators

### Resolution

**Action: Add versioning fields**

```python
@dataclass
class UniversalContract:
    # ... existing fields ...

    # Versioning (NEW)
    schema_version: str = "1.0.0"        # Contract schema version
    contract_version: int = 1             # Incremented on amendments

    # For caching/memoization
    def cache_key(self) -> str:
        """Generate deterministic cache key"""
        key_components = [
            self.contract_id,
            self.contract_type.value,
            str(self.contract_version),
            self.schema_version,
            json.dumps(self.acceptance_criteria, sort_keys=True, default=str)
        ]
        return hashlib.sha256("|".join(key_components).encode()).hexdigest()


@dataclass
class VerificationResult:
    # ... existing fields ...

    # Versioning (NEW)
    validator_versions: Dict[str, str] = field(default_factory=dict)  # {"openapi": "0.18.0"}
    environment: Dict[str, str] = field(default_factory=dict)          # {"python": "3.11", "node": "20.0"}

    # For caching
    def cache_key(self) -> str:
        """Generate cache key including validator versions"""
        key_components = [
            self.contract_id,
            json.dumps(self.validator_versions, sort_keys=True),
            json.dumps(self.environment, sort_keys=True)
        ]
        return hashlib.sha256("|".join(key_components).encode()).hexdigest()
```

**Compatibility Matrix**:

```python
@dataclass
class SchemaCompatibility:
    """Schema compatibility rules"""

    COMPATIBILITY_MATRIX = {
        ("1.0.0", "1.0.1"): "BACKWARD",   # Patch: backward compatible
        ("1.0.0", "1.1.0"): "BACKWARD",   # Minor: backward compatible
        ("1.0.0", "2.0.0"): "BREAKING",   # Major: breaking change
    }

    @staticmethod
    def check_compatibility(old_version: str, new_version: str) -> str:
        """Check if schema versions are compatible"""
        return SchemaCompatibility.COMPATIBILITY_MATRIX.get(
            (old_version, new_version),
            "UNKNOWN"
        )
```

**Files Updated**:
- CONTRACT_TYPES_REFERENCE.md: Add versioning fields
- UNIVERSAL_CONTRACT_PROTOCOL.md: Add "Versioning and Compatibility" section
- IMPLEMENTATION_GUIDE.md: Add "Caching and Memoization" section

---

## Summary of Corrections

| # | Issue | Resolution | Files Updated | Priority |
|---|-------|------------|---------------|----------|
| 1 | Lifecycle state mismatch | Add VERIFIED_WITH_WARNINGS, define transitions, wire NEGOTIATING | 3 | HIGH |
| 2 | API method mismatches | Add 7 methods to ContractRegistry API spec | 3 | HIGH |
| 3 | Data model duplication | Centralize definitions in CONTRACT_TYPES_REFERENCE | 4 | HIGH |
| 4 | Validator implementation issues | Fix OpenAPI, accessibility, performance, security validators | 2 | HIGH |
| 5 | Unrealistic thresholds | Update to realistic defaults with stretch targets | 3 | MEDIUM |
| 6 | No artifact standardization | Define Artifact, ArtifactManifest, ArtifactStore | 4 + NEW | HIGH |
| 7 | Missing HandoffSpec | Define work package model and WORK_PACKAGE contract type | 4 + NEW | HIGH |
| 8 | No state machine docs | Define state transitions, guards, and event schemas | 3 | MEDIUM |
| 9 | Integration unclear | Define adapter pattern for existing ContractManager | 2 | MEDIUM |
| 10 | No versioning | Add schema_version, contract_version, compatibility checks | 3 | MEDIUM |

**Total Files Updated**: 5 existing + 2 new = 7 documents

---

## Implementation Checklist

- [ ] Update UNIVERSAL_CONTRACT_PROTOCOL.md
  - [ ] Add VERIFIED_WITH_WARNINGS to lifecycle enum
  - [ ] Define state transition diagram
  - [ ] Add 7 new API methods
  - [ ] Add versioning section
  - [ ] Add phase boundary / HandoffSpec section
  - [ ] Replace artifact references with Artifact type

- [ ] Update CONTRACT_TYPES_REFERENCE.md
  - [ ] Add "Canonical Definitions" section at top
  - [ ] Add WORK_PACKAGE contract type
  - [ ] Add versioning fields
  - [ ] Add event class definitions
  - [ ] Add ValidationPolicy class

- [ ] Update IMPLEMENTATION_GUIDE.md
  - [ ] Add implementation guidance for 7 new API methods
  - [ ] Add "Validator Runtime Requirements" section
  - [ ] Add "Event Handling" section
  - [ ] Add "Caching and Memoization" section
  - [ ] Add "Integration with Existing Systems" section

- [ ] Update VALIDATOR_FRAMEWORK.md
  - [ ] Replace OpenAPI validator with corrected version
  - [ ] Replace accessibility validator with runtime requirements
  - [ ] Document performance validator external execution
  - [ ] Add security validator sandboxing requirements

- [ ] Update EXAMPLES_AND_PATTERNS.md
  - [ ] Fix all API calls to use correct method names
  - [ ] Update thresholds to realistic values
  - [ ] Add imports for centralized data models
  - [ ] Update artifacts to use ArtifactStore
  - [ ] Add handoff examples

- [ ] Create HANDOFF_SPEC.md
  - [ ] Define HandoffSpec data model
  - [ ] Define Task data model
  - [ ] Explain phase boundary transfers
  - [ ] Provide examples

- [ ] Create ARTIFACT_STANDARD.md
  - [ ] Define Artifact data model
  - [ ] Define ArtifactManifest data model
  - [ ] Define ArtifactStore API
  - [ ] Explain content-addressable storage
  - [ ] Provide examples

---

## Validation

After implementing all corrections:

1. **Consistency Check**: Verify all examples can be implemented using documented API
2. **Completeness Check**: Verify all referenced classes are defined
3. **Feasibility Check**: Verify all validators have correct implementations and runtime requirements
4. **Realism Check**: Verify all thresholds are achievable in production environments

---

## References

- GPT5_UNIVERSAL_PROTOCOL_FEEDBACK.md (source of corrections)
- AGENT3_CONTRACT_ENHANCEMENT_RECOMMENDATIONS.md (strategic enhancements for Phase 2)
- DAG_AND_CONTRACT_INTEGRATION_ANALYSIS.md (integration architecture)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-11
**Status**: Ready for implementation
