# Production Readiness Enhancements - Tri-Modal Mission Control

**Date**: 2025-10-13
**Status**: Critical Production Requirements
**Priority**: High - Must implement before production deployment

---

## Executive Summary

This document addresses critical production readiness gaps identified in the Mission Control architecture. These enhancements are **mandatory** for production deployment and focus on:

1. **Tri-Modal System Hardening**: Schema enforcement, observability, exactly-once semantics
2. **Infrastructure Resilience**: Load testing, backpressure, disaster recovery
3. **Quick Start & Operations**: One-click deployment, golden datasets, troubleshooting

---

## 1. Tri-Modal System Hardening

### 1.1 Schema Registry + Versioning (CRITICAL)

**Problem**: Without schema enforcement, breaking changes can crash the entire pipeline.

**Solution**: Strict Avro schema evolution with compatibility checks.

#### Implementation

**Schema Registry Configuration**:
```yaml
# config/schema-registry.yaml
compatibility:
  level: BACKWARD  # New schemas can read old data

schemas:
  trimodal.events.dde.v1:
    version: 1
    file: schemas/avro/dde_event_v1.avsc
    compatibility: BACKWARD

  trimodal.events.bdv.v1:
    version: 1
    file: schemas/avro/bdv_event_v1.avsc
    compatibility: BACKWARD

  trimodal.events.acc.v1:
    version: 1
    file: schemas/avro/acc_event_v1.avsc
    compatibility: BACKWARD
```

**Schema Evolution Policy**:
```python
# ics/schema_validator.py
from confluent_kafka import avro
from confluent_kafka.schema_registry import SchemaRegistryClient

class SchemaValidator:
    """Enforce schema versioning with compatibility checks."""

    def __init__(self):
        self.registry = SchemaRegistryClient({
            'url': 'http://schema-registry:8081'
        })

    async def validate_event(self, event: dict, topic: str) -> bool:
        """Validate event against latest schema."""
        try:
            # Get latest schema version
            schema = await self.registry.get_latest_version(f"{topic}-value")

            # Validate event structure
            avro.validate(schema, event)

            # Add schema metadata to event
            event['_schema_version'] = schema.version
            event['_schema_id'] = schema.schema_id

            return True

        except avro.AvroException as e:
            # Schema validation failed - send to DLQ
            await self.send_to_dlq(event, error=f"Schema validation failed: {e}")
            return False

    async def check_compatibility(self, new_schema: dict, topic: str) -> bool:
        """Check if new schema is compatible with existing data."""
        try:
            result = await self.registry.test_compatibility(
                subject=f"{topic}-value",
                schema=new_schema
            )
            return result.is_compatible

        except Exception as e:
            logging.error(f"Compatibility check failed: {e}")
            return False
```

**Schema Versioning Example**:
```json
// schemas/avro/dde_event_v1.avsc
{
  "type": "record",
  "name": "DDEEvent",
  "namespace": "com.maestro.trimodal.dde",
  "version": 1,
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "iteration_id", "type": "string"},
    {"name": "node_id", "type": "string"},
    {"name": "event_type", "type": "string"},

    // Version 1 fields
    {"name": "status", "type": "string"},
    {"name": "retry_count", "type": "int", "default": 0}
  ]
}

// schemas/avro/dde_event_v2.avsc (BACKWARD compatible)
{
  "type": "record",
  "name": "DDEEvent",
  "namespace": "com.maestro.trimodal.dde",
  "version": 2,
  "fields": [
    // ... existing fields ...

    // NEW in v2: Optional field with default
    {"name": "resource_usage", "type": ["null", {
      "type": "record",
      "name": "ResourceUsage",
      "fields": [
        {"name": "cpu_percent", "type": "float"},
        {"name": "memory_mb", "type": "int"}
      ]
    }], "default": null}
  ]
}
```

**CI/CD Schema Check**:
```bash
#!/bin/bash
# scripts/validate_schema_evolution.sh

# Check if new schema is compatible
curl -X POST http://schema-registry:8081/compatibility/subjects/trimodal.events.dde-value/versions/latest \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d @schemas/avro/dde_event_v2.avsc

# Exit non-zero if incompatible
if [ $? -ne 0 ]; then
  echo "❌ Schema evolution would break compatibility!"
  exit 1
fi

echo "✅ Schema is backward compatible"
```

---

### 1.2 OpenTelemetry Trace/Span IDs (CRITICAL)

**Problem**: Without distributed tracing, debugging cross-service issues is impossible.

**Solution**: Inject OpenTelemetry context into every event and propagate through all services.

#### Implementation

**Event Producer (DAGExecutor)**:
```python
# dag_executor.py
from opentelemetry import trace
from opentelemetry.propagate import inject

tracer = trace.get_tracer(__name__)

class DAGExecutor:
    async def execute_task(self, task: Task):
        # Start span for this task execution
        with tracer.start_as_current_span(
            "dde.task.execute",
            kind=trace.SpanKind.INTERNAL,
            attributes={
                "task.id": task.id,
                "task.type": task.type,
                "iteration.id": self.iteration_id
            }
        ) as span:
            # Get current trace context
            ctx = {}
            inject(ctx)  # Injects traceparent, tracestate headers

            # Emit Kafka event with trace context
            event = {
                "event_id": str(uuid.uuid7()),
                "timestamp": int(time.time() * 1000),
                "iteration_id": self.iteration_id,
                "node_id": task.id,
                "event_type": "dde.task.started",

                # OpenTelemetry context
                "trace_id": format(span.get_span_context().trace_id, '032x'),
                "span_id": format(span.get_span_context().span_id, '016x'),
                "trace_flags": span.get_span_context().trace_flags,

                # W3C Trace Context (for HTTP propagation)
                "traceparent": ctx.get("traceparent"),
                "tracestate": ctx.get("tracestate"),

                "metadata": {
                    "capability": task.capability,
                    "estimated_effort": task.estimated_effort
                }
            }

            await self.kafka_producer.send("trimodal.events.dde", event)

            # Execute task
            try:
                result = await self._execute_task_impl(task)
                span.set_status(trace.Status(trace.StatusCode.OK))

                # Emit completion event
                await self._emit_event("dde.task.completed", task, result)

            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)

                # Emit failure event
                await self._emit_event("dde.task.failed", task, error=e)
                raise
```

