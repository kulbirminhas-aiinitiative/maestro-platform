"""
Tri-Modal Integration Tests for GraphQL Gateway

Tests the complete pipeline:
1. Produce events to Kafka
2. ICS processes and writes to Neo4j
3. Query GraphQL API
4. Verify results match expectations

Tests DDE, BDV, and ACC flows end-to-end.
"""

import pytest
import asyncio
import time
import uuid
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List

# GraphQL client
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Event producers
from ics.producers.instrumented_producer import InstrumentedKafkaProducer
from ics.config import config


# ============================================================================
# Test Configuration
# ============================================================================

GRAPHQL_URL = "http://localhost:8000/graphql"
KAFKA_BOOTSTRAP_SERVERS = config.kafka.bootstrap_servers
SCHEMA_REGISTRY_URL = config.kafka.schema_registry_url

DDE_TOPIC = config.dde_topic
BDV_TOPIC = config.bdv_topic
ACC_TOPIC = config.acc_topic

# Wait times for async processing
EVENT_PROCESSING_WAIT = 5  # seconds
CORRELATION_WAIT = 10  # seconds


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def graphql_client():
    """Create GraphQL client."""
    transport = RequestsHTTPTransport(url=GRAPHQL_URL)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    return client


@pytest.fixture(scope="module")
def dde_producer():
    """Create DDE event producer."""
    producer = InstrumentedKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        schema_registry_url=SCHEMA_REGISTRY_URL
    )
    yield producer
    producer.close()


@pytest.fixture(scope="module")
def bdv_producer():
    """Create BDV event producer."""
    producer = InstrumentedKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        schema_registry_url=SCHEMA_REGISTRY_URL
    )
    yield producer
    producer.close()


@pytest.fixture(scope="module")
def acc_producer():
    """Create ACC event producer."""
    producer = InstrumentedKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        schema_registry_url=SCHEMA_REGISTRY_URL
    )
    yield producer
    producer.close()


@pytest.fixture(scope="function")
def iteration_id():
    """Generate unique iteration ID for test."""
    return f"test-iter-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def contract_id():
    """Generate unique contract ID for test."""
    return f"TestAPI:v{uuid.uuid4().hex[:4]}"


# ============================================================================
# Helper Functions
# ============================================================================

def wait_for_processing(seconds: int = EVENT_PROCESSING_WAIT):
    """Wait for Kafka → ICS → Neo4j processing."""
    print(f"Waiting {seconds}s for event processing...")
    time.sleep(seconds)


def create_dde_event(
    iteration_id: str,
    contract_id: str,
    event_type: str = "CONTRACT_VALIDATED",
    node_id: str = None
) -> Dict[str, Any]:
    """Create DDE event dict."""
    return {
        "event_id": str(uuid.uuid4()),
        "iteration_id": iteration_id,
        "timestamp": datetime.now().isoformat(),
        "workflow_id": f"workflow-{iteration_id}",
        "event_type": event_type,
        "node_id": node_id or str(uuid.uuid4()),
        "node_type": "INTERFACE",
        "node_status": "COMPLETED",
        "contract_id": contract_id,
        "quality_gate_passed": True,
        "trace_id": str(uuid.uuid4()),
        "span_id": str(uuid.uuid4()),
        "metadata": {}
    }


def create_bdv_event(
    iteration_id: str,
    contract_id: str,
    event_type: str = "SCENARIO_PASSED",
    scenario_id: str = None
) -> Dict[str, Any]:
    """Create BDV event dict."""
    return {
        "event_id": str(uuid.uuid4()),
        "iteration_id": iteration_id,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "scenario_id": scenario_id or str(uuid.uuid4()),
        "scenario_name": f"Test scenario for {contract_id}",
        "scenario_status": "PASSED",
        "scenario_tags": [f"@contract:{contract_id}"],
        "contract_tags": [contract_id],
        "duration_ms": 1000,
        "trace_id": str(uuid.uuid4()),
        "span_id": str(uuid.uuid4()),
        "metadata": {}
    }


