"""
Mock Server Manager
MD-2482 Task 1.3: Start mock servers from OpenAPI specs.

AC-6: Mock servers started from OpenAPI specs
AC-7: Mock lifecycle management (start/stop/health)
"""

import os
import subprocess
import signal
import socket
import time
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
import threading
import uuid

logger = logging.getLogger(__name__)


class MockServerType(Enum):
    """Supported mock server types."""
    PRISM = "prism"
    WIREMOCK = "wiremock"


class MockStatus(Enum):
    """Mock server status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class MockEndpoint:
    """Mock endpoint configuration."""
    path: str
    method: str
    status_code: int = 200
    response_body: Any = None
    content_type: str = "application/json"


@dataclass
class HealthStatus:
    """Health check result."""
    healthy: bool
    status: MockStatus
    uptime_seconds: float = 0
    requests_handled: int = 0
    last_error: Optional[str] = None


@dataclass
class MockServer:
    """
    Mock server instance.
    AC-6: Mock servers started from OpenAPI specs
    """
    id: str
    type: MockServerType
    port: int
    spec_path: str
    status: MockStatus = MockStatus.STOPPED
    endpoints: List[MockEndpoint] = field(default_factory=list)
    process: Optional[subprocess.Popen] = None
    start_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "port": self.port,
            "spec_path": self.spec_path,
            "status": self.status.value,
            "endpoints": [
                {"path": e.path, "method": e.method}
                for e in self.endpoints
            ],
            "uptime": time.time() - self.start_time if self.start_time else 0,
        }


class OpenAPIConverter:
    """
    Convert OpenAPI spec to mock configuration.
    Part of AC-6: Mock servers started from OpenAPI specs
    """
    
    def __init__(self, spec_path: str):
        """
        Initialize converter.
        
        Args:
            spec_path: Path to OpenAPI spec file
        """
        self.spec_path = Path(spec_path)
        self.spec: Dict = {}
    
    def load(self) -> bool:
        """Load OpenAPI specification."""
        if not self.spec_path.exists():
            logger.error(f"Spec file not found: {self.spec_path}")
            return False
        
        try:
            content = self.spec_path.read_text()
            
            if self.spec_path.suffix in [".yaml", ".yml"]:
                import yaml
                self.spec = yaml.safe_load(content)
            else:
                self.spec = json.loads(content)
            
            return True
        except Exception as e:
            logger.error(f"Failed to load spec: {e}")
            return False
    
    def extract_endpoints(self) -> List[MockEndpoint]:
        """Extract endpoints from OpenAPI spec."""
        endpoints = []
        
        paths = self.spec.get("paths", {})
        for path, methods in paths.items():
            for method, config in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue
                
                # Get default response
                responses = config.get("responses", {})
                default_status = 200
                response_body = None
                
                for status_code, response in responses.items():
                    if status_code.startswith("2"):
                        default_status = int(status_code)
                        # Extract example response if available
                        content = response.get("content", {})
                        json_content = content.get("application/json", {})
                        response_body = json_content.get("example")
                        break
                
                endpoints.append(MockEndpoint(
                    path=path,
                    method=method.upper(),
                    status_code=default_status,
                    response_body=response_body,
                ))
        
        return endpoints
    
    def get_server_url(self) -> Optional[str]:
        """Get server URL from spec."""
        servers = self.spec.get("servers", [])
        if servers:
            return servers[0].get("url", "http://localhost:4010")
        return None


class MockManager:
    """
    Manage mock server lifecycle.
    
    AC-6: Mock servers started from OpenAPI specs
    AC-7: Mock lifecycle management (start/stop/health)
    """
    
    def __init__(self, base_port: int = 4010):
        """
        Initialize mock manager.
        
        Args:
            base_port: Starting port for mock servers
        """
        self.base_port = base_port
        self.servers: Dict[str, MockServer] = {}
        self._port_counter = base_port
        self._lock = threading.Lock()
    
    def create_mock(
        self,
        spec_path: str,
        server_type: MockServerType = MockServerType.PRISM,
    ) -> MockServer:
        """
        Create a mock server from OpenAPI spec.
        AC-6: Mock servers started from OpenAPI specs
        
        Args:
            spec_path: Path to OpenAPI specification
            server_type: Type of mock server to use
            
        Returns:
            MockServer instance
        """
        # Convert spec
        converter = OpenAPIConverter(spec_path)
        if not converter.load():
            raise ValueError(f"Could not load spec: {spec_path}")
        
        # Get available port
        port = self._get_available_port()
        
        # Extract endpoints
        endpoints = converter.extract_endpoints()
        
        # Create server instance
        server_id = str(uuid.uuid4())[:8]
        server = MockServer(
            id=server_id,
            type=server_type,
            port=port,
            spec_path=spec_path,
            endpoints=endpoints,
        )
        
        with self._lock:
            self.servers[server_id] = server
        
        logger.info(f"Created mock server {server_id} on port {port}")
        return server
    
    def start(self, mock_id: str) -> bool:
        """
        Start a mock server.
        AC-7: Mock lifecycle management (start/stop/health)
        
        Args:
            mock_id: Server ID to start
            
        Returns:
            True if started successfully
        """
        server = self.servers.get(mock_id)
        if not server:
            logger.error(f"Server not found: {mock_id}")
            return False
        
        if server.status == MockStatus.RUNNING:
            logger.warning(f"Server {mock_id} already running")
            return True
        
        server.status = MockStatus.STARTING
        
        try:
            # Build command based on server type
            if server.type == MockServerType.PRISM:
                cmd = self._build_prism_command(server)
            else:
                cmd = self._build_wiremock_command(server)
            
            # Start process
            server.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,  # Create new process group
            )
            
            # Wait for server to be ready
            if self._wait_for_ready(server, timeout=10):
                server.status = MockStatus.RUNNING
                server.start_time = time.time()
                logger.info(f"Started mock server {mock_id} on port {server.port}")
                return True
            else:
                server.status = MockStatus.ERROR
                self._cleanup_process(server)
                return False
                
        except Exception as e:
            logger.error(f"Failed to start mock server: {e}")
            server.status = MockStatus.ERROR
            return False
    
    def stop(self, mock_id: str) -> bool:
        """
        Stop a mock server.
        AC-7: Mock lifecycle management (start/stop/health)
        
        Args:
            mock_id: Server ID to stop
            
        Returns:
            True if stopped successfully
        """
        server = self.servers.get(mock_id)
        if not server:
            logger.error(f"Server not found: {mock_id}")
            return False
        
        if server.status == MockStatus.STOPPED:
            return True
        
        server.status = MockStatus.STOPPING
        
        try:
            self._cleanup_process(server)
            server.status = MockStatus.STOPPED
            server.start_time = None
            logger.info(f"Stopped mock server {mock_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop mock server: {e}")
            return False
    
    def health_check(self, mock_id: str) -> HealthStatus:
        """
        Check health of a mock server.
        AC-7: Mock lifecycle management (start/stop/health)
        
        Args:
            mock_id: Server ID to check
            
        Returns:
            HealthStatus with server health info
        """
        server = self.servers.get(mock_id)
        if not server:
            return HealthStatus(
                healthy=False,
                status=MockStatus.STOPPED,
                last_error="Server not found",
            )
        
        # Check if process is alive
        if server.process and server.process.poll() is None:
            # Process running, check if port responsive
            if self._is_port_open(server.port):
                uptime = time.time() - server.start_time if server.start_time else 0
                return HealthStatus(
                    healthy=True,
                    status=MockStatus.RUNNING,
                    uptime_seconds=uptime,
                )
        
        # Process not running
        server.status = MockStatus.STOPPED
        return HealthStatus(
            healthy=False,
            status=MockStatus.STOPPED,
            last_error="Process not running",
        )
    
    def stop_all(self) -> None:
        """Stop all running mock servers."""
        for mock_id in list(self.servers.keys()):
            self.stop(mock_id)
    
    def list_servers(self) -> List[Dict]:
        """List all mock servers."""
        return [server.to_dict() for server in self.servers.values()]
    
    def get_server(self, mock_id: str) -> Optional[MockServer]:
        """Get mock server by ID."""
        return self.servers.get(mock_id)
    
    def _get_available_port(self) -> int:
        """Get next available port."""
        with self._lock:
            while not self._is_port_available(self._port_counter):
                self._port_counter += 1
            port = self._port_counter
            self._port_counter += 1
            return port
    
    def _is_port_available(self, port: int) -> bool:
        """Check if port is available."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result != 0
        except Exception:
            return True
    
    def _is_port_open(self, port: int) -> bool:
        """Check if port is accepting connections."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _build_prism_command(self, server: MockServer) -> List[str]:
        """Build Prism mock server command."""
        return [
            "prism", "mock",
            server.spec_path,
            "-p", str(server.port),
            "--host", "0.0.0.0",
        ]
    
    def _build_wiremock_command(self, server: MockServer) -> List[str]:
        """Build WireMock server command."""
        return [
            "java", "-jar", "wiremock.jar",
            "--port", str(server.port),
        ]
    
    def _wait_for_ready(self, server: MockServer, timeout: int = 10) -> bool:
        """Wait for server to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            if self._is_port_open(server.port):
                return True
            time.sleep(0.5)
        return False
    
    def _cleanup_process(self, server: MockServer) -> None:
        """Cleanup server process."""
        if server.process:
            try:
                # Kill process group
                os.killpg(os.getpgid(server.process.pid), signal.SIGTERM)
                server.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(server.process.pid), signal.SIGKILL)
                except OSError:
                    pass
            finally:
                server.process = None


class MockRegistry:
    """
    Registry for tracking mock server instances.
    Provides global access to mock management.
    """
    
    _instance: Optional[MockManager] = None
    
    @classmethod
    def get_manager(cls) -> MockManager:
        """Get or create the mock manager singleton."""
        if cls._instance is None:
            cls._instance = MockManager()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the registry (stops all servers)."""
        if cls._instance:
            cls._instance.stop_all()
            cls._instance = None