**Event Consumer (ICS)**:
```python
# ics/event_processor.py
from opentelemetry import trace
from opentelemetry.propagate import extract

tracer = trace.get_tracer(__name__)

class EventProcessor:
    async def process_event(self, event: dict):
        # Extract trace context from event
        ctx = {
            "traceparent": event.get("traceparent"),
            "tracestate": event.get("tracestate")
        }
        parent_ctx = extract(ctx)

        # Continue the trace with a new span
        with tracer.start_as_current_span(
            "ics.event.process",
            context=parent_ctx,  # Links to original trace
            kind=trace.SpanKind.CONSUMER,
            attributes={
                "event.type": event["event_type"],
                "event.id": event["event_id"],
                "iteration.id": event["iteration_id"]
            }
        ) as span:
            try:
                # Validate schema
                if not await self.validate_schema(event):
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Schema validation failed"))
                    return

                # Check idempotency
                if await self.is_duplicate(event["idempotency_key"]):
                    span.set_attribute("duplicate", True)
                    return

                # Correlate and update UGM
                await self.correlate_and_update_ugm(event)

                # Update CQRS projections
                await self.update_projections(event)

                span.set_status(trace.Status(trace.StatusCode.OK))

            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)

                # Send to DLQ
                await self.send_to_dlq(event, error=e)
```

**GraphQL Resolver with Tracing**:
```python
# graphql/resolvers.py
from opentelemetry.instrumentation.graphql import GraphQLInstrumentor

# Auto-instrument GraphQL
GraphQLInstrumentor().instrument()

class QueryResolvers:
    async def get_dde_graph(self, info, iteration_id: str):
        # Trace is automatically created by instrumentation
        span = trace.get_current_span()
        span.set_attribute("iteration.id", iteration_id)

        # Query Neo4j
        graph = await self.ugm.get_dde_graph(iteration_id)

        span.set_attribute("graph.node_count", len(graph.nodes))

        return graph
```

**Jaeger UI Query**:
```
# Find all events for a specific iteration
trace.iteration.id="Iter-20251013-001"

# Find slow operations
duration:>5s

# Find errors
error=true
```

---

### 1.3 Idempotency + Exactly-Once + DLQ/Replay (CRITICAL)

**Problem**: Network failures, retries, and replays can cause duplicate processing and data corruption.

**Solution**: Idempotency keys + transactional Kafka + DLQ with replay.

#### Implementation

**Idempotency Key Generation**:
```python
# common/idempotency.py
import hashlib

def generate_idempotency_key(event: dict) -> str:
    """Generate deterministic idempotency key from event content."""
    # Combine fields that uniquely identify this event
    unique_fields = f"{event['iteration_id']}:{event['node_id']}:{event['event_type']}:{event['timestamp']}"

    # Hash to fixed length
    return hashlib.sha256(unique_fields.encode()).hexdigest()[:32]
```

**Transactional Kafka Producer**:
```python
# common/kafka_producer.py
from confluent_kafka import Producer

class TransactionalKafkaProducer:
    """Kafka producer with exactly-once semantics."""

    def __init__(self):
        self.producer = Producer({
            'bootstrap.servers': 'kafka:9092',
            'transactional.id': f'dde-executor-{socket.gethostname()}',
            'enable.idempotence': True,
            'acks': 'all',
            'max.in.flight.requests.per.connection': 1
        })

        # Initialize transactions
        self.producer.init_transactions()

    async def send_event(self, topic: str, event: dict):
        """Send event with exactly-once guarantee."""
        try:
            # Start transaction
            self.producer.begin_transaction()

            # Generate idempotency key
            event['idempotency_key'] = generate_idempotency_key(event)

            # Send to Kafka
            self.producer.produce(
                topic=topic,
                value=json.dumps(event).encode('utf-8'),
                key=event['idempotency_key'].encode('utf-8')
            )

            # Commit transaction
            self.producer.commit_transaction()

        except Exception as e:
            # Abort transaction on error
            self.producer.abort_transaction()
            raise
```

**Idempotent Event Consumer**:
```python
# ics/idempotent_consumer.py
from redis import Redis
from datetime import timedelta

class IdempotentEventConsumer:
    """Consumer with idempotency checking."""

    def __init__(self):
        self.redis = Redis(host='redis', port=6379, db=0)
        self.ttl = timedelta(days=7)  # Keep keys for 7 days

    async def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if event was already processed."""
        key = f"processed:{idempotency_key}"

        # Check Redis
        exists = self.redis.exists(key)

        if exists:
            # Already processed
            return True

        # Mark as processing (with TTL)
        self.redis.setex(
            key,
            self.ttl,
            json.dumps({
                "processed_at": datetime.now().isoformat(),
                "processor": socket.gethostname()
            })
        )

        return False

    async def mark_processed(self, idempotency_key: str, result: dict):
        """Mark event as successfully processed."""
        key = f"processed:{idempotency_key}"

        # Update with result
        self.redis.setex(
            key,
            self.ttl,
            json.dumps({
                "processed_at": datetime.now().isoformat(),
                "processor": socket.gethostname(),
                "result": result
            })
        )
```

