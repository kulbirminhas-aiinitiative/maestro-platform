import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { io } from '@/server';
import { AutomationRuleData, AutomationTrigger, AutomationAction } from '@/types';

interface AutomationExecution {
  ruleId: string;
  triggeredBy: any;
  executedActions: Array<{
    type: string;
    success: boolean;
    result?: any;
    error?: string;
  }>;
  executedAt: Date;
}

interface TriggerContext {
  entityType: 'item' | 'board' | 'user';
  entityId: string;
  action: string;
  oldValues?: any;
  newValues?: any;
  userId: string;
  organizationId: string;
  workspaceId?: string;
  boardId?: string;
}

export class AutomationService {
  private static readonly EXECUTION_TIMEOUT = 30000; // 30 seconds
  private static readonly MAX_EXECUTIONS_PER_MINUTE = 100;

  /**
   * Create a new automation rule
   */
  static async createRule(
    ruleData: AutomationRuleData,
    createdBy: string,
    organizationId: string,
    boardId?: string
  ): Promise<any> {
    try {
      // Validate rule configuration
      this.validateRule(ruleData);

      const rule = await prisma.automationRule.create({
        data: {
          name: ruleData.name,
          description: ruleData.description,
          trigger: ruleData.trigger,
          conditions: ruleData.conditions || {},
          actions: ruleData.actions,
          isEnabled: ruleData.isEnabled ?? true,
          createdBy,
          organizationId,
          boardId,
        },
      });

      Logger.business(`Automation rule created: ${rule.name}`, {
        ruleId: rule.id,
        createdBy,
        organizationId,
        boardId,
      });

      return rule;
    } catch (error) {
      Logger.error('Automation rule creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Update an automation rule
   */
  static async updateRule(
    ruleId: string,
    updates: Partial<AutomationRuleData>,
    userId: string
  ): Promise<any> {
    try {
      // Validate updates if provided
      if (updates.trigger || updates.actions) {
        this.validateRule(updates as AutomationRuleData);
      }

      const rule = await prisma.automationRule.update({
        where: { id: ruleId },
        data: {
          ...(updates.name && { name: updates.name }),
          ...(updates.description && { description: updates.description }),
          ...(updates.trigger && { trigger: updates.trigger }),
          ...(updates.conditions && { conditions: updates.conditions }),
          ...(updates.actions && { actions: updates.actions }),
          ...(updates.isEnabled !== undefined && { isEnabled: updates.isEnabled }),
          updatedAt: new Date(),
        },
      });

      Logger.business(`Automation rule updated: ${rule.name}`, {
        ruleId,
        userId,
      });

      return rule;
    } catch (error) {
      Logger.error('Automation rule update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete an automation rule
   */
  static async deleteRule(ruleId: string, userId: string): Promise<void> {
    try {
      await prisma.automationRule.update({
        where: { id: ruleId },
        data: { deletedAt: new Date() },
      });

      Logger.business(`Automation rule deleted`, {
        ruleId,
        userId,
      });
    } catch (error) {
      Logger.error('Automation rule deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Get automation rules for a scope
   */
  static async getRules(
    organizationId: string,
    boardId?: string,
    includeDisabled = false
  ): Promise<any[]> {
    try {
      const rules = await prisma.automationRule.findMany({
        where: {
          organizationId,
          ...(boardId && { boardId }),
          deletedAt: null,
          ...(includeDisabled ? {} : { isEnabled: true }),
        },
        orderBy: { createdAt: 'desc' },
      });

      return rules;
    } catch (error) {
      Logger.error('Failed to get automation rules', error as Error);
      throw error;
    }
  }

  /**
   * Execute automation rules for a given trigger context
   */
  static async executeTrigger(context: TriggerContext): Promise<void> {
    try {
      // Check rate limiting
      if (!(await this.checkRateLimit(context.organizationId))) {
        Logger.api('Automation execution rate limited', { organizationId: context.organizationId });
        return;
      }

      // Find matching rules
      const matchingRules = await this.findMatchingRules(context);

      if (matchingRules.length === 0) {
        return;
      }

      Logger.automation(`Executing ${matchingRules.length} automation rules`, {
        trigger: context.action,
        entityType: context.entityType,
        entityId: context.entityId,
      });

      // Execute rules in parallel
      await Promise.allSettled(
        matchingRules.map(rule => this.executeRule(rule, context))
      );

    } catch (error) {
      Logger.error('Automation trigger execution failed', error as Error);
      // Don't throw error to prevent breaking the main flow
    }
  }

  /**
   * Test an automation rule without executing actions
   */
  static async testRule(
    ruleId: string,
    testContext: TriggerContext
  ): Promise<{
    triggered: boolean;
    conditionResults: Record<string, boolean>;
    simulatedActions: Array<{
      type: string;
      parameters: any;
      wouldExecute: boolean;
    }>;
  }> {
    try {
      const rule = await prisma.automationRule.findUnique({
        where: { id: ruleId },
      });

      if (!rule) {
        throw new Error('Automation rule not found');
      }

      const triggered = this.matchesTrigger(rule.trigger as AutomationTrigger, testContext);
      const conditionResults = triggered
        ? this.evaluateConditions(rule.conditions as Record<string, any>, testContext)
        : {};

      const allConditionsMet = Object.values(conditionResults).every(Boolean);

      const simulatedActions = (rule.actions as AutomationAction[]).map(action => ({
        type: action.type,
        parameters: action.parameters,
        wouldExecute: triggered && allConditionsMet,
      }));

      return {
        triggered,
        conditionResults,
        simulatedActions,
      };
    } catch (error) {
      Logger.error('Automation rule test failed', error as Error);
      throw error;
    }
  }

  /**
   * Get automation execution history
   */
  static async getExecutionHistory(
    organizationId: string,
    ruleId?: string,
    limit = 50
  ): Promise<AutomationExecution[]> {
    try {
      const executions = await prisma.automationExecution.findMany({
        where: {
          organizationId,
          ...(ruleId && { ruleId }),
        },
        orderBy: { executedAt: 'desc' },
        take: limit,
      });

      return executions.map(execution => ({
        ruleId: execution.ruleId,
        triggeredBy: execution.triggeredBy,
        executedActions: execution.executedActions as any,
        executedAt: execution.executedAt,
      }));
    } catch (error) {
      Logger.error('Failed to get execution history', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Validate automation rule configuration
   */
  private static validateRule(rule: Partial<AutomationRuleData>): void {
    if (rule.trigger) {
      if (!rule.trigger.type || !rule.trigger.conditions) {
        throw new Error('Invalid trigger configuration');
      }
    }

    if (rule.actions) {
      if (!Array.isArray(rule.actions) || rule.actions.length === 0) {
        throw new Error('At least one action is required');
      }

      for (const action of rule.actions) {
        if (!action.type || !action.parameters) {
          throw new Error('Invalid action configuration');
        }
      }
    }
  }

  /**
   * Check rate limiting for automation executions
   */
  private static async checkRateLimit(organizationId: string): Promise<boolean> {
    try {
      const key = `automation:rate_limit:${organizationId}`;
      const currentCount = await RedisService.getCache(key) || '0';
      const count = parseInt(currentCount, 10);

      if (count >= this.MAX_EXECUTIONS_PER_MINUTE) {
        return false;
      }

      await RedisService.setCache(key, (count + 1).toString(), 60); // 1 minute TTL
      return true;
    } catch (error) {
      Logger.error('Rate limit check failed', error as Error);
      return true; // Allow execution if rate limit check fails
    }
  }

  /**
   * Find automation rules that match the trigger context
   */
  private static async findMatchingRules(context: TriggerContext): Promise<any[]> {
    try {
      const rules = await prisma.automationRule.findMany({
        where: {
          organizationId: context.organizationId,
          ...(context.boardId && {
            OR: [
              { boardId: context.boardId },
              { boardId: null }, // Organization-wide rules
            ]
          }),
          isEnabled: true,
          deletedAt: null,
        },
      });

      return rules.filter(rule =>
        this.matchesTrigger(rule.trigger as AutomationTrigger, context)
      );
    } catch (error) {
      Logger.error('Failed to find matching rules', error as Error);
      return [];
    }
  }

  /**
   * Check if a trigger matches the context
   */
  private static matchesTrigger(trigger: AutomationTrigger, context: TriggerContext): boolean {
    // Match trigger type
    if (trigger.type !== context.action) {
      return false;
    }

    // Match entity type if specified
    if (trigger.conditions.entityType && trigger.conditions.entityType !== context.entityType) {
      return false;
    }

    // Additional trigger-specific matching
    switch (trigger.type) {
      case 'item_created':
      case 'item_updated':
      case 'item_deleted':
        return context.entityType === 'item';

      case 'item_status_changed':
        return context.entityType === 'item' &&
               context.oldValues?.status !== context.newValues?.status;

      case 'item_assigned':
        return context.entityType === 'item' &&
               context.newValues?.assigneeIds?.length > (context.oldValues?.assigneeIds?.length || 0);

      case 'item_due_date_approaching':
        // This would be triggered by a scheduled job
        return context.action === 'item_due_date_approaching';

      default:
        return true;
    }
  }

  /**
   * Evaluate rule conditions
   */
  private static evaluateConditions(
    conditions: Record<string, any>,
    context: TriggerContext
  ): Record<string, boolean> {
    const results: Record<string, boolean> = {};

    for (const [key, condition] of Object.entries(conditions)) {
      try {
        switch (key) {
          case 'status':
            results[key] = this.evaluateStatusCondition(condition, context);
            break;

          case 'assignee':
            results[key] = this.evaluateAssigneeCondition(condition, context);
            break;

          case 'priority':
            results[key] = this.evaluatePriorityCondition(condition, context);
            break;

          case 'dueDate':
            results[key] = this.evaluateDueDateCondition(condition, context);
            break;

          case 'tags':
            results[key] = this.evaluateTagsCondition(condition, context);
            break;

          default:
            results[key] = true; // Unknown conditions default to true
        }
      } catch (error) {
        Logger.error(`Condition evaluation failed for ${key}`, error as Error);
        results[key] = false;
      }
    }

    return results;
  }

  /**
   * Evaluate status condition
   */
  private static evaluateStatusCondition(condition: any, context: TriggerContext): boolean {
    const currentStatus = context.newValues?.status || context.newValues?.itemData?.status;

    if (condition.equals) {
      return currentStatus === condition.equals;
    }

    if (condition.in) {
      return condition.in.includes(currentStatus);
    }

    if (condition.changed) {
      return context.oldValues?.status !== context.newValues?.status;
    }

    return false;
  }

  /**
   * Evaluate assignee condition
   */
  private static evaluateAssigneeCondition(condition: any, context: TriggerContext): boolean {
    const assigneeIds = context.newValues?.assigneeIds || [];

    if (condition.includes) {
      return assigneeIds.includes(condition.includes);
    }

    if (condition.count) {
      const count = assigneeIds.length;
      if (condition.count.gt) return count > condition.count.gt;
      if (condition.count.lt) return count < condition.count.lt;
      if (condition.count.eq) return count === condition.count.eq;
    }

    return false;
  }

  /**
   * Evaluate priority condition
   */
  private static evaluatePriorityCondition(condition: any, context: TriggerContext): boolean {
    const priority = context.newValues?.itemData?.priority;

    if (condition.equals) {
      return priority === condition.equals;
    }

    if (condition.in) {
      return condition.in.includes(priority);
    }

    return false;
  }

  /**
   * Evaluate due date condition
   */
  private static evaluateDueDateCondition(condition: any, context: TriggerContext): boolean {
    const dueDate = context.newValues?.itemData?.dueDate;

    if (!dueDate) return false;

    const dueDateObj = new Date(dueDate);
    const now = new Date();

    if (condition.approaching) {
      const hoursUntilDue = (dueDateObj.getTime() - now.getTime()) / (1000 * 60 * 60);
      return hoursUntilDue <= condition.approaching && hoursUntilDue > 0;
    }

    if (condition.overdue) {
      return dueDateObj < now;
    }

    return false;
  }

  /**
   * Evaluate tags condition
   */
  private static evaluateTagsCondition(condition: any, context: TriggerContext): boolean {
    const tags = context.newValues?.itemData?.tags || [];

    if (condition.includes) {
      return condition.includes.some((tag: string) => tags.includes(tag));
    }

    if (condition.excludes) {
      return !condition.excludes.some((tag: string) => tags.includes(tag));
    }

    return false;
  }

  /**
   * Execute a single automation rule
   */
  private static async executeRule(rule: any, context: TriggerContext): Promise<void> {
    try {
      // Evaluate conditions
      const conditionResults = this.evaluateConditions(
        rule.conditions as Record<string, any>,
        context
      );

      const allConditionsMet = Object.values(conditionResults).every(Boolean);

      if (!allConditionsMet) {
        Logger.automation(`Rule conditions not met: ${rule.name}`, {
          ruleId: rule.id,
          conditionResults,
        });
        return;
      }

      // Execute actions
      const executedActions: any[] = [];

      for (const action of rule.actions as AutomationAction[]) {
        try {
          const result = await this.executeAction(action, context);
          executedActions.push({
            type: action.type,
            success: true,
            result,
          });
        } catch (error) {
          Logger.error(`Action execution failed: ${action.type}`, error as Error);
          executedActions.push({
            type: action.type,
            success: false,
            error: (error as Error).message,
          });
        }
      }

      // Log execution
      await prisma.automationExecution.create({
        data: {
          ruleId: rule.id,
          organizationId: context.organizationId,
          triggeredBy: {
            entityType: context.entityType,
            entityId: context.entityId,
            action: context.action,
            userId: context.userId,
          },
          executedActions,
          executedAt: new Date(),
        },
      });

      Logger.automation(`Rule executed successfully: ${rule.name}`, {
        ruleId: rule.id,
        actionsExecuted: executedActions.length,
        successfulActions: executedActions.filter(a => a.success).length,
      });

    } catch (error) {
      Logger.error(`Rule execution failed: ${rule.name}`, error as Error);
    }
  }

  /**
   * Execute a single automation action
   */
  private static async executeAction(action: AutomationAction, context: TriggerContext): Promise<any> {
    switch (action.type) {
      case 'update_item_status':
        return this.executeUpdateItemStatus(action.parameters, context);

      case 'assign_item':
        return this.executeAssignItem(action.parameters, context);

      case 'send_notification':
        return this.executeSendNotification(action.parameters, context);

      case 'create_item':
        return this.executeCreateItem(action.parameters, context);

      case 'move_item':
        return this.executeMoveItem(action.parameters, context);

      case 'add_comment':
        return this.executeAddComment(action.parameters, context);

      case 'update_due_date':
        return this.executeUpdateDueDate(action.parameters, context);

      case 'send_email':
        return this.executeSendEmail(action.parameters, context);

      default:
        throw new Error(`Unknown action type: ${action.type}`);
    }
  }

  /**
   * Execute update item status action
   */
  private static async executeUpdateItemStatus(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    if (context.entityType !== 'item') {
      throw new Error('Update item status can only be applied to items');
    }

    const newStatus = parameters.status;

    await prisma.item.update({
      where: { id: context.entityId },
      data: {
        itemData: {
          ...(context.newValues?.itemData || {}),
          status: newStatus,
        },
      },
    });

    // Emit real-time update
    io.to(`board:${context.boardId}`).emit('item_updated', {
      itemId: context.entityId,
      changes: { status: newStatus },
      updatedBy: 'automation',
    });

    return { status: newStatus };
  }

  /**
   * Execute assign item action
   */
  private static async executeAssignItem(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    if (context.entityType !== 'item') {
      throw new Error('Assign item can only be applied to items');
    }

    const { userId, assignedBy } = parameters;

    await prisma.itemAssignment.create({
      data: {
        itemId: context.entityId,
        userId,
        assignedBy: assignedBy || 'automation',
      },
    });

    return { assignedTo: userId };
  }

  /**
   * Execute send notification action
   */
  private static async executeSendNotification(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    const { userIds, message, type = 'automation' } = parameters;

    // Create notifications for specified users
    for (const userId of userIds) {
      await prisma.notification.create({
        data: {
          userId,
          type,
          title: 'Automation Notification',
          message,
          data: {
            entityType: context.entityType,
            entityId: context.entityId,
            triggeredBy: context.action,
          },
        },
      });
    }

    // Emit real-time notifications
    userIds.forEach((userId: string) => {
      io.to(`user:${userId}`).emit('notification', {
        type,
        message,
        entityType: context.entityType,
        entityId: context.entityId,
      });
    });

    return { notifiedUsers: userIds.length };
  }

  /**
   * Execute create item action
   */
  private static async executeCreateItem(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    const { name, description, boardId, itemData = {} } = parameters;

    const item = await prisma.item.create({
      data: {
        name,
        description,
        boardId: boardId || context.boardId,
        itemData,
        createdBy: context.userId,
        position: new Decimal(Date.now()), // Simple position assignment
      },
    });

    return { itemId: item.id };
  }

  /**
   * Execute move item action
   */
  private static async executeMoveItem(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    if (context.entityType !== 'item') {
      throw new Error('Move item can only be applied to items');
    }

    const { columnId, position } = parameters;

    await prisma.item.update({
      where: { id: context.entityId },
      data: {
        itemData: {
          ...(context.newValues?.itemData || {}),
          columnId,
        },
        ...(position && { position: new Decimal(position) }),
      },
    });

    return { columnId, position };
  }

  /**
   * Execute add comment action
   */
  private static async executeAddComment(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    if (context.entityType !== 'item') {
      throw new Error('Add comment can only be applied to items');
    }

    const { content } = parameters;

    const comment = await prisma.comment.create({
      data: {
        content,
        itemId: context.entityId,
        userId: context.userId,
        metadata: {
          createdBy: 'automation',
          trigger: context.action,
        },
      },
    });

    return { commentId: comment.id };
  }

  /**
   * Execute update due date action
   */
  private static async executeUpdateDueDate(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    if (context.entityType !== 'item') {
      throw new Error('Update due date can only be applied to items');
    }

    const { dueDate, addDays } = parameters;

    let newDueDate: Date;

    if (dueDate) {
      newDueDate = new Date(dueDate);
    } else if (addDays) {
      newDueDate = new Date();
      newDueDate.setDate(newDueDate.getDate() + addDays);
    } else {
      throw new Error('Either dueDate or addDays must be specified');
    }

    await prisma.item.update({
      where: { id: context.entityId },
      data: {
        itemData: {
          ...(context.newValues?.itemData || {}),
          dueDate: newDueDate.toISOString(),
        },
      },
    });

    return { dueDate: newDueDate.toISOString() };
  }

  /**
   * Execute send email action
   */
  private static async executeSendEmail(
    parameters: any,
    context: TriggerContext
  ): Promise<any> {
    // This would integrate with an email service like SendGrid, AWS SES, etc.
    const { to, subject, template, data } = parameters;

    Logger.business('Email automation triggered', {
      to: Array.isArray(to) ? to.length : 1,
      subject,
      template,
      entityType: context.entityType,
      entityId: context.entityId,
    });

    // For now, just log the email action
    // In production, you would integrate with your email service here

    return { emailsSent: Array.isArray(to) ? to.length : 1 };
  }
}