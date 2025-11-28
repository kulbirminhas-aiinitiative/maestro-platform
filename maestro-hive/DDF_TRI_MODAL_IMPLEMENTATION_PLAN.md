# DDF Tri-Modal Implementation Plan - 3 Independent Parallel Streams

**Document Version**: 1.0
**Date**: 2025-10-12
**Status**: Implementation Roadmap
**Framework**: DDF (Dependency-Driven Framework) with Tri-Modal Convergence

---

## Executive Summary

This plan implements the **Tri-Modal Convergence Framework (DDF)** as **3 independent, parallel development streams** that can:

- ✅ **Develop in parallel** with minimal coordination
- ✅ **Deploy independently** (each stream provides value on its own)
- ✅ **Converge at deployment gate** (all 3 must pass for production)
- ✅ **Evolve at different speeds** (one stream can accelerate without blocking others)

### The Three Independent Streams

1. **STREAM 1: DDE** - Dependency-Driven Execution (Execution Engine)
   - **Goal**: "Built Right" - Parallel execution with compliance
   - **Owner**: Lead Engineer (Execution Track)

2. **STREAM 2: BDV** - Behavior-Driven Validation (Validation Engine)
   - **Goal**: "Built the Right Thing" - Business intent validation
   - **Owner**: Engineer 2 (Validation Track)

3. **STREAM 3: ACC** - Architectural Conformance Checking (Structural Engine)
   - **Goal**: "Built to Last" - Structural integrity
   - **Owner**: Engineer 3 (Architecture Track)

### Deployment Gate

**Deploy to Production ONLY when**: DDE ✅ **AND** BDV ✅ **AND** ACC ✅

Each stream has **non-overlapping blind spots**, ensuring comprehensive validation.

---

## STREAM 1: DDE - Dependency-Driven Execution

**Owner**: Lead Engineer (Execution Track)
**Repository**: `/dde/`
**Database Schema**: `dde_manifests`, `dde_nodes`, `dde_events`, `dde_artifacts`, `dde_audits`
**Files**: `/manifests/execution/{id}.yaml`, `/reports/dde/{id}/`

### Phase 1A: Foundation (Weeks 1-2)

**Goal**: Interface-first execution prevents integration failures

**Tasks**:

1. **Execution Manifest Schema v1.0**
   - File: `schemas/execution_manifest.schema.json`
   - Structure:
     ```yaml
     iteration_id: Iter-YYYYMMDD-HHMM-###
     timestamp: <UTC-ISO8601>
     project: <ProjectName>
     constraints:
       security_standard: OWASP-L2
       library_policy: InternalOnly
       runtime: Python3.11
     policies:
       - id: coverage >= 70%
         severity: BLOCKING
     nodes:
       - id: IF.AuthAPI
         type: interface
         capability: Architecture:APIDesign
         outputs: [openapi.yaml]
         gates: [openapi-lint, semver, breaking-change-check]
         estimated_effort: 60
       - id: FE.Login
         type: impl
         capability: Web:React
         depends_on: [IF.AuthAPI]
         gates: [unit-tests, coverage, contract-tests]
         estimated_effort: 120
     ```

2. **Add NodeType.INTERFACE to dag_workflow.py**
   - Location: `dag_workflow.py:50`
   - Change:
     ```python
     class NodeType(Enum):
         ACTION = "action"
         PHASE = "phase"
         CHECKPOINT = "checkpoint"
         NOTIFICATION = "notification"
         INTERFACE = "interface"  # NEW
     ```

3. **Extend WorkflowNode.config**
   - Location: `dag_workflow.py:NodeConfig`
   - Add fields:
     ```python
     @dataclass
     class NodeConfig:
         # Existing fields...
         capability: Optional[str] = None  # NEW
         gates: List[str] = field(default_factory=list)  # NEW
         estimated_effort: Optional[int] = None  # NEW (minutes)
         contract_version: Optional[str] = None  # NEW
     ```

4. **Interface-First Scheduling**
   - Location: `dag_executor.py`
   - New method:
     ```python
     def get_execution_order_with_interfaces(self) -> List[List[str]]:
         """
         Modified execution order that prioritizes interface nodes.

         Interface nodes execute first to unblock maximum downstream work.
         """
         # 1. Extract interface nodes
         interface_nodes = [
             n.node_id for n in self.workflow.nodes.values()
             if n.node_type == NodeType.INTERFACE
         ]

         # 2. Build execution groups
         groups = []

         # Group 0: Interface nodes (critical path)
         if interface_nodes:
             groups.append(interface_nodes)

         # Remaining groups: Topological sort of non-interface nodes
         non_interface_nodes = [
             n for n in self.workflow.nodes.values()
             if n.node_type != NodeType.INTERFACE
         ]

         remaining_groups = self._topological_sort(non_interface_nodes)
         groups.extend(remaining_groups)

         return groups
     ```

5. **Artifact Stamping Convention**
   - Location: New file `dde/artifact_stamper.py`
   - Convention: `{IterationID}/{NodeID}/{ArtifactName}`
   - Metadata labels: `iteration`, `node`, `capability`, `contractVersion`
   - Implementation:
     ```python
     class ArtifactStamper:
         def stamp_artifact(
             self,
             iteration_id: str,
             node_id: str,
             artifact_path: str,
             capability: str,
             contract_version: Optional[str] = None
         ) -> str:
             """Stamp artifact with metadata and move to canonical location."""
             stamped_path = f"artifacts/{iteration_id}/{node_id}/{Path(artifact_path).name}"

             # Copy artifact
             shutil.copy(artifact_path, stamped_path)

             # Write metadata
             metadata = {
                 "iteration_id": iteration_id,
                 "node_id": node_id,
                 "capability": capability,
                 "contract_version": contract_version,
                 "original_path": artifact_path,
                 "sha256": self._compute_sha256(stamped_path),
                 "timestamp": datetime.utcnow().isoformat()
             }

             with open(f"{stamped_path}.meta.json", "w") as f:
                 json.dump(metadata, f, indent=2)

             return stamped_path
     ```

6. **Add workflow.metadata.iteration_id**
   - Location: `dag_workflow.py:WorkflowDAG`
   - Change:
     ```python
     @dataclass
     class WorkflowDAG:
         workflow_id: str
         nodes: Dict[str, WorkflowNode]
         metadata: Dict[str, Any] = field(default_factory=dict)  # Add iteration_id here
     ```

**Deliverables**:
- ✅ `schemas/execution_manifest.schema.json`
- ✅ Updated `dag_workflow.py` with NodeType.INTERFACE
- ✅ Updated `dag_executor.py` with interface-first scheduling
- ✅ `dde/artifact_stamper.py`
- ✅ 5-10 sample execution manifests

**Success Criteria**:
- Interface nodes execute before dependent nodes (100%)
- Artifacts stamped with correct metadata
- Sample manifest validates against schema

**Independent Value**: Interface-first execution prevents integration failures by locking contracts early

---

### Phase 1B: Capability Routing (Weeks 3-4)

**Goal**: Capability-based routing improves utilization

**Tasks**:

1. **Capability Taxonomy v1.0**
   - File: `config/capability_taxonomy.yaml`
   - Structure:
     ```yaml
     version: "1.0.0"
     taxonomy:
       Web:
         React:
           - Hooks
           - StateManagement
           - Performance
         Vue:
           - Composition
           - Reactivity
       Backend:
         Python:
           - FastAPI
           - AsyncIO
           - ORM
         Node:
           - Express
           - NestJS
       Architecture:
         - APIDesign
         - DatabaseDesign
         - Microservices
       Security:
         - OWASP
         - OAuth2
         - Encryption
       DevOps:
         - Kubernetes
         - Docker
         - CICD
     ```

2. **Capability Registry Database**
   - File: `dde/database/schema.sql`
   - Tables:
     ```sql
     CREATE TABLE agent_profiles (
         agent_id VARCHAR(100) PRIMARY KEY,
         name VARCHAR(255) NOT NULL,
         availability_status VARCHAR(50), -- 'available', 'busy', 'offline'
         wip_limit INT DEFAULT 3,
         recent_quality_score DECIMAL(3,2), -- 0.00 to 1.00
         last_active TIMESTAMP,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );

     CREATE TABLE agent_capabilities (
         id SERIAL PRIMARY KEY,
         agent_id VARCHAR(100) REFERENCES agent_profiles(agent_id),
         skill_id VARCHAR(100) NOT NULL, -- 'Web:React:Hooks'
         proficiency INT CHECK (proficiency BETWEEN 1 AND 5),
         last_used TIMESTAMP,
         certifications TEXT[],
         UNIQUE(agent_id, skill_id)
     );

     CREATE INDEX idx_agent_capabilities_skill ON agent_capabilities(skill_id);
     CREATE INDEX idx_agent_profiles_status ON agent_profiles(availability_status);
     ```

