/**
 * DDE (Dependency-Driven Execution) Executor Service
 *
 * Orchestrates workflow execution following the 'Built Right' validation system.
 * Ensures interface-first execution pattern, capability-based routing,
 * quality gate enforcement, and artifact stamping with metadata.
 *
 * @module dde-executor.service
 * @version 1.0.0
 */

import { v4 as uuidv4 } from 'uuid';
import { createHash } from 'crypto';
import { EventEmitter } from 'events';
import {
  ExecutionPhase,
  ExecutionStatus,
  ExecutionNode,
  ExecutionContext,
  WorkflowDefinition,
  WorkflowExecutionResult,
  NodeExecutionResult,
  ExecutionError,
  ArtifactStamp,
  ArtifactType,
  ContractVersion,
  Agent,
  AgentCapability,
  RoutingDecision,
  QualityGateResult,
  DDEEvent,
  ExecuteWorkflowRequest,
  ExecuteWorkflowResponse
} from '../types/dde.types';
import { QualityGateService, qualityGateService } from './quality-gate.service';

/**
 * Configuration for DDEExecutorService
 */
export interface DDEExecutorServiceConfig {
  /** Maximum concurrent node executions */
  maxConcurrency: number;
  /** Default execution timeout in ms */
  defaultTimeout: number;
  /** Enable verbose logging */
  verbose: boolean;
  /** Quality gate service instance */
  qualityGateService: QualityGateService;
}

/**
 * Phase execution order (interfaces first, then implementations)
 */
const PHASE_ORDER: ExecutionPhase[] = [
  ExecutionPhase.REQUIREMENTS,
  ExecutionPhase.DESIGN,
  ExecutionPhase.INTERFACE_DEFINITION,
  ExecutionPhase.IMPLEMENTATION,
  ExecutionPhase.TESTING,
  ExecutionPhase.INTEGRATION,
  ExecutionPhase.DEPLOYMENT
];

/**
 * DDE Executor Service
 *
 * Main orchestrator for dependency-driven workflow execution with
 * quality gate enforcement and capability-based agent routing.
 */
export class DDEExecutorService extends EventEmitter {
  private config: DDEExecutorServiceConfig;
  private workflows: Map<string, WorkflowDefinition> = new Map();
  private executions: Map<string, ExecutionContext> = new Map();
  private agents: Map<string, Agent> = new Map();
  private contractVersions: Map<string, ContractVersion> = new Map();

  constructor(config: Partial<DDEExecutorServiceConfig> = {}) {
    super();
    this.config = {
      maxConcurrency: 5,
      defaultTimeout: 300000, // 5 minutes
      verbose: false,
      qualityGateService: qualityGateService,
      ...config
    };
  }

  // ===========================================================================
  // Workflow Management
  // ===========================================================================

  /**
   * Register a workflow definition
   */
  registerWorkflow(workflow: WorkflowDefinition): void {
    // Validate workflow
    this.validateWorkflow(workflow);

    // Store workflow
    this.workflows.set(workflow.workflowId, workflow);

    // Register quality gates
    this.config.qualityGateService.registerGates(workflow.qualityGates);

    this.log(`Registered workflow: ${workflow.workflowId}`);
  }

  /**
   * Validate workflow definition
   */
  private validateWorkflow(workflow: WorkflowDefinition): void {
    // Check for cycles in dependencies
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const hasCycle = (nodeId: string): boolean => {
      visited.add(nodeId);
      recursionStack.add(nodeId);

      const node = workflow.nodes.find(n => n.nodeId === nodeId);
      if (node) {
        for (const depId of node.dependencies) {
          if (!visited.has(depId) && hasCycle(depId)) {
            return true;
          } else if (recursionStack.has(depId)) {
            return true;
          }
        }
      }

      recursionStack.delete(nodeId);
      return false;
    };

    for (const node of workflow.nodes) {
      if (hasCycle(node.nodeId)) {
        throw new Error(`Circular dependency detected in workflow: ${workflow.workflowId}`);
      }
      visited.clear();
      recursionStack.clear();
    }

    // Validate phase order (interfaces must come before implementations)
    for (const node of workflow.nodes) {
      for (const depId of node.dependencies) {
        const depNode = workflow.nodes.find(n => n.nodeId === depId);
        if (depNode) {
          const nodePhaseIndex = PHASE_ORDER.indexOf(node.phase);
          const depPhaseIndex = PHASE_ORDER.indexOf(depNode.phase);

          if (depPhaseIndex > nodePhaseIndex) {
            throw new Error(
              `Invalid dependency order: ${node.nodeId} (${node.phase}) depends on ` +
              `${depNode.nodeId} (${depNode.phase}). Interfaces must come before implementations.`
            );
          }
        }
      }
    }
  }