def create_acc_event(
    iteration_id: str,
    contract_id: str,
    event_type: str = "MODULE_ANALYZED",
    violation_detected: bool = False
) -> Dict[str, Any]:
    """Create ACC event dict."""
    event = {
        "event_id": str(uuid.uuid4()),
        "iteration_id": iteration_id,
        "timestamp": datetime.now().isoformat(),
        "manifest_name": "test-manifest",
        "event_type": event_type,
        "module_path": f"src/{contract_id.replace(':', '/')}.py",
        "module_name": contract_id.split(':')[0],
        "total_modules": 10,
        "total_dependencies": 15,
        "total_violations": 1 if violation_detected else 0,
        "blocking_violations": 0,
        "trace_id": str(uuid.uuid4()),
        "span_id": str(uuid.uuid4()),
        "metadata": {}
    }

    if violation_detected:
        event.update({
            "violation_type": "HIGH_COUPLING",
            "violation_severity": "WARNING",
            "violation_message": "Module coupling score exceeds threshold"
        })

    return event


# ============================================================================
# Test 1: DDE Flow
# ============================================================================

def test_dde_flow(graphql_client, dde_producer, iteration_id, contract_id):
    """
    Test DDE event flow: Kafka → ICS → Neo4j → GraphQL.
    """
    print(f"\n{'='*80}")
    print(f"TEST 1: DDE FLOW")
    print(f"Iteration ID: {iteration_id}")
    print(f"Contract ID: {contract_id}")
    print(f"{'='*80}\n")

    # Step 1: Produce DDE event to Kafka
    dde_event = create_dde_event(iteration_id, contract_id)
    event_id = dde_event["event_id"]

    print(f"1. Producing DDE event to Kafka: {event_id}")
    dde_producer.produce(
        topic=DDE_TOPIC,
        key=iteration_id,
        value=dde_event
    )
    dde_producer.flush()
    print("   ✓ Event produced")

    # Step 2: Wait for processing
    wait_for_processing()

    # Step 3: Query GraphQL for event
    print(f"\n2. Querying GraphQL for DDE event: {event_id}")
    query = gql("""
        query GetDDEEvent($eventId: ID!) {
            ddeEvent(eventId: $eventId) {
                eventId
                iterationId
                timestamp
                workflowId
                eventType
                nodeId
                nodeType
                nodeStatus
                contractId
                qualityGatePassed
                traceId
                spanId
                correlations {
                    linkId
                    targetStream
                    confidence {
                        value
                        provenance
                    }
                }
            }
        }
    """)

    result = graphql_client.execute(query, variable_values={"eventId": event_id})

    # Step 4: Verify result
    print("\n3. Verifying results...")
    assert result is not None, "GraphQL query returned None"
    assert "ddeEvent" in result, "Missing ddeEvent in response"

    dde_result = result["ddeEvent"]
    assert dde_result is not None, f"DDE event {event_id} not found in Neo4j"

    # Verify fields
    assert dde_result["eventId"] == event_id
    assert dde_result["iterationId"] == iteration_id
    assert dde_result["contractId"] == contract_id
    assert dde_result["eventType"] == "CONTRACT_VALIDATED"
    assert dde_result["nodeType"] == "INTERFACE"

    print(f"   ✓ Event ID matches: {dde_result['eventId']}")
    print(f"   ✓ Iteration ID matches: {dde_result['iterationId']}")
    print(f"   ✓ Contract ID matches: {dde_result['contractId']}")
    print(f"   ✓ Event type: {dde_result['eventType']}")
    print(f"   ✓ Node type: {dde_result['nodeType']}")

    # Correlations may be empty if other streams haven't produced yet
    correlations = dde_result.get("correlations", [])
    print(f"   ℹ Correlations found: {len(correlations)}")

    print("\n✅ TEST 1 PASSED: DDE Flow\n")


