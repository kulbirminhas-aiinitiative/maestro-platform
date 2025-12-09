/**
 * Critical Decision Service
 * AC-6: Implement human approval for critical decisions
 * EU AI Act Article 14 - Human approval requirement
 * EPIC: MD-2158
 */

import {
  CriticalDecision,
  DecisionApprovalRequest,
  DecisionApproval,
  DecisionRiskLevel,
  ApprovalStatus,
  ComplianceContext,
  OversightConfig,
} from './types';
import { ComplianceLogger } from './complianceLogger';

interface DatabaseClient {
  query<T>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}

interface NotificationService {
  sendAlert(recipients: string[], subject: string, message: string, priority: string): Promise<void>;
}

interface DecisionRecord {
  id: string;
  decision_type: string;
  description: string;
  risk_level: DecisionRiskLevel;
  context: string; // JSON string
  required_approvers: number;
  expires_at: Date;
  status: ApprovalStatus;
  created_at: Date;
  resolved_at?: Date;
}

interface ApprovalRecord {
  id: string;
  decision_id: string;
  approved: boolean;
  comments: string;
  approver_id: string;
  created_at: Date;
}

/**
 * Critical Decision Service
 * Requires human approval for high-impact AI decisions
 */
export class CriticalDecisionService {
  private db: DatabaseClient;
  private notifier: NotificationService;
  private logger: ComplianceLogger;
  private config: OversightConfig;

  constructor(
    db: DatabaseClient,
    notifier: NotificationService,
    logger: ComplianceLogger,
    config: OversightConfig
  ) {
    this.db = db;
    this.notifier = notifier;
    this.logger = logger;
    this.config = config;
  }

  /**
   * Submit a critical decision for approval
   */
  async submitDecision(
    decisionType: string,
    description: string,
    riskLevel: DecisionRiskLevel,
    context: Record<string, unknown>,
    requiredApprovers: number = 1
  ): Promise<CriticalDecision> {
    const decisionId = this.generateDecisionId();

    // Calculate expiry based on config
    const expiresAt = new Date();
    expiresAt.setHours(expiresAt.getHours() + this.config.approval.expiryHours);

    // Adjust required approvers based on risk level
    const actualApprovers = this.calculateRequiredApprovers(riskLevel, requiredApprovers);

    // Create decision record
    await this.db.query(
      `INSERT INTO critical_decisions
       (id, decision_type, description, risk_level, context, required_approvers, expires_at, status, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())`,
      [decisionId, decisionType, description, riskLevel, JSON.stringify(context), actualApprovers, expiresAt, 'pending']
    );

    // Notify approvers
    const approvers = await this.getApproversForRiskLevel(riskLevel);
    const subject = this.formatSubject(riskLevel, decisionType);
    const message = this.formatMessage(decisionId, decisionType, description, riskLevel, expiresAt);

    await this.notifier.sendAlert(approvers, subject, message, this.mapRiskToPriority(riskLevel));

    return {
      id: decisionId,
      decisionType,
      description,
      riskLevel,
      context,
      requiredApprovers: actualApprovers,
      expiresAt,
      status: 'pending',
      createdAt: new Date(),
    };
  }