  // ===========================================================================
  // Agent Management
  // ===========================================================================

  /**
   * Register an AI agent
   */
  registerAgent(agent: Agent): void {
    this.agents.set(agent.agentId, agent);
    this.log(`Registered agent: ${agent.agentId} with capabilities: ${agent.capabilities.join(', ')}`);
  }

  /**
   * Route task to best available agent
   */
  private routeToAgent(
    node: ExecutionNode,
    executionId: string
  ): RoutingDecision {
    const candidates: Array<{ agent: Agent; score: number }> = [];

    for (const agent of this.agents.values()) {
      if (!agent.available) continue;

      // Check capability match
      const hasAllCapabilities = node.requiredCapabilities.every(
        cap => agent.capabilities.includes(cap)
      );

      if (!hasAllCapabilities) continue;

      // Calculate routing score based on:
      // 1. Capability coverage (how many extra capabilities)
      // 2. Current load
      // 3. Max concurrency headroom
      const capabilityCoverage = node.requiredCapabilities.length / agent.capabilities.length;
      const loadScore = 1 - agent.currentLoad;
      const concurrencyScore = agent.currentLoad < 1 ? 1 : 0;

      const score = (capabilityCoverage * 0.3) + (loadScore * 0.5) + (concurrencyScore * 0.2);

      candidates.push({ agent, score });
    }

    if (candidates.length === 0) {
      throw new Error(
        `No available agent found for capabilities: ${node.requiredCapabilities.join(', ')}`
      );
    }

    // Sort by score descending
    candidates.sort((a, b) => b.score - a.score);

    const selected = candidates[0];
    const alternatives = candidates.slice(1, 4).map(c => ({
      agentId: c.agent.agentId,
      score: c.score
    }));

    const decision: RoutingDecision = {
      taskId: `${executionId}-${node.nodeId}`,
      agentId: selected.agent.agentId,
      requiredCapabilities: node.requiredCapabilities,
      score: selected.score,
      reason: `Best match with score ${selected.score.toFixed(2)}`,
      alternatives
    };

    this.log(`Routed node ${node.nodeId} to agent ${selected.agent.agentId}`);

    return decision;
  }

  // ===========================================================================
  // Workflow Execution
  // ===========================================================================

  /**
   * Execute a workflow
   */
  async executeWorkflow(request: ExecuteWorkflowRequest): Promise<ExecuteWorkflowResponse> {
    const executionId = uuidv4();
    const workflow = this.workflows.get(request.workflowId);

    if (!workflow) {
      throw new Error(`Workflow not found: ${request.workflowId}`);
    }

    // Create execution context
    const context: ExecutionContext = {
      executionId,
      workflowId: request.workflowId,
      currentPhase: ExecutionPhase.REQUIREMENTS,
      artifacts: new Map(),
      gateResults: new Map(),
      variables: { ...request.inputs },
      startedAt: new Date().toISOString()
    };

    this.executions.set(executionId, context);

    // Start execution asynchronously
    this.runWorkflow(workflow, context, request.options || {}).catch(error => {
      this.log(`Workflow execution failed: ${error.message}`, 'error');
    });

    return {
      executionId,
      status: ExecutionStatus.RUNNING,
      message: `Workflow execution started: ${executionId}`
    };
  }

