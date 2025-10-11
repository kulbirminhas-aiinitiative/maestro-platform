import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import { config } from '@/config';
import { v4 as uuidv4 } from 'uuid';

interface AIRequest {
  type: 'text_generation' | 'smart_suggestions' | 'sentiment_analysis' | 'content_summarization' | 'task_prioritization';
  context: {
    userId: string;
    organizationId: string;
    workspaceId?: string;
    boardId?: string;
    itemId?: string;
  };
  input: any;
  parameters?: Record<string, any>;
}

interface AIResponse {
  id: string;
  type: string;
  result: any;
  confidence: number;
  processingTime: number;
  timestamp: string;
  tokens_used?: number;
}

interface SmartSuggestion {
  type: 'column_value' | 'assignee' | 'due_date' | 'priority' | 'status';
  suggestion: any;
  confidence: number;
  reasoning: string;
}

interface TaskPrioritization {
  itemId: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  score: number;
  factors: string[];
}

export class AIService {
  private static readonly API_BASE_URL = config.ai?.apiUrl || 'https://api.openai.com/v1';
  private static readonly API_KEY = config.ai?.apiKey || process.env.OPENAI_API_KEY;
  private static readonly MODEL = config.ai?.model || 'gpt-3.5-turbo';

  /**
   * Generate text content using AI
   */
  static async generateText(
    userId: string,
    prompt: string,
    context: Record<string, any> = {},
    maxTokens: number = 500
  ): Promise<AIResponse> {
    const startTime = Date.now();
    const requestId = uuidv4();

    try {
      // Check rate limits
      await this.checkRateLimit(userId);

      // Prepare the request
      const messages = [
        {
          role: 'system',
          content: 'You are an AI assistant helping with work management and productivity. Provide helpful, concise responses.',
        },
        {
          role: 'user',
          content: this.buildContextualPrompt(prompt, context),
        },
      ];

      // Call AI API (OpenAI compatible)
      const response = await this.callAIAPI({
        model: this.MODEL,
        messages,
        max_tokens: maxTokens,
        temperature: 0.7,
      });

      const result = response.choices[0].message.content;
      const processingTime = Date.now() - startTime;

      // Log usage
      await this.logAIUsage({
        userId,
        type: 'text_generation',
        tokens: response.usage?.total_tokens || 0,
        processingTime,
        requestId,
      });

      const aiResponse: AIResponse = {
        id: requestId,
        type: 'text_generation',
        result: result.trim(),
        confidence: 0.8, // Default confidence
        processingTime,
        timestamp: new Date().toISOString(),
        tokens_used: response.usage?.total_tokens,
      };

      Logger.ai(`Text generated for user ${userId}`, { requestId, processingTime, tokens: response.usage?.total_tokens });

      return aiResponse;
    } catch (error) {
      Logger.error('AI text generation failed', error as Error);
      throw new Error('Failed to generate text. Please try again.');
    }
  }