**Dead Letter Queue (DLQ)**:
```python
# ics/dlq_handler.py
class DLQHandler:
    """Handle failed events with categorization and replay."""

    async def send_to_dlq(self, event: dict, error: Exception):
        """Send failed event to DLQ with error context."""
        dlq_event = {
            "original_event": event,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "stack_trace": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            },
            "failure_category": self._categorize_failure(error),
            "retry_count": event.get("retry_count", 0) + 1,
            "can_retry": self._is_retryable(error)
        }

        # Send to DLQ topic
        await self.kafka_producer.send(
            topic="trimodal.events.dlq",
            value=dlq_event
        )

        # Alert if critical
        if dlq_event["failure_category"] == "CRITICAL":
            await self.alert_ops(dlq_event)

    def _categorize_failure(self, error: Exception) -> str:
        """Categorize failure for routing."""
        if isinstance(error, SchemaValidationError):
            return "SCHEMA_VALIDATION"
        elif isinstance(error, CorrelationError):
            return "CORRELATION_FAILED"
        elif isinstance(error, DatabaseError):
            return "DATABASE_ERROR"
        elif isinstance(error, TransientNetworkError):
            return "TRANSIENT_NETWORK"
        else:
            return "CRITICAL"

    def _is_retryable(self, error: Exception) -> bool:
        """Determine if failure can be retried."""
        # Schema errors are not retryable (need fix)
        if isinstance(error, SchemaValidationError):
            return False

        # Transient errors are retryable
        if isinstance(error, (TransientNetworkError, TemporaryDatabaseError)):
            return True

        return False
```

**DLQ Replay Mechanism**:
```python
# scripts/replay_dlq.py
class DLQReplayer:
    """Replay failed events from DLQ after fixes."""

    async def replay_events(
        self,
        category: str = None,
        from_timestamp: datetime = None,
        to_timestamp: datetime = None,
        dry_run: bool = True
    ):
        """Replay events from DLQ matching criteria."""
        # Query DLQ events
        events = await self._query_dlq(category, from_timestamp, to_timestamp)

        print(f"Found {len(events)} events to replay")

        replayed = 0
        failed = 0

        for event in events:
            # Check if retryable
            if not event["can_retry"]:
                print(f"Skipping non-retryable event: {event['original_event']['event_id']}")
                continue

            # Replay
            if not dry_run:
                try:
                    # Send back to original topic
                    original_topic = self._get_original_topic(event["original_event"])
                    await self.kafka_producer.send(original_topic, event["original_event"])
                    replayed += 1

                    # Remove from DLQ
                    await self._remove_from_dlq(event)

                except Exception as e:
                    print(f"Failed to replay {event['original_event']['event_id']}: {e}")
                    failed += 1

        print(f"Replayed: {replayed}, Failed: {failed}")

        return {"replayed": replayed, "failed": failed}

# Usage:
replayer = DLQReplayer()

# Dry run (check what would be replayed)
await replayer.replay_events(
    category="TRANSIENT_NETWORK",
    from_timestamp=datetime(2025, 10, 13, 10, 0),
    to_timestamp=datetime(2025, 10, 13, 11, 0),
    dry_run=True
)

# Actually replay
await replayer.replay_events(
    category="TRANSIENT_NETWORK",
    dry_run=False
)
```

---

### 1.4 ICS Provenance + Confidence Scoring

**Problem**: Correlation logic has uncertainty - some links are inferred, not explicit.

**Solution**: Track provenance and confidence for every correlation.

#### Implementation

```python
# ics/correlator.py
from enum import Enum

class CorrelationMethod(Enum):
    """How correlation was established."""
    EXPLICIT_ID = "explicit_id"              # requirement_id in event
    FILE_PATH_EXACT = "file_path_exact"      # Exact file path match
    FILE_PATH_FUZZY = "file_path_fuzzy"      # Similar file path
    CONTRACT_TAG = "contract_tag"            # @contract tag match
    HEURISTIC = "heuristic"                  # ML or rule-based
    MANUAL = "manual"                        # Human override

class CorrelationEngine:
    """Correlate events with provenance tracking."""

    async def correlate_task_to_requirement(self, task_event: dict):
        """Link Task → Requirement with confidence scoring."""

        # Explicit requirement_id (100% confidence)
        if task_event.get("requirement_id"):
            confidence = 1.0
            method = CorrelationMethod.EXPLICIT_ID
            explainability = "Event contains explicit requirement_id field"

            await self._create_link(
                source=("Task", task_event["node_id"]),
                target=("Requirement", task_event["requirement_id"]),
                rel_type="FULFILLED_BY",
                confidence=confidence,
                method=method,
                explainability=explainability
            )
            return

        # Fallback: Heuristic matching (lower confidence)
        # Match by task name similarity to requirement text
        requirements = await self.ugm.query(
            "MATCH (r:Requirement) WHERE r.iteration_id = $iteration_id RETURN r",
            iteration_id=task_event["iteration_id"]
        )

        task_name = task_event["metadata"].get("name", "")

        best_match = None
        best_score = 0.0

        for req in requirements:
            # Simple text similarity (Jaccard)
            similarity = self._calculate_similarity(task_name, req["name"])
            if similarity > best_score:
                best_score = similarity
                best_match = req

        if best_match and best_score > 0.5:  # Threshold
            confidence = best_score  # 0.5 to 1.0
            method = CorrelationMethod.HEURISTIC
            explainability = f"Matched by name similarity: {best_score:.2f}"

            await self._create_link(
                source=("Task", task_event["node_id"]),
                target=("Requirement", best_match["id"]),
                rel_type="FULFILLED_BY",
                confidence=confidence,
                method=method,
                explainability=explainability
            )
        else:
            # No match - log for manual review
            await self._log_unmatched_event(task_event, "No matching requirement found")

    async def _create_link(
        self,
        source: tuple,
        target: tuple,
        rel_type: str,
        confidence: float,
        method: CorrelationMethod,
        explainability: str
    ):
        """Create relationship with provenance metadata."""
        await self.ugm.create_relationship(
            source_type=source[0],
            source_id=source[1],
            target_type=target[0],
            target_id=target[1],
            rel_type=rel_type,
            properties={
                "confidence": confidence,
                "correlation_method": method.value,
                "explainability": explainability,
                "created_at": datetime.now().isoformat(),
                "created_by": "ICS",

                # Provenance chain
                "source_event_id": self.current_event["event_id"],
                "source_trace_id": self.current_event["trace_id"]
            }
        )
```

