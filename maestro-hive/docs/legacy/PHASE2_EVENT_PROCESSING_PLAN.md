# Phase 2: Event Processing Correctness Tests - PLAN

**Date**: 2025-10-13
**Phase**: Event Processing Correctness
**Status**: 🎯 **PLANNING**

---

## Executive Summary

Phase 2 focuses on **event processing correctness** - ensuring the system handles real-world event stream chaos correctly. This includes:
- **Event Ordering Chaos**: Out-of-order, duplicate, and late-arriving events
- **Property-Based ICS Correlation**: Invariant-based testing for event correlation
- **Bi-Temporal Queries**: Time-travel and deterministic processing

**Total Tests**: 150 tests
**Estimated Time**: 10-12 hours
**Risk Level**: MEDIUM (complex state management)

---

## Phase 2 Breakdown

### Phase 2.1: Event Ordering Chaos Tests (50 tests)
**File**: `tests/dde/chaos/test_event_ordering.py`
**Test IDs**: DDE-950 to DDE-999

**Focus**: Real-world event stream chaos scenarios
- Out-of-order event arrival
- Duplicate event detection and handling
- Late-arriving events
- Event reordering by timestamp
- Watermark-based processing
- Event windowing (tumbling, sliding, session)
- Event time vs processing time
- Backfill scenarios

**Key Patterns**:
```python
# Out-of-order detection
events = [
    Event(id=1, timestamp="2024-01-01T10:00:00", seq=1),
    Event(id=2, timestamp="2024-01-01T10:00:02", seq=3),  # Arrives second
    Event(id=3, timestamp="2024-01-01T10:00:01", seq=2),  # Late arrival
]
# Expected: Events reordered by timestamp, not arrival order
```

**Test Categories**:
1. **Out-of-Order Events** (10 tests)
   - Single out-of-order event
   - Multiple out-of-order events
   - Extreme out-of-order (hours/days late)
   - Watermark advancement
   - Late data handling

2. **Duplicate Events** (10 tests)
   - Exact duplicate detection
   - Partial duplicate (same ID, different payload)
   - Duplicate across windows
   - Deduplication window size
   - Duplicate handling strategies (keep first, keep last, merge)

3. **Event Windowing** (15 tests)
   - Tumbling windows (fixed size, non-overlapping)
   - Sliding windows (overlapping)
   - Session windows (gap-based)
   - Window trigger policies (time, count, watermark)
   - Late data in closed windows
   - Window early close
   - Window state management

4. **Watermarks** (10 tests)
   - Watermark generation strategies
   - Watermark propagation
   - Watermark alignment across partitions
   - Allowed lateness
   - Watermark stalls

5. **Backfill & Replay** (5 tests)
   - Historical data backfill
   - Event replay with correct timestamps
   - Backfill without affecting live processing
   - Replay idempotency
   - Replay performance

---

### Phase 2.2: Property-Based ICS Correlation Tests (50 tests)
**File**: `tests/dde/property/test_ics_correlation.py`
**Test IDs**: ACC-150 to ACC-199

**Focus**: Invariant-based testing for event correlation using Hypothesis
- ICS (Immutable Correlation State) invariants
- Event correlation by correlation ID
- Saga pattern validation
- Distributed trace correlation
- Causal ordering

**Key Patterns**:
```python
from hypothesis import given, strategies as st

@given(
    events=st.lists(
        st.builds(Event,
            correlation_id=st.uuids(),
            event_type=st.sampled_from(["Started", "Processing", "Completed"]),
            timestamp=st.datetimes()
        ),
        min_size=3, max_size=100
    )
)
def test_correlation_invariants(events):
    # Property: All events with same correlation_id must maintain causal order
    processor = ICSProcessor()
    result = processor.process_batch(events)

    # Invariant 1: Each correlation_id has events in causal order
    for corr_id in result.correlation_ids:
        correlated_events = result.get_by_correlation(corr_id)
        assert is_causally_ordered(correlated_events)

    # Invariant 2: No orphaned events (all correlated events have parent)
    assert result.orphaned_events == []
```

**Test Categories**:
1. **ICS Invariants** (15 tests)
   - Correlation ID uniqueness
   - Parent-child relationships
   - Causal ordering within correlation
   - Complete saga paths
   - No orphaned events

2. **Correlation Strategies** (10 tests)
   - Direct correlation by ID
   - Transitive correlation (A→B→C)
   - Multi-parent correlation (fan-in)
   - Multi-child correlation (fan-out)
   - Correlation timeout handling

