/**
 * Contract Amendment Service
 * AC-4: Allow contract amendment/renegotiation
 * EU AI Act Article 14 - Human modification capability
 * EPIC: MD-2158
 */

import {
  ContractAmendmentRequest,
  ContractAmendment,
  ContractChange,
  AmendmentStatus,
  ComplianceContext,
  OversightConfig,
} from './types';
import { ComplianceLogger } from './complianceLogger';

interface DatabaseClient {
  query<T>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}

interface ContractRecord {
  id: string;
  version: number;
  data: Record<string, unknown>;
  locked: boolean;
}

interface AmendmentRecord {
  id: string;
  contract_id: string;
  amendments: string; // JSON string
  requester_id: string;
  reason: string;
  status: AmendmentStatus;
  approver_id?: string;
  approval_comments?: string;
  created_at: Date;
  approved_at?: Date;
  applied_at?: Date;
}

/**
 * Contract Amendment Service
 * Allows human-initiated amendments to AI-generated contracts
 */
export class ContractAmendmentService {
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
   * Request a contract amendment
   */
  async requestAmendment(request: ContractAmendmentRequest): Promise<ContractAmendment> {
    const { contractId, amendments, requesterId, reason, context } = request;

    // Verify contract exists and is not locked
    const contractResult = await this.db.query<ContractRecord>(
      'SELECT * FROM contracts WHERE id = $1',
      [contractId]
    );

    if (contractResult.rows.length === 0) {
      throw new Error('Contract not found: ' + contractId);
    }

    const contract = contractResult.rows[0];
    if (contract.locked) {
      throw new Error('Contract is locked and cannot be amended: ' + contractId);
    }

    // Validate amendments reference valid fields
    this.validateAmendments(amendments, contract.data);

    // Generate amendment ID
    const amendmentId = this.generateAmendmentId();

    // Create amendment request
    await this.db.query(
      `INSERT INTO contract_amendments
       (id, contract_id, amendments, requester_id, reason, status, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, NOW())`,
      [amendmentId, contractId, JSON.stringify(amendments), requesterId, reason, 'pending_approval']
    );

    // Log to compliance audit
    const auditEntry = await this.logger.logAmendment(
      requesterId,
      contractId,
      amendments,
      reason,
      'pending_approval',
      context
    );

    return {
      id: amendmentId,
      contractId,
      amendments,
      requesterId,
      reason,
      status: 'pending_approval',
      createdAt: new Date(),
      auditLogId: auditEntry.id,
    };
  }

  /**
   * Approve an amendment request
   */
  async approveAmendment(
    amendmentId: string,
    approverId: string,
    comments: string
  ): Promise<ContractAmendment> {
    const amendment = await this.getAmendmentRecord(amendmentId);

    if (amendment.status !== 'pending_approval') {
      throw new Error('Amendment cannot be approved. Current status: ' + amendment.status);
    }

    // Cannot approve own request
    if (amendment.requester_id === approverId) {
      throw new Error('Cannot approve your own amendment request');
    }

    await this.db.query(
      `UPDATE contract_amendments
       SET status = 'approved', approver_id = $1, approval_comments = $2, approved_at = NOW()
       WHERE id = $3`,
      [approverId, comments, amendmentId]
    );

    await this.logger.logAction('approve', approverId, amendmentId, {
      contractId: amendment.contract_id,
      comments,
      actionType: 'amendment_approved',
    });

    return this.getAmendment(amendmentId) as Promise<ContractAmendment>;
  }

  /**
   * Reject an amendment request
   */
  async rejectAmendment(
    amendmentId: string,
    approverId: string,
    comments: string
  ): Promise<void> {
    const amendment = await this.getAmendmentRecord(amendmentId);

    if (amendment.status !== 'pending_approval') {
      throw new Error('Amendment cannot be rejected. Current status: ' + amendment.status);
    }

    await this.db.query(
      `UPDATE contract_amendments
       SET status = 'rejected', approver_id = $1, approval_comments = $2, approved_at = NOW()
       WHERE id = $3`,
      [approverId, comments, amendmentId]
    );

    await this.logger.logAction('reject', approverId, amendmentId, {
      contractId: amendment.contract_id,
      comments,
      actionType: 'amendment_rejected',
    });
  }