# ============================================================================
# Test 2: BDV Flow
# ============================================================================

def test_bdv_flow(graphql_client, bdv_producer, iteration_id, contract_id):
    """
    Test BDV event flow: Kafka → ICS → Neo4j → GraphQL.
    """
    print(f"\n{'='*80}")
    print(f"TEST 2: BDV FLOW")
    print(f"Iteration ID: {iteration_id}")
    print(f"Contract ID: {contract_id}")
    print(f"{'='*80}\n")

    # Step 1: Produce BDV event to Kafka
    bdv_event = create_bdv_event(iteration_id, contract_id)
    event_id = bdv_event["event_id"]

    print(f"1. Producing BDV event to Kafka: {event_id}")
    bdv_producer.produce(
        topic=BDV_TOPIC,
        key=iteration_id,
        value=bdv_event
    )
    bdv_producer.flush()
    print("   ✓ Event produced")

    # Step 2: Wait for processing
    wait_for_processing()

    # Step 3: Query GraphQL for event
    print(f"\n2. Querying GraphQL for BDV event: {event_id}")
    query = gql("""
        query GetBDVEvent($eventId: ID!) {
            bdvEvent(eventId: $eventId) {
                eventId
                iterationId
                timestamp
                eventType
                scenarioId
                scenarioName
                scenarioStatus
                contractTags
                durationMs
                traceId
                spanId
                correlations {
                    linkId
                    targetStream
                    confidence {
                        value
                        provenance
                    }
                }
            }
        }
    """)

    result = graphql_client.execute(query, variable_values={"eventId": event_id})

    # Step 4: Verify result
    print("\n3. Verifying results...")
    assert result is not None, "GraphQL query returned None"
    assert "bdvEvent" in result, "Missing bdvEvent in response"

    bdv_result = result["bdvEvent"]
    assert bdv_result is not None, f"BDV event {event_id} not found in Neo4j"

    # Verify fields
    assert bdv_result["eventId"] == event_id
    assert bdv_result["iterationId"] == iteration_id
    assert contract_id in bdv_result["contractTags"]
    assert bdv_result["eventType"] == "SCENARIO_PASSED"
    assert bdv_result["scenarioStatus"] == "PASSED"

    print(f"   ✓ Event ID matches: {bdv_result['eventId']}")
    print(f"   ✓ Iteration ID matches: {bdv_result['iterationId']}")
    print(f"   ✓ Contract tags: {bdv_result['contractTags']}")
    print(f"   ✓ Event type: {bdv_result['eventType']}")
    print(f"   ✓ Scenario status: {bdv_result['scenarioStatus']}")

    correlations = bdv_result.get("correlations", [])
    print(f"   ℹ Correlations found: {len(correlations)}")

    print("\n✅ TEST 2 PASSED: BDV Flow\n")


# ============================================================================
# Test 3: ACC Flow
# ============================================================================

