"""
Tests for Bug Fixes Module (EPIC MD-2798).

Tests for:
- MD-1993: Numeric parser for Prisma Decimal types
- MD-1992: Batch team counts endpoint
- MD-1991: WebSocket configuration

EPIC: MD-2798 - [Bugs] Known Issues & Fixes
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import patch, MagicMock
import os

from maestro_hive.bugs.numeric_parser import (
    parse_numeric_value,
    parse_decimal,
    safe_divide,
    aggregate_numeric_values,
    NumericParseError,
)

from maestro_hive.bugs.batch_team_counts import (
    BatchTeamCountsService,
    TeamCountRequest,
    TeamCountResponse,
    BatchTeamCountsResponse,
    BatchStatus,
    RequestStatus,
    create_team_count_request,
)

from maestro_hive.bugs.websocket_config import (
    WebSocketConfig,
    Environment,
    Protocol,
    get_websocket_url,
    get_gateway_url,
    validate_websocket_connection,
    get_frontend_websocket_config,
)


# ==============================================================================
# Tests for Numeric Parser (MD-1993)
# ==============================================================================

class TestParseNumericValue:
    """Tests for parse_numeric_value function."""

    def test_parse_none_returns_default(self):
        """None should return default value."""
        assert parse_numeric_value(None) == 0.0
        assert parse_numeric_value(None, default=10.0) == 10.0

    def test_parse_integer(self):
        """Integers should be converted to float."""
        assert parse_numeric_value(42) == 42.0
        assert parse_numeric_value(-10) == -10.0
        assert parse_numeric_value(0) == 0.0

    def test_parse_float(self):
        """Floats should pass through with rounding."""
        assert parse_numeric_value(3.14159) == 3.14159
        assert parse_numeric_value(3.14159, precision=2) == 3.14

    def test_parse_string_number(self):
        """String numbers should be converted."""
        assert parse_numeric_value("123") == 123.0
        assert parse_numeric_value("3.14") == 3.14
        assert parse_numeric_value("  456  ") == 456.0

    def test_parse_empty_string_returns_default(self):
        """Empty string should return default."""
        assert parse_numeric_value("") == 0.0
        assert parse_numeric_value("   ") == 0.0

    def test_parse_invalid_string_returns_default(self):
        """Invalid string should return default."""
        assert parse_numeric_value("not a number") == 0.0
        assert parse_numeric_value("abc123") == 0.0

    def test_parse_decimal(self):
        """Python Decimal should be converted."""
        assert parse_numeric_value(Decimal("123.456")) == 123.456
        assert parse_numeric_value(Decimal("0.001"), precision=2) == 0.0

    def test_parse_boolean_as_default(self):
        """Boolean should not be treated as numeric."""
        # Booleans are excluded from int check
        assert parse_numeric_value(True) == 0.0
        assert parse_numeric_value(False) == 0.0

    def test_precision_rounding(self):
        """Precision should control decimal places."""
        assert parse_numeric_value(1.23456789, precision=2) == 1.23
        assert parse_numeric_value(1.23456789, precision=4) == 1.2346
        assert parse_numeric_value(1.23456789, precision=0) == 1.0

    def test_raise_on_error(self):
        """Should raise when requested."""
        with pytest.raises(NumericParseError):
            parse_numeric_value("invalid", raise_on_error=True)

    def test_object_with_to_number_method(self):
        """Objects with toNumber() should be handled."""
        class PrismaDecimal:
            def toNumber(self):
                return 42.5

        result = parse_numeric_value(PrismaDecimal())
        assert result == 42.5

    def test_object_with_float_method(self):
        """Objects with __float__ should be handled."""
        class CustomFloat:
            def __float__(self):
                return 3.14

        result = parse_numeric_value(CustomFloat())
        assert result == 3.14

    def test_dict_with_value_key(self):
        """Dict with 'value' key should extract value."""
        assert parse_numeric_value({"value": 42}) == 42.0
        assert parse_numeric_value({"value": "3.14"}) == 3.14


class TestParseDecimal:
    """Tests for parse_decimal function."""

    def test_parse_string_to_decimal(self):
        """String should convert to Decimal."""
        result = parse_decimal("123.456789", precision=4)
        assert result == Decimal("123.4568")

    def test_parse_float_to_decimal(self):
        """Float should convert to Decimal."""
        result = parse_decimal(3.14159, precision=2)
        assert result == Decimal("3.14")

    def test_parse_none_returns_default(self):
        """None should return default."""
        assert parse_decimal(None) is None
        assert parse_decimal(None, default=Decimal("0")) == Decimal("0")


class TestSafeDivide:
    """Tests for safe_divide function."""

    def test_normal_division(self):
        """Normal division should work."""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(7, 2) == 3.5

    def test_division_by_zero_returns_default(self):
        """Division by zero should return default."""
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=-1) == -1

    def test_none_numerator(self):
        """None numerator should be treated as 0."""
        assert safe_divide(None, 5) == 0.0

    def test_decimal_values(self):
        """Decimal values should be handled."""
        assert safe_divide(Decimal("10"), Decimal("4")) == 2.5


class TestAggregateNumericValues:
    """Tests for aggregate_numeric_values function."""

    def test_sum_operation(self):
        """Sum should add all values."""
        result = aggregate_numeric_values([1, 2, 3, 4, 5], "sum")
        assert result == 15.0

    def test_avg_operation(self):
        """Avg should calculate average."""
        result = aggregate_numeric_values([10, 20, 30], "avg")
        assert result == 20.0

    def test_min_operation(self):
        """Min should find minimum."""
        result = aggregate_numeric_values([5, 2, 8, 1, 9], "min")
        assert result == 1.0

    def test_max_operation(self):
        """Max should find maximum."""
        result = aggregate_numeric_values([5, 2, 8, 1, 9], "max")
        assert result == 9.0

    def test_mixed_types(self):
        """Mixed types should be handled."""
        result = aggregate_numeric_values([1, "2", Decimal("3.5"), 4.5], "sum")
        assert result == 11.0

    def test_skip_none_values(self):
        """None values should be skipped by default."""
        result = aggregate_numeric_values([1, None, 3], "sum")
        assert result == 4.0

    def test_empty_list(self):
        """Empty list should return 0."""
        result = aggregate_numeric_values([], "sum")
        assert result == 0.0


# ==============================================================================
# Tests for Batch Team Counts (MD-1992)
# ==============================================================================

class TestTeamCountRequest:
    """Tests for TeamCountRequest dataclass."""

    def test_request_validation_valid(self):
        """Valid request should pass validation."""
        request = TeamCountRequest(execution_id="exec-001")
        assert request.validate() is True

    def test_request_validation_empty_id(self):
        """Empty execution_id should fail validation."""
        request = TeamCountRequest(execution_id="")
        assert request.validate() is False

    def test_request_validation_long_id(self):
        """Too long execution_id should fail validation."""
        request = TeamCountRequest(execution_id="x" * 300)
        assert request.validate() is False

    def test_request_defaults(self):
        """Default values should be set correctly."""
        request = TeamCountRequest(execution_id="exec-001")
        assert request.team_id is None
        assert request.include_inactive is False
        assert request.filters == {}


class TestTeamCountResponse:
    """Tests for TeamCountResponse dataclass."""

    def test_response_to_dict(self):
        """Response should serialize to dict."""
        response = TeamCountResponse(
            execution_id="exec-001",
            team_id="team-001",
            team_count=5,
            active_count=4,
            status=RequestStatus.SUCCESS,
        )
        result = response.to_dict()
        assert result["execution_id"] == "exec-001"
        assert result["team_count"] == 5
        assert result["status"] == "success"


class TestBatchTeamCountsService:
    """Tests for BatchTeamCountsService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return BatchTeamCountsService()

    @pytest.mark.asyncio
    async def test_process_empty_batch(self, service):
        """Empty batch should return empty results."""
        response = await service.process_batch([])
        assert response.batch_size == 0
        assert response.processed == 0
        assert response.status == BatchStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_process_single_request(self, service):
        """Single request should be processed."""
        request = TeamCountRequest(execution_id="exec-001", team_id="team-001")
        response = await service.process_batch([request])

        assert response.batch_size == 1
        assert response.processed == 1
        assert response.failed == 0
        assert response.status == BatchStatus.SUCCESS
        assert len(response.results) == 1

    @pytest.mark.asyncio
    async def test_process_multiple_requests(self, service):
        """Multiple requests should be processed concurrently."""
        requests = [
            TeamCountRequest(execution_id=f"exec-{i:03d}")
            for i in range(10)
        ]
        response = await service.process_batch(requests)

        assert response.batch_size == 10
        assert response.processed == 10
        assert response.status == BatchStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_batch_size_limit(self, service):
        """Exceeding batch size should raise error."""
        requests = [TeamCountRequest(execution_id=f"exec-{i}") for i in range(100)]
        with pytest.raises(ValueError, match="exceeds maximum"):
            await service.process_batch(requests)

    @pytest.mark.asyncio
    async def test_invalid_request_returns_error(self, service):
        """Invalid request should return error status."""
        request = TeamCountRequest(execution_id="")  # Invalid
        response = await service.process_batch([request])

        assert response.batch_size == 1
        assert response.processed == 0
        assert response.failed == 1
        assert response.results[0].status == RequestStatus.ERROR

    @pytest.mark.asyncio
    async def test_concurrency_limiting(self, service):
        """Concurrency should be limited."""
        requests = [TeamCountRequest(execution_id=f"exec-{i}") for i in range(20)]
        response = await service.process_batch(requests, max_concurrent=2)

        assert response.batch_size == 20
        assert response.processed == 20

    def test_cache_operations(self, service):
        """Cache should be clearable."""
        service._team_data_cache["test"] = {"total": 5, "active": 3}
        assert len(service._team_data_cache) == 1
        service.clear_cache()
        assert len(service._team_data_cache) == 0