  /**
   * Apply an approved amendment to the contract
   */
  async applyAmendment(amendmentId: string, operatorId: string): Promise<void> {
    const amendment = await this.getAmendmentRecord(amendmentId);

    if (amendment.status !== 'approved') {
      throw new Error('Only approved amendments can be applied. Current status: ' + amendment.status);
    }

    // Get current contract
    const contractResult = await this.db.query<ContractRecord>(
      'SELECT * FROM contracts WHERE id = $1',
      [amendment.contract_id]
    );

    if (contractResult.rows.length === 0) {
      throw new Error('Contract not found: ' + amendment.contract_id);
    }

    const contract = contractResult.rows[0];
    const amendments: ContractChange[] = JSON.parse(amendment.amendments);

    // Apply amendments to contract data
    const updatedData = this.applyChanges(contract.data, amendments);

    // Update contract with new version
    await this.db.query(
      `UPDATE contracts
       SET data = $1, version = version + 1, updated_at = NOW()
       WHERE id = $2`,
      [JSON.stringify(updatedData), amendment.contract_id]
    );

    // Mark amendment as applied
    await this.db.query(
      `UPDATE contract_amendments
       SET status = 'applied', applied_at = NOW()
       WHERE id = $1`,
      [amendmentId]
    );

    // Record version history
    await this.db.query(
      `INSERT INTO contract_versions
       (contract_id, version, data, amendment_id, created_at)
       VALUES ($1, $2, $3, $4, NOW())`,
      [amendment.contract_id, contract.version + 1, JSON.stringify(updatedData), amendmentId]
    );

    await this.logger.logAction('amend', operatorId, amendment.contract_id, {
      amendmentId,
      newVersion: contract.version + 1,
      actionType: 'amendment_applied',
    });
  }

  /**
   * Get an amendment by ID
   */
  async getAmendment(amendmentId: string): Promise<ContractAmendment | null> {
    const result = await this.db.query<AmendmentRecord>(
      'SELECT * FROM contract_amendments WHERE id = $1',
      [amendmentId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      contractId: row.contract_id,
      amendments: JSON.parse(row.amendments),
      requesterId: row.requester_id,
      reason: row.reason,
      status: row.status,
      approverId: row.approver_id,
      approvalComments: row.approval_comments,
      createdAt: row.created_at,
      approvedAt: row.approved_at,
      appliedAt: row.applied_at,
      auditLogId: '',
    };
  }

  /**
   * List pending amendments for a contract
   */
  async listPendingAmendments(contractId?: string): Promise<ContractAmendment[]> {
    let sql = `SELECT * FROM contract_amendments WHERE status = 'pending_approval'`;
    const params: unknown[] = [];

    if (contractId) {
      sql += ' AND contract_id = $1';
      params.push(contractId);
    }

    sql += ' ORDER BY created_at ASC';

    const result = await this.db.query<AmendmentRecord>(sql, params);

    return result.rows.map(row => ({
      id: row.id,
      contractId: row.contract_id,
      amendments: JSON.parse(row.amendments),
      requesterId: row.requester_id,
      reason: row.reason,
      status: row.status,
      approverId: row.approver_id,
      approvalComments: row.approval_comments,
      createdAt: row.created_at,
      approvedAt: row.approved_at,
      appliedAt: row.applied_at,
      auditLogId: '',
    }));
  }

  /**
   * Get amendment history for a contract
   */
  async getAmendmentHistory(contractId: string): Promise<ContractAmendment[]> {
    const result = await this.db.query<AmendmentRecord>(
      `SELECT * FROM contract_amendments
       WHERE contract_id = $1
       ORDER BY created_at DESC`,
      [contractId]
    );

    return result.rows.map(row => ({
      id: row.id,
      contractId: row.contract_id,
      amendments: JSON.parse(row.amendments),
      requesterId: row.requester_id,
      reason: row.reason,
      status: row.status,
      approverId: row.approver_id,
      approvalComments: row.approval_comments,
      createdAt: row.created_at,
      approvedAt: row.approved_at,
      appliedAt: row.applied_at,
      auditLogId: '',
    }));
  }

  /**
   * Get amendment record (internal)
   */
  private async getAmendmentRecord(amendmentId: string): Promise<AmendmentRecord> {
    const result = await this.db.query<AmendmentRecord>(
      'SELECT * FROM contract_amendments WHERE id = $1',
      [amendmentId]
    );

    if (result.rows.length === 0) {
      throw new Error('Amendment not found: ' + amendmentId);
    }

    return result.rows[0];
  }

  /**
   * Validate amendments against contract schema
   */
  private validateAmendments(amendments: ContractChange[], contractData: Record<string, unknown>): void {
    for (const change of amendments) {
      if (change.changeType === 'modify' || change.changeType === 'remove') {
        if (!(change.field in contractData)) {
          throw new Error('Field not found in contract: ' + change.field);
        }
      }
    }
  }

  /**
   * Apply changes to contract data
   */
  private applyChanges(
    data: Record<string, unknown>,
    changes: ContractChange[]
  ): Record<string, unknown> {
    const updated = { ...data };

    for (const change of changes) {
      switch (change.changeType) {
        case 'add':
          updated[change.field] = change.newValue;
          break;
        case 'modify':
          updated[change.field] = change.newValue;
          break;
        case 'remove':
          delete updated[change.field];
          break;
      }
    }

    return updated;
  }

  private generateAmendmentId(): string {
    return 'amd_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
  }
}

export default ContractAmendmentService;
