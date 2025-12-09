"""
Health Check Integration for Rollback Decisions.

Monitors service health to trigger automatic rollbacks.
"""

import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class CheckType(str, Enum):
    """Health check type."""
    HTTP = "http"
    TCP = "tcp"
    GRPC = "grpc"
    COMMAND = "command"


@dataclass
class HealthEndpoint:
    """Health check endpoint configuration."""
    name: str
    url: str
    check_type: CheckType = CheckType.HTTP
    timeout_seconds: float = 5.0
    interval_seconds: float = 30.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    expected_status: int = 200
    expected_body: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "check_type": self.check_type.value,
            "timeout_seconds": self.timeout_seconds,
            "interval_seconds": self.interval_seconds,
            "healthy_threshold": self.healthy_threshold,
            "unhealthy_threshold": self.unhealthy_threshold
        }


@dataclass
class HealthResult:
    """Result of a health check."""
    endpoint: str
    status: HealthStatus
    latency_ms: float
    checked_at: datetime
    response_code: Optional[int] = None
    error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.endpoint,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "checked_at": self.checked_at.isoformat(),
            "response_code": self.response_code,
            "error": self.error,
            "details": self.details
        }


@dataclass
class AggregatedHealth:
    """Aggregated health status."""
    status: HealthStatus
    components: list[HealthResult]
    timestamp: datetime
    healthy_count: int = 0
    unhealthy_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "components": [c.to_dict() for c in self.components],
            "timestamp": self.timestamp.isoformat(),
            "healthy_count": self.healthy_count,
            "unhealthy_count": self.unhealthy_count
        }


class HealthChecker:
    """Health check integration for rollback decisions."""

    def __init__(
        self,
        endpoints: Optional[list[HealthEndpoint]] = None,
        failure_threshold: float = 0.5
    ):
        self.endpoints = endpoints or []
        self.failure_threshold = failure_threshold
        self._results: dict[str, list[HealthResult]] = {}
        self._consecutive_failures: dict[str, int] = {}

    def add_endpoint(self, endpoint: HealthEndpoint) -> None:
        """Add health check endpoint."""
        self.endpoints.append(endpoint)
        self._results[endpoint.name] = []
        self._consecutive_failures[endpoint.name] = 0

    async def check(self, endpoint: HealthEndpoint) -> HealthResult:
        """Check single endpoint health."""
        start_time = datetime.utcnow()

        try:
            if endpoint.check_type == CheckType.HTTP:
                result = await self._http_check(endpoint)
            elif endpoint.check_type == CheckType.TCP:
                result = await self._tcp_check(endpoint)
            else:
                result = HealthResult(
                    endpoint=endpoint.name,
                    status=HealthStatus.HEALTHY,
                    latency_ms=0,
                    checked_at=start_time
                )

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.latency_ms = elapsed

            # Track consecutive failures
            if result.status == HealthStatus.HEALTHY:
                self._consecutive_failures[endpoint.name] = 0
            else:
                self._consecutive_failures[endpoint.name] += 1

            # Store result
            if endpoint.name not in self._results:
                self._results[endpoint.name] = []
            self._results[endpoint.name].append(result)

            # Keep only last 100 results
            if len(self._results[endpoint.name]) > 100:
                self._results[endpoint.name] = self._results[endpoint.name][-100:]

            return result

        except asyncio.TimeoutError:
            return HealthResult(
                endpoint=endpoint.name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=endpoint.timeout_seconds * 1000,
                checked_at=start_time,
                error="Timeout"
            )
        except Exception as e:
            return HealthResult(
                endpoint=endpoint.name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                checked_at=start_time,
                error=str(e)
            )

    async def _http_check(self, endpoint: HealthEndpoint) -> HealthResult:
        """Perform HTTP health check (simulated)."""
        # Simulated check - in production would use aiohttp
        await asyncio.sleep(0.001)
        return HealthResult(
            endpoint=endpoint.name,
            status=HealthStatus.HEALTHY,
            latency_ms=5.0,
            checked_at=datetime.utcnow(),
            response_code=200
        )

    async def _tcp_check(self, endpoint: HealthEndpoint) -> HealthResult:
        """Perform TCP health check (simulated)."""
        await asyncio.sleep(0.001)
        return HealthResult(
            endpoint=endpoint.name,
            status=HealthStatus.HEALTHY,
            latency_ms=2.0,
            checked_at=datetime.utcnow()
        )

    async def check_all(self) -> AggregatedHealth:
        """Check all health endpoints."""
        if not self.endpoints:
            return AggregatedHealth(
                status=HealthStatus.HEALTHY,
                components=[],
                timestamp=datetime.utcnow()
            )

        results = await asyncio.gather(*[
            self.check(ep) for ep in self.endpoints
        ])

        healthy = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        unhealthy = len(results) - healthy

        if unhealthy == 0:
            overall = HealthStatus.HEALTHY
        elif healthy == 0:
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED

        return AggregatedHealth(
            status=overall,
            components=list(results),
            timestamp=datetime.utcnow(),
            healthy_count=healthy,
            unhealthy_count=unhealthy
        )

    async def should_rollback(self) -> bool:
        """Determine if rollback is needed based on health."""
        health = await self.check_all()

        if health.status == HealthStatus.UNHEALTHY:
            return True

        if health.status == HealthStatus.DEGRADED:
            failure_rate = health.unhealthy_count / len(health.components)
            return failure_rate >= self.failure_threshold

        return False

    def get_history(self, endpoint_name: str, limit: int = 10) -> list[HealthResult]:
        """Get health check history for endpoint."""
        results = self._results.get(endpoint_name, [])
        return results[-limit:]

    def get_uptime(self, endpoint_name: str) -> float:
        """Calculate uptime percentage for endpoint."""
        results = self._results.get(endpoint_name, [])
        if not results:
            return 100.0

        healthy = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        return (healthy / len(results)) * 100

    def get_average_latency(self, endpoint_name: str) -> float:
        """Calculate average latency for endpoint."""
        results = self._results.get(endpoint_name, [])
        if not results:
            return 0.0

        return sum(r.latency_ms for r in results) / len(results)