  /**
   * Get smart suggestions for item completion
   */
  static async getSmartSuggestions(
    userId: string,
    itemId: string,
    context: {
      boardId: string;
      workspaceId: string;
      organizationId: string;
    }
  ): Promise<SmartSuggestion[]> {
    const startTime = Date.now();

    try {
      // Get item and board context
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          board: {
            include: {
              columns: true,
              items: {
                where: { deletedAt: null },
                include: { assignments: true },
                take: 50, // Recent items for pattern analysis
              },
            },
          },
          assignments: {
            include: { user: true },
          },
        },
      });

      if (!item) {
        throw new Error('Item not found');
      }

      const suggestions: SmartSuggestion[] = [];

      // Analyze patterns and generate suggestions
      const boardItems = item.board.items;
      const boardColumns = item.board.columns;

      // Status suggestions based on similar items
      const statusSuggestion = await this.suggestStatus(item, boardItems, boardColumns);
      if (statusSuggestion) {
        suggestions.push(statusSuggestion);
      }

      // Priority suggestions based on content analysis
      const prioritySuggestion = await this.suggestPriority(item, boardItems);
      if (prioritySuggestion) {
        suggestions.push(prioritySuggestion);
      }

      // Assignee suggestions based on workload and expertise
      const assigneeSuggestion = await this.suggestAssignee(item, context);
      if (assigneeSuggestion) {
        suggestions.push(assigneeSuggestion);
      }

      // Due date suggestions based on complexity and dependencies
      const dueDateSuggestion = await this.suggestDueDate(item, boardItems);
      if (dueDateSuggestion) {
        suggestions.push(dueDateSuggestion);
      }

      const processingTime = Date.now() - startTime;

      // Log usage
      await this.logAIUsage({
        userId,
        type: 'smart_suggestions',
        tokens: 0, // Local processing
        processingTime,
        requestId: uuidv4(),
      });

      Logger.ai(`Smart suggestions generated for item ${itemId}`, {
        userId,
        itemId,
        suggestionsCount: suggestions.length,
        processingTime,
      });

      return suggestions;
    } catch (error) {
      Logger.error('Smart suggestions failed', error as Error);
      return [];
    }
  }

  /**
   * Analyze sentiment of comments and descriptions
   */
  static async analyzeSentiment(
    userId: string,
    text: string,
    context: Record<string, any> = {}
  ): Promise<{
    sentiment: 'positive' | 'negative' | 'neutral';
    confidence: number;
    keywords: string[];
  }> {
    const startTime = Date.now();

    try {
      // Check rate limits
      await this.checkRateLimit(userId);

      // Simple sentiment analysis using keyword matching
      // In production, you'd use a proper sentiment analysis API
      const sentiment = this.analyzeTextSentiment(text);

      const processingTime = Date.now() - startTime;

      // Log usage
      await this.logAIUsage({
        userId,
        type: 'sentiment_analysis',
        tokens: 0, // Local processing
        processingTime,
        requestId: uuidv4(),
      });

      Logger.ai(`Sentiment analyzed for user ${userId}`, { sentiment: sentiment.sentiment, confidence: sentiment.confidence });

      return sentiment;
    } catch (error) {
      Logger.error('Sentiment analysis failed', error as Error);
      return {
        sentiment: 'neutral',
        confidence: 0.5,
        keywords: [],
      };
    }
  }

  /**
   * Summarize content (comments, descriptions, etc.)
   */
  static async summarizeContent(
    userId: string,
    content: string[],
    maxLength: number = 200
  ): Promise<AIResponse> {
    const startTime = Date.now();
    const requestId = uuidv4();

    try {
      // Check rate limits
      await this.checkRateLimit(userId);

      if (content.length === 0) {
        throw new Error('No content to summarize');
      }

      const combinedContent = content.join('\n\n');

      // Use AI to summarize if content is long enough
      if (combinedContent.length > 1000) {
        const messages = [
          {
            role: 'system',
            content: `Summarize the following content in ${maxLength} characters or less. Focus on key points and actionable items.`,
          },
          {
            role: 'user',
            content: combinedContent,
          },
        ];

        const response = await this.callAIAPI({
          model: this.MODEL,
          messages,
          max_tokens: Math.ceil(maxLength / 3), // Rough token estimation
          temperature: 0.3, // Lower temperature for factual summaries
        });

        const result = response.choices[0].message.content.trim();
        const processingTime = Date.now() - startTime;

        // Log usage
        await this.logAIUsage({
          userId,
          type: 'content_summarization',
          tokens: response.usage?.total_tokens || 0,
          processingTime,
          requestId,
        });

        return {
          id: requestId,
          type: 'content_summarization',
          result,
          confidence: 0.8,
          processingTime,
          timestamp: new Date().toISOString(),
          tokens_used: response.usage?.total_tokens,
        };
      } else {
        // Simple truncation for shorter content
        const summary = combinedContent.length <= maxLength
          ? combinedContent
          : combinedContent.substring(0, maxLength - 3) + '...';

        return {
          id: requestId,
          type: 'content_summarization',
          result: summary,
          confidence: 1.0,
          processingTime: Date.now() - startTime,
          timestamp: new Date().toISOString(),
        };
      }
    } catch (error) {
      Logger.error('Content summarization failed', error as Error);
      throw new Error('Failed to summarize content. Please try again.');
    }
  }

  /**
   * Prioritize tasks using AI analysis
   */
  static async prioritizeTasks(
    userId: string,
    itemIds: string[],
    context: {
      boardId: string;
      workspaceId: string;
      organizationId: string;
    }
  ): Promise<TaskPrioritization[]> {
    const startTime = Date.now();

    try {
      if (itemIds.length === 0) {
        return [];
      }

      // Get items with full context
      const items = await prisma.item.findMany({
        where: {
          id: { in: itemIds },
          deletedAt: null,
        },
        include: {
          assignments: {
            include: { user: true },
          },
          dependencies: true,
          comments: {
            where: { deletedAt: null },
            orderBy: { createdAt: 'desc' },
            take: 5,
          },
          timeEntries: true,
        },
      });

      const prioritizations: TaskPrioritization[] = [];

      for (const item of items) {
        const prioritization = await this.analyzeTaskPriority(item);
        prioritizations.push(prioritization);
      }

      // Sort by priority score (highest first)
      prioritizations.sort((a, b) => b.score - a.score);

      const processingTime = Date.now() - startTime;

      // Log usage
      await this.logAIUsage({
        userId,
        type: 'task_prioritization',
        tokens: 0, // Local processing
        processingTime,
        requestId: uuidv4(),
      });

      Logger.ai(`Tasks prioritized for user ${userId}`, {
        itemCount: items.length,
        processingTime,
      });

      return prioritizations;
    } catch (error) {
      Logger.error('Task prioritization failed', error as Error);
      return [];
    }
  }

  /**
   * Get AI insights for a board
   */
  static async getBoardInsights(
    userId: string,
    boardId: string
  ): Promise<{
    productivity: {
      completionRate: number;
      avgTimeToComplete: number;
      bottlenecks: string[];
    };
    recommendations: string[];
    trends: {
      itemsCreated: number;
      itemsCompleted: number;
      trend: 'up' | 'down' | 'stable';
    };
  }> {
    try {
      // Get board data for analysis
      const board = await prisma.board.findUnique({
        where: { id: boardId },
        include: {
          items: {
            where: { deletedAt: null },
            include: {
              assignments: true,
              timeEntries: true,
              comments: { where: { deletedAt: null } },
            },
          },
          columns: true,
        },
      });

      if (!board) {
        throw new Error('Board not found');
      }

      // Analyze productivity metrics
      const totalItems = board.items.length;
      const completedItems = board.items.filter(item => {
        const itemData = item.itemData as any;
        return itemData?.status === 'Done' || itemData?.status === 'Completed';
      }).length;

      const completionRate = totalItems > 0 ? (completedItems / totalItems) * 100 : 0;

      // Calculate average time to completion
      const completedItemsWithTime = board.items.filter(item => {
        const itemData = item.itemData as any;
        return (itemData?.status === 'Done' || itemData?.status === 'Completed') && item.timeEntries.length > 0;
      });

      const avgTimeToComplete = completedItemsWithTime.length > 0
        ? completedItemsWithTime.reduce((sum, item) => {
            const totalTime = item.timeEntries.reduce((time, entry) => time + (entry.durationSeconds || 0), 0);
            return sum + totalTime;
          }, 0) / completedItemsWithTime.length / 3600 // Convert to hours
        : 0;

      // Identify bottlenecks
      const bottlenecks = this.identifyBottlenecks(board.items, board.columns);

      // Generate recommendations
      const recommendations = this.generateRecommendations(board, {
        completionRate,
        avgTimeToComplete,
        bottlenecks,
      });

      // Calculate trends (last 30 days)
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      const recentItems = board.items.filter(item => item.createdAt > thirtyDaysAgo);
      const recentCompletions = board.items.filter(item => {
        const itemData = item.itemData as any;
        return (itemData?.status === 'Done' || itemData?.status === 'Completed') &&
               item.updatedAt > thirtyDaysAgo;
      });

      const trend = recentItems.length > recentCompletions.length ? 'down' :
                   recentItems.length < recentCompletions.length ? 'up' : 'stable';

      Logger.ai(`Board insights generated for board ${boardId}`, {
        userId,
        boardId,
        completionRate,
        totalItems,
      });

      return {
        productivity: {
          completionRate: Math.round(completionRate * 100) / 100,
          avgTimeToComplete: Math.round(avgTimeToComplete * 100) / 100,
          bottlenecks,
        },
        recommendations,
        trends: {
          itemsCreated: recentItems.length,
          itemsCompleted: recentCompletions.length,
          trend,
        },
      };
    } catch (error) {
      Logger.error('Board insights failed', error as Error);
      throw new Error('Failed to generate board insights');
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  /**
   * Call external AI API (OpenAI compatible)
   */
  private static async callAIAPI(payload: any): Promise<any> {
    if (!this.API_KEY) {
      throw new Error('AI API key not configured');
    }

    // In a real implementation, this would make an HTTP request to the AI API
    // For this demo, we'll simulate the response
    return this.simulateAIResponse(payload);
  }

  /**
   * Simulate AI API response for demo purposes
   */
  private static simulateAIResponse(payload: any): any {
    const prompts = payload.messages || [];
    const userMessage = prompts.find((m: any) => m.role === 'user')?.content || '';

    // Generate a contextual response based on the prompt
    let response = '';
    if (userMessage.toLowerCase().includes('summary') || userMessage.toLowerCase().includes('summarize')) {
      response = 'This is a summary of the key points and actionable items from the provided content.';
    } else if (userMessage.toLowerCase().includes('help') || userMessage.toLowerCase().includes('suggest')) {
      response = 'Here are some suggestions to help you move forward with this task or project.';
    } else {
      response = 'I understand your request and am here to help with your work management needs.';
    }

    return {
      choices: [{
        message: {
          content: response
        }
      }],
      usage: {
        total_tokens: Math.floor(userMessage.length / 4) + Math.floor(response.length / 4),
        prompt_tokens: Math.floor(userMessage.length / 4),
        completion_tokens: Math.floor(response.length / 4),
      }
    };
  }

  /**
   * Build contextual prompt with relevant information
   */
  private static buildContextualPrompt(prompt: string, context: Record<string, any>): string {
    let contextualPrompt = prompt;

    if (context.boardName) {
      contextualPrompt = `Board: ${context.boardName}\n\n${contextualPrompt}`;
    }

    if (context.itemName) {
      contextualPrompt = `Item: ${context.itemName}\n\n${contextualPrompt}`;
    }

    if (context.description) {
      contextualPrompt = `Context: ${context.description}\n\n${contextualPrompt}`;
    }

    return contextualPrompt;
  }

  /**
   * Check rate limits for AI usage
   */
  private static async checkRateLimit(userId: string): Promise<void> {
    const rateKey = `ai_rate_limit:${userId}`;
    const currentCount = await RedisService.getCache(rateKey) || 0;
    const limit = 100; // 100 requests per hour

    if (currentCount >= limit) {
      throw new Error('AI usage rate limit exceeded. Please try again later.');
    }

    await RedisService.setCache(rateKey, currentCount + 1, 3600); // 1 hour TTL
  }

  /**
   * Log AI usage for analytics and billing
   */
  private static async logAIUsage(data: {
    userId: string;
    type: string;
    tokens: number;
    processingTime: number;
    requestId: string;
  }): Promise<void> {
    try {
      // Store in database for analytics
      await prisma.activityLog.create({
        data: {
          id: data.requestId,
          organizationId: await this.getUserOrganizationId(data.userId),
          userId: data.userId,
          action: 'ai_usage',
          entityType: 'ai_request',
          entityId: data.requestId,
          metadata: {
            type: data.type,
            tokens: data.tokens,
            processingTime: data.processingTime,
          },
        },
      });
    } catch (error) {
      Logger.error('Failed to log AI usage', error as Error);
    }
  }

  /**
   * Get user's organization ID
   */
  private static async getUserOrganizationId(userId: string): Promise<string> {
    const membership = await prisma.organizationMember.findFirst({
      where: { userId, status: 'active' },
      select: { organizationId: true },
    });
    return membership?.organizationId || 'unknown';
  }

  /**
   * Analyze text sentiment using keyword matching
   */
  private static analyzeTextSentiment(text: string): {
    sentiment: 'positive' | 'negative' | 'neutral';
    confidence: number;
    keywords: string[];
  } {
    const positiveWords = ['good', 'great', 'excellent', 'awesome', 'perfect', 'love', 'amazing', 'fantastic', 'wonderful'];
    const negativeWords = ['bad', 'terrible', 'awful', 'hate', 'horrible', 'worst', 'problem', 'issue', 'error', 'fail'];

    const words = text.toLowerCase().split(/\W+/);
    const foundPositive = words.filter(word => positiveWords.includes(word));
    const foundNegative = words.filter(word => negativeWords.includes(word));

    const positiveCount = foundPositive.length;
    const negativeCount = foundNegative.length;

    if (positiveCount > negativeCount) {
      return {
        sentiment: 'positive',
        confidence: Math.min(0.9, 0.5 + (positiveCount - negativeCount) * 0.1),
        keywords: foundPositive,
      };
    } else if (negativeCount > positiveCount) {
      return {
        sentiment: 'negative',
        confidence: Math.min(0.9, 0.5 + (negativeCount - positiveCount) * 0.1),
        keywords: foundNegative,
      };
    } else {
      return {
        sentiment: 'neutral',
        confidence: 0.6,
        keywords: [],
      };
    }
  }

  /**
   * Suggest status based on similar items
   */
  private static async suggestStatus(item: any, boardItems: any[], boardColumns: any[]): Promise<SmartSuggestion | null> {
    const statusColumn = boardColumns.find(col => col.columnType === 'status');
    if (!statusColumn || !statusColumn.settings?.options) {
      return null;
    }

    // Analyze similar items
    const similarItems = boardItems.filter(boardItem =>
      boardItem.id !== item.id &&
      boardItem.name.toLowerCase().includes(item.name.toLowerCase().split(' ')[0])
    );

    if (similarItems.length === 0) {
      return null;
    }

    // Find most common status among similar items
    const statusCounts: Record<string, number> = {};
    similarItems.forEach(similarItem => {
      const status = (similarItem.itemData as any)?.status;
      if (status) {
        statusCounts[status] = (statusCounts[status] || 0) + 1;
      }
    });

    const mostCommonStatus = Object.entries(statusCounts)
      .sort(([,a], [,b]) => b - a)[0]?.[0];

    if (!mostCommonStatus) {
      return null;
    }

    return {
      type: 'status',
      suggestion: mostCommonStatus,
      confidence: Math.min(0.8, statusCounts[mostCommonStatus] / similarItems.length),
      reasoning: `Based on ${similarItems.length} similar items, most commonly use "${mostCommonStatus}" status`,
    };
  }

  /**
   * Suggest priority based on content analysis
   */
  private static async suggestPriority(item: any, boardItems: any[]): Promise<SmartSuggestion | null> {
    const urgencyWords = ['urgent', 'asap', 'critical', 'emergency', 'immediately'];
    const highPriorityWords = ['important', 'priority', 'deadline', 'due'];

    const itemText = `${item.name} ${item.description || ''}`.toLowerCase();

    const hasUrgency = urgencyWords.some(word => itemText.includes(word));
    const hasHighPriority = highPriorityWords.some(word => itemText.includes(word));

    let priority = 'medium';
    let confidence = 0.6;
    let reasoning = 'Based on standard priority assessment';

    if (hasUrgency) {
      priority = 'critical';
      confidence = 0.9;
      reasoning = 'Contains urgent language indicators';
    } else if (hasHighPriority) {
      priority = 'high';
      confidence = 0.8;
      reasoning = 'Contains high priority indicators';
    }

    return {
      type: 'priority',
      suggestion: priority,
      confidence,
      reasoning,
    };
  }

  /**
   * Suggest assignee based on workload and expertise
   */
  private static async suggestAssignee(item: any, context: any): Promise<SmartSuggestion | null> {
    // Get workspace members
    const workspaceMembers = await prisma.workspaceMember.findMany({
      where: { workspaceId: context.workspaceId },
      include: {
        user: true,
      },
    });

    if (workspaceMembers.length === 0) {
      return null;
    }

    // Simple suggestion: least assigned member
    const memberWorkloads = await Promise.all(
      workspaceMembers.map(async (member) => {
        const assignmentCount = await prisma.itemAssignment.count({
          where: {
            userId: member.userId,
            item: {
              board: { workspaceId: context.workspaceId },
              deletedAt: null,
            },
          },
        });

        return {
          user: member.user,
          workload: assignmentCount,
        };
      })
    );

    const suggestedMember = memberWorkloads.sort((a, b) => a.workload - b.workload)[0];

    return {
      type: 'assignee',
      suggestion: {
        id: suggestedMember.user.id,
        name: `${suggestedMember.user.firstName} ${suggestedMember.user.lastName}`,
        email: suggestedMember.user.email,
      },
      confidence: 0.7,
      reasoning: `Has the lowest current workload (${suggestedMember.workload} assignments)`,
    };
  }

  /**
   * Suggest due date based on complexity
   */
  private static async suggestDueDate(item: any, boardItems: any[]): Promise<SmartSuggestion | null> {
    // Simple heuristic based on item name length and description
    const complexity = (item.name.length + (item.description?.length || 0)) / 100;
    const baseDays = Math.min(14, Math.max(3, Math.ceil(complexity * 7)));

    const suggestedDate = new Date();
    suggestedDate.setDate(suggestedDate.getDate() + baseDays);

    return {
      type: 'due_date',
      suggestion: suggestedDate.toISOString().split('T')[0],
      confidence: 0.6,
      reasoning: `Estimated ${baseDays} days based on task complexity`,
    };
  }

  /**
   * Analyze task priority based on multiple factors
   */
  private static async analyzeTaskPriority(item: any): Promise<TaskPrioritization> {
    let score = 50; // Base score
    const factors: string[] = [];

    // Check for urgent keywords
    const urgencyWords = ['urgent', 'asap', 'critical', 'emergency'];
    const itemText = `${item.name} ${item.description || ''}`.toLowerCase();

    if (urgencyWords.some(word => itemText.includes(word))) {
      score += 30;
      factors.push('Contains urgent keywords');
    }

    // Check assignment count
    if (item.assignments.length > 1) {
      score += 10;
      factors.push('Multiple assignees');
    }

    // Check dependencies
    if (item.dependencies.length > 0) {
      score += 15;
      factors.push('Has dependencies');
    }

    // Check recent activity (comments, time entries)
    if (item.comments.length > 0) {
      score += 5;
      factors.push('Recent activity');
    }

    // Time tracking indicates active work
    if (item.timeEntries.length > 0) {
      score += 10;
      factors.push('Time tracking active');
    }

    // Determine priority level
    let priority: 'critical' | 'high' | 'medium' | 'low';
    if (score >= 80) priority = 'critical';
    else if (score >= 65) priority = 'high';
    else if (score >= 40) priority = 'medium';
    else priority = 'low';

    return {
      itemId: item.id,
      priority,
      score,
      factors,
    };
  }

  /**
   * Identify bottlenecks in the board
   */
  private static identifyBottlenecks(items: any[], columns: any[]): string[] {
    const bottlenecks: string[] = [];

    // Find status columns with too many items
    const statusColumn = columns.find(col => col.columnType === 'status');
    if (statusColumn && statusColumn.settings?.options) {
      const statusCounts: Record<string, number> = {};

      items.forEach(item => {
        const status = (item.itemData as any)?.status;
        if (status) {
          statusCounts[status] = (statusCounts[status] || 0) + 1;
        }
      });

      // Identify bottlenecks (status with >30% of items)
      const totalItems = items.length;
      Object.entries(statusCounts).forEach(([status, count]) => {
        if (count / totalItems > 0.3) {
          bottlenecks.push(`Too many items in "${status}" status`);
        }
      });
    }

    // Check for items without assignees
    const unassignedCount = items.filter(item => !item.assignments?.length).length;
    if (unassignedCount > items.length * 0.2) {
      bottlenecks.push('Many items lack assignees');
    }

    return bottlenecks;
  }

  /**
   * Generate recommendations based on analysis
   */
  private static generateRecommendations(board: any, metrics: any): string[] {
    const recommendations: string[] = [];

    if (metrics.completionRate < 50) {
      recommendations.push('Consider breaking down large tasks into smaller, manageable items');
    }

    if (metrics.avgTimeToComplete > 40) {
      recommendations.push('Review task complexity and consider setting more realistic time estimates');
    }

    if (metrics.bottlenecks.length > 0) {
      recommendations.push('Address workflow bottlenecks to improve team productivity');
    }

    const totalItems = board.items.length;
    const assignedItems = board.items.filter((item: any) => item.assignments?.length > 0).length;

    if (assignedItems / totalItems < 0.7) {
      recommendations.push('Assign more items to team members to improve accountability');
    }

    if (recommendations.length === 0) {
      recommendations.push('Your board is performing well! Keep up the good work.');
    }

    return recommendations;
  }
}