3. **Distributed Tracing** (10 tests)
   - Trace ID propagation
   - Span hierarchy
   - Trace completion detection
   - Missing spans detection
   - Trace stitching across services

4. **Saga Patterns** (10 tests)
   - Saga initiation
   - Saga progression
   - Saga completion
   - Saga compensation (rollback)
   - Saga timeout

5. **Property-Based Edge Cases** (5 tests)
   - Random event orderings
   - Extreme latencies
   - Partition skew
   - High fan-out scenarios
   - Cyclic dependencies

---

### Phase 2.3: Bi-Temporal Query Tests (50 tests)
**File**: `tests/acc/temporal/test_bitemporal_queries.py`
**Test IDs**: ACC-200 to ACC-249

**Focus**: Bi-temporal data management - event time vs record time
- Event time (when event occurred)
- Record time (when we learned about it)
- Time-travel queries
- As-of queries
- Point-in-time snapshots
- Temporal joins
- Late corrections

**Key Patterns**:
```python
# Bi-temporal data model
class BiTemporalRecord:
    entity_id: str
    event_time: datetime  # When event happened
    record_time: datetime  # When we learned about it
    data: dict
    valid_from: datetime
    valid_to: datetime

# Time-travel query
def query_as_of(entity_id: str, as_of_time: datetime):
    """Query state as it was known at as_of_time"""
    return db.query(
        entity_id=entity_id,
        record_time <= as_of_time
    ).order_by(record_time.desc()).first()
```

**Test Categories**:
1. **Bi-Temporal Model** (10 tests)
   - Event time vs record time
   - Valid time ranges
   - Temporal versioning
   - Late arrival corrections
   - Retroactive updates

2. **Time-Travel Queries** (15 tests)
   - Query as of past time
   - Query as of future time (projections)
   - Query version history
   - Query temporal ranges
   - Query temporal gaps

3. **Temporal Joins** (10 tests)
   - Join on event time
   - Join on record time
   - Join with temporal overlap
   - Join with temporal lag
   - Temporal window joins

4. **Corrections & Amendments** (10 tests)
   - Late correction handling
   - Retroactive data fixes
   - Correction propagation
   - Correction audit trail
   - Correction idempotency

5. **Deterministic Processing** (5 tests)
   - Same input → same output (determinism)
   - Replay determinism
   - Time-dependent determinism
   - Snapshot consistency
   - Read-your-writes consistency

---

## Technical Implementation Details

### Event Ordering Implementation

```python
class EventBuffer:
    """Buffer for out-of-order event handling"""

    def __init__(self, max_lateness: timedelta):
        self.max_lateness = max_lateness
        self.buffer: List[Event] = []
        self.watermark: datetime = datetime.min

    def add(self, event: Event):
        """Add event to buffer"""
        self.buffer.append(event)

        # Update watermark (max event time seen - max_lateness)
        max_event_time = max(e.event_time for e in self.buffer)
        self.watermark = max_event_time - self.max_lateness

    def get_ready_events(self) -> List[Event]:
        """Get events ready for processing (before watermark)"""
        ready = [e for e in self.buffer if e.event_time <= self.watermark]
        self.buffer = [e for e in self.buffer if e.event_time > self.watermark]
        return sorted(ready, key=lambda e: e.event_time)
```

### ICS Correlation Implementation

```python
class ICSProcessor:
    """Immutable Correlation State processor"""

    def __init__(self):
        self.correlations: Dict[str, List[Event]] = {}
        self.parent_map: Dict[str, str] = {}  # event_id -> parent_id

    def process(self, event: Event) -> CorrelationResult:
        """Process event with correlation"""
        corr_id = event.correlation_id

        # Add to correlation group
        if corr_id not in self.correlations:
            self.correlations[corr_id] = []
        self.correlations[corr_id].append(event)

        # Track parent-child relationship
        if event.parent_event_id:
            self.parent_map[event.event_id] = event.parent_event_id

        # Check causal ordering invariant
        events = self.correlations[corr_id]
        if not self._is_causally_ordered(events):
            raise CausalOrderViolation(f"Events for {corr_id} not causally ordered")

        return CorrelationResult(
            correlation_id=corr_id,
            events=events,
            is_complete=self._is_complete(corr_id)
        )

    def _is_causally_ordered(self, events: List[Event]) -> bool:
        """Check if events maintain causal order"""
        for i in range(1, len(events)):
            # Child must come after parent
            if events[i].parent_event_id:
                parent_idx = next((j for j, e in enumerate(events)
                                  if e.event_id == events[i].parent_event_id), None)
                if parent_idx and parent_idx >= i:
                    return False
        return True
```

