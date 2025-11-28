/**
 * Quality Gate Service
 *
 * Enforces quality gates at each execution phase, evaluating artifacts
 * against defined criteria and ensuring quality thresholds are met.
 *
 * @module quality-gate.service
 * @version 1.0.0
 */

import { v4 as uuidv4 } from 'uuid';
import {
  QualityGate,
  QualityGateResult,
  QualityGateStatus,
  QualityCriterion,
  CriterionResult,
  QualityIssue,
  ArtifactStamp,
  ExecutionPhase
} from '../types/dde.types';

/**
 * Configuration for QualityGateService
 */
export interface QualityGateServiceConfig {
  /** Default threshold for gates without explicit threshold */
  defaultThreshold: number;
  /** Enable detailed logging */
  verbose: boolean;
  /** Custom evaluators map */
  customEvaluators?: Map<string, EvaluatorFunction>;
}

/**
 * Evaluator function signature
 */
type EvaluatorFunction = (
  artifact: ArtifactStamp,
  config: Record<string, unknown>
) => Promise<{ score: number; details: string; evidence: Record<string, unknown> }>;

/**
 * Quality Gate Service
 *
 * Provides quality gate definition, evaluation, and enforcement
 * for the DDE workflow execution engine.
 */
export class QualityGateService {
  private gates: Map<string, QualityGate> = new Map();
  private results: Map<string, QualityGateResult[]> = new Map();
  private evaluators: Map<string, EvaluatorFunction> = new Map();
  private config: QualityGateServiceConfig;

  constructor(config: Partial<QualityGateServiceConfig> = {}) {
    this.config = {
      defaultThreshold: 0.8,
      verbose: false,
      ...config
    };

    this.initializeDefaultEvaluators();

    if (config.customEvaluators) {
      config.customEvaluators.forEach((evaluator, name) => {
        this.evaluators.set(name, evaluator);
      });
    }
  }

  /**
   * Initialize built-in quality evaluators
   */
  private initializeDefaultEvaluators(): void {
    // Completeness evaluator - checks if artifact has all required fields
    this.evaluators.set('completeness', async (artifact, config) => {
      const requiredFields = (config.requiredFields as string[]) || [];
      const metadata = artifact.metadata as Record<string, unknown>;

      const presentFields = requiredFields.filter(field =>
        metadata[field] !== undefined && metadata[field] !== null
      );

      const score = requiredFields.length > 0
        ? presentFields.length / requiredFields.length
        : 1;

      return {
        score,
        details: `${presentFields.length}/${requiredFields.length} required fields present`,
        evidence: { presentFields, missingFields: requiredFields.filter(f => !presentFields.includes(f)) }
      };
    });

    // Consistency evaluator - checks artifact consistency with dependencies
    this.evaluators.set('consistency', async (artifact, config) => {
      const hasDependencies = artifact.dependencies.length > 0;
      const hasValidHash = artifact.contentHash && artifact.contentHash.length === 64;

      let score = 0;
      if (hasValidHash) score += 0.5;
      if (hasDependencies || config.allowNoDependencies) score += 0.5;

      return {
        score,
        details: `Hash valid: ${hasValidHash}, Dependencies tracked: ${hasDependencies}`,
        evidence: { hasValidHash, dependencyCount: artifact.dependencies.length }
      };
    });

    // Coverage evaluator - checks test coverage or documentation coverage
    this.evaluators.set('coverage', async (artifact, config) => {
      const minCoverage = (config.minCoverage as number) || 0.8;
      const actualCoverage = (artifact.metadata.coverage as number) || 0;
      const score = Math.min(actualCoverage / minCoverage, 1);

      return {
        score,
        details: `Coverage: ${(actualCoverage * 100).toFixed(1)}% (min: ${(minCoverage * 100).toFixed(1)}%)`,
        evidence: { actualCoverage, minCoverage }
      };
    });

    // Security evaluator - checks for security issues
    this.evaluators.set('security', async (artifact, config) => {
      const securityIssues = (artifact.metadata.securityIssues as unknown[]) || [];
      const criticalCount = securityIssues.filter((i: any) => i.severity === 'critical').length;
      const highCount = securityIssues.filter((i: any) => i.severity === 'high').length;

      let score = 1;
      score -= criticalCount * 0.3;
      score -= highCount * 0.1;
      score = Math.max(0, score);

      return {
        score,
        details: `Security issues: ${criticalCount} critical, ${highCount} high`,
        evidence: { criticalCount, highCount, totalIssues: securityIssues.length }
      };
    });

    // Interface compliance evaluator
    this.evaluators.set('interfaceCompliance', async (artifact, config) => {
      const interfaces = (artifact.metadata.interfaces as string[]) || [];
      const implementations = (artifact.metadata.implementations as string[]) || [];

      const implemented = interfaces.filter(i => implementations.includes(i));
      const score = interfaces.length > 0 ? implemented.length / interfaces.length : 1;

      return {
        score,
        details: `${implemented.length}/${interfaces.length} interfaces implemented`,
        evidence: { interfaces, implementations, missing: interfaces.filter(i => !implemented.includes(i)) }
      };
    });

    // Contract version evaluator
    this.evaluators.set('contractVersion', async (artifact, config) => {
      const hasVersion = !!artifact.contractVersion.version;
      const hasHash = !!artifact.contractVersion.hash;
      const noBreaking = !artifact.contractVersion.hasBreakingChanges || (config.allowBreaking as boolean);

      let score = 0;
      if (hasVersion) score += 0.4;
      if (hasHash) score += 0.4;
      if (noBreaking) score += 0.2;

      return {
        score,
        details: `Version: ${artifact.contractVersion.version}, Breaking: ${artifact.contractVersion.hasBreakingChanges}`,
        evidence: { ...artifact.contractVersion }
      };
    });
  }

