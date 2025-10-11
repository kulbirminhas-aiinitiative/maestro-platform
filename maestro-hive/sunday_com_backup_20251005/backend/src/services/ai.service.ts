import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { config } from '@/config';
import OpenAI from 'openai';

interface TaskSuggestion {
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  estimatedDuration?: number; // in minutes
  tags: string[];
  confidence: number; // 0-1
}

interface AutoTagResult {
  tags: string[];
  categories: string[];
  priority: 'low' | 'medium' | 'high';
  confidence: number;
}

interface WorkloadRecommendation {
  userId: string;
  currentWorkload: number;
  recommendedTasks: number;
  reason: string;
  suggestions: string[];
}

export class AIService {
  private static openai: OpenAI;

  /**
   * Initialize OpenAI client
   */
  static initialize(): void {
    if (!config.openai?.apiKey) {
      Logger.api('AI service disabled - no OpenAI API key provided');
      return;
    }

    this.openai = new OpenAI({
      apiKey: config.openai.apiKey,
    });

    Logger.api('AI service initialized with OpenAI integration');
  }

  /**
   * Generate smart task suggestions based on board patterns and history
   */
  static async generateTaskSuggestions(
    boardId: string,
    userId: string,
    context?: string,
    limit = 5
  ): Promise<TaskSuggestion[]> {
    try {
      if (!this.openai) {
        throw new Error('AI service not available');
      }

      // Get board context and patterns
      const boardContext = await this.getBoardContext(boardId);
      const userPatterns = await this.getUserPatterns(userId, boardId);

      const prompt = this.buildTaskSuggestionPrompt(
        boardContext,
        userPatterns,
        context,
        limit
      );

      const completion = await this.openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are a project management AI assistant. Generate practical, actionable task suggestions based on board patterns and user context. Return only valid JSON.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 1000,
      });

      const response = completion.choices[0]?.message?.content;
      if (!response) {
        throw new Error('No response from AI service');
      }

      const suggestions = JSON.parse(response) as TaskSuggestion[];

      // Cache suggestions for faster access
      await RedisService.setCache(
        `ai:suggestions:${boardId}:${userId}`,
        suggestions,
        3600 // 1 hour
      );

      Logger.business('Task suggestions generated', {
        boardId,
        userId,
        suggestionsCount: suggestions.length,
      });

