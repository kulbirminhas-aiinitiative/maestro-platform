/**
 * DDE (Dependency-Driven Execution) Type Definitions
 *
 * Implements the 'Built Right' validation system with interface-first execution,
 * capability-based routing, quality gate enforcement, and artifact stamping.
 *
 * @module dde.types
 * @version 1.0.0
 */

// =============================================================================
// Core Enums
// =============================================================================

/**
 * Execution phases in dependency order (interfaces first, then implementations)
 */
export enum ExecutionPhase {
  REQUIREMENTS = 'REQUIREMENTS',
  DESIGN = 'DESIGN',
  INTERFACE_DEFINITION = 'INTERFACE_DEFINITION',
  IMPLEMENTATION = 'IMPLEMENTATION',
  TESTING = 'TESTING',
  INTEGRATION = 'INTEGRATION',
  DEPLOYMENT = 'DEPLOYMENT'
}

/**
 * Quality gate status indicators
 */
export enum QualityGateStatus {
  PENDING = 'PENDING',
  IN_PROGRESS = 'IN_PROGRESS',
  PASSED = 'PASSED',
  FAILED = 'FAILED',
  SKIPPED = 'SKIPPED',
  BLOCKED = 'BLOCKED'
}

/**
 * Artifact types produced during execution
 */
export enum ArtifactType {
  REQUIREMENT_SPEC = 'REQUIREMENT_SPEC',
  DESIGN_DOC = 'DESIGN_DOC',
  INTERFACE_DEFINITION = 'INTERFACE_DEFINITION',
  SOURCE_CODE = 'SOURCE_CODE',
  TEST_SUITE = 'TEST_SUITE',
  TEST_RESULTS = 'TEST_RESULTS',
  DEPLOYMENT_CONFIG = 'DEPLOYMENT_CONFIG',
  API_DOCUMENTATION = 'API_DOCUMENTATION'
}

/**
 * Agent capability types for routing
 */
export enum AgentCapability {
  REQUIREMENTS_ANALYSIS = 'REQUIREMENTS_ANALYSIS',
  ARCHITECTURE_DESIGN = 'ARCHITECTURE_DESIGN',
  INTERFACE_DESIGN = 'INTERFACE_DESIGN',
  CODE_GENERATION = 'CODE_GENERATION',
  TEST_GENERATION = 'TEST_GENERATION',
  CODE_REVIEW = 'CODE_REVIEW',
  DEPLOYMENT = 'DEPLOYMENT',
  DOCUMENTATION = 'DOCUMENTATION'
}

/**
 * Execution status for workflow nodes
 */
export enum ExecutionStatus {
  PENDING = 'PENDING',
  QUEUED = 'QUEUED',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
  BLOCKED = 'BLOCKED'
}

// =============================================================================
// Core Interfaces
// =============================================================================

/**
 * Contract version tracking for artifacts
 */
export interface ContractVersion {
  /** Semantic version string */
  version: string;
  /** Contract hash for integrity verification */
  hash: string;
  /** ISO timestamp of contract creation */
  createdAt: string;
  /** Previous version reference (if exists) */
  previousVersion?: string;
  /** Breaking changes flag */
  hasBreakingChanges: boolean;
}

/**
 * Metadata stamped on each artifact
 */
export interface ArtifactStamp {
  /** Unique artifact identifier */
  artifactId: string;
  /** Type of artifact */
  type: ArtifactType;
  /** ISO timestamp of creation */
  createdAt: string;
  /** Agent that produced the artifact */
  producedBy: string;
  /** Execution phase that produced artifact */
  phase: ExecutionPhase;
  /** SHA-256 hash of artifact content */
  contentHash: string;
  /** Contract version at time of creation */
  contractVersion: ContractVersion;
  /** Parent artifact IDs (dependencies) */
  dependencies: string[];
  /** Quality score (0-1) */
  qualityScore: number;
  /** Additional metadata */
  metadata: Record<string, unknown>;
}

/**
 * Quality gate definition
 */
export interface QualityGate {
  /** Unique gate identifier */
  gateId: string;
  /** Gate name */
  name: string;
  /** Execution phase this gate belongs to */
  phase: ExecutionPhase;
  /** Quality criteria to evaluate */
  criteria: QualityCriterion[];
  /** Minimum score to pass (0-1) */
  threshold: number;
  /** Whether this gate is mandatory */
  mandatory: boolean;
  /** Gate dependencies (must pass before this gate) */
  dependsOn: string[];
}

