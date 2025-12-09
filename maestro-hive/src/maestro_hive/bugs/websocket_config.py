"""
WebSocket Configuration - Fix for MD-1991.

Fixes Sandbox WebSocket connection by routing through API Gateway (port 8080)
instead of direct service access (port 4001).

Usage:
    from maestro_hive.bugs import WebSocketConfig, get_websocket_url

    config = WebSocketConfig.from_environment()
    ws_url = get_websocket_url(config)

EPIC: MD-2798 - [Bugs] Known Issues & Fixes
Task: MD-1991 - Sandbox WebSocket connection failing - wrong IP configuration
"""

import os
import re
import socket
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"


class Protocol(Enum):
    """WebSocket protocol."""
    WS = "ws"
    WSS = "wss"


@dataclass
class WebSocketConfig:
    """
    WebSocket configuration for Maestro platform.

    Centralizes all WebSocket URL construction to ensure consistent
    gateway routing across all environments.

    Attributes:
        environment: Current deployment environment.
        gateway_host: API Gateway hostname.
        gateway_port: API Gateway port (default 8080).
        protocol: WebSocket protocol (ws or wss).
        path: WebSocket endpoint path.
        connection_timeout: Connection timeout in seconds.
        heartbeat_interval: Heartbeat ping interval in seconds.
    """
    environment: Environment = Environment.DEVELOPMENT
    gateway_host: str = "localhost"
    gateway_port: int = 8080  # CRITICAL: Use gateway port, NOT 4001
    protocol: Protocol = Protocol.WS
    path: str = "/ws"
    connection_timeout: float = 30.0
    heartbeat_interval: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    extra_headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_environment(cls) -> "WebSocketConfig":
        """
        Create configuration from environment variables.

        Environment variables:
        - VITE_WS_GATEWAY_URL: Full WebSocket URL (overrides other settings)
        - VITE_API_GATEWAY_URL: API Gateway URL (used to derive WS URL)
        - MAESTRO_ENVIRONMENT: Environment name
        - WS_CONNECTION_TIMEOUT: Connection timeout
        - WS_HEARTBEAT_INTERVAL: Heartbeat interval

        Returns:
            WebSocketConfig instance configured from environment.
        """
        # Check for explicit WebSocket URL
        ws_url = os.getenv("VITE_WS_GATEWAY_URL")
        if ws_url:
            return cls._from_url(ws_url)

        # Derive from API Gateway URL
        api_url = os.getenv("VITE_API_GATEWAY_URL")
        if api_url:
            return cls._from_api_url(api_url)

        # Build from individual settings
        env_name = os.getenv("MAESTRO_ENVIRONMENT", "development").lower()
        try:
            environment = Environment(env_name)
        except ValueError:
            environment = Environment.DEVELOPMENT

        # Get host from environment or use defaults
        host = os.getenv("WS_HOST", "localhost")
        port = int(os.getenv("WS_PORT", "8080"))  # Default to gateway port
        use_ssl = os.getenv("WS_SSL", "false").lower() == "true"

        # Environment-specific defaults
        if environment == Environment.SANDBOX:
            host = os.getenv("SANDBOX_HOST", host)
            use_ssl = True
        elif environment == Environment.PRODUCTION:
            host = os.getenv("PRODUCTION_HOST", host)
            use_ssl = True

        return cls(
            environment=environment,
            gateway_host=host,
            gateway_port=port,
            protocol=Protocol.WSS if use_ssl else Protocol.WS,
            path=os.getenv("WS_PATH", "/ws"),
            connection_timeout=float(os.getenv("WS_CONNECTION_TIMEOUT", "30")),
            heartbeat_interval=float(os.getenv("WS_HEARTBEAT_INTERVAL", "30")),
        )

    @classmethod
    def _from_url(cls, url: str) -> "WebSocketConfig":
        """Create config from WebSocket URL."""
        parsed = urlparse(url)

        protocol = Protocol.WSS if parsed.scheme == "wss" else Protocol.WS
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if protocol == Protocol.WSS else 8080)
        path = parsed.path or "/ws"

        return cls(
            gateway_host=host,
            gateway_port=port,
            protocol=protocol,
            path=path,
        )

    @classmethod
    def _from_api_url(cls, api_url: str) -> "WebSocketConfig":
        """Create WebSocket config from API URL."""
        parsed = urlparse(api_url)

        # Convert http(s) to ws(s)
        if parsed.scheme == "https":
            protocol = Protocol.WSS
        else:
            protocol = Protocol.WS

        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if protocol == Protocol.WSS else 8080)

        return cls(
            gateway_host=host,
            gateway_port=port,
            protocol=protocol,
            path="/ws",
        )

    def get_url(self) -> str:
        """
        Get the full WebSocket URL.

        Returns:
            WebSocket URL string.
        """
        return f"{self.protocol.value}://{self.gateway_host}:{self.gateway_port}{self.path}"

    def get_url_for_host(self, hostname: str, use_ssl: bool = False) -> str:
        """
        Get WebSocket URL for a specific hostname.

        Useful for dynamic host resolution in frontend.

        Args:
            hostname: Target hostname.
            use_ssl: Whether to use WSS protocol.

        Returns:
            WebSocket URL for the specified host.
        """
        protocol = Protocol.WSS if use_ssl else self.protocol
        return f"{protocol.value}://{hostname}:{self.gateway_port}{self.path}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "environment": self.environment.value,
            "gateway_host": self.gateway_host,
            "gateway_port": self.gateway_port,
            "protocol": self.protocol.value,
            "path": self.path,
            "url": self.get_url(),
            "connection_timeout": self.connection_timeout,
            "heartbeat_interval": self.heartbeat_interval,
        }