  /**
   * Register a quality gate
   */
  registerGate(gate: QualityGate): void {
    this.gates.set(gate.gateId, gate);

    if (this.config.verbose) {
      console.log(`[QualityGateService] Registered gate: ${gate.gateId} for phase ${gate.phase}`);
    }
  }

  /**
   * Register multiple quality gates
   */
  registerGates(gates: QualityGate[]): void {
    gates.forEach(gate => this.registerGate(gate));
  }

  /**
   * Get gate by ID
   */
  getGate(gateId: string): QualityGate | undefined {
    return this.gates.get(gateId);
  }

  /**
   * Get all gates for a phase
   */
  getGatesForPhase(phase: ExecutionPhase): QualityGate[] {
    return Array.from(this.gates.values()).filter(gate => gate.phase === phase);
  }

  /**
   * Register a custom evaluator
   */
  registerEvaluator(name: string, evaluator: EvaluatorFunction): void {
    this.evaluators.set(name, evaluator);
  }

  /**
   * Evaluate a quality gate against artifacts
   */
  async evaluateGate(
    gateId: string,
    artifacts: ArtifactStamp[],
    executionId: string
  ): Promise<QualityGateResult> {
    const startTime = Date.now();
    const gate = this.gates.get(gateId);

    if (!gate) {
      throw new Error(`Quality gate not found: ${gateId}`);
    }

    // Check gate dependencies
    const dependencyResults = await this.checkGateDependencies(gate, executionId);
    if (!dependencyResults.allPassed) {
      return this.createBlockedResult(gate, startTime, dependencyResults.failedGates);
    }

    // Evaluate each criterion
    const criterionResults: CriterionResult[] = [];
    const issues: QualityIssue[] = [];
    const recommendations: string[] = [];

    for (const criterion of gate.criteria) {
      const result = await this.evaluateCriterion(criterion, artifacts);
      criterionResults.push(result);

      if (!result.passed) {
        issues.push({
          severity: criterion.weight > 0.5 ? 'major' : 'minor',
          category: criterion.name,
          message: `Criterion '${criterion.name}' did not meet threshold`,
          suggestion: `Review ${criterion.description}`
        });
        recommendations.push(`Improve ${criterion.name}: ${result.details}`);
      }
    }

    // Calculate weighted score
    const totalWeight = gate.criteria.reduce((sum, c) => sum + c.weight, 0);
    const weightedScore = criterionResults.reduce((sum, result, index) => {
      return sum + (result.score * gate.criteria[index].weight);
    }, 0) / (totalWeight || 1);

    const passed = weightedScore >= gate.threshold;
    const status = passed ? QualityGateStatus.PASSED : QualityGateStatus.FAILED;

    const result: QualityGateResult = {
      gateId,
      status,
      score: weightedScore,
      passed,
      criterionResults,
      evaluatedAt: new Date().toISOString(),
      durationMs: Date.now() - startTime,
      issues,
      recommendations
    };

    // Store result
    this.storeResult(executionId, result);

    if (this.config.verbose) {
      console.log(`[QualityGateService] Gate ${gateId}: ${status} (score: ${weightedScore.toFixed(2)})`);
    }

    return result;
  }

