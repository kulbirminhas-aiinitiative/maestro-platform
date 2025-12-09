/**
 * Agent Override Service
 * AC-1: Implement agent override mechanism
 * EU AI Act Article 14 - Human intervention capability
 * EPIC: MD-2158
 */

import {
  AgentOverrideRequest,
  AgentOverrideResult,
  AgentResumeRequest,
  AgentState,
  ComplianceContext,
  OversightConfig,
} from './types';
import { ComplianceLogger } from './complianceLogger';

interface DatabaseClient {
  query<T>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}

interface MessageQueue {
  publish(topic: string, message: unknown): Promise<void>;
}

interface AgentRecord {
  id: string;
  state: AgentState;
  last_override_id?: string;
}

/**
 * Agent Override Service
 * Provides kill-switch capability for AI agents with full audit trail
 */
export class AgentOverrideService {
  private db: DatabaseClient;
  private mq: MessageQueue;
  private logger: ComplianceLogger;
  private config: OversightConfig;

  constructor(
    db: DatabaseClient,
    mq: MessageQueue,
    logger: ComplianceLogger,
    config: OversightConfig
  ) {
    this.db = db;
    this.mq = mq;
    this.logger = logger;
    this.config = config;
  }

  /**
   * Override (stop) an agent immediately
   * This is the kill-switch capability required by EU AI Act Article 14
   */
  async overrideAgent(request: AgentOverrideRequest): Promise<AgentOverrideResult> {
    const { agentId, reason, operatorId, severity, context } = request;

    // Get current agent state
    const agentResult = await this.db.query<AgentRecord>(
      'SELECT id, state, last_override_id FROM agents WHERE id = $1',
      [agentId]
    );

    if (agentResult.rows.length === 0) {
      throw new Error(`Agent not found: ${agentId}`);
    }

    const agent = agentResult.rows[0];
    const previousState = agent.state;

    // Determine new state based on severity
    const newState: AgentState = severity === 'hard' ? 'terminated' : 'stopped';

    // Generate override ID
    const overrideId = this.generateOverrideId();

    // Update agent state in database
    await this.db.query(
      `UPDATE agents 
       SET state = $1, last_override_id = $2, updated_at = NOW()
       WHERE id = $3`,
      [newState, overrideId, agentId]
    );

    // Record override in oversight_actions table
    await this.db.query(
      `INSERT INTO oversight_actions (id, action_type, target_id, operator_id, reason, severity, previous_state, new_state, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())`,
      [overrideId, 'override', agentId, operatorId, reason, severity, previousState, newState]
    );

    // Send immediate stop signal via message queue
    await this.mq.publish('agent.control', {
      type: 'override',
      agentId,
      overrideId,
      severity,
      command: severity === 'hard' ? 'TERMINATE' : 'STOP',
      timestamp: new Date().toISOString(),
    });

    // Log to compliance audit system
    const auditEntry = await this.logger.logOverride(
      operatorId,
      agentId,
      reason,
      severity,
      true,
      context
    );

    return {
      success: true,
      agentId,
      previousState,
      newState,
      overrideId,
      timestamp: new Date(),
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Resume an agent after override review
   */
  async resumeAgent(request: AgentResumeRequest): Promise<AgentOverrideResult> {
    const { agentId, overrideId, operatorId, reviewNotes } = request;

    // Verify the override exists and matches
    const overrideResult = await this.db.query<{ id: string; target_id: string; new_state: AgentState }>(
      'SELECT id, target_id, new_state FROM oversight_actions WHERE id = $1 AND action_type = $2',
      [overrideId, 'override']
    );

    if (overrideResult.rows.length === 0) {
      throw new Error(`Override not found: ${overrideId}`);
    }

    const override = overrideResult.rows[0];
    if (override.target_id !== agentId) {
      throw new Error(`Override ${overrideId} does not match agent ${agentId}`);
    }

    // Cannot resume a terminated agent
    if (override.new_state === 'terminated') {
      throw new Error(`Cannot resume terminated agent ${agentId}. Create new agent instance instead.`);
    }

    // Get current agent state
    const agentResult = await this.db.query<AgentRecord>(
      'SELECT id, state FROM agents WHERE id = $1',
      [agentId]
    );

    if (agentResult.rows.length === 0) {
      throw new Error(`Agent not found: ${agentId}`);
    }

    const agent = agentResult.rows[0];
    const previousState = agent.state;

    // Resume agent
    const newState: AgentState = 'running';

    await this.db.query(
      `UPDATE agents 
       SET state = $1, last_override_id = NULL, updated_at = NOW()
       WHERE id = $2`,
      [newState, agentId]
    );

    // Record resume action
    const resumeId = this.generateOverrideId();
    await this.db.query(
      `INSERT INTO oversight_actions (id, action_type, target_id, operator_id, reason, previous_state, new_state, related_override_id, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())`,
      [resumeId, 'resume', agentId, operatorId, reviewNotes || 'Agent resumed after review', previousState, newState, overrideId]
    );

    // Send resume signal
    await this.mq.publish('agent.control', {
      type: 'resume',
      agentId,
      resumeId,
      relatedOverrideId: overrideId,
      command: 'START',
      timestamp: new Date().toISOString(),
    });

    // Log to audit
    const auditEntry = await this.logger.logAction(
      'resume',
      operatorId,
      agentId,
      { overrideId, reviewNotes, actionType: 'agent_resume' }
    );

    return {
      success: true,
      agentId,
      previousState,
      newState,
      overrideId: resumeId,
      timestamp: new Date(),
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Get current status of an agent
   */
  async getAgentStatus(agentId: string): Promise<{
    agentId: string;
    state: AgentState;
    lastOverrideId?: string;
    lastOverrideTime?: Date;
  }> {
    const result = await this.db.query<{
      id: string;
      state: AgentState;
      last_override_id?: string;
      updated_at: Date;
    }>(
      'SELECT id, state, last_override_id, updated_at FROM agents WHERE id = $1',
      [agentId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Agent not found: ${agentId}`);
    }

    const agent = result.rows[0];
    return {
      agentId: agent.id,
      state: agent.state,
      lastOverrideId: agent.last_override_id,
      lastOverrideTime: agent.last_override_id ? agent.updated_at : undefined,
    };
  }

  /**
   * List all active overrides
   */
  async listActiveOverrides(): Promise<Array<{
    overrideId: string;
    agentId: string;
    operatorId: string;
    reason: string;
    severity: string;
    createdAt: Date;
  }>> {
    const result = await this.db.query<{
      id: string;
      target_id: string;
      operator_id: string;
      reason: string;
      severity: string;
      created_at: Date;
    }>(
      `SELECT oa.id, oa.target_id, oa.operator_id, oa.reason, oa.severity, oa.created_at
       FROM oversight_actions oa
       JOIN agents a ON oa.target_id = a.id
       WHERE oa.action_type = 'override'
         AND a.state IN ('stopped', 'terminated')
         AND a.last_override_id = oa.id
       ORDER BY oa.created_at DESC`
    );

    return result.rows.map(row => ({
      overrideId: row.id,
      agentId: row.target_id,
      operatorId: row.operator_id,
      reason: row.reason,
      severity: row.severity,
      createdAt: row.created_at,
    }));
  }

  /**
   * Emergency stop all agents
   */
  async emergencyStopAll(operatorId: string, reason: string): Promise<number> {
    // Get all running agents
    const runningAgents = await this.db.query<{ id: string }>(
      "SELECT id FROM agents WHERE state = 'running'"
    );

    let stoppedCount = 0;

    for (const agent of runningAgents.rows) {
      try {
        await this.overrideAgent({
          agentId: agent.id,
          reason: `EMERGENCY STOP: ${reason}`,
          operatorId,
          severity: 'hard',
        });
        stoppedCount++;
      } catch (error) {
        console.error(`Failed to stop agent ${agent.id}:`, error);
      }
    }

    return stoppedCount;
  }

  private generateOverrideId(): string {
    return 'ovr_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }
}

export default AgentOverrideService;