  /**
   * Run workflow execution
   */
  private async runWorkflow(
    workflow: WorkflowDefinition,
    context: ExecutionContext,
    options: Record<string, unknown>
  ): Promise<WorkflowExecutionResult> {
    const startTime = Date.now();
    const nodeResults: NodeExecutionResult[] = [];
    const errors: ExecutionError[] = [];

    try {
      // Execute phases in order
      for (const phase of PHASE_ORDER) {
        context.currentPhase = phase;
        this.emitEvent('PHASE_CHANGE', context.executionId, {
          previousPhase: PHASE_ORDER[PHASE_ORDER.indexOf(phase) - 1] || null,
          newPhase: phase
        });

        // Get nodes for this phase
        const phaseNodes = workflow.nodes.filter(n => n.phase === phase);

        if (phaseNodes.length === 0) continue;

        // Execute nodes respecting dependencies
        const results = await this.executePhaseNodes(phaseNodes, context, workflow);
        nodeResults.push(...results.nodeResults);
        errors.push(...results.errors);

        // Check if any node failed
        if (results.errors.some(e => e.code === 'NODE_EXECUTION_FAILED')) {
          if (!workflow.config.continueOnFailure) {
            throw new Error(`Phase ${phase} failed with errors`);
          }
        }

        // Evaluate quality gates for this phase
        const phaseArtifacts = Array.from(context.artifacts.values()).filter(
          a => a.phase === phase
        );

        const gateResults = await this.config.qualityGateService.evaluatePhaseGates(
          phase,
          phaseArtifacts,
          context.executionId
        );

        // Store gate results
        for (const result of gateResults.results) {
          context.gateResults.set(result.gateId, result);
          this.emitEvent('QUALITY_GATE_EVALUATED', context.executionId, {
            gateId: result.gateId,
            result
          });
        }

        // Check if gates passed
        if (!gateResults.passed && !workflow.config.continueOnFailure) {
          throw new Error(`Quality gates failed for phase ${phase}`);
        }
      }

      // Calculate final quality score
      const qualityScore = this.config.qualityGateService.calculateOverallScore(
        context.executionId
      );

      const result: WorkflowExecutionResult = {
        executionId: context.executionId,
        workflowId: workflow.workflowId,
        status: errors.length > 0 ? ExecutionStatus.FAILED : ExecutionStatus.COMPLETED,
        qualityScore,
        artifacts: Array.from(context.artifacts.values()),
        gateResults: Array.from(context.gateResults.values()),
        nodeResults,
        startedAt: context.startedAt,
        completedAt: new Date().toISOString(),
        durationMs: Date.now() - startTime,
        errors
      };

      this.log(`Workflow completed: ${context.executionId} (score: ${qualityScore.toFixed(2)})`);

      return result;
    } catch (error) {
      const execError: ExecutionError = {
        code: 'WORKFLOW_EXECUTION_FAILED',
        message: (error as Error).message,
        details: {},
        timestamp: new Date().toISOString()
      };
      errors.push(execError);

      return {
        executionId: context.executionId,
        workflowId: workflow.workflowId,
        status: ExecutionStatus.FAILED,
        qualityScore: 0,
        artifacts: Array.from(context.artifacts.values()),
        gateResults: Array.from(context.gateResults.values()),
        nodeResults,
        startedAt: context.startedAt,
        completedAt: new Date().toISOString(),
        durationMs: Date.now() - startTime,
        errors
      };
    }
  }

  /**
   * Execute nodes within a phase
   */
  private async executePhaseNodes(
    nodes: ExecutionNode[],
    context: ExecutionContext,
    workflow: WorkflowDefinition
  ): Promise<{ nodeResults: NodeExecutionResult[]; errors: ExecutionError[] }> {
    const nodeResults: NodeExecutionResult[] = [];
    const errors: ExecutionError[] = [];
    const completed = new Set<string>();

    // Topological sort for dependency order
    const sortedNodes = this.topologicalSortNodes(nodes);

    // Execute with concurrency control
    const { parallelExecution } = workflow.config;
    const maxParallel = parallelExecution.enabled ? parallelExecution.maxParallel : 1;

    let index = 0;
    while (index < sortedNodes.length) {
      // Find nodes ready to execute (all dependencies satisfied)
      const readyNodes: ExecutionNode[] = [];

      for (let i = index; i < sortedNodes.length && readyNodes.length < maxParallel; i++) {
        const node = sortedNodes[i];
        const depsCompleted = node.dependencies.every(dep => completed.has(dep));

        if (depsCompleted) {
          readyNodes.push(node);
        }
      }

      if (readyNodes.length === 0 && index < sortedNodes.length) {
        // Dependency deadlock
        throw new Error('Dependency deadlock detected');
      }

      // Execute ready nodes in parallel
      const results = await Promise.allSettled(
        readyNodes.map(node => this.executeNode(node, context, workflow))
      );

      // Process results
      for (let i = 0; i < results.length; i++) {
        const result = results[i];
        const node = readyNodes[i];

        if (result.status === 'fulfilled') {
          nodeResults.push(result.value);
          completed.add(node.nodeId);
        } else {
          const error: ExecutionError = {
            code: 'NODE_EXECUTION_FAILED',
            message: result.reason?.message || 'Unknown error',
            details: { nodeId: node.nodeId },
            nodeId: node.nodeId,
            timestamp: new Date().toISOString()
          };
          errors.push(error);
        }

        index++;
      }
    }

    return { nodeResults, errors };
  }