  /**
   * Evaluate a single criterion
   */
  private async evaluateCriterion(
    criterion: QualityCriterion,
    artifacts: ArtifactStamp[]
  ): Promise<CriterionResult> {
    const evaluator = this.evaluators.get(criterion.evaluator);

    if (!evaluator) {
      return {
        criterionId: criterion.criterionId,
        score: 0,
        passed: false,
        details: `Evaluator not found: ${criterion.evaluator}`,
        evidence: {}
      };
    }

    // Aggregate scores across all artifacts
    let totalScore = 0;
    const allEvidence: Record<string, unknown> = {};

    for (const artifact of artifacts) {
      const result = await evaluator(artifact, criterion.config);
      totalScore += result.score;
      Object.assign(allEvidence, result.evidence);
    }

    const avgScore = artifacts.length > 0 ? totalScore / artifacts.length : 0;
    const passed = avgScore >= 0.8; // Individual criterion threshold

    return {
      criterionId: criterion.criterionId,
      score: avgScore,
      passed,
      details: `Evaluated across ${artifacts.length} artifacts`,
      evidence: allEvidence
    };
  }

  /**
   * Check if gate dependencies are satisfied
   */
  private async checkGateDependencies(
    gate: QualityGate,
    executionId: string
  ): Promise<{ allPassed: boolean; failedGates: string[] }> {
    const results = this.results.get(executionId) || [];
    const failedGates: string[] = [];

    for (const depGateId of gate.dependsOn) {
      const depResult = results.find(r => r.gateId === depGateId);
      if (!depResult || !depResult.passed) {
        failedGates.push(depGateId);
      }
    }

    return {
      allPassed: failedGates.length === 0,
      failedGates
    };
  }

  /**
   * Create a blocked result for gates with failed dependencies
   */
  private createBlockedResult(
    gate: QualityGate,
    startTime: number,
    failedDependencies: string[]
  ): QualityGateResult {
    return {
      gateId: gate.gateId,
      status: QualityGateStatus.BLOCKED,
      score: 0,
      passed: false,
      criterionResults: [],
      evaluatedAt: new Date().toISOString(),
      durationMs: Date.now() - startTime,
      issues: [{
        severity: 'critical',
        category: 'dependency',
        message: `Gate blocked by failed dependencies: ${failedDependencies.join(', ')}`
      }],
      recommendations: [`Resolve failed gates: ${failedDependencies.join(', ')}`]
    };
  }

  /**
   * Store gate result for an execution
   */
  private storeResult(executionId: string, result: QualityGateResult): void {
    const existing = this.results.get(executionId) || [];
    existing.push(result);
    this.results.set(executionId, existing);
  }

  /**
   * Get all results for an execution
   */
  getResults(executionId: string): QualityGateResult[] {
    return this.results.get(executionId) || [];
  }

  /**
   * Get result for a specific gate
   */
  getGateResult(executionId: string, gateId: string): QualityGateResult | undefined {
    const results = this.results.get(executionId) || [];
    return results.find(r => r.gateId === gateId);
  }

  /**
   * Evaluate all gates for a phase
   */
  async evaluatePhaseGates(
    phase: ExecutionPhase,
    artifacts: ArtifactStamp[],
    executionId: string
  ): Promise<{ passed: boolean; results: QualityGateResult[] }> {
    const gates = this.getGatesForPhase(phase);
    const results: QualityGateResult[] = [];
    let allPassed = true;

    // Sort gates by dependencies
    const sortedGates = this.topologicalSort(gates);

    for (const gate of sortedGates) {
      const result = await this.evaluateGate(gate.gateId, artifacts, executionId);
      results.push(result);

      if (gate.mandatory && !result.passed) {
        allPassed = false;
      }
    }

    return { passed: allPassed, results };
  }

  /**
   * Topological sort of gates by dependencies
   */
  private topologicalSort(gates: QualityGate[]): QualityGate[] {
    const sorted: QualityGate[] = [];
    const visited = new Set<string>();
    const visiting = new Set<string>();
    const gateMap = new Map(gates.map(g => [g.gateId, g]));

    const visit = (gate: QualityGate) => {
      if (visited.has(gate.gateId)) return;
      if (visiting.has(gate.gateId)) {
        throw new Error(`Circular dependency detected in gates: ${gate.gateId}`);
      }

      visiting.add(gate.gateId);

      for (const depId of gate.dependsOn) {
        const depGate = gateMap.get(depId);
        if (depGate) {
          visit(depGate);
        }
      }

      visiting.delete(gate.gateId);
      visited.add(gate.gateId);
      sorted.push(gate);
    };

    for (const gate of gates) {
      visit(gate);
    }

    return sorted;
  }

  /**
   * Calculate overall quality score for an execution
   */
  calculateOverallScore(executionId: string): number {
    const results = this.results.get(executionId) || [];
    if (results.length === 0) return 0;

    const totalScore = results.reduce((sum, r) => sum + r.score, 0);
    return totalScore / results.length;
  }