/**
 * Individual quality criterion within a gate
 */
export interface QualityCriterion {
  /** Criterion identifier */
  criterionId: string;
  /** Criterion name */
  name: string;
  /** Description of what is being checked */
  description: string;
  /** Weight for scoring (0-1) */
  weight: number;
  /** Evaluation function name */
  evaluator: string;
  /** Configuration for the evaluator */
  config: Record<string, unknown>;
}

/**
 * Result of quality gate evaluation
 */
export interface QualityGateResult {
  /** Gate that was evaluated */
  gateId: string;
  /** Overall status */
  status: QualityGateStatus;
  /** Overall score (0-1) */
  score: number;
  /** Whether threshold was met */
  passed: boolean;
  /** Individual criterion results */
  criterionResults: CriterionResult[];
  /** Evaluation timestamp */
  evaluatedAt: string;
  /** Evaluation duration in ms */
  durationMs: number;
  /** Issues found during evaluation */
  issues: QualityIssue[];
  /** Recommendations for improvement */
  recommendations: string[];
}

/**
 * Individual criterion evaluation result
 */
export interface CriterionResult {
  /** Criterion that was evaluated */
  criterionId: string;
  /** Score achieved (0-1) */
  score: number;
  /** Whether criterion passed */
  passed: boolean;
  /** Details about evaluation */
  details: string;
  /** Evidence supporting the result */
  evidence: Record<string, unknown>;
}

/**
 * Quality issue found during evaluation
 */
export interface QualityIssue {
  /** Issue severity */
  severity: 'critical' | 'major' | 'minor' | 'info';
  /** Issue category */
  category: string;
  /** Issue description */
  message: string;
  /** Location of issue (if applicable) */
  location?: string;
  /** Suggested fix */
  suggestion?: string;
}

// =============================================================================
// Agent & Routing Interfaces
// =============================================================================

/**
 * AI Agent definition for capability-based routing
 */
export interface Agent {
  /** Unique agent identifier */
  agentId: string;
  /** Agent name */
  name: string;
  /** Agent description */
  description: string;
  /** Capabilities this agent provides */
  capabilities: AgentCapability[];
  /** Maximum concurrent tasks */
  maxConcurrency: number;
  /** Current load (0-1) */
  currentLoad: number;
  /** Agent availability status */
  available: boolean;
  /** Agent-specific configuration */
  config: Record<string, unknown>;
}

/**
 * Routing decision for task assignment
 */
export interface RoutingDecision {
  /** Task to be routed */
  taskId: string;
  /** Selected agent */
  agentId: string;
  /** Required capabilities */
  requiredCapabilities: AgentCapability[];
  /** Routing score (0-1) */
  score: number;
  /** Reason for selection */
  reason: string;
  /** Alternative agents considered */
  alternatives: Array<{ agentId: string; score: number }>;
}

// =============================================================================
// Execution Interfaces
// =============================================================================

/**
 * Execution node in the dependency graph
 */
export interface ExecutionNode {
  /** Unique node identifier */
  nodeId: string;
  /** Node name */
  name: string;
  /** Execution phase */
  phase: ExecutionPhase;
  /** Required capabilities */
  requiredCapabilities: AgentCapability[];
  /** Dependencies (node IDs that must complete first) */
  dependencies: string[];
  /** Current execution status */
  status: ExecutionStatus;
  /** Assigned agent (if routed) */
  assignedAgent?: string;
  /** Input artifacts */
  inputs: string[];
  /** Output artifacts */
  outputs: string[];
  /** Execution configuration */
  config: Record<string, unknown>;
}

/**
 * Execution context passed through the workflow
 */
export interface ExecutionContext {
  /** Workflow execution ID */
  executionId: string;
  /** Workflow definition ID */
  workflowId: string;
  /** Current execution phase */
  currentPhase: ExecutionPhase;
  /** Artifacts produced so far */
  artifacts: Map<string, ArtifactStamp>;
  /** Quality gate results */
  gateResults: Map<string, QualityGateResult>;
  /** Execution variables */
  variables: Record<string, unknown>;
  /** Execution start time */
  startedAt: string;
  /** Parent context (for nested workflows) */
  parentContext?: string;
}

/**
 * Workflow definition
 */
