"""
Ingestion & Correlation Service (ICS)

Sprint 1: Event-Driven Foundation for Tri-Modal Mission Control

The ICS is responsible for:
1. Consuming events from Kafka (DDE, BDV, ACC streams)
2. Validating events against Avro schemas
3. Correlating events across streams using provenance tracking
4. Writing to Neo4j Unified Graph Model (UGM)
5. Updating CQRS projections in Redis
6. Recording metrics in TimescaleDB
7. Handling failures with categorized DLQ
8. Ensuring idempotency with Redis deduplication
"""

__version__ = "1.0.0"
__author__ = "Maestro Platform Engineering"
