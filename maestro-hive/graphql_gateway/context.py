"""
GraphQL Context

Dependency injection context for GraphQL resolvers.
Provides access to services, dataloaders, and request state.
"""

import logging
from typing import Optional
from dataclasses import dataclass
from fastapi import Request

from ..ics.services.neo4j_writer import Neo4jWriter
from ..ics.services.idempotency_checker import IdempotencyChecker
from ..ics.services.correlation_engine import CorrelationEngine
from ..ics.config import config
from .dataloaders import DataLoaderRegistry

logger = logging.getLogger(__name__)


@dataclass
class Context:
    """
    GraphQL context for resolvers.

    Provides access to:
    - Neo4j writer for querying graph
    - Redis client for caching
    - DataLoaders for batch loading
    - Request state (user, auth, etc.)
    """

    # Services
    neo4j_writer: Neo4jWriter
    idempotency_checker: IdempotencyChecker
    correlation_engine: CorrelationEngine

    # DataLoaders
    dataloaders: DataLoaderRegistry

    # Request state
    request: Optional[Request] = None
    user_id: Optional[str] = None
    is_authenticated: bool = False
    roles: list[str] = None

    def __post_init__(self):
        """Initialize roles if not provided."""
        if self.roles is None:
            self.roles = []


# Global service instances (initialized at startup)
_neo4j_writer: Optional[Neo4jWriter] = None
_idempotency_checker: Optional[IdempotencyChecker] = None
_correlation_engine: Optional[CorrelationEngine] = None


def initialize_services():
    """
    Initialize global service instances.

    Called at application startup (in server.py lifespan).
    """
    global _neo4j_writer, _idempotency_checker, _correlation_engine

    try:
        logger.info("Initializing GraphQL context services...")

        # Initialize Neo4j writer
        _neo4j_writer = Neo4jWriter()
        logger.info("Neo4j writer initialized")

        # Initialize idempotency checker
        _idempotency_checker = IdempotencyChecker()
        logger.info("Idempotency checker initialized")

        # Initialize correlation engine
        _correlation_engine = CorrelationEngine()
        logger.info("Correlation engine initialized")

        logger.info("GraphQL context services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise


async def close_services():
    """
    Close global service instances.

    Called at application shutdown (in server.py lifespan).
    """
    global _neo4j_writer, _idempotency_checker, _correlation_engine

    try:
        logger.info("Closing GraphQL context services...")

        if _neo4j_writer:
            _neo4j_writer.close()
            _neo4j_writer = None

        if _idempotency_checker:
            await _idempotency_checker.close()
            _idempotency_checker = None

        if _correlation_engine:
            _correlation_engine = None

        logger.info("GraphQL context services closed")

    except Exception as e:
        logger.error(f"Error closing services: {e}", exc_info=True)


async def get_context(request: Request = None) -> Context:
    """
    Get GraphQL context for request.

    Creates a new context with:
    - Global service instances
    - Fresh DataLoader registry per request
    - Request state (auth, user, etc.)

    Args:
        request: FastAPI request

    Returns:
        Context instance
    """
    # Check services are initialized
    if not _neo4j_writer or not _idempotency_checker or not _correlation_engine:
        raise RuntimeError(
            "Services not initialized. Call initialize_services() at startup."
        )

    # Create fresh DataLoader registry for this request
    dataloaders = DataLoaderRegistry(neo4j_writer=_neo4j_writer)

    # Extract auth info from request (placeholder for Week 8)
    user_id = None
    is_authenticated = False
    roles = []

    if request:
        # TODO: Extract from JWT token in Authorization header
        # auth_header = request.headers.get("Authorization")
        # if auth_header:
        #     token = auth_header.replace("Bearer ", "")
        #     payload = decode_jwt(token)
        #     user_id = payload.get("sub")
        #     is_authenticated = True
        #     roles = payload.get("roles", [])
        pass

    # Create context
    return Context(
        neo4j_writer=_neo4j_writer,
        idempotency_checker=_idempotency_checker,
        correlation_engine=_correlation_engine,
        dataloaders=dataloaders,
        request=request,
        user_id=user_id,
        is_authenticated=is_authenticated,
        roles=roles
    )