3. **Capability Matcher Implementation**
   - File: `dde/capability_matcher.py`
   - Algorithm:
     ```python
     class CapabilityMatcher:
         def match(
             self,
             required_skills: List[str],
             min_proficiency: int = 3
         ) -> List[Tuple[str, float]]:
             """
             Match agents with required skills.

             Returns list of (agent_id, match_score) tuples, sorted by score.

             Score = (proficiency * 0.4) + (availability * 0.3) +
                     (recent_quality * 0.2) + (low_load * 0.1)
             """
             candidates = []

             for agent in self.get_agents_with_skills(required_skills, min_proficiency):
                 score = self._calculate_match_score(agent, required_skills)
                 candidates.append((agent.agent_id, score))

             return sorted(candidates, key=lambda x: x[1], reverse=True)

         def _calculate_match_score(self, agent, required_skills):
             # Proficiency component (0.4 weight)
             avg_proficiency = self._get_avg_proficiency(agent, required_skills)
             proficiency_score = (avg_proficiency / 5.0) * 0.4

             # Availability component (0.3 weight)
             availability_score = 0.3 if agent.availability_status == 'available' else 0

             # Quality component (0.2 weight)
             quality_score = agent.recent_quality_score * 0.2

             # Load component (0.1 weight)
             load_score = (1 - (agent.current_wip / agent.wip_limit)) * 0.1

             return proficiency_score + availability_score + quality_score + load_score
     ```

4. **JIT Task Assignment**
   - File: `dde/task_router.py`
   - Implementation:
     ```python
     class TaskRouter:
         def __init__(self, matcher: CapabilityMatcher):
             self.matcher = matcher
             self.task_queues = {}  # capability -> queue

         async def assign_task(
             self,
             node_id: str,
             required_capability: str,
             context: Dict[str, Any]
         ) -> str:
             """
             Assign task to best available agent.

             Returns agent_id or raises NoAgentAvailableError.
             """
             # Match capabilities
             candidates = self.matcher.match([required_capability])

             if not candidates:
                 raise NoAgentAvailableError(f"No agent for {required_capability}")

             # Try top 3 candidates
             for agent_id, score in candidates[:3]:
                 if await self._try_assign(agent_id, node_id, context):
                     return agent_id

             # All top candidates busy, queue task
             await self._enqueue_task(required_capability, node_id, context)
             raise TaskQueuedError(f"Task queued for {required_capability}")
     ```

5. **WIP Limit Management**
   - Track active tasks per agent
   - Enforce WIP limits (default: 3)
   - Backpressure when all agents at limit
   - Queue model: per-capability queues with FIFO

**Deliverables**:
- ✅ `config/capability_taxonomy.yaml`
- ✅ `dde/database/schema.sql` (agent profiles + capabilities)
- ✅ `dde/capability_matcher.py`
- ✅ `dde/task_router.py`
- ✅ Migration scripts (Alembic)
- ✅ 12 agent profiles for existing personas

**Success Criteria**:
- Capability matching returns ranked agents within 200ms
- All 12 personas mapped to 10-15 skills
- WIP limits enforced correctly

**Independent Value**: Capability-based routing improves resource utilization by 20-40%

---

### Phase 1C: Policy Enforcement (Weeks 5-6)

**Goal**: Policy compliance automated

**Tasks**:

1. **Gate Classification**
   - File: `config/gate_classification.yaml`
   - Structure:
     ```yaml
     gate_execution_points:
       pre_commit:
         gates: [lint, format]
         severity: WARNING
         optional: true

       pull_request:
         gates:
           - name: unit_tests
             severity: BLOCKING
           - name: coverage
             threshold: 70
             severity: BLOCKING
           - name: sast
             severity: WARNING
         mandatory: true

       node_complete:
         gates:
           - name: contract_tests
             severity: BLOCKING
             applicable_to: [impl, integration]
           - name: openapi_lint
             severity: BLOCKING
             applicable_to: [interface]
     ```

2. **Contract Lockdown Mechanism**
   - File: `dde/contract_lockdown.py`
   - Flow:
     ```python
     async def on_interface_node_complete(
         node_id: str,
         output: Dict[str, Any],
         context: WorkflowContext
     ):
         """
         Called when interface node completes.
         Locks contract and notifies dependent nodes.
         """
         # 1. Extract contract specification
         contract_spec = output.get('contract_spec')  # OpenAPI, GraphQL, etc.

         # 2. Create or evolve contract
         contract = await contract_manager.create_contract(
             team_id=context.global_context['team_id'],
             contract_name=node_id.replace('IF.', ''),
             version=output.get('version', 'v0.1'),
             contract_type=output.get('contract_type', 'REST_API'),
             specification=contract_spec,
             owner_agent=context.get_node_state(node_id).assigned_agent
         )

         # 3. Mark as locked in manifest
         manifest = load_manifest(context.global_context['iteration_id'])
         manifest.mark_contract_locked(node_id, contract.id, contract.version)

         # 4. Publish contract
         contract_path = f"contracts/{contract.contract_name}/{contract.version}/"
         save_contract(contract_path, contract_spec)

         # 5. Emit event
         await event_bus.emit('contract.locked', {
             'contract_id': contract.id,
             'node_id': node_id,
             'version': contract.version,
             'dependents': get_dependent_nodes(node_id)
         })
     ```

3. **Quality Gate Execution Hooks**
   - Integrate with existing PolicyLoader
   - Add pre-execution validation (can node start?)
   - Add post-execution validation (can node complete?)
   - File: `dde/gate_executor.py`

4. **Execution Event Log**
   - Format: JSONL (one JSON object per line)
   - File: `/reports/dde/{iteration_id}/execution.log`
   - Schema:
     ```json
     {
       "iteration_id": "Iter-20251012-1430-001",
       "node_id": "BE.JWT",
       "timestamp": "2025-10-12T14:45:32.123Z",
       "event_type": "node_started",
       "payload": {
         "assigned_agent": "backend_dev_1",
         "capability": "Backend:Python:FastAPI",
         "depends_on_outputs": {...}
       }
     }
     ```

**Deliverables**:
- ✅ `config/gate_classification.yaml`
- ✅ `dde/contract_lockdown.py`
- ✅ `dde/gate_executor.py`
- ✅ Event log writer with JSONL format
- ✅ Integration with PolicyLoader

**Success Criteria**:
- Gates execute at correct points (pre-commit, PR, node-complete)
- Contracts locked after interface nodes
- Event log complete and queryable

**Independent Value**: Policy compliance automated, reducing manual review burden

---

### Phase 1D: Audit & Deployment (Weeks 7-8)

**Goal**: Full DDE audit + deployment gate

**Tasks**:

1. **Manifest vs Execution Log Comparator**
   - File: `dde/audit_comparator.py`
   - Algorithm:
     ```python
     class DDEAuditComparator:
         def compare(self, iteration_id: str) -> DDEAuditResult:
             """
             Compare manifest (planned) vs execution log (as-built).
             """
             manifest = load_manifest(iteration_id)
             execution_log = load_execution_log(iteration_id)

             results = {
                 'nodes_complete': [],
                 'nodes_missing': [],
                 'gates_passed': [],
                 'gates_failed': [],
                 'artifacts_stamped': [],
                 'artifacts_missing': [],
                 'contracts_locked': [],
                 'contracts_missing': []
             }

             # Check each node in manifest
             for node in manifest.nodes:
                 events = execution_log.get_node_events(node.id)

                 if self._is_node_complete(events):
                     results['nodes_complete'].append(node.id)

                     # Check gates
                     for gate in node.gates:
                         if self._gate_passed(events, gate):
                             results['gates_passed'].append((node.id, gate))
                         else:
                             results['gates_failed'].append((node.id, gate))

                     # Check artifacts
                     for artifact in node.outputs:
                         if self._artifact_stamped(events, artifact):
                             results['artifacts_stamped'].append((node.id, artifact))
                         else:
                             results['artifacts_missing'].append((node.id, artifact))
                 else:
                     results['nodes_missing'].append(node.id)

             # Calculate completeness score
             total_nodes = len(manifest.nodes)
             complete_nodes = len(results['nodes_complete'])
             score = complete_nodes / total_nodes if total_nodes > 0 else 0

             return DDEAuditResult(
                 iteration_id=iteration_id,
                 score=score,
                 passed=score == 1.0 and len(results['gates_failed']) == 0,
                 details=results
             )
     ```

2. **Preflight DAG Simulator**
   - File: `dde/preflight_simulator.py`
   - Checks:
     ```python
     class PreflightSimulator:
         def simulate(self, manifest: ExecutionManifest) -> PreflightResult:
             """
             Validate DAG before execution.
             Fail-fast if issues detected.
             """
             issues = []

             # 1. Topological validation (no cycles)
             if self._has_cycles(manifest):
                 issues.append({"severity": "CRITICAL", "message": "Cyclic dependencies detected"})

             # 2. Capability capacity check
             capacity_gaps = self._check_capacity(manifest)
             if capacity_gaps:
                 issues.append({
                     "severity": "HIGH",
                     "message": f"Insufficient capacity for: {capacity_gaps}"
                 })

             # 3. Contract availability check
             missing_contracts = self._check_contracts(manifest)
             if missing_contracts:
                 issues.append({
                     "severity": "MEDIUM",
                     "message": f"Missing contracts: {missing_contracts}"
                 })

             # 4. Critical path analysis
             critical_path = self._calculate_critical_path(manifest)
             if critical_path > 240:  # 4 hours
                 issues.append({
                     "severity": "WARNING",
                     "message": f"Long critical path: {critical_path} minutes"
                 })

             return PreflightResult(
                 passed=len([i for i in issues if i['severity'] in ['CRITICAL', 'HIGH']]) == 0,
                 issues=issues
             )
     ```

