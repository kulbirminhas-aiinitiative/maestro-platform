# Sunday.com - Integration Patterns & API Architecture
## Comprehensive Integration Design for Service Implementation

**Document Version:** 1.0 - Implementation Ready
**Date:** December 19, 2024
**Author:** Solution Architect
**Project Phase:** Iteration 2 - Core Feature Implementation
**Focus:** Service Integration Patterns & API Specifications

---

## Executive Summary

This document defines the comprehensive integration patterns and API architecture for Sunday.com's service implementation. It focuses on the critical integration requirements for the missing 5,547+ lines of business logic, real-time collaboration patterns, and testing infrastructure integration.

### Integration Priorities

**1. Service-to-Service Integration** - Internal API communication patterns
**2. Real-time Collaboration Integration** - WebSocket and event-driven patterns
**3. Testing Infrastructure Integration** - Quality assurance in integration design
**4. External API Integration** - Third-party service integration patterns
**5. Data Flow Integration** - Event sourcing and CQRS patterns

---

## Table of Contents

1. [Service Integration Architecture](#service-integration-architecture)
2. [Real-time Collaboration Patterns](#real-time-collaboration-patterns)
3. [Event-Driven Integration Patterns](#event-driven-integration-patterns)
4. [API Gateway Integration](#api-gateway-integration)
5. [Testing Integration Patterns](#testing-integration-patterns)
6. [External Service Integration](#external-service-integration)
7. [Data Flow Integration Patterns](#data-flow-integration-patterns)
8. [Performance Integration Patterns](#performance-integration-patterns)

---

## Service Integration Architecture

### Internal Service Communication Patterns

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        Service Integration Patterns                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        Direct Service Calls                                │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  calls  ┌─────────────────┐  calls  ┌─────────────────┐│  │
│  │  │  BoardService   │ ────────▶│ PermissionSvc   │ ────────▶│  UserService    ││  │
│  │  │                 │         │                 │         │                 ││  │
│  │  │ • createBoard   │         │ • checkAccess   │         │ • getUser       ││  │
│  │  │ • updateBoard   │         │ • validateRole  │         │ • getUserRoles  ││  │
│  │  │ • shareBoard    │         │ • auditAction   │         │ • isActive      ││  │
│  │  └─────────────────┘         └─────────────────┘         └─────────────────┘│  │
│  │           │                                                        │         │  │
│  │           │                  ┌─────────────────┐                   │         │  │
│  │           └─────────calls────▶│   CacheService  │◀──────calls───────┘         │  │
│  │                              │                 │                             │  │
│  │                              │ • get/set       │                             │  │
│  │                              │ • invalidate    │                             │  │
│  │                              │ • performance   │                             │  │
│  │                              └─────────────────┘                             │  │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                     Dependency Injection Pattern                           │   │
│  │                                                                             │   │
│  │  interface IBoardService {                                                  │   │
│  │    createBoard(data: CreateBoardRequest, context: Context): Promise<Board> │   │
│  │  }                                                                          │   │
│  │                                                                             │   │
│  │  @injectable()                                                              │   │
│  │  class BoardService implements IBoardService {                             │   │
│  │    constructor(                                                             │   │
│  │      @inject(TYPES.BoardRepository)                                        │   │
│  │      private boardRepo: IBoardRepository,                                  │   │
│  │                                                                             │   │
│  │      @inject(TYPES.PermissionService)                                      │   │
│  │      private permissionSvc: IPermissionService,                            │   │
│  │                                                                             │   │
│  │      @inject(TYPES.EventBus)                                               │   │
│  │      private eventBus: IEventBus,                                          │   │
│  │                                                                             │   │
│  │      @inject(TYPES.CacheManager)                                           │   │
│  │      private cache: ICacheManager                                          │   │
│  │    ) {}                                                                     │   │
│  │                                                                             │   │
│  │    async createBoard(data, context): Promise<Board> {                      │   │
│  │      // Validate permissions                                               │   │
│  │      await this.permissionSvc.requirePermission(                          │   │
│  │        context.userId, 'board:create', context.workspaceId               │   │
│  │      );                                                                     │   │
│  │                                                                             │   │
│  │      // Create board                                                       │   │
│  │      const board = await this.boardRepo.create(data);                     │   │
│  │                                                                             │   │
│  │      // Publish event                                                      │   │
│  │      await this.eventBus.publish('board.created', {                       │   │
│  │        boardId: board.id,                                                  │   │
│  │        userId: context.userId                                              │   │
│  │      });                                                                   │   │
│  │                                                                             │   │
│  │      // Invalidate cache                                                   │   │
│  │      await this.cache.invalidatePattern(                                  │   │
│  │        `workspace:${board.workspaceId}:boards`                            │   │
│  │      );                                                                     │   │
│  │                                                                             │   │
│  │      return board;                                                          │   │
│  │    }                                                                        │   │
│  │  }                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Service Interaction Patterns

```typescript
// Complex Service Interaction Pattern Example: Item Creation with Dependencies

@injectable()
export class ItemService implements IItemService {
  constructor(
    @inject(TYPES.ItemRepository) private itemRepo: IItemRepository,
    @inject(TYPES.BoardService) private boardService: IBoardService,
    @inject(TYPES.PermissionService) private permissionService: IPermissionService,
    @inject(TYPES.AutomationService) private automationService: IAutomationService,
    @inject(TYPES.SearchService) private searchService: ISearchService,
    @inject(TYPES.EventBus) private eventBus: IEventBus,
    @inject(TYPES.Logger) private logger: ILogger
  ) {}

  async createItem(
    data: CreateItemRequest,
    context: UserContext
  ): Promise<Item> {
    const executionId = generateExecutionId();

    this.logger.info('Starting item creation', {
      executionId,
      boardId: data.boardId,
      userId: context.userId
    });

    try {
      // Step 1: Validate board access and permissions
      const board = await this.boardService.getBoard(data.boardId, context);
      await this.permissionService.requirePermission(
        context.userId,
        'item:create',
        data.boardId
      );

      // Step 2: Validate item data and dependencies
      await this.validateItemCreation(data, board, context);

      // Step 3: Create item in transaction
      const item = await this.itemRepo.transaction(async (trx) => {
        // Create the item
        const newItem = await this.itemRepo.create({
          ...data,
          position: await this.calculateNextPosition(data.boardId, data.parentId, trx),
          createdById: context.userId,
          organizationId: context.organizationId
        }, trx);

        // Handle dependencies if specified
        if (data.dependencies?.length > 0) {
          await this.createItemDependencies(newItem.id, data.dependencies, trx);
        }

        // Handle file attachments if specified
        if (data.attachments?.length > 0) {
          await this.attachFiles(newItem.id, data.attachments, context, trx);
        }

        return newItem;
      });

      // Step 4: Index for search
      await this.searchService.indexItem(item);

      // Step 5: Trigger automation rules
      await this.automationService.triggerEvent('item.created', {
        item,
        board,
        user: context.user,
        context: {
          organizationId: context.organizationId,
          workspaceId: board.workspaceId,
          boardId: board.id
        }
      });

      // Step 6: Publish domain event
      await this.eventBus.publish('item.created', {
        item,
        createdBy: context.userId,
        boardId: data.boardId,
        executionId,
        timestamp: new Date()
      });

      // Step 7: Update analytics
      await this.eventBus.publish('analytics.item_created', {
        itemId: item.id,
        boardId: data.boardId,
        workspaceId: board.workspaceId,
        organizationId: context.organizationId,
        userId: context.userId,
        timestamp: new Date()
      });

      this.logger.info('Item creation completed', {
        executionId,
        itemId: item.id,
        duration: Date.now() - startTime
      });

      return item;

    } catch (error) {
      this.logger.error('Item creation failed', {
        executionId,
        error: error.message,
        boardId: data.boardId,
        userId: context.userId
      });

      // Publish failure event for monitoring
      await this.eventBus.publish('item.creation_failed', {
        boardId: data.boardId,
        userId: context.userId,
        error: error.message,
        executionId,
        timestamp: new Date()
      });

      throw error;
    }
  }

  private async validateItemCreation(
    data: CreateItemRequest,
    board: Board,
    context: UserContext
  ): Promise<void> {
    // Validate item data schema
    const schema = z.object({
      name: z.string().min(1).max(500),
      description: z.string().max(10000).optional(),
      parentId: z.string().uuid().optional(),
      data: z.record(z.any()).optional(),
      dependencies: z.array(z.string().uuid()).optional()
    });

    const validatedData = schema.parse(data);

    // Business rule validations
    if (data.parentId) {
      const parentItem = await this.itemRepo.findById(data.parentId);
      if (!parentItem || parentItem.boardId !== data.boardId) {
        throw new ValidationError('Invalid parent item');
      }

      // Check for circular dependencies
      if (await this.wouldCreateCircularHierarchy(data.parentId, data.boardId)) {
        throw new ValidationError('Cannot create circular item hierarchy');
      }
    }

    // Check board capacity limits
    const itemCount = await this.itemRepo.countByBoard(data.boardId);
    const maxItems = await this.getMaxItemsForPlan(context.subscriptionPlan);

    if (itemCount >= maxItems) {
      throw new QuotaExceededError(`Maximum ${maxItems} items allowed per board`);
    }

    // Validate custom field data against board schema
    if (data.data) {
      await this.validateCustomFieldData(data.data, board.columns);
    }
  }

  // Complex dependency creation with circular detection
  private async createItemDependencies(
    itemId: string,
    dependencyIds: string[],
    trx: Transaction
  ): Promise<void> {
    for (const depId of dependencyIds) {
      // Validate dependency item exists
      const depItem = await this.itemRepo.findById(depId, trx);
      if (!depItem) {
        throw new ValidationError(`Dependency item ${depId} not found`);
      }

      // Check for circular dependencies
      if (await this.dependencyService.wouldCreateCycle(itemId, depId)) {
        throw new ValidationError(
          `Creating dependency on ${depId} would create a circular reference`
        );
      }

      // Create the dependency
      await this.itemRepo.createDependency({
        predecessorId: depId,
        successorId: itemId,
        dependencyType: 'blocks',
        createdAt: new Date()
      }, trx);
    }
  }
}

// Event-Driven Integration Pattern
@injectable()
export class EventDrivenIntegrationService {
  constructor(
    @inject(TYPES.EventBus) private eventBus: IEventBus,
    @inject(TYPES.Logger) private logger: ILogger
  ) {
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    // Board events
    this.eventBus.subscribe('board.created', this.handleBoardCreated.bind(this));
    this.eventBus.subscribe('board.updated', this.handleBoardUpdated.bind(this));
    this.eventBus.subscribe('board.deleted', this.handleBoardDeleted.bind(this));

    // Item events
    this.eventBus.subscribe('item.created', this.handleItemCreated.bind(this));
    this.eventBus.subscribe('item.updated', this.handleItemUpdated.bind(this));
    this.eventBus.subscribe('item.deleted', this.handleItemDeleted.bind(this));

    // Real-time events
    this.eventBus.subscribe('realtime.item.updated', this.handleRealtimeItemUpdate.bind(this));
    this.eventBus.subscribe('realtime.user.presence', this.handleUserPresence.bind(this));
  }

  private async handleBoardCreated(event: BoardCreatedEvent): Promise<void> {
    try {
      // Update search index
      await this.searchService.indexBoard(event.board);

      // Initialize default automations
      await this.automationService.createDefaultRules(event.board.id);

      // Update analytics
      await this.analyticsService.recordBoardCreation(event);

      // Send notifications to workspace members
      await this.notificationService.notifyWorkspaceMembers(
        event.board.workspaceId,
        'board_created',
        { board: event.board, createdBy: event.createdBy }
      );

    } catch (error) {
      this.logger.error('Failed to handle board created event', {
        error: error.message,
        boardId: event.board.id,
        eventId: event.id
      });
    }
  }

  private async handleRealtimeItemUpdate(event: RealtimeItemUpdateEvent): Promise<void> {
    try {
      // Broadcast to WebSocket clients
      await this.webSocketService.broadcastToBoardMembers(
        event.item.boardId,
        'item.updated',
        {
          item: event.item,
          changes: event.changes,
          updatedBy: event.updatedBy,
          timestamp: event.timestamp
        },
        event.updatedBy // Exclude the user who made the change
      );

      // Update search index asynchronously
      setImmediate(async () => {
        await this.searchService.updateItemIndex(event.item);
      });

      // Trigger automation rules if significant changes
      if (this.isSignificantChange(event.changes)) {
        await this.automationService.triggerEvent('item.updated', {
          item: event.item,
          changes: event.changes,
          context: event.context
        });
      }

    } catch (error) {
      this.logger.error('Failed to handle realtime item update', {
        error: error.message,
        itemId: event.item.id,
        eventId: event.id
      });
    }
  }

  private isSignificantChange(changes: Record<string, any>): boolean {
    const significantFields = [
      'status', 'assignees', 'priority', 'dueDate', 'parentId'
    ];

    return Object.keys(changes).some(field =>
      significantFields.includes(field)
    );
  }
}
```

---

## Real-time Collaboration Patterns

### WebSocket Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    Real-time Collaboration Integration                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        Frontend WebSocket Integration                       │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐     events    ┌─────────────────┐     state   ┌──────┐│  │
│  │  │   UI Components │ ◀──────────── │   WebSocket     │ ◀─────────── │ Store││  │
│  │  │                 │               │   Client        │              │      ││  │
│  │  │ • BoardView     │               │                 │              │ Redux││  │
│  │  │ • ItemCard      │ ──────────▶   │ • Connection    │ ──────────▶  │ RTK  ││  │
│  │  │ • Presence      │    actions    │ • Event Handler │    updates   │ Query││  │
│  │  │ • Conflicts     │               │ • State Sync    │              │      ││  │
│  │  └─────────────────┘               └─────────────────┘              └──────┘│  │
│  │           │                                  │                              │  │
│  │           │                                  ▼                              │  │
│  │           │                        ┌─────────────────┐                     │  │
│  │           │                        │   Optimistic    │                     │  │
│  │           │                        │   Update        │                     │  │
│  │           │                        │   Manager       │                     │  │
│  │           │                        │                 │                     │  │
│  │           │                        │ • Local Apply   │                     │  │
│  │           │                        │ • Rollback      │                     │  │
│  │           │                        │ • Confirmation  │                     │  │
│  │           │                        │ • Conflict Res  │                     │  │
│  │           │                        └─────────────────┘                     │  │
│  │           │                                  │                              │  │
│  │           ▼                                  ▼                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    WebSocket Message Bus                           │   │  │
│  │  │                                                                     │   │  │
│  │  │  Message Types:                                                     │   │  │
│  │  │  • item.update.request → server                                    │   │  │
│  │  │  • item.update.broadcast ← server                                  │   │  │
│  │  │  • presence.update → server                                        │   │  │
│  │  │  • presence.changed ← server                                       │   │  │
│  │  │  • conflict.detected ← server                                      │   │  │
│  │  │  • conflict.resolved → server                                      │   │  │
│  │  └─────────────────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        Backend WebSocket Integration                        │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐               ┌─────────────────┐               ┌─────┐│  │
│  │  │  Socket.IO      │  authenticates │  Auth Service   │  validates    │User ││  │
│  │  │  Server         │ ◀─────────────│                 │ ◀─────────────│Mgmt ││  │
│  │  │                 │               │ • JWT Verify    │               │     ││  │
│  │  │ • Connection    │ ──────────────▶│ • Permission    │ ──────────────▶│     ││  │
│  │  │ • Room Mgmt     │    requests    │ • Rate Limit    │    queries    │     ││  │
│  │  │ • Broadcasting  │               │ • Audit Log     │               │     ││  │
│  │  └─────────────────┘               └─────────────────┘               └─────┘│  │
│  │           │                                                                  │  │
│  │           ▼                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                      Message Processing Pipeline                   │   │  │
│  │  │                                                                     │   │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │  │
│  │  │  │   Receive   │  │  Validate   │  │   Process   │  │  Broadcast  │ │  │  │
│  │  │  │   Message   │─▶│   Message   │─▶│   Business  │─▶│   to Rooms  │ │  │  │
│  │  │  │             │  │             │  │   Logic     │  │             │ │  │  │
│  │  │  │ • Parse     │  │ • Schema    │  │ • Service   │  │ • Selective │ │  │  │
│  │  │  │ • Rate Limit│  │ • Auth      │  │ • Database  │  │ • Efficient │ │  │  │
│  │  │  │ • Queue     │  │ • Permission│  │ • Events    │  │ • Real-time │ │  │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │  │  │
│  │  └─────────────────────────────────────────────────────────────────────┘   │  │
│  │           │                                                                  │  │
│  │           ▼                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                     Service Integration Layer                      │   │  │
│  │  │                                                                     │   │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │  │
│  │  │  │ ItemService │  │BoardService │  │PermissionSvc│  │ EventBus    │ │  │  │
│  │  │  │             │  │             │  │             │  │             │ │  │  │
│  │  │  │ • Update    │  │ • Get Board │  │ • Check     │  │ • Publish   │ │  │  │
│  │  │  │ • Validate  │  │ • Members   │  │ • Authorize │  │ • Subscribe │ │  │  │
│  │  │  │ • Persist   │  │ • Settings  │  │ • Audit     │  │ • Route     │ │  │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │  │  │
│  │  └─────────────────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Real-time Implementation Patterns

```typescript
// Real-time Collaboration Service Integration

@injectable()
export class CollaborationService {
  constructor(
    @inject(TYPES.WebSocketServer) private wsServer: IWebSocketServer,
    @inject(TYPES.ItemService) private itemService: IItemService,
    @inject(TYPES.BoardService) private boardService: IBoardService,
    @inject(TYPES.PermissionService) private permissionService: IPermissionService,
    @inject(TYPES.ConflictResolver) private conflictResolver: IConflictResolver,
    @inject(TYPES.PresenceManager) private presenceManager: IPresenceManager,
    @inject(TYPES.EventBus) private eventBus: IEventBus,
    @inject(TYPES.Logger) private logger: ILogger
  ) {}

  // Handle real-time item updates with conflict detection
  async handleItemUpdate(
    socket: Socket,
    updateRequest: RealtimeItemUpdateRequest
  ): Promise<void> {
    const userId = socket.data.userId;
    const { itemId, updates, optimisticId, timestamp } = updateRequest;

    try {
      // Validate permissions
      await this.permissionService.requirePermission(
        userId,
        'item:write',
        itemId
      );

      // Check for conflicts with other users
      const conflicts = await this.conflictResolver.detectConflicts(
        itemId,
        updates,
        userId,
        timestamp
      );

      if (conflicts.length > 0) {
        // Send conflict notification to client
        socket.emit('item.conflict', {
          itemId,
          conflicts,
          optimisticId,
          timestamp: Date.now()
        });

        // Log conflict for monitoring
        this.logger.warn('Item update conflict detected', {
          itemId,
          userId,
          conflicts: conflicts.length,
          conflictFields: conflicts.map(c => c.field)
        });

        return;
      }

      // Apply update through service layer
      const updatedItem = await this.itemService.updateItem(
        itemId,
        updates,
        { userId, optimistic: false }
      );

      // Get board information for broadcasting
      const board = await this.boardService.getBoard(
        updatedItem.boardId,
        { userId }
      );

      // Broadcast to other users in the board
      await this.broadcastItemUpdate(
        board.id,
        updatedItem,
        updates,
        userId,
        optimisticId
      );

      // Confirm to originating client
      socket.emit('item.update.success', {
        itemId,
        optimisticId,
        item: updatedItem,
        timestamp: Date.now()
      });

      // Update user activity
      await this.presenceManager.updateActivity(userId, board.id, {
        type: 'item_edit',
        itemId,
        timestamp: Date.now()
      });

    } catch (error) {
      this.logger.error('Real-time item update failed', {
        error: error.message,
        itemId,
        userId,
        updates: Object.keys(updates)
      });

      socket.emit('item.update.error', {
        itemId,
        optimisticId,
        error: error.message,
        timestamp: Date.now()
      });
    }
  }

  private async broadcastItemUpdate(
    boardId: string,
    item: Item,
    changes: Record<string, any>,
    excludeUserId: string,
    optimisticId?: string
  ): Promise<void> {
    const boardRoom = `board:${boardId}`;

    // Get all users in the board room
    const roomUsers = await this.wsServer.getUsersInRoom(boardRoom);

    // Filter out the user who made the change
    const targetUsers = roomUsers.filter(userId => userId !== excludeUserId);

    if (targetUsers.length === 0) {
      return; // No one to broadcast to
    }

    // Prepare broadcast message
    const broadcastMessage = {
      type: 'item.updated',
      data: {
        item: this.sanitizeItemForBroadcast(item),
        changes,
        updatedBy: excludeUserId,
        optimisticId,
        timestamp: Date.now()
      }
    };

    // Broadcast efficiently
    await this.wsServer.broadcastToRoom(boardRoom, broadcastMessage, [excludeUserId]);

    // Publish event for other integrations
    await this.eventBus.publish('realtime.item.updated', {
      itemId: item.id,
      boardId,
      changes,
      updatedBy: excludeUserId,
      targetUsers,
      timestamp: new Date()
    });
  }

  // Handle user presence updates
  async handlePresenceUpdate(
    socket: Socket,
    presenceUpdate: PresenceUpdateRequest
  ): Promise<void> {
    const userId = socket.data.userId;
    const { boardId, presence } = presenceUpdate;

    try {
      // Validate board access
      await this.permissionService.requirePermission(
        userId,
        'board:read',
        boardId
      );

      // Update presence in manager
      await this.presenceManager.updatePresence(userId, boardId, {
        ...presence,
        socketId: socket.id,
        timestamp: Date.now()
      });

      // Broadcast presence update to other board members
      const boardRoom = `board:${boardId}`;
      socket.to(boardRoom).emit('presence.updated', {
        userId,
        presence,
        timestamp: Date.now()
      });

    } catch (error) {
      this.logger.error('Presence update failed', {
        error: error.message,
        userId,
        boardId
      });
    }
  }

  // Handle cursor movement with throttling
  async handleCursorMove(
    socket: Socket,
    cursorUpdate: CursorUpdateRequest
  ): Promise<void> {
    const userId = socket.data.userId;
    const { boardId, position } = cursorUpdate;

    // Throttle cursor updates (max 30 FPS)
    const throttleKey = `cursor:${userId}:${boardId}`;
    if (await this.isThrottled(throttleKey, 33)) {
      return;
    }

    try {
      // Update cursor position
      await this.presenceManager.updateCursor(userId, boardId, position);

      // Broadcast to other users (very lightweight)
      const boardRoom = `board:${boardId}`;
      socket.to(boardRoom).emit('cursor.moved', {
        userId,
        position,
        timestamp: Date.now()
      });

    } catch (error) {
      // Don't log cursor errors as they're frequent and not critical
      console.debug('Cursor update failed', { userId, boardId, error: error.message });
    }
  }

  private async isThrottled(key: string, intervalMs: number): Promise<boolean> {
    const now = Date.now();
    const lastUpdate = await this.cache.get(key);

    if (lastUpdate && (now - lastUpdate) < intervalMs) {
      return true;
    }

    await this.cache.set(key, now, Math.ceil(intervalMs / 1000));
    return false;
  }

  private sanitizeItemForBroadcast(item: Item): Partial<Item> {
    // Only send necessary fields to reduce bandwidth
    return {
      id: item.id,
      boardId: item.boardId,
      name: item.name,
      data: item.data,
      position: item.position,
      assignees: item.assignees,
      updatedAt: item.updatedAt
    };
  }
}

// Conflict Resolution Integration Pattern
@injectable()
export class ConflictResolver {
  constructor(
    @inject(TYPES.CacheManager) private cache: ICacheManager,
    @inject(TYPES.Logger) private logger: ILogger
  ) {}

  async detectConflicts(
    itemId: string,
    updates: Record<string, any>,
    userId: string,
    timestamp: number
  ): Promise<Conflict[]> {
    const conflictKey = `conflicts:${itemId}`;
    const activeEdits = await this.cache.get(conflictKey) || {};

    const conflicts: Conflict[] = [];
    const currentTime = Date.now();

    // Check each field for conflicts
    for (const [field, value] of Object.entries(updates)) {
      const activeEdit = activeEdits[field];

      if (activeEdit && activeEdit.userId !== userId) {
        const timeDiff = currentTime - activeEdit.timestamp;

        // Consider it a conflict if another user edited within 10 seconds
        if (timeDiff < 10000) {
          conflicts.push({
            field,
            conflictingUserId: activeEdit.userId,
            conflictingValue: activeEdit.value,
            conflictingTimestamp: activeEdit.timestamp,
            proposedValue: value,
            proposedTimestamp: timestamp
          });
        }
      }
    }

    // Track current edits
    const updatedActiveEdits = { ...activeEdits };
    for (const [field, value] of Object.entries(updates)) {
      updatedActiveEdits[field] = {
        userId,
        value,
        timestamp: currentTime
      };
    }

    // Cache active edits with TTL
    await this.cache.set(conflictKey, updatedActiveEdits, 30);

    return conflicts;
  }

  async resolveConflict(
    itemId: string,
    conflict: Conflict,
    resolution: ConflictResolution
  ): Promise<ResolvedUpdate> {
    this.logger.info('Resolving conflict', {
      itemId,
      field: conflict.field,
      strategy: resolution.strategy
    });

    switch (resolution.strategy) {
      case 'accept_mine':
        return {
          field: conflict.field,
          value: conflict.proposedValue,
          resolvedBy: resolution.userId,
          strategy: 'accept_mine'
        };

      case 'accept_theirs':
        return {
          field: conflict.field,
          value: conflict.conflictingValue,
          resolvedBy: resolution.userId,
          strategy: 'accept_theirs'
        };

      case 'merge':
        return this.mergeValues(conflict, resolution);

      case 'custom':
        return {
          field: conflict.field,
          value: resolution.customValue,
          resolvedBy: resolution.userId,
          strategy: 'custom'
        };

      default:
        throw new Error(`Unknown resolution strategy: ${resolution.strategy}`);
    }
  }

  private mergeValues(
    conflict: Conflict,
    resolution: ConflictResolution
  ): ResolvedUpdate {
    // Implement intelligent merging based on field type
    const { proposedValue, conflictingValue } = conflict;

    if (Array.isArray(proposedValue) && Array.isArray(conflictingValue)) {
      // Merge arrays by combining unique values
      const merged = [...new Set([...conflictingValue, ...proposedValue])];
      return {
        field: conflict.field,
        value: merged,
        resolvedBy: resolution.userId,
        strategy: 'merge'
      };
    }

    if (typeof proposedValue === 'string' && typeof conflictingValue === 'string') {
      // For strings, concatenate with separator
      const merged = `${conflictingValue} | ${proposedValue}`;
      return {
        field: conflict.field,
        value: merged,
        resolvedBy: resolution.userId,
        strategy: 'merge'
      };
    }

    // Default to proposed value for non-mergeable types
    return {
      field: conflict.field,
      value: proposedValue,
      resolvedBy: resolution.userId,
      strategy: 'merge_fallback'
    };
  }
}
```

---

## Event-Driven Integration Patterns

### Event Bus Architecture Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         Event-Driven Integration Architecture                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                            Event Producers                                  │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │   │
│  │  │  Domain         │  │  Application    │  │  Infrastructure │            │   │
│  │  │  Services       │  │  Services       │  │  Events         │            │   │
│  │  │                 │  │                 │  │                 │            │   │
│  │  │ • BoardService  │  │ • AuthService   │  │ • SystemEvents  │            │   │
│  │  │ • ItemService   │  │ • NotifService  │  │ • HealthChecks  │            │   │
│  │  │ • UserService   │  │ • EmailService  │  │ • Errors        │            │   │
│  │  │ • AutoService   │  │ • FileService   │  │ • Metrics       │            │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │   │
│  │           │                    │                    │                      │   │
│  │           ▼                    ▼                    ▼                      │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                        Event Bus Abstraction                       │   │   │
│  │  │                                                                     │   │   │
│  │  │  interface IEventBus {                                              │   │   │
│  │  │    publish<T>(eventName: string, payload: T): Promise<void>        │   │   │
│  │  │    subscribe<T>(eventName: string, handler: EventHandler<T>): void │   │   │
│  │  │    unsubscribe(eventName: string, handler: EventHandler): void     │   │   │
│  │  │  }                                                                  │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          Event Infrastructure                               │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │   │
│  │  │  Redis Pub/Sub  │  │   Kafka Stream  │  │  Event Store    │            │   │
│  │  │  (Real-time)    │  │  (Durability)   │  │  (Audit/Replay) │            │   │
│  │  │                 │  │                 │  │                 │            │   │
│  │  │ • Fast delivery │  │ • Reliability   │  │ • Event Sourcing│            │   │
│  │  │ • Simple setup  │  │ • Partitioning  │  │ • Time Travel   │            │   │
│  │  │ • Memory based  │  │ • Replay        │  │ • Debugging     │            │   │
│  │  │ • Volatile      │  │ • Persistent    │  │ • Compliance    │            │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                            Event Consumers                                  │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │   │
│  │  │   Real-time     │  │   Automation    │  │   Analytics     │            │   │
│  │  │   Updates       │  │   Engine        │  │   Processing    │            │   │
│  │  │                 │  │                 │  │                 │            │   │
│  │  │ • WebSocket     │  │ • Rule Engine   │  │ • Data Aggreg   │            │   │
│  │  │ • Notifications │  │ • Triggers      │  │ • Reporting     │            │   │
│  │  │ • UI Updates    │  │ • Workflows     │  │ • Metrics       │            │   │
│  │  │ • Presence      │  │ • Integration   │  │ • Insights      │            │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │   │
│  │  │   Search        │  │   Audit &       │  │   External      │            │   │
│  │  │   Indexing      │  │   Compliance    │  │   Integration   │            │   │
│  │  │                 │  │                 │  │                 │            │   │
│  │  │ • ES Indexing   │  │ • Audit Logs    │  │ • Webhooks      │            │   │
│  │  │ • Search Update │  │ • Compliance    │  │ • API Calls     │            │   │
│  │  │ • Faceted Data  │  │ • Data Gov      │  │ • Sync Jobs     │            │   │
│  │  │ • Suggestions   │  │ • GDPR          │  │ • Notifications │            │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Event Bus Implementation Pattern

```typescript
// Event Bus Implementation with Multiple Backends

@injectable()
export class EventBus implements IEventBus {
  private handlers = new Map<string, Set<EventHandler>>();
  private redisPublisher: Redis;
  private redisSubscriber: Redis;
  private eventStore: IEventStore;

  constructor(
    @inject(TYPES.RedisPublisher) redisPublisher: Redis,
    @inject(TYPES.RedisSubscriber) redisSubscriber: Redis,
    @inject(TYPES.EventStore) eventStore: IEventStore,
    @inject(TYPES.Logger) private logger: ILogger
  ) {
    this.redisPublisher = redisPublisher;
    this.redisSubscriber = redisSubscriber;
    this.eventStore = eventStore;

    this.setupRedisSubscriptions();
  }

  async publish<T>(eventName: string, payload: T): Promise<void> {
    const eventId = generateEventId();
    const timestamp = new Date();

    const event: DomainEvent<T> = {
      id: eventId,
      name: eventName,
      payload,
      timestamp,
      metadata: {
        publishedBy: this.getPublisherId(),
        correlationId: this.getCorrelationId(),
        version: '1.0'
      }
    };

    try {
      // Store event for audit and replay
      await this.eventStore.append(event);

      // Publish to Redis for real-time delivery
      await this.redisPublisher.publish(
        `events:${eventName}`,
        JSON.stringify(event)
      );

      // Handle local subscribers immediately
      await this.handleLocalSubscribers(eventName, event);

      this.logger.debug('Event published', {
        eventId,
        eventName,
        payloadSize: JSON.stringify(payload).length
      });

    } catch (error) {
      this.logger.error('Failed to publish event', {
        eventId,
        eventName,
        error: error.message
      });

      // Publish to dead letter queue for retry
      await this.publishToDeadLetter(event, error);
      throw error;
    }
  }

  subscribe<T>(eventName: string, handler: EventHandler<T>): void {
    if (!this.handlers.has(eventName)) {
      this.handlers.set(eventName, new Set());

      // Subscribe to Redis pattern for this event
      this.redisSubscriber.subscribe(`events:${eventName}`);
    }

    this.handlers.get(eventName)!.add(handler);

    this.logger.debug('Event handler subscribed', {
      eventName,
      handlerCount: this.handlers.get(eventName)!.size
    });
  }

  private async handleLocalSubscribers<T>(
    eventName: string,
    event: DomainEvent<T>
  ): Promise<void> {
    const handlers = this.handlers.get(eventName);
    if (!handlers || handlers.size === 0) {
      return;
    }

    // Execute handlers in parallel but catch individual failures
    const handlerPromises = Array.from(handlers).map(async (handler) => {
      try {
        await handler(event);
      } catch (error) {
        this.logger.error('Event handler failed', {
          eventId: event.id,
          eventName,
          error: error.message
        });

        // Don't rethrow to avoid breaking other handlers
      }
    });

    await Promise.allSettled(handlerPromises);
  }

  private setupRedisSubscriptions(): void {
    this.redisSubscriber.on('message', async (channel: string, message: string) => {
      try {
        const event = JSON.parse(message) as DomainEvent<any>;
        const eventName = channel.replace('events:', '');

        // Skip if this instance published the event (avoid loops)
        if (event.metadata.publishedBy === this.getPublisherId()) {
          return;
        }

        await this.handleLocalSubscribers(eventName, event);

      } catch (error) {
        this.logger.error('Failed to handle Redis event', {
          channel,
          error: error.message
        });
      }
    });
  }

  private async publishToDeadLetter(
    event: DomainEvent<any>,
    error: Error
  ): Promise<void> {
    try {
      await this.redisPublisher.lpush('events:dead_letter', JSON.stringify({
        event,
        error: error.message,
        timestamp: new Date()
      }));
    } catch (dlqError) {
      this.logger.error('Failed to publish to dead letter queue', {
        originalError: error.message,
        dlqError: dlqError.message
      });
    }
  }
}

// Comprehensive Event Handler Integration Example
@injectable()
export class IntegratedEventHandlers {
  constructor(
    @inject(TYPES.WebSocketService) private wsService: IWebSocketService,
    @inject(TYPES.SearchService) private searchService: ISearchService,
    @inject(TYPES.NotificationService) private notificationService: INotificationService,
    @inject(TYPES.AnalyticsService) private analyticsService: IAnalyticsService,
    @inject(TYPES.AutomationService) private automationService: IAutomationService,
    @inject(TYPES.AuditService) private auditService: IAuditService,
    @inject(TYPES.Logger) private logger: ILogger
  ) {}

  @EventHandler('item.created')
  async handleItemCreated(event: DomainEvent<ItemCreatedEvent>): Promise<void> {
    const { item, createdBy, boardId } = event.payload;

    try {
      // Real-time updates
      await this.wsService.broadcastToBoardMembers(
        boardId,
        'item.created',
        { item, createdBy },
        createdBy
      );

      // Search indexing
      await this.searchService.indexItem(item);

      // Notifications
      await this.notificationService.notifyItemCreated(item, createdBy);

      // Analytics
      await this.analyticsService.recordItemCreation(item, createdBy);

      // Automation triggers
      await this.automationService.triggerEvent('item_created', {
        item,
        context: { boardId, userId: createdBy }
      });

      // Audit logging
      await this.auditService.logAction({
        action: 'item.created',
        userId: createdBy,
        resourceId: item.id,
        resourceType: 'item',
        timestamp: event.timestamp
      });

    } catch (error) {
      this.logger.error('Failed to handle item created event', {
        itemId: item.id,
        eventId: event.id,
        error: error.message
      });
    }
  }

  @EventHandler('board.shared')
  async handleBoardShared(event: DomainEvent<BoardSharedEvent>): Promise<void> {
    const { boardId, sharedWith, sharedBy } = event.payload;

    try {
      // Notify each new member
      for (const userId of sharedWith) {
        await this.notificationService.notifyBoardAccess(
          userId,
          boardId,
          sharedBy,
          'shared'
        );

        // Add to user's board list cache
        await this.wsService.notifyUser(userId, 'board.access_granted', {
          boardId,
          grantedBy: sharedBy,
          timestamp: event.timestamp
        });
      }

      // Update search permissions
      await this.searchService.updateBoardPermissions(boardId, sharedWith);

      // Analytics
      await this.analyticsService.recordBoardSharing(
        boardId,
        sharedBy,
        sharedWith.length
      );

    } catch (error) {
      this.logger.error('Failed to handle board shared event', {
        boardId,
        eventId: event.id,
        error: error.message
      });
    }
  }

  @EventHandler('automation.executed')
  async handleAutomationExecuted(event: DomainEvent<AutomationExecutedEvent>): Promise<void> {
    const { executionId, ruleId, results, triggeredBy } = event.payload;

    try {
      // Analytics for automation effectiveness
      await this.analyticsService.recordAutomationExecution({
        executionId,
        ruleId,
        success: results.every(r => r.status === 'success'),
        executionTime: event.metadata.executionTime,
        triggeredBy
      });

      // Notify rule owner if execution failed
      if (results.some(r => r.status === 'error')) {
        await this.notificationService.notifyAutomationFailure(
          ruleId,
          executionId,
          results.filter(r => r.status === 'error')
        );
      }

      // Audit logging
      await this.auditService.logAutomationExecution({
        executionId,
        ruleId,
        results,
        triggeredBy,
        timestamp: event.timestamp
      });

    } catch (error) {
      this.logger.error('Failed to handle automation executed event', {
        executionId,
        ruleId,
        eventId: event.id,
        error: error.message
      });
    }
  }
}

// Event Sourcing Integration for Critical Operations
@injectable()
export class BoardEventSourcingService {
  constructor(
    @inject(TYPES.EventStore) private eventStore: IEventStore,
    @inject(TYPES.EventBus) private eventBus: IEventBus,
    @inject(TYPES.Logger) private logger: ILogger
  ) {}

  async createBoard(
    command: CreateBoardCommand,
    context: UserContext
  ): Promise<Board> {
    const boardId = generateId();
    const timestamp = new Date();

    // Create events
    const events: DomainEvent[] = [
      {
        id: generateEventId(),
        name: 'board.creation_initiated',
        aggregateId: boardId,
        aggregateType: 'Board',
        version: 1,
        payload: {
          boardId,
          workspaceId: command.workspaceId,
          name: command.name,
          description: command.description,
          initiatedBy: context.userId
        },
        timestamp
      }
    ];

    try {
      // Validate command
      await this.validateCreateBoardCommand(command, context);

      // Store events
      await this.eventStore.appendToAggregate(boardId, events);

      // Apply events to create board aggregate
      const board = this.applyEvents(events);

      // Publish events for side effects
      for (const event of events) {
        await this.eventBus.publish(event.name, event.payload);
      }

      // Add completion event
      const completionEvent = {
        id: generateEventId(),
        name: 'board.created',
        aggregateId: boardId,
        aggregateType: 'Board',
        version: 2,
        payload: {
          board,
          createdBy: context.userId
        },
        timestamp: new Date()
      };

      await this.eventStore.appendToAggregate(boardId, [completionEvent]);
      await this.eventBus.publish(completionEvent.name, completionEvent.payload);

      return board;

    } catch (error) {
      // Store failure event
      const failureEvent = {
        id: generateEventId(),
        name: 'board.creation_failed',
        aggregateId: boardId,
        aggregateType: 'Board',
        version: events.length + 1,
        payload: {
          boardId,
          error: error.message,
          command,
          failedBy: context.userId
        },
        timestamp: new Date()
      };

      await this.eventStore.appendToAggregate(boardId, [failureEvent]);
      await this.eventBus.publish(failureEvent.name, failureEvent.payload);

      throw error;
    }
  }

  async replayBoardHistory(boardId: string): Promise<Board> {
    const events = await this.eventStore.getAggregateEvents(boardId);
    return this.applyEvents(events);
  }

  private applyEvents(events: DomainEvent[]): Board {
    let board: Partial<Board> = {};

    for (const event of events) {
      switch (event.name) {
        case 'board.creation_initiated':
          board = {
            id: event.payload.boardId,
            workspaceId: event.payload.workspaceId,
            name: event.payload.name,
            description: event.payload.description,
            createdById: event.payload.initiatedBy,
            createdAt: event.timestamp,
            version: event.version
          };
          break;

        case 'board.updated':
          board = {
            ...board,
            ...event.payload.changes,
            updatedAt: event.timestamp,
            version: event.version
          };
          break;

        case 'board.archived':
          board = {
            ...board,
            archivedAt: event.timestamp,
            archivedBy: event.payload.archivedBy,
            version: event.version
          };
          break;
      }
    }

    return board as Board;
  }
}
```

---

## Testing Integration Patterns

### Test Infrastructure Integration

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create comprehensive architecture design document", "status": "completed", "activeForm": "Creating comprehensive architecture design document"}, {"content": "Design technology stack with testing infrastructure focus", "status": "completed", "activeForm": "Designing technology stack with testing infrastructure focus"}, {"content": "Create detailed component architecture diagram", "status": "completed", "activeForm": "Creating detailed component architecture diagram"}, {"content": "Define integration patterns for real-time collaboration", "status": "completed", "activeForm": "Defining integration patterns for real-time collaboration"}, {"content": "Specify API architecture for missing services", "status": "in_progress", "activeForm": "Specifying API architecture for missing services"}]