/**
 * Workflow Pause Service
 * AC-5: Add pause and review capability to workflows
 * EU AI Act Article 14 - Human review capability
 * EPIC: MD-2158
 */

import {
  WorkflowPauseRequest,
  WorkflowPauseResult,
  WorkflowResumeRequest,
  WorkflowCheckpoint,
  WorkflowState,
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

interface WorkflowRecord {
  id: string;
  state: WorkflowState;
  current_step: number;
  current_step_name: string;
  context_data: string; // JSON string
  last_pause_id?: string;
}

interface CheckpointRecord {
  id: string;
  workflow_id: string;
  step_index: number;
  step_name: string;
  state: string; // JSON string
  captured_at: Date;
}

interface PauseRecord {
  id: string;
  workflow_id: string;
  reason: string;
  operator_id: string;
  checkpoint_id?: string;
  created_at: Date;
}

/**
 * Workflow Pause Service
 * Provides pause, checkpoint, and resume capabilities for AI workflows
 */
export class WorkflowPauseService {
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
   * Pause a running workflow
   */
  async pauseWorkflow(request: WorkflowPauseRequest): Promise<WorkflowPauseResult> {
    const { workflowId, reason, operatorId, captureCheckpoint, context } = request;

    // Get current workflow state
    const workflowResult = await this.db.query<WorkflowRecord>(
      'SELECT * FROM workflows WHERE id = $1',
      [workflowId]
    );

    if (workflowResult.rows.length === 0) {
      throw new Error('Workflow not found: ' + workflowId);
    }

    const workflow = workflowResult.rows[0];
    const previousState = workflow.state;

    if (previousState !== 'running') {
      throw new Error('Can only pause running workflows. Current state: ' + previousState);
    }

    // Generate pause ID
    const pauseId = this.generatePauseId();
    let checkpoint: WorkflowCheckpoint | undefined;

    // Capture checkpoint if requested
    if (captureCheckpoint) {
      checkpoint = await this.captureCheckpoint(workflow);
    }

    // Update workflow state
    await this.db.query(
      `UPDATE workflows
       SET state = 'paused', last_pause_id = $1, updated_at = NOW()
       WHERE id = $2`,
      [pauseId, workflowId]
    );

    // Record pause action
    await this.db.query(
      `INSERT INTO workflow_pauses
       (id, workflow_id, reason, operator_id, checkpoint_id, created_at)
       VALUES ($1, $2, $3, $4, $5, NOW())`,
      [pauseId, workflowId, reason, operatorId, checkpoint?.id || null]
    );

    // Send pause signal to workflow engine
    await this.mq.publish('workflow.control', {
      type: 'pause',
      workflowId,
      pauseId,
      command: 'PAUSE',
      timestamp: new Date().toISOString(),
    });

    // Log to compliance audit
    const auditEntry = await this.logger.logWorkflowControl(
      operatorId,
      workflowId,
      'pause',
      reason,
      checkpoint?.id,
      context
    );

    return {
      success: true,
      workflowId,
      previousState,
      checkpoint,
      pauseId,
      timestamp: new Date(),
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Resume a paused workflow
   */
  async resumeWorkflow(request: WorkflowResumeRequest): Promise<WorkflowPauseResult> {
    const { workflowId, pauseId, operatorId, fromCheckpoint, reviewNotes } = request;

    // Verify pause record exists
    const pauseResult = await this.db.query<PauseRecord>(
      'SELECT * FROM workflow_pauses WHERE id = $1',
      [pauseId]
    );

    if (pauseResult.rows.length === 0) {
      throw new Error('Pause record not found: ' + pauseId);
    }

    const pause = pauseResult.rows[0];
    if (pause.workflow_id !== workflowId) {
      throw new Error('Pause record does not match workflow: ' + workflowId);
    }

    // Get workflow
    const workflowResult = await this.db.query<WorkflowRecord>(
      'SELECT * FROM workflows WHERE id = $1',
      [workflowId]
    );

    if (workflowResult.rows.length === 0) {
      throw new Error('Workflow not found: ' + workflowId);
    }

    const workflow = workflowResult.rows[0];
    const previousState = workflow.state;

    if (previousState !== 'paused') {
      throw new Error('Can only resume paused workflows. Current state: ' + previousState);
    }

    // If resuming from checkpoint, restore state
    let checkpoint: WorkflowCheckpoint | undefined;
    if (fromCheckpoint) {
      checkpoint = await this.restoreFromCheckpoint(workflowId, fromCheckpoint);
    }

    // Update workflow state
    await this.db.query(
      `UPDATE workflows
       SET state = 'running', last_pause_id = NULL, updated_at = NOW()
       WHERE id = $1`,
      [workflowId]
    );

    // Generate resume ID
    const resumeId = this.generatePauseId();

    // Record resume action
    await this.db.query(
      `INSERT INTO workflow_resumes
       (id, workflow_id, pause_id, operator_id, from_checkpoint, review_notes, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, NOW())`,
      [resumeId, workflowId, pauseId, operatorId, fromCheckpoint || null, reviewNotes || null]
    );

    // Send resume signal to workflow engine
    await this.mq.publish('workflow.control', {
      type: 'resume',
      workflowId,
      resumeId,
      pauseId,
      fromCheckpoint: fromCheckpoint || null,
      command: 'RESUME',
      timestamp: new Date().toISOString(),
    });

    // Log to compliance audit
    const auditEntry = await this.logger.logWorkflowControl(
      operatorId,
      workflowId,
      'resume',
      reviewNotes || 'Workflow resumed after review',
      fromCheckpoint
    );

    return {
      success: true,
      workflowId,
      previousState,
      checkpoint,
      pauseId: resumeId,
      timestamp: new Date(),
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Capture current workflow state as checkpoint
   */
  async captureCheckpoint(workflow: WorkflowRecord): Promise<WorkflowCheckpoint> {
    const checkpointId = this.generateCheckpointId();

    const checkpoint: WorkflowCheckpoint = {
      id: checkpointId,
      workflowId: workflow.id,
      stepIndex: workflow.current_step,
      stepName: workflow.current_step_name,
      state: JSON.parse(workflow.context_data || '{}'),
      capturedAt: new Date(),
    };

    await this.db.query(
      `INSERT INTO workflow_checkpoints
       (id, workflow_id, step_index, step_name, state, captured_at)
       VALUES ($1, $2, $3, $4, $5, NOW())`,
      [checkpointId, workflow.id, workflow.current_step, workflow.current_step_name, workflow.context_data]
    );

    return checkpoint;
  }

  /**
   * Restore workflow from checkpoint
   */
  async restoreFromCheckpoint(workflowId: string, checkpointId: string): Promise<WorkflowCheckpoint> {
    const result = await this.db.query<CheckpointRecord>(
      'SELECT * FROM workflow_checkpoints WHERE id = $1 AND workflow_id = $2',
      [checkpointId, workflowId]
    );

    if (result.rows.length === 0) {
      throw new Error('Checkpoint not found: ' + checkpointId);
    }

    const cp = result.rows[0];

    // Restore workflow state from checkpoint
    await this.db.query(
      `UPDATE workflows
       SET current_step = $1, current_step_name = $2, context_data = $3, updated_at = NOW()
       WHERE id = $4`,
      [cp.step_index, cp.step_name, cp.state, workflowId]
    );

    return {
      id: cp.id,
      workflowId: cp.workflow_id,
      stepIndex: cp.step_index,
      stepName: cp.step_name,
      state: JSON.parse(cp.state || '{}'),
      capturedAt: cp.captured_at,
    };
  }

  /**
   * List checkpoints for a workflow
   */
  async listCheckpoints(workflowId: string): Promise<WorkflowCheckpoint[]> {
    const result = await this.db.query<CheckpointRecord>(
      `SELECT * FROM workflow_checkpoints
       WHERE workflow_id = $1
       ORDER BY captured_at DESC`,
      [workflowId]
    );

    return result.rows.map(row => ({
      id: row.id,
      workflowId: row.workflow_id,
      stepIndex: row.step_index,
      stepName: row.step_name,
      state: JSON.parse(row.state || '{}'),
      capturedAt: row.captured_at,
    }));
  }

  /**
   * Get workflow status
   */
  async getWorkflowStatus(workflowId: string): Promise<{
    workflowId: string;
    state: WorkflowState;
    currentStep: number;
    currentStepName: string;
    lastPauseId?: string;
  }> {
    const result = await this.db.query<WorkflowRecord>(
      'SELECT * FROM workflows WHERE id = $1',
      [workflowId]
    );

    if (result.rows.length === 0) {
      throw new Error('Workflow not found: ' + workflowId);
    }

    const workflow = result.rows[0];
    return {
      workflowId: workflow.id,
      state: workflow.state,
      currentStep: workflow.current_step,
      currentStepName: workflow.current_step_name,
      lastPauseId: workflow.last_pause_id,
    };
  }

  /**
   * List paused workflows
   */
  async listPausedWorkflows(): Promise<Array<{
    workflowId: string;
    pauseId: string;
    reason: string;
    operatorId: string;
    pausedAt: Date;
  }>> {
    const result = await this.db.query<{
      id: string;
      last_pause_id: string;
    }>(
      `SELECT w.id, w.last_pause_id
       FROM workflows w
       WHERE w.state = 'paused' AND w.last_pause_id IS NOT NULL`
    );

    const paused = [];
    for (const row of result.rows) {
      const pauseResult = await this.db.query<PauseRecord>(
        'SELECT * FROM workflow_pauses WHERE id = $1',
        [row.last_pause_id]
      );

      if (pauseResult.rows.length > 0) {
        const pause = pauseResult.rows[0];
        paused.push({
          workflowId: row.id,
          pauseId: pause.id,
          reason: pause.reason,
          operatorId: pause.operator_id,
          pausedAt: pause.created_at,
        });
      }
    }

    return paused;
  }

  private generatePauseId(): string {
    return 'pse_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }

  private generateCheckpointId(): string {
    return 'chk_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }
}

export default WorkflowPauseService;