3. **DDE Audit Implementation**
   - File: `dde/dde_audit.py`
   - Combines: comparator + preflight + policy validation
   - Stores result in database

4. **Observability Metrics**
   - Prometheus metrics:
     ```python
     # Assign latency
     assign_latency_histogram = Histogram(
         'dde_task_assign_latency_seconds',
         'Time to assign task to agent',
         buckets=[1, 5, 10, 30, 60, 120]
     )

     # Gate pass rate
     gate_pass_rate = Gauge(
         'dde_gate_pass_rate',
         'Percentage of gates passing on first try',
         ['gate_name']
     )

     # Queue depth
     queue_depth = Gauge(
         'dde_queue_depth',
         'Number of tasks waiting',
         ['capability']
     )
     ```

**Deliverables**:
- ✅ `dde/audit_comparator.py`
- ✅ `dde/preflight_simulator.py`
- ✅ `dde/dde_audit.py`
- ✅ Prometheus metrics exporter
- ✅ Grafana dashboard (DDE metrics)

**Success Criteria**:
- Audit detects all missing nodes, artifacts, gates
- Preflight catches topology/capacity issues
- Metrics exported to Prometheus

**Independent Value**: Full DDE audit enables compliance and traceability

---

### DDE API Endpoints

```python
# dde/api.py
from fastapi import APIRouter

router = APIRouter(prefix="/v1/dde")

@router.post("/manifest")
async def create_manifest(manifest: ExecutionManifest):
    """Create new execution manifest"""
    pass

@router.get("/manifest/{id}")
async def get_manifest(id: str):
    """Retrieve execution manifest"""
    pass

@router.post("/execute/{id}")
async def execute_iteration(id: str):
    """Execute iteration with DDE"""
    pass

@router.get("/status/{id}")
async def get_status(id: str):
    """Get execution status"""
    pass

@router.post("/audit/{id}")
async def run_audit(id: str):
    """Run DDE audit"""
    pass

@router.get("/audit/{id}/report")
async def get_audit_report(id: str):
    """Get DDE audit report"""
    pass

@router.get("/capabilities/agents")
async def list_agents():
    """List all agents with capabilities"""
    pass

@router.post("/capabilities/match")
async def match_capabilities(skills: List[str]):
    """Match agents to required skills"""
    pass
```

---

### DDE Deployment Gate

```python
# dde/deployment_gate.py

def can_deploy_dde(iteration_id: str) -> bool:
    """
    DDE deployment gate.

    Returns True if iteration meets DDE criteria for deployment.
    """
    audit = dde_audit(iteration_id)

    return (
        audit.all_nodes_complete and
        audit.blocking_gates_passed and
        audit.artifacts_stamped and
        audit.lineage_intact and
        audit.contracts_locked
    )
```

---

## STREAM 2: BDV - Behavior-Driven Validation

**Owner**: Engineer 2 (Validation Track)
**Repository**: `/bdv/`
**Database Schema**: `bdv_manifests`, `bdv_scenarios`, `bdv_results`, `bdv_audits`
**Files**: `/manifests/behavioral/{id}.feature`, `/reports/bdv/{id}/`

### Phase 2A: Foundation (Weeks 1-2)

**Goal**: Core user journeys validated against build

**Tasks**:

1. **Behavioral Manifest Structure (Gherkin)**
   - Directory: `features/{domain}/{feature}.feature`
   - Example:
     ```gherkin
     # features/auth/authentication.feature
     @contract:AuthAPI:v1.2
     Feature: User Authentication
       As a registered user
       I want to authenticate with email and password
       So that I can access protected resources

       Background:
         Given the system has registered users
         And the AuthAPI v1.2 contract is available

       Scenario: Successful login with valid credentials
         Given a registered user "alice@example.com" with password "p@ss123"
         When she requests a token via POST /auth/token with:
           | email    | password |
           | alice@example.com | p@ss123  |
         Then the response status is 200
         And the response body contains a JWT token
         And the token has claim "sub=alice@example.com"
         And the token is valid for 3600 seconds

       Scenario: Failed login with invalid password
         Given a registered user "alice@example.com" with password "p@ss123"
         When she requests a token via POST /auth/token with:
           | email    | password |
           | alice@example.com | wrong_password |
         Then the response status is 401
         And the response body contains error "Invalid credentials"

       Scenario: Token refresh for expired token
         Given a user "alice@example.com" with an expired token
         When she requests a new token via POST /auth/refresh with the expired token
         Then the response status is 200
         And a new JWT token is returned
     ```

2. **BDV Runner Implementation (pytest-bdd)**
   - File: `bdv/bdv_runner.py`
   - Discovery: Finds all .feature files
   - Execution: Runs against base URL
   - Reporting: JSON output
   - Implementation:
     ```python
     class BDVRunner:
         def __init__(self, base_url: str):
             self.base_url = base_url
             self.results = []

         def discover_features(self, path: str = "features/") -> List[str]:
             """Find all .feature files"""
             return list(Path(path).rglob("*.feature"))

         def run(self, feature_files: List[str]) -> BDVResult:
             """Run all scenarios and collect results"""
             pytest_args = [
                 "--tb=short",
                 "--json-report",
                 f"--json-report-file=bdv_report.json",
                 "--base-url", self.base_url
             ]
             pytest_args.extend(feature_files)

             exit_code = pytest.main(pytest_args)

             # Parse results
             with open("bdv_report.json") as f:
                 report = json.load(f)

             return BDVResult(
                 total_scenarios=report['summary']['total'],
                 passed=report['summary']['passed'],
                 failed=report['summary']['failed'],
                 skipped=report['summary']['skipped'],
                 duration=report['duration'],
                 details=report['tests']
             )
     ```

3. **Step Definitions**
   - File: `bdv/steps/auth_steps.py`
   - Example:
     ```python
     from pytest_bdd import given, when, then, parsers

     @given(parsers.parse('a registered user "{email}" with password "{password}"'))
     def registered_user(context, email, password):
         context.user = {"email": email, "password": password}
         # Register user via API
         requests.post(f"{context.base_url}/auth/register", json=context.user)

     @when(parsers.parse('she requests a token via POST {endpoint} with:'))
     def request_token(context, endpoint, datatable):
         data = {row['email']: row['password'] for row in datatable}
         context.response = requests.post(
             f"{context.base_url}{endpoint}",
             json=data
         )

     @then(parsers.parse('the response status is {status:d}'))
     def check_status(context, status):
         assert context.response.status_code == status

     @then('the response body contains a JWT token')
     def check_jwt_token(context):
         data = context.response.json()
         assert 'token' in data
         assert jwt.decode(data['token'], verify=False)  # Basic validation
     ```

4. **Initial Scenario Coverage**
   - Identify top 5-10 user journeys
   - Write scenarios for each
   - Focus on happy path first

**Deliverables**:
- ✅ `features/` directory with 5-10 .feature files
- ✅ `bdv/bdv_runner.py`
- ✅ `bdv/steps/` with step definitions
- ✅ `pytest.ini` configuration
- ✅ Sample BDV report (JSON)

**Success Criteria**:
- 5-10 core scenarios run successfully
- Runner produces JSON report
- Scenarios pass against integrated build

**Independent Value**: Core user journeys validated, catching behavior drift early

---

### Phase 2B: Contract Integration (Weeks 3-4)

**Goal**: Contract-scenario alignment prevents drift

**Tasks**:

1. **Contract Reference in Gherkin Tags**
   - Convention: `@contract:ContractName:Version`
   - Example:
     ```gherkin
     @contract:AuthAPI:v1.2
     Feature: Authentication
     ```

2. **Contract Version Validation**
   - File: `bdv/contract_validator.py`
   - Logic:
     ```python
     def validate_contract_versions(feature_file: str, base_url: str):
         """
         Ensure scenarios reference correct contract versions.
         """
         # Parse contract tag from feature file
         with open(feature_file) as f:
             content = f.read()
             match = re.search(r'@contract:(\w+):v([\d.]+)', content)
             if match:
                 contract_name, version = match.groups()

                 # Check deployed version
                 deployed_version = get_deployed_contract_version(base_url, contract_name)

                 if deployed_version != f"v{version}":
                     raise ContractVersionMismatchError(
                         f"Feature expects {contract_name}:v{version} "
                         f"but deployed version is {deployed_version}"
                     )
     ```

3. **OpenAPI to Gherkin Generator**
   - File: `bdv/generators/openapi_to_gherkin.py`
   - Generate scenarios from OpenAPI examples
   - Algorithm:
     ```python
     def generate_scenarios(openapi_spec: Dict) -> str:
         """
         Generate Gherkin scenarios from OpenAPI spec.
         Uses examples in spec to create Given/When/Then.
         """
         scenarios = []

         for path, methods in openapi_spec['paths'].items():
             for method, details in methods.items():
                 if 'examples' in details.get('requestBody', {}):
                     scenario = self._create_scenario(path, method, details)
                     scenarios.append(scenario)

         return "\n\n".join(scenarios)

     def _create_scenario(self, path, method, details):
         example = details['requestBody']['examples']['default']['value']

         return f"""
         Scenario: {details['summary']}
           When I {method.upper()} to {path} with:
             | field | value |
             {self._format_example(example)}
           Then the response status is {details['responses']['200']['description']}
         """
     ```