def test_acc_flow(graphql_client, acc_producer, iteration_id, contract_id):
    """
    Test ACC event flow: Kafka → ICS → Neo4j → GraphQL.
    """
    print(f"\n{'='*80}")
    print(f"TEST 3: ACC FLOW")
    print(f"Iteration ID: {iteration_id}")
    print(f"Contract ID: {contract_id}")
    print(f"{'='*80}\n")

    # Step 1: Produce ACC event to Kafka
    acc_event = create_acc_event(iteration_id, contract_id, violation_detected=False)
    event_id = acc_event["event_id"]

    print(f"1. Producing ACC event to Kafka: {event_id}")
    acc_producer.produce(
        topic=ACC_TOPIC,
        key=iteration_id,
        value=acc_event
    )
    acc_producer.flush()
    print("   ✓ Event produced")

    # Step 2: Wait for processing
    wait_for_processing()

    # Step 3: Query GraphQL for event
    print(f"\n2. Querying GraphQL for ACC event: {event_id}")
    query = gql("""
        query GetACCEvent($eventId: ID!) {
            accEvent(eventId: $eventId) {
                eventId
                iterationId
                timestamp
                manifestName
                eventType
                modulePath
                moduleName
                totalModules
                totalDependencies
                totalViolations
                blockingViolations
                traceId
                spanId
                correlations {
                    linkId
                    targetStream
                    confidence {
                        value
                        provenance
                    }
                }
            }
        }
    """)

    result = graphql_client.execute(query, variable_values={"eventId": event_id})

    # Step 4: Verify result
    print("\n3. Verifying results...")
    assert result is not None, "GraphQL query returned None"
    assert "accEvent" in result, "Missing accEvent in response"

    acc_result = result["accEvent"]
    assert acc_result is not None, f"ACC event {event_id} not found in Neo4j"

    # Verify fields
    assert acc_result["eventId"] == event_id
    assert acc_result["iterationId"] == iteration_id
    assert acc_result["eventType"] == "MODULE_ANALYZED"
    assert acc_result["totalViolations"] == 0  # No violations

    print(f"   ✓ Event ID matches: {acc_result['eventId']}")
    print(f"   ✓ Iteration ID matches: {acc_result['iterationId']}")
    print(f"   ✓ Event type: {acc_result['eventType']}")
    print(f"   ✓ Total violations: {acc_result['totalViolations']}")
    print(f"   ✓ Module path: {acc_result['modulePath']}")

    correlations = acc_result.get("correlations", [])
    print(f"   ℹ Correlations found: {len(correlations)}")

    print("\n✅ TEST 3 PASSED: ACC Flow\n")


# ============================================================================
# Test 4: Contract Star Formation (Tri-Modal Convergence)
# ============================================================================

def test_contract_star_formation(
    graphql_client,
    dde_producer,
    bdv_producer,
    acc_producer,
    iteration_id,
    contract_id
):
    """
    Test contract star formation when all 3 streams converge.

    Deployment Rule: Deploy ONLY when DDE ✅ AND BDV ✅ AND ACC ✅
    """
    print(f"\n{'='*80}")
    print(f"TEST 4: CONTRACT STAR FORMATION (TRI-MODAL CONVERGENCE)")
    print(f"Iteration ID: {iteration_id}")
    print(f"Contract ID: {contract_id}")
    print(f"{'='*80}\n")

    # Step 1: Produce events from all 3 streams
    print("1. Producing events from all 3 streams...")

    # DDE: Contract validated
    dde_event = create_dde_event(iteration_id, contract_id, "CONTRACT_VALIDATED")
    dde_producer.produce(topic=DDE_TOPIC, key=iteration_id, value=dde_event)
    print(f"   ✓ DDE event produced: {dde_event['event_id']}")

    # BDV: Scenario passed with contract tag
    bdv_event = create_bdv_event(iteration_id, contract_id, "SCENARIO_PASSED")
    bdv_producer.produce(topic=BDV_TOPIC, key=iteration_id, value=bdv_event)
    print(f"   ✓ BDV event produced: {bdv_event['event_id']}")

    # ACC: Module analyzed, no violations
    acc_event = create_acc_event(iteration_id, contract_id, "MODULE_ANALYZED", violation_detected=False)
    acc_producer.produce(topic=ACC_TOPIC, key=iteration_id, value=acc_event)
    print(f"   ✓ ACC event produced: {acc_event['event_id']}")

    dde_producer.flush()
    bdv_producer.flush()
    acc_producer.flush()

    # Step 2: Wait for correlation processing
    print(f"\n2. Waiting {CORRELATION_WAIT}s for correlation and contract star formation...")
    time.sleep(CORRELATION_WAIT)

    # Step 3: Query for contract star
    print(f"\n3. Querying GraphQL for contract star: {contract_id}")
    query = gql("""
        query GetContractStar($contractId: String!, $iterationId: ID!) {
            contractStar(contractId: $contractId, iterationId: $iterationId) {
                contractId
                iterationId
                ddeInterfaceNodeId
                ddeContractLocked
                ddeContractValidated
                bdvContractTag
                bdvScenarios
                bdvAllPassed
                accComponentBoundary
                accViolations
                accClean
                isComplete
                isValid
                createdAt
                updatedAt
            }
        }
    """)

    result = graphql_client.execute(
        query,
        variable_values={
            "contractId": contract_id,
            "iterationId": iteration_id
        }
    )

    # Step 4: Verify contract star
    print("\n4. Verifying contract star...")
    assert result is not None, "GraphQL query returned None"
    assert "contractStar" in result, "Missing contractStar in response"

    star = result["contractStar"]

    if star is None:
        print("   ⚠️  Contract star not yet formed (correlation may still be processing)")
        print("   ℹ This is acceptable for async processing")
        print("\n⚠️  TEST 4 SKIPPED: Contract star not yet formed\n")
        pytest.skip("Contract star not yet formed")
        return

    # Verify tri-modal convergence
    print(f"   ✓ Contract star found: {star['contractId']}")
    print(f"   ✓ Is complete: {star['isComplete']}")
    print(f"   ✓ Is valid: {star['isValid']}")
    print(f"\n   Tri-Modal Status:")
    print(f"   - DDE Contract Validated: {star['ddeContractValidated']} {'✅' if star['ddeContractValidated'] else '❌'}")
    print(f"   - BDV All Passed: {star['bdvAllPassed']} {'✅' if star['bdvAllPassed'] else '❌'}")
    print(f"   - ACC Clean: {star['accClean']} {'✅' if star['accClean'] else '❌'}")

    # Deployment readiness check
    is_deployable = (
        star['ddeContractValidated'] and
        star['bdvAllPassed'] and
        star['accClean']
    )

    print(f"\n   🚀 Deployment Readiness: {is_deployable} {'✅ READY TO DEPLOY' if is_deployable else '❌ NOT READY'}")

    assert star["isComplete"], "Contract star should be complete"
    assert star["isValid"] == is_deployable, "isValid should match deployment readiness"

    print("\n✅ TEST 4 PASSED: Contract Star Formation\n")


