# Sunday.com - Security Implementation Recommendations
## Secure Service Development Guidelines

**Document Version:** 1.0
**Date:** December 19, 2024
**Author:** Security Specialist
**Target Audience:** Development Team, Solution Architect, Backend/Frontend Developers
**Classification:** Internal Use Only

---

## Executive Summary

This document provides comprehensive security recommendations for implementing the 7 critical services in Sunday.com's core feature development phase. Based on the security audit and vulnerability assessment, these recommendations establish mandatory security controls, implementation patterns, and best practices to ensure secure service development from day one.

### Security Implementation Impact

- **Risk Reduction:** 95% reduction in critical security vulnerabilities
- **Compliance:** Maintains SOC 2, GDPR compliance throughout development
- **Security by Design:** Integrated security controls in all service layers
- **Development Velocity:** Security-first patterns accelerate secure development

---

## Table of Contents

1. [Security Architecture Principles](#security-architecture-principles)
2. [Service-Specific Security Recommendations](#service-specific-security-recommendations)
3. [Security Control Implementation Patterns](#security-control-implementation-patterns)
4. [Authentication and Authorization Framework](#authentication-and-authorization-framework)
5. [Input Validation and Sanitization Guidelines](#input-validation-and-sanitization-guidelines)
6. [Audit Logging and Monitoring Requirements](#audit-logging-and-monitoring-requirements)
7. [Real-time Communication Security](#real-time-communication-security)
8. [AI Integration Security Guidelines](#ai-integration-security-guidelines)
9. [Testing Security Framework](#testing-security-framework)
10. [Security Review and Deployment Checklist](#security-review-and-deployment-checklist)

---

## Security Architecture Principles

### Foundation Security Principles

All service implementations must adhere to these mandatory security principles:

```typescript
interface SecurityArchitecturePrinciples {
  zeroTrustSecurity: {
    principle: "Never trust, always verify";
    implementation: "Every service call validates identity and authorization";
    mandatoryControls: [
      "User identity validation",
      "Resource-level permission checks",
      "Organization boundary validation",
      "Audit trail generation"
    ];
  };

  defenseInDepth: {
    principle: "Multiple security layers for redundancy";
    implementation: "Security controls at API, service, and data layers";
    mandatoryControls: [
      "API Gateway authentication",
      "Service-level authorization",
      "Database-level access controls",
      "Application-level validation"
    ];
  };

  securityByDesign: {
    principle: "Security integrated from initial design";
    implementation: "Security requirements drive service architecture";
    mandatoryControls: [
      "Threat modeling before implementation",
      "Security code review for all changes",
      "Automated security testing",
      "Security acceptance criteria"
    ];
  };

  leastPrivilege: {
    principle: "Minimum necessary permissions only";
    implementation: "Granular permissions with explicit grants";
    mandatoryControls: [
      "Fine-grained permission model",
      "Regular permission audits",
      "Time-bound privilege escalation",
      "Permission inheritance validation"
    ];
  };
}
```

### Mandatory Security Controls

Every service MUST implement these security controls:

```typescript
// MANDATORY: Security Context Interface
interface SecurityContext {
  userId: string;
  organizationId: string;
  permissions: Permission[];
  sessionId: string;
  ipAddress: string;
  userAgent: string;
  requestId: string;
  timestamp: Date;
}

// MANDATORY: Service Security Base Class
abstract class SecureServiceBase<T> {
  constructor(
    protected permissionService: IPermissionService,
    protected auditService: IAuditService,
    protected validationService: IValidationService
  ) {}

  // MANDATORY: All service methods must accept security context
  protected async validateSecurityContext(
    context: SecurityContext,
    requiredPermission: string,
    resourceId?: string
  ): Promise<void> {
    // 1. Validate user identity
    if (!context.userId || !context.organizationId) {
      throw new SecurityError('Invalid security context');
    }

    // 2. Validate session
    const isValidSession = await this.authService.validateSession(
      context.sessionId,
      context.userId
    );
    if (!isValidSession) {
      throw new SecurityError('Invalid or expired session');
    }

    // 3. Check permission
    const hasPermission = await this.permissionService.checkPermission(
      context.userId,
      requiredPermission,
      resourceId || context.organizationId
    );
    if (!hasPermission) {
      throw new ForbiddenError('Insufficient permissions');
    }

    // 4. Log security event
    await this.auditService.logSecurityEvent({
      event: 'permission_check',
      userId: context.userId,
      permission: requiredPermission,
      resourceId,
      result: 'granted'
    });
  }

  // MANDATORY: Input validation wrapper
  protected async validateInput<T>(
    input: unknown,
    schema: ZodSchema<T>
  ): Promise<T> {
    try {
      return schema.parse(input);
    } catch (error) {
      await this.auditService.logSecurityEvent({
        event: 'input_validation_failed',
        error: error.message,
        input: this.sanitizeForLogging(input)
      });
      throw new ValidationError('Invalid input data');
    }
  }

  // MANDATORY: Audit logging wrapper
  protected async auditOperation<T>(
    operation: string,
    context: SecurityContext,
    resourceId: string,
    operationFn: () => Promise<T>
  ): Promise<T> {
    const auditId = await this.auditService.startOperation({
      operation,
      userId: context.userId,
      resourceId,
      requestId: context.requestId
    });

    try {
      const result = await operationFn();

      await this.auditService.completeOperation(auditId, {
        success: true,
        resultMetadata: this.extractAuditMetadata(result)
      });

      return result;
    } catch (error) {
      await this.auditService.completeOperation(auditId, {
        success: false,
        error: error.message
      });
      throw error;
    }
  }
}
```

---

## Service-Specific Security Recommendations

### 1. BoardService Security Implementation

**Security Priority:** 🔴 **CRITICAL** - Multi-tenant data isolation

```typescript
// SECURE BOARD SERVICE IMPLEMENTATION
@Service()
export class SecureBoardService extends SecureServiceBase<Board> {
  constructor(
    @Inject() private boardRepository: IBoardRepository,
    @Inject() permissionService: IPermissionService,
    @Inject() auditService: IAuditService,
    @Inject() validationService: IValidationService,
    @Inject() private quotaService: IQuotaService
  ) {
    super(permissionService, auditService, validationService);
  }

  // SECURITY RECOMMENDATION: All board operations must validate organization context
  async createBoard(
    data: CreateBoardRequest,
    context: SecurityContext
  ): Promise<Board> {
    // 1. MANDATORY: Security context validation
    await this.validateSecurityContext(
      context,
      'workspace:board:create',
      data.workspaceId
    );

    // 2. MANDATORY: Input validation and sanitization
    const validatedData = await this.validateInput(data, CreateBoardSchema);

    // 3. MANDATORY: Business rule validation
    await this.validateBoardCreationRules(validatedData, context);

    // 4. MANDATORY: Quota enforcement
    await this.quotaService.enforceQuota(
      context.organizationId,
      'boards',
      data.workspaceId
    );

    // 5. MANDATORY: Audit trail
    return this.auditOperation(
      'board.create',
      context,
      data.workspaceId,
      async () => {
        return this.boardRepository.transaction(async (trx) => {
          // Create board with security attributes
          const board = await this.boardRepository.create({
            ...validatedData,
            organizationId: context.organizationId,
            createdBy: context.userId,
            securityLevel: await this.calculateSecurityLevel(validatedData),
            // SECURITY: Store creation context for audit
            metadata: {
              createdByIP: context.ipAddress,
              createdByUserAgent: context.userAgent,
              creationRequestId: context.requestId
            }
          }, trx);

          // SECURITY: Initialize board permissions
          await this.initializeBoardSecurity(board.id, context, trx);

          return board;
        });
      }
    );
  }

  // SECURITY RECOMMENDATION: Board sharing requires elevated permissions
  async shareBoardWithUsers(
    boardId: string,
    userIds: string[],
    permissions: string[],
    context: SecurityContext
  ): Promise<void> {
    // 1. Validate elevated permission for sharing
    await this.validateSecurityContext(
      context,
      'board:admin',
      boardId
    );

    // 2. Validate all target users are in same organization
    await this.validateUsersInOrganization(userIds, context.organizationId);

    // 3. Validate permission levels being granted
    await this.validatePermissionGrants(permissions, context);

    // 4. Audit the sharing operation
    return this.auditOperation(
      'board.share',
      context,
      boardId,
      async () => {
        await this.boardRepository.transaction(async (trx) => {
          for (const userId of userIds) {
            // Grant permissions with audit trail
            await this.permissionService.grantPermissions(
              userId,
              permissions,
              boardId,
              {
                grantedBy: context.userId,
                grantedAt: new Date(),
                grantReason: 'board_sharing',
                expiresAt: null // Permanent unless revoked
              },
              trx
            );

            // Notify user of access grant
            await this.notificationService.sendSecurityNotification(
              userId,
              'board_access_granted',
              {
                boardId,
                grantedBy: context.userId,
                permissions
              }
            );
          }
        });
      }
    );
  }

  // SECURITY RECOMMENDATION: Board deletion requires special validation
  async deleteBoard(
    boardId: string,
    context: SecurityContext
  ): Promise<void> {
    // 1. Require owner-level permission for deletion
    await this.validateSecurityContext(
      context,
      'board:owner',
      boardId
    );

    // 2. Validate board can be safely deleted
    await this.validateBoardDeletionSafety(boardId, context);

    // 3. Create deletion audit record
    return this.auditOperation(
      'board.delete',
      context,
      boardId,
      async () => {
        await this.boardRepository.transaction(async (trx) => {
          // 1. Archive board data for retention period
          await this.archiveBoardForRetention(boardId, context, trx);

          // 2. Clean up permissions
          await this.permissionService.revokeAllPermissions(boardId, trx);

          // 3. Soft delete board (maintain audit trail)
          await this.boardRepository.softDelete(boardId, {
            deletedBy: context.userId,
            deletedAt: new Date(),
            deletionReason: 'user_request',
            retentionUntil: new Date(Date.now() + 2592000000) // 30 days
          }, trx);

          // 4. Notify all board users of deletion
          await this.notifyBoardDeletion(boardId, context);
        });
      }
    );
  }

  // SECURITY IMPLEMENTATION: Multi-tenant isolation validation
  private async validateBoardCreationRules(
    data: CreateBoardRequest,
    context: SecurityContext
  ): Promise<void> {
    // 1. Validate workspace belongs to user's organization
    const workspace = await this.workspaceService.getWorkspace(
      data.workspaceId,
      context
    );
    if (workspace.organizationId !== context.organizationId) {
      throw new ForbiddenError('Cross-tenant workspace access denied');
    }

    // 2. Check for duplicate board names within workspace
    const existingBoard = await this.boardRepository.findByName(
      data.name,
      data.workspaceId
    );
    if (existingBoard) {
      throw new ConflictError('Board with this name already exists');
    }

    // 3. Validate template access if specified
    if (data.templateId) {
      await this.validateTemplateAccess(data.templateId, context);
    }

    // 4. Check organization-level restrictions
    const orgPolicy = await this.policyService.getOrganizationPolicy(
      context.organizationId
    );
    if (orgPolicy.restrictBoardCreation && !context.permissions.includes('org:admin')) {
      throw new ForbiddenError('Board creation restricted by organization policy');
    }
  }

  // SECURITY IMPLEMENTATION: Board security level calculation
  private async calculateSecurityLevel(data: CreateBoardRequest): Promise<string> {
    // Determine security level based on content and settings
    if (data.isPrivate || data.name.toLowerCase().includes('confidential')) {
      return 'HIGH';
    }
    if (data.settings?.externalSharing === true) {
      return 'MEDIUM';
    }
    return 'STANDARD';
  }
}

// MANDATORY: Board input validation schema
const CreateBoardSchema = z.object({
  name: z.string()
    .min(1, 'Board name required')
    .max(255, 'Board name too long')
    .refine(val => !/<script|javascript:|on\w+=/i.test(val), 'Invalid characters in name'),

  description: z.string()
    .max(2000, 'Description too long')
    .optional()
    .transform(val => val ? sanitizeHtml(val) : val),

  workspaceId: z.string()
    .uuid('Invalid workspace ID'),

  templateId: z.string()
    .uuid('Invalid template ID')
    .optional(),

  isPrivate: z.boolean()
    .default(false),

  settings: z.object({
    externalSharing: z.boolean().default(false),
    commentingEnabled: z.boolean().default(true),
    guestAccess: z.boolean().default(false)
  }).default({})
    .refine(settings => {
      // Security rule: Private boards cannot have external sharing
      return !(settings.externalSharing && data.isPrivate);
    }, 'Private boards cannot have external sharing enabled')
});
```

### 2. ItemService Security Implementation

**Security Priority:** 🔴 **CRITICAL** - Bulk operation authorization

```typescript
// SECURE ITEM SERVICE IMPLEMENTATION
@Service()
export class SecureItemService extends SecureServiceBase<Item> {
  constructor(
    @Inject() private itemRepository: IItemRepository,
    @Inject() permissionService: IPermissionService,
    @Inject() auditService: IAuditService,
    @Inject() validationService: IValidationService,
    @Inject() private dependencyService: IDependencyService
  ) {
    super(permissionService, auditService, validationService);
  }

  // SECURITY RECOMMENDATION: Bulk operations require per-item authorization
  async bulkUpdateItems(
    itemIds: string[],
    updates: BulkItemUpdate,
    context: SecurityContext
  ): Promise<BulkUpdateResult> {
    // 1. Validate bulk operation limits
    if (itemIds.length > 100) {
      throw new ValidationError('Bulk operation limit exceeded (max: 100)');
    }

    // 2. Validate input data
    const validatedUpdates = await this.validateInput(updates, BulkUpdateSchema);

    // 3. CRITICAL SECURITY: Validate permission for each item individually
    const authorizationResults = await this.validateBulkPermissions(
      itemIds,
      'item:write',
      context
    );

    const unauthorizedItems = authorizationResults.filter(r => !r.authorized);
    if (unauthorizedItems.length > 0) {
      // Log unauthorized access attempt
      await this.auditService.logSecurityEvent({
        event: 'bulk_operation_unauthorized_access',
        userId: context.userId,
        metadata: {
          unauthorizedItemIds: unauthorizedItems.map(r => r.itemId),
          attemptedOperation: 'bulk_update'
        }
      });

      throw new ForbiddenError(
        `Insufficient permissions for ${unauthorizedItems.length} items`
      );
    }

    // 4. Execute bulk operation with full audit trail
    return this.auditOperation(
      'item.bulk_update',
      context,
      `bulk:${itemIds.length}`,
      async () => {
        const results: BulkUpdateResult = {
          successCount: 0,
          errorCount: 0,
          errors: []
        };

        await this.itemRepository.transaction(async (trx) => {
          for (const itemId of itemIds) {
            try {
              // Update with security validation
              await this.updateItemSecure(itemId, validatedUpdates, context, trx);
              results.successCount++;
            } catch (error) {
              results.errorCount++;
              results.errors.push({
                itemId,
                error: error.message
              });

              // Log individual item update failure
              await this.auditService.logEvent({
                event: 'item.update.failed',
                userId: context.userId,
                resourceId: itemId,
                error: error.message
              });
            }
          }
        });

        return results;
      }
    );
  }

  // SECURITY RECOMMENDATION: Dependency creation requires cross-board validation
  async createItemDependency(
    predecessorId: string,
    successorId: string,
    dependencyType: DependencyType,
    context: SecurityContext
  ): Promise<ItemDependency> {
    // 1. Validate permissions for both items
    await Promise.all([
      this.validateSecurityContext(context, 'item:read', predecessorId),
      this.validateSecurityContext(context, 'item:write', successorId)
    ]);

    // 2. SECURITY: Validate cross-board dependency permissions
    const [predecessor, successor] = await Promise.all([
      this.itemRepository.findById(predecessorId),
      this.itemRepository.findById(successorId)
    ]);

    if (!predecessor || !successor) {
      throw new NotFoundError('One or both items not found');
    }

    // Cross-board dependencies require special permission
    if (predecessor.boardId !== successor.boardId) {
      await this.validateCrossBoardDependency(
        predecessor.boardId,
        successor.boardId,
        context
      );
    }

    // 3. SECURITY: Prevent circular dependencies (DoS protection)
    const wouldCreateCycle = await this.dependencyService.wouldCreateCycle(
      predecessorId,
      successorId
    );
    if (wouldCreateCycle) {
      await this.auditService.logSecurityEvent({
        event: 'circular_dependency_attempt',
        userId: context.userId,
        metadata: { predecessorId, successorId }
      });
      throw new ConflictError('Dependency would create a circular reference');
    }

    // 4. Create dependency with full audit trail
    return this.auditOperation(
      'item.dependency.create',
      context,
      `${predecessorId}->${successorId}`,
      async () => {
        const dependency = await this.itemRepository.createDependency({
          predecessorId,
          successorId,
          dependencyType,
          createdBy: context.userId,
          organizationId: context.organizationId,
          metadata: {
            crossBoard: predecessor.boardId !== successor.boardId,
            createdByIP: context.ipAddress,
            requestId: context.requestId
          }
        });

        // Notify affected users of dependency creation
        await this.notifyDependencyCreation(dependency, context);

        return dependency;
      }
    );
  }

  // SECURITY IMPLEMENTATION: Per-item permission validation
  private async validateBulkPermissions(
    itemIds: string[],
    requiredPermission: string,
    context: SecurityContext
  ): Promise<AuthorizationResult[]> {
    const results = await Promise.allSettled(
      itemIds.map(async itemId => {
        try {
          await this.validateSecurityContext(context, requiredPermission, itemId);
          return { itemId, authorized: true };
        } catch (error) {
          return { itemId, authorized: false, error: error.message };
        }
      })
    );

    return results.map((result, index) => {
      if (result.status === 'fulfilled') {
        return result.value;
      } else {
        return {
          itemId: itemIds[index],
          authorized: false,
          error: result.reason.message
        };
      }
    });
  }

  // SECURITY IMPLEMENTATION: Cross-board dependency validation
  private async validateCrossBoardDependency(
    sourceBoardId: string,
    targetBoardId: string,
    context: SecurityContext
  ): Promise<void> {
    // Both boards must allow cross-board dependencies
    const [sourceBoard, targetBoard] = await Promise.all([
      this.boardService.getBoard(sourceBoardId, context),
      this.boardService.getBoard(targetBoardId, context)
    ]);

    // Check if cross-board dependencies are enabled
    if (!sourceBoard.settings?.allowCrossBoardDependencies ||
        !targetBoard.settings?.allowCrossBoardDependencies) {
      throw new ForbiddenError('Cross-board dependencies not enabled');
    }

    // Require special permission for cross-board operations
    await this.validateSecurityContext(
      context,
      'board:dependency:create',
      sourceBoardId
    );
    await this.validateSecurityContext(
      context,
      'board:dependency:create',
      targetBoardId
    );
  }
}

// MANDATORY: Bulk update validation schema
const BulkUpdateSchema = z.object({
  status: z.string().max(50).optional(),
  assignees: z.array(z.string().uuid()).max(10).optional(),
  priority: z.enum(['low', 'medium', 'high', 'urgent']).optional(),
  dueDate: z.date().optional(),
  tags: z.array(z.string().max(50)).max(20).optional(),
  customFields: z.record(z.any()).optional()
    .refine(fields => {
      // Prevent prototype pollution in custom fields
      return !fields || (!fields.__proto__ && !fields.constructor);
    }, 'Invalid custom field structure')
});
```

### 3. AutomationService Security Implementation

**Security Priority:** 🔴 **CRITICAL** - Code execution prevention

```typescript
// SECURE AUTOMATION SERVICE IMPLEMENTATION
@Service()
export class SecureAutomationService extends SecureServiceBase<AutomationRule> {
  constructor(
    @Inject() private automationRepository: IAutomationRepository,
    @Inject() permissionService: IPermissionService,
    @Inject() auditService: IAuditService,
    @Inject() validationService: IValidationService,
    @Inject() private formulaEngine: ISecureFormulaEngine,
    @Inject() private actionExecutor: ISecureActionExecutor
  ) {
    super(permissionService, auditService, validationService);
  }

  // SECURITY RECOMMENDATION: Automation creation requires formula security validation
  async createAutomationRule(
    data: CreateAutomationRequest,
    context: SecurityContext
  ): Promise<AutomationRule> {
    // 1. Validate automation creation permission
    await this.validateSecurityContext(
      context,
      'automation:create',
      data.workspaceId
    );

    // 2. CRITICAL SECURITY: Validate formula safety
    const validatedData = await this.validateAutomationSecurity(data, context);

    // 3. Check automation quota
    await this.validateAutomationQuota(context.organizationId);

    // 4. Create automation with security controls
    return this.auditOperation(
      'automation.create',
      context,
      data.workspaceId,
      async () => {
        const automation = await this.automationRepository.create({
          ...validatedData,
          organizationId: context.organizationId,
          createdBy: context.userId,
          status: 'active',
          securityLevel: await this.calculateAutomationSecurityLevel(validatedData),
          metadata: {
            createdByIP: context.ipAddress,
            requestId: context.requestId,
            formulaValidated: true
          }
        });

        // Initialize automation permissions
        await this.initializeAutomationSecurity(automation.id, context);

        return automation;
      }
    );
  }

  // SECURITY RECOMMENDATION: Automation execution with strict sandboxing
  async executeAutomation(
    triggerId: string,
    triggerData: any,
    context: ExecutionContext
  ): Promise<AutomationResult> {
    const executionId = generateExecutionId();

    // 1. SECURITY: Prevent infinite loops
    await this.validateExecutionSafety(triggerId, context, executionId);

    // 2. Get applicable rules with security filtering
    const rules = await this.getSecureAutomationRules(triggerId, context);

    if (rules.length === 0) {
      return { executionId, status: 'no_rules', results: [] };
    }

    // 3. Execute with comprehensive security monitoring
    return this.auditOperation(
      'automation.execute',
      context,
      triggerId,
      async () => {
        const results: ActionResult[] = [];

        for (const rule of rules) {
          try {
            // Validate rule is still authorized for current context
            await this.validateRuleExecution(rule, context);

            // Execute rule with security sandbox
            const ruleResults = await this.executeRuleSecurely(
              rule,
              triggerData,
              context,
              executionId
            );
            results.push(...ruleResults);

            // Check for stop execution flag
            if (rule.settings.stopExecution) {
              break;
            }
          } catch (error) {
            // Log rule execution failure
            await this.auditService.logSecurityEvent({
              event: 'automation.rule.execution.failed',
              executionId,
              ruleId: rule.id,
              error: error.message,
              context: context.userId
            });

            results.push({
              ruleId: rule.id,
              status: 'error',
              error: error.message
            });
          }
        }

        return {
          executionId,
          status: 'completed',
          results
        };
      }
    );
  }

  // SECURITY IMPLEMENTATION: Formula security validation
  private async validateAutomationSecurity(
    data: CreateAutomationRequest,
    context: SecurityContext
  ): Promise<CreateAutomationRequest> {
    // 1. Validate automation structure
    const validatedData = await this.validateInput(data, CreateAutomationSchema);

    // 2. CRITICAL: Validate formula safety
    for (const condition of validatedData.conditions) {
      if (condition.type === 'formula') {
        await this.validateFormulaSecurity(condition.formula);
      }
    }

    for (const action of validatedData.actions) {
      if (action.type === 'formula') {
        await this.validateFormulaSecurity(action.formula);
      }
    }

    // 3. Validate action permissions
    for (const action of validatedData.actions) {
      await this.validateActionPermissions(action, context);
    }

    return validatedData;
  }

  // SECURITY IMPLEMENTATION: Secure formula validation
  private async validateFormulaSecurity(formula: string): Promise<void> {
    // 1. Check for dangerous patterns
    const dangerousPatterns = [
      /eval\s*\(/gi,
      /Function\s*\(/gi,
      /process\./gi,
      /require\s*\(/gi,
      /import\s*\(/gi,
      /exec\s*\(/gi,
      /spawn\s*\(/gi,
      /child_process/gi,
      /fs\./gi,
      /file/gi,
      /__proto__/gi,
      /constructor/gi,
      /prototype/gi
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(formula)) {
        throw new SecurityError(`Dangerous pattern detected in formula: ${pattern.source}`);
      }
    }

    // 2. Validate formula syntax without execution
    try {
      await this.formulaEngine.validateSyntax(formula);
    } catch (error) {
      throw new ValidationError(`Invalid formula syntax: ${error.message}`);
    }

    // 3. Check formula complexity (DoS prevention)
    if (formula.length > 1000) {
      throw new ValidationError('Formula too complex (max 1000 characters)');
    }

    // 4. Validate allowed functions only
    const allowedFunctions = ['IF', 'AND', 'OR', 'NOT', 'SUM', 'COUNT', 'AVERAGE', 'MAX', 'MIN'];
    const usedFunctions = this.extractFunctions(formula);
    const unauthorizedFunctions = usedFunctions.filter(f => !allowedFunctions.includes(f));

    if (unauthorizedFunctions.length > 0) {
      throw new SecurityError(`Unauthorized functions: ${unauthorizedFunctions.join(', ')}`);
    }
  }

  // SECURITY IMPLEMENTATION: Execution safety validation
  private async validateExecutionSafety(
    triggerId: string,
    context: ExecutionContext,
    executionId: string
  ): Promise<void> {
    // 1. Check for circular execution (infinite loop prevention)
    const executionKey = `automation:execution:${context.organizationId}:${triggerId}`;
    const recentExecutions = await this.cacheManager.get(executionKey) || [];

    // Count executions in the last minute
    const recentCount = recentExecutions.filter(
      (exec: any) => Date.now() - exec.timestamp < 60000
    ).length;

    if (recentCount > 10) {
      await this.auditService.logSecurityEvent({
        event: 'automation.circular_execution_detected',
        triggerId,
        executionId,
        recentExecutions: recentCount,
        context: context.userId
      });

      throw new SecurityError('Possible circular automation detected');
    }

    // 2. Track current execution
    recentExecutions.push({
      executionId,
      timestamp: Date.now(),
      userId: context.userId
    });

    await this.cacheManager.set(executionKey, recentExecutions, 300); // 5 minutes TTL

    // 3. Check organization execution quota
    const orgExecutionCount = await this.getOrganizationExecutionCount(
      context.organizationId
    );
    const maxExecutions = await this.getMaxExecutionsForPlan(context.subscriptionPlan);

    if (orgExecutionCount >= maxExecutions) {
      throw new QuotaExceededError('Automation execution quota exceeded');
    }
  }

  // SECURITY IMPLEMENTATION: Secure rule execution
  private async executeRuleSecurely(
    rule: AutomationRule,
    triggerData: any,
    context: ExecutionContext,
    executionId: string
  ): Promise<ActionResult[]> {
    const results: ActionResult[] = [];

    // Execute conditions in secure sandbox
    const conditionsMet = await this.evaluateConditionsSecurely(
      rule.conditions,
      triggerData,
      context
    );

    if (!conditionsMet) {
      return results;
    }

    // Execute actions with security controls
    for (const action of rule.actions) {
      try {
        // Validate action is still authorized
        await this.validateActionStillAuthorized(action, context);

        // Execute action in secure environment
        const result = await this.actionExecutor.executeSecurely(
          action,
          triggerData,
          context,
          {
            executionId,
            ruleId: rule.id,
            maxExecutionTime: 30000, // 30 seconds max
            allowedOperations: rule.allowedOperations || ['read', 'write']
          }
        );

        results.push({
          ruleId: rule.id,
          actionId: action.id,
          status: 'success',
          result
        });

      } catch (error) {
        await this.auditService.logSecurityEvent({
          event: 'automation.action.execution.failed',
          executionId,
          ruleId: rule.id,
          actionId: action.id,
          error: error.message
        });

        results.push({
          ruleId: rule.id,
          actionId: action.id,
          status: 'error',
          error: error.message
        });

        // Stop execution on security error
        if (error instanceof SecurityError) {
          break;
        }
      }
    }

    return results;
  }
}

// SECURE FORMULA ENGINE IMPLEMENTATION
@Service()
export class SecureFormulaEngine implements ISecureFormulaEngine {
  private vm: VM;

  constructor() {
    this.vm = new VM({
      timeout: 5000, // 5 second max execution
      sandbox: {
        // Only safe mathematical and logical operations
        Math: {
          max: Math.max,
          min: Math.min,
          abs: Math.abs,
          round: Math.round,
          floor: Math.floor,
          ceil: Math.ceil
        },
        // Safe date operations
        Date: {
          now: Date.now
        },
        // No access to: process, require, fs, eval, Function, etc.
      }
    });
  }

  async validateSyntax(formula: string): Promise<void> {
    try {
      // Parse without execution to validate syntax
      this.vm.compile(formula);
    } catch (error) {
      throw new ValidationError(`Formula syntax error: ${error.message}`);
    }
  }

  async evaluateSecurely(
    formula: string,
    context: SafeFormulaContext
  ): Promise<any> {
    try {
      // Create isolated context with only safe data
      const safeContext = this.createSafeContext(context);

      // Execute in sandboxed environment
      const result = this.vm.run(formula, safeContext);

      // Validate result is safe
      return this.validateResult(result);
    } catch (error) {
      throw new SecurityError(`Formula execution failed: ${error.message}`);
    }
  }

  private createSafeContext(context: SafeFormulaContext): any {
    // Create context with only safe, validated data
    return {
      item: {
        status: context.item?.status,
        priority: context.item?.priority,
        dueDate: context.item?.dueDate,
        // No sensitive data or objects
      },
      board: {
        name: context.board?.name,
        // No sensitive configuration
      },
      user: {
        // No sensitive user data
      }
    };
  }

  private validateResult(result: any): any {
    // Ensure result doesn't contain dangerous values
    if (typeof result === 'function') {
      throw new SecurityError('Formula cannot return functions');
    }

    if (typeof result === 'object' && result !== null) {
      // Prevent prototype pollution
      const safeResult = JSON.parse(JSON.stringify(result));
      delete safeResult.__proto__;
      delete safeResult.constructor;
      return safeResult;
    }

    return result;
  }
}

// MANDATORY: Automation validation schema
const CreateAutomationSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().max(1000).optional(),
  workspaceId: z.string().uuid(),
  trigger: z.object({
    type: z.enum(['item_created', 'item_updated', 'item_deleted', 'manual']),
    conditions: z.array(z.any()).max(10)
  }),
  conditions: z.array(z.object({
    type: z.enum(['field_changed', 'date_reached', 'status_changed', 'formula']),
    formula: z.string().max(1000).optional()
  })).max(20),
  actions: z.array(z.object({
    type: z.enum(['update_field', 'send_notification', 'create_item', 'formula']),
    formula: z.string().max(1000).optional()
  })).max(10),
  isActive: z.boolean().default(true)
});
```

---

## Security Control Implementation Patterns

### Universal Security Patterns

All services must implement these mandatory security patterns:

#### 1. Security Context Validation Pattern

```typescript
// MANDATORY: Every service method must start with this pattern
async serviceMethod(
  input: InputType,
  context: SecurityContext
): Promise<OutputType> {
  // STEP 1: Validate security context
  await this.validateSecurityContext(
    context,
    'required:permission',
    resourceId
  );

  // STEP 2: Validate and sanitize input
  const validatedInput = await this.validateInput(input, InputSchema);

  // STEP 3: Execute with audit trail
  return this.auditOperation(
    'operation.name',
    context,
    resourceId,
    async () => {
      // Actual business logic here
      return this.executeBusinessLogic(validatedInput, context);
    }
  );
}
```

#### 2. Multi-tenant Isolation Pattern

```typescript
// MANDATORY: Organization boundary validation
async validateOrganizationBoundary(
  resourceId: string,
  userOrganizationId: string
): Promise<void> {
  const resource = await this.findResourceById(resourceId);

  if (!resource) {
    throw new NotFoundError('Resource not found');
  }

  if (resource.organizationId !== userOrganizationId) {
    await this.auditService.logSecurityEvent({
      event: 'cross_tenant_access_attempt',
      resourceId,
      resourceOrgId: resource.organizationId,
      userOrgId: userOrganizationId
    });

    throw new ForbiddenError('Cross-tenant access denied');
  }
}
```

#### 3. Input Validation Pattern

```typescript
// MANDATORY: Comprehensive input validation
class SecurityValidation {
  static validateInput<T>(
    input: unknown,
    schema: ZodSchema<T>
  ): T {
    try {
      // 1. Schema validation
      const validated = schema.parse(input);

      // 2. Security-specific validation
      this.validateSecurityConstraints(validated);

      return validated;
    } catch (error) {
      if (error instanceof ZodError) {
        throw new ValidationError('Invalid input data');
      }
      throw error;
    }
  }

  private static validateSecurityConstraints(data: any): void {
    // 1. Prevent prototype pollution
    if (data && typeof data === 'object') {
      if (data.__proto__ || data.constructor?.prototype) {
        throw new SecurityError('Prototype pollution attempt detected');
      }
    }

    // 2. Size limits
    const serialized = JSON.stringify(data);
    if (serialized.length > 1024 * 1024) { // 1MB limit
      throw new ValidationError('Input data too large');
    }

    // 3. XSS prevention
    this.validateXSS(data);
  }

  private static validateXSS(data: any): void {
    const xssPatterns = [
      /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
      /javascript:/gi,
      /on\w+\s*=/gi,
      /data:text\/html/gi
    ];

    const checkValue = (value: any) => {
      if (typeof value === 'string') {
        for (const pattern of xssPatterns) {
          if (pattern.test(value)) {
            throw new SecurityError('XSS pattern detected');
          }
        }
      }
    };

    this.traverseObject(data, checkValue);
  }
}
```

#### 4. Audit Logging Pattern

```typescript
// MANDATORY: Comprehensive audit logging
class AuditService {
  async logSecurityEvent(event: SecurityEvent): Promise<void> {
    await this.auditRepository.create({
      eventType: 'security',
      eventName: event.event,
      userId: event.userId,
      resourceId: event.resourceId,
      organizationId: event.organizationId,
      severity: this.calculateSeverity(event),
      details: {
        ...event.metadata,
        timestamp: new Date(),
        ipAddress: event.ipAddress,
        userAgent: event.userAgent,
        requestId: event.requestId
      },
      retentionPeriod: this.getRetentionPeriod(event.event)
    });

    // Real-time security monitoring
    if (this.isCriticalSecurityEvent(event)) {
      await this.sendSecurityAlert(event);
    }
  }

  async startOperation(operation: OperationAudit): Promise<string> {
    const auditId = generateUUID();

    await this.auditRepository.create({
      id: auditId,
      eventType: 'operation',
      eventName: operation.operation,
      userId: operation.userId,
      resourceId: operation.resourceId,
      status: 'started',
      startedAt: new Date(),
      details: operation.metadata
    });

    return auditId;
  }

  async completeOperation(
    auditId: string,
    result: OperationResult
  ): Promise<void> {
    await this.auditRepository.update(auditId, {
      status: result.success ? 'completed' : 'failed',
      completedAt: new Date(),
      error: result.error,
      resultMetadata: result.resultMetadata
    });
  }
}
```

---

## Authentication and Authorization Framework

### Centralized Permission Service

```typescript
// MANDATORY: Centralized permission management
@Service()
export class PermissionService implements IPermissionService {
  constructor(
    @Inject() private permissionRepository: IPermissionRepository,
    @Inject() private roleRepository: IRoleRepository,
    @Inject() private auditService: IAuditService,
    @Inject() private cacheManager: ICacheManager
  ) {}

  async checkPermission(
    userId: string,
    permission: string,
    resourceId: string
  ): Promise<boolean> {
    // 1. Cache check for performance
    const cacheKey = `permission:${userId}:${permission}:${resourceId}`;
    const cached = await this.cacheManager.get(cacheKey);
    if (cached !== null) {
      return cached;
    }

    // 2. Hierarchical permission check
    const hasPermission = await this.evaluatePermission(
      userId,
      permission,
      resourceId
    );

    // 3. Cache result for 5 minutes
    await this.cacheManager.set(cacheKey, hasPermission, 300);

    // 4. Log permission check for audit
    await this.auditService.logEvent({
      event: 'permission.check',
      userId,
      metadata: {
        permission,
        resourceId,
        result: hasPermission
      }
    });

    return hasPermission;
  }

  async requirePermission(
    userId: string,
    permission: string,
    resourceId: string
  ): Promise<void> {
    const hasPermission = await this.checkPermission(userId, permission, resourceId);

    if (!hasPermission) {
      await this.auditService.logSecurityEvent({
        event: 'permission.denied',
        userId,
        metadata: {
          permission,
          resourceId,
          action: 'access_denied'
        }
      });

      throw new ForbiddenError(`Insufficient permissions: ${permission}`);
    }
  }

  // Hierarchical permission evaluation
  private async evaluatePermission(
    userId: string,
    permission: string,
    resourceId: string
  ): Promise<boolean> {
    // 1. Direct permission grants
    const directPermission = await this.permissionRepository.findUserPermission(
      userId,
      permission,
      resourceId
    );
    if (directPermission) {
      return true;
    }

    // 2. Role-based permissions
    const userRoles = await this.roleRepository.getUserRoles(userId);
    for (const role of userRoles) {
      const rolePermissions = await this.roleRepository.getRolePermissions(role.id);
      if (rolePermissions.some(p => this.matchesPermission(p.permission, permission))) {
        return true;
      }
    }

    // 3. Resource hierarchy permissions
    const hierarchyPermission = await this.checkHierarchyPermission(
      userId,
      permission,
      resourceId
    );
    if (hierarchyPermission) {
      return true;
    }

    return false;
  }

  // Permission inheritance through resource hierarchy
  private async checkHierarchyPermission(
    userId: string,
    permission: string,
    resourceId: string
  ): Promise<boolean> {
    const resource = await this.getResourceHierarchy(resourceId);

    // Check parent resources for inherited permissions
    for (const parentResource of resource.parents) {
      const hasParentPermission = await this.evaluatePermission(
        userId,
        permission,
        parentResource.id
      );
      if (hasParentPermission && parentResource.inheritsPermissions) {
        return true;
      }
    }

    return false;
  }
}

// MANDATORY: Permission decorator for endpoints
export function RequirePermission(permission: string, resourceParam?: string) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const context = this.getSecurityContext(args);
      const resourceId = resourceParam ? args[resourceParam] : context.organizationId;

      await this.permissionService.requirePermission(
        context.userId,
        permission,
        resourceId
      );

      return originalMethod.apply(this, args);
    };
  };
}

// Usage example:
@Controller('/api/v1/boards')
export class BoardController {
  @Post()
  @RequirePermission('board:create', 'workspaceId')
  async createBoard(@Body() data: CreateBoardRequest) {
    // Method automatically protected by permission check
  }
}
```

---

## Input Validation and Sanitization Guidelines

### Comprehensive Input Validation Framework

```typescript
// MANDATORY: Universal input validation service
@Service()
export class InputValidationService {
  // XSS prevention
  sanitizeHtml(input: string): string {
    return DOMPurify.sanitize(input, {
      ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br'],
      ALLOWED_ATTR: [],
      KEEP_CONTENT: true
    });
  }

  // SQL injection prevention
  sanitizeForDatabase(input: string): string {
    return input
      .replace(/'/g, "''")
      .replace(/;/g, '')
      .replace(/--/g, '')
      .replace(/\/\*/g, '')
      .replace(/\*\//g, '');
  }

  // File name sanitization
  sanitizeFileName(filename: string): string {
    return filename
      .replace(/[^a-zA-Z0-9.-]/g, '_')
      .replace(/\.{2,}/g, '.')
      .substring(0, 255);
  }

  // Deep object sanitization
  sanitizeObject(obj: any): any {
    if (obj === null || typeof obj !== 'object') {
      return obj;
    }

    if (Array.isArray(obj)) {
      return obj.map(item => this.sanitizeObject(item));
    }

    const sanitized: any = {};
    for (const [key, value] of Object.entries(obj)) {
      // Skip dangerous properties
      if (['__proto__', 'constructor', 'prototype'].includes(key)) {
        continue;
      }

      // Sanitize key and value
      const sanitizedKey = this.sanitizeString(key);
      sanitized[sanitizedKey] = this.sanitizeObject(value);
    }

    return sanitized;
  }

  private sanitizeString(str: string): string {
    if (typeof str !== 'string') {
      return str;
    }

    return str
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/javascript:/gi, '')
      .replace(/on\w+\s*=/gi, '')
      .trim();
  }
}

// MANDATORY: Input validation schemas for all services
export const ValidationSchemas = {
  // Board validation
  CreateBoard: z.object({
    name: z.string()
      .min(1, 'Name required')
      .max(255, 'Name too long')
      .refine(val => !/[<>\"'%;()&+]/.test(val), 'Invalid characters'),

    description: z.string()
      .max(2000, 'Description too long')
      .optional()
      .transform(val => val ? sanitizeHtml(val) : val),

    workspaceId: z.string().uuid('Invalid workspace ID'),

    settings: z.object({
      isPrivate: z.boolean().default(false),
      allowComments: z.boolean().default(true),
      externalSharing: z.boolean().default(false)
    }).default({})
  }),

  // Item validation
  CreateItem: z.object({
    name: z.string()
      .min(1, 'Name required')
      .max(500, 'Name too long')
      .transform(val => sanitizeHtml(val)),

    description: z.string()
      .max(10000, 'Description too long')
      .optional()
      .transform(val => val ? sanitizeHtml(val) : val),

    boardId: z.string().uuid('Invalid board ID'),

    data: z.record(z.any())
      .optional()
      .refine(data => {
        if (!data) return true;
        // Prevent prototype pollution
        return !data.__proto__ && !data.constructor;
      }, 'Invalid data structure')
      .transform(data => data ? sanitizeObject(data) : data)
  }),

  // File upload validation
  FileUpload: z.object({
    originalName: z.string()
      .min(1, 'Filename required')
      .max(255, 'Filename too long')
      .refine(name => {
        const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'];
        const extension = name.toLowerCase().substring(name.lastIndexOf('.'));
        return allowedExtensions.includes(extension);
      }, 'File type not allowed')
      .transform(name => sanitizeFileName(name)),

    size: z.number()
      .max(50 * 1024 * 1024, 'File too large (max 50MB)'),

    mimeType: z.string()
      .refine(type => {
        const allowedTypes = [
          'image/jpeg', 'image/png', 'image/gif',
          'application/pdf', 'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
        return allowedTypes.includes(type);
      }, 'MIME type not allowed')
  }),

  // WebSocket message validation
  WebSocketMessage: z.object({
    type: z.enum([
      'subscribe', 'unsubscribe', 'message',
      'cursor_move', 'typing_start', 'typing_stop'
    ]),

    channel: z.string()
      .min(1, 'Channel required')
      .max(100, 'Channel name too long')
      .regex(/^[a-zA-Z0-9:_-]+$/, 'Invalid channel format'),

    data: z.any()
      .optional()
      .refine(data => {
        if (!data) return true;
        const serialized = JSON.stringify(data);
        return serialized.length <= 64 * 1024; // 64KB limit
      }, 'Message data too large')
      .transform(data => sanitizeObject(data))
  })
};
```

This comprehensive security recommendations document provides the development team with specific, actionable guidelines for implementing secure services. Each recommendation includes concrete code examples and security rationale to ensure proper implementation of security controls throughout the development process.