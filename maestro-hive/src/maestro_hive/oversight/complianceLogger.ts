/**
 * Compliance Logger Service
 * Provides PII-masked audit logging for all oversight actions
 * EPIC: MD-2158
 */

import { AuditLogEntry, OversightActionType, ComplianceContext } from './types';

/**
 * PII patterns to mask in logs
 */
const PII_PATTERNS = [
  { pattern: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, replacement: '[EMAIL_MASKED]' },
  { pattern: /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, replacement: '[PHONE_MASKED]' },
  { pattern: /\b\d{3}[-]?\d{2}[-]?\d{4}\b/g, replacement: '[SSN_MASKED]' },
  { pattern: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g, replacement: '[CARD_MASKED]' },
  { pattern: /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, replacement: '[IP_MASKED]' },
];

interface KafkaProducer {
  send(topic: string, message: string): Promise<void>;
}

interface DatabaseClient {
  query<T>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}

/**
 * Compliance Logger with PII masking
 */
export class ComplianceLogger {
  private kafka: KafkaProducer;
  private db: DatabaseClient;
  private auditTopic: string;

  constructor(kafka: KafkaProducer, db: DatabaseClient, auditTopic: string = 'compliance.oversight.audit') {
    this.kafka = kafka;
    this.db = db;
    this.auditTopic = auditTopic;
  }

  /**
   * Log an oversight action with PII masking
   */
  async logAction(
    action: OversightActionType,
    actor: string,
    target: string,
    details: Record<string, unknown>,
    context?: ComplianceContext
  ): Promise<AuditLogEntry> {
    const id = this.generateId();
    const timestamp = new Date();

    // Mask PII in all string fields
    const maskedDetails = this.maskPII(details);
    const maskedActor = this.maskPIIString(actor);
    const maskedTarget = this.maskPIIString(target);

    const entry: AuditLogEntry = {
      id,
      contextId: context?.sessionId || 'unknown',
      action,
      actor: maskedActor,
      target: maskedTarget,
      details: maskedDetails,
      timestamp,
      piiMasked: true,
    };

    // Persist to database
    await this.persistToDatabase(entry);

    // Send to Kafka for real-time streaming
    await this.sendToKafka(entry);

    return entry;
  }

  /**
   * Log an override action (AC-1)
   */
  async logOverride(
    operatorId: string,
    agentId: string,
    reason: string,
    severity: string,
    result: boolean,
    context?: ComplianceContext
  ): Promise<AuditLogEntry> {
    return this.logAction('override', operatorId, agentId, {
      reason,
      severity,
      result,
      actionType: 'agent_override',
    }, context);
  }

  /**
   * Log a bypass action (AC-2)
   */
  async logBypass(
    approverId: string,
    gateId: string,
    justification: string,
    scope: string,
    expiry: Date,
    context?: ComplianceContext
  ): Promise<AuditLogEntry> {
    return this.logAction('bypass', approverId, gateId, {
      justification,
      scope,
      expiry: expiry.toISOString(),
      actionType: 'quality_gate_bypass',
    }, context);
  }

  /**
   * Log an escalation action (AC-3)
   */
  async logEscalation(
    escalatorId: string,
    contextId: string,
    tier: number,
    reason: string,
    priority: string,
    context?: ComplianceContext
  ): Promise<AuditLogEntry> {
    return this.logAction('escalate', escalatorId, contextId, {
      tier,
      reason,
      priority,
      actionType: 'escalation',
    }, context);
  }

  /**
   * Log a contract amendment action (AC-4)
   */
  async logAmendment(
    requesterId: string,
    contractId: string,
    amendments: unknown[],
    reason: string,
    status: string,
    context?: ComplianceContext
  ): Promise<AuditLogEntry> {
    return this.logAction('amend', requesterId, contractId, {
      amendmentCount: amendments.length,
      reason,
      status,
      actionType: 'contract_amendment',
    }, context);
  }