def get_websocket_url(config: Optional[WebSocketConfig] = None) -> str:
    """
    Get the WebSocket URL using gateway configuration.

    This is the primary function to use when establishing WebSocket connections.
    Always routes through the API Gateway (port 8080) instead of direct
    service access (port 4001).

    Args:
        config: Optional WebSocketConfig. If not provided, creates from environment.

    Returns:
        WebSocket URL string.

    Example:
        >>> url = get_websocket_url()
        >>> print(url)
        "ws://localhost:8080/ws"
    """
    if config is None:
        config = WebSocketConfig.from_environment()
    return config.get_url()


def get_gateway_url(config: Optional[WebSocketConfig] = None) -> str:
    """
    Get the API Gateway URL (HTTP, not WebSocket).

    Args:
        config: Optional WebSocketConfig. If not provided, creates from environment.

    Returns:
        API Gateway URL string.

    Example:
        >>> url = get_gateway_url()
        >>> print(url)
        "http://localhost:8080"
    """
    if config is None:
        config = WebSocketConfig.from_environment()

    protocol = "https" if config.protocol == Protocol.WSS else "http"
    return f"{protocol}://{config.gateway_host}:{config.gateway_port}"


def validate_websocket_connection(
    config: Optional[WebSocketConfig] = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Validate WebSocket connection parameters.

    Checks:
    - Host is resolvable
    - Port is reachable
    - URL format is valid

    Args:
        config: WebSocket configuration to validate.
        timeout: Connection timeout for validation.

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "url": str,
            "host_resolvable": bool,
            "port_reachable": bool,
            "errors": List[str]
        }
    """
    if config is None:
        config = WebSocketConfig.from_environment()

    result = {
        "valid": True,
        "url": config.get_url(),
        "host_resolvable": False,
        "port_reachable": False,
        "errors": [],
    }

    # Check host resolution
    try:
        socket.gethostbyname(config.gateway_host)
        result["host_resolvable"] = True
    except socket.gaierror as e:
        result["valid"] = False
        result["errors"].append(f"Cannot resolve host '{config.gateway_host}': {e}")

    # Check port reachability (only if host resolved)
    if result["host_resolvable"]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((config.gateway_host, config.gateway_port))
            result["port_reachable"] = True
        except (socket.timeout, socket.error) as e:
            result["valid"] = False
            result["errors"].append(
                f"Cannot connect to {config.gateway_host}:{config.gateway_port}: {e}"
            )
        finally:
            sock.close()

    # Validate URL format
    url = config.get_url()
    if not re.match(r"^wss?://", url):
        result["valid"] = False
        result["errors"].append(f"Invalid WebSocket URL format: {url}")

    return result


def get_frontend_websocket_config() -> str:
    """
    Generate JavaScript/TypeScript code for frontend WebSocket configuration.

    This generates the correct configuration to replace the hardcoded
    port 4001 in the frontend code.

    Returns:
        JavaScript code string for WebSocket URL construction.
    """
    return '''
// WebSocket URL construction - uses gateway port 8080 instead of 4001
const WS_URL = import.meta.env.VITE_WS_GATEWAY_URL ||
  (typeof window !== 'undefined' ?
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8080/ws` :
    'ws://localhost:8080/ws');

export function getWebSocketUrl(): string {
  return WS_URL;
}

export function getWebSocketUrlForHost(hostname: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${hostname}:8080/ws`;
}
'''


# Convenience function for TypeScript/JavaScript migration
def generate_vite_config_patch() -> str:
    """
    Generate patch for vite.config.ts to fix WebSocket port.

    Returns:
        Diff-style patch for vite.config.ts.
    """
    return '''
// vite.config.ts patch for MD-1991
// Replace:
//   const websocketUrl = env.VITE_WEBSOCKET_URL || "ws://localhost:4001";
// With:
const websocketUrl = env.VITE_WEBSOCKET_URL || "ws://localhost:8080/ws";
'''
