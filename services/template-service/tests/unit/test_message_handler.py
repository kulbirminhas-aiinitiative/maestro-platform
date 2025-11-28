"""
Unit tests for TemplateMessageHandler.
"""

import asyncio
import json
from uuid import uuid4

import pytest

from template_service.message_handler import (
    TemplateMessageHandler,
    TemplateRequest,
    TemplateResult,
    TemplateUsageEvent,
)


@pytest.mark.asyncio
async def test_template_request_creation():
    """Test creating a TemplateRequest."""
    request = TemplateRequest(
        template_id="test-template-123",
        operation="retrieve",
        tenant_id="tenant-123",
        user_id="user-456",
        parameters={"format": "json"}
    )

    assert request.template_id == "test-template-123"
    assert request.operation == "retrieve"
    assert request.tenant_id == "tenant-123"
    assert request.user_id == "user-456"
    assert request.parameters["format"] == "json"
    assert request.request_id is not None


@pytest.mark.asyncio
async def test_template_result_creation():
    """Test creating a TemplateResult."""
    result = TemplateResult(
        request_id="req-123",
        template_id="template-456",
        status="success",
        result={"name": "Test Template"},
        duration_ms=150
    )

    assert result.request_id == "req-123"
    assert result.template_id == "template-456"
    assert result.status == "success"
    assert result.result["name"] == "Test Template"
    assert result.duration_ms == 150
    assert result.error is None


@pytest.mark.asyncio
async def test_template_usage_event_creation():
    """Test creating a TemplateUsageEvent."""
    event = TemplateUsageEvent(
        template_id="template-789",
        tenant_id="tenant-123",
        user_id="user-456",
        operation="search",
        success=True,
        duration_ms=200
    )

    assert event.template_id == "template-789"
    assert event.tenant_id == "tenant-123"
    assert event.user_id == "user-456"
    assert event.operation == "search"
    assert event.success is True
    assert event.duration_ms == 200
    assert event.event_id is not None


@pytest.mark.asyncio
async def test_message_handler_initialization(template_message_handler):
    """Test TemplateMessageHandler initialization and start."""
    handler = template_message_handler

    assert handler.is_running
    assert handler.redis_client is not None


@pytest.mark.asyncio
async def test_publish_and_consume_request(template_message_handler, test_tenant_id, test_user_id):
    """Test publishing and consuming a template request."""
    handler = template_message_handler

    # Create test request
    request = TemplateRequest(
        template_id="test-template-123",
        operation="retrieve",
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        parameters={}
    )

    # Publish request
    message_id = await handler.publish_request(request)
    assert message_id is not None

    # Wait for processing
    await asyncio.sleep(2)

    # Check results stream for response
    results = await handler.redis_client.xread(
        streams={handler.stream_results: "0"},
        count=1
    )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_search_operation(template_message_handler, test_tenant_id, test_user_id):
    """Test search operation."""
    handler = template_message_handler

    # Create search request
    request = TemplateRequest(
        operation="search",
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        parameters={"category": "backend_developer"}
    )

    # Publish request
    await handler.publish_request(request)

    # Wait for processing
    await asyncio.sleep(2)

    # Verify result was published
    results = await handler.redis_client.xread(
        streams={handler.stream_results: "0"},
        count=10
    )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_error_handling(template_message_handler, test_tenant_id, test_user_id):
    """Test error handling for invalid operations."""
    handler = template_message_handler

    # Create request with invalid operation
    request = TemplateRequest(
        operation="invalid_operation",
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        parameters={}
    )

    # Publish request
    await handler.publish_request(request)

    # Wait for processing
    await asyncio.sleep(2)

    # Check results for error
    results = await handler.redis_client.xread(
        streams={handler.stream_results: "0"},
        count=10
    )

    # Should have error result
    assert len(results) > 0


@pytest.mark.asyncio
async def test_usage_tracking(template_message_handler, test_tenant_id, test_user_id):
    """Test usage event tracking."""
    handler = template_message_handler

    # Create request
    request = TemplateRequest(
        template_id="test-template-123",
        operation="retrieve",
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        parameters={}
    )

    # Publish request
    await handler.publish_request(request)

    # Wait for processing
    await asyncio.sleep(2)

    # Check usage stream
    usage_events = await handler.redis_client.xread(
        streams={handler.stream_usage: "0"},
        count=10
    )

    assert len(usage_events) > 0
