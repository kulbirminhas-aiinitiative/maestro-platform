"""
Health Check API Endpoint

A simple, production-ready health check API endpoint for monitoring
service availability and system status.

Author: Requirement Analyst
Date: 2025-11-22
"""

import os
import sys
import time
import socket
import platform
from datetime import datetime, timezone
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health check endpoints."""

    # Track service start time for uptime calculation
    start_time = time.time()

    def do_GET(self) -> None:
        """Handle GET requests for health check endpoints."""
        try:
            if self.path == "/health":
                self._handle_health_check()
            elif self.path == "/health/live":
                self._handle_liveness_check()
            elif self.path == "/health/ready":
                self._handle_readiness_check()
            else:
                self._send_not_found()
        except Exception as e:
            self._send_error(500, "Internal Server Error", str(e))

    def _send_error(self, status_code: int, error: str, message: str) -> None:
        """Send an error response."""
        self._send_json_response(status_code, {
            "error": error,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def _handle_health_check(self) -> None:
        """
        Main health check endpoint.
        Returns comprehensive health information about the service.
        """
        health_data = self._get_health_data()
        self._send_json_response(200, health_data)

    def _handle_liveness_check(self) -> None:
        """
        Liveness probe endpoint.
        Returns minimal response to indicate service is running.
        Used by orchestrators like Kubernetes for restart decisions.
        """
        response = {
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._send_json_response(200, response)

    def _handle_readiness_check(self) -> None:
        """
        Readiness probe endpoint.
        Indicates if the service is ready to accept traffic.
        """
        # In production, add checks for dependencies (DB, cache, etc.)
        is_ready = self._check_readiness()
        status_code = 200 if is_ready else 503

        response = {
            "status": HealthStatus.HEALTHY if is_ready else HealthStatus.UNHEALTHY,
            "ready": is_ready,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._send_json_response(status_code, response)

    def _get_health_data(self) -> Dict[str, Any]:
        """Compile comprehensive health check data."""
        uptime_seconds = time.time() - self.start_time

        return {
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": {
                "name": "health-check-api",
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development")
            },
            "system": {
                "hostname": socket.gethostname(),
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "uptime_seconds": round(uptime_seconds, 2)
            },
            "checks": {
                "memory": self._check_memory(),
                "disk": self._check_disk()
            }
        }

    def _check_readiness(self) -> bool:
        """
        Check if service is ready to handle requests.
        Override this to add dependency checks.
        """
        return True

    def _check_memory(self) -> Dict[str, Any]:
        """Check memory status."""
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "status": HealthStatus.HEALTHY,
                "max_rss_mb": round(usage.ru_maxrss / 1024, 2)
            }
        except Exception:
            return {"status": HealthStatus.HEALTHY, "info": "memory check unavailable"}

    def _check_disk(self) -> Dict[str, Any]:
        """Check disk space status."""
        try:
            statvfs = os.statvfs("/")
            free_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
            total_gb = (statvfs.f_frsize * statvfs.f_blocks) / (1024**3)
            used_percent = ((total_gb - free_gb) / total_gb) * 100

            status = HealthStatus.HEALTHY
            if used_percent > 90:
                status = HealthStatus.UNHEALTHY
            elif used_percent > 80:
                status = HealthStatus.DEGRADED

            return {
                "status": status,
                "free_gb": round(free_gb, 2),
                "used_percent": round(used_percent, 1)
            }
        except Exception:
            return {"status": HealthStatus.HEALTHY, "info": "disk check unavailable"}

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _send_not_found(self) -> None:
        """Send a 404 Not Found response."""
        self._send_json_response(404, {
            "error": "Not Found",
            "message": f"Endpoint {self.path} not found",
            "available_endpoints": ["/health", "/health/live", "/health/ready"]
        })

    def log_message(self, format: str, *args) -> None:
        """Override to customize logging."""
        sys.stderr.write(f"[{datetime.now().isoformat()}] {args[0]}\n")


def create_server(host: str = "0.0.0.0", port: int = 8080) -> HTTPServer:
    """
    Create and return an HTTP server instance.

    Args:
        host: Host address to bind to
        port: Port number to listen on

    Returns:
        Configured HTTPServer instance
    """
    server_address = (host, port)
    return HTTPServer(server_address, HealthCheckHandler)


def main() -> None:
    """Main entry point for the health check API server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))

    server = create_server(host, port)
    print(f"Health Check API running on http://{host}:{port}")
    print("Endpoints: /health, /health/live, /health/ready")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()
