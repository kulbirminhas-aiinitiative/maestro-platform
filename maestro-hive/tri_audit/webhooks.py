"""
Webhook Notifications for Tri-Modal Audit

Provides webhook notification functionality:
- Verdict change notifications
- Deployment gate status updates
- Systemic failure alerts
- Configurable webhook endpoints

Part of MD-2043: Trimodal Convergence Completion
Task: MD-2092 - Add webhook notifications for verdicts

Author: Claude Code Agent
Date: 2025-12-02
"""

import json
import asyncio
import hashlib
import hmac
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import queue

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

# Import tri-audit types
try:
    from tri_audit.tri_audit import TriModalVerdict, TriAuditResult
except ImportError:
    TriModalVerdict = None
    TriAuditResult = None


class WebhookEventType(str, Enum):
    """Types of webhook events."""
    VERDICT_CHANGED = "verdict_changed"
    DEPLOYMENT_APPROVED = "deployment_approved"
    DEPLOYMENT_BLOCKED = "deployment_blocked"
    SYSTEMIC_FAILURE = "systemic_failure"
    STREAM_FAILURE = "stream_failure"
    HEALTH_DEGRADED = "health_degraded"
    MANUAL_OVERRIDE = "manual_override"


class WebhookStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""
    id: str
    url: str
    name: str
    secret: Optional[str] = None  # For HMAC signature
    events: List[WebhookEventType] = field(default_factory=lambda: list(WebhookEventType))
    active: bool = True
    retry_count: int = 3
    retry_delay_seconds: int = 30
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["events"] = [e.value if isinstance(e, WebhookEventType) else e for e in self.events]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookConfig":
        events = [
            WebhookEventType(e) if isinstance(e, str) else e
            for e in data.get("events", [])
        ]
        return cls(
            id=data["id"],
            url=data["url"],
            name=data["name"],
            secret=data.get("secret"),
            events=events,
            active=data.get("active", True),
            retry_count=data.get("retry_count", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 30),
            headers=data.get("headers", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat() + "Z")
        )


@dataclass
class WebhookPayload:
    """Payload for webhook delivery."""
    event_type: WebhookEventType
    timestamp: str
    iteration_id: str
    verdict: Optional[str] = None
    previous_verdict: Optional[str] = None
    can_deploy: bool = False
    dde_passed: Optional[bool] = None
    bdv_passed: Optional[bool] = None
    acc_passed: Optional[bool] = None
    diagnosis: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["event_type"] = self.event_type.value if isinstance(self.event_type, WebhookEventType) else self.event_type
        return result


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""
    id: str
    webhook_id: str
    payload: Dict[str, Any]
    status: WebhookStatus
    attempts: int = 0
    last_attempt: Optional[str] = None
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value if isinstance(self.status, WebhookStatus) else self.status
        return result