**Deliverables**:
- ✅ Contract tags added to all features
- ✅ `bdv/contract_validator.py`
- ✅ `bdv/generators/openapi_to_gherkin.py`
- ✅ 10+ auto-generated scenarios

**Success Criteria**:
- Contract version validation catches mismatches
- Auto-generated scenarios pass
- Coverage increased by 50%

**Independent Value**: Contract-scenario alignment prevents drift between spec and behavior

---

### Phase 2C: Flake Management (Weeks 5-6)

**Goal**: Flaky test quarantine improves signal

**Tasks**:

1. **Quarantine List**
   - File: `config/bdv_quarantine.yaml`
   - Structure:
     ```yaml
     quarantined_scenarios:
       - id: auth/authentication.feature::Scenario: Token refresh for expired token
         reason: Intermittent timing issue with token expiry
         quarantined_at: 2025-10-12
         quarantined_by: engineer-2
         jira_ticket: ENG-1234
         review_date: 2025-11-12

       - id: payment/checkout.feature::Scenario: Process payment with retry
         reason: External payment gateway flaky
         quarantined_at: 2025-10-11
         quarantined_by: engineer-2
         jira_ticket: ENG-1235
         review_date: 2025-11-11
     ```

2. **Auto-Ratchet (Require 2 Green Runs)**
   - File: `bdv/flake_detector.py`
   - Logic:
     ```python
     class FlakeDetector:
         def require_consecutive_passes(self, scenario_id: str, result: bool):
             """
             Track scenario results. Mark as passed only after 2 consecutive greens.
             """
             history = self.get_history(scenario_id)
             history.append(result)

             if len(history) >= 2 and history[-2:] == [True, True]:
                 return True  # Passed
             elif not result:
                 return False  # Failed
             else:
                 return None  # Need one more run
     ```

3. **Flake Rate Tracking**
   - Metric: `flake_rate = flaky_scenarios / total_scenarios`
   - Prometheus metric:
     ```python
     flake_rate = Gauge(
         'bdv_flake_rate',
         'Percentage of flaky scenarios',
         ['feature']
     )
     ```

4. **Fail if Flake Rate > Threshold**
   - Threshold: 10%
   - Enforcement: BDV audit fails if flake_rate > 0.10

**Deliverables**:
- ✅ `config/bdv_quarantine.yaml`
- ✅ `bdv/flake_detector.py`
- ✅ Flake rate metrics
- ✅ Threshold enforcement

**Success Criteria**:
- Quarantined scenarios excluded from audit
- Flake rate tracked and reported
- Audit fails if flake_rate > 10%

**Independent Value**: Flake management improves signal-to-noise ratio in BDV results

---

### Phase 2D: Coverage Expansion (Weeks 7-8)

**Goal**: Comprehensive behavioral validation

**Tasks**:

1. **Expand to 20 User Journeys**
   - Identify top 20 user journeys
   - Write scenarios for each
   - Focus on critical paths

2. **Contract-Driven Test Generation**
   - Automate scenario generation from OpenAPI
   - Generate 50+ scenarios
   - Human review and enhancement

3. **BDV Audit Implementation**
   - File: `bdv/bdv_audit.py`
   - Logic:
     ```python
     def bdv_audit(iteration_id: str) -> BDVAuditResult:
         """
         BDV deployment gate audit.
         """
         # Run all scenarios
         result = bdv_runner.run_all()

         # Check flake rate
         flake_rate = flake_detector.get_flake_rate()

         # Check contract versions
         contract_mismatches = contract_validator.validate_all()

         # Check coverage
         coverage = calculate_coverage()

         return BDVAuditResult(
             iteration_id=iteration_id,
             passed=result.failed == 0 and flake_rate < 0.10 and not contract_mismatches,
             total_scenarios=result.total_scenarios,
             passed_scenarios=result.passed,
             failed_scenarios=result.failed,
             flake_rate=flake_rate,
             contract_mismatches=contract_mismatches,
             coverage=coverage
         )
     ```

4. **Coverage Tracking**
   - Track which API endpoints covered
   - Track which user journeys covered
   - Report gaps

**Deliverables**:
- ✅ 20 user journeys with scenarios
- ✅ 50+ auto-generated scenarios
- ✅ `bdv/bdv_audit.py`
- ✅ Coverage tracker

**Success Criteria**:
- 20 user journeys covered
- 50+ scenarios passing
- Coverage >70% of critical APIs

**Independent Value**: Comprehensive behavioral validation catches regressions

---

### BDV API Endpoints

```python
# bdv/api.py
from fastapi import APIRouter

router = APIRouter(prefix="/v1/bdv")

@router.post("/manifest")
async def create_manifest(features: List[str]):
    """Create behavioral manifest"""
    pass

@router.get("/manifest/{id}")
async def get_manifest(id: str):
    """Get behavioral manifest"""
    pass

@router.post("/run/{id}")
async def run_tests(id: str, base_url: str):
    """Run BDV tests"""
    pass

@router.get("/results/{id}")
async def get_results(id: str):
    """Get test results"""
    pass

@router.post("/audit/{id}")
async def run_audit(id: str):
    """Run BDV audit"""
    pass

@router.get("/audit/{id}/report")
async def get_audit_report(id: str):
    """Get BDV audit report"""
    pass

@router.get("/coverage/{id}")
async def get_coverage(id: str):
    """Get coverage metrics"""
    pass
```

---

### BDV Deployment Gate

```python
# bdv/deployment_gate.py

def can_deploy_bdv(iteration_id: str) -> bool:
    """
    BDV deployment gate.

    Returns True if iteration meets BDV criteria for deployment.
    """
    audit = bdv_audit(iteration_id)

    return (
        audit.all_scenarios_passed and
        audit.flake_rate < 0.10 and
        not audit.contract_mismatches and
        audit.critical_journeys_covered
    )
```

---

## STREAM 3: ACC - Architectural Conformance Checking

**Owner**: Engineer 3 (Architecture Track)
**Repository**: `/acc/`
**Database Schema**: `acc_manifests`, `acc_rules`, `acc_violations`, `acc_audits`
**Files**: `/manifests/architectural/{id}.yaml`, `/reports/acc/{id}/`

### Phase 3A: Foundation (Weeks 1-2)

**Goal**: Basic layering rules prevent architecture violations

**Tasks**:

1. **Architectural Manifest Schema**
   - File: `schemas/architectural_manifest.schema.json`
   - Structure:
     ```yaml
     # manifests/architectural/dog-marketplace.yaml
     project: DogMarketplace
     version: "1.0.0"

     components:
       - name: Presentation
         paths: [frontend/src/components/, frontend/src/pages/]

       - name: BusinessLogic
         paths: [backend/src/services/, backend/src/domain/]

       - name: DataAccess
         paths: [backend/src/repositories/, backend/src/models/]

       - name: Infrastructure
         paths: [backend/src/infrastructure/, backend/src/config/]

     rules:
       - id: R1
         type: dependency
         description: Presentation can only call BusinessLogic
         rule: Presentation: CAN_CALL(BusinessLogic)
         severity: BLOCKING

       - id: R2
         type: dependency
         description: BusinessLogic can only call DataAccess and Infrastructure
         rule: BusinessLogic: CAN_CALL(DataAccess, Infrastructure)
         severity: BLOCKING

       - id: R3
         type: dependency
         description: Presentation must not call DataAccess directly
         rule: Presentation: MUST_NOT_CALL(DataAccess)
         severity: BLOCKING

       - id: R4
         type: dependency
         description: DataAccess must not call Presentation or BusinessLogic
         rule: DataAccess: MUST_NOT_CALL(Presentation, BusinessLogic)
         severity: BLOCKING

       - id: R5
         type: coupling
         description: BusinessLogic coupling must be low
         rule: BusinessLogic: COUPLING < 10
         severity: WARNING

     tech:
       language: python
       analyzers: [import_graph, ast]
     ```

2. **Import Graph Builder (Python)**
   - File: `acc/import_graph_builder.py`
   - Algorithm:
     ```python
     class ImportGraphBuilder:
         def build_graph(self, project_path: str) -> ImportGraph:
             """
             Build import graph from Python files.
             Uses AST to parse imports.
             """
             graph = ImportGraph()

             for py_file in Path(project_path).rglob("*.py"):
                 module_name = self._get_module_name(py_file, project_path)
                 imports = self._extract_imports(py_file)

                 for imported_module in imports:
                     graph.add_edge(module_name, imported_module)

             return graph

         def _extract_imports(self, py_file: Path) -> List[str]:
             """Parse imports using AST"""
             with open(py_file) as f:
                 tree = ast.parse(f.read())

             imports = []
             for node in ast.walk(tree):
                 if isinstance(node, ast.Import):
                     for alias in node.names:
                         imports.append(alias.name)
                 elif isinstance(node, ast.ImportFrom):
                     if node.module:
                         imports.append(node.module)

             return imports
     ```

