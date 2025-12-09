"""
Bug Fixes Module for EPIC MD-2798.

This module contains fixes for known issues:
- MD-1993: Prisma Decimal parsing in Team Performance Overview
- MD-1992: Missing /api/ai-agents/batch/team-counts endpoint
- MD-1991: Sandbox WebSocket connection configuration

EPIC: MD-2798 - [Bugs] Known Issues & Fixes
"""

from .numeric_parser import (
    parse_numeric_value,
    parse_decimal,
    safe_divide,
    aggregate_numeric_values,
    NumericParseError,
)

from .batch_team_counts import (
    BatchTeamCountsService,
    TeamCountRequest,
    TeamCountResponse,
    BatchTeamCountsResponse,
    BatchStatus,
    RequestStatus,
    create_team_count_request,
)

from .websocket_config import (
    WebSocketConfig,
    get_websocket_url,
    get_gateway_url,
    validate_websocket_connection,
    get_frontend_websocket_config,
    Environment,
    Protocol,
)

__all__ = [
    # Numeric Parser (MD-1993)
    "parse_numeric_value",
    "parse_decimal",
    "safe_divide",
    "aggregate_numeric_values",
    "NumericParseError",
    # Batch Team Counts (MD-1992)
    "BatchTeamCountsService",
    "TeamCountRequest",
    "TeamCountResponse",
    "BatchTeamCountsResponse",
    "BatchStatus",
    "RequestStatus",
    "create_team_count_request",
    # WebSocket Config (MD-1991)
    "WebSocketConfig",
    "get_websocket_url",
    "get_gateway_url",
    "validate_websocket_connection",
    "get_frontend_websocket_config",
    "Environment",
    "Protocol",
]