**Confidence Visualization in UI**:
```typescript
// frontend/src/components/edges/ConfidenceEdge.tsx
export const ConfidenceEdge: React.FC<{ edge: Edge }> = ({ edge }) => {
  const confidence = edge.data.confidence;

  // Color gradient based on confidence
  const getColor = (conf: number) => {
    if (conf >= 0.9) return '#22c55e';  // Green - high confidence
    if (conf >= 0.7) return '#eab308';  // Yellow - medium confidence
    return '#ef4444';                    // Red - low confidence
  };

  // Line style based on correlation method
  const getStyle = (method: string) => {
    if (method === 'explicit_id') return 'solid';
    if (method === 'contract_tag') return 'solid';
    return 'dashed';  // Heuristic/inferred
  };

  return (
    <Edge
      {...edge}
      style={{
        stroke: getColor(confidence),
        strokeWidth: 2,
        strokeDasharray: getStyle(edge.data.correlation_method) === 'dashed' ? '5,5' : '0'
      }}
      label={`${(confidence * 100).toFixed0}%`}
      title={edge.data.explainability}
    />
  );
};
```

---

### 1.5 Bi-Temporal UGM for Time-Travel

**Problem**: Single timestamp doesn't support "what was known at time X" queries.

**Solution**: Bi-temporal model with valid_from/to and observed_at.

#### Implementation

**Neo4j Schema**:
```cypher
// Create bi-temporal node
CREATE (t:Task {
  id: "T-123",
  iteration_id: "Iter-001",

  // Current state
  status: "completed",
  retry_count: 2,

  // Bi-temporal tracking
  valid_from: datetime('2025-10-13T10:00:00Z'),  // When this state became true
  valid_to: datetime('2025-10-13T10:05:00Z'),    // When it stopped being true
  observed_at: datetime('2025-10-13T10:00:05Z'), // When system learned about it

  // Version tracking
  version: 3  // This is version 3 of this node
})

// Current version (valid_to is null)
CREATE (t_current:Task {
  id: "T-123",
  iteration_id: "Iter-001",
  status: "failed",
  retry_count: 3,
  valid_from: datetime('2025-10-13T10:05:00Z'),
  valid_to: null,  // Current version
  observed_at: datetime('2025-10-13T10:05:02Z'),
  version: 4
})
```

**Time-Travel Queries**:
```python
# ugm/temporal_queries.py
class TemporalUGM:
    """Time-travel queries on bi-temporal graph."""

    async def get_graph_at_time(self, iteration_id: str, as_of: datetime):
        """Get graph state as it was at specific time (valid_from perspective)."""
        query = """
        MATCH (n)
        WHERE n.iteration_id = $iteration_id
          AND n.valid_from <= $as_of
          AND (n.valid_to IS NULL OR n.valid_to > $as_of)
        RETURN n
        """

        nodes = await self.neo4j.run(query, iteration_id=iteration_id, as_of=as_of)
        return nodes

    async def get_graph_as_observed_at(self, iteration_id: str, observed_at: datetime):
        """Get graph state as it was known at specific time (observed_at perspective)."""
        query = """
        MATCH (n)
        WHERE n.iteration_id = $iteration_id
          AND n.observed_at <= $observed_at
        WITH n.id AS node_id, n
        ORDER BY n.observed_at DESC
        WITH node_id, COLLECT(n)[0] AS latest_node
        RETURN latest_node
        """

        nodes = await self.neo4j.run(query, iteration_id=iteration_id, observed_at=observed_at)
        return nodes

    async def get_node_history(self, node_id: str):
        """Get all historical versions of a node."""
        query = """
        MATCH (n {id: $node_id})
        RETURN n
        ORDER BY n.version ASC
        """

        versions = await self.neo4j.run(query, node_id=node_id)
        return versions

    async def get_changes_between(
        self,
        iteration_id: str,
        from_time: datetime,
        to_time: datetime
    ):
        """Get all changes that occurred in time window."""
        query = """
        MATCH (n)
        WHERE n.iteration_id = $iteration_id
          AND n.valid_from >= $from_time
          AND n.valid_from < $to_time
        RETURN n, n.valid_from AS change_time
        ORDER BY change_time ASC
        """

        changes = await self.neo4j.run(
            query,
            iteration_id=iteration_id,
            from_time=from_time,
            to_time=to_time
        )
        return changes
```

**GraphQL Integration**:
```graphql
type Query {
  # Time-travel queries
  getDDEGraph(iterationId: ID!, asOf: DateTime): DDEGraph
  getDDEGraphAsObserved(iterationId: ID!, observedAt: DateTime): DDEGraph

  # Node history
  getTaskHistory(taskId: ID!): [TaskVersion!]!

  # Change detection
  getChanges(iterationId: ID!, from: DateTime!, to: DateTime!): [Change!]!
}

type TaskVersion {
  id: ID!
  status: NodeStatus!
  retryCount: Int!
  validFrom: DateTime!
  validTo: DateTime
  observedAt: DateTime!
  version: Int!
}

type Change {
  nodeId: ID!
  nodeType: String!
  changeType: ChangeType!  # CREATED, UPDATED, DELETED
  timestamp: DateTime!
  previousState: JSON
  newState: JSON
}
```

---

### 1.6 RBAC + PII + Retention Policies