  /**
   * Submit approval or rejection for a decision
   */
  async submitApproval(request: DecisionApprovalRequest): Promise<DecisionApproval> {
    const { decisionId, approved, comments, approverId, context } = request;

    // Get decision
    const decisionResult = await this.db.query<DecisionRecord>(
      'SELECT * FROM critical_decisions WHERE id = $1',
      [decisionId]
    );

    if (decisionResult.rows.length === 0) {
      throw new Error('Decision not found: ' + decisionId);
    }

    const decision = decisionResult.rows[0];

    if (decision.status !== 'pending') {
      throw new Error('Decision is no longer pending. Status: ' + decision.status);
    }

    if (new Date() > decision.expires_at) {
      throw new Error('Decision has expired');
    }

    // Check if approver already voted
    const existingVote = await this.db.query<ApprovalRecord>(
      'SELECT * FROM decision_approvals WHERE decision_id = $1 AND approver_id = $2',
      [decisionId, approverId]
    );

    if (existingVote.rows.length > 0) {
      throw new Error('Approver has already voted on this decision');
    }

    // Record approval
    const approvalId = this.generateApprovalId();

    await this.db.query(
      `INSERT INTO decision_approvals
       (id, decision_id, approved, comments, approver_id, created_at)
       VALUES ($1, $2, $3, $4, $5, NOW())`,
      [approvalId, decisionId, approved, comments, approverId]
    );

    // Log to compliance audit
    const auditEntry = await this.logger.logApproval(
      approverId,
      decisionId,
      approved,
      comments,
      decision.risk_level,
      context
    );

    // Check if decision is now resolved
    await this.checkAndUpdateDecisionStatus(decisionId);

    return {
      id: approvalId,
      decisionId,
      approved,
      comments,
      approverId,
      createdAt: new Date(),
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Check if decision has enough approvals and update status
   */
  private async checkAndUpdateDecisionStatus(decisionId: string): Promise<void> {
    const decision = await this.db.query<DecisionRecord>(
      'SELECT * FROM critical_decisions WHERE id = $1',
      [decisionId]
    );

    if (decision.rows.length === 0) return;

    const decisionRecord = decision.rows[0];

    // Get all approvals
    const approvals = await this.db.query<ApprovalRecord>(
      'SELECT * FROM decision_approvals WHERE decision_id = $1',
      [decisionId]
    );

    const approvedCount = approvals.rows.filter(a => a.approved).length;
    const rejectedCount = approvals.rows.filter(a => !a.approved).length;

    let newStatus: ApprovalStatus = 'pending';

    // Check if approved (enough approvals)
    if (approvedCount >= decisionRecord.required_approvers) {
      newStatus = 'approved';
    }
    // Check if rejected (any rejection for critical/high, or majority for others)
    else if (decisionRecord.risk_level === 'critical' || decisionRecord.risk_level === 'high') {
      if (rejectedCount > 0) {
        newStatus = 'rejected';
      }
    } else if (rejectedCount >= decisionRecord.required_approvers) {
      newStatus = 'rejected';
    }

    if (newStatus !== 'pending') {
      await this.db.query(
        `UPDATE critical_decisions
         SET status = $1, resolved_at = NOW()
         WHERE id = $2`,
        [newStatus, decisionId]
      );
    }
  }

  /**
   * Get decision by ID
   */
  async getDecision(decisionId: string): Promise<CriticalDecision | null> {
    const result = await this.db.query<DecisionRecord>(
      'SELECT * FROM critical_decisions WHERE id = $1',
      [decisionId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      decisionType: row.decision_type,
      description: row.description,
      riskLevel: row.risk_level,
      context: JSON.parse(row.context || '{}'),
      requiredApprovers: row.required_approvers,
      expiresAt: row.expires_at,
      status: row.status,
      createdAt: row.created_at,
      resolvedAt: row.resolved_at,
    };
  }

  /**
   * Get approval status for a decision
   */
  async getApprovalStatus(decisionId: string): Promise<{
    decision: CriticalDecision;
    approvals: DecisionApproval[];
    approvedCount: number;
    rejectedCount: number;
    pendingCount: number;
  }> {
    const decision = await this.getDecision(decisionId);
    if (!decision) {
      throw new Error('Decision not found: ' + decisionId);
    }

    const approvals = await this.db.query<ApprovalRecord>(
      'SELECT * FROM decision_approvals WHERE decision_id = $1 ORDER BY created_at ASC',
      [decisionId]
    );

    const approvedCount = approvals.rows.filter(a => a.approved).length;
    const rejectedCount = approvals.rows.filter(a => !a.approved).length;
    const pendingCount = decision.requiredApprovers - approvedCount;

    return {
      decision,
      approvals: approvals.rows.map(row => ({
        id: row.id,
        decisionId: row.decision_id,
        approved: row.approved,
        comments: row.comments,
        approverId: row.approver_id,
        createdAt: row.created_at,
        auditLogId: '',
      })),
      approvedCount,
      rejectedCount,
      pendingCount: Math.max(0, pendingCount),
    };
  }

  /**
   * List pending decisions
   */
  async listPendingDecisions(riskLevel?: DecisionRiskLevel): Promise<CriticalDecision[]> {
    let sql = `SELECT * FROM critical_decisions WHERE status = 'pending' AND expires_at > NOW()`;
    const params: unknown[] = [];

    if (riskLevel) {
      sql += ' AND risk_level = $1';
      params.push(riskLevel);
    }

    sql += ' ORDER BY risk_level DESC, created_at ASC';

    const result = await this.db.query<DecisionRecord>(sql, params);

    return result.rows.map(row => ({
      id: row.id,
      decisionType: row.decision_type,
      description: row.description,
      riskLevel: row.risk_level,
      context: JSON.parse(row.context || '{}'),
      requiredApprovers: row.required_approvers,
      expiresAt: row.expires_at,
      status: row.status,
      createdAt: row.created_at,
      resolvedAt: row.resolved_at,
    }));
  }

  /**
   * Expire overdue decisions
   */
  async expireOverdueDecisions(): Promise<number> {
    const result = await this.db.query<{ count: number }>(
      `WITH updated AS (
        UPDATE critical_decisions
        SET status = 'expired', resolved_at = NOW()
        WHERE status = 'pending' AND expires_at <= NOW()
        RETURNING *
      )
      SELECT COUNT(*) as count FROM updated`
    );

    return result.rows[0]?.count || 0;
  }

  /**
   * Auto-approve low-risk decisions after timeout
   */
  async autoApproveEligibleDecisions(): Promise<number> {
    // Only auto-approve low risk decisions that have been pending for a threshold
    const autoApproveThreshold = new Date();
    autoApproveThreshold.setHours(autoApproveThreshold.getHours() - 24); // 24 hours

    const result = await this.db.query<{ count: number }>(
      `WITH updated AS (
        UPDATE critical_decisions
        SET status = 'auto_approved', resolved_at = NOW()
        WHERE status = 'pending'
          AND risk_level = 'low'
          AND created_at <= $1
          AND expires_at > NOW()
        RETURNING *
      )
      SELECT COUNT(*) as count FROM updated`,
      [autoApproveThreshold]
    );

    return result.rows[0]?.count || 0;
  }

  /**
   * Calculate required approvers based on risk level
   */
  private calculateRequiredApprovers(riskLevel: DecisionRiskLevel, requested: number): number {
    const minimums: Record<DecisionRiskLevel, number> = {
      low: 1,
      medium: 1,
      high: 2,
      critical: 3,
    };

    return Math.max(minimums[riskLevel], requested);
  }

  /**
   * Get approvers for a risk level
   */
  private async getApproversForRiskLevel(riskLevel: DecisionRiskLevel): Promise<string[]> {
    const result = await this.db.query<{ email: string }>(
      `SELECT email FROM decision_approvers
       WHERE risk_level_threshold <= $1 AND active = true
       ORDER BY risk_level_threshold DESC`,
      [this.riskLevelToNumber(riskLevel)]
    );

    return result.rows.map(r => r.email);
  }

  /**
   * Convert risk level to numeric for comparison
   */
  private riskLevelToNumber(level: DecisionRiskLevel): number {
    const levels: Record<DecisionRiskLevel, number> = {
      low: 1,
      medium: 2,
      high: 3,
      critical: 4,
    };
    return levels[level];
  }

  /**
   * Map risk level to notification priority
   */
  private mapRiskToPriority(riskLevel: DecisionRiskLevel): string {
    const mapping: Record<DecisionRiskLevel, string> = {
      low: 'low',
      medium: 'medium',
      high: 'high',
      critical: 'critical',
    };
    return mapping[riskLevel];
  }

  /**
   * Format notification subject
   */
  private formatSubject(riskLevel: DecisionRiskLevel, decisionType: string): string {
    return '[' + riskLevel.toUpperCase() + ' RISK] Approval Required: ' + decisionType;
  }

  /**
   * Format notification message
   */
  private formatMessage(
    decisionId: string,
    decisionType: string,
    description: string,
    riskLevel: DecisionRiskLevel,
    expiresAt: Date
  ): string {
    return [
      'Decision ID: ' + decisionId,
      'Type: ' + decisionType,
      'Risk Level: ' + riskLevel.toUpperCase(),
      'Description: ' + description,
      'Expires: ' + expiresAt.toISOString(),
      '',
      'Please review and submit your approval or rejection.',
    ].join('\n');
  }

  private generateDecisionId(): string {
    return 'dec_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }

  private generateApprovalId(): string {
    return 'apr_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }
}

export default CriticalDecisionService;