3. **Rule Engine Implementation**
   - File: `acc/rule_engine.py`
   - Supported rule types:
     - `CAN_CALL(Target1, Target2, ...)` - Allow dependencies
     - `MUST_NOT_CALL(Target1, Target2, ...)` - Forbid dependencies
     - `COUPLING < N` - Enforce coupling limit
     - `NO_CYCLES` - Forbid cyclic dependencies
   - Algorithm:
     ```python
     class RuleEngine:
         def evaluate_rule(
             self,
             rule: ArchRule,
             graph: ImportGraph,
             manifest: ArchManifest
         ) -> RuleEvaluationResult:
             """
             Evaluate architectural rule against import graph.
             """
             violations = []

             if rule.type == 'dependency':
                 violations = self._check_dependency_rule(rule, graph, manifest)
             elif rule.type == 'coupling':
                 violations = self._check_coupling_rule(rule, graph, manifest)
             elif rule.type == 'cycles':
                 violations = self._check_cycles(graph, manifest)

             return RuleEvaluationResult(
                 rule_id=rule.id,
                 passed=len(violations) == 0,
                 severity=rule.severity,
                 violations=violations
             )

         def _check_dependency_rule(self, rule, graph, manifest):
             violations = []

             source_component = rule.source  # e.g., "Presentation"
             source_modules = manifest.get_modules_in_component(source_component)

             if 'CAN_CALL' in rule.rule:
                 allowed_targets = self._parse_can_call(rule.rule)
                 allowed_modules = set()
                 for target in allowed_targets:
                     allowed_modules.update(manifest.get_modules_in_component(target))

                 # Check all outgoing edges from source modules
                 for source_module in source_modules:
                     for target_module in graph.get_dependencies(source_module):
                         if target_module not in allowed_modules:
                             violations.append({
                                 "source": source_module,
                                 "target": target_module,
                                 "message": f"{source_module} cannot call {target_module}"
                             })

             elif 'MUST_NOT_CALL' in rule.rule:
                 forbidden_targets = self._parse_must_not_call(rule.rule)
                 forbidden_modules = set()
                 for target in forbidden_targets:
                     forbidden_modules.update(manifest.get_modules_in_component(target))

                 # Check for forbidden dependencies
                 for source_module in source_modules:
                     for target_module in graph.get_dependencies(source_module):
                         if target_module in forbidden_modules:
                             violations.append({
                                 "source": source_module,
                                 "target": target_module,
                                 "message": f"{source_module} must not call {target_module}"
                             })

             return violations
     ```

4. **ACC Checker CLI**
   - File: `acc/acc_check.py`
   - Usage: `python acc_check.py --manifest dog-marketplace.yaml --project-path ./`
   - Output: JSON report with violations

**Deliverables**:
- ✅ `schemas/architectural_manifest.schema.json`
- ✅ Sample architectural manifest
- ✅ `acc/import_graph_builder.py`
- ✅ `acc/rule_engine.py`
- ✅ `acc/acc_check.py` CLI

**Success Criteria**:
- Import graph built correctly
- 3-5 basic rules evaluated
- Violations detected and reported

**Independent Value**: Basic layering rules prevent common architecture violations

---

### Phase 3B: Rule Engine (Weeks 3-4)

**Goal**: Comprehensive rules with pragmatic enforcement

**Tasks**:

1. **Rule Type Expansion**
   - Dependency rules (CAN_CALL, MUST_NOT_CALL)
   - Layering rules (enforce layer hierarchy)
   - Coupling rules (afferent/efferent coupling limits)
   - Naming rules (enforce naming conventions)
   - Size rules (module/class size limits)

2. **Severity Levels**
   - BLOCKING: Must fix before merge
   - WARNING: Should fix, but not blocking
   - INFO: Informational only

3. **Suppression System**
   - File: `acc/suppression_manager.py`
   - Format:
     ```yaml
     # config/acc_suppressions.yaml
     suppressions:
       - rule_id: R3
         violation: "frontend/src/components/UserList.tsx calls backend/src/models/User.py"
         reason: "Legacy code, will refactor in Q2"
         adr: ADR-2025-001
         expires: 2025-12-31
         approved_by: tech-lead
     ```
   - Logic:
     ```python
     class SuppressionManager:
         def is_suppressed(self, violation: Violation) -> bool:
             """Check if violation is suppressed"""
             suppressions = self.load_suppressions()

             for suppression in suppressions:
                 if self._matches(suppression, violation):
                     if self._is_expired(suppression):
                         raise SuppressionExpiredError(
                             f"Suppression for {violation} expired on {suppression.expires}"
                         )
                     if not suppression.adr:
                         raise MissingADRError(
                             f"Suppression for {violation} missing ADR"
                         )
                     return True

             return False
     ```

4. **Rule Validation**
   - Validate rule syntax before execution
   - Provide helpful error messages
   - Suggest fixes for common mistakes

**Deliverables**:
- ✅ 10+ rule types implemented
- ✅ Severity system working
- ✅ `acc/suppression_manager.py`
- ✅ `config/acc_suppressions.yaml` template

**Success Criteria**:
- 10 rule types working
- Suppressions enforced with ADR requirement
- Expired suppressions cause failures

**Independent Value**: Comprehensive rules with pragmatic enforcement balance rigor and flexibility

---

### Phase 3C: Analysis Expansion (Weeks 5-6)

**Goal**: Comprehensive static analysis catches hidden issues

**Tasks**:

1. **Cyclic Dependency Detection**
   - Algorithm: Tarjan's strongly connected components
   - Report all cycles
   - Severity: BLOCKING (cycles must be broken)

2. **Coupling Metrics**
   - Afferent coupling (Ca): Number of incoming dependencies
   - Efferent coupling (Ce): Number of outgoing dependencies
   - Instability (I): Ce / (Ca + Ce)
   - Rules:
     - BusinessLogic: I < 0.5 (stable)
     - Utilities: I < 0.3 (very stable)

3. **Complexity Metrics**
   - Cyclomatic complexity per function
   - Lines of code per module
   - Nesting depth
   - Rules:
     - Cyclomatic complexity < 10
     - Module size < 500 lines
     - Nesting depth < 4

4. **Dead Code Detection**
   - Find unused imports
   - Find unused functions/classes
   - Report as INFO (not blocking)

**Deliverables**:
- ✅ Cyclic dependency detector
- ✅ Coupling analyzer
- ✅ Complexity analyzer
- ✅ Dead code detector

**Success Criteria**:
- All cycles detected
- Coupling metrics accurate
- Complexity metrics per module

**Independent Value**: Comprehensive static analysis catches architectural debt before it compounds

---

### Phase 3D: Evolution Tracking (Weeks 7-8)

**Goal**: Evolution tracking shows architectural health trends

**Tasks**:

1. **Architecture Diff**
   - File: `acc/architecture_diff.py`
   - Compare current vs previous iteration
   - Report:
     - New violations introduced
     - Violations fixed
     - Coupling changes
     - New cyclic dependencies

2. **Visual Dependency Graph**
   - Generate graph visualization (Graphviz)
   - Highlight violations in red
   - Show component boundaries
   - Export to SVG/PNG

3. **Erosion Detection**
   - Track violations over time
   - Alert if violations increasing
   - Metric: `erosion_rate = new_violations / time`

4. **ACC Audit Implementation**
   - File: `acc/acc_audit.py`
   - Logic:
     ```python
     def acc_audit(iteration_id: str) -> ACCAuditResult:
         """
         ACC deployment gate audit.
         """
         # Load manifest
         manifest = load_architectural_manifest(iteration_id)

         # Build import graph
         graph = import_graph_builder.build_graph(manifest.project_path)

         # Evaluate all rules
         results = []
         for rule in manifest.rules:
             result = rule_engine.evaluate_rule(rule, graph, manifest)
             results.append(result)

         # Check suppressions
         unsuppressed_violations = []
         for result in results:
             for violation in result.violations:
                 if not suppression_manager.is_suppressed(violation):
                     unsuppressed_violations.append(violation)

         # Calculate metrics
         coupling_scores = coupling_analyzer.analyze(graph, manifest)
         cycles = cycle_detector.find_cycles(graph)

         return ACCAuditResult(
             iteration_id=iteration_id,
             passed=len(unsuppressed_violations) == 0 and len(cycles) == 0,
             blocking_violations=len([v for v in unsuppressed_violations if v.severity == 'BLOCKING']),
             warning_violations=len([v for v in unsuppressed_violations if v.severity == 'WARNING']),
             cycles=cycles,
             coupling_scores=coupling_scores
         )
     ```

**Deliverables**:
- ✅ `acc/architecture_diff.py`
- ✅ Visual dependency graph generator
- ✅ Erosion detector
- ✅ `acc/acc_audit.py`

**Success Criteria**:
- Diffs show architectural changes
- Graphs visualize violations
- Erosion tracked over time
- Audit passes/fails correctly

**Independent Value**: Evolution tracking provides visibility into architectural health

---

### ACC API Endpoints

```python
# acc/api.py
from fastapi import APIRouter

router = APIRouter(prefix="/v1/acc")

@router.post("/manifest")
async def create_manifest(manifest: ArchManifest):
    """Create architectural manifest"""
    pass

@router.get("/manifest/{id}")
async def get_manifest(id: str):
    """Get architectural manifest"""
    pass

@router.post("/check/{id}")
async def run_check(id: str):
    """Run ACC check"""
    pass

@router.get("/results/{id}")
async def get_results(id: str):
    """Get check results"""
    pass

@router.post("/audit/{id}")
async def run_audit(id: str):
    """Run ACC audit"""
    pass

@router.get("/audit/{id}/report")
async def get_audit_report(id: str):
    """Get ACC audit report"""
    pass

@router.get("/evolution/{id}")
async def get_evolution(id: str):
    """Get architecture diffs"""
    pass
```

