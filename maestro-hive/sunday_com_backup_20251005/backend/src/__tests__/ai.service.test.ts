import { prismaMock } from './setup';
import { AIService } from '@/services/ai.service';
import { RedisService } from '@/config/redis';
import OpenAI from 'openai';

// Mock OpenAI
jest.mock('openai');
const MockedOpenAI = OpenAI as jest.MockedClass<typeof OpenAI>;

// Mock Redis
jest.mock('@/config/redis', () => ({
  RedisService: {
    getCache: jest.fn(),
    setCache: jest.fn(),
    deleteCache: jest.fn(),
    deleteCachePattern: jest.fn(),
  },
}));

// Mock config
jest.mock('@/config', () => ({
  config: {
    openai: {
      apiKey: 'test-api-key',
    },
  },
}));

describe('AIService', () => {
  let mockOpenAI: jest.Mocked<OpenAI>;

  beforeEach(() => {
    jest.clearAllMocks();

    // Create mock OpenAI instance
    mockOpenAI = {
      chat: {
        completions: {
          create: jest.fn(),
        },
      },
    } as any;

    MockedOpenAI.mockImplementation(() => mockOpenAI);

    // Initialize service
    AIService.initialize();
  });

  describe('generateTaskSuggestions', () => {
    it('should generate task suggestions successfully', async () => {
      const mockResponse = {
        choices: [{
          message: {
            content: JSON.stringify([
              {
                title: 'Review API documentation',
                description: 'Update API docs for new endpoints',
                priority: 'medium',
                estimatedDuration: 60,
                tags: ['documentation', 'api'],
                confidence: 0.8,
              },
            ]),
          },
        }],
      };

      mockOpenAI.chat.completions.create.mockResolvedValue(mockResponse as any);
      (RedisService.setCache as jest.Mock).mockResolvedValue(undefined);

      // Mock board context queries
      prismaMock.board.findUnique.mockResolvedValue({
        id: 'board-1',
        name: 'Test Board',
        items: [
          { name: 'Test Item', description: 'Test', itemData: {}, createdAt: new Date(), assignments: [] },
        ],
        columns: [{ name: 'To Do' }],
      } as any);

      prismaMock.activityLog.findMany.mockResolvedValue([]);
      prismaMock.item.findMany.mockResolvedValue([]);

      const suggestions = await AIService.generateTaskSuggestions(
        'board-1',
        'user-1',
        'Need to update documentation',
        3
      );

      expect(suggestions).toHaveLength(1);
      expect(suggestions[0]).toMatchObject({
        title: 'Review API documentation',
        priority: 'medium',
        confidence: 0.8,
      });

      expect(mockOpenAI.chat.completions.create).toHaveBeenCalledWith({
        model: 'gpt-3.5-turbo',
        messages: expect.any(Array),
        temperature: 0.7,
        max_tokens: 1000,
      });

      expect(RedisService.setCache).toHaveBeenCalledWith(
        'ai:suggestions:board-1:user-1',
        suggestions,
        3600
      );
    });

    it('should throw error when AI service is not available', async () => {
      // Mock service without initialization
      (AIService as any).openai = null;

      await expect(
        AIService.generateTaskSuggestions('board-1', 'user-1')
      ).rejects.toThrow('AI service not available');
    });

    it('should throw error when OpenAI returns no response', async () => {
      const mockResponse = {
        choices: [],
      };

      mockOpenAI.chat.completions.create.mockResolvedValue(mockResponse as any);

      // Mock board context queries
      prismaMock.board.findUnique.mockResolvedValue({
        id: 'board-1',
        name: 'Test Board',
        items: [],
        columns: [],
      } as any);

      prismaMock.activityLog.findMany.mockResolvedValue([]);
      prismaMock.item.findMany.mockResolvedValue([]);

      await expect(
        AIService.generateTaskSuggestions('board-1', 'user-1')
      ).rejects.toThrow('No response from AI service');
    });
  });

  describe('autoTagItem', () => {
    it('should auto-tag item successfully', async () => {
      const mockResponse = {
        choices: [{
          message: {
            content: JSON.stringify({
              tags: ['api', 'documentation', 'backend'],
              categories: ['development', 'documentation'],
              priority: 'medium',
              confidence: 0.9,
            }),
          },
        }],
      };

      mockOpenAI.chat.completions.create.mockResolvedValue(mockResponse as any);
      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      (RedisService.setCache as jest.Mock).mockResolvedValue(undefined);

      prismaMock.item.findUnique.mockResolvedValue({
        id: 'item-1',
        board: {
          items: [
            { name: 'Related Item', itemData: { tags: ['api', 'backend'] } },
          ],
        },
      } as any);

      const result = await AIService.autoTagItem(
        'item-1',
        'Update API documentation',
        'Need to update the REST API documentation with new endpoints'
      );

      expect(result).toMatchObject({
        tags: ['api', 'documentation', 'backend'],
        categories: ['development', 'documentation'],
        priority: 'medium',
        confidence: 0.9,
      });

      expect(RedisService.setCache).toHaveBeenCalledWith(
        'ai:tags:item-1',
        result,
        86400
      );
    });

    it('should return cached result when available', async () => {
      const cachedResult = {
        tags: ['cached', 'tag'],
        categories: ['cached'],
        priority: 'low',
        confidence: 0.7,
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(cachedResult);

      const result = await AIService.autoTagItem('item-1', 'Test', 'Test description');

      expect(result).toEqual(cachedResult);
      expect(mockOpenAI.chat.completions.create).not.toHaveBeenCalled();
    });

    it('should throw error when item not found', async () => {
      prismaMock.item.findUnique.mockResolvedValue(null);

      await expect(
        AIService.autoTagItem('nonexistent-item', 'Test', 'Test')
      ).rejects.toThrow('Item not found');
    });
  });

  describe('analyzeWorkloadDistribution', () => {
    it('should analyze workload distribution successfully', async () => {
      const mockResponse = {
        choices: [{
          message: {
            content: JSON.stringify([
              {
                userId: 'user-1',
                currentWorkload: 75,
                recommendedTasks: 2,
                reason: 'User has moderate workload with good completion rate',
                suggestions: ['Focus on high-priority items', 'Consider delegation'],
              },
            ]),
          },
        }],
      };

      mockOpenAI.chat.completions.create.mockResolvedValue(mockResponse as any);

      // Mock workload data query
      prismaMock.$queryRaw.mockResolvedValue([
        {
          userId: 'user-1',
          firstName: 'John',
          lastName: 'Doe',
          assignedItems: BigInt(10),
          completedItems: BigInt(7),
          avgEstimatedHours: 5.5,
        },
      ]);

      const recommendations = await AIService.analyzeWorkloadDistribution('board-1', 30);

      expect(recommendations).toHaveLength(1);
      expect(recommendations[0]).toMatchObject({
        userId: 'user-1',
        currentWorkload: 75,
        recommendedTasks: 2,
      });
    });
  });

  describe('suggestTaskScheduling', () => {
    it('should suggest task scheduling successfully', async () => {
      const mockResponse = {
        choices: [{
          message: {
            content: JSON.stringify([
              {
                itemId: 'item-1',
                suggestedStartDate: '2024-01-15T09:00:00.000Z',
                suggestedDueDate: '2024-01-17T17:00:00.000Z',
                reason: 'Based on user availability and task complexity',
              },
            ]),
          },
        }],
      };

      mockOpenAI.chat.completions.create.mockResolvedValue(mockResponse as any);

      // Mock user schedule context
      prismaMock.$queryRaw.mockResolvedValue([
        {
          totalItems: BigInt(20),
          avgCompletionDays: 3.5,
          overdueItems: BigInt(2),
        },
      ]);

      const taskEstimates = [
        { itemId: 'item-1', estimatedHours: 8 },
      ];

      const suggestions = await AIService.suggestTaskScheduling(
        'board-1',
        'user-1',
        taskEstimates
      );

      expect(suggestions).toHaveLength(1);
      expect(suggestions[0]).toMatchObject({
        itemId: 'item-1',
        suggestedStartDate: new Date('2024-01-15T09:00:00.000Z'),
        suggestedDueDate: new Date('2024-01-17T17:00:00.000Z'),
      });
    });
  });

  describe('detectProjectRisks', () => {
    it('should detect project risks successfully', async () => {
      const mockResponse = {
        choices: [{
          message: {
            content: JSON.stringify([
              {
                type: 'deadline_risk',
                severity: 'high',
                description: 'Multiple items are overdue and may impact project timeline',
                affectedItems: ['item-1', 'item-2'],
                suggestions: ['Prioritize overdue items', 'Consider resource reallocation'],
              },
            ]),
          },
        }],
      };

      mockOpenAI.chat.completions.create.mockResolvedValue(mockResponse as any);

      // Mock risk analysis context
      prismaMock.$queryRaw.mockResolvedValue([
        {
          totalItems: BigInt(50),
          overdueItems: BigInt(5),
          blockedItems: BigInt(2),
          avgItemAge: 15.5,
          teamSize: BigInt(5),
        },
      ]);

      const risks = await AIService.detectProjectRisks('board-1');

      expect(risks).toHaveLength(1);
      expect(risks[0]).toMatchObject({
        type: 'deadline_risk',
        severity: 'high',
        affectedItems: ['item-1', 'item-2'],
      });
    });
  });
});