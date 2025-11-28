"""
GraphQL DataLoaders

Batch loading implementation to prevent N+1 query problem.
"""

import logging
from typing import List, Optional, Dict, Any
from strawberry.dataloader import DataLoader

from ..ics.services.neo4j_writer import Neo4jWriter
from .types import CorrelationLink, ConfidenceScore, ProvenanceType

logger = logging.getLogger(__name__)


class DataLoaderRegistry:
    """
    Registry for all DataLoaders in the application.

    DataLoaders provide batch loading to avoid N+1 queries:
    - Instead of N individual queries, make 1 batch query
    - Cache results within single request
    - Automatic deduplication
    """

    def __init__(self, neo4j_writer: Neo4jWriter):
        """
        Initialize DataLoader registry.

        Args:
            neo4j_writer: Neo4j writer for queries
        """
        self.neo4j_writer = neo4j_writer

        # Event loaders
        self.dde_events = DataLoader(load_fn=self._load_dde_events)
        self.bdv_events = DataLoader(load_fn=self._load_bdv_events)
        self.acc_events = DataLoader(load_fn=self._load_acc_events)

        # Correlation loaders
        self.correlations = DataLoader(load_fn=self._load_correlations)

        # Contract star loaders
        self.contract_stars = DataLoader(load_fn=self._load_contract_stars)

    # ========================================================================
    # DDE Event Loader
    # ========================================================================

    async def _load_dde_events(self, event_ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        Batch load DDE events by IDs.

        Args:
            event_ids: List of event IDs to load

        Returns:
            List of event dicts (or None if not found)
        """
        try:
            with self.neo4j_writer.driver.session(
                database=self.neo4j_writer.database
            ) as session:
                query = """
                UNWIND $event_ids AS event_id
                MATCH (n:DDE_EVENT {event_id: event_id})
                RETURN n
                ORDER BY n.timestamp DESC
                """

                result = session.run(query, event_ids=event_ids)
                events = [dict(record["n"]) for record in result]

                # Create lookup map
                event_map = {event["event_id"]: event for event in events}

                # Return in same order as requested, with None for missing
                return [event_map.get(event_id) for event_id in event_ids]

        except Exception as e:
            logger.error(f"Failed to batch load DDE events: {e}", exc_info=True)
            return [None] * len(event_ids)

    # ========================================================================
    # BDV Event Loader
    # ========================================================================

    async def _load_bdv_events(self, event_ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        Batch load BDV events by IDs.

        Args:
            event_ids: List of event IDs to load

        Returns:
            List of event dicts (or None if not found)
        """
        try:
            with self.neo4j_writer.driver.session(
                database=self.neo4j_writer.database
            ) as session:
                query = """
                UNWIND $event_ids AS event_id
                MATCH (n:BDV_EVENT {event_id: event_id})
                RETURN n
                ORDER BY n.timestamp DESC
                """

                result = session.run(query, event_ids=event_ids)
                events = [dict(record["n"]) for record in result]

                # Create lookup map
                event_map = {event["event_id"]: event for event in events}

                # Return in same order as requested
                return [event_map.get(event_id) for event_id in event_ids]

        except Exception as e:
            logger.error(f"Failed to batch load BDV events: {e}", exc_info=True)
            return [None] * len(event_ids)

    # ========================================================================
    # ACC Event Loader
    # ========================================================================

    async def _load_acc_events(self, event_ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        Batch load ACC events by IDs.

        Args:
            event_ids: List of event IDs to load

        Returns:
            List of event dicts (or None if not found)
        """
        try:
            with self.neo4j_writer.driver.session(
                database=self.neo4j_writer.database
            ) as session:
                query = """
                UNWIND $event_ids AS event_id
                MATCH (n:ACC_EVENT {event_id: event_id})
                RETURN n
                ORDER BY n.timestamp DESC
                """

                result = session.run(query, event_ids=event_ids)
                events = [dict(record["n"]) for record in result]

                # Create lookup map
                event_map = {event["event_id"]: event for event in events}

                # Return in same order as requested
                return [event_map.get(event_id) for event_id in event_ids]

        except Exception as e:
            logger.error(f"Failed to batch load ACC events: {e}", exc_info=True)
            return [None] * len(event_ids)

    # ========================================================================
    # Correlation Loader
    # ========================================================================

    async def _load_correlations(self, event_ids: List[str]) -> List[List[CorrelationLink]]:
        """
        Batch load correlations for events.

        Args:
            event_ids: List of event IDs

        Returns:
            List of correlation lists (one list per event)
        """
        try:
            with self.neo4j_writer.driver.session(
                database=self.neo4j_writer.database
            ) as session:
                # Query all correlations for these events
                query = """
                UNWIND $event_ids AS event_id
                MATCH (source {event_id: event_id})-[r:CORRELATES]->(target)
                RETURN
                    source.event_id AS source_event_id,
                    r.link_id AS link_id,
                    r.source_stream AS source_stream,
                    r.source_entity_id AS source_entity_id,
                    r.target_stream AS target_stream,
                    target.event_id AS target_event_id,
                    r.target_entity_id AS target_entity_id,
                    r.confidence AS confidence,
                    r.provenance AS provenance,
                    r.reasoning AS reasoning,
                    r.link_type AS link_type,
                    r.iteration_id AS iteration_id,
                    r.created_at AS created_at,
                    r.metadata AS metadata
                ORDER BY r.created_at DESC
                """

                result = session.run(query, event_ids=event_ids)

                # Group correlations by source event
                correlations_by_event: Dict[str, List[CorrelationLink]] = {
                    event_id: [] for event_id in event_ids
                }

                for record in result:
                    source_event_id = record["source_event_id"]

                    # Convert to CorrelationLink type
                    correlation = CorrelationLink(
                        link_id=record["link_id"],
                        source_stream=record["source_stream"],
                        source_event_id=source_event_id,
                        source_entity_id=record["source_entity_id"],
                        target_stream=record["target_stream"],
                        target_event_id=record["target_event_id"],
                        target_entity_id=record["target_entity_id"],
                        confidence=ConfidenceScore(
                            value=record["confidence"],
                            provenance=ProvenanceType(record["provenance"]),
                            reasoning=record.get("reasoning"),
                            created_at=record["created_at"]
                        ),
                        link_type=record["link_type"],
                        iteration_id=record["iteration_id"],
                        created_at=record["created_at"],
                        metadata=record.get("metadata")
                    )

                    correlations_by_event[source_event_id].append(correlation)

                # Return in same order as requested
                return [correlations_by_event.get(event_id, []) for event_id in event_ids]

        except Exception as e:
            logger.error(f"Failed to batch load correlations: {e}", exc_info=True)
            return [[] for _ in event_ids]

    # ========================================================================
    # Contract Star Loader
    # ========================================================================

    async def _load_contract_stars(
        self,
        contract_keys: List[tuple[str, str]]
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Batch load contract stars by (contract_id, iteration_id).

        Args:
            contract_keys: List of (contract_id, iteration_id) tuples

        Returns:
            List of contract star dicts (or None if not found)
        """
        try:
            with self.neo4j_writer.driver.session(
                database=self.neo4j_writer.database
            ) as session:
                # Convert tuples to list of dicts for Cypher
                keys_list = [
                    {"contract_id": contract_id, "iteration_id": iteration_id}
                    for contract_id, iteration_id in contract_keys
                ]

                query = """
                UNWIND $keys AS key
                MATCH (star:CONTRACT_STAR {
                    contract_id: key.contract_id,
                    iteration_id: key.iteration_id
                })
                RETURN star
                """

                result = session.run(query, keys=keys_list)
                stars = [dict(record["star"]) for record in result]

                # Create lookup map
                star_map = {
                    (star["contract_id"], star["iteration_id"]): star
                    for star in stars
                }

                # Return in same order as requested
                return [star_map.get(key) for key in contract_keys]

        except Exception as e:
            logger.error(f"Failed to batch load contract stars: {e}", exc_info=True)
            return [None] * len(contract_keys)