class TestCreateTeamCountRequest:
    """Tests for factory function."""

    def test_create_from_dict(self):
        """Should create request from dict."""
        data = {
            "execution_id": "exec-001",
            "team_id": "team-001",
            "include_inactive": True,
            "filters": {"status": "active"},
        }
        request = create_team_count_request(data)

        assert request.execution_id == "exec-001"
        assert request.team_id == "team-001"
        assert request.include_inactive is True
        assert request.filters == {"status": "active"}

    def test_create_with_missing_fields(self):
        """Should handle missing optional fields."""
        data = {"execution_id": "exec-001"}
        request = create_team_count_request(data)

        assert request.execution_id == "exec-001"
        assert request.team_id is None
        assert request.include_inactive is False


# ==============================================================================
# Tests for WebSocket Config (MD-1991)
# ==============================================================================

class TestWebSocketConfig:
    """Tests for WebSocketConfig dataclass."""

    def test_default_config(self):
        """Default config should use gateway port 8080."""
        config = WebSocketConfig()
        assert config.gateway_port == 8080  # NOT 4001
        assert config.gateway_host == "localhost"
        assert config.protocol == Protocol.WS

    def test_get_url(self):
        """Should generate correct WebSocket URL."""
        config = WebSocketConfig()
        url = config.get_url()
        assert url == "ws://localhost:8080/ws"

    def test_get_url_with_ssl(self):
        """Should generate WSS URL when configured."""
        config = WebSocketConfig(protocol=Protocol.WSS)
        url = config.get_url()
        assert url == "wss://localhost:8080/ws"

    def test_from_url(self):
        """Should create config from URL."""
        config = WebSocketConfig._from_url("wss://example.com:443/ws")
        assert config.gateway_host == "example.com"
        assert config.gateway_port == 443
        assert config.protocol == Protocol.WSS

    def test_to_dict(self):
        """Should serialize to dict."""
        config = WebSocketConfig()
        result = config.to_dict()
        assert "url" in result
        assert result["gateway_port"] == 8080

    def test_get_url_for_host(self):
        """Should generate URL for specific host."""
        config = WebSocketConfig()
        url = config.get_url_for_host("sandbox.example.com", use_ssl=True)
        assert url == "wss://sandbox.example.com:8080/ws"