**Problem**: Multi-tenant system needs strict access control and compliance.

**Solution**: Row-level security, PII tagging, automated retention.

#### Implementation

**RBAC Model**:
```python
# auth/rbac.py
from enum import Enum

class Role(Enum):
    ADMIN = "admin"              # Full access
    ENGINEER = "engineer"        # Read/write iterations
    VIEWER = "viewer"            # Read-only
    AUDITOR = "auditor"          # Read-only + audit logs

class Permission(Enum):
    READ_ITERATION = "iteration:read"
    WRITE_ITERATION = "iteration:write"
    DELETE_ITERATION = "iteration:delete"
    READ_AUDIT_LOG = "audit:read"
    MANAGE_USERS = "users:manage"

ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.READ_ITERATION,
        Permission.WRITE_ITERATION,
        Permission.DELETE_ITERATION,
        Permission.READ_AUDIT_LOG,
        Permission.MANAGE_USERS
    ],
    Role.ENGINEER: [
        Permission.READ_ITERATION,
        Permission.WRITE_ITERATION
    ],
    Role.VIEWER: [
        Permission.READ_ITERATION
    ],
    Role.AUDITOR: [
        Permission.READ_ITERATION,
        Permission.READ_AUDIT_LOG
    ]
}

class RBACMiddleware:
    """GraphQL RBAC middleware."""

    async def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has permission."""
        user_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in user_permissions

    async def filter_by_tenant(self, user: User, query_results: list) -> list:
        """Filter results to user's tenant."""
        if user.role == Role.ADMIN:
            return query_results  # Admins see all

        # Filter to user's tenant
        return [r for r in query_results if r.tenant_id == user.tenant_id]
```

**PII Tagging**:
```python
# common/pii_handler.py
from typing import Set

class PIITagger:
    """Tag events with PII for compliance."""

    PII_FIELDS = {
        "email", "phone", "ssn", "name", "address",
        "credit_card", "ip_address", "user_id"
    }

    def detect_pii(self, event: dict) -> Set[str]:
        """Detect PII fields in event."""
        pii_tags = set()

        # Check all fields
        for key, value in self._flatten_dict(event).items():
            # Check field name
            if any(pii_field in key.lower() for pii_field in self.PII_FIELDS):
                pii_tags.add(key)

            # Check value patterns (email, phone, SSN regex)
            if self._is_email(value):
                pii_tags.add(f"{key}:email")
            elif self._is_phone(value):
                pii_tags.add(f"{key}:phone")

        return pii_tags

    def anonymize(self, event: dict, pii_tags: Set[str]):
        """Anonymize PII fields for logging."""
        anonymized = event.copy()

        for tag in pii_tags:
            field = tag.split(":")[0]
            # Replace with hash
            if field in anonymized:
                anonymized[field] = hashlib.sha256(str(anonymized[field]).encode()).hexdigest()[:16]

        return anonymized
```

**Retention Policies**:
```python
# compliance/retention.py
from datetime import timedelta

class RetentionPolicy(Enum):
    STANDARD = timedelta(days=90)     # 90 days
    AUDIT = timedelta(days=2555)      # 7 years
    COMPLIANCE = timedelta(days=365)  # 1 year
    TEMP = timedelta(days=7)          # 7 days

class RetentionManager:
    """Automated data retention and deletion."""

    async def apply_retention_policies(self):
        """Delete expired data based on retention policies."""
        now = datetime.now()

        # Query events past retention
        query = """
        MATCH (n)
        WHERE n.retention_policy IS NOT NULL
          AND n.created_at + duration(n.retention_policy) < $now
        DELETE n
        RETURN COUNT(n) AS deleted_count
        """

        result = await self.neo4j.run(query, now=now)

        print(f"Deleted {result['deleted_count']} expired nodes")

    async def archive_to_cold_storage(self, age_days: int = 30):
        """Move old data to cold storage (S3 Glacier)."""
        cutoff = datetime.now() - timedelta(days=age_days)

        # Query old iterations
        old_iterations = await self.ugm.query(
            """
            MATCH (i:Iteration)
            WHERE i.created_at < $cutoff
            RETURN i
            """,
            cutoff=cutoff
        )

        for iteration in old_iterations:
            # Export to JSON
            graph_snapshot = await self.export_iteration(iteration["id"])

            # Upload to S3 Glacier
            await self.s3.upload(
                bucket="trimodal-archive",
                key=f"iterations/{iteration['id']}.json.gz",
                body=gzip.compress(json.dumps(graph_snapshot).encode()),
                storage_class="GLACIER"
            )

            # Mark as archived (don't delete yet)
            await self.ugm.update_node(
                iteration["id"],
                {"archived": True, "archive_location": f"s3://trimodal-archive/iterations/{iteration['id']}.json.gz"}
            )
```

---

### 1.7 SLOs from Ingest → UI

**Problem**: No end-to-end latency tracking from event emission to UI update.

**Solution**: Distributed tracing with critical path SLIs.

#### Implementation

**SLI Definitions**:
```python
# observability/slis.py
from prometheus_client import Histogram, Counter, Gauge

# End-to-end latency: Event emitted → UI receives update
e2e_latency = Histogram(
    'trimodal_e2e_latency_seconds',
    'End-to-end latency from event emission to UI update',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Per-stage latency
kafka_publish_latency = Histogram(
    'trimodal_kafka_publish_seconds',
    'Time to publish event to Kafka',
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5]
)

ics_processing_latency = Histogram(
    'trimodal_ics_processing_seconds',
    'ICS event processing time',
    buckets=[0.01, 0.1, 0.5, 1.0, 5.0]
)

ugm_write_latency = Histogram(
    'trimodal_ugm_write_seconds',
    'Neo4j write latency',
    buckets=[0.01, 0.1, 0.5, 1.0, 5.0]
)

graphql_query_latency = Histogram(
    'trimodal_graphql_query_seconds',
    'GraphQL query latency',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

subscription_push_latency = Histogram(
    'trimodal_subscription_push_seconds',
    'WebSocket subscription push latency',
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5]
)

# Error rates
event_processing_errors = Counter(
    'trimodal_event_processing_errors_total',
    'Event processing errors',
    ['stage', 'error_type']
)
```