  /**
   * Log a workflow pause/resume action (AC-5)
   */
  async logWorkflowControl(
    operatorId: string,
    workflowId: string,
    action: 'pause' | 'resume',
    reason: string,
    checkpointId?: string,
    context?: ComplianceContext
  ): Promise<AuditLogEntry> {
    return this.logAction(action, operatorId, workflowId, {
      reason,
      checkpointId,
      actionType: `workflow_${action}`,
    }, context);
  }

  /**
   * Log a decision approval action (AC-6)
   */
  async logApproval(
    approverId: string,
    decisionId: string,
    approved: boolean,
    comments: string,
    riskLevel: string,
    context?: ComplianceContext
  ): Promise<AuditLogEntry> {
    return this.logAction(approved ? 'approve' : 'reject', approverId, decisionId, {
      approved,
      comments,
      riskLevel,
      actionType: 'decision_approval',
    }, context);
  }

  /**
   * Query audit log entries
   */
  async queryLogs(
    filters: {
      action?: OversightActionType;
      actor?: string;
      target?: string;
      startDate?: Date;
      endDate?: Date;
    },
    limit: number = 100
  ): Promise<AuditLogEntry[]> {
    let sql = 'SELECT * FROM oversight_audit_log WHERE 1=1';
    const params: unknown[] = [];
    let paramIndex = 1;

    if (filters.action) {
      sql += ` AND action = $${paramIndex++}`;
      params.push(filters.action);
    }
    if (filters.actor) {
      sql += ` AND actor = $${paramIndex++}`;
      params.push(filters.actor);
    }
    if (filters.target) {
      sql += ` AND target = $${paramIndex++}`;
      params.push(filters.target);
    }
    if (filters.startDate) {
      sql += ` AND timestamp >= $${paramIndex++}`;
      params.push(filters.startDate);
    }
    if (filters.endDate) {
      sql += ` AND timestamp <= $${paramIndex++}`;
      params.push(filters.endDate);
    }

    sql += ` ORDER BY timestamp DESC LIMIT $${paramIndex}`;
    params.push(limit);

    const result = await this.db.query<AuditLogEntry>(sql, params);
    return result.rows;
  }

  /**
   * Mask PII in an object recursively
   */
  private maskPII(obj: Record<string, unknown>): Record<string, unknown> {
    const masked: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(obj)) {
      if (typeof value === 'string') {
        masked[key] = this.maskPIIString(value);
      } else if (typeof value === 'object' && value !== null) {
        if (Array.isArray(value)) {
          masked[key] = value.map(item => 
            typeof item === 'string' ? this.maskPIIString(item) :
            typeof item === 'object' && item !== null ? this.maskPII(item as Record<string, unknown>) : item
          );
        } else {
          masked[key] = this.maskPII(value as Record<string, unknown>);
        }
      } else {
        masked[key] = value;
      }
    }

    return masked;
  }

  /**
   * Mask PII patterns in a string
   */
  private maskPIIString(str: string): string {
    let masked = str;
    for (const { pattern, replacement } of PII_PATTERNS) {
      masked = masked.replace(pattern, replacement);
    }
    return masked;
  }

  /**
   * Persist audit entry to database
   */
  private async persistToDatabase(entry: AuditLogEntry): Promise<void> {
    await this.db.query(
      `INSERT INTO oversight_audit_log (id, context_id, action, actor, target, details, timestamp, pii_masked)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [entry.id, entry.contextId, entry.action, entry.actor, entry.target, 
       JSON.stringify(entry.details), entry.timestamp, entry.piiMasked]
    );
  }

  /**
   * Send audit entry to Kafka for real-time processing
   */
  private async sendToKafka(entry: AuditLogEntry): Promise<void> {
    await this.kafka.send(this.auditTopic, JSON.stringify(entry));
  }

  /**
   * Generate a unique ID
   */
  private generateId(): string {
    return 'audit_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }
}

export default ComplianceLogger;