### Bi-Temporal Implementation

```python
class BiTemporalStore:
    """Bi-temporal data store with time-travel queries"""

    def __init__(self):
        # Store: (entity_id, record_time) -> (event_time, data)
        self.store: Dict[Tuple[str, datetime], Tuple[datetime, dict]] = {}

    def insert(self, entity_id: str, event_time: datetime, data: dict):
        """Insert record with bi-temporal timestamps"""
        record_time = datetime.now()
        self.store[(entity_id, record_time)] = (event_time, data)

    def query_as_of(self, entity_id: str, as_of_time: datetime) -> Optional[dict]:
        """Query state as known at as_of_time (record time)"""
        # Find latest record before as_of_time
        records = [
            (record_time, event_time, data)
            for (eid, record_time), (event_time, data) in self.store.items()
            if eid == entity_id and record_time <= as_of_time
        ]

        if not records:
            return None

        # Return latest by record time
        records.sort(key=lambda r: r[0], reverse=True)
        return records[0][2]  # data

    def query_at_event_time(self, entity_id: str, event_time: datetime) -> Optional[dict]:
        """Query state at specific event time"""
        # Find record with event time closest to target
        records = [
            (et, data)
            for (eid, _), (et, data) in self.store.items()
            if eid == entity_id and et <= event_time
        ]

        if not records:
            return None

        # Return latest by event time
        records.sort(key=lambda r: r[0], reverse=True)
        return records[0][1]  # data
```

---

## Dependencies

### New Dependencies Required

```python
# requirements-test.txt additions

# Property-based testing
hypothesis>=6.92.0

# Event streaming simulation
faker>=20.0.0  # For generating realistic test data

# Time manipulation
freezegun>=1.2.0  # For time-travel testing

# Performance profiling
pytest-benchmark>=4.0.0

# Async testing enhancements
pytest-asyncio>=0.21.0
```

---

## Success Criteria

| Criterion | Target | Priority |
|-----------|--------|----------|
| **Tests Created** | 150 | ✅ Required |
| **Pass Rate** | >95% | ✅ Required |
| **Execution Time** | <2 minutes | ✅ Required |
| **Property Tests** | 30+ property-based tests | ✅ Required |
| **Coverage** | Event processing: >90% | ✅ Required |

---

## Implementation Order

1. **Phase 2.1**: Event Ordering Chaos (Days 1-4)
   - Day 1: Out-of-order and duplicate events
   - Day 2: Event windowing
   - Day 3: Watermarks and late data
   - Day 4: Backfill and replay

2. **Phase 2.2**: ICS Correlation (Days 5-8)
   - Day 5: ICS invariants and basic correlation
   - Day 6: Property-based tests with Hypothesis
   - Day 7: Distributed tracing correlation
   - Day 8: Saga patterns

3. **Phase 2.3**: Bi-Temporal Queries (Days 9-12)
   - Day 9: Bi-temporal model and queries
   - Day 10: Time-travel queries
   - Day 11: Temporal joins and corrections
   - Day 12: Deterministic processing

---

## Risk Assessment

### High-Risk Areas
- ⚠️ **Non-deterministic tests**: Time-dependent tests may be flaky
- ⚠️ **Property-based complexity**: Hypothesis may generate edge cases hard to debug
- ⚠️ **State management**: Complex state across events may cause issues

### Mitigation Strategies
- Use `freezegun` for deterministic time in tests
- Start with simple Hypothesis strategies, expand gradually
- Implement comprehensive state logging for debugging
- Use snapshot testing for complex state assertions

---

## Next Steps

1. ✅ Create Phase 2 plan document
2. ⏭️ Set up Hypothesis framework
3. ⏭️ Implement Phase 2.1 tests (Event Ordering)
4. ⏭️ Implement Phase 2.2 tests (ICS Correlation)
5. ⏭️ Implement Phase 2.3 tests (Bi-Temporal)
6. ⏭️ Run full Phase 2 test suite
7. ⏭️ Update documentation

---

**Status**: 🎯 **READY TO START IMPLEMENTATION**

**Next Action**: Begin Phase 2.1 - Event Ordering Chaos Tests

**Estimated Completion**: 12 working hours over 2 weeks

---

**Prepared by**: Claude Code
**Date**: 2025-10-13
**Phase 2 Status**: PLANNING COMPLETE