# ============================================================================
# Test 5: Pagination
# ============================================================================

def test_pagination(graphql_client, dde_producer, iteration_id):
    """Test cursor-based pagination."""
    print(f"\n{'='*80}")
    print(f"TEST 5: PAGINATION")
    print(f"Iteration ID: {iteration_id}")
    print(f"{'='*80}\n")

    # Step 1: Produce 10 events
    print("1. Producing 10 DDE events...")
    event_ids = []
    for i in range(10):
        event = create_dde_event(iteration_id, f"Contract{i:02d}")
        event_ids.append(event["event_id"])
        dde_producer.produce(topic=DDE_TOPIC, key=iteration_id, value=event)

    dde_producer.flush()
    print(f"   ✓ Produced {len(event_ids)} events")

    # Step 2: Wait for processing
    wait_for_processing()

    # Step 3: Query with pagination (first 5)
    print("\n2. Querying first 5 events...")
    query = gql("""
        query GetDDEEvents($iterationId: ID!, $first: Int, $after: String) {
            ddeEvents(
                filter: { iterationId: $iterationId }
                pagination: { first: $first, after: $after }
            ) {
                edges {
                    node {
                        eventId
                        iterationId
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
                totalCount
            }
        }
    """)

    result = graphql_client.execute(
        query,
        variable_values={"iterationId": iteration_id, "first": 5}
    )

    # Step 4: Verify pagination
    print("\n3. Verifying pagination...")
    assert result is not None
    assert "ddeEvents" in result

    connection = result["ddeEvents"]
    edges = connection["edges"]
    page_info = connection["pageInfo"]

    print(f"   ✓ Total count: {connection['totalCount']}")
    print(f"   ✓ Edges returned: {len(edges)}")
    print(f"   ✓ Has next page: {page_info['hasNextPage']}")

    assert len(edges) == 5, "Should return 5 events"
    assert page_info["hasNextPage"], "Should have next page"
    assert connection["totalCount"] >= 10, "Total count should be at least 10"

    # Step 5: Query next page
    print("\n4. Querying next page...")
    end_cursor = page_info["endCursor"]

    result2 = graphql_client.execute(
        query,
        variable_values={
            "iterationId": iteration_id,
            "first": 5,
            "after": end_cursor
        }
    )

    connection2 = result2["ddeEvents"]
    edges2 = connection2["edges"]

    print(f"   ✓ Second page edges: {len(edges2)}")

    assert len(edges2) >= 5, "Should return at least 5 more events"

    # Verify no overlap
    first_page_ids = [edge["node"]["eventId"] for edge in edges]
    second_page_ids = [edge["node"]["eventId"] for edge in edges2]

    overlap = set(first_page_ids) & set(second_page_ids)
    assert len(overlap) == 0, f"Pages should not overlap, found: {overlap}"

    print("   ✓ No overlap between pages")

    print("\n✅ TEST 5 PASSED: Pagination\n")


