# Development Guide

## Project Structure

```
eventsourcing-saas/
├── src/
│   └── backend/
│       ├── domain/              # Domain layer
│       │   ├── events/          # Domain events
│       │   └── aggregates/      # Aggregate roots
│       ├── application/         # Application layer
│       │   ├── commands/        # Command handlers
│       │   └── queries/         # Query handlers
│       ├── infrastructure/      # Infrastructure layer
│       │   ├── event_store/     # Event persistence
│       │   ├── projections/     # Read model updates
│       │   ├── event_bus/       # Event distribution
│       │   ├── multi_tenancy/   # Tenant isolation
│       │   └── database/        # Database connections
│       └── api/                 # API layer
│           ├── routers/         # API endpoints
│           └── dependencies.py  # FastAPI dependencies
├── database/
│   └── migrations/              # Database migrations
├── kubernetes/                  # K8s manifests
├── tests/                       # Test suite
├── docs/                        # Documentation
└── monitoring/                  # Monitoring configs
```

## Development Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Setup Pre-commit Hooks
```bash
pre-commit install
```

### 3. Run Tests
```bash
pytest tests/ -v --cov=src
```

### 4. Start Development Server
```bash
uvicorn src.backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Adding New Features

### Creating a New Aggregate

1. Define events in `src/backend/domain/events/`:
```python
from ..events.base_event import DomainEvent

class OrderCreatedEvent(DomainEvent):
    order_id: UUID
    customer_id: UUID
    items: List[dict]
```

2. Create aggregate in `src/backend/domain/aggregates/`:
```python
from ..aggregates.base_aggregate import AggregateRoot

class Order(AggregateRoot):
    def __init__(self, order_id: UUID, tenant_id: UUID):
        super().__init__(order_id, tenant_id)
        self.status = None
        self.items = []

    def create(self, customer_id: UUID, items: List[dict]):
        event = OrderCreatedEvent(
            event_type="OrderCreated",
            aggregate_id=self.aggregate_id,
            aggregate_type="Order",
            tenant_id=self.tenant_id,
            version=self.version + 1,
            order_id=self.aggregate_id,
            customer_id=customer_id,
            items=items
        )
        self.apply_event(event)

    def _apply(self, event: DomainEvent):
        if event.event_type == "OrderCreated":
            self.status = "created"
            self.items = event.items
```

### Creating Commands

1. Define command in `src/backend/application/commands/`:
```python
from .base_command import Command

class CreateOrderCommand(Command):
    customer_id: UUID
    items: List[dict]
```

2. Create handler:
```python
from .command_handler import CommandHandler
from .base_command import CommandResult

class CreateOrderCommandHandler(CommandHandler):
    def __init__(self, event_store, event_bus):
        self.event_store = event_store
        self.event_bus = event_bus

    async def handle(self, command: CreateOrderCommand) -> CommandResult:
        # Create aggregate
        order = Order(uuid4(), command.tenant_id)
        order.create(command.customer_id, command.items)

        # Save events
        await self.event_store.save_events(
            aggregate_id=order.aggregate_id,
            events=order.get_uncommitted_events(),
            expected_version=0,
            tenant_id=command.tenant_id
        )

        # Publish events
        await self.event_bus.publish_many(order.get_uncommitted_events())

        return CommandResult(
            success=True,
            aggregate_id=order.aggregate_id,
            message="Order created"
        )
```

### Creating Queries

1. Define query:
```python
from .base_query import Query

class GetOrderByIdQuery(Query):
    order_id: UUID
```

2. Create handler:
```python
from .query_handler import QueryHandler
from .base_query import QueryResult

class GetOrderByIdQueryHandler(QueryHandler):
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def handle(self, query: GetOrderByIdQuery) -> QueryResult:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM read_model_entities WHERE entity_id = $1 AND tenant_id = $2",
                query.order_id,
                query.tenant_id
            )

            if row:
                return QueryResult(
                    success=True,
                    data=row['data']
                )

            return QueryResult(
                success=False,
                message="Order not found"
            )
```

### Creating Projections

1. Create projection class:
```python
from ...infrastructure.projections.projection_manager import Projection

class OrderProjection(Projection):
    def __init__(self, db_pool):
        self.db_pool = db_pool

    def handles(self) -> List[str]:
        return ["OrderCreated", "OrderUpdated"]

    async def project(self, event: DomainEvent):
        async with self.db_pool.acquire() as conn:
            if event.event_type == "OrderCreated":
                await conn.execute(
                    """
                    INSERT INTO read_model_entities (entity_id, tenant_id, entity_type, data, version)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    event.order_id,
                    event.tenant_id,
                    "Order",
                    event.to_dict(),
                    event.version
                )
```

## Testing

### Unit Tests
```python
@pytest.mark.asyncio
async def test_create_order():
    order = Order(uuid4(), uuid4())
    order.create(uuid4(), [{"item": "test"}])

    events = order.get_uncommitted_events()
    assert len(events) == 1
    assert events[0].event_type == "OrderCreated"
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_create_order_integration(event_store, event_bus):
    command = CreateOrderCommand(
        command_id=uuid4(),
        tenant_id=uuid4(),
        customer_id=uuid4(),
        items=[{"item": "test"}]
    )

    handler = CreateOrderCommandHandler(event_store, event_bus)
    result = await handler.handle(command)

    assert result.success is True
    assert result.aggregate_id is not None
```

## Code Style

### Formatting
```bash
black src/ tests/
isort src/ tests/
```

### Linting
```bash
flake8 src/ tests/
pylint src/ tests/
mypy src/
```

## Database Migrations

### Creating Migration
1. Create new SQL file in `database/migrations/`
2. Name with incrementing number: `003_add_feature.sql`
3. Test locally before committing

### Running Migrations
```bash
psql -U postgres -d eventsourcing -f database/migrations/003_add_feature.sql
```

## Performance Optimization

### Event Replay Optimization
- Implement snapshots for large aggregates
- Snapshot every N events (configurable)

### Query Optimization
- Add indexes for common queries
- Use read replicas for heavy read loads
- Implement caching layer (Redis)

### Projection Optimization
- Process events in batches
- Use parallel processing for independent projections
- Track projection lag metrics

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Event Store Inspection
```sql
-- View recent events
SELECT * FROM events ORDER BY position DESC LIMIT 10;

-- View events for aggregate
SELECT * FROM events WHERE aggregate_id = 'uuid' ORDER BY version;

-- Check projection progress
SELECT * FROM projection_checkpoints;
```

## Contributing

1. Create feature branch
2. Write tests
3. Implement feature
4. Run test suite
5. Create pull request
6. Address review comments