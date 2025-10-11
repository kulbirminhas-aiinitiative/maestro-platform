import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import { AutomationRuleData, AutomationTrigger, AutomationAction } from '@/types';
import { v4 as uuidv4 } from 'uuid';
import { io } from '@/server';

interface AutomationContext {
  trigger: {
    type: string;
    data: any;
  };
  entity: {
    type: 'item' | 'board' | 'workspace' | 'organization';
    id: string;
    data: any;
  };
  user: {
    id: string;
    email: string;
  };
  organization: {
    id: string;
  };
  workspace?: {
    id: string;
  };
  board?: {
    id: string;
  };
}

interface AutomationExecution {
  ruleId: string;
  context: AutomationContext;
  actions: AutomationAction[];
  startTime: Date;
  endTime?: Date;
  status: 'running' | 'completed' | 'failed';
  error?: string;
  results: any[];
}

export class AutomationService {
  /**
   * Create a new automation rule
   */
  static async createRule(
    userId: string,
    scope: 'board' | 'workspace' | 'organization',
    scopeId: string,
    data: AutomationRuleData
  ): Promise<any> {
    try {
      // Verify user has permission to create automation rules
      const hasPermission = await this.verifyAutomationPermission(userId, scope, scopeId);
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Validate trigger and actions
      this.validateTrigger(data.trigger);
      data.actions.forEach(action => this.validateAction(action));

      // Create the rule
      const rule = await prisma.automationRule.create({
        data: {
          id: uuidv4(),
          name: data.name,
          description: data.description,
          triggerConfig: data.trigger,
          conditionConfig: data.conditions || {},
          actionConfig: data.actions,
          isEnabled: data.isEnabled !== false,
          createdBy: userId,
          ...(scope === 'board' && { boardId: scopeId }),
          ...(scope === 'workspace' && { workspaceId: scopeId }),
          ...(scope === 'organization' && { organizationId: scopeId }),
        },
      });

      Logger.automation(`Automation rule created: ${rule.name}`, {
        ruleId: rule.id,
        scope,
        scopeId,
        userId,
      });

      return rule;
    } catch (error) {
      Logger.error('Automation rule creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Update automation rule
   */
  static async updateRule(
    ruleId: string,
    userId: string,
    data: Partial<AutomationRuleData>
  ): Promise<any> {
    try {
      // Get current rule
      const rule = await prisma.automationRule.findUnique({
        where: { id: ruleId },
      });

      if (!rule) {
        throw new Error('Automation rule not found');
      }

      // Verify permission
      const scope = rule.boardId ? 'board' : rule.workspaceId ? 'workspace' : 'organization';
      const scopeId = rule.boardId || rule.workspaceId || rule.organizationId!;
      const hasPermission = await this.verifyAutomationPermission(userId, scope, scopeId);

      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Validate if trigger or actions are being updated
      if (data.trigger) {
        this.validateTrigger(data.trigger);
      }
      if (data.actions) {
        data.actions.forEach(action => this.validateAction(action));
      }

      // Update the rule
      const updatedRule = await prisma.automationRule.update({
        where: { id: ruleId },
        data: {
          name: data.name,
          description: data.description,
          triggerConfig: data.trigger,
          conditionConfig: data.conditions,
          actionConfig: data.actions,
          isEnabled: data.isEnabled,
          updatedAt: new Date(),
        },
      });

      Logger.automation(`Automation rule updated: ${updatedRule.name}`, {
        ruleId,
        userId,
      });

      return updatedRule;
    } catch (error) {
      Logger.error('Automation rule update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete automation rule
   */
  static async deleteRule(ruleId: string, userId: string): Promise<void> {
    try {
      const rule = await prisma.automationRule.findUnique({
        where: { id: ruleId },
      });

      if (!rule) {
        throw new Error('Automation rule not found');
      }

      // Verify permission
      const scope = rule.boardId ? 'board' : rule.workspaceId ? 'workspace' : 'organization';
      const scopeId = rule.boardId || rule.workspaceId || rule.organizationId!;
      const hasPermission = await this.verifyAutomationPermission(userId, scope, scopeId);

      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      await prisma.automationRule.delete({
        where: { id: ruleId },
      });

      Logger.automation(`Automation rule deleted: ${ruleId}`, { ruleId, userId });
    } catch (error) {
      Logger.error('Automation rule deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Get automation rules for a scope
   */
  static async getRules(
    userId: string,
    scope: 'board' | 'workspace' | 'organization',
    scopeId: string
  ): Promise<any[]> {
    try {
      // Verify permission
      const hasPermission = await this.verifyAutomationPermission(userId, scope, scopeId);
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const where: any = {};
      switch (scope) {
        case 'board':
          where.boardId = scopeId;
          break;
        case 'workspace':
          where.workspaceId = scopeId;
          break;
        case 'organization':
          where.organizationId = scopeId;
          break;
      }

      const rules = await prisma.automationRule.findMany({
        where,
        include: {
          createdByUser: {
            select: { id: true, firstName: true, lastName: true, email: true },
          },
        },
        orderBy: { createdAt: 'desc' },
      });

      return rules;
    } catch (error) {
      Logger.error('Get automation rules failed', error as Error);
      throw error;
    }
  }

  /**
   * Execute automation rules for a trigger event
   */
  static async executeAutomations(
    trigger: string,
    context: AutomationContext
  ): Promise<void> {
    try {
      // Find applicable rules
      const rules = await this.findApplicableRules(trigger, context);

      if (rules.length === 0) {
        return;
      }

      Logger.automation(`Executing ${rules.length} automation rules for trigger: ${trigger}`, {
        trigger,
        entityType: context.entity.type,
        entityId: context.entity.id,
      });

      // Execute rules in parallel with individual error handling
      const executions = rules.map(rule => this.executeRule(rule, context));
      await Promise.allSettled(executions);

    } catch (error) {
      Logger.error('Automation execution failed', error as Error);
    }
  }

  /**
   * Toggle automation rule enabled status
   */
  static async toggleRule(ruleId: string, userId: string, enabled: boolean): Promise<any> {
    try {
      const rule = await prisma.automationRule.findUnique({
        where: { id: ruleId },
      });

      if (!rule) {
        throw new Error('Automation rule not found');
      }

      // Verify permission
      const scope = rule.boardId ? 'board' : rule.workspaceId ? 'workspace' : 'organization';
      const scopeId = rule.boardId || rule.workspaceId || rule.organizationId!;
      const hasPermission = await this.verifyAutomationPermission(userId, scope, scopeId);

      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const updatedRule = await prisma.automationRule.update({
        where: { id: ruleId },
        data: { isEnabled: enabled },
      });

      Logger.automation(`Automation rule ${enabled ? 'enabled' : 'disabled'}: ${ruleId}`, {
        ruleId,
        enabled,
        userId,
      });

      return updatedRule;
    } catch (error) {
      Logger.error('Toggle automation rule failed', error as Error);
      throw error;
    }
  }

  /**
   * Get automation execution history
   */
  static async getExecutionHistory(
    ruleId: string,
    userId: string,
    page: number = 1,
    limit: number = 20
  ): Promise<any> {
    try {
      const rule = await prisma.automationRule.findUnique({
        where: { id: ruleId },
      });

      if (!rule) {
        throw new Error('Automation rule not found');
      }

      // Verify permission
      const scope = rule.boardId ? 'board' : rule.workspaceId ? 'workspace' : 'organization';
      const scopeId = rule.boardId || rule.workspaceId || rule.organizationId!;
      const hasPermission = await this.verifyAutomationPermission(userId, scope, scopeId);

      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const offset = (page - 1) * limit;

      const [executions, total] = await Promise.all([
        prisma.automationExecution.findMany({
          where: { ruleId },
          orderBy: { executedAt: 'desc' },
          skip: offset,
          take: limit,
        }),
        prisma.automationExecution.count({ where: { ruleId } }),
      ]);

      return {
        data: executions,
        meta: {
          page,
          limit,
          total,
          totalPages: Math.ceil(total / limit),
          hasNext: page * limit < total,
          hasPrev: page > 1,
        },
      };
    } catch (error) {
      Logger.error('Get execution history failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // TRIGGER HANDLERS
  // ============================================================================

  /**
   * Handle item creation trigger
   */
  static async handleItemCreated(itemId: string, userId: string): Promise<void> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          board: {
            include: {
              workspace: true,
            },
          },
          createdByUser: true,
        },
      });

      if (!item) return;

      const context: AutomationContext = {
        trigger: { type: 'item_created', data: { itemId } },
        entity: { type: 'item', id: itemId, data: item },
        user: { id: userId, email: item.createdByUser.email },
        organization: { id: item.board.workspace.organizationId },
        workspace: { id: item.board.workspaceId },
        board: { id: item.boardId },
      };

      await this.executeAutomations('item_created', context);
    } catch (error) {
      Logger.error('Handle item created trigger failed', error as Error);
    }
  }

  /**
   * Handle item updated trigger
   */
  static async handleItemUpdated(
    itemId: string,
    userId: string,
    oldValues: any,
    newValues: any
  ): Promise<void> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          board: {
            include: {
              workspace: true,
            },
          },
        },
      });

      if (!item) return;

      const user = await prisma.user.findUnique({ where: { id: userId } });
      if (!user) return;

      const context: AutomationContext = {
        trigger: {
          type: 'item_updated',
          data: { itemId, oldValues, newValues },
        },
        entity: { type: 'item', id: itemId, data: item },
        user: { id: userId, email: user.email },
        organization: { id: item.board.workspace.organizationId },
        workspace: { id: item.board.workspaceId },
        board: { id: item.boardId },
      };

      await this.executeAutomations('item_updated', context);
    } catch (error) {
      Logger.error('Handle item updated trigger failed', error as Error);
    }
  }

  /**
   * Handle status change trigger
   */
  static async handleStatusChanged(
    itemId: string,
    userId: string,
    oldStatus: string,
    newStatus: string
  ): Promise<void> {
    try {
      const context: AutomationContext = await this.buildItemContext(itemId, userId, {
        type: 'status_changed',
        data: { itemId, oldStatus, newStatus },
      });

      await this.executeAutomations('status_changed', context);
    } catch (error) {
      Logger.error('Handle status changed trigger failed', error as Error);
    }
  }

  /**
   * Handle assignment trigger
   */
  static async handleItemAssigned(
    itemId: string,
    assigneeId: string,
    assignedBy: string
  ): Promise<void> {
    try {
      const context: AutomationContext = await this.buildItemContext(itemId, assignedBy, {
        type: 'item_assigned',
        data: { itemId, assigneeId, assignedBy },
      });

      await this.executeAutomations('item_assigned', context);
    } catch (error) {
      Logger.error('Handle item assigned trigger failed', error as Error);
    }
  }

  /**
   * Handle due date trigger
   */
  static async handleDueDateApproaching(itemId: string): Promise<void> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          board: { include: { workspace: true } },
          createdByUser: true,
        },
      });

      if (!item) return;

      const context: AutomationContext = {
        trigger: { type: 'due_date_approaching', data: { itemId } },
        entity: { type: 'item', id: itemId, data: item },
        user: { id: item.createdBy, email: item.createdByUser.email },
        organization: { id: item.board.workspace.organizationId },
        workspace: { id: item.board.workspaceId },
        board: { id: item.boardId },
      };

      await this.executeAutomations('due_date_approaching', context);
    } catch (error) {
      Logger.error('Handle due date approaching trigger failed', error as Error);
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Find applicable automation rules for a trigger
   */
  private static async findApplicableRules(
    trigger: string,
    context: AutomationContext
  ): Promise<any[]> {
    const where: any = {
      isEnabled: true,
      triggerConfig: {
        path: ['type'],
        equals: trigger,
      },
    };

    // Add scope filters based on context
    const orConditions = [];

    if (context.board) {
      orConditions.push({ boardId: context.board.id });
    }

    if (context.workspace) {
      orConditions.push({ workspaceId: context.workspace.id });
    }

    if (context.organization) {
      orConditions.push({ organizationId: context.organization.id });
    }

    if (orConditions.length > 0) {
      where.OR = orConditions;
    }

    const rules = await prisma.automationRule.findMany({
      where,
      include: {
        createdByUser: true,
      },
    });

    // Filter by conditions
    return rules.filter(rule => this.evaluateConditions(rule.conditionConfig, context));
  }

  /**
   * Execute a single automation rule
   */
  private static async executeRule(rule: any, context: AutomationContext): Promise<void> {
    const execution: AutomationExecution = {
      ruleId: rule.id,
      context,
      actions: rule.actionConfig,
      startTime: new Date(),
      status: 'running',
      results: [],
    };

    try {
      Logger.automation(`Executing automation rule: ${rule.name}`, {
        ruleId: rule.id,
        trigger: context.trigger.type,
      });

      // Execute each action
      for (const action of execution.actions) {
        try {
          const result = await this.executeAction(action, context);
          execution.results.push({ action: action.type, success: true, result });
        } catch (actionError) {
          Logger.error(`Action execution failed: ${action.type}`, actionError as Error);
          execution.results.push({
            action: action.type,
            success: false,
            error: (actionError as Error).message,
          });
        }
      }

      execution.status = 'completed';
      execution.endTime = new Date();

      // Update execution count
      await prisma.automationRule.update({
        where: { id: rule.id },
        data: {
          executionCount: { increment: 1 },
          lastExecutedAt: new Date(),
        },
      });

      // Log execution
      await this.logExecution(execution);

      Logger.automation(`Automation rule completed: ${rule.name}`, {
        ruleId: rule.id,
        processingTime: execution.endTime.getTime() - execution.startTime.getTime(),
      });

    } catch (error) {
      execution.status = 'failed';
      execution.error = (error as Error).message;
      execution.endTime = new Date();

      await this.logExecution(execution);

      Logger.error(`Automation rule failed: ${rule.name}`, error as Error);
    }
  }

  /**
   * Execute a single automation action
   */
  private static async executeAction(action: AutomationAction, context: AutomationContext): Promise<any> {
    switch (action.type) {
      case 'update_item':
        return await this.executeUpdateItemAction(action, context);

      case 'assign_user':
        return await this.executeAssignUserAction(action, context);

      case 'create_item':
        return await this.executeCreateItemAction(action, context);

      case 'send_notification':
        return await this.executeSendNotificationAction(action, context);

      case 'move_item':
        return await this.executeMoveItemAction(action, context);

      case 'add_comment':
        return await this.executeAddCommentAction(action, context);

      case 'webhook':
        return await this.executeWebhookAction(action, context);

      default:
        throw new Error(`Unknown action type: ${action.type}`);
    }
  }

  /**
   * Execute update item action
   */
  private static async executeUpdateItemAction(
    action: AutomationAction,
    context: AutomationContext
  ): Promise<any> {
    const { itemId = context.entity.id, updates } = action.parameters;

    return await prisma.item.update({
      where: { id: itemId },
      data: {
        ...updates,
        updatedAt: new Date(),
      },
    });
  }

  /**
   * Execute assign user action
   */
  private static async executeAssignUserAction(
    action: AutomationAction,
    context: AutomationContext
  ): Promise<any> {
    const { itemId = context.entity.id, userId } = action.parameters;

    // Check if assignment already exists
    const existingAssignment = await prisma.itemAssignment.findFirst({
      where: { itemId, userId },
    });

    if (existingAssignment) {
      return existingAssignment;
    }

    return await prisma.itemAssignment.create({
      data: {
        itemId,
        userId,
        assignedBy: context.user.id,
      },
    });
  }

  /**
   * Execute create item action
   */
  private static async executeCreateItemAction(
    action: AutomationAction,
    context: AutomationContext
  ): Promise<any> {
    const { boardId = context.board?.id, name, description, data } = action.parameters;

    if (!boardId) {
      throw new Error('Board ID required for create item action');
    }

    return await prisma.item.create({
      data: {
        id: uuidv4(),
        boardId,
        name,
        description,
        itemData: data || {},
        position: 1, // Add to top
        createdBy: context.user.id,
      },
    });
  }

  /**
   * Execute send notification action
   */
  private static async executeSendNotificationAction(
    action: AutomationAction,
    context: AutomationContext
  ): Promise<any> {
    const { recipientId, message, type = 'info' } = action.parameters;

    // Send real-time notification via WebSocket
    if (io) {
      io.to(`user:${recipientId}`).emit('notification', {
        id: uuidv4(),
        type,
        title: 'Automation Notification',
        message,
        timestamp: new Date().toISOString(),
        data: {
          automationRuleId: context.trigger.data.ruleId,
          entityType: context.entity.type,
          entityId: context.entity.id,
        },
      });
    }

    return { sent: true, recipientId, message };
  }

  /**
   * Execute move item action
   */
  private static async executeMoveItemAction(
    action: AutomationAction,
    context: AutomationContext
  ): Promise<any> {
    const { itemId = context.entity.id, targetBoardId, position } = action.parameters;

    return await prisma.item.update({
      where: { id: itemId },
      data: {
        boardId: targetBoardId,
        position: position || 1,
        updatedAt: new Date(),
      },
    });
  }

  /**
   * Execute add comment action
   */
  private static async executeAddCommentAction(
    action: AutomationAction,
    context: AutomationContext
  ): Promise<any> {
    const { itemId = context.entity.id, content } = action.parameters;

    return await prisma.comment.create({
      data: {
        id: uuidv4(),
        itemId,
        userId: context.user.id,
        content,
        contentType: 'text',
      },
    });
  }

  /**
   * Execute webhook action
   */
  private static async executeWebhookAction(
    action: AutomationAction,
    context: AutomationContext
  ): Promise<any> {
    const { url, method = 'POST', headers = {}, payload } = action.parameters;

    // In a real implementation, this would make an HTTP request
    // For now, we'll simulate the webhook
    Logger.automation('Webhook action executed', {
      url,
      method,
      payload: JSON.stringify(payload),
    });

    return { sent: true, url, method };
  }

  /**
   * Evaluate automation conditions
   */
  private static evaluateConditions(conditions: any, context: AutomationContext): boolean {
    if (!conditions || Object.keys(conditions).length === 0) {
      return true; // No conditions means always execute
    }

    // Simple condition evaluation
    // In a real implementation, this would be more sophisticated
    for (const [key, value] of Object.entries(conditions)) {
      const contextValue = this.getContextValue(context, key);
      if (contextValue !== value) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get value from automation context
   */
  private static getContextValue(context: AutomationContext, path: string): any {
    const parts = path.split('.');
    let current: any = context;

    for (const part of parts) {
      if (current && typeof current === 'object' && part in current) {
        current = current[part];
      } else {
        return undefined;
      }
    }

    return current;
  }

  /**
   * Build item context for triggers
   */
  private static async buildItemContext(
    itemId: string,
    userId: string,
    trigger: any
  ): Promise<AutomationContext> {
    const item = await prisma.item.findUnique({
      where: { id: itemId },
      include: {
        board: {
          include: {
            workspace: true,
          },
        },
      },
    });

    const user = await prisma.user.findUnique({ where: { id: userId } });

    if (!item || !user) {
      throw new Error('Item or user not found');
    }

    return {
      trigger,
      entity: { type: 'item', id: itemId, data: item },
      user: { id: userId, email: user.email },
      organization: { id: item.board.workspace.organizationId },
      workspace: { id: item.board.workspaceId },
      board: { id: item.boardId },
    };
  }

  /**
   * Log automation execution
   */
  private static async logExecution(execution: AutomationExecution): Promise<void> {
    try {
      await prisma.automationExecution.create({
        data: {
          id: uuidv4(),
          ruleId: execution.ruleId,
          itemId: execution.context.entity.type === 'item' ? execution.context.entity.id : undefined,
          triggerData: execution.context.trigger,
          executionStatus: execution.status,
          errorMessage: execution.error,
          executionTimeMs: execution.endTime
            ? execution.endTime.getTime() - execution.startTime.getTime()
            : undefined,
          executedAt: execution.startTime,
        },
      });
    } catch (error) {
      Logger.error('Failed to log automation execution', error as Error);
    }
  }

  /**
   * Verify automation permission
   */
  private static async verifyAutomationPermission(
    userId: string,
    scope: string,
    scopeId: string
  ): Promise<boolean> {
    try {
      switch (scope) {
        case 'board':
          const boardAccess = await prisma.board.findFirst({
            where: {
              id: scopeId,
              OR: [
                {
                  members: {
                    some: {
                      userId,
                      role: { in: ['owner', 'admin'] },
                    },
                  },
                },
                {
                  workspace: {
                    members: {
                      some: {
                        userId,
                        role: 'admin',
                      },
                    },
                  },
                },
              ],
            },
          });
          return !!boardAccess;

        case 'workspace':
          const workspaceAccess = await prisma.workspace.findFirst({
            where: {
              id: scopeId,
              OR: [
                {
                  members: {
                    some: {
                      userId,
                      role: 'admin',
                    },
                  },
                },
                {
                  organization: {
                    members: {
                      some: {
                        userId,
                        status: 'active',
                        role: { in: ['owner', 'admin'] },
                      },
                    },
                  },
                },
              ],
            },
          });
          return !!workspaceAccess;

        case 'organization':
          const orgAccess = await prisma.organizationMember.findFirst({
            where: {
              organizationId: scopeId,
              userId,
              status: 'active',
              role: { in: ['owner', 'admin'] },
            },
          });
          return !!orgAccess;

        default:
          return false;
      }
    } catch (error) {
      Logger.error('Verify automation permission failed', error as Error);
      return false;
    }
  }

  /**
   * Validate automation trigger
   */
  private static validateTrigger(trigger: AutomationTrigger): void {
    const validTriggers = [
      'item_created',
      'item_updated',
      'status_changed',
      'item_assigned',
      'due_date_approaching',
      'board_created',
      'member_added',
    ];

    if (!validTriggers.includes(trigger.type)) {
      throw new Error(`Invalid trigger type: ${trigger.type}`);
    }
  }

  /**
   * Validate automation action
   */
  private static validateAction(action: AutomationAction): void {
    const validActions = [
      'update_item',
      'assign_user',
      'create_item',
      'send_notification',
      'move_item',
      'add_comment',
      'webhook',
    ];

    if (!validActions.includes(action.type)) {
      throw new Error(`Invalid action type: ${action.type}`);
    }

    // Validate required parameters for each action type
    switch (action.type) {
      case 'update_item':
        if (!action.parameters.updates) {
          throw new Error('update_item action requires updates parameter');
        }
        break;
      case 'assign_user':
        if (!action.parameters.userId) {
          throw new Error('assign_user action requires userId parameter');
        }
        break;
      case 'create_item':
        if (!action.parameters.name) {
          throw new Error('create_item action requires name parameter');
        }
        break;
      case 'send_notification':
        if (!action.parameters.recipientId || !action.parameters.message) {
          throw new Error('send_notification action requires recipientId and message parameters');
        }
        break;
      case 'webhook':
        if (!action.parameters.url) {
          throw new Error('webhook action requires url parameter');
        }
        break;
    }
  }
}