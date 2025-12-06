"""
BlockWirer - AC-4: Wire blocks together

Wires resolved blocks together via their interfaces, creating
a connected system ready for execution.

Reference: MD-2508 Acceptance Criterion 4
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from .dependency_resolver import ResolvedDependencies, ResolvedBlock

logger = logging.getLogger(__name__)


class ConnectionType(str, Enum):
    """Types of connections between blocks"""
    DIRECT = "direct"         # Direct method/interface call
    EVENT = "event"           # Event-based communication
    QUEUE = "queue"           # Queue-based messaging
    CALLBACK = "callback"     # Callback pattern


@dataclass
class Connection:
    """Definition of a connection between blocks"""
    source_block: str
    source_port: str          # Interface/method name on source
    target_block: str
    target_port: str          # Interface/method name on target
    connection_type: ConnectionType = ConnectionType.DIRECT
    transform: Optional[Callable] = None  # Optional data transform
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WiringResult:
    """Result of a single wiring operation"""
    connection: Connection
    success: bool
    error: Optional[str] = None


@dataclass
class WiredBlock:
    """A block with its connections established"""
    block_id: str
    block_instance: Any
    inbound_connections: List[Connection]
    outbound_connections: List[Connection]


@dataclass
class WiredSystem:
    """
    A fully wired system of blocks.

    Contains all blocks with their connections established
    and ready for execution.
    """
    blocks: Dict[str, WiredBlock]
    connections: List[Connection]
    entry_points: List[str]     # Blocks that can be entry points
    exit_points: List[str]      # Blocks that produce final output
    wiring_errors: List[WiringResult]

    def get_block(self, block_id: str) -> Optional[WiredBlock]:
        """Get wired block by ID"""
        return self.blocks.get(block_id)

    def is_valid(self) -> bool:
        """Check if system is valid (no wiring errors)"""
        return len(self.wiring_errors) == 0

    def get_execution_order(self) -> List[str]:
        """Get order in which blocks should be executed"""
        # Start from entry points and traverse connections
        order = []
        visited = set()

        def visit(block_id: str):
            if block_id in visited:
                return
            visited.add(block_id)

            block = self.blocks.get(block_id)
            if block:
                # Visit dependencies first
                for conn in block.inbound_connections:
                    visit(conn.source_block)
                order.append(block_id)

        for entry in self.entry_points:
            visit(entry)

        # Add any remaining blocks
        for bid in self.blocks:
            if bid not in order:
                order.append(bid)

        return order


@dataclass
class ValidationResult:
    """Result of wiring validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]