class WebhookManager:
    """
    Manages webhook configurations and deliveries.

    Features:
    - Register/unregister webhooks
    - Queue and deliver webhook payloads
    - Retry failed deliveries
    - Track delivery history
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize webhook manager."""
        self.config_path = Path(config_path or "data/tri_audit/webhooks.json")
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.delivery_queue: queue.Queue = queue.Queue()
        self.delivery_history: List[WebhookDelivery] = []
        self._lock = threading.RLock()
        self._load_config()

    def _load_config(self):
        """Load webhook configurations from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                for webhook_data in data.get("webhooks", []):
                    webhook = WebhookConfig.from_dict(webhook_data)
                    self.webhooks[webhook.id] = webhook
            except Exception as e:
                print(f"Error loading webhook config: {e}")

    def _save_config(self):
        """Save webhook configurations to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            data = {
                "webhooks": [w.to_dict() for w in self.webhooks.values()],
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)

    def register_webhook(self, config: WebhookConfig) -> bool:
        """
        Register a new webhook.

        Args:
            config: WebhookConfig for the webhook

        Returns:
            True if registered successfully
        """
        with self._lock:
            self.webhooks[config.id] = config
            self._save_config()
            return True

    def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a webhook.

        Args:
            webhook_id: ID of webhook to unregister

        Returns:
            True if unregistered successfully
        """
        with self._lock:
            if webhook_id in self.webhooks:
                del self.webhooks[webhook_id]
                self._save_config()
                return True
            return False

    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get webhook by ID."""
        return self.webhooks.get(webhook_id)

    def list_webhooks(self) -> List[WebhookConfig]:
        """List all registered webhooks."""
        return list(self.webhooks.values())

    def update_webhook(self, webhook_id: str, updates: Dict[str, Any]) -> Optional[WebhookConfig]:
        """
        Update webhook configuration.

        Args:
            webhook_id: ID of webhook to update
            updates: Dict of fields to update

        Returns:
            Updated WebhookConfig or None
        """
        with self._lock:
            if webhook_id not in self.webhooks:
                return None

            webhook = self.webhooks[webhook_id]

            if "url" in updates:
                webhook.url = updates["url"]
            if "name" in updates:
                webhook.name = updates["name"]
            if "secret" in updates:
                webhook.secret = updates["secret"]
            if "events" in updates:
                webhook.events = [
                    WebhookEventType(e) if isinstance(e, str) else e
                    for e in updates["events"]
                ]
            if "active" in updates:
                webhook.active = updates["active"]
            if "retry_count" in updates:
                webhook.retry_count = updates["retry_count"]
            if "headers" in updates:
                webhook.headers = updates["headers"]

            self._save_config()
            return webhook

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Create HMAC signature for payload."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def _get_webhooks_for_event(self, event_type: WebhookEventType) -> List[WebhookConfig]:
        """Get webhooks that subscribe to an event type."""
        return [
            w for w in self.webhooks.values()
            if w.active and event_type in w.events
        ]

    async def send_webhook(
        self,
        webhook: WebhookConfig,
        payload: WebhookPayload,
        attempt: int = 1
    ) -> WebhookDelivery:
        """
        Send webhook delivery.

        Args:
            webhook: WebhookConfig to send to
            payload: WebhookPayload to deliver
            attempt: Current attempt number

        Returns:
            WebhookDelivery with result
        """
        import aiohttp

        delivery_id = f"delivery-{webhook.id}-{datetime.utcnow().timestamp()}"
        payload_dict = payload.to_dict()
        payload_json = json.dumps(payload_dict)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": payload.event_type.value,
            "X-Webhook-Delivery": delivery_id,
            **webhook.headers
        }

        # Add signature if secret configured
        if webhook.secret:
            signature = self._sign_payload(payload_json, webhook.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            payload=payload_dict,
            status=WebhookStatus.PENDING,
            attempts=attempt,
            last_attempt=datetime.utcnow().isoformat() + "Z"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.url,
                    data=payload_json,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    delivery.response_code = response.status
                    delivery.response_body = await response.text()

                    if 200 <= response.status < 300:
                        delivery.status = WebhookStatus.DELIVERED
                    else:
                        delivery.status = WebhookStatus.FAILED
                        delivery.error = f"HTTP {response.status}"

        except asyncio.TimeoutError:
            delivery.status = WebhookStatus.FAILED
            delivery.error = "Request timed out"
        except Exception as e:
            delivery.status = WebhookStatus.FAILED
            delivery.error = str(e)

        # Retry if failed and attempts remaining
        if delivery.status == WebhookStatus.FAILED and attempt < webhook.retry_count:
            delivery.status = WebhookStatus.RETRYING
            await asyncio.sleep(webhook.retry_delay_seconds)
            return await self.send_webhook(webhook, payload, attempt + 1)

        # Track delivery
        with self._lock:
            self.delivery_history.append(delivery)
            # Keep last 1000 deliveries
            if len(self.delivery_history) > 1000:
                self.delivery_history = self.delivery_history[-1000:]

        return delivery

    async def notify(
        self,
        event_type: WebhookEventType,
        iteration_id: str,
        verdict: Optional[str] = None,
        previous_verdict: Optional[str] = None,
        can_deploy: bool = False,
        dde_passed: Optional[bool] = None,
        bdv_passed: Optional[bool] = None,
        acc_passed: Optional[bool] = None,
        diagnosis: Optional[str] = None,
        recommendations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[WebhookDelivery]:
        """
        Send notification to all subscribed webhooks.

        Args:
            event_type: Type of event
            iteration_id: Iteration identifier
            verdict: Current verdict
            previous_verdict: Previous verdict (for changes)
            can_deploy: Deployment approval status
            dde_passed: DDE audit result
            bdv_passed: BDV audit result
            acc_passed: ACC audit result
            diagnosis: Diagnostic message
            recommendations: List of recommendations
            metadata: Additional metadata

        Returns:
            List of WebhookDelivery results
        """
        webhooks = self._get_webhooks_for_event(event_type)
        if not webhooks:
            return []

        payload = WebhookPayload(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            iteration_id=iteration_id,
            verdict=verdict,
            previous_verdict=previous_verdict,
            can_deploy=can_deploy,
            dde_passed=dde_passed,
            bdv_passed=bdv_passed,
            acc_passed=acc_passed,
            diagnosis=diagnosis,
            recommendations=recommendations or [],
            metadata=metadata or {}
        )

        # Send to all webhooks in parallel
        tasks = [self.send_webhook(w, payload) for w in webhooks]
        deliveries = await asyncio.gather(*tasks, return_exceptions=True)

        return [d for d in deliveries if isinstance(d, WebhookDelivery)]

    def get_delivery_history(
        self,
        webhook_id: Optional[str] = None,
        limit: int = 100
    ) -> List[WebhookDelivery]:
        """
        Get delivery history.

        Args:
            webhook_id: Filter by webhook ID
            limit: Maximum entries

        Returns:
            List of WebhookDelivery
        """
        with self._lock:
            history = self.delivery_history
            if webhook_id:
                history = [d for d in history if d.webhook_id == webhook_id]
            return history[-limit:][::-1]  # Most recent first


# Global webhook manager
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get or create global webhook manager."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


# ============================================================================
# Convenience Functions
# ============================================================================

async def notify_verdict_changed(
    iteration_id: str,
    verdict: str,
    previous_verdict: Optional[str] = None,
    can_deploy: bool = False,
    dde_passed: bool = False,
    bdv_passed: bool = False,
    acc_passed: bool = False,
    diagnosis: Optional[str] = None,
    recommendations: Optional[List[str]] = None
) -> List[WebhookDelivery]:
    """Notify webhooks of verdict change."""
    manager = get_webhook_manager()
    return await manager.notify(
        event_type=WebhookEventType.VERDICT_CHANGED,
        iteration_id=iteration_id,
        verdict=verdict,
        previous_verdict=previous_verdict,
        can_deploy=can_deploy,
        dde_passed=dde_passed,
        bdv_passed=bdv_passed,
        acc_passed=acc_passed,
        diagnosis=diagnosis,
        recommendations=recommendations
    )


async def notify_deployment_approved(
    iteration_id: str,
    project: str,
    version: str
) -> List[WebhookDelivery]:
    """Notify webhooks of deployment approval."""
    manager = get_webhook_manager()
    return await manager.notify(
        event_type=WebhookEventType.DEPLOYMENT_APPROVED,
        iteration_id=iteration_id,
        can_deploy=True,
        metadata={"project": project, "version": version}
    )


async def notify_deployment_blocked(
    iteration_id: str,
    verdict: str,
    blocking_reasons: List[str]
) -> List[WebhookDelivery]:
    """Notify webhooks of deployment block."""
    manager = get_webhook_manager()
    return await manager.notify(
        event_type=WebhookEventType.DEPLOYMENT_BLOCKED,
        iteration_id=iteration_id,
        verdict=verdict,
        can_deploy=False,
        metadata={"blocking_reasons": blocking_reasons}
    )


async def notify_systemic_failure(
    iteration_id: str,
    diagnosis: str,
    recommendations: List[str]
) -> List[WebhookDelivery]:
    """Notify webhooks of systemic failure."""
    manager = get_webhook_manager()
    return await manager.notify(
        event_type=WebhookEventType.SYSTEMIC_FAILURE,
        iteration_id=iteration_id,
        verdict="systemic_failure",
        can_deploy=False,
        dde_passed=False,
        bdv_passed=False,
        acc_passed=False,
        diagnosis=diagnosis,
        recommendations=recommendations
    )


# ============================================================================
# API Router
# ============================================================================

class WebhookConfigRequest(BaseModel):
    """Request to register a webhook."""
    url: str = Field(..., description="Webhook URL")
    name: str = Field(..., description="Webhook name")
    secret: Optional[str] = Field(None, description="HMAC secret for signatures")
    events: List[str] = Field(default_factory=list, description="Event types to subscribe")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook."""
    url: Optional[str] = None
    name: Optional[str] = None
    secret: Optional[str] = None
    events: Optional[List[str]] = None
    active: Optional[bool] = None
    headers: Optional[Dict[str, str]] = None


router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.get("")
async def list_webhooks() -> Dict[str, Any]:
    """List all registered webhooks."""
    manager = get_webhook_manager()
    webhooks = manager.list_webhooks()

    return {
        "webhooks": [
            {
                "id": w.id,
                "name": w.name,
                "url": w.url,
                "events": [e.value for e in w.events],
                "active": w.active,
                "created_at": w.created_at
            }
            for w in webhooks
        ],
        "count": len(webhooks)
    }


@router.post("")
async def register_webhook(request: WebhookConfigRequest) -> Dict[str, Any]:
    """Register a new webhook."""
    manager = get_webhook_manager()

    webhook_id = f"webhook-{datetime.utcnow().timestamp()}"
    events = [WebhookEventType(e) for e in request.events] if request.events else list(WebhookEventType)

    config = WebhookConfig(
        id=webhook_id,
        url=request.url,
        name=request.name,
        secret=request.secret,
        events=events,
        headers=request.headers
    )

    manager.register_webhook(config)

    return {
        "success": True,
        "webhook_id": webhook_id,
        "message": f"Webhook '{request.name}' registered successfully"
    }


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str) -> Dict[str, Any]:
    """Get webhook details."""
    manager = get_webhook_manager()
    webhook = manager.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {
        "webhook": {
            "id": webhook.id,
            "name": webhook.name,
            "url": webhook.url,
            "events": [e.value for e in webhook.events],
            "active": webhook.active,
            "retry_count": webhook.retry_count,
            "created_at": webhook.created_at
        }
    }


@router.patch("/{webhook_id}")
async def update_webhook(webhook_id: str, request: WebhookUpdateRequest) -> Dict[str, Any]:
    """Update webhook configuration."""
    manager = get_webhook_manager()

    updates = request.dict(exclude_none=True)
    webhook = manager.update_webhook(webhook_id, updates)

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {
        "success": True,
        "message": f"Webhook '{webhook.name}' updated successfully"
    }


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str) -> Dict[str, Any]:
    """Delete a webhook."""
    manager = get_webhook_manager()

    if manager.unregister_webhook(webhook_id):
        return {"success": True, "message": "Webhook deleted"}

    raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str) -> Dict[str, Any]:
    """Send test webhook delivery."""
    manager = get_webhook_manager()
    webhook = manager.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    payload = WebhookPayload(
        event_type=WebhookEventType.VERDICT_CHANGED,
        timestamp=datetime.utcnow().isoformat() + "Z",
        iteration_id="test-webhook-delivery",
        verdict="all_pass",
        can_deploy=True,
        dde_passed=True,
        bdv_passed=True,
        acc_passed=True,
        diagnosis="Test webhook delivery",
        metadata={"test": True}
    )

    delivery = await manager.send_webhook(webhook, payload)

    return {
        "success": delivery.status == WebhookStatus.DELIVERED,
        "delivery": delivery.to_dict()
    }


@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, description="Maximum entries")
) -> Dict[str, Any]:
    """Get delivery history for a webhook."""
    manager = get_webhook_manager()
    deliveries = manager.get_delivery_history(webhook_id=webhook_id, limit=limit)

    return {
        "deliveries": [d.to_dict() for d in deliveries],
        "count": len(deliveries)
    }


@router.get("/deliveries/all")
async def get_all_deliveries(
    limit: int = Query(100, description="Maximum entries")
) -> Dict[str, Any]:
    """Get all delivery history."""
    manager = get_webhook_manager()
    deliveries = manager.get_delivery_history(limit=limit)

    return {
        "deliveries": [d.to_dict() for d in deliveries],
        "count": len(deliveries)
    }