  /**
   * Check if execution can proceed based on gates
   */
  canProceed(executionId: string): boolean {
    const results = this.results.get(executionId) || [];

    return results.every(result => {
      const gate = this.gates.get(result.gateId);
      return !gate?.mandatory || result.passed;
    });
  }

  /**
   * Clear results for an execution
   */
  clearResults(executionId: string): void {
    this.results.delete(executionId);
  }

  /**
   * Create default gates for standard SDLC phases
   */
  createDefaultGates(): QualityGate[] {
    return [
      {
        gateId: 'requirements-gate',
        name: 'Requirements Quality Gate',
        phase: ExecutionPhase.REQUIREMENTS,
        criteria: [
          {
            criterionId: 'req-completeness',
            name: 'Requirements Completeness',
            description: 'All required fields present in requirements',
            weight: 0.4,
            evaluator: 'completeness',
            config: { requiredFields: ['title', 'description', 'acceptanceCriteria'] }
          },
          {
            criterionId: 'req-consistency',
            name: 'Requirements Consistency',
            description: 'Requirements are consistent and traceable',
            weight: 0.3,
            evaluator: 'consistency',
            config: { allowNoDependencies: true }
          },
          {
            criterionId: 'req-contract',
            name: 'Contract Version',
            description: 'Contract version is properly tracked',
            weight: 0.3,
            evaluator: 'contractVersion',
            config: { allowBreaking: true }
          }
        ],
        threshold: 0.8,
        mandatory: true,
        dependsOn: []
      },
      {
        gateId: 'design-gate',
        name: 'Design Quality Gate',
        phase: ExecutionPhase.DESIGN,
        criteria: [
          {
            criterionId: 'design-completeness',
            name: 'Design Completeness',
            description: 'Design documents are complete',
            weight: 0.4,
            evaluator: 'completeness',
            config: { requiredFields: ['architecture', 'components', 'dataFlow'] }
          },
          {
            criterionId: 'design-consistency',
            name: 'Design Consistency',
            description: 'Design aligns with requirements',
            weight: 0.6,
            evaluator: 'consistency',
            config: {}
          }
        ],
        threshold: 0.8,
        mandatory: true,
        dependsOn: ['requirements-gate']
      },
      {
        gateId: 'interface-gate',
        name: 'Interface Definition Quality Gate',
        phase: ExecutionPhase.INTERFACE_DEFINITION,
        criteria: [
          {
            criterionId: 'interface-completeness',
            name: 'Interface Completeness',
            description: 'All interfaces are fully defined',
            weight: 0.5,
            evaluator: 'completeness',
            config: { requiredFields: ['methods', 'types', 'contracts'] }
          },
          {
            criterionId: 'interface-contract',
            name: 'Interface Contract',
            description: 'Contracts are version-controlled',
            weight: 0.5,
            evaluator: 'contractVersion',
            config: { allowBreaking: false }
          }
        ],
        threshold: 0.85,
        mandatory: true,
        dependsOn: ['design-gate']
      },
      {
        gateId: 'implementation-gate',
        name: 'Implementation Quality Gate',
        phase: ExecutionPhase.IMPLEMENTATION,
        criteria: [
          {
            criterionId: 'impl-compliance',
            name: 'Interface Compliance',
            description: 'Implementation follows interfaces',
            weight: 0.4,
            evaluator: 'interfaceCompliance',
            config: {}
          },
          {
            criterionId: 'impl-security',
            name: 'Security Check',
            description: 'No critical security issues',
            weight: 0.3,
            evaluator: 'security',
            config: {}
          },
          {
            criterionId: 'impl-coverage',
            name: 'Code Coverage',
            description: 'Adequate test coverage',
            weight: 0.3,
            evaluator: 'coverage',
            config: { minCoverage: 0.8 }
          }
        ],
        threshold: 0.8,
        mandatory: true,
        dependsOn: ['interface-gate']
      },
      {
        gateId: 'testing-gate',
        name: 'Testing Quality Gate',
        phase: ExecutionPhase.TESTING,
        criteria: [
          {
            criterionId: 'test-coverage',
            name: 'Test Coverage',
            description: 'Tests cover critical paths',
            weight: 0.6,
            evaluator: 'coverage',
            config: { minCoverage: 0.9 }
          },
          {
            criterionId: 'test-completeness',
            name: 'Test Completeness',
            description: 'All test types present',
            weight: 0.4,
            evaluator: 'completeness',
            config: { requiredFields: ['unit', 'integration', 'e2e'] }
          }
        ],
        threshold: 0.85,
        mandatory: true,
        dependsOn: ['implementation-gate']
      }
    ];
  }
}

// Export singleton instance
export const qualityGateService = new QualityGateService();