class BlockWirer:
    """
    Wirer for connecting blocks via interfaces.

    Implements AC-4: Wire blocks together

    Features:
    - Connect blocks via interfaces
    - Support multiple connection types
    - Validate wiring compatibility
    - Auto-detect connection points
    - Generate wiring diagram
    """

    def __init__(self):
        logger.info("BlockWirer initialized")

    def wire(
        self,
        resolved: ResolvedDependencies,
        connections: Optional[List[Connection]] = None
    ) -> WiredSystem:
        """
        Wire blocks together.

        Args:
            resolved: Resolved dependencies with block instances
            connections: Optional explicit connections (auto-detected if None)

        Returns:
            WiredSystem with connected blocks
        """
        wired_blocks = {}
        wiring_errors = []

        # Initialize wired blocks
        for block_id, resolved_block in resolved.blocks.items():
            wired_blocks[block_id] = WiredBlock(
                block_id=block_id,
                block_instance=resolved_block.block_instance,
                inbound_connections=[],
                outbound_connections=[]
            )

        # Determine connections
        if connections:
            all_connections = connections
        else:
            all_connections = self._auto_detect_connections(resolved)

        # Apply connections
        for conn in all_connections:
            result = self._apply_connection(conn, wired_blocks)
            if not result.success:
                wiring_errors.append(result)
            else:
                # Track connections on blocks
                if conn.source_block in wired_blocks:
                    wired_blocks[conn.source_block].outbound_connections.append(conn)
                if conn.target_block in wired_blocks:
                    wired_blocks[conn.target_block].inbound_connections.append(conn)

        # Determine entry and exit points
        entry_points = self._find_entry_points(wired_blocks)
        exit_points = self._find_exit_points(wired_blocks)

        logger.info(f"Wired {len(wired_blocks)} blocks with {len(all_connections)} connections")

        return WiredSystem(
            blocks=wired_blocks,
            connections=all_connections,
            entry_points=entry_points,
            exit_points=exit_points,
            wiring_errors=wiring_errors
        )

    def _auto_detect_connections(self, resolved: ResolvedDependencies) -> List[Connection]:
        """
        Auto-detect connections based on block interfaces.

        Examines blocks for:
        - Declared dependencies
        - Compatible interfaces
        - Required/provided port matching
        """
        connections = []
        blocks = list(resolved.blocks.values())

        for i, block in enumerate(blocks):
            instance = block.block_instance
            if not instance:
                continue

            # Check declared dependencies
            deps = getattr(instance, 'dependencies', [])
            for dep_id in deps:
                if dep_id in resolved.blocks:
                    # Create connection from dependency to this block
                    connections.append(Connection(
                        source_block=dep_id,
                        source_port="output",
                        target_block=block.block_id,
                        target_port="input",
                        connection_type=ConnectionType.DIRECT
                    ))

            # Check interface matching
            required = getattr(instance, 'required_interfaces', [])
            for req_interface in required:
                # Find block that provides this interface
                for other in blocks:
                    if other.block_id == block.block_id:
                        continue
                    other_instance = other.block_instance
                    if not other_instance:
                        continue

                    provided = getattr(other_instance, 'provided_interfaces', [])
                    if req_interface in provided:
                        connections.append(Connection(
                            source_block=other.block_id,
                            source_port=req_interface,
                            target_block=block.block_id,
                            target_port=req_interface,
                            connection_type=ConnectionType.DIRECT
                        ))

        return connections

    def _apply_connection(
        self,
        conn: Connection,
        wired_blocks: Dict[str, WiredBlock]
    ) -> WiringResult:
        """Apply a single connection between blocks"""
        source = wired_blocks.get(conn.source_block)
        target = wired_blocks.get(conn.target_block)

        if not source:
            return WiringResult(
                connection=conn,
                success=False,
                error=f"Source block not found: {conn.source_block}"
            )

        if not target:
            return WiringResult(
                connection=conn,
                success=False,
                error=f"Target block not found: {conn.target_block}"
            )

        # Verify ports exist
        source_instance = source.block_instance
        target_instance = target.block_instance

        if source_instance and not self._has_port(source_instance, conn.source_port):
            return WiringResult(
                connection=conn,
                success=False,
                error=f"Source port not found: {conn.source_block}.{conn.source_port}"
            )

        if target_instance and not self._has_port(target_instance, conn.target_port):
            return WiringResult(
                connection=conn,
                success=False,
                error=f"Target port not found: {conn.target_block}.{conn.target_port}"
            )

        # Apply the wiring based on connection type
        try:
            if conn.connection_type == ConnectionType.DIRECT:
                self._wire_direct(source_instance, target_instance, conn)
            elif conn.connection_type == ConnectionType.CALLBACK:
                self._wire_callback(source_instance, target_instance, conn)
            elif conn.connection_type == ConnectionType.EVENT:
                self._wire_event(source_instance, target_instance, conn)

            return WiringResult(connection=conn, success=True)

        except Exception as e:
            return WiringResult(
                connection=conn,
                success=False,
                error=str(e)
            )

    def _has_port(self, instance: Any, port_name: str) -> bool:
        """Check if instance has a port (method/attribute)"""
        # Accept generic port names
        if port_name in ["input", "output"]:
            return True

        return hasattr(instance, port_name) or hasattr(instance, f"get_{port_name}")

    def _wire_direct(self, source: Any, target: Any, conn: Connection):
        """Wire blocks via direct method injection"""
        # Inject source reference into target
        if hasattr(target, f"set_{conn.source_port}"):
            getattr(target, f"set_{conn.source_port}")(source)
        elif hasattr(target, "_dependencies"):
            target._dependencies[conn.source_block] = source

    def _wire_callback(self, source: Any, target: Any, conn: Connection):
        """Wire blocks via callback registration"""
        if hasattr(source, "register_callback"):
            callback = getattr(target, conn.target_port, None)
            if callback and callable(callback):
                source.register_callback(callback)

    def _wire_event(self, source: Any, target: Any, conn: Connection):
        """Wire blocks via event subscription"""
        if hasattr(source, "subscribe"):
            handler = getattr(target, conn.target_port, None)
            if handler and callable(handler):
                source.subscribe(conn.source_port, handler)

    def _find_entry_points(self, blocks: Dict[str, WiredBlock]) -> List[str]:
        """Find blocks with no inbound connections (entry points)"""
        return [
            bid for bid, block in blocks.items()
            if len(block.inbound_connections) == 0
        ]

    def _find_exit_points(self, blocks: Dict[str, WiredBlock]) -> List[str]:
        """Find blocks with no outbound connections (exit points)"""
        return [
            bid for bid, block in blocks.items()
            if len(block.outbound_connections) == 0
        ]

    def validate_wiring(self, system: WiredSystem) -> ValidationResult:
        """
        Validate a wired system.

        Args:
            system: WiredSystem to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check for wiring errors
        for error in system.wiring_errors:
            errors.append(error.error or "Unknown wiring error")

        # Check for disconnected blocks
        for block_id, block in system.blocks.items():
            if not block.inbound_connections and not block.outbound_connections:
                warnings.append(f"Block '{block_id}' is not connected to any other block")

        # Check for cycles (optional warning)
        if self._has_cycle(system):
            warnings.append("Wiring contains cycles (may cause infinite loops)")

        # Check for missing entry points
        if not system.entry_points:
            errors.append("No entry points detected in wired system")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _has_cycle(self, system: WiredSystem) -> bool:
        """Check if wiring has cycles"""
        visited = set()
        rec_stack = set()

        def dfs(block_id: str) -> bool:
            visited.add(block_id)
            rec_stack.add(block_id)

            block = system.blocks.get(block_id)
            if block:
                for conn in block.outbound_connections:
                    target = conn.target_block
                    if target not in visited:
                        if dfs(target):
                            return True
                    elif target in rec_stack:
                        return True

            rec_stack.remove(block_id)
            return False

        for block_id in system.blocks:
            if block_id not in visited:
                if dfs(block_id):
                    return True

        return False

    def generate_diagram(self, system: WiredSystem) -> str:
        """Generate ASCII diagram of wired system"""
        lines = ["Wiring Diagram:", "=" * 40]

        for block_id, block in system.blocks.items():
            marker = ""
            if block_id in system.entry_points:
                marker += " [ENTRY]"
            if block_id in system.exit_points:
                marker += " [EXIT]"

            lines.append(f"\n[{block_id}]{marker}")

            for conn in block.outbound_connections:
                lines.append(f"  -> {conn.target_block} (via {conn.source_port})")

        lines.append("\n" + "=" * 40)
        return "\n".join(lines)