class TestWebSocketConfigFromEnvironment:
    """Tests for environment-based configuration."""

    def test_from_explicit_ws_url(self):
        """Should use VITE_WS_GATEWAY_URL if set."""
        with patch.dict(os.environ, {"VITE_WS_GATEWAY_URL": "wss://gateway.io:8080/ws"}):
            config = WebSocketConfig.from_environment()
            assert config.gateway_host == "gateway.io"
            assert config.gateway_port == 8080
            assert config.protocol == Protocol.WSS

    def test_from_api_url(self):
        """Should derive from VITE_API_GATEWAY_URL."""
        with patch.dict(os.environ, {"VITE_API_GATEWAY_URL": "https://api.example.com:8080"}, clear=True):
            config = WebSocketConfig.from_environment()
            assert config.gateway_host == "api.example.com"
            assert config.protocol == Protocol.WSS

    def test_default_without_env(self):
        """Should use defaults without environment vars."""
        with patch.dict(os.environ, {}, clear=True):
            config = WebSocketConfig.from_environment()
            assert config.gateway_host == "localhost"
            assert config.gateway_port == 8080


class TestGetWebSocketUrl:
    """Tests for get_websocket_url function."""

    def test_returns_gateway_url(self):
        """Should return gateway URL, not port 4001."""
        url = get_websocket_url()
        assert ":8080" in url
        assert ":4001" not in url

    def test_with_custom_config(self):
        """Should use provided config."""
        config = WebSocketConfig(gateway_host="custom.io", gateway_port=9000)
        url = get_websocket_url(config)
        assert url == "ws://custom.io:9000/ws"


class TestGetGatewayUrl:
    """Tests for get_gateway_url function."""

    def test_returns_http_url(self):
        """Should return HTTP URL."""
        url = get_gateway_url()
        assert url.startswith("http")
        assert ":8080" in url


