# Sunday.com - Advanced System Integration Patterns

## Executive Summary

This document defines advanced system integration patterns for Sunday.com, providing enterprise-grade solutions for complex distributed system challenges. These patterns ensure reliable, scalable, and maintainable integration between microservices, external systems, and data stores while maintaining high performance and fault tolerance.

## Table of Contents

1. [Integration Pattern Overview](#integration-pattern-overview)
2. [Distributed Transaction Patterns](#distributed-transaction-patterns)
3. [Data Consistency Patterns](#data-consistency-patterns)
4. [Resilience & Fault Tolerance Patterns](#resilience--fault-tolerance-patterns)
5. [Performance Optimization Patterns](#performance-optimization-patterns)
6. [Security Integration Patterns](#security-integration-patterns)
7. [Observability Integration Patterns](#observability-integration-patterns)
8. [Deployment & Release Patterns](#deployment--release-patterns)
9. [Anti-Patterns & Best Practices](#anti-patterns--best-practices)
10. [Implementation Guidelines](#implementation-guidelines)

---

## Integration Pattern Overview

### Pattern Classification Framework

```
┌─────────────────────────────────────────────────────────────────┐
│                Integration Pattern Taxonomy                     │
├─────────────────────────────────────────────────────────────────┤
│  Communication Patterns                                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Synchronous │ Asynchronous │ Hybrid │ Event-Driven │ Batch │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Data Patterns                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ CQRS │ Event Sourcing │ Saga │ Outbox │ CDC │ Materialized  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Resilience Patterns                                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Circuit Breaker │ Retry │ Bulkhead │ Timeout │ Fallback    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Security Patterns                                             │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ OAuth │ mTLS │ JWT │ API Gateway │ Zero Trust │ Encryption  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern Selection Matrix

| Scenario | Primary Pattern | Secondary Pattern | Use Case |
|----------|----------------|-------------------|----------|
| **User Registration** | Saga Pattern | Event Sourcing | Multi-service transaction |
| **Real-time Collaboration** | Event Streaming | CQRS | Live updates |
| **File Processing** | Asynchronous Pipeline | Circuit Breaker | Heavy operations |
| **Third-party Integration** | Anti-corruption Layer | Retry Pattern | External systems |
| **Data Analytics** | Event Sourcing | Materialized Views | Historical analysis |
| **Payment Processing** | Saga Pattern | Compensating Actions | Financial transactions |

---

## Distributed Transaction Patterns

### 1. Saga Pattern Implementation

#### Orchestrator-based Saga

```typescript
// Saga Orchestrator for User Registration Process
interface SagaStep {
  name: string;
  execute: (context: SagaContext) => Promise<any>;
  compensate: (context: SagaContext) => Promise<void>;
  retryable: boolean;
  timeout: number;
}

class UserRegistrationSaga {
  private steps: SagaStep[] = [
    {
      name: 'validateUserData',
      execute: this.validateUserData.bind(this),
      compensate: this.compensateValidateUserData.bind(this),
      retryable: true,
      timeout: 5000,
    },
    {
      name: 'createUserAccount',
      execute: this.createUserAccount.bind(this),
      compensate: this.compensateCreateUserAccount.bind(this),
      retryable: true,
      timeout: 10000,
    },
    {
      name: 'setupUserWorkspace',
      execute: this.setupUserWorkspace.bind(this),
      compensate: this.compensateSetupUserWorkspace.bind(this),
      retryable: true,
      timeout: 15000,
    },
    {
      name: 'sendWelcomeEmail',
      execute: this.sendWelcomeEmail.bind(this),
      compensate: this.compensateSendWelcomeEmail.bind(this),
      retryable: false,
      timeout: 30000,
    },
    {
      name: 'updateAnalytics',
      execute: this.updateAnalytics.bind(this),
      compensate: this.compensateUpdateAnalytics.bind(this),
      retryable: false,
      timeout: 5000,
    },
  ];

  async execute(sagaContext: SagaContext): Promise<SagaResult> {
    const sagaId = randomUUID();
    const executedSteps: string[] = [];

    try {
      // Execute each step in sequence
      for (const step of this.steps) {
        await this.executeStepWithTimeout(step, sagaContext);
        executedSteps.push(step.name);

        // Save progress for recovery
        await this.saveSagaProgress(sagaId, executedSteps, sagaContext);
      }

      return {
        success: true,
        sagaId,
        result: sagaContext.result,
      };
    } catch (error) {
      // Compensate in reverse order
      await this.compensate(executedSteps.reverse(), sagaContext);

      return {
        success: false,
        sagaId,
        error: error.message,
        compensated: true,
      };
    }
  }

  private async executeStepWithTimeout(step: SagaStep, context: SagaContext): Promise<void> {
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error(`Step ${step.name} timed out`)), step.timeout);
    });

    try {
      await Promise.race([step.execute(context), timeoutPromise]);
    } catch (error) {
      if (step.retryable) {
        // Implement exponential backoff retry
        await this.retryStep(step, context, 3);
      } else {
        throw error;
      }
    }
  }

  private async retryStep(step: SagaStep, context: SagaContext, maxRetries: number): Promise<void> {
    let lastError: Error;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await step.execute(context);
        return;
      } catch (error) {
        lastError = error as Error;

        if (attempt < maxRetries) {
          const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
          await this.sleep(delay);
        }
      }
    }

    throw lastError!;
  }

  private async compensate(executedSteps: string[], context: SagaContext): Promise<void> {
    for (const stepName of executedSteps) {
      const step = this.steps.find(s => s.name === stepName);
      if (step) {
        try {
          await step.compensate(context);
        } catch (error) {
          // Log compensation failure but continue
          console.error(`Compensation failed for step ${stepName}:`, error);
        }
      }
    }
  }

  // Step implementations
  private async validateUserData(context: SagaContext): Promise<void> {
    const validationResult = await this.userValidationService.validate(context.userData);
    if (!validationResult.valid) {
      throw new Error(`Validation failed: ${validationResult.errors.join(', ')}`);
    }
    context.validatedData = validationResult.data;
  }

  private async createUserAccount(context: SagaContext): Promise<void> {
    const user = await this.userService.create(context.validatedData);
    context.userId = user.id;
    context.organizationId = user.organizationId;
  }

  private async setupUserWorkspace(context: SagaContext): Promise<void> {
    const workspace = await this.workspaceService.createDefault({
      organizationId: context.organizationId,
      ownerId: context.userId,
      name: `${context.validatedData.firstName}'s Workspace`,
    });
    context.workspaceId = workspace.id;

    // Create default board
    const board = await this.boardService.create({
      workspaceId: workspace.id,
      name: 'My First Board',
      template: 'getting-started',
    });
    context.boardId = board.id;
  }

  private async sendWelcomeEmail(context: SagaContext): Promise<void> {
    await this.emailService.sendWelcomeEmail({
      userId: context.userId,
      email: context.validatedData.email,
      firstName: context.validatedData.firstName,
      workspaceUrl: `https://app.sunday.com/workspace/${context.workspaceId}`,
    });
  }

  private async updateAnalytics(context: SagaContext): Promise<void> {
    await this.analyticsService.trackEvent({
      event: 'user_registered',
      userId: context.userId,
      organizationId: context.organizationId,
      properties: {
        registrationMethod: context.registrationMethod,
        source: context.source,
      },
    });
  }

  // Compensation methods
  private async compensateValidateUserData(context: SagaContext): Promise<void> {
    // No compensation needed for validation
  }

  private async compensateCreateUserAccount(context: SagaContext): Promise<void> {
    if (context.userId) {
      await this.userService.delete(context.userId);
    }
  }

  private async compensateSetupUserWorkspace(context: SagaContext): Promise<void> {
    if (context.workspaceId) {
      await this.workspaceService.delete(context.workspaceId);
    }
  }

  private async compensateSendWelcomeEmail(context: SagaContext): Promise<void> {
    // Cannot unsend email, but can send cancellation notice
    if (context.userId) {
      await this.emailService.sendRegistrationCancelled(context.validatedData.email);
    }
  }

  private async compensateUpdateAnalytics(context: SagaContext): Promise<void> {
    if (context.userId) {
      await this.analyticsService.trackEvent({
        event: 'user_registration_failed',
        userId: context.userId,
        organizationId: context.organizationId,
      });
    }
  }
}
```

#### Choreography-based Saga

```typescript
// Event-driven Saga using choreography
class ProjectCreationChoreography {
  private eventBus: EventBus;
  private sagaRepository: SagaRepository;

  constructor(eventBus: EventBus, sagaRepository: SagaRepository) {
    this.eventBus = eventBus;
    this.sagaRepository = sagaRepository;

    // Subscribe to relevant events
    this.subscribeToEvents();
  }

  private subscribeToEvents(): void {
    this.eventBus.subscribe('project.creation.requested', this.handleProjectCreationRequested.bind(this));
    this.eventBus.subscribe('project.created', this.handleProjectCreated.bind(this));
    this.eventBus.subscribe('project.creation.failed', this.handleProjectCreationFailed.bind(this));
    this.eventBus.subscribe('board.created', this.handleBoardCreated.bind(this));
    this.eventBus.subscribe('board.creation.failed', this.handleBoardCreationFailed.bind(this));
    this.eventBus.subscribe('team.notified', this.handleTeamNotified.bind(this));
  }

  async handleProjectCreationRequested(event: DomainEvent): Promise<void> {
    const sagaId = event.metadata.correlationId;

    // Initialize saga state
    const sagaState = {
      sagaId,
      status: 'in_progress',
      steps: {
        createProject: 'pending',
        createDefaultBoard: 'pending',
        notifyTeam: 'pending',
      },
      data: event.data,
      startedAt: new Date(),
    };

    await this.sagaRepository.save(sagaState);

    // Start the saga by creating the project
    await this.eventBus.publish({
      eventType: 'project.create.command',
      aggregateId: event.data.projectId,
      data: event.data,
      metadata: {
        correlationId: sagaId,
        timestamp: new Date(),
        source: 'project-creation-saga',
      },
    });
  }

  async handleProjectCreated(event: DomainEvent): Promise<void> {
    const sagaId = event.metadata.correlationId;
    const sagaState = await this.sagaRepository.findById(sagaId);

    if (!sagaState) return;

    // Update saga state
    sagaState.steps.createProject = 'completed';
    sagaState.data.projectId = event.aggregateId;
    await this.sagaRepository.save(sagaState);

    // Next step: Create default board
    await this.eventBus.publish({
      eventType: 'board.create.command',
      aggregateId: randomUUID(),
      data: {
        projectId: event.aggregateId,
        name: 'Main Board',
        template: 'default',
      },
      metadata: {
        correlationId: sagaId,
        timestamp: new Date(),
        source: 'project-creation-saga',
      },
    });
  }

  async handleBoardCreated(event: DomainEvent): Promise<void> {
    const sagaId = event.metadata.correlationId;
    const sagaState = await this.sagaRepository.findById(sagaId);

    if (!sagaState) return;

    // Update saga state
    sagaState.steps.createDefaultBoard = 'completed';
    sagaState.data.boardId = event.aggregateId;
    await this.sagaRepository.save(sagaState);

    // Next step: Notify team
    await this.eventBus.publish({
      eventType: 'team.notify.command',
      aggregateId: sagaState.data.projectId,
      data: {
        projectId: sagaState.data.projectId,
        boardId: event.aggregateId,
        teamMembers: sagaState.data.teamMembers,
        message: `New project "${sagaState.data.projectName}" has been created`,
      },
      metadata: {
        correlationId: sagaId,
        timestamp: new Date(),
        source: 'project-creation-saga',
      },
    });
  }

  async handleTeamNotified(event: DomainEvent): Promise<void> {
    const sagaId = event.metadata.correlationId;
    const sagaState = await this.sagaRepository.findById(sagaId);

    if (!sagaState) return;

    // Complete the saga
    sagaState.steps.notifyTeam = 'completed';
    sagaState.status = 'completed';
    sagaState.completedAt = new Date();
    await this.sagaRepository.save(sagaState);

    // Publish saga completed event
    await this.eventBus.publish({
      eventType: 'project.creation.completed',
      aggregateId: sagaState.data.projectId,
      data: {
        projectId: sagaState.data.projectId,
        boardId: sagaState.data.boardId,
        sagaId,
      },
      metadata: {
        correlationId: sagaId,
        timestamp: new Date(),
        source: 'project-creation-saga',
      },
    });
  }

  async handleProjectCreationFailed(event: DomainEvent): Promise<void> {
    const sagaId = event.metadata.correlationId;
    await this.compensateProjectCreation(sagaId, event.data.error);
  }

  async handleBoardCreationFailed(event: DomainEvent): Promise<void> {
    const sagaId = event.metadata.correlationId;
    await this.compensateBoardCreation(sagaId, event.data.error);
  }

  private async compensateProjectCreation(sagaId: string, error: any): Promise<void> {
    const sagaState = await this.sagaRepository.findById(sagaId);
    if (!sagaState) return;

    sagaState.status = 'compensating';
    await this.sagaRepository.save(sagaState);

    // No compensation needed as project creation failed
    sagaState.status = 'failed';
    sagaState.error = error;
    sagaState.completedAt = new Date();
    await this.sagaRepository.save(sagaState);
  }

  private async compensateBoardCreation(sagaId: string, error: any): Promise<void> {
    const sagaState = await this.sagaRepository.findById(sagaId);
    if (!sagaState) return;

    sagaState.status = 'compensating';
    await this.sagaRepository.save(sagaState);

    // Compensate by deleting the created project
    if (sagaState.data.projectId) {
      await this.eventBus.publish({
        eventType: 'project.delete.command',
        aggregateId: sagaState.data.projectId,
        data: { reason: 'saga_compensation' },
        metadata: {
          correlationId: sagaId,
          timestamp: new Date(),
          source: 'project-creation-saga-compensation',
        },
      });
    }

    sagaState.status = 'compensated';
    sagaState.error = error;
    sagaState.completedAt = new Date();
    await this.sagaRepository.save(sagaState);
  }
}
```

### 2. Outbox Pattern for Reliable Messaging

```typescript
// Outbox Pattern Implementation
class OutboxEventPublisher {
  private db: Database;
  private eventBus: EventBus;
  private isProcessing = false;
  private batchSize = 100;

  constructor(db: Database, eventBus: EventBus) {
    this.db = db;
    this.eventBus = eventBus;

    // Start outbox processor
    this.startOutboxProcessor();
  }

  async publishEventWithOutbox(
    aggregateEvent: DomainEvent,
    businessOperation: () => Promise<any>
  ): Promise<void> {
    await this.db.transaction(async (tx) => {
      // Execute business logic
      await businessOperation();

      // Store event in outbox table
      await tx.query(`
        INSERT INTO outbox_events (
          id, event_type, aggregate_id, event_data, correlation_id, created_at, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
      `, [
        aggregateEvent.eventId,
        aggregateEvent.eventType,
        aggregateEvent.aggregateId,
        JSON.stringify(aggregateEvent),
        aggregateEvent.metadata.correlationId,
        new Date(),
        'pending'
      ]);
    });
  }

  private startOutboxProcessor(): void {
    setInterval(async () => {
      if (!this.isProcessing) {
        await this.processOutboxEvents();
      }
    }, 1000); // Check every second
  }

  private async processOutboxEvents(): Promise<void> {
    this.isProcessing = true;

    try {
      const events = await this.db.query(`
        SELECT id, event_data FROM outbox_events
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT $1
        FOR UPDATE SKIP LOCKED
      `, [this.batchSize]);

      for (const row of events) {
        try {
          const event = JSON.parse(row.event_data);
          await this.eventBus.publishEvent(event);

          // Mark as published
          await this.db.query(`
            UPDATE outbox_events
            SET status = 'published', published_at = NOW()
            WHERE id = $1
          `, [row.id]);
        } catch (error) {
          // Mark as failed
          await this.db.query(`
            UPDATE outbox_events
            SET status = 'failed', error_message = $2, retry_count = retry_count + 1
            WHERE id = $1
          `, [row.id, error.message]);
        }
      }
    } finally {
      this.isProcessing = false;
    }
  }

  async retryFailedEvents(): Promise<void> {
    await this.db.query(`
      UPDATE outbox_events
      SET status = 'pending', error_message = NULL
      WHERE status = 'failed' AND retry_count < 3
    `);
  }
}

// Usage in Service
class ProjectService {
  private outboxPublisher: OutboxEventPublisher;
  private projectRepository: ProjectRepository;

  async createProject(projectData: CreateProjectData): Promise<Project> {
    const project = new Project(projectData);
    const event: DomainEvent = {
      eventId: randomUUID(),
      eventType: 'project.created',
      aggregateId: project.id,
      version: 1,
      data: project.toEventData(),
      metadata: {
        correlationId: projectData.correlationId || randomUUID(),
        timestamp: new Date(),
        source: 'project-service',
        userId: projectData.createdBy,
      },
    };

    await this.outboxPublisher.publishEventWithOutbox(
      event,
      async () => {
        await this.projectRepository.save(project);
      }
    );

    return project;
  }
}
```

---

## Data Consistency Patterns

### 1. CQRS with Event Sourcing

```typescript
// Command Side - Write Model
class ProjectCommandHandler {
  private eventStore: EventStore;

  constructor(eventStore: EventStore) {
    this.eventStore = eventStore;
  }

  async handleCreateProject(command: CreateProjectCommand): Promise<void> {
    // Load aggregate from event store
    const project = await this.eventStore.loadAggregate(Project, command.projectId);

    // Execute business logic
    project.create(command.data, command.userId);

    // Save new events
    const uncommittedEvents = project.getUncommittedEvents();
    await this.eventStore.appendEvents(
      command.projectId,
      project.version - uncommittedEvents.length,
      uncommittedEvents
    );

    project.markEventsAsCommitted();
  }

  async handleUpdateProject(command: UpdateProjectCommand): Promise<void> {
    const project = await this.eventStore.loadAggregate(Project, command.projectId);

    project.update(command.updates, command.userId);

    const uncommittedEvents = project.getUncommittedEvents();
    await this.eventStore.appendEvents(
      command.projectId,
      project.version - uncommittedEvents.length,
      uncommittedEvents
    );

    project.markEventsAsCommitted();
  }
}

// Query Side - Read Model
class ProjectQueryHandler {
  private readModelRepo: ProjectReadModelRepository;

  constructor(readModelRepo: ProjectReadModelRepository) {
    this.readModelRepo = readModelRepo;
  }

  async getProject(projectId: string): Promise<ProjectReadModel | null> {
    return this.readModelRepo.findById(projectId);
  }

  async getProjectsByWorkspace(workspaceId: string, filters: ProjectFilters): Promise<ProjectReadModel[]> {
    return this.readModelRepo.findByWorkspace(workspaceId, filters);
  }

  async getProjectStatistics(projectId: string): Promise<ProjectStatistics> {
    return this.readModelRepo.getStatistics(projectId);
  }
}

// Read Model Projector
class ProjectReadModelProjector {
  private readModelRepo: ProjectReadModelRepository;
  private eventBus: EventBus;

  constructor(readModelRepo: ProjectReadModelRepository, eventBus: EventBus) {
    this.readModelRepo = readModelRepo;
    this.eventBus = eventBus;

    this.subscribeToEvents();
  }

  private subscribeToEvents(): void {
    this.eventBus.subscribe('project.created', this.handleProjectCreated.bind(this));
    this.eventBus.subscribe('project.updated', this.handleProjectUpdated.bind(this));
    this.eventBus.subscribe('project.archived', this.handleProjectArchived.bind(this));
    this.eventBus.subscribe('item.created', this.handleItemCreated.bind(this));
    this.eventBus.subscribe('item.completed', this.handleItemCompleted.bind(this));
  }

  async handleProjectCreated(event: DomainEvent): Promise<void> {
    const readModel: ProjectReadModel = {
      id: event.aggregateId,
      name: event.data.name,
      description: event.data.description,
      workspaceId: event.data.workspaceId,
      ownerId: event.data.ownerId,
      status: 'active',
      statistics: {
        totalItems: 0,
        completedItems: 0,
        activeMembers: 1,
        lastActivity: event.metadata.timestamp,
      },
      createdAt: event.metadata.timestamp,
      updatedAt: event.metadata.timestamp,
    };

    await this.readModelRepo.save(readModel);
  }

  async handleProjectUpdated(event: DomainEvent): Promise<void> {
    const readModel = await this.readModelRepo.findById(event.aggregateId);
    if (!readModel) return;

    // Apply updates
    Object.assign(readModel, event.data.updates);
    readModel.updatedAt = event.metadata.timestamp;

    await this.readModelRepo.save(readModel);
  }

  async handleItemCreated(event: DomainEvent): Promise<void> {
    const projectId = event.data.projectId;
    const readModel = await this.readModelRepo.findById(projectId);
    if (!readModel) return;

    readModel.statistics.totalItems++;
    readModel.statistics.lastActivity = event.metadata.timestamp;

    await this.readModelRepo.save(readModel);
  }

  async handleItemCompleted(event: DomainEvent): Promise<void> {
    const projectId = event.data.projectId;
    const readModel = await this.readModelRepo.findById(projectId);
    if (!readModel) return;

    readModel.statistics.completedItems++;
    readModel.statistics.lastActivity = event.metadata.timestamp;

    await this.readModelRepo.save(readModel);
  }
}
```

### 2. Eventual Consistency with Compensation

```typescript
// Eventual Consistency Manager
class EventualConsistencyManager {
  private inconsistencyDetector: InconsistencyDetector;
  private consistencyRepairer: ConsistencyRepairer;
  private monitoringService: MonitoringService;

  constructor() {
    this.inconsistencyDetector = new InconsistencyDetector();
    this.consistencyRepairer = new ConsistencyRepairer();
    this.monitoringService = new MonitoringService();

    this.startConsistencyChecks();
  }

  private startConsistencyChecks(): void {
    // Run consistency checks every 5 minutes
    setInterval(async () => {
      await this.runConsistencyCheck();
    }, 5 * 60 * 1000);
  }

  async runConsistencyCheck(): Promise<void> {
    try {
      const inconsistencies = await this.inconsistencyDetector.detectInconsistencies();

      for (const inconsistency of inconsistencies) {
        await this.handleInconsistency(inconsistency);
      }

      // Report metrics
      await this.monitoringService.recordMetric('consistency_check_completed', {
        inconsistencies_found: inconsistencies.length,
        timestamp: new Date(),
      });
    } catch (error) {
      await this.monitoringService.recordError('consistency_check_failed', error);
    }
  }

  private async handleInconsistency(inconsistency: DataInconsistency): Promise<void> {
    switch (inconsistency.type) {
      case 'missing_projection':
        await this.repairMissingProjection(inconsistency);
        break;

      case 'stale_data':
        await this.repairStaleData(inconsistency);
        break;

      case 'duplicate_data':
        await this.repairDuplicateData(inconsistency);
        break;

      case 'orphaned_data':
        await this.repairOrphanedData(inconsistency);
        break;
    }
  }

  private async repairMissingProjection(inconsistency: DataInconsistency): Promise<void> {
    // Rebuild projection from event store
    const events = await this.eventStore.loadEvents(
      inconsistency.aggregateId,
      0 // From beginning
    );

    const projector = this.getProjectorForAggregate(inconsistency.aggregateType);
    for (const event of events) {
      await projector.project(event);
    }
  }
}

// Inconsistency Detection
class InconsistencyDetector {
  async detectInconsistencies(): Promise<DataInconsistency[]> {
    const inconsistencies: DataInconsistency[] = [];

    // Check for missing projections
    await this.checkMissingProjections(inconsistencies);

    // Check for stale data
    await this.checkStaleData(inconsistencies);

    // Check for orphaned references
    await this.checkOrphanedReferences(inconsistencies);

    return inconsistencies;
  }

  private async checkMissingProjections(inconsistencies: DataInconsistency[]): Promise<void> {
    // Compare event store with read models
    const query = `
      SELECT DISTINCT aggregate_id, aggregate_type
      FROM events
      WHERE created_at > NOW() - INTERVAL '1 hour'
      AND aggregate_id NOT IN (
        SELECT id FROM project_read_models
        UNION
        SELECT id FROM item_read_models
        UNION
        SELECT id FROM user_read_models
      )
    `;

    const missingProjections = await this.db.query(query);

    for (const row of missingProjections) {
      inconsistencies.push({
        type: 'missing_projection',
        aggregateId: row.aggregate_id,
        aggregateType: row.aggregate_type,
        severity: 'high',
        detectedAt: new Date(),
      });
    }
  }

  private async checkStaleData(inconsistencies: DataInconsistency[]): Promise<void> {
    // Check for read models that haven't been updated recently
    // but have recent events
    const query = `
      SELECT rm.id, rm.updated_at as rm_updated, MAX(e.created_at) as last_event
      FROM project_read_models rm
      JOIN events e ON rm.id = e.aggregate_id
      WHERE e.created_at > rm.updated_at + INTERVAL '5 minutes'
      GROUP BY rm.id, rm.updated_at
    `;

    const staleData = await this.db.query(query);

    for (const row of staleData) {
      inconsistencies.push({
        type: 'stale_data',
        aggregateId: row.id,
        aggregateType: 'project',
        severity: 'medium',
        detectedAt: new Date(),
        details: {
          readModelUpdated: row.rm_updated,
          lastEvent: row.last_event,
        },
      });
    }
  }
}
```

---

## Resilience & Fault Tolerance Patterns

### 1. Advanced Circuit Breaker Implementation

```typescript
// Multi-level Circuit Breaker with Metrics
class AdvancedCircuitBreaker {
  private state: CircuitBreakerState = 'CLOSED';
  private failureCount = 0;
  private successCount = 0;
  private lastFailureTime = 0;
  private halfOpenStartTime = 0;
  private metrics: CircuitBreakerMetrics;

  constructor(private config: CircuitBreakerConfig) {
    this.metrics = new CircuitBreakerMetrics(config.name);
  }

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    // Record attempt
    this.metrics.recordAttempt();

    if (this.state === 'OPEN') {
      if (this.shouldAttemptReset()) {
        this.state = 'HALF_OPEN';
        this.halfOpenStartTime = Date.now();
        this.metrics.recordStateChange('HALF_OPEN');
      } else {
        this.metrics.recordRejection();
        throw new CircuitBreakerOpenError('Circuit breaker is OPEN');
      }
    }

    try {
      const result = await this.executeWithTimeout(operation);
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure(error);
      throw error;
    }
  }

  private async executeWithTimeout<T>(operation: () => Promise<T>): Promise<T> {
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => {
        reject(new TimeoutError(`Operation timed out after ${this.config.timeout}ms`));
      }, this.config.timeout);
    });

    return Promise.race([operation(), timeoutPromise]);
  }

  private onSuccess(): void {
    this.resetFailureCount();

    if (this.state === 'HALF_OPEN') {
      this.successCount++;

      if (this.successCount >= this.config.halfOpenSuccessThreshold) {
        this.state = 'CLOSED';
        this.successCount = 0;
        this.metrics.recordStateChange('CLOSED');
      }
    }

    this.metrics.recordSuccess();
  }

  private onFailure(error: Error): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.shouldOpenCircuit()) {
      this.state = 'OPEN';
      this.metrics.recordStateChange('OPEN');
    }

    this.metrics.recordFailure(error);
  }

  private shouldOpenCircuit(): boolean {
    if (this.state === 'HALF_OPEN') {
      return true; // Any failure in half-open state opens the circuit
    }

    // Check failure threshold
    if (this.failureCount >= this.config.failureThreshold) {
      return true;
    }

    // Check failure rate over time window
    const recentFailures = this.metrics.getFailureRateInWindow(this.config.timeWindow);
    return recentFailures >= this.config.failureRateThreshold;
  }

  private shouldAttemptReset(): boolean {
    return Date.now() - this.lastFailureTime >= this.config.openTimeout;
  }

  private resetFailureCount(): void {
    this.failureCount = 0;
  }

  getState(): CircuitBreakerState {
    return this.state;
  }

  getMetrics(): CircuitBreakerStats {
    return this.metrics.getStats();
  }
}