export interface WorkflowDefinition {
  /** Unique workflow identifier */
  workflowId: string;
  /** Workflow name */
  name: string;
  /** Workflow description */
  description: string;
  /** Workflow version */
  version: string;
  /** Execution nodes */
  nodes: ExecutionNode[];
  /** Quality gates */
  qualityGates: QualityGate[];
  /** Global configuration */
  config: WorkflowConfig;
}

/**
 * Workflow configuration options
 */
export interface WorkflowConfig {
  /** Quality threshold for overall workflow */
  qualityThreshold: number;
  /** Maximum execution time in ms */
  maxExecutionTime: number;
  /** Whether to continue on non-critical failures */
  continueOnFailure: boolean;
  /** Parallel execution settings */
  parallelExecution: {
    enabled: boolean;
    maxParallel: number;
  };
  /** Retry configuration */
  retry: {
    enabled: boolean;
    maxRetries: number;
    backoffMs: number;
  };
}

/**
 * Workflow execution result
 */
export interface WorkflowExecutionResult {
  /** Execution ID */
  executionId: string;
  /** Workflow ID */
  workflowId: string;
  /** Overall status */
  status: ExecutionStatus;
  /** Overall quality score */
  qualityScore: number;
  /** All artifacts produced */
  artifacts: ArtifactStamp[];
  /** All gate results */
  gateResults: QualityGateResult[];
  /** Node execution summaries */
  nodeResults: NodeExecutionResult[];
  /** Execution start time */
  startedAt: string;
  /** Execution end time */
  completedAt: string;
  /** Total duration in ms */
  durationMs: number;
  /** Errors encountered */
  errors: ExecutionError[];
}

/**
 * Individual node execution result
 */
export interface NodeExecutionResult {
  /** Node ID */
  nodeId: string;
  /** Execution status */
  status: ExecutionStatus;
  /** Assigned agent */
  agentId: string;
  /** Output artifacts */
  outputs: string[];
  /** Start time */
  startedAt: string;
  /** End time */
  completedAt: string;
  /** Duration in ms */
  durationMs: number;
  /** Error (if failed) */
  error?: ExecutionError;
}

/**
 * Execution error details
 */
export interface ExecutionError {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Error details */
  details: Record<string, unknown>;
  /** Stack trace (if available) */
  stack?: string;
  /** Node that failed */
  nodeId?: string;
  /** Timestamp */
  timestamp: string;
}

// =============================================================================
// API Request/Response Types
// =============================================================================

/**
 * Request to execute a workflow
 */
export interface ExecuteWorkflowRequest {
  /** Workflow ID to execute */
  workflowId: string;
  /** Input parameters */
  inputs: Record<string, unknown>;
  /** Execution options */
  options?: Partial<WorkflowConfig>;
}

/**
 * Response from workflow execution
 */
export interface ExecuteWorkflowResponse {
  /** Execution ID */
  executionId: string;
  /** Current status */
  status: ExecutionStatus;
  /** Message */
  message: string;
}

/**
 * Request to check quality gate
 */
export interface CheckQualityGateRequest {
  /** Execution ID */
  executionId: string;
  /** Gate ID to check */
  gateId: string;
  /** Artifacts to evaluate */
  artifacts: string[];
}

/**
 * Response from quality gate check
 */
export interface CheckQualityGateResponse {
  /** Gate result */
  result: QualityGateResult;
  /** Can proceed flag */
  canProceed: boolean;
}

// =============================================================================
// Event Types
// =============================================================================

/**
 * Base event interface
 */
export interface DDEEvent {
  /** Event ID */
  eventId: string;
  /** Event type */
  type: string;
  /** Event timestamp */
  timestamp: string;
  /** Execution ID */
  executionId: string;
  /** Event payload */
  payload: Record<string, unknown>;
}

/**
 * Event emitted when execution phase changes
 */
export interface PhaseChangeEvent extends DDEEvent {
  type: 'PHASE_CHANGE';
  payload: {
    previousPhase: ExecutionPhase;
    newPhase: ExecutionPhase;
  };
}

/**
 * Event emitted when quality gate is evaluated
 */
export interface QualityGateEvent extends DDEEvent {
  type: 'QUALITY_GATE_EVALUATED';
  payload: {
    gateId: string;
    result: QualityGateResult;
  };
}

/**
 * Event emitted when artifact is produced
 */
export interface ArtifactProducedEvent extends DDEEvent {
  type: 'ARTIFACT_PRODUCED';
  payload: {
    artifact: ArtifactStamp;
  };
}

export type DDEEventType = PhaseChangeEvent | QualityGateEvent | ArtifactProducedEvent;
