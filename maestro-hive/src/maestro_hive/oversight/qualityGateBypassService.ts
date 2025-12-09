/**
 * Quality Gate Bypass Service
 * AC-2: Add manual quality gate bypass with audit trail
 * EU AI Act Article 14 - Human override capability
 * EPIC: MD-2158
 */

import {
  QualityGateBypassRequest,
  QualityGateBypass,
  BypassScope,
  BypassStatus,
  ComplianceContext,
  OversightConfig,
} from './types';
import { ComplianceLogger } from './complianceLogger';

interface DatabaseClient {
  query<T>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}

/**
 * Quality Gate Bypass Service
 * Allows human-authorized bypasses of automated quality gates with full audit trail
 */
export class QualityGateBypassService {
  private db: DatabaseClient;
  private logger: ComplianceLogger;
  private config: OversightConfig;

  constructor(
    db: DatabaseClient,
    logger: ComplianceLogger,
    config: OversightConfig
  ) {
    this.db = db;
    this.logger = logger;
    this.config = config;
  }

  /**
   * Create a new quality gate bypass
   * Requires explicit justification and has mandatory expiry
   */
  async createBypass(request: QualityGateBypassRequest): Promise<QualityGateBypass> {
    const { gateId, justification, approverId, expiry, scope, context } = request;

    // Validate expiry is within allowed maximum
    const maxExpiry = new Date();
    maxExpiry.setHours(maxExpiry.getHours() + this.config.bypass.maxDurationHours);

    if (expiry > maxExpiry) {
      throw new Error(`Bypass expiry cannot exceed ${this.config.bypass.maxDurationHours} hours`);
    }

    // Check for existing active bypasses
    const existingResult = await this.db.query<{ id: string }>(
      `SELECT id FROM quality_gate_bypasses 
       WHERE gate_id = $1 AND status = 'active' AND expiry > NOW()`,
      [gateId]
    );

    if (existingResult.rows.length > 0) {
      throw new Error(`Active bypass already exists for gate ${gateId}`);
    }

    // Generate bypass ID
    const bypassId = this.generateBypassId();

    // Create bypass record
    await this.db.query(
      `INSERT INTO quality_gate_bypasses 
       (id, gate_id, justification, approver_id, expiry, scope, status, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())`,
      [bypassId, gateId, justification, approverId, expiry, scope, 'active']
    );

    // Log to compliance audit
    const auditEntry = await this.logger.logBypass(
      approverId,
      gateId,
      justification,
      scope,
      expiry,
      context
    );

    return {
      id: bypassId,
      gateId,
      justification,
      approverId,
      expiry,
      scope,
      status: 'active',
      createdAt: new Date(),
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Check if a bypass is valid for a gate
   */
  async checkBypass(gateId: string, workflowId?: string, sessionId?: string): Promise<{
    bypassed: boolean;
    bypassId?: string;
    scope?: BypassScope;
    expiresAt?: Date;
  }> {
    // Check for active bypass matching the gate
    let query = `
      SELECT id, scope, expiry 
      FROM quality_gate_bypasses 
      WHERE gate_id = $1 
        AND status = 'active' 
        AND expiry > NOW()
    `;
    const params: unknown[] = [gateId];

    const result = await this.db.query<{ id: string; scope: BypassScope; expiry: Date }>(query, params);

    if (result.rows.length === 0) {
      return { bypassed: false };
    }

    const bypass = result.rows[0];

    // For 'single' scope bypasses, mark as used after returning
    if (bypass.scope === 'single') {
      await this.markBypassUsed(bypass.id);
    }

    return {
      bypassed: true,
      bypassId: bypass.id,
      scope: bypass.scope,
      expiresAt: bypass.expiry,
    };
  }

  /**
   * Mark a single-use bypass as used
   */
  async markBypassUsed(bypassId: string): Promise<void> {
    await this.db.query(
      `UPDATE quality_gate_bypasses 
       SET status = 'used', used_at = NOW()
       WHERE id = $1 AND scope = 'single'`,
      [bypassId]
    );
  }

  /**
   * Revoke an active bypass
   */
  async revokeBypass(bypassId: string, revokerId: string, reason: string): Promise<void> {
    const result = await this.db.query<{ id: string; gate_id: string; status: BypassStatus }>(
      'SELECT id, gate_id, status FROM quality_gate_bypasses WHERE id = $1',
      [bypassId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Bypass not found: ${bypassId}`);
    }

    const bypass = result.rows[0];
    if (bypass.status !== 'active') {
      throw new Error(`Cannot revoke bypass with status: ${bypass.status}`);
    }

    await this.db.query(
      `UPDATE quality_gate_bypasses 
       SET status = 'revoked', revoked_by = $1, revoke_reason = $2, revoked_at = NOW()
       WHERE id = $3`,
      [revokerId, reason, bypassId]
    );

    await this.logger.logAction('bypass', revokerId, bypass.gate_id, {
      bypassId,
      action: 'revoke',
      reason,
      actionType: 'bypass_revoked',
    });
  }

  /**
   * Get bypass status
   */
  async getBypass(bypassId: string): Promise<QualityGateBypass | null> {
    const result = await this.db.query<{
      id: string;
      gate_id: string;
      justification: string;
      approver_id: string;
      expiry: Date;
      scope: BypassScope;
      status: BypassStatus;
      created_at: Date;
      used_at?: Date;
    }>(
      'SELECT * FROM quality_gate_bypasses WHERE id = $1',
      [bypassId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      gateId: row.gate_id,
      justification: row.justification,
      approverId: row.approver_id,
      expiry: row.expiry,
      scope: row.scope,
      status: row.status,
      createdAt: row.created_at,
      usedAt: row.used_at,
      auditLogId: '',
    };
  }

  /**
   * List active bypasses
   */
  async listActiveBypasses(): Promise<QualityGateBypass[]> {
    const result = await this.db.query<{
      id: string;
      gate_id: string;
      justification: string;
      approver_id: string;
      expiry: Date;
      scope: BypassScope;
      status: BypassStatus;
      created_at: Date;
    }>(
      `SELECT * FROM quality_gate_bypasses 
       WHERE status = 'active' AND expiry > NOW()
       ORDER BY expiry ASC`
    );

    return result.rows.map(row => ({
      id: row.id,
      gateId: row.gate_id,
      justification: row.justification,
      approverId: row.approver_id,
      expiry: row.expiry,
      scope: row.scope,
      status: row.status,
      createdAt: row.created_at,
      auditLogId: '',
    }));
  }

  /**
   * Clean up expired bypasses
   */
  async cleanupExpiredBypasses(): Promise<number> {
    const result = await this.db.query<{ count: number }>(
      `WITH updated AS (
        UPDATE quality_gate_bypasses 
        SET status = 'expired'
        WHERE status = 'active' AND expiry <= NOW()
        RETURNING *
      )
      SELECT COUNT(*) as count FROM updated`
    );

    return result.rows[0]?.count || 0;
  }

  private generateBypassId(): string {
    return 'byp_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }
}

export default QualityGateBypassService;