// Circuit Breaker with Bulkhead Pattern
class BulkheadCircuitBreaker {
  private circuitBreakers: Map<string, AdvancedCircuitBreaker> = new Map();
  private resourcePools: Map<string, ResourcePool> = new Map();

  constructor(private config: BulkheadConfig) {
    this.initializeResourcePools();
  }

  private initializeResourcePools(): void {
    for (const [resourceType, poolConfig] of Object.entries(this.config.resourcePools)) {
      this.resourcePools.set(resourceType, new ResourcePool(poolConfig));

      this.circuitBreakers.set(
        resourceType,
        new AdvancedCircuitBreaker(poolConfig.circuitBreakerConfig)
      );
    }
  }

  async execute<T>(
    resourceType: string,
    operation: () => Promise<T>
  ): Promise<T> {
    const circuitBreaker = this.circuitBreakers.get(resourceType);
    const resourcePool = this.resourcePools.get(resourceType);

    if (!circuitBreaker || !resourcePool) {
      throw new Error(`Unknown resource type: ${resourceType}`);
    }

    // Acquire resource from pool
    const resource = await resourcePool.acquire();

    try {
      return await circuitBreaker.execute(async () => {
        return operation();
      });
    } finally {
      resourcePool.release(resource);
    }
  }
}

// Resource Pool Implementation
class ResourcePool {
  private pool: Resource[] = [];
  private inUse: Set<Resource> = new Set();
  private waitingQueue: Array<{
    resolve: (resource: Resource) => void;
    reject: (error: Error) => void;
    timeout: NodeJS.Timeout;
  }> = [];