---

### ACC Deployment Gate

```python
# acc/deployment_gate.py

def can_deploy_acc(iteration_id: str) -> bool:
    """
    ACC deployment gate.

    Returns True if iteration meets ACC criteria for deployment.
    """
    audit = acc_audit(iteration_id)

    return (
        audit.blocking_violations == 0 and
        audit.suppressions_have_adrs and
        audit.coupling_within_limits and
        audit.no_new_cycles
    )
```

---

## CONVERGENCE LAYER: Tri-Modal Audit

**Owner**: All 3 engineers (collaborative)
**Goal**: Aggregate verdicts from all 3 streams
**Repository**: `/tri_audit/`
**Database Schema**: `tri_audits`
**Files**: `/reports/tri-modal/{id}/`

### Implementation (Weeks 7-8)

**File**: `tri_audit/tri_audit.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any

class TriModalVerdict(Enum):
    ALL_PASS = "all_pass"
    DESIGN_GAP = "design_gap"
    ARCHITECTURAL_EROSION = "architectural_erosion"
    PROCESS_ISSUE = "process_issue"
    SYSTEMIC_FAILURE = "systemic_failure"
    MIXED_FAILURE = "mixed_failure"

@dataclass
class TriAuditResult:
    iteration_id: str
    verdict: TriModalVerdict
    dde_passed: bool
    bdv_passed: bool
    acc_passed: bool
    can_deploy: bool
    diagnosis: str
    recommendations: List[str]
    dde_details: Dict[str, Any]
    bdv_details: Dict[str, Any]
    acc_details: Dict[str, Any]

def tri_modal_audit(iteration_id: str) -> TriAuditResult:
    """
    Run tri-modal convergence audit.

    Aggregates verdicts from DDE, BDV, and ACC.
    Deploy ONLY if all three pass.
    """
    # Run individual audits
    dde_audit_result = dde_audit(iteration_id)
    bdv_audit_result = bdv_audit(iteration_id)
    acc_audit_result = acc_audit(iteration_id)

    # Extract pass/fail
    dde_pass = dde_audit_result.passed
    bdv_pass = bdv_audit_result.passed
    acc_pass = acc_audit_result.passed

    # Determine verdict
    verdict = determine_verdict(dde_pass, bdv_pass, acc_pass)

    # Generate diagnosis
    diagnosis = diagnose_failure(verdict, dde_pass, bdv_pass, acc_pass)

    # Generate recommendations
    recommendations = generate_recommendations(
        verdict,
        dde_audit_result,
        bdv_audit_result,
        acc_audit_result
    )

    return TriAuditResult(
        iteration_id=iteration_id,
        verdict=verdict,
        dde_passed=dde_pass,
        bdv_passed=bdv_pass,
        acc_passed=acc_pass,
        can_deploy=verdict == TriModalVerdict.ALL_PASS,
        diagnosis=diagnosis,
        recommendations=recommendations,
        dde_details=dde_audit_result.to_dict(),
        bdv_details=bdv_audit_result.to_dict(),
        acc_details=acc_audit_result.to_dict()
    )

def determine_verdict(dde: bool, bdv: bool, acc: bool) -> TriModalVerdict:
    """
    Determine tri-modal verdict from individual results.
    """
    if dde and bdv and acc:
        return TriModalVerdict.ALL_PASS
    elif dde and not bdv and acc:
        return TriModalVerdict.DESIGN_GAP
    elif dde and bdv and not acc:
        return TriModalVerdict.ARCHITECTURAL_EROSION
    elif not dde and bdv and acc:
        return TriModalVerdict.PROCESS_ISSUE
    elif not dde and not bdv and not acc:
        return TriModalVerdict.SYSTEMIC_FAILURE
    else:
        return TriModalVerdict.MIXED_FAILURE

def diagnose_failure(
    verdict: TriModalVerdict,
    dde: bool,
    bdv: bool,
    acc: bool
) -> str:
    """
    Generate human-readable diagnosis.
    """
    diagnoses = {
        TriModalVerdict.ALL_PASS: "All audits passed. Safe to deploy.",

        TriModalVerdict.DESIGN_GAP: (
            "DDE and ACC passed, but BDV failed. "
            "This indicates a gap between implementation and business intent. "
            "Action: Revisit requirements and contracts. "
            "The system is technically correct but doesn't meet user needs."
        ),

        TriModalVerdict.ARCHITECTURAL_EROSION: (
            "DDE and BDV passed, but ACC failed. "
            "This indicates architectural violations despite functional correctness. "
            "Action: Refactor to fix architectural issues before deploy. "
            "Do not accept technical debt."
        ),

        TriModalVerdict.PROCESS_ISSUE: (
            "BDV and ACC passed, but DDE failed. "
            "This indicates process or pipeline issues. "
            "Action: Tune quality gates or fix pipeline configuration."
        ),

        TriModalVerdict.SYSTEMIC_FAILURE: (
            "All three audits failed. "
            "This indicates systemic issues. "
            "Action: HALT. Conduct retrospective. Reduce scope."
        ),

        TriModalVerdict.MIXED_FAILURE: (
            f"Mixed failure: DDE={dde}, BDV={bdv}, ACC={acc}. "
            "Multiple issues detected. Review each audit report."
        )
    }

    return diagnoses[verdict]

def generate_recommendations(
    verdict: TriModalVerdict,
    dde_result: DDEAuditResult,
    bdv_result: BDVAuditResult,
    acc_result: ACCAuditResult
) -> List[str]:
    """
    Generate actionable recommendations based on failures.
    """
    recommendations = []

    if not dde_result.passed:
        if dde_result.details['nodes_missing']:
            recommendations.append(
                f"Complete missing DDE nodes: {', '.join(dde_result.details['nodes_missing'])}"
            )
        if dde_result.details['gates_failed']:
            recommendations.append(
                f"Fix failed quality gates: {', '.join([g[1] for g in dde_result.details['gates_failed']])}"
            )

    if not bdv_result.passed:
        if bdv_result.failed_scenarios > 0:
            recommendations.append(
                f"Fix {bdv_result.failed_scenarios} failing BDV scenarios"
            )
        if bdv_result.flake_rate > 0.10:
            recommendations.append(
                f"Reduce flake rate from {bdv_result.flake_rate:.2%} to <10%"
            )
        if bdv_result.contract_mismatches:
            recommendations.append(
                "Update scenarios to match deployed contract versions"
            )

    if not acc_result.passed:
        if acc_result.blocking_violations > 0:
            recommendations.append(
                f"Fix {acc_result.blocking_violations} blocking architectural violations"
            )
        if acc_result.cycles:
            recommendations.append(
                f"Break {len(acc_result.cycles)} cyclic dependencies"
            )

    return recommendations
```

### Convergence API

```python
# tri_audit/api.py
from fastapi import APIRouter

router = APIRouter(prefix="/v1/audit/tri-modal")

@router.post("/{iteration_id}")
async def run_tri_audit(iteration_id: str):
    """Run tri-modal convergence audit"""
    result = tri_modal_audit(iteration_id)

    # Store result
    await store_tri_audit_result(result)

    return result

@router.get("/{iteration_id}/report")
async def get_tri_audit_report(iteration_id: str):
    """Get tri-modal audit report"""
    result = load_tri_audit_result(iteration_id)

    return {
        "iteration_id": result.iteration_id,
        "verdict": result.verdict.value,
        "can_deploy": result.can_deploy,
        "diagnosis": result.diagnosis,
        "recommendations": result.recommendations,
        "audits": {
            "dde": {"passed": result.dde_passed, "details": result.dde_details},
            "bdv": {"passed": result.bdv_passed, "details": result.bdv_details},
            "acc": {"passed": result.acc_passed, "details": result.acc_details}
        }
    }

@router.get("/{iteration_id}/diagnosis")
async def get_failure_diagnosis(iteration_id: str):
    """Get failure diagnosis matrix"""
    result = load_tri_audit_result(iteration_id)

    return {
        "verdict": result.verdict.value,
        "diagnosis": result.diagnosis,
        "recommendations": result.recommendations
    }
```

### Deployment Gate (Final)

```python
# deployment_gate.py

def can_deploy_to_production(iteration_id: str) -> bool:
    """
    FINAL DEPLOYMENT GATE.

    Deploy to production ONLY if all three audits pass.
    """
    result = tri_modal_audit(iteration_id)

    return result.can_deploy
```

---

## DATA ISOLATION (3 Independent Databases)

### Stream 1 (DDE) Database Schema