**Instrumentation**:
```python
# dag_executor.py
@e2e_latency.time()
async def execute_task(self, task: Task):
    # Emit start event
    with kafka_publish_latency.time():
        await self.emit_event("dde.task.started", task)

    # Execute
    # ...
```

**SLO Definitions**:
```yaml
# config/slos.yaml
slos:
  - name: end_to_end_latency
    description: "Event emission to UI update"
    target: 0.95  # 95% of requests
    threshold: 5.0  # Within 5 seconds
    window: 30d

  - name: ics_processing_latency
    description: "ICS event processing"
    target: 0.99  # 99% of events
    threshold: 1.0  # Within 1 second
    window: 7d

  - name: graphql_availability
    description: "GraphQL API uptime"
    target: 0.999  # 99.9% uptime
    window: 30d
```

**Grafana Dashboard**:
```json
{
  "dashboard": {
    "title": "Tri-Modal SLO Dashboard",
    "panels": [
      {
        "title": "End-to-End Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(trimodal_e2e_latency_seconds_bucket[5m]))"
          }
        ],
        "thresholds": [
          {"value": 5.0, "color": "red"}
        ]
      },
      {
        "title": "SLO Burn Rate",
        "targets": [
          {
            "expr": "rate(trimodal_e2e_latency_seconds_count{le=\"5.0\"}[1h]) / rate(trimodal_e2e_latency_seconds_count[1h])"
          }
        ]
      }
    ]
  }
}
```

---

## 2. Infrastructure Resilience

### 2.1 Load Testing & Benchmarks

**Critical Scenarios**:

1. **Event Fanout**: 1 iteration creates 100 tasks → 100 events
2. **Graph Size**: Render 1000-node DDE workflow
3. **Concurrent Users**: 1000 users viewing same iteration
4. **Subscription Storm**: 100 subscriptions × 10 events/sec
5. **DLQ Replay**: Replay 10K events

**Load Test Suite**:
```python
# tests/load/test_event_fanout.py
import asyncio
from locust import User, task, between

class TriModalUser(User):
    wait_time = between(1, 3)

    @task(weight=10)
    async def view_dde_graph(self):
        """Simulate viewing DDE graph."""
        response = await self.client.post(
            "/graphql",
            json={
                "query": """
                query GetDDEGraph($iterationId: ID!) {
                  getDDEGraph(iterationId: $iterationId) {
                    nodes { id status }
                    edges { source target }
                  }
                }
                """,
                "variables": {"iterationId": "Iter-001"}
            }
        )

        # Assert latency SLO
        assert response.elapsed.total_seconds() < 1.0, "GraphQL query exceeded 1s SLO"

    @task(weight=5)
    async def subscribe_to_updates(self):
        """Simulate WebSocket subscription."""
        async with self.client.ws_connect("/graphql") as ws:
            # Send subscription
            await ws.send_json({
                "type": "subscribe",
                "payload": {
                    "query": """
                    subscription NodeUpdates($iterationId: ID!) {
                      nodeStatusUpdated(iterationId: $iterationId) {
                        nodeId
                        status
                      }
                    }
                    """,
                    "variables": {"iterationId": "Iter-001"}
                }
            })

            # Receive updates for 30 seconds
            start = time.time()
            while time.time() - start < 30:
                message = await ws.receive_json()
                # Assert latency
                assert message["timestamp"] - time.time() < 0.5, "Subscription latency exceeded 500ms"

# Run load test
# locust -f tests/load/test_event_fanout.py --users 1000 --spawn-rate 10
```

**Benchmark Results Matrix**:
```
| Scenario                  | Target       | Current | Status |
|---------------------------|--------------|---------|--------|
| Event throughput          | 10K/sec      | TBD     | ⏳     |
| ICS processing latency    | <1s (P99)    | TBD     | ⏳     |
| GraphQL query (100 nodes) | <100ms (P95) | TBD     | ⏳     |
| GraphQL query (1000 nodes)| <500ms (P95) | TBD     | ⏳     |
| Subscription push         | <500ms (P99) | TBD     | ⏳     |
| Concurrent users          | 1000         | TBD     | ⏳     |
| Memory per user           | <50MB        | TBD     | ⏳     |
```

---

### 2.2 Backpressure Paths

**Problem**: Downstream slowness can cause cascading failures.

**Solution**: Backpressure at every layer with circuit breakers.

```python
# ics/backpressure.py
from asyncio import Semaphore, Queue

class BackpressureManager:
    """Manage backpressure across pipeline."""

    def __init__(self):
        # Limit concurrent ICS processing
        self.ics_semaphore = Semaphore(100)  # Max 100 concurrent

        # Buffer for Neo4j writes
        self.neo4j_write_queue = Queue(maxsize=1000)

        # Circuit breaker for Neo4j
        self.neo4j_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )

    async def process_with_backpressure(self, event: dict):
        """Process event with backpressure control."""
        # Acquire semaphore (blocks if at limit)
        async with self.ics_semaphore:
            # Check circuit breaker
            if self.neo4j_circuit_breaker.is_open():
                # Circuit open - send to DLQ
                await self.send_to_dlq(event, error="Neo4j circuit breaker open")
                return

            try:
                # Process event
                await self._correlate(event)

                # Queue Neo4j write (non-blocking)
                try:
                    self.neo4j_write_queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Queue full - apply backpressure to Kafka
                    await self.kafka_consumer.pause()
                    logging.warning("Neo4j write queue full - pausing Kafka consumer")

                    # Wait for queue to drain
                    await asyncio.sleep(1)
                    await self.kafka_consumer.resume()

            except Neo4jError as e:
                # Record failure
                self.neo4j_circuit_breaker.record_failure()
                raise

class CircuitBreaker:
    """Circuit breaker pattern."""

    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logging.error(f"Circuit breaker OPEN after {self.failure_count} failures")

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == "CLOSED":
            return False

        if self.state == "OPEN":
            # Check if recovery timeout elapsed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logging.info("Circuit breaker entering HALF_OPEN state")
                return False
            return True

        # HALF_OPEN: Allow one request through
        return False

    def record_success(self):
        """Record a success (reset failure count)."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logging.info("Circuit breaker CLOSED")

        self.failure_count = 0
```