      return suggestions;
    } catch (error) {
      Logger.error('Task suggestion generation failed', error as Error);
      throw new Error('Failed to generate task suggestions');
    }
  }

  /**
   * Auto-tag items using NLP analysis
   */
  static async autoTagItem(
    itemId: string,
    title: string,
    description?: string
  ): Promise<AutoTagResult> {
    try {
      if (!this.openai) {
        throw new Error('AI service not available');
      }

      // Check cache first
      const cacheKey = `ai:tags:${itemId}`;
      const cached = await RedisService.getCache(cacheKey);
      if (cached) {
        return cached;
      }

      // Get item's board context for better tagging
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          board: {
            include: {
              items: {
                where: { deletedAt: null },
                select: {
                  name: true,
                  itemData: true,
                },
                take: 20, // Recent items for context
              },
            },
          },
        },
      });

      if (!item) {
        throw new Error('Item not found');
      }

      const prompt = this.buildAutoTagPrompt(title, description, item.board.items);

      const completion = await this.openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are a task classification AI. Analyze tasks and suggest relevant tags, categories, and priority levels. Return only valid JSON.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.3,
        max_tokens: 500,
      });

      const response = completion.choices[0]?.message?.content;
      if (!response) {
        throw new Error('No response from AI service');
      }

      const result = JSON.parse(response) as AutoTagResult;

      // Cache result for 24 hours
      await RedisService.setCache(cacheKey, result, 86400);

      Logger.business('Item auto-tagged', {
        itemId,
        tagsCount: result.tags.length,
        priority: result.priority,
      });

      return result;
    } catch (error) {
      Logger.error('Auto-tagging failed', error as Error);
      throw new Error('Failed to auto-tag item');
    }
  }

  /**
   * Analyze workload and recommend task distribution
   */
  static async analyzeWorkloadDistribution(
    boardId: string,
    timeframe = 30 // days
  ): Promise<WorkloadRecommendation[]> {
    try {
      if (!this.openai) {
        throw new Error('AI service not available');
      }

      // Get workload data
      const workloadData = await this.getWorkloadData(boardId, timeframe);

      const prompt = this.buildWorkloadAnalysisPrompt(workloadData);

      const completion = await this.openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are a workload optimization AI. Analyze team workloads and provide balanced task distribution recommendations. Return only valid JSON.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.5,
        max_tokens: 1500,
      });

      const response = completion.choices[0]?.message?.content;
      if (!response) {
        throw new Error('No response from AI service');
      }

      const recommendations = JSON.parse(response) as WorkloadRecommendation[];

      Logger.business('Workload analysis completed', {
        boardId,
        recommendationsCount: recommendations.length,
      });

      return recommendations;
    } catch (error) {
      Logger.error('Workload analysis failed', error as Error);
      throw new Error('Failed to analyze workload distribution');
    }
  }

  /**
   * Suggest optimal task scheduling based on patterns
   */
  static async suggestTaskScheduling(
    boardId: string,
    userId: string,
    taskEstimates: Array<{ itemId: string; estimatedHours: number }>
  ): Promise<Array<{
    itemId: string;
    suggestedStartDate: Date;
    suggestedDueDate: Date;
    reason: string;
  }>> {
    try {
      if (!this.openai) {
        throw new Error('AI service not available');
      }

      // Get user's schedule patterns and current workload
      const scheduleContext = await this.getScheduleContext(userId, boardId);

      const prompt = this.buildSchedulingSuggestionPrompt(
        scheduleContext,
        taskEstimates
      );

      const completion = await this.openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are a task scheduling AI. Analyze user patterns and workload to suggest optimal task scheduling. Return only valid JSON with ISO date strings.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.4,
        max_tokens: 1000,
      });

      const response = completion.choices[0]?.message?.content;
      if (!response) {
        throw new Error('No response from AI service');
      }

      const suggestions = JSON.parse(response);

      // Convert date strings to Date objects
      const processedSuggestions = suggestions.map((suggestion: any) => ({
        ...suggestion,
        suggestedStartDate: new Date(suggestion.suggestedStartDate),
        suggestedDueDate: new Date(suggestion.suggestedDueDate),
      }));

      Logger.business('Task scheduling suggestions generated', {
        boardId,
        userId,
        tasksCount: taskEstimates.length,
      });

      return processedSuggestions;
    } catch (error) {
      Logger.error('Task scheduling suggestion failed', error as Error);
      throw new Error('Failed to generate scheduling suggestions');
    }
  }

  /**
   * Detect potential project risks and blockers
   */
  static async detectProjectRisks(
    boardId: string
  ): Promise<Array<{
    type: string;
    severity: 'low' | 'medium' | 'high';
    description: string;
    affectedItems: string[];
    suggestions: string[];
  }>> {
    try {
      if (!this.openai) {
        throw new Error('AI service not available');
      }

      // Get comprehensive board data for risk analysis
      const riskContext = await this.getRiskAnalysisContext(boardId);

      const prompt = this.buildRiskAnalysisPrompt(riskContext);

      const completion = await this.openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are a project risk analysis AI. Identify potential risks, bottlenecks, and blockers in project data. Return only valid JSON.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.3,
        max_tokens: 1200,
      });

      const response = completion.choices[0]?.message?.content;
      if (!response) {
        throw new Error('No response from AI service');
      }

      const risks = JSON.parse(response);

      Logger.business('Project risks analyzed', {
        boardId,
        risksDetected: risks.length,
      });

      return risks;
    } catch (error) {
      Logger.error('Project risk detection failed', error as Error);
      throw new Error('Failed to detect project risks');
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  /**
   * Get board context for AI analysis
   */
  private static async getBoardContext(boardId: string) {
    const board = await prisma.board.findUnique({
      where: { id: boardId },
      include: {
        items: {
          where: { deletedAt: null },
          select: {
            name: true,
            description: true,
            itemData: true,
            createdAt: true,
            assignments: {
              include: {
                user: {
                  select: { firstName: true, lastName: true },
                },
              },
            },
          },
          orderBy: { createdAt: 'desc' },
          take: 50,
        },
        columns: {
          select: { name: true },
        },
      },
    });

    return {
      boardName: board?.name,
      itemCount: board?.items.length || 0,
      columns: board?.columns.map(c => c.name) || [],
      recentItems: board?.items || [],
    };
  }

  /**
   * Get user patterns for personalized suggestions
   */
  private static async getUserPatterns(userId: string, boardId: string) {
    const userActivity = await prisma.activityLog.findMany({
      where: {
        userId,
        boardId,
        createdAt: {
          gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Last 30 days
        },
      },
      select: {
        action: true,
        entityType: true,
        newValues: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
      take: 100,
    });

    const userItems = await prisma.item.findMany({
      where: {
        boardId,
        assignments: {
          some: { userId },
        },
        deletedAt: null,
      },
      select: {
        name: true,
        itemData: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
      take: 20,
    });

    return {
      activityCount: userActivity.length,
      recentActions: userActivity.slice(0, 10),
      assignedItems: userItems,
    };
  }

  /**
   * Build prompt for task suggestions
   */
  private static buildTaskSuggestionPrompt(
    boardContext: any,
    userPatterns: any,
    context?: string,
    limit = 5
  ): string {
    return `
Analyze this project board and suggest ${limit} actionable tasks:

Board Context:
- Name: ${boardContext.boardName}
- Columns: ${boardContext.columns.join(', ')}
- Total Items: ${boardContext.itemCount}
- Recent Items: ${boardContext.recentItems.slice(0, 5).map((item: any) => item.name).join(', ')}

User Context:
- Recent Activities: ${userPatterns.activityCount}
- Assigned Items: ${userPatterns.assignedItems.length}

${context ? `Additional Context: ${context}` : ''}

Generate practical task suggestions in this exact JSON format:
[
  {
    "title": "Clear, actionable task title",
    "description": "Detailed description of what needs to be done",
    "priority": "low|medium|high",
    "estimatedDuration": number_in_minutes,
    "tags": ["relevant", "tags"],
    "confidence": 0.0_to_1.0
  }
]
`;
  }

  /**
   * Build prompt for auto-tagging
   */
  private static buildAutoTagPrompt(
    title: string,
    description?: string,
    boardItems: any[] = []
  ): string {
    const commonTags = this.extractCommonTags(boardItems);

    return `
Analyze this task and suggest tags, categories, and priority:

Task Title: ${title}
Task Description: ${description || 'No description provided'}

Common tags in this board: ${commonTags.join(', ')}

Return analysis in this exact JSON format:
{
  "tags": ["relevant", "actionable", "tags"],
  "categories": ["functional", "categories"],
  "priority": "low|medium|high",
  "confidence": 0.0_to_1.0
}
`;
  }

  /**
   * Extract common tags from board items
   */
  private static extractCommonTags(items: any[]): string[] {
    const tagCounts = new Map<string, number>();

    items.forEach(item => {
      const itemData = item.itemData as any;
      if (itemData?.tags) {
        itemData.tags.forEach((tag: string) => {
          tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
        });
      }
    });

    return Array.from(tagCounts.entries())
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([tag]) => tag);
  }

  /**
   * Get workload data for analysis
   */
  private static async getWorkloadData(boardId: string, timeframeDays: number) {
    const startDate = new Date(Date.now() - timeframeDays * 24 * 60 * 60 * 1000);

    const workloadStats = await prisma.$queryRaw`
      SELECT
        u.id as "userId",
        u.first_name as "firstName",
        u.last_name as "lastName",
        COUNT(DISTINCT i.id) as "assignedItems",
        COUNT(DISTINCT CASE
          WHEN JSON_EXTRACT(i.item_data, '$.status') = 'Done'
          THEN i.id
        END) as "completedItems",
        AVG(CASE
          WHEN JSON_EXTRACT(i.item_data, '$.estimatedHours') IS NOT NULL
          THEN CAST(JSON_EXTRACT(i.item_data, '$.estimatedHours') AS UNSIGNED)
        END) as "avgEstimatedHours"
      FROM users u
      LEFT JOIN item_assignments ia ON u.id = ia.user_id
      LEFT JOIN items i ON ia.item_id = i.id AND i.board_id = ${boardId}
      WHERE i.created_at >= ${startDate} OR i.created_at IS NULL
      GROUP BY u.id, u.first_name, u.last_name
      HAVING COUNT(DISTINCT i.id) > 0
    `;

    return workloadStats;
  }

  /**
   * Build workload analysis prompt
   */
  private static buildWorkloadAnalysisPrompt(workloadData: any): string {
    return `
Analyze team workload and recommend balanced task distribution:

Team Workload Data:
${JSON.stringify(workloadData, null, 2)}

Provide recommendations in this exact JSON format:
[
  {
    "userId": "user_id",
    "currentWorkload": number_0_to_100,
    "recommendedTasks": number_of_additional_tasks,
    "reason": "explanation for recommendation",
    "suggestions": ["specific", "improvement", "suggestions"]
  }
]
`;
  }

  /**
   * Get schedule context for task scheduling
   */
  private static async getScheduleContext(userId: string, boardId: string) {
    const userStats = await prisma.$queryRaw`
      SELECT
        COUNT(*) as "totalItems",
        AVG(DATEDIFF(
          COALESCE(JSON_EXTRACT(item_data, '$.completedAt'), NOW()),
          created_at
        )) as "avgCompletionDays",
        COUNT(CASE
          WHEN JSON_EXTRACT(item_data, '$.dueDate') < NOW()
          AND JSON_EXTRACT(item_data, '$.status') != 'Done'
          THEN 1
        END) as "overdueItems"
      FROM items i
      JOIN item_assignments ia ON i.id = ia.item_id
      WHERE ia.user_id = ${userId}
      AND i.board_id = ${boardId}
      AND i.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    `;

    return userStats;
  }

  /**
   * Build scheduling suggestion prompt
   */
  private static buildSchedulingSuggestionPrompt(
    scheduleContext: any,
    taskEstimates: any[]
  ): string {
    return `
Generate optimal task scheduling based on user patterns:

User Performance:
${JSON.stringify(scheduleContext, null, 2)}

Tasks to Schedule:
${JSON.stringify(taskEstimates, null, 2)}

Current Date: ${new Date().toISOString()}

Provide scheduling in this exact JSON format:
[
  {
    "itemId": "task_id",
    "suggestedStartDate": "ISO_date_string",
    "suggestedDueDate": "ISO_date_string",
    "reason": "explanation for timing"
  }
]
`;
  }

  /**
   * Get risk analysis context
   */
  private static async getRiskAnalysisContext(boardId: string) {
    const riskData = await prisma.$queryRaw`
      SELECT
        COUNT(*) as "totalItems",
        COUNT(CASE
          WHEN JSON_EXTRACT(item_data, '$.dueDate') < NOW()
          AND JSON_EXTRACT(item_data, '$.status') != 'Done'
          THEN 1
        END) as "overdueItems",
        COUNT(CASE
          WHEN JSON_EXTRACT(item_data, '$.status') = 'Blocked'
          THEN 1
        END) as "blockedItems",
        AVG(DATEDIFF(NOW(), created_at)) as "avgItemAge",
        COUNT(DISTINCT ia.user_id) as "teamSize"
      FROM items i
      LEFT JOIN item_assignments ia ON i.id = ia.item_id
      WHERE i.board_id = ${boardId}
      AND i.deleted_at IS NULL
    `;

    return riskData[0];
  }

  /**
   * Build risk analysis prompt
   */
  private static buildRiskAnalysisPrompt(riskContext: any): string {
    return `
Analyze project data for risks and blockers:

Project Metrics:
${JSON.stringify(riskContext, null, 2)}

Identify risks in this exact JSON format:
[
  {
    "type": "risk_category",
    "severity": "low|medium|high",
    "description": "detailed risk description",
    "affectedItems": ["item_ids_if_applicable"],
    "suggestions": ["mitigation", "strategies"]
  }
]
`;
  }
}

// Initialize the service when the module is loaded
AIService.initialize();