  constructor(private config: ResourcePoolConfig) {
    this.initializePool();
  }

  private initializePool(): void {
    for (let i = 0; i < this.config.minSize; i++) {
      this.pool.push(this.createResource());
    }
  }

  async acquire(): Promise<Resource> {
    // Try to get an available resource
    if (this.pool.length > 0) {
      const resource = this.pool.pop()!;
      this.inUse.add(resource);
      return resource;
    }

    // Create new resource if under max limit
    if (this.inUse.size < this.config.maxSize) {
      const resource = this.createResource();
      this.inUse.add(resource);
      return resource;
    }

    // Wait for resource to become available
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        const index = this.waitingQueue.findIndex(item => item.resolve === resolve);
        if (index >= 0) {
          this.waitingQueue.splice(index, 1);
        }
        reject(new Error('Resource acquisition timeout'));
      }, this.config.acquireTimeout);

      this.waitingQueue.push({ resolve, reject, timeout });
    });
  }

  release(resource: Resource): void {
    this.inUse.delete(resource);

    // Serve waiting requests first
    if (this.waitingQueue.length > 0) {
      const waiter = this.waitingQueue.shift()!;
      clearTimeout(waiter.timeout);
      this.inUse.add(resource);
      waiter.resolve(resource);
      return;
    }

    // Return to pool if under min size
    if (this.pool.length < this.config.minSize) {
      this.pool.push(resource);
    } else {
      this.destroyResource(resource);
    }
  }

  private createResource(): Resource {
    return {
      id: randomUUID(),
      createdAt: new Date(),
      lastUsed: new Date(),
    };
  }

  private destroyResource(resource: Resource): void {
    // Cleanup resource if needed
  }
}
```

### 2. Retry Pattern with Jitter

```typescript
// Advanced Retry Pattern
class RetryPolicy {
  constructor(private config: RetryConfig) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    let lastError: Error;
    let attempt = 0;