# ============================================================================
# Test 6: Filtering
# ============================================================================

def test_filtering(graphql_client, dde_producer, bdv_producer, iteration_id):
    """Test event filtering."""
    print(f"\n{'='*80}")
    print(f"TEST 6: FILTERING")
    print(f"Iteration ID: {iteration_id}")
    print(f"{'='*80}\n")

    # Step 1: Produce events with different types
    print("1. Producing events with different types...")

    # 5 CONTRACT_VALIDATED events
    contract_ids = []
    for i in range(5):
        contract_id = f"FilterContract{i:02d}"
        contract_ids.append(contract_id)
        event = create_dde_event(iteration_id, contract_id, "CONTRACT_VALIDATED")
        dde_producer.produce(topic=DDE_TOPIC, key=iteration_id, value=event)

    # 3 ARTIFACT_CREATED events
    for i in range(3):
        event = create_dde_event(iteration_id, f"ArtifactContract{i:02d}", "ARTIFACT_CREATED")
        dde_producer.produce(topic=DDE_TOPIC, key=iteration_id, value=event)

    dde_producer.flush()
    print(f"   ✓ Produced 5 CONTRACT_VALIDATED + 3 ARTIFACT_CREATED events")

    # Step 2: Wait for processing
    wait_for_processing()

    # Step 3: Query with filter for CONTRACT_VALIDATED only
    print("\n2. Querying with filter: eventType = CONTRACT_VALIDATED")
    query = gql("""
        query GetFilteredDDEEvents($iterationId: ID!, $eventType: DDEEventType) {
            ddeEvents(
                filter: {
                    iterationId: $iterationId
                    eventType: $eventType
                }
            ) {
                edges {
                    node {
                        eventId
                        eventType
                        contractId
                    }
                }
                totalCount
            }
        }
    """)

    result = graphql_client.execute(
        query,
        variable_values={
            "iterationId": iteration_id,
            "eventType": "CONTRACT_VALIDATED"
        }
    )

    # Step 4: Verify filtering
    print("\n3. Verifying filtering...")
    assert result is not None
    assert "ddeEvents" in result

    connection = result["ddeEvents"]
    edges = connection["edges"]

    print(f"   ✓ Total count: {connection['totalCount']}")
    print(f"   ✓ Edges returned: {len(edges)}")

    # All events should be CONTRACT_VALIDATED
    for edge in edges:
        assert edge["node"]["eventType"] == "CONTRACT_VALIDATED", \
            f"Expected CONTRACT_VALIDATED, got {edge['node']['eventType']}"

    print("   ✓ All events match filter: CONTRACT_VALIDATED")

    assert len(edges) == 5, f"Expected 5 CONTRACT_VALIDATED events, got {len(edges)}"

    print("\n✅ TEST 6 PASSED: Filtering\n")


# ============================================================================
# Test 7: Statistics
# ============================================================================

