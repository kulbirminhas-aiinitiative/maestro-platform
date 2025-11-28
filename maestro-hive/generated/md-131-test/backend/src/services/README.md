# DDE Workflow Execution Engine

## Overview

The Dependency-Driven Execution (DDE) Engine implements a 'Built Right' validation system that ensures software artifacts are created following proper dependency order with quality gates at each phase.

## Components

### 1. Type Definitions (`dde.types.ts`)

Core type definitions for the DDE system including:

- **Execution Phases**: Requirements → Design → Interface Definition → Implementation → Testing → Integration → Deployment
- **Quality Gate Types**: Status, criteria, results
- **Artifact Stamping**: Metadata, contract versions, dependencies
- **Agent Routing**: Capabilities, routing decisions

### 2. Quality Gate Service (`quality-gate.service.ts`)

Enforces quality gates at each execution phase.

#### Features:
- Configurable quality criteria with weights
- Built-in evaluators (completeness, consistency, coverage, security)
- Custom evaluator support
- Gate dependency management
- Phase-based gate evaluation

#### Built-in Evaluators:
- `completeness` - Checks required fields presence
- `consistency` - Validates artifact consistency
- `coverage` - Validates test/documentation coverage
- `security` - Checks for security issues
- `interfaceCompliance` - Validates interface implementations
- `contractVersion` - Validates contract versioning

### 3. DDE Executor Service (`dde-executor.service.ts`)

Main orchestrator for workflow execution.

#### Features:
- Interface-first execution pattern
- Capability-based agent routing
- Parallel execution with dependency management
- Artifact stamping with full metadata
- Contract version tracking
- Event emission for monitoring

## Usage

### Basic Workflow Execution

```typescript
import { ddeExecutorService } from './services/dde-executor.service';

// Register sample agents
const agents = ddeExecutorService.createSampleAgents();
agents.forEach(agent => ddeExecutorService.registerAgent(agent));

// Register workflow
const workflow = ddeExecutorService.createSampleWorkflow();
ddeExecutorService.registerWorkflow(workflow);

// Execute workflow
const response = await ddeExecutorService.executeWorkflow({
  workflowId: 'sample-dde-workflow',
  inputs: {
    projectName: 'my-project',
    requirements: ['REQ-001', 'REQ-002']
  }
});

console.log(`Execution started: ${response.executionId}`);
```

### Custom Quality Gates

```typescript
import { qualityGateService } from './services/quality-gate.service';
import { ExecutionPhase } from './types/dde.types';

// Register custom gate
qualityGateService.registerGate({
  gateId: 'custom-security-gate',
  name: 'Enhanced Security Gate',
  phase: ExecutionPhase.IMPLEMENTATION,
  criteria: [
    {
      criterionId: 'vuln-scan',
      name: 'Vulnerability Scan',
      description: 'No critical vulnerabilities',
      weight: 0.7,
      evaluator: 'security',
      config: {}
    },
    {
      criterionId: 'code-review',
      name: 'Code Review',
      description: 'Code review completed',
      weight: 0.3,
      evaluator: 'completeness',
      config: { requiredFields: ['reviewed', 'reviewedBy'] }
    }
  ],
  threshold: 0.9,
  mandatory: true,
  dependsOn: ['interface-gate']
});
```

### Custom Evaluators

```typescript
import { qualityGateService } from './services/quality-gate.service';

// Register custom evaluator
qualityGateService.registerEvaluator('performanceCheck', async (artifact, config) => {
  const metrics = artifact.metadata.performanceMetrics as any;
  const threshold = (config.responseTimeMs as number) || 200;

  const score = metrics?.avgResponseTime < threshold ? 1 : 0.5;

  return {
    score,
    details: `Avg response time: ${metrics?.avgResponseTime}ms (threshold: ${threshold}ms)`,
    evidence: { metrics }
  };
});
```

### Event Handling

```typescript
import { ddeExecutorService } from './services/dde-executor.service';

// Listen for all events
ddeExecutorService.on('event', (event) => {
  console.log(`Event: ${event.type}`, event.payload);
});

// Listen for specific events
ddeExecutorService.on('PHASE_CHANGE', (event) => {
  console.log(`Phase changed to: ${event.payload.newPhase}`);
});

ddeExecutorService.on('QUALITY_GATE_EVALUATED', (event) => {
  const { gateId, result } = event.payload;
  console.log(`Gate ${gateId}: ${result.status} (score: ${result.score})`);
});

ddeExecutorService.on('ARTIFACT_PRODUCED', (event) => {
  const { artifact } = event.payload;
  console.log(`Artifact produced: ${artifact.artifactId}`);
});
```

## API Reference

### DDEExecutorService

| Method | Description |
|--------|-------------|
| `registerWorkflow(workflow)` | Register a workflow definition |
| `registerAgent(agent)` | Register an AI agent |
| `executeWorkflow(request)` | Start workflow execution |
| `getExecutionStatus(executionId)` | Get current execution context |
| `getExecutionArtifacts(executionId)` | Get all artifacts for an execution |
| `updateContractVersion(workflowId, hasBreaking)` | Update contract version |
| `createSampleWorkflow()` | Create a sample workflow for testing |
| `createSampleAgents()` | Create sample agents for testing |

### QualityGateService

| Method | Description |
|--------|-------------|
| `registerGate(gate)` | Register a quality gate |
| `registerGates(gates)` | Register multiple gates |
| `registerEvaluator(name, fn)` | Register custom evaluator |
| `evaluateGate(gateId, artifacts, executionId)` | Evaluate a single gate |
| `evaluatePhaseGates(phase, artifacts, executionId)` | Evaluate all gates for a phase |
| `getResults(executionId)` | Get all results for an execution |
| `calculateOverallScore(executionId)` | Calculate overall quality score |
| `canProceed(executionId)` | Check if execution can proceed |
| `createDefaultGates()` | Create default SDLC gates |

## Architecture

```
┌─────────────────────────────────────────────────┐
│              DDE Executor Service               │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐             │
│  │  Workflow   │  │    Agent     │             │
│  │  Manager    │  │   Router     │             │
│  └─────────────┘  └──────────────┘             │
│                                                 │
│  ┌─────────────────────────────────┐           │
│  │      Phase Executor             │           │
│  │  (respects dependency order)    │           │
│  └─────────────────────────────────┘           │
│                                                 │
│  ┌─────────────┐  ┌──────────────┐             │
│  │  Artifact   │  │  Contract    │             │
│  │  Stamper    │  │  Versioning  │             │
│  └─────────────┘  └──────────────┘             │
├─────────────────────────────────────────────────┤
│           Quality Gate Service                  │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐             │
│  │    Gate     │  │  Evaluator   │             │
│  │  Registry   │  │   Engine     │             │
│  └─────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘
```

## Quality Metrics

The system tracks and enforces:

- **Completeness**: All required fields present
- **Consistency**: Artifacts align with dependencies
- **Coverage**: Test and documentation coverage
- **Security**: No critical/high vulnerabilities
- **Interface Compliance**: Implementations match interfaces
- **Contract Versioning**: Proper version tracking

## Contract Deliverables

This implementation fulfills the Backend Developer Contract for MD-131:

✅ **api_endpoints** - ExecuteWorkflowRequest/Response types defined
✅ **backend_code** - DDEExecutorService and QualityGateService implemented
✅ **database_schema** - Type definitions for persistence (dde.types.ts)
✅ **api_documentation** - This README and inline JSDoc comments

## Dependencies

- `uuid` - For generating unique identifiers
- `crypto` - For content hashing (SHA-256)
- `events` - For event emission

## Version

1.0.0 - Initial implementation