    while (attempt < this.config.maxAttempts) {
      try {
        return await operation();
      } catch (error) {
        attempt++;
        lastError = error as Error;

        if (!this.shouldRetry(error, attempt)) {
          throw error;
        }

        if (attempt < this.config.maxAttempts) {
          const delay = this.calculateDelay(attempt);
          await this.sleep(delay);
        }
      }
    }

    throw lastError!;
  }

  private shouldRetry(error: any, attempt: number): boolean {
    if (attempt >= this.config.maxAttempts) {
      return false;
    }

    // Check if error is retryable
    if (this.config.retryableErrors) {
      return this.config.retryableErrors.some(retryableError =>
        error instanceof retryableError ||
        error.name === retryableError.name ||
        error.code === retryableError.code
      );
    }

    // Default retryable conditions
    return (
      error.code === 'ECONNRESET' ||
      error.code === 'ETIMEDOUT' ||
      error.code === 'ECONNREFUSED' ||
      (error.response && error.response.status >= 500)
    );
  }

  private calculateDelay(attempt: number): number {
    let delay: number;

    switch (this.config.strategy) {
      case 'fixed':
        delay = this.config.baseDelay;
        break;

      case 'linear':
        delay = this.config.baseDelay * attempt;
        break;

      case 'exponential':
        delay = this.config.baseDelay * Math.pow(2, attempt - 1);
        break;

      case 'exponential_jitter':
        const exponentialDelay = this.config.baseDelay * Math.pow(2, attempt - 1);
        delay = exponentialDelay + (Math.random() * exponentialDelay * 0.1);
        break;

      default:
        delay = this.config.baseDelay;
    }

    // Apply max delay limit
    return Math.min(delay, this.config.maxDelay);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Retry with Circuit Breaker Integration
class ResilientOperationExecutor {
  private retryPolicy: RetryPolicy;
  private circuitBreaker: AdvancedCircuitBreaker;
  private rateLimiter: RateLimiter;

  constructor(config: ResilientOperationConfig) {
    this.retryPolicy = new RetryPolicy(config.retry);
    this.circuitBreaker = new AdvancedCircuitBreaker(config.circuitBreaker);
    this.rateLimiter = new RateLimiter(config.rateLimit);
  }

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    // Check rate limit
    await this.rateLimiter.checkLimit();

    // Execute with circuit breaker and retry
    return this.retryPolicy.execute(async () => {
      return this.circuitBreaker.execute(operation);
    });
  }
}
```

This comprehensive advanced system integration patterns document provides enterprise-grade solutions for complex distributed system challenges, ensuring reliable, scalable, and maintainable integration between services while maintaining high performance and fault tolerance.

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*
*Approval Required: CTO, Principal Architect, Platform Engineering Lead*