"""
ICS Configuration

Environment-based configuration for the Ingestion & Correlation Service.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    """Kafka connection configuration."""
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    schema_registry_url: str = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    consumer_group_id: str = "ics-processor"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False  # Manual commit for exactly-once
    isolation_level: str = "read_committed"  # For transactional reads


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "maestro_dev")
    database: str = "neo4j"
    max_connection_pool_size: int = 50
    connection_timeout: int = 30


@dataclass
class RedisConfig:
    """Redis connection configuration."""
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    decode_responses: bool = False  # Binary for performance


@dataclass
class TimescaleDBConfig:
    """TimescaleDB connection configuration."""
    host: str = os.getenv("TIMESCALEDB_HOST", "localhost")
    port: int = int(os.getenv("TIMESCALEDB_PORT", "5432"))
    user: str = os.getenv("TIMESCALEDB_USER", "maestro")
    password: str = os.getenv("TIMESCALEDB_PASSWORD", "maestro_dev")
    database: str = os.getenv("TIMESCALEDB_DB", "trimodal_metrics")
    pool_size: int = 20
    max_overflow: int = 10


@dataclass
class OpenTelemetryConfig:
    """OpenTelemetry configuration."""
    jaeger_agent_host: str = os.getenv("JAEGER_AGENT_HOST", "localhost")
    jaeger_agent_port: int = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
    otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    service_name: str = "ics"
    service_version: str = "1.0.0"


@dataclass
class ICSConfig:
    """Main ICS configuration."""
    kafka: KafkaConfig = KafkaConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    redis: RedisConfig = RedisConfig()
    timescaledb: TimescaleDBConfig = TimescaleDBConfig()
    otel: OpenTelemetryConfig = OpenTelemetryConfig()

    # Topics
    dde_topic: str = "trimodal.events.dde"
    bdv_topic: str = "trimodal.events.bdv"
    acc_topic: str = "trimodal.events.acc"
    dlq_topic: str = "trimodal.events.dlq"

    # Processing settings
    batch_size: int = 100
    batch_timeout_ms: int = 1000
    max_retries: int = 3
    retry_backoff_ms: int = 1000

    # Idempotency
    idempotency_ttl_days: int = 7

    # Correlation confidence thresholds
    explicit_id_confidence: float = 1.0
    file_path_exact_confidence: float = 0.9
    file_path_fuzzy_confidence: float = 0.7
    tag_match_confidence: float = 0.8
    heuristic_confidence: float = 0.5

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        """Validate configuration."""
        assert 0 <= self.explicit_id_confidence <= 1.0
        assert 0 <= self.file_path_exact_confidence <= 1.0
        assert 0 <= self.file_path_fuzzy_confidence <= 1.0
        assert 0 <= self.tag_match_confidence <= 1.0
        assert 0 <= self.heuristic_confidence <= 1.0


# Global configuration instance
config = ICSConfig()