  /**
   * Execute a single node
   */
  private async executeNode(
    node: ExecutionNode,
    context: ExecutionContext,
    workflow: WorkflowDefinition
  ): Promise<NodeExecutionResult> {
    const startTime = Date.now();

    // Route to agent
    const routing = this.routeToAgent(node, context.executionId);
    node.assignedAgent = routing.agentId;
    node.status = ExecutionStatus.RUNNING;

    this.log(`Executing node: ${node.nodeId} on agent ${routing.agentId}`);

    try {
      // Simulate node execution (in real implementation, this would call the agent)
      await this.simulateNodeExecution(node, context);

      // Create artifact stamp
      const artifact = this.createArtifactStamp(node, context, routing.agentId);
      context.artifacts.set(artifact.artifactId, artifact);

      this.emitEvent('ARTIFACT_PRODUCED', context.executionId, { artifact });

      node.status = ExecutionStatus.COMPLETED;

      return {
        nodeId: node.nodeId,
        status: ExecutionStatus.COMPLETED,
        agentId: routing.agentId,
        outputs: [artifact.artifactId],
        startedAt: new Date(startTime).toISOString(),
        completedAt: new Date().toISOString(),
        durationMs: Date.now() - startTime
      };
    } catch (error) {
      node.status = ExecutionStatus.FAILED;

      return {
        nodeId: node.nodeId,
        status: ExecutionStatus.FAILED,
        agentId: routing.agentId,
        outputs: [],
        startedAt: new Date(startTime).toISOString(),
        completedAt: new Date().toISOString(),
        durationMs: Date.now() - startTime,
        error: {
          code: 'NODE_EXECUTION_ERROR',
          message: (error as Error).message,
          details: {},
          nodeId: node.nodeId,
          timestamp: new Date().toISOString()
        }
      };
    }
  }