---

### 2.3 Disaster Recovery

**Scenario**: Complete Neo4j failure - rebuild from Kafka log.

```python
# scripts/rebuild_from_kafka.py
class DisasterRecovery:
    """Rebuild UGM from Kafka event log."""

    async def rebuild_ugm(self, from_timestamp: datetime):
        """Replay all events since timestamp."""
        print(f"Starting UGM rebuild from {from_timestamp}")

        # Reset Neo4j (dangerous!)
        await self._confirm_reset()
        await self.neo4j.run("MATCH (n) DETACH DELETE n")

        # Replay all topics
        topics = ["trimodal.events.dde", "trimodal.events.bdv", "trimodal.events.acc"]

        for topic in topics:
            print(f"Replaying topic: {topic}")

            # Seek to timestamp
            consumer = self.create_consumer(topic)
            consumer.seek_to_timestamp(from_timestamp)

            # Replay events
            events_replayed = 0

            while True:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    break

                event = json.loads(msg.value())

                # Process event (skip duplicates via idempotency check)
                await self.ics.process_event(event)

                events_replayed += 1

                if events_replayed % 1000 == 0:
                    print(f"Replayed {events_replayed} events from {topic}")

            print(f"Finished replaying {topic}: {events_replayed} events")

        print("UGM rebuild complete")

        # Verify
        await self._verify_rebuild()
```

---

## 3. Quick Start & Operations

### 3.1 One-Click Docker Compose

**Goal**: `docker-compose up` and system is ready with golden dataset.

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Kafka
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  # Schema Registry
  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    environment:
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
    depends_on:
      - kafka

  # Neo4j
  neo4j:
    image: neo4j:5.13.0
    environment:
      NEO4J_AUTH: neo4j/maestro_dev
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
    volumes:
      - neo4j-data:/data
      - ./scripts/neo4j-init.cypher:/docker-entrypoint-initdb.d/init.cypher

  # Redis
  redis:
    image: redis:7.2-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

  # Elasticsearch
  elasticsearch:
    image: elasticsearch:8.10.0
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
    volumes:
      - es-data:/usr/share/elasticsearch/data

  # ICS
  ics:
    build: ./ics
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      NEO4J_URI: bolt://neo4j:7687
      REDIS_HOST: redis
    depends_on:
      - kafka
      - neo4j
      - redis

  # GraphQL API
  graphql:
    build: ./graphql
    ports:
      - "8000:8000"
    environment:
      NEO4J_URI: bolt://neo4j:7687
      REDIS_HOST: redis
    depends_on:
      - neo4j
      - redis

  # Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_GRAPHQL_URL: http://localhost:8000/graphql
      REACT_APP_WS_URL: ws://localhost:8000/graphql

  # Seed data
  seed:
    build: ./seed
    command: python seed_golden_dataset.py
    depends_on:
      - kafka
      - neo4j
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092

volumes:
  neo4j-data:
  redis-data:
  es-data:
```

**Golden Dataset Seeder**:
```python
# seed/seed_golden_dataset.py
class GoldenDatasetSeeder:
    """Seed system with golden dataset for demos and testing."""

    GOLDEN_ITERATIONS = [
        {
            "id": "Iter-Golden-AllPass",
            "description": "All three streams passing - deployable",
            "tasks": 50,
            "scenarios": 100,
            "modules": 80,
            "dde_status": "all_passed",
            "bdv_status": "95_percent_pass",
            "acc_status": "zero_violations"
        },
        {
            "id": "Iter-Golden-DesignGap",
            "description": "DDE + ACC pass, BDV fails - design gap",
            "tasks": 50,
            "scenarios": 100,
            "modules": 80,
            "dde_status": "all_passed",
            "bdv_status": "60_percent_pass",  # Below threshold
            "acc_status": "zero_violations"
        },
        # ... more scenarios
    ]

    async def seed(self):
        """Seed all golden datasets."""
        for iteration_spec in self.GOLDEN_ITERATIONS:
            print(f"Seeding: {iteration_spec['id']}")

            # Generate events
            events = await self.generate_iteration_events(iteration_spec)

            # Publish to Kafka
            for event in events:
                await self.kafka_producer.send(
                    topic=f"trimodal.events.{event['model_type'].lower()}",
                    value=event
                )

            print(f"Seeded {len(events)} events for {iteration_spec['id']}")

        # Wait for ICS to process
        await asyncio.sleep(10)

        # Verify
        await self.verify_golden_datasets()

# Run seeder
seeder = GoldenDatasetSeeder()
asyncio.run(seeder.seed())
```

**Quick Start Script**:
```bash
#!/bin/bash
# scripts/quick_start.sh

echo "🚀 Starting Tri-Modal Mission Control..."

# Check dependencies
command -v docker-compose >/dev/null 2>&1 || {
  echo "❌ docker-compose not installed"
  exit 1
}

# Start services
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."

# Check Kafka
until docker-compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list >/dev/null 2>&1; do
  echo "  Waiting for Kafka..."
  sleep 2
