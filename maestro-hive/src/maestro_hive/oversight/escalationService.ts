/**
 * Escalation Service
 * AC-3: Create escalation path for edge cases
 * EU AI Act Article 14 - Human escalation capability
 * EPIC: MD-2158
 */

import {
  EscalationRequest,
  Escalation,
  EscalationTier,
  EscalationPriority,
  EscalationStatus,
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

interface EscalationRecord {
  id: string;
  context_id: string;
  tier: EscalationTier;
  reason: string;
  priority: EscalationPriority;
  status: EscalationStatus;
  assigned_to?: string;
  resolution?: string;
  created_at: Date;
  sla_deadline: Date;
  resolved_at?: Date;
}

/**
 * Escalation Service
 * Provides tiered escalation paths for edge cases requiring human intervention
 */
export class EscalationService {
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
   * Create a new escalation
   */
  async createEscalation(request: EscalationRequest): Promise<Escalation> {
    const { contextId, tier, reason, priority, context } = request;

    // Calculate SLA deadline based on tier
    const slaDeadline = this.calculateSlaDeadline(tier);

    // Generate escalation ID
    const escalationId = this.generateEscalationId();

    // Insert escalation record
    await this.db.query(
      `INSERT INTO escalations
       (id, context_id, tier, reason, priority, status, sla_deadline, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())`,
      [escalationId, contextId, tier, reason, priority, 'pending', slaDeadline]
    );

    // Get recipients for this tier
    const recipients = await this.getEscalationRecipients(tier);

    // Send notification
    const subject = this.formatSubject(priority, tier, reason);
    const message = this.formatMessage(escalationId, contextId, tier, reason, priority, slaDeadline);

    await this.notifier.sendAlert(recipients, subject, message, priority);

    // Log to compliance audit
    const auditEntry = await this.logger.logEscalation(
      context?.userId || 'system',
      contextId,
      tier,
      reason,
      priority,
      context
    );

    return {
      id: escalationId,
      contextId,
      tier,
      reason,
      priority,
      status: 'pending',
      createdAt: new Date(),
      slaDeadline,
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Assign escalation to a handler
   */
  async assignEscalation(escalationId: string, assigneeId: string): Promise<void> {
    const result = await this.db.query<EscalationRecord>(
      'SELECT * FROM escalations WHERE id = $1',
      [escalationId]
    );

    if (result.rows.length === 0) {
      throw new Error('Escalation not found: ' + escalationId);
    }

    const escalation = result.rows[0];
    if (escalation.status !== 'pending') {
      throw new Error('Can only assign pending escalations. Current status: ' + escalation.status);
    }

    await this.db.query(
      `UPDATE escalations
       SET status = 'assigned', assigned_to = $1, updated_at = NOW()
       WHERE id = $2`,
      [assigneeId, escalationId]
    );

    await this.logger.logAction('escalate', assigneeId, escalationId, {
      action: 'assign',
      assigneeId,
      actionType: 'escalation_assigned',
    });
  }

  /**
   * Mark escalation as in progress
   */
  async startEscalation(escalationId: string, handlerId: string): Promise<void> {
    await this.db.query(
      `UPDATE escalations
       SET status = 'in_progress', updated_at = NOW()
       WHERE id = $1 AND assigned_to = $2`,
      [escalationId, handlerId]
    );

    await this.logger.logAction('escalate', handlerId, escalationId, {
      action: 'start',
      actionType: 'escalation_started',
    });
  }

  /**
   * Resolve an escalation
   */
  async resolveEscalation(
    escalationId: string,
    resolverId: string,
    resolution: string
  ): Promise<void> {
    const result = await this.db.query<EscalationRecord>(
      'SELECT * FROM escalations WHERE id = $1',
      [escalationId]
    );

    if (result.rows.length === 0) {
      throw new Error('Escalation not found: ' + escalationId);
    }

    const escalation = result.rows[0];
    if (escalation.status === 'resolved' || escalation.status === 'expired') {
      throw new Error('Escalation already closed. Status: ' + escalation.status);
    }

    await this.db.query(
      `UPDATE escalations
       SET status = 'resolved', resolution = $1, resolved_at = NOW(), updated_at = NOW()
       WHERE id = $2`,
      [resolution, escalationId]
    );

    await this.logger.logAction('escalate', resolverId, escalationId, {
      action: 'resolve',
      resolution,
      actionType: 'escalation_resolved',
    });
  }

  /**
   * Escalate to next tier
   */
  async escalateToNextTier(escalationId: string, reason: string): Promise<Escalation | null> {
    const result = await this.db.query<EscalationRecord>(
      'SELECT * FROM escalations WHERE id = $1',
      [escalationId]
    );

    if (result.rows.length === 0) {
      throw new Error('Escalation not found: ' + escalationId);
    }

    const escalation = result.rows[0];

    // Check if already at max tier
    if (escalation.tier >= 3) {
      return null; // Cannot escalate beyond tier 3
    }

    const nextTier = (escalation.tier + 1) as EscalationTier;

    // Create new escalation at next tier
    return this.createEscalation({
      contextId: escalation.context_id,
      tier: nextTier,
      reason: 'Escalated from Tier ' + escalation.tier + ': ' + reason,
      priority: this.upgradePriority(escalation.priority),
    });
  }

  /**
   * Get escalation by ID
   */
  async getEscalation(escalationId: string): Promise<Escalation | null> {
    const result = await this.db.query<EscalationRecord>(
      'SELECT * FROM escalations WHERE id = $1',
      [escalationId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      contextId: row.context_id,
      tier: row.tier,
      reason: row.reason,
      priority: row.priority,
      status: row.status,
      assignedTo: row.assigned_to,
      resolution: row.resolution,
      createdAt: row.created_at,
      slaDeadline: row.sla_deadline,
      resolvedAt: row.resolved_at,
      auditLogId: '',
    };
  }

  /**
   * List pending escalations by tier
   */
  async listPendingEscalations(tier?: EscalationTier): Promise<Escalation[]> {
    let sql = `SELECT * FROM escalations WHERE status IN ('pending', 'assigned', 'in_progress')`;
    const params: unknown[] = [];

    if (tier !== undefined) {
      sql += ' AND tier = $1';
      params.push(tier);
    }

    sql += ' ORDER BY priority DESC, created_at ASC';

    const result = await this.db.query<EscalationRecord>(sql, params);

    return result.rows.map(row => ({
      id: row.id,
      contextId: row.context_id,
      tier: row.tier,
      reason: row.reason,
      priority: row.priority,
      status: row.status,
      assignedTo: row.assigned_to,
      resolution: row.resolution,
      createdAt: row.created_at,
      slaDeadline: row.sla_deadline,
      resolvedAt: row.resolved_at,
      auditLogId: '',
    }));
  }

  /**
   * Check and expire overdue escalations
   */
  async expireOverdueEscalations(): Promise<number> {
    const result = await this.db.query<{ count: number }>(
      `WITH updated AS (
        UPDATE escalations
        SET status = 'expired', updated_at = NOW()
        WHERE status IN ('pending', 'assigned')
          AND sla_deadline < NOW()
        RETURNING *
      )
      SELECT COUNT(*) as count FROM updated`
    );

    return result.rows[0]?.count || 0;
  }

  /**
   * Calculate SLA deadline based on tier
   */
  private calculateSlaDeadline(tier: EscalationTier): Date {
    const now = new Date();
    let slaMins: number;

    switch (tier) {
      case 1:
        slaMins = this.config.escalation.tier1SlaMins;
        break;
      case 2:
        slaMins = this.config.escalation.tier2SlaMins;
        break;
      case 3:
        slaMins = this.config.escalation.tier3SlaMins;
        break;
      default:
        slaMins = 60; // Default to 1 hour
    }

    return new Date(now.getTime() + slaMins * 60 * 1000);
  }

  /**
   * Get recipients for escalation tier
   */
  private async getEscalationRecipients(tier: EscalationTier): Promise<string[]> {
    const result = await this.db.query<{ email: string }>(
      `SELECT email FROM escalation_recipients
       WHERE tier <= $1 AND active = true
       ORDER BY tier DESC`,
      [tier]
    );

    return result.rows.map(r => r.email);
  }

  /**
   * Upgrade priority when escalating
   */
  private upgradePriority(current: EscalationPriority): EscalationPriority {
    const priorities: EscalationPriority[] = ['low', 'medium', 'high', 'critical'];
    const currentIndex = priorities.indexOf(current);
    return priorities[Math.min(currentIndex + 1, priorities.length - 1)];
  }

  /**
   * Format notification subject
   */
  private formatSubject(priority: EscalationPriority, tier: EscalationTier, reason: string): string {
    return '[' + priority.toUpperCase() + '] Tier ' + tier + ' Escalation: ' + reason.substring(0, 50);
  }

  /**
   * Format notification message
   */
  private formatMessage(
    escalationId: string,
    contextId: string,
    tier: EscalationTier,
    reason: string,
    priority: EscalationPriority,
    slaDeadline: Date
  ): string {
    return [
      'Escalation ID: ' + escalationId,
      'Context: ' + contextId,
      'Tier: ' + tier,
      'Priority: ' + priority.toUpperCase(),
      'Reason: ' + reason,
      'SLA Deadline: ' + slaDeadline.toISOString(),
      '',
      'Please respond within the SLA window.',
    ].join('\n');
  }

  private generateEscalationId(): string {
    return 'esc_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }
}

export default EscalationService;