  /**
   * Simulate node execution (placeholder for actual agent call)
   */
  private async simulateNodeExecution(
    node: ExecutionNode,
    context: ExecutionContext
  ): Promise<void> {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  // ===========================================================================
  // Artifact Stamping
  // ===========================================================================

  /**
   * Create an artifact stamp with full metadata
   */
  private createArtifactStamp(
    node: ExecutionNode,
    context: ExecutionContext,
    agentId: string
  ): ArtifactStamp {
    const artifactId = uuidv4();
    const content = JSON.stringify({
      nodeId: node.nodeId,
      phase: node.phase,
      executionId: context.executionId
    });

    // Get or create contract version
    const contractVersion = this.getOrCreateContractVersion(context.workflowId);

    // Get artifact dependencies
    const dependencies = node.inputs
      .map(input => context.artifacts.get(input)?.artifactId)
      .filter((id): id is string => id !== undefined);

    const artifact: ArtifactStamp = {
      artifactId,
      type: this.nodePhaseToArtifactType(node.phase),
      createdAt: new Date().toISOString(),
      producedBy: agentId,
      phase: node.phase,
      contentHash: this.hashContent(content),
      contractVersion,
      dependencies,
      qualityScore: 0.85, // Will be updated after quality gate evaluation
      metadata: {
        nodeId: node.nodeId,
        workflowId: context.workflowId,
        executionId: context.executionId,
        ...node.config
      }
    };

    this.log(`Created artifact: ${artifactId} for node ${node.nodeId}`);

    return artifact;
  }

  /**
   * Get or create contract version for a workflow
   */
  private getOrCreateContractVersion(workflowId: string): ContractVersion {
    const existing = this.contractVersions.get(workflowId);

    if (existing) {
      return existing;
    }

    const version: ContractVersion = {
      version: '1.0.0',
      hash: this.hashContent(workflowId + Date.now()),
      createdAt: new Date().toISOString(),
      hasBreakingChanges: false
    };

    this.contractVersions.set(workflowId, version);
    return version;
  }

  /**
   * Update contract version (increments version)
   */
  updateContractVersion(
    workflowId: string,
    hasBreakingChanges: boolean
  ): ContractVersion {
    const existing = this.contractVersions.get(workflowId);
    const previousVersion = existing?.version || '0.0.0';

    const [major, minor, patch] = previousVersion.split('.').map(Number);
    const newVersion = hasBreakingChanges
      ? `${major + 1}.0.0`
      : `${major}.${minor + 1}.${patch}`;

    const version: ContractVersion = {
      version: newVersion,
      hash: this.hashContent(workflowId + newVersion + Date.now()),
      createdAt: new Date().toISOString(),
      previousVersion,
      hasBreakingChanges
    };

    this.contractVersions.set(workflowId, version);
    return version;
  }

  /**
   * Map execution phase to artifact type
   */
  private nodePhaseToArtifactType(phase: ExecutionPhase): ArtifactType {
    const mapping: Record<ExecutionPhase, ArtifactType> = {
      [ExecutionPhase.REQUIREMENTS]: ArtifactType.REQUIREMENT_SPEC,
      [ExecutionPhase.DESIGN]: ArtifactType.DESIGN_DOC,
      [ExecutionPhase.INTERFACE_DEFINITION]: ArtifactType.INTERFACE_DEFINITION,
      [ExecutionPhase.IMPLEMENTATION]: ArtifactType.SOURCE_CODE,
      [ExecutionPhase.TESTING]: ArtifactType.TEST_SUITE,
      [ExecutionPhase.INTEGRATION]: ArtifactType.TEST_RESULTS,
      [ExecutionPhase.DEPLOYMENT]: ArtifactType.DEPLOYMENT_CONFIG
    };

    return mapping[phase];
  }

  /**
   * Hash content using SHA-256
   */
  private hashContent(content: string): string {
    return createHash('sha256').update(content).digest('hex');
  }

  // ===========================================================================
  // Utility Methods
  // ===========================================================================

  /**
   * Topological sort of nodes
   */
  private topologicalSortNodes(nodes: ExecutionNode[]): ExecutionNode[] {
    const sorted: ExecutionNode[] = [];
    const visited = new Set<string>();
    const nodeMap = new Map(nodes.map(n => [n.nodeId, n]));

    const visit = (node: ExecutionNode) => {
      if (visited.has(node.nodeId)) return;
      visited.add(node.nodeId);

      for (const depId of node.dependencies) {
        const depNode = nodeMap.get(depId);
        if (depNode) {
          visit(depNode);
        }
      }

      sorted.push(node);
    };

    for (const node of nodes) {
      visit(node);
    }

    return sorted;
  }

  /**
   * Emit execution event
   */
  private emitEvent(
    type: string,
    executionId: string,
    payload: Record<string, unknown>
  ): void {
    const event: DDEEvent = {
      eventId: uuidv4(),
      type,
      timestamp: new Date().toISOString(),
      executionId,
      payload
    };

    this.emit(type, event);
    this.emit('event', event);
  }

  /**
   * Get execution status
   */
  getExecutionStatus(executionId: string): ExecutionContext | undefined {
    return this.executions.get(executionId);
  }

  /**
   * Get all artifacts for an execution
   */
  getExecutionArtifacts(executionId: string): ArtifactStamp[] {
    const context = this.executions.get(executionId);
    if (!context) return [];
    return Array.from(context.artifacts.values());
  }

  /**
   * Logging helper
   */
  private log(message: string, level: 'info' | 'error' = 'info'): void {
    if (this.config.verbose) {
      const prefix = `[DDEExecutor]`;
      if (level === 'error') {
        console.error(`${prefix} ${message}`);
      } else {
        console.log(`${prefix} ${message}`);
      }
    }
  }

  // ===========================================================================
  // Factory Methods
  // ===========================================================================

  /**
   * Create a sample workflow for testing
   */
  createSampleWorkflow(): WorkflowDefinition {
    return {
      workflowId: 'sample-dde-workflow',
      name: 'Sample DDE Workflow',
      description: 'Demonstrates interface-first execution pattern',
      version: '1.0.0',
      nodes: [
        {
          nodeId: 'req-analysis',
          name: 'Requirements Analysis',
          phase: ExecutionPhase.REQUIREMENTS,
          requiredCapabilities: [AgentCapability.REQUIREMENTS_ANALYSIS],
          dependencies: [],
          status: ExecutionStatus.PENDING,
          inputs: [],
          outputs: ['requirements'],
          config: {}
        },
        {
          nodeId: 'arch-design',
          name: 'Architecture Design',
          phase: ExecutionPhase.DESIGN,
          requiredCapabilities: [AgentCapability.ARCHITECTURE_DESIGN],
          dependencies: ['req-analysis'],
          status: ExecutionStatus.PENDING,
          inputs: ['requirements'],
          outputs: ['design'],
          config: {}
        },
        {
          nodeId: 'interface-def',
          name: 'Interface Definition',
          phase: ExecutionPhase.INTERFACE_DEFINITION,
          requiredCapabilities: [AgentCapability.INTERFACE_DESIGN],
          dependencies: ['arch-design'],
          status: ExecutionStatus.PENDING,
          inputs: ['design'],
          outputs: ['interfaces'],
          config: {}
        },
        {
          nodeId: 'impl-code',
          name: 'Implementation',
          phase: ExecutionPhase.IMPLEMENTATION,
          requiredCapabilities: [AgentCapability.CODE_GENERATION],
          dependencies: ['interface-def'],
          status: ExecutionStatus.PENDING,
          inputs: ['interfaces'],
          outputs: ['code'],
          config: {}
        },
        {
          nodeId: 'test-gen',
          name: 'Test Generation',
          phase: ExecutionPhase.TESTING,
          requiredCapabilities: [AgentCapability.TEST_GENERATION],
          dependencies: ['impl-code'],
          status: ExecutionStatus.PENDING,
          inputs: ['code', 'interfaces'],
          outputs: ['tests'],
          config: {}
        }
      ],
      qualityGates: this.config.qualityGateService.createDefaultGates(),
      config: {
        qualityThreshold: 0.8,
        maxExecutionTime: 600000,
        continueOnFailure: false,
        parallelExecution: {
          enabled: true,
          maxParallel: 3
        },
        retry: {
          enabled: true,
          maxRetries: 3,
          backoffMs: 1000
        }
      }
    };
  }

  /**
   * Create sample agents for testing
   */
  createSampleAgents(): Agent[] {
    return [
      {
        agentId: 'requirements-agent',
        name: 'Requirements Analyst',
        description: 'Analyzes and documents requirements',
        capabilities: [AgentCapability.REQUIREMENTS_ANALYSIS, AgentCapability.DOCUMENTATION],
        maxConcurrency: 5,
        currentLoad: 0,
        available: true,
        config: {}
      },
      {
        agentId: 'architect-agent',
        name: 'System Architect',
        description: 'Designs system architecture',
        capabilities: [AgentCapability.ARCHITECTURE_DESIGN, AgentCapability.INTERFACE_DESIGN],
        maxConcurrency: 3,
        currentLoad: 0,
        available: true,
        config: {}
      },
      {
        agentId: 'developer-agent',
        name: 'Developer',
        description: 'Implements code',
        capabilities: [AgentCapability.CODE_GENERATION, AgentCapability.CODE_REVIEW],
        maxConcurrency: 10,
        currentLoad: 0,
        available: true,
        config: {}
      },
      {
        agentId: 'tester-agent',
        name: 'Test Engineer',
        description: 'Creates and runs tests',
        capabilities: [AgentCapability.TEST_GENERATION],
        maxConcurrency: 5,
        currentLoad: 0,
        available: true,
        config: {}
      }
    ];
  }
}

// Export singleton instance
export const ddeExecutorService = new DDEExecutorService({ verbose: true });
