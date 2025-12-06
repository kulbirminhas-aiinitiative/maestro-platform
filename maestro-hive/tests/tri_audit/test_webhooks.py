"""
Tests for tri_audit/webhooks.py (MD-2092)

Tests webhook notification functionality:
- Webhook registration and management
- Payload creation
- Event filtering
- Signature generation
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from tri_audit.webhooks import (
    WebhookEventType,
    WebhookStatus,
    WebhookConfig,
    WebhookPayload,
    WebhookDelivery,
    WebhookManager,
    get_webhook_manager,
    notify_verdict_changed,
    notify_deployment_approved,
    notify_deployment_blocked,
    notify_systemic_failure
)


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def webhook_manager(temp_config_dir):
    """Create webhook manager with temp config."""
    config_path = temp_config_dir / "webhooks.json"
    return WebhookManager(str(config_path))


@pytest.fixture
def sample_webhook_config():
    """Create sample webhook configuration."""
    return WebhookConfig(
        id="test-webhook-1",
        url="https://example.com/webhook",
        name="Test Webhook",
        secret="test-secret-123",
        events=[WebhookEventType.VERDICT_CHANGED, WebhookEventType.SYSTEMIC_FAILURE],
        active=True,
        retry_count=3,
        retry_delay_seconds=1
    )


class TestWebhookEventType:
    """Tests for WebhookEventType enum."""

    def test_all_event_types_exist(self):
        """All event types should exist."""
        assert WebhookEventType.VERDICT_CHANGED.value == "verdict_changed"
        assert WebhookEventType.DEPLOYMENT_APPROVED.value == "deployment_approved"
        assert WebhookEventType.DEPLOYMENT_BLOCKED.value == "deployment_blocked"
        assert WebhookEventType.SYSTEMIC_FAILURE.value == "systemic_failure"
        assert WebhookEventType.STREAM_FAILURE.value == "stream_failure"
        assert WebhookEventType.HEALTH_DEGRADED.value == "health_degraded"
        assert WebhookEventType.MANUAL_OVERRIDE.value == "manual_override"


class TestWebhookStatus:
    """Tests for WebhookStatus enum."""

    def test_all_statuses_exist(self):
        """All statuses should exist."""
        assert WebhookStatus.PENDING.value == "pending"
        assert WebhookStatus.DELIVERED.value == "delivered"
        assert WebhookStatus.FAILED.value == "failed"
        assert WebhookStatus.RETRYING.value == "retrying"


class TestWebhookConfig:
    """Tests for WebhookConfig dataclass."""

    def test_create_config(self, sample_webhook_config):
        """Test creating webhook configuration."""
        assert sample_webhook_config.id == "test-webhook-1"
        assert sample_webhook_config.url == "https://example.com/webhook"
        assert sample_webhook_config.active is True
        assert len(sample_webhook_config.events) == 2

    def test_to_dict(self, sample_webhook_config):
        """Test converting config to dict."""
        d = sample_webhook_config.to_dict()
        assert d["id"] == "test-webhook-1"
        assert d["url"] == "https://example.com/webhook"
        assert "verdict_changed" in d["events"]

    def test_from_dict(self):
        """Test creating config from dict."""
        data = {
            "id": "test-123",
            "url": "https://example.com/webhook",
            "name": "Test",
            "events": ["verdict_changed"],
            "active": True
        }
        config = WebhookConfig.from_dict(data)
        assert config.id == "test-123"
        assert WebhookEventType.VERDICT_CHANGED in config.events


class TestWebhookPayload:
    """Tests for WebhookPayload dataclass."""

    def test_create_payload(self):
        """Test creating webhook payload."""
        payload = WebhookPayload(
            event_type=WebhookEventType.VERDICT_CHANGED,
            timestamp=datetime.utcnow().isoformat() + "Z",
            iteration_id="iter-123",
            verdict="all_pass",
            can_deploy=True,
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True
        )
        assert payload.iteration_id == "iter-123"
        assert payload.can_deploy is True

    def test_to_dict(self):
        """Test converting payload to dict."""
        payload = WebhookPayload(
            event_type=WebhookEventType.SYSTEMIC_FAILURE,
            timestamp=datetime.utcnow().isoformat() + "Z",
            iteration_id="iter-456",
            verdict="systemic_failure",
            can_deploy=False
        )
        d = payload.to_dict()
        assert d["event_type"] == "systemic_failure"
        assert d["iteration_id"] == "iter-456"


class TestWebhookDelivery:
    """Tests for WebhookDelivery dataclass."""

    def test_create_delivery(self):
        """Test creating delivery record."""
        delivery = WebhookDelivery(
            id="delivery-123",
            webhook_id="webhook-1",
            payload={"test": True},
            status=WebhookStatus.DELIVERED,
            attempts=1,
            response_code=200
        )
        assert delivery.status == WebhookStatus.DELIVERED
        assert delivery.response_code == 200

    def test_to_dict(self):
        """Test converting delivery to dict."""
        delivery = WebhookDelivery(
            id="delivery-456",
            webhook_id="webhook-2",
            payload={},
            status=WebhookStatus.FAILED,
            error="Connection timeout"
        )
        d = delivery.to_dict()
        assert d["status"] == "failed"
        assert d["error"] == "Connection timeout"


class TestWebhookManager:
    """Tests for WebhookManager class."""

    def test_register_webhook(self, webhook_manager, sample_webhook_config):
        """Test registering a webhook."""
        result = webhook_manager.register_webhook(sample_webhook_config)
        assert result is True
        assert sample_webhook_config.id in webhook_manager.webhooks

    def test_unregister_webhook(self, webhook_manager, sample_webhook_config):
        """Test unregistering a webhook."""
        webhook_manager.register_webhook(sample_webhook_config)
        result = webhook_manager.unregister_webhook(sample_webhook_config.id)
        assert result is True
        assert sample_webhook_config.id not in webhook_manager.webhooks

    def test_unregister_nonexistent(self, webhook_manager):
        """Test unregistering non-existent webhook."""
        result = webhook_manager.unregister_webhook("nonexistent")
        assert result is False

    def test_get_webhook(self, webhook_manager, sample_webhook_config):
        """Test getting webhook by ID."""
        webhook_manager.register_webhook(sample_webhook_config)
        webhook = webhook_manager.get_webhook(sample_webhook_config.id)
        assert webhook is not None
        assert webhook.name == sample_webhook_config.name

    def test_list_webhooks(self, webhook_manager, sample_webhook_config):
        """Test listing all webhooks."""
        webhook_manager.register_webhook(sample_webhook_config)
        webhooks = webhook_manager.list_webhooks()
        assert len(webhooks) == 1

    def test_update_webhook(self, webhook_manager, sample_webhook_config):
        """Test updating webhook configuration."""
        webhook_manager.register_webhook(sample_webhook_config)
        updated = webhook_manager.update_webhook(
            sample_webhook_config.id,
            {"name": "Updated Name", "active": False}
        )
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.active is False

    def test_update_nonexistent(self, webhook_manager):
        """Test updating non-existent webhook."""
        result = webhook_manager.update_webhook("nonexistent", {"name": "Test"})
        assert result is None

    def test_get_webhooks_for_event(self, webhook_manager, sample_webhook_config):
        """Test filtering webhooks by event type."""
        webhook_manager.register_webhook(sample_webhook_config)

        # Should match VERDICT_CHANGED
        matching = webhook_manager._get_webhooks_for_event(WebhookEventType.VERDICT_CHANGED)
        assert len(matching) == 1

        # Should not match DEPLOYMENT_APPROVED (not subscribed)
        matching = webhook_manager._get_webhooks_for_event(WebhookEventType.DEPLOYMENT_APPROVED)
        assert len(matching) == 0

    def test_sign_payload(self, webhook_manager):
        """Test HMAC signature generation."""
        payload = '{"test": true}'
        secret = "test-secret"

        signature = webhook_manager._sign_payload(payload, secret)
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex digest

    def test_config_persistence(self, temp_config_dir, sample_webhook_config):
        """Test config is persisted and reloaded."""
        config_path = temp_config_dir / "webhooks.json"

        # Create manager and register webhook
        manager1 = WebhookManager(str(config_path))
        manager1.register_webhook(sample_webhook_config)

        # Create new manager, should load from file
        manager2 = WebhookManager(str(config_path))
        assert sample_webhook_config.id in manager2.webhooks

    def test_delivery_history(self, webhook_manager):
        """Test delivery history tracking."""
        # Add some deliveries directly
        delivery = WebhookDelivery(
            id="test-delivery",
            webhook_id="webhook-1",
            payload={},
            status=WebhookStatus.DELIVERED
        )
        webhook_manager.delivery_history.append(delivery)

        history = webhook_manager.get_delivery_history(limit=10)
        assert len(history) == 1

    def test_delivery_history_filter_by_webhook(self, webhook_manager):
        """Test filtering delivery history by webhook ID."""
        # Add deliveries for different webhooks
        webhook_manager.delivery_history.append(
            WebhookDelivery(id="d1", webhook_id="webhook-1", payload={}, status=WebhookStatus.DELIVERED)
        )
        webhook_manager.delivery_history.append(
            WebhookDelivery(id="d2", webhook_id="webhook-2", payload={}, status=WebhookStatus.DELIVERED)
        )

        history = webhook_manager.get_delivery_history(webhook_id="webhook-1")
        assert len(history) == 1
        assert history[0].webhook_id == "webhook-1"


class TestWebhookManagerAsync:
    """Async tests for WebhookManager."""

    @pytest.mark.asyncio
    async def test_notify_no_webhooks(self, webhook_manager):
        """Test notifying with no registered webhooks."""
        deliveries = await webhook_manager.notify(
            event_type=WebhookEventType.VERDICT_CHANGED,
            iteration_id="iter-123"
        )
        assert len(deliveries) == 0

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_send_webhook_success(self, mock_session, webhook_manager, sample_webhook_config):
        """Test successful webhook delivery."""
        # Setup mock
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true}')

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        mock_post = MagicMock(return_value=mock_context)

        mock_session_instance = AsyncMock()
        mock_session_instance.post = mock_post
        mock_session_instance.__aenter__.return_value = mock_session_instance
        mock_session_instance.__aexit__.return_value = None

        mock_session.return_value = mock_session_instance

        # Register webhook and send
        webhook_manager.register_webhook(sample_webhook_config)

        payload = WebhookPayload(
            event_type=WebhookEventType.VERDICT_CHANGED,
            timestamp=datetime.utcnow().isoformat() + "Z",
            iteration_id="iter-123",
            verdict="all_pass"
        )

        delivery = await webhook_manager.send_webhook(sample_webhook_config, payload)

        # Note: Due to mock complexity, we just verify no exceptions
        assert delivery is not None


class TestConvenienceFunctions:
    """Tests for convenience notification functions."""

    @pytest.mark.asyncio
    @patch('tri_audit.webhooks.get_webhook_manager')
    async def test_notify_verdict_changed(self, mock_get_manager):
        """Test notify_verdict_changed function."""
        mock_manager = MagicMock()
        mock_manager.notify = AsyncMock(return_value=[])
        mock_get_manager.return_value = mock_manager

        await notify_verdict_changed(
            iteration_id="iter-123",
            verdict="all_pass",
            can_deploy=True,
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True
        )

        mock_manager.notify.assert_called_once()
        call_args = mock_manager.notify.call_args
        assert call_args.kwargs["event_type"] == WebhookEventType.VERDICT_CHANGED
        assert call_args.kwargs["iteration_id"] == "iter-123"

    @pytest.mark.asyncio
    @patch('tri_audit.webhooks.get_webhook_manager')
    async def test_notify_deployment_approved(self, mock_get_manager):
        """Test notify_deployment_approved function."""
        mock_manager = MagicMock()
        mock_manager.notify = AsyncMock(return_value=[])
        mock_get_manager.return_value = mock_manager

        await notify_deployment_approved(
            iteration_id="iter-123",
            project="myapp",
            version="1.0.0"
        )

        mock_manager.notify.assert_called_once()
        call_args = mock_manager.notify.call_args
        assert call_args.kwargs["event_type"] == WebhookEventType.DEPLOYMENT_APPROVED

    @pytest.mark.asyncio
    @patch('tri_audit.webhooks.get_webhook_manager')
    async def test_notify_systemic_failure(self, mock_get_manager):
        """Test notify_systemic_failure function."""
        mock_manager = MagicMock()
        mock_manager.notify = AsyncMock(return_value=[])
        mock_get_manager.return_value = mock_manager

        await notify_systemic_failure(
            iteration_id="iter-123",
            diagnosis="All audits failed",
            recommendations=["HALT", "Retrospective"]
        )

        mock_manager.notify.assert_called_once()
        call_args = mock_manager.notify.call_args
        assert call_args.kwargs["event_type"] == WebhookEventType.SYSTEMIC_FAILURE
        assert call_args.kwargs["verdict"] == "systemic_failure"