```sql
-- DDE database tables
CREATE TABLE dde_manifests (
    id VARCHAR(100) PRIMARY KEY,
    iteration_id VARCHAR(100) UNIQUE NOT NULL,
    project VARCHAR(255),
    constraints JSONB,
    policies JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dde_nodes (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES dde_manifests(iteration_id),
    node_id VARCHAR(100) NOT NULL,
    node_type VARCHAR(50),
    capability VARCHAR(100),
    depends_on VARCHAR(100)[],
    gates VARCHAR(100)[],
    estimated_effort INT,
    contract_version VARCHAR(50),
    status VARCHAR(50),
    assigned_agent VARCHAR(100),
    UNIQUE(iteration_id, node_id)
);

CREATE TABLE dde_events (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES dde_manifests(iteration_id),
    node_id VARCHAR(100),
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB
);

CREATE TABLE dde_artifacts (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES dde_manifests(iteration_id),
    node_id VARCHAR(100),
    path VARCHAR(500),
    sha256 VARCHAR(64),
    labels JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dde_audits (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES dde_manifests(iteration_id),
    audit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    passed BOOLEAN,
    score DECIMAL(3,2),
    details JSONB
);

CREATE INDEX idx_dde_events_iteration ON dde_events(iteration_id);
CREATE INDEX idx_dde_events_node ON dde_events(node_id);
CREATE INDEX idx_dde_artifacts_iteration ON dde_artifacts(iteration_id);
```

### Stream 2 (BDV) Database Schema

```sql
-- BDV database tables
CREATE TABLE bdv_manifests (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) UNIQUE NOT NULL,
    feature_files TEXT[],
    base_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bdv_scenarios (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES bdv_manifests(iteration_id),
    feature_file VARCHAR(500),
    scenario_id VARCHAR(500),
    scenario_name TEXT,
    contract_tag VARCHAR(100),
    status VARCHAR(50)
);

CREATE TABLE bdv_results (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES bdv_manifests(iteration_id),
    scenario_id VARCHAR(500),
    run_timestamp TIMESTAMP,
    passed BOOLEAN,
    duration DECIMAL(10,3),
    error_message TEXT
);

CREATE TABLE bdv_audits (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES bdv_manifests(iteration_id),
    audit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    passed BOOLEAN,
    total_scenarios INT,
    passed_scenarios INT,
    failed_scenarios INT,
    flake_rate DECIMAL(3,2),
    contract_mismatches TEXT[],
    details JSONB
);

CREATE INDEX idx_bdv_results_iteration ON bdv_results(iteration_id);
CREATE INDEX idx_bdv_results_scenario ON bdv_results(scenario_id);
```

### Stream 3 (ACC) Database Schema

```sql
-- ACC database tables
CREATE TABLE acc_manifests (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) UNIQUE NOT NULL,
    project VARCHAR(255),
    version VARCHAR(50),
    components JSONB,
    rules JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE acc_rules (
    id SERIAL PRIMARY KEY,
    manifest_id INT REFERENCES acc_manifests(id),
    rule_id VARCHAR(100),
    rule_type VARCHAR(50),
    description TEXT,
    rule_expression TEXT,
    severity VARCHAR(50)
);

CREATE TABLE acc_violations (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES acc_manifests(iteration_id),
    rule_id VARCHAR(100),
    source_module VARCHAR(500),
    target_module VARCHAR(500),
    message TEXT,
    severity VARCHAR(50),
    suppressed BOOLEAN DEFAULT FALSE
);

CREATE TABLE acc_audits (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) REFERENCES acc_manifests(iteration_id),
    audit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    passed BOOLEAN,
    blocking_violations INT,
    warning_violations INT,
    cycles INT,
    coupling_scores JSONB,
    details JSONB
);

CREATE INDEX idx_acc_violations_iteration ON acc_violations(iteration_id);
CREATE INDEX idx_acc_violations_rule ON acc_violations(rule_id);
```

### Convergence Database Schema

```sql
-- Tri-modal audit results
CREATE TABLE tri_audits (
    id SERIAL PRIMARY KEY,
    iteration_id VARCHAR(100) UNIQUE NOT NULL,
    audit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verdict VARCHAR(50),
    can_deploy BOOLEAN,
    diagnosis TEXT,
    recommendations TEXT[],
    dde_audit_id INT REFERENCES dde_audits(id),
    bdv_audit_id INT REFERENCES bdv_audits(id),
    acc_audit_id INT REFERENCES acc_audits(id),
    dde_passed BOOLEAN,
    bdv_passed BOOLEAN,
    acc_passed BOOLEAN
);

CREATE INDEX idx_tri_audits_iteration ON tri_audits(iteration_id);
CREATE INDEX idx_tri_audits_verdict ON tri_audits(verdict);
```

---

## PARALLEL DEVELOPMENT TIMELINE