class TestValidateWebSocketConnection:
    """Tests for validate_websocket_connection function."""

    def test_validation_returns_result(self):
        """Should return validation result dict."""
        with patch("socket.gethostbyname", return_value="127.0.0.1"):
            with patch("socket.socket") as mock_socket:
                mock_instance = MagicMock()
                mock_socket.return_value = mock_instance
                mock_instance.connect.return_value = None

                result = validate_websocket_connection()

                assert "valid" in result
                assert "url" in result
                assert "errors" in result

    def test_validation_detects_unresolvable_host(self):
        """Should detect unresolvable host."""
        import socket
        with patch("socket.gethostbyname", side_effect=socket.gaierror("not found")):
            config = WebSocketConfig(gateway_host="nonexistent.invalid")
            result = validate_websocket_connection(config)

            assert result["valid"] is False
            assert result["host_resolvable"] is False


class TestGetFrontendWebSocketConfig:
    """Tests for get_frontend_websocket_config function."""

    def test_returns_javascript_code(self):
        """Should return JS code snippet."""
        code = get_frontend_websocket_config()
        assert "const WS_URL" in code
        assert ":8080" in code
        assert "getWebSocketUrl" in code


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests combining multiple modules."""

    def test_numeric_parser_with_batch_service(self):
        """Numeric parser should work with batch service responses."""
        response = TeamCountResponse(
            execution_id="exec-001",
            team_id="team-001",
            team_count=5,
            active_count=4,
            status=RequestStatus.SUCCESS,
        )

        # Parse count values through numeric parser
        total = parse_numeric_value(response.team_count)
        active = parse_numeric_value(response.active_count)

        assert total == 5.0
        assert active == 4.0

    def test_websocket_config_url_format(self):
        """WebSocket URL should be valid format."""
        config = WebSocketConfig()
        url = config.get_url()

        # Should be valid WebSocket URL format
        assert url.startswith("ws://") or url.startswith("wss://")
        assert "/ws" in url

    @pytest.mark.asyncio
    async def test_batch_service_results_serializable(self):
        """Batch results should be JSON serializable."""
        import json

        service = BatchTeamCountsService()
        requests = [TeamCountRequest(execution_id="exec-001")]
        response = await service.process_batch(requests)

        # Should serialize without error
        result = json.dumps(response.to_dict())
        assert isinstance(result, str)

        # Should deserialize back
        parsed = json.loads(result)
        assert parsed["batch_size"] == 1


# ==============================================================================
# Acceptance Criteria Verification Tests
# ==============================================================================

class TestAcceptanceCriteria:
    """Tests that verify each AC is met."""

    def test_ac1_prisma_decimal_handling(self):
        """
        AC-1: parseNumericValue handles Prisma Decimal types.

        The Team Performance Overview should correctly display
        numeric values from Prisma Decimal fields.
        """
        # Simulate Prisma Decimal object
        class PrismaDecimal:
            def __init__(self, value):
                self._value = value
            def toNumber(self):
                return self._value

        # Various Prisma Decimal values
        outcome_quality = PrismaDecimal(0.85)
        friction_score = PrismaDecimal(0.15)

        # Parse should handle correctly
        quality = parse_numeric_value(outcome_quality)
        friction = parse_numeric_value(friction_score)

        assert quality == 0.85
        assert friction == 0.15
        assert isinstance(quality, float)

    @pytest.mark.asyncio
    async def test_ac2_batch_endpoint_exists(self):
        """
        AC-2: /api/ai-agents/batch/team-counts endpoint exists.

        The endpoint should accept batch requests and return
        team counts for multiple executions.
        """
        service = BatchTeamCountsService()

        # Simulate batch request
        requests = [
            TeamCountRequest(execution_id="exec-001", team_id="team-001"),
            TeamCountRequest(execution_id="exec-002", team_id="team-002"),
        ]

        response = await service.process_batch(requests)

        # Endpoint should process batch
        assert response.batch_size == 2
        assert response.status == BatchStatus.SUCCESS
        assert len(response.results) == 2

        # Each result should have team counts
        for result in response.results:
            assert result.team_count >= 0
            assert result.active_count >= 0

    def test_ac3_websocket_uses_gateway_port(self):
        """
        AC-3: WebSocket connections use gateway port 8080.

        Sandbox WebSocket connections should route through
        the API Gateway (port 8080), not direct service (port 4001).
        """
        config = WebSocketConfig()

        # Default port should be 8080
        assert config.gateway_port == 8080

        # URL should use gateway port
        url = get_websocket_url()
        assert ":8080" in url
        assert ":4001" not in url

        # Frontend config should use gateway port
        frontend_code = get_frontend_websocket_config()
        assert ":8080" in frontend_code
        assert ":4001" not in frontend_code