done
echo "✅ Kafka ready"

# Check Neo4j
until docker-compose exec neo4j cypher-shell -u neo4j -p maestro_dev "RETURN 1" >/dev/null 2>&1; do
  echo "  Waiting for Neo4j..."
  sleep 2
done
echo "✅ Neo4j ready"

# Seed golden dataset
echo "📊 Seeding golden dataset..."
docker-compose run --rm seed
echo "✅ Golden dataset seeded"

# Run golden-run assertions
echo "🧪 Running golden-run assertions..."
docker-compose run --rm -e ITERATION_ID=Iter-Golden-AllPass test python -m pytest tests/golden/ -v
echo "✅ Golden-run assertions passed"

# Open browser
echo ""
echo "🎉 Mission Control is ready!"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  GraphQL:   http://localhost:8000/graphql"
echo "  Neo4j:     http://localhost:7474"
echo "  Grafana:   http://localhost:3001"
echo ""
echo "Golden iterations:"
echo "  - Iter-Golden-AllPass     (All passing - deployable)"
echo "  - Iter-Golden-DesignGap   (Design gap scenario)"
echo "  - Iter-Golden-TechDebt    (Architectural erosion)"
echo ""
```

---

### 3.2 Troubleshooting Matrix

**Symptom → Layer → Solution**:

```markdown
| Symptom                        | Layer      | Root Cause                | Solution                              |
|--------------------------------|------------|---------------------------|---------------------------------------|
| Events not appearing in UI     | GraphQL    | Subscription not working  | Check WebSocket connection            |
| Events not in Neo4j            | ICS        | Processing failure        | Check ICS logs, DLQ topic             |
| Slow graph rendering           | Frontend   | Too many nodes            | Enable clustering, virtualization     |
| High latency                   | Neo4j      | Missing indexes           | Add indexes on iteration_id, node_id  |
| WebSocket disconnects          | GraphQL    | Timeout                   | Increase timeout, check backpressure  |
| Kafka consumer lag             | ICS        | Processing too slow       | Scale ICS replicas                    |
| Memory leak                    | Frontend   | Subscription not cleaned  | Add cleanup in useEffect              |
| Circuit breaker open           | ICS        | Downstream failure        | Check Neo4j, Redis connectivity       |
```

**Diagnostic Commands**:
```bash
# Check Kafka consumer lag
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9092 \
  --group ics-processor \
  --describe

# Check DLQ
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9092 \
  --topic trimodal.events.dlq \
  --from-beginning

# Check Neo4j query performance
docker-compose exec neo4j cypher-shell -u neo4j -p maestro_dev \
  "CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Transactions') YIELD attributes RETURN attributes"

# Check ICS health
curl http://localhost:8001/health

# Replay events from timestamp
docker-compose run --rm ics python scripts/replay_from_timestamp.py \
  --from "2025-10-13T10:00:00Z" \
  --to "2025-10-13T11:00:00Z"
```

---

### 3.3 Per-Lens KPIs and Exit Criteria

**DDE Lens KPIs**:
```yaml
kpis:
  - name: Task Success Rate
    target: 99%
    current: TBD
    exit_criteria: Must be ≥95% before production

  - name: Retry Rate
    target: <10%
    current: TBD
    exit_criteria: Must be <15%

  - name: Contract Lock Latency
    target: <1s
    current: TBD
    exit_criteria: P95 must be <2s
```

**BDV Lens KPIs**:
```yaml
kpis:
  - name: Scenario Pass Rate
    target: 95%
    current: TBD
    exit_criteria: Must be ≥90% before production

  - name: Flake Rate
    target: <5%
    current: TBD
    exit_criteria: Must be <10%

  - name: Test Execution Time
    target: <5min
    current: TBD
    exit_criteria: P95 must be <10min
```

**ACC Lens KPIs**:
```yaml
kpis:
  - name: Blocking Violations
    target: 0
    current: TBD
    exit_criteria: Must be 0 before production

  - name: Cyclic Dependencies
    target: 0
    current: TBD
    exit_criteria: Must be 0 before production

  - name: Average Instability
    target: <0.5
    current: TBD
    exit_criteria: Must be <0.7
```

**Convergence Lens KPIs**:
```yaml
kpis:
  - name: Deployment Approval Rate
    target: 80%
    current: TBD
    exit_criteria: Must be ≥70%

  - name: Contract Alignment
    target: 100%
    current: TBD
    exit_criteria: Must be 100% (all contracts linked)

  - name: Time-Travel Query Latency
    target: <2s
    current: TBD
    exit_criteria: P95 must be <5s
```

---

## Summary

This document addresses critical production readiness requirements:

### Tri-Modal System Hardening
✅ Schema registry with versioning and compatibility checks
✅ OpenTelemetry distributed tracing end-to-end
✅ Idempotency + exactly-once with transactional Kafka
✅ DLQ with categorized replay mechanisms
✅ ICS provenance tracking with confidence scoring
✅ Bi-temporal UGM for time-travel queries
✅ RBAC + PII tagging + retention policies
✅ End-to-end SLO tracking (ingest → UI)

### Infrastructure Resilience
✅ Load testing scenarios and benchmarks
✅ Backpressure with circuit breakers
✅ Disaster recovery from Kafka log
✅ Canary deployments with trace replay

### Quick Start & Operations
✅ One-click Docker Compose with golden dataset
✅ Golden-run assertions for CI/CD
✅ Troubleshooting symptom → solution matrix
✅ Diagnostic commands and replay tools
✅ Per-lens KPIs with exit criteria

**Priority**: Implement in Sprint 1-2 before frontend development.

---

**Document Version**: 1.0
**Date**: 2025-10-13
**Status**: Critical Production Requirements
**Next**: Implement in Sprint 1 (Event-Driven Foundation)