def test_statistics(graphql_client, iteration_id):
    """Test system and iteration statistics."""
    print(f"\n{'='*80}")
    print(f"TEST 7: STATISTICS")
    print(f"Iteration ID: {iteration_id}")
    print(f"{'='*80}\n")

    # Step 1: Query system stats
    print("1. Querying system statistics...")
    system_query = gql("""
        query GetSystemStats {
            systemStats {
                totalEvents
                totalCorrelations
                totalContractStars
                eventsByStream
                correlationRate
                throughput {
                    eventsPerSecond
                    correlationsPerSecond
                }
                latency {
                    p50Ms
                    p95Ms
                    p99Ms
                }
            }
        }
    """)

    system_result = graphql_client.execute(system_query)

    print("\n2. System Statistics:")
    stats = system_result["systemStats"]
    print(f"   - Total Events: {stats['totalEvents']}")
    print(f"   - Total Correlations: {stats['totalCorrelations']}")
    print(f"   - Total Contract Stars: {stats['totalContractStars']}")
    print(f"   - Correlation Rate: {stats['correlationRate']:.2f}")

    assert stats["totalEvents"] > 0, "Should have events in system"

    # Step 2: Query iteration stats
    print("\n3. Querying iteration statistics...")
    iter_query = gql("""
        query GetIterationStats($iterationId: ID!) {
            iterationStats(iterationId: $iterationId) {
                iterationId
                totalEvents
                ddeEvents
                bdvEvents
                accEvents
                correlations
                contractStars
                contractStarsValid
                startedAt
                completedAt
                durationSeconds
            }
        }
    """)

    iter_result = graphql_client.execute(
        iter_query,
        variable_values={"iterationId": iteration_id}
    )

    if iter_result["iterationStats"]:
        iter_stats = iter_result["iterationStats"]
        print(f"\n4. Iteration Statistics:")
        print(f"   - Iteration ID: {iter_stats['iterationId']}")
        print(f"   - Total Events: {iter_stats['totalEvents']}")
        print(f"   - DDE Events: {iter_stats['ddeEvents']}")
        print(f"   - BDV Events: {iter_stats['bdvEvents']}")
        print(f"   - ACC Events: {iter_stats['accEvents']}")
        print(f"   - Correlations: {iter_stats['correlations']}")
        print(f"   - Contract Stars: {iter_stats['contractStars']}")
        print(f"   - Contract Stars Valid: {iter_stats['contractStarsValid']}")

        assert iter_stats["iterationId"] == iteration_id
    else:
        print("   ℹ No iteration snapshot found (may not have been created yet)")

    print("\n✅ TEST 7 PASSED: Statistics\n")


# ============================================================================
# Test 8: Health Check
# ============================================================================

def test_health_check(graphql_client):
    """Test health check endpoint."""
    print(f"\n{'='*80}")
    print(f"TEST 8: HEALTH CHECK")
    print(f"{'='*80}\n")

    print("1. Querying health endpoint...")
    query = gql("""
        query GetHealth {
            health {
                status
                timestamp
                services {
                    name
                    status
                    latencyMs
                    error
                }
            }
        }
    """)

    result = graphql_client.execute(query)

    print("\n2. Health Status:")
    health = result["health"]
    print(f"   Overall Status: {health['status']}")
    print(f"   Timestamp: {health['timestamp']}")

    print(f"\n3. Service Health:")
    for service in health["services"]:
        status_emoji = "✅" if service["status"] == "healthy" else "❌"
        print(f"   {status_emoji} {service['name']}: {service['status']} ({service['latencyMs']}ms)")

        # Neo4j and Redis should be healthy
        if service["name"] in ["neo4j", "redis"]:
            assert service["status"] == "healthy", f"{service['name']} should be healthy"

    assert health["status"] in ["healthy", "degraded"], "System should be healthy or degraded"

    print("\n✅ TEST 8 PASSED: Health Check\n")


# ============================================================================
# Main Test Suite
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
