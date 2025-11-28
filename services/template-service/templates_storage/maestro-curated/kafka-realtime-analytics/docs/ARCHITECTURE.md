# System Architecture

## Overview

The Real-Time Analytics Platform is a distributed system designed for high-throughput data ingestion, stream processing, and real-time analytics using Apache Kafka as the backbone.

## Architecture Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────────┐
│   Clients   │────────>│   Producer   │────────>│     Kafka       │
│             │         │   Service    │         │   (Topics)      │
└─────────────┘         └──────────────┘         └─────────────────┘
                                                          │
                                                          │
                                                          v
                                                  ┌─────────────────┐
                                                  │     Stream      │
                                                  │   Processor     │
                                                  └─────────────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────┐
                        │                                 │         │
                        v                                 v         v
                ┌──────────────┐                  ┌──────────┐  ┌─────────┐
                │  PostgreSQL  │                  │  Redis   │  │ Anomaly │
                │ (Aggregated) │                  │ (Cache)  │  │Detection│
                └──────────────┘                  └──────────┘  └─────────┘
                        │
                        v
                ┌──────────────┐         ┌─────────────┐
                │  API Service │<────────│  Dashboard  │
                └──────────────┘         └─────────────┘
                        │
                        v
                ┌──────────────┐
                │  Prometheus  │
                │   Grafana    │
                └──────────────┘
```

## Components

### 1. Producer Service
- **Purpose**: Data ingestion endpoint
- **Technology**: Flask (Python), Kafka Producer
- **Port**: 8080
- **Features**:
  - REST API for event ingestion
  - Batch processing support
  - Traffic simulation for testing
  - Message enrichment and validation

### 2. Stream Processor
- **Purpose**: Real-time stream processing and analytics
- **Technology**: Kafka Streams (Python), Custom Processing
- **Features**:
  - Windowed aggregations (5-minute windows)
  - Real-time metrics calculation
  - Anomaly detection
  - Multiple event type support

### 3. API Service
- **Purpose**: Query interface for analytics data
- **Technology**: Flask (Python), REST API
- **Port**: 8081
- **Features**:
  - Historical event queries
  - Aggregation queries
  - Real-time metrics access
  - Dashboard data endpoints

### 4. Apache Kafka
- **Purpose**: Message broker and stream backbone
- **Configuration**:
  - 3 broker replicas (production)
  - Zookeeper for coordination
  - Multiple topics by event type
  - Configurable retention and replication

### 5. PostgreSQL
- **Purpose**: Persistent storage for events and aggregations
- **Tables**:
  - `raw_events`: All ingested events
  - `aggregations`: Computed window aggregations
  - `anomalies`: Detected anomalies
  - `system_metrics`: System monitoring data

### 6. Redis
- **Purpose**: High-speed cache for real-time metrics
- **Usage**:
  - Real-time event counters
  - Regional distribution tracking
  - Sliding window data
  - Session caching

### 7. Monitoring Stack
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Features**:
  - Service health monitoring
  - Performance metrics
  - Custom dashboards
  - Alerting (configurable)

## Data Flow

1. **Ingestion**:
   - Clients send events to Producer Service via REST API
   - Producer enriches events with metadata and timestamps
   - Events published to Kafka topics by event type

2. **Processing**:
   - Stream Processor consumes from Kafka topics
   - Events added to windowed aggregations
   - Real-time metrics updated in Redis
   - Completed windows stored in PostgreSQL
   - Anomalies detected and logged

3. **Query**:
   - API Service queries PostgreSQL for historical data
   - Redis accessed for real-time metrics
   - Results returned to clients/dashboards

4. **Monitoring**:
   - Services expose Prometheus metrics
   - Grafana visualizes system health
   - Alerts triggered on anomalies or failures

## Scalability

### Horizontal Scaling
- **Producer**: Scale replicas based on ingestion load
- **Stream Processor**: Scale consumers within consumer group
- **API**: Scale replicas behind load balancer
- **Kafka**: Add brokers for higher throughput

### Vertical Scaling
- Increase resources for database and cache
- Adjust JVM settings for Kafka brokers
- Tune application workers and threads

## Performance Characteristics

- **Throughput**: 100K+ events/second (with 3 Kafka brokers)
- **Latency**: <100ms end-to-end (ingestion to availability)
- **Window Processing**: 5-minute tumbling windows
- **Data Retention**: 30 days (configurable)

## High Availability

- **Kafka**: Replication factor of 3
- **PostgreSQL**: StatefulSet with persistent volumes
- **Redis**: Persistence with AOF
- **Services**: Multiple replicas with health checks

## Security Considerations

- Network policies for pod-to-pod communication
- Secrets management for credentials
- TLS encryption for external endpoints
- RBAC for Kubernetes resources
- Input validation and sanitization

## Monitoring and Observability

- Health check endpoints on all services
- Structured logging with correlation IDs
- Distributed tracing (can be added with Jaeger)
- Custom business metrics
- Performance profiling

## Disaster Recovery

- Regular PostgreSQL backups
- Kafka topic replication
- Redis persistence snapshots
- Infrastructure as Code for quick rebuild
- Multi-region deployment (optional)