```
┌─────────────┬─────────────────────┬─────────────────────┬─────────────────────┐
│             │   STREAM 1 (DDE)    │   STREAM 2 (BDV)    │   STREAM 3 (ACC)    │
├─────────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ WEEK 1-2    │ - Manifest schema   │ - Feature files     │ - AaC schema        │
│ Foundation  │ - Interface nodes   │ - Runner setup      │ - Import graph      │
│             │ - Artifact stamping │ - 5-10 scenarios    │ - Basic rules       │
│             │                     │                     │ - Rule engine       │
├─────────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ WEEK 3-4    │ - Capability reg    │ - Contract tags     │ - Severity levels   │
│ Enhancement │ - Taxonomy (10-15)  │ - Version checks    │ - Suppressions      │
│             │ - Matcher algo      │ - OpenAPI→Gherkin   │ - ADR enforcement   │
│             │ - JIT assignment    │ - 10+ scenarios     │ - Rule validation   │
├─────────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ WEEK 5-6    │ - Gate classify     │ - Quarantine list   │ - Cyclic deps       │
│ Maturity    │ - Contract lockdown │ - Auto-ratchet      │ - Coupling metrics  │
│             │ - Event log         │ - Flake tracking    │ - Complexity        │
│             │ - Policy enforce    │ - Threshold enforce │ - Dead code detect  │
├─────────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ WEEK 7-8    │ - DDE audit         │ - 20 journeys       │ - Arch diffs        │
│ Audit       │ - Preflight sim     │ - 50+ scenarios     │ - Visual graphs     │
│             │ - Metrics (Prom)    │ - BDV audit         │ - Erosion tracking  │
│             │ - DDE API           │ - BDV API           │ - ACC audit         │
│             │                     │                     │ - ACC API           │
├─────────────┴─────────────────────┴─────────────────────┴─────────────────────┤
│                          CONVERGENCE LAYER (WEEK 7-8)                          │
│                    - tri_audit.py (collaborative)                              │
│                    - Failure diagnosis matrix                                  │
│                    - Deployment gate (all 3 must pass)                         │
│                    - Pilot project with all 3 streams                          │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## COORDINATION PROTOCOL (Minimal)

### Weekly Sync (30 minutes, every Friday)

**Agenda**:
1. **Progress Update** (10 min)
   - Stream 1 (DDE): Share completions, blockers
   - Stream 2 (BDV): Share completions, blockers
   - Stream 3 (ACC): Share completions, blockers

2. **Blocker Resolution** (10 min)
   - Identify cross-stream dependencies
   - Agree on resolution plans

3. **Convergence Planning** (10 min)
   - Week 6: Review convergence API contracts
   - Week 7-8: Coordinate pilot project

### Week 6 Integration Planning Session (1 hour)

**Agenda**:
1. **API Contract Review** (30 min)
   - Review audit result schemas (DDEAuditResult, BDVAuditResult, ACCAuditResult)
   - Agree on tri-audit API contracts
   - Define JSON response formats

2. **Pilot Project Planning** (30 min)
   - Select pilot project (5-7 nodes)
   - Assign tasks (each engineer owns their stream)
   - Schedule Week 8 execution

### Week 7-8 Convergence Sprint

**Daily Standup** (15 min):
- Yesterday: What did I complete?
- Today: What will I work on?
- Blockers: What's blocking me?

**Collaborative Tasks**:
- tri_audit.py implementation (pair programming)
- Failure diagnosis matrix testing
- Pilot project execution and monitoring

---

## INCREMENTAL VALUE DELIVERY

### After Week 2 (Each Stream Independently Valuable)

**Stream 1 (DDE)**:
- ✅ Interface nodes execute before dependents
- **Value**: Integration failures reduced by 30%

**Stream 2 (BDV)**:
- ✅ 5-10 core scenarios validated
- **Value**: Behavior drift detected early

**Stream 3 (ACC)**:
- ✅ Basic layering enforced
- **Value**: Common violations prevented

### After Week 4 (Each Stream Enhanced)

**Stream 1 (DDE)**:
- ✅ Capability-based routing active
- **Value**: Resource utilization improved by 20%

**Stream 2 (BDV)**:
- ✅ Contract-scenario alignment enforced
- **Value**: Spec-behavior drift eliminated

**Stream 3 (ACC)**:
- ✅ Comprehensive rules with suppressions
- **Value**: Pragmatic enforcement balances rigor and flexibility

### After Week 6 (Each Stream Mature)

**Stream 1 (DDE)**:
- ✅ Policy compliance automated
- **Value**: Manual review burden reduced

**Stream 2 (BDV)**:
- ✅ Flaky tests managed
- **Value**: Signal-to-noise ratio improved

**Stream 3 (ACC)**:
- ✅ Static analysis comprehensive
- **Value**: Hidden issues caught proactively

### After Week 8 (Full Tri-Modal)

**All Streams**:
- ✅ Tri-modal audit operational
- ✅ Deployment gate enforced
- ✅ Pilot project successful
- **Value**: Comprehensive validation with non-overlapping blind spots

---

## SUCCESS METRICS

### Per-Stream Metrics

**Stream 1 (DDE)**:
- Interface-first execution: 100% of projects
- Assign latency (P95): <60s
- Gate pass rate (first try): ≥70%
- DDE audit detects issues: 100% accuracy

**Stream 2 (BDV)**:
- Core scenarios passing: ≥90%
- Flake rate: <10%
- Contract version validation: 100%
- BDV audit detects drift: 100% accuracy

**Stream 3 (ACC)**:
- Blocking violations: 0
- Cyclic dependencies: 0
- Coupling within limits: 100%
- ACC audit detects erosion: 100% accuracy

### Tri-Modal Metrics

- **Audit pass rate**: ≥95% (after initial stabilization)
- **Deployment blocked (rightfully)**: Track prevented bad deployments
- **False positives**: <5% (audits fail but should pass)
- **False negatives**: 0% (audits pass but issues exist)

---

## PILOT PROJECT (Week 8)

### Project: Simple API Feature

**Description**: Add user profile update endpoint to Dog Marketplace API

**Complexity**: 5-7 nodes, 2 interface nodes

**Expected Duration**: 4 hours end-to-end

### Execution Plan

**Stream 1 (DDE)**:
1. Generate execution manifest:
   - IF.UserProfileAPI (interface node)
   - IF.UserProfileSchema (interface node)
   - FE.ProfilePage (implementation node)
   - BE.UpdateProfile (implementation node)
   - BE.ValidateProfile (implementation node)
   - DB.UserProfileMigration (implementation node)
   - QA.ProfileTests (implementation node)

2. Execute with interface-first scheduling
3. Monitor assign latency, gate pass rate
4. Run DDE audit

**Stream 2 (BDV)**:
1. Write 3-5 scenarios:
   - Scenario: Update profile with valid data
   - Scenario: Update profile with invalid data
   - Scenario: Update profile with missing fields

2. Tag with contract version: `@contract:UserProfileAPI:v1.0`
3. Run scenarios against integrated build
4. Run BDV audit

**Stream 3 (ACC)**:
1. Define expected layering:
   - FE.ProfilePage → BE.UpdateProfile (allowed)
   - BE.UpdateProfile → DB.UserProfileMigration (allowed)
   - FE.ProfilePage → DB.UserProfileMigration (forbidden)

2. Run ACC check
3. Generate dependency graph
4. Run ACC audit

**Convergence**:
1. Run tri-modal audit
2. Check verdict:
   - If ALL_PASS → Deploy to staging
   - If any fail → Diagnose and iterate

3. Collect metrics:
   - DDE: Execution time, gate pass rate
   - BDV: Scenario pass rate, flake rate
   - ACC: Violations, coupling

4. Compare to baseline (traditional SDLC)

### Expected Outcomes

**Success Criteria**:
- Tri-modal audit passes on first or second attempt
- Pilot deployed to staging within 4 hours
- Metrics show improvement vs baseline:
  - 20-30% faster cycle time
  - 40-50% fewer integration issues
  - 100% traceability

**Failure Scenarios**:
- If DDE fails: Fix gates or adjust manifest
- If BDV fails: Fix scenarios or implementation
- If ACC fails: Refactor to fix violations
- Iterate until tri-modal audit passes

---

## REPOSITORY STRUCTURE

```
maestro-hive/
├── dde/                          # Stream 1: DDE
│   ├── api.py                    # DDE REST API
│   ├── artifact_stamper.py       # Artifact stamping
│   ├── audit_comparator.py       # Manifest vs execution log
│   ├── capability_matcher.py     # Capability matching
│   ├── contract_lockdown.py      # Contract lockdown logic
│   ├── dde_audit.py              # DDE audit
│   ├── gate_executor.py          # Gate execution hooks
│   ├── preflight_simulator.py    # Preflight validation
│   └── task_router.py            # JIT task assignment
│
├── bdv/                          # Stream 2: BDV
│   ├── api.py                    # BDV REST API
│   ├── bdv_audit.py              # BDV audit
│   ├── bdv_runner.py             # pytest-bdd runner
│   ├── contract_validator.py    # Contract version checks
│   ├── flake_detector.py         # Flake management
│   ├── generators/
│   │   └── openapi_to_gherkin.py # Test generation
│   └── steps/                    # Step definitions
│       ├── auth_steps.py
│       └── user_steps.py
│
├── acc/                          # Stream 3: ACC
│   ├── api.py                    # ACC REST API
│   ├── acc_audit.py              # ACC audit
│   ├── acc_check.py              # CLI tool
│   ├── architecture_diff.py      # Evolution tracking
│   ├── coupling_analyzer.py      # Coupling metrics
│   ├── import_graph_builder.py   # Import graph
│   ├── rule_engine.py            # Rule evaluation
│   └── suppression_manager.py    # Suppression logic
│
├── tri_audit/                    # Convergence Layer
│   ├── api.py                    # Tri-modal API
│   ├── failure_diagnosis.py      # Diagnosis logic
│   └── tri_audit.py              # Main convergence logic
│
├── config/                       # Configuration
│   ├── capability_taxonomy.yaml  # Skill taxonomy
│   ├── gate_classification.yaml  # Gate execution points
│   ├── bdv_quarantine.yaml       # Flaky test quarantine
│   └── acc_suppressions.yaml     # ACC suppressions
│
├── schemas/                      # JSON Schemas
│   ├── execution_manifest.schema.json
│   ├── architectural_manifest.schema.json
│   └── audit_result.schema.json
│
├── features/                     # BDV feature files
│   ├── auth/
│   │   └── authentication.feature
│   └── user/
│       └── profile.feature
│
├── manifests/                    # Manifests
│   ├── execution/                # Execution manifests
│   ├── behavioral/               # Feature files (symlink to features/)
│   └── architectural/            # Architectural manifests
│
└── reports/                      # Audit reports
    ├── dde/{iteration_id}/       # DDE reports
    ├── bdv/{iteration_id}/       # BDV reports
    ├── acc/{iteration_id}/       # ACC reports
    └── tri-modal/{iteration_id}/ # Tri-modal reports
```

---

## CODEOWNERS (Ownership Isolation)

```
# .github/CODEOWNERS

# Stream 1: DDE
/dde/**                         @lead-engineer
/manifests/execution/**         @lead-engineer
/reports/dde/**                 @lead-engineer

# Stream 2: BDV
/bdv/**                         @engineer-2
/features/**                    @engineer-2
/manifests/behavioral/**        @engineer-2
/reports/bdv/**                 @engineer-2

# Stream 3: ACC
/acc/**                         @engineer-3
/manifests/architectural/**     @engineer-3
/reports/acc/**                 @engineer-3

# Convergence Layer (all engineers)
/tri_audit/**                   @lead-engineer @engineer-2 @engineer-3

# Schemas (all engineers)
/schemas/**                     @lead-engineer @engineer-2 @engineer-3

# Config (requires 2 approvals)
/config/**                      @lead-engineer @engineer-2 @engineer-3
```

---

## NEXT STEPS (Immediate - Week 1, Day 1-2)

### Day 1: Kickoff & Decisions

1. **Team Assignment** (30 min)
   - Lead Engineer → Stream 1 (DDE)
   - Engineer 2 → Stream 2 (BDV)
   - Engineer 3 → Stream 3 (ACC)

2. **Kickoff Meeting** (1 hour)
   - Review this plan
   - Answer open questions
   - Agree on coordination protocol

3. **Decisions** (1 hour)
   - Contract testing: Spec-driven (start), Pact (Phase 2)
   - Multi-capability nodes: Split by default
   - Capability registry: Single-tenant MVP
   - BDV framework: pytest-bdd
   - ACC tooling: Custom (start)

4. **GitHub Project Setup** (1 hour)
   - Create 3 project boards (one per stream)
   - Create issues from this plan
   - Assign to engineers

### Day 2: Design Sprint

1. **Stream 1 (DDE)** - Lead Engineer
   - Design capability taxonomy (10-15 skills)
   - Draft execution manifest schema
   - Sketch database ERD

2. **Stream 2 (BDV)** - Engineer 2
   - Identify 5-10 core user journeys
   - Draft feature file structure
   - Sketch BDV runner architecture

3. **Stream 3 (ACC)** - Engineer 3
   - Draft architectural manifest schema
   - Design 3-5 basic rules
   - Sketch import graph builder

4. **Sync** (30 min)
   - Share designs
   - Identify dependencies
   - Finalize Week 1 tasks

---

## CONCLUSION

This plan implements the Tri-Modal Convergence Framework (DDF) as **3 independent, parallel streams**:

1. **STREAM 1 (DDE)**: Execution engine with capability routing
2. **STREAM 2 (BDV)**: Behavioral validation with contract alignment
3. **STREAM 3 (ACC)**: Architectural conformance checking

Each stream:
- ✅ Develops in parallel
- ✅ Delivers incremental value
- ✅ Has independent APIs and databases
- ✅ Can evolve at different speeds

They **converge at deployment** via tri-modal audit:

**Deploy ONLY when: DDE ✅ AND BDV ✅ AND ACC ✅**

This ensures **comprehensive validation with non-overlapping blind spots**.

**Timeline**: 8 weeks to MVP, with value delivered every 2 weeks.

**Outcome**: A production-ready tri-modal framework that prevents bad deployments by requiring convergence of execution, behavior, and architecture audits.

---

**END OF TRI-MODAL IMPLEMENTATION PLAN**
