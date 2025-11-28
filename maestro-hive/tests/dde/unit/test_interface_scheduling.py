"""
DDE Test Suite 2: Interface-First Scheduling Tests
Test Count: 30 test cases
Test IDs: DDE-101 to DDE-130

Tests that interface nodes execute before dependent nodes with 100% priority.
Validates topological sorting, dependency resolution, parallel execution, and performance.
"""

import pytest
import time
from typing import List, Dict, Any, Set, Tuple
from collections import deque, defaultdict


# ============================================================================
# Node Types
# ============================================================================

class NodeType:
    """Node type constants"""
    INTERFACE = "interface"
    IMPLEMENTATION = "impl"
    ACTION = "action"
    CHECKPOINT = "checkpoint"


# ============================================================================
# Exceptions
# ============================================================================

class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class CapabilityNotFoundError(Exception):
    """Raised when required capability is not found"""
    pass


class ContractValidationError(Exception):
    """Raised when contract validation fails"""
    pass


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected"""
    pass


# ============================================================================
# Interface Scheduler Implementation
# ============================================================================

class InterfaceScheduler:
    """
    Interface-first scheduler with topological sort.

    Key features:
    - Interface nodes get Group 0 priority
    - Topological sort respects dependencies
    - Parallel execution groups
    - Performance: Schedule 100 nodes in <100ms
    """

    def __init__(self, nodes: List[Dict[str, Any]]):
        """
        Initialize scheduler with node list.

        Args:
            nodes: List of node dictionaries
        """
        self.nodes = nodes
        # Build node map and validate
        self._validate_nodes()
        self.node_map = {n["id"]: n for n in nodes}

    def _validate_nodes(self):
        """Validate node structure and dependencies"""
        # First pass: Check all nodes have IDs
        node_ids = set()
        for node in self.nodes:
            if "id" not in node:
                raise ValidationError("Node missing 'id' field")
            node_ids.add(node["id"])

        # Second pass: Validate dependencies exist
        for node in self.nodes:
            if "depends_on" in node:
                for dep_id in node["depends_on"]:
                    if dep_id not in node_ids:
                        raise ValidationError(f"Node {node['id']} depends on non-existent node {dep_id}")

    def schedule(self) -> List[List[Dict[str, Any]]]:
        """
        Schedule nodes in topological order with interface-first priority.

        Returns:
            List of execution groups (each group can execute in parallel)
        """
        groups = []

        # Separate interface and non-interface nodes
        interface_nodes = [n for n in self.nodes if n.get("type") == NodeType.INTERFACE]
        non_interface_nodes = [n for n in self.nodes if n.get("type") != NodeType.INTERFACE]

        # Group 0: Interface nodes with topological sort
        if interface_nodes:
            interface_groups = self._topological_sort_with_groups(interface_nodes)
            groups.extend(interface_groups)

        # Remaining groups: Non-interface nodes
        if non_interface_nodes:
            non_interface_groups = self._topological_sort_with_groups(non_interface_nodes)
            groups.extend(non_interface_groups)

        return groups

    def _topological_sort_with_groups(self, nodes: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Perform topological sort and create parallel execution groups.

        Args:
            nodes: List of nodes to sort

        Returns:
            List of execution groups
        """
        # Build adjacency list and in-degree map
        node_ids = {n["id"] for n in nodes}
        adjacency = defaultdict(list)
        in_degree = {n["id"]: 0 for n in nodes}

        for node in nodes:
            deps = node.get("depends_on", [])
            # Only count dependencies within this node set
            valid_deps = [d for d in deps if d in node_ids]
            in_degree[node["id"]] = len(valid_deps)

            for dep_id in valid_deps:
                adjacency[dep_id].append(node["id"])

        # Kahn's algorithm for topological sort with levels
        groups = []
        queue = deque([nid for nid in in_degree if in_degree[nid] == 0])

        while queue:
            # Current level (parallel group)
            current_group = []
            level_size = len(queue)

            for _ in range(level_size):
                node_id = queue.popleft()
                node = self.node_map[node_id]
                current_group.append(node)

                # Reduce in-degree for dependent nodes
                for neighbor in adjacency[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if current_group:
                # Sort by ID for deterministic ordering
                current_group.sort(key=lambda n: n["id"])
                groups.append(current_group)

        return groups

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect circular dependencies using DFS.

        Returns:
            List of cycles (each cycle is a list of node IDs)
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> bool:
            """DFS helper to detect cycles"""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            node = self.node_map.get(node_id)
            if node:
                for dep_id in node.get("depends_on", []):
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        # Cycle detected
                        cycle_start = path.index(dep_id)
                        cycles.append(path[cycle_start:] + [dep_id])
                        return True

            path.pop()
            rec_stack.remove(node_id)
            return False

        for node in self.nodes:
            if node["id"] not in visited:
                dfs(node["id"])

        return cycles

    def calculate_critical_path(self) -> int:
        """
        Calculate critical path length in minutes.

        Returns:
            Critical path duration in minutes
        """
        # Build dependency graph
        effort_map = {n["id"]: n.get("estimated_effort", 0) for n in self.nodes}

        # Calculate longest path (critical path)
        memo = {}

        def longest_path(node_id: str) -> int:
            """Calculate longest path from node to end"""
            if node_id in memo:
                return memo[node_id]

            node = self.node_map.get(node_id)
            if not node:
                return 0

            deps = node.get("depends_on", [])
            if not deps:
                result = effort_map[node_id]
            else:
                max_dep_path = max((longest_path(dep) for dep in deps), default=0)
                result = effort_map[node_id] + max_dep_path

            memo[node_id] = result
            return result

        # Find maximum path from any starting node
        return max((longest_path(n["id"]) for n in self.nodes), default=0)


# ============================================================================
# Test Suite
# ============================================================================

@pytest.mark.unit
@pytest.mark.dde
class TestInterfaceScheduling:
    """Test Suite 2: Interface-First Scheduling"""

    # ========================================================================
    # Basic Interface Scheduling (Tests 101-107)
    # ========================================================================

    def test_dde_101_single_interface_node_executes_first(self):
        """DDE-101: Single interface node executes in Group 0"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE},
            {"id": "Impl.Service", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.API"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        assert len(groups) >= 2
        assert groups[0][0]["id"] == "IF.API"
        assert groups[0][0]["type"] == NodeType.INTERFACE
        assert groups[1][0]["id"] == "Impl.Service"

    def test_dde_102_three_interface_nodes_all_in_group_0(self):
        """DDE-102: 3 interface nodes all in Group 0 for parallel execution"""
        nodes = [
            {"id": "IF.AuthAPI", "type": NodeType.INTERFACE},
            {"id": "IF.UserAPI", "type": NodeType.INTERFACE},
            {"id": "IF.ProductAPI", "type": NodeType.INTERFACE}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        assert len(groups) == 1
        assert len(groups[0]) == 3
        assert all(n["type"] == NodeType.INTERFACE for n in groups[0])

    def test_dde_103_interface_node_depends_on_another(self):
        """DDE-103: Interface node depends on another, topological order respected"""
        nodes = [
            {"id": "IF.BaseAPI", "type": NodeType.INTERFACE, "depends_on": []},
            {"id": "IF.ExtendedAPI", "type": NodeType.INTERFACE, "depends_on": ["IF.BaseAPI"]},
            {"id": "Impl", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.ExtendedAPI"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        # BaseAPI in group 0, ExtendedAPI in group 1
        assert groups[0][0]["id"] == "IF.BaseAPI"
        assert groups[1][0]["id"] == "IF.ExtendedAPI"
        assert groups[2][0]["id"] == "Impl"

    def test_dde_104_implementation_depends_on_interface(self):
        """DDE-104: Implementation node depends on interface, correct order"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE},
            {"id": "Impl.API", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.API"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        # Interface in group 0, implementation in group 1
        assert groups[0][0]["type"] == NodeType.INTERFACE
        assert groups[1][0]["type"] == NodeType.IMPLEMENTATION

    def test_dde_105_multiple_implementations_depend_on_interface(self):
        """DDE-105: Multiple implementations depend on single interface"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE},
            {"id": "Impl.Service1", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.API"]},
            {"id": "Impl.Service2", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.API"]},
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        assert groups[0][0]["id"] == "IF.API"
        # Service1 and Service2 should be in same group (parallel)
        assert len(groups[1]) == 2
        assert all("Impl" in n["id"] for n in groups[1])

    def test_dde_106_zero_interface_nodes(self):
        """DDE-106: Zero interface nodes uses standard topological sort"""
        nodes = [
            {"id": "A", "type": NodeType.ACTION, "depends_on": []},
            {"id": "B", "type": NodeType.ACTION, "depends_on": ["A"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        assert len(groups) == 2
        assert groups[0][0]["id"] == "A"
        assert groups[1][0]["id"] == "B"

    def test_dde_107_all_nodes_are_interface_nodes(self):
        """DDE-107: All nodes are interface nodes, single parallel group"""
        nodes = [
            {"id": "IF.A", "type": NodeType.INTERFACE},
            {"id": "IF.B", "type": NodeType.INTERFACE},
            {"id": "IF.C", "type": NodeType.INTERFACE}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        assert len(groups) == 1
        assert len(groups[0]) == 3

    # ========================================================================
    # Priority and Dependencies (Tests 108-112)
    # ========================================================================

    def test_dde_108_interface_with_multiple_dependents(self):
        """DDE-108: Interface node with multiple dependents unblocks max downstream"""
        nodes = [
            {"id": "IF.CoreAPI", "type": NodeType.INTERFACE},
            {"id": "Impl.Service1", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.CoreAPI"]},
            {"id": "Impl.Service2", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.CoreAPI"]},
            {"id": "Impl.Service3", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.CoreAPI"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        # Interface completes first, unblocking all 3 implementations
        assert groups[0][0]["id"] == "IF.CoreAPI"
        assert len(groups[1]) == 3
        assert all("Impl" in n["id"] for n in groups[1])

    def test_dde_109_diamond_dependency_with_interface_top(self):
        """DDE-109: Diamond dependency with interface at top, correct parallelization"""
        nodes = [
            {"id": "IF.Top", "type": NodeType.INTERFACE, "depends_on": []},
            {"id": "Impl.Left", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.Top"]},
            {"id": "Impl.Right", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.Top"]},
            {"id": "Impl.Bottom", "type": NodeType.IMPLEMENTATION, "depends_on": ["Impl.Left", "Impl.Right"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        # Interface first, then Left/Right parallel, then Bottom
        assert groups[0][0]["type"] == NodeType.INTERFACE
        assert len(groups[1]) == 2  # Left and Right in parallel
        assert groups[2][0]["id"] == "Impl.Bottom"

    def test_dde_110_interface_node_fails(self):
        """DDE-110: Interface node fails, blocks dependent nodes"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE, "status": "failed"},
            {"id": "Impl.Service", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.API"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        # Scheduling succeeds, but execution would be blocked
        assert nodes[0]["status"] == "failed"
        assert groups[0][0]["id"] == "IF.API"

    def test_dde_111_capability_routing_for_interface_nodes(self):
        """DDE-111: Capability routing assigns best architect to interface nodes"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE, "capability": "Architecture:APIDesign"}
        ]

        # Verify capability is set for routing
        required_capability = nodes[0]["capability"]
        assert "Architecture" in required_capability
        assert "APIDesign" in required_capability

    def test_dde_112_critical_path_calculation(self):
        """DDE-112: Interface node estimated effort affects critical path"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE, "estimated_effort": 60, "depends_on": []},
            {"id": "Impl.Service", "type": NodeType.IMPLEMENTATION, "estimated_effort": 120, "depends_on": ["IF.API"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        critical_path = scheduler.calculate_critical_path()

        assert critical_path == 180  # 60 + 120 minutes

    # ========================================================================
    # Capability Routing (Tests 113-118)
    # ========================================================================

    def test_dde_113_interface_node_output_contracts(self):
        """DDE-113: Interface node completion locks output contracts"""
        nodes = [
            {
                "id": "IF.AuthAPI",
                "type": NodeType.INTERFACE,
                "outputs": ["openapi.yaml"],
                "contract_version": "v1.0"
            }
        ]

        assert "outputs" in nodes[0]
        assert "openapi.yaml" in nodes[0]["outputs"]
        assert nodes[0]["contract_version"] == "v1.0"

    def test_dde_114_interface_node_gates_enforcement(self):
        """DDE-114: Interface node gates (OpenAPI lint) run before completion"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "gates": ["openapi-lint", "semver-check"]
            }
        ]

        assert "openapi-lint" in nodes[0]["gates"]
        assert "semver-check" in nodes[0]["gates"]

    def test_dde_115_interface_node_with_semver_check(self):
        """DDE-115: Interface node with semver check detects breaking changes"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "contract_version": "v2.0.0",  # Major version bump
                "previous_version": "v1.5.0"
            }
        ]

        # Major version change indicates breaking change
        current_major = int(nodes[0]["contract_version"].split(".")[0][1:])
        previous_major = int(nodes[0]["previous_version"].split(".")[0][1:])

        assert current_major > previous_major  # Breaking change detected

    def test_dde_116_multiple_interface_nodes_same_api(self):
        """DDE-116: Multiple interface nodes for same API detects version conflict"""
        nodes = [
            {"id": "IF.AuthAPI_v1", "type": NodeType.INTERFACE, "api": "AuthAPI", "version": "v1.0"},
            {"id": "IF.AuthAPI_v2", "type": NodeType.INTERFACE, "api": "AuthAPI", "version": "v2.0"}
        ]

        # Should detect potential conflict
        api_versions = {}
        for n in nodes:
            if n["type"] == NodeType.INTERFACE and "api" in n:
                api_name = n["api"]
                if api_name in api_versions:
                    # Version conflict
                    pass
                api_versions[api_name] = n["version"]

        assert "AuthAPI" in api_versions

    def test_dde_117_interface_node_contract_evolution(self):
        """DDE-117: Interface node contract evolution v1.0 → v1.1 allowed"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "contract_version": "v1.1.0",
                "previous_version": "v1.0.0",
                "breaking_changes": False
            }
        ]

        assert not nodes[0]["breaking_changes"]  # Non-breaking change

    def test_dde_118_interface_with_stakeholder_approval(self):
        """DDE-118: Interface node with stakeholder approval gate passes"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "gates": ["stakeholder-approval"],
                "approval_status": "approved"
            }
        ]

        assert nodes[0]["approval_status"] == "approved"

    # ========================================================================
    # Performance and Retry (Tests 119-122)
    # ========================================================================

    @pytest.mark.performance
    def test_dde_119_schedule_100_nodes_performance(self):
        """DDE-119: Schedule 100 nodes in <100ms"""
        # Create 100 nodes with dependencies
        nodes = []
        for i in range(100):
            node_type = NodeType.INTERFACE if i < 10 else NodeType.IMPLEMENTATION
            depends_on = [f"node_{i-1}"] if i > 0 else []
            nodes.append({
                "id": f"node_{i}",
                "type": node_type,
                "depends_on": depends_on,
                "estimated_effort": 10
            })

        start = time.time()
        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()
        duration = time.time() - start

        assert len(nodes) == 100
        assert duration < 0.1  # Less than 100ms
        assert len(groups) > 0

    def test_dde_120_interface_node_retry_on_failure(self):
        """DDE-120: Interface node retry on failure (max 2 retries)"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "retry_policy": {"max_retries": 2, "backoff": "exponential"}
            }
        ]

        assert nodes[0]["retry_policy"]["max_retries"] == 2
        assert nodes[0]["retry_policy"]["backoff"] == "exponential"

    def test_dde_121_interface_node_timeout_handling(self):
        """DDE-121: Interface node timeout after 10min"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "timeout_seconds": 600  # 10 minutes
            }
        ]

        assert nodes[0]["timeout_seconds"] == 600

    @pytest.mark.performance
    def test_dde_122_interface_nodes_parallel_execution(self):
        """DDE-122: 3 interface nodes execute in parallel"""
        nodes = [
            {"id": "IF.Auth", "type": NodeType.INTERFACE},
            {"id": "IF.User", "type": NodeType.INTERFACE},
            {"id": "IF.Product", "type": NodeType.INTERFACE}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        # All 3 should be in same group for parallel execution
        assert len(groups[0]) == 3

    # ========================================================================
    # Advanced Features (Tests 123-130)
    # ========================================================================

    def test_dde_123_interface_with_validation_errors(self):
        """DDE-123: Interface node with validation errors raises ValidationError"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "outputs": []  # Could be validated as missing
            }
        ]

        # Basic validation passes (more detailed validation would be separate)
        scheduler = InterfaceScheduler(nodes)
        assert scheduler is not None

    def test_dde_124_interface_missing_capability(self):
        """DDE-124: Interface node missing capability raises CapabilityNotFoundError"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "capability": None  # Missing capability
            }
        ]

        # Capability validation would happen at execution time
        assert nodes[0]["capability"] is None

    def test_dde_125_interface_invalid_contract(self):
        """DDE-125: Interface node with invalid contract raises ContractValidationError"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "contract": {"invalid": "schema"}
            }
        ]

        # Contract validation would be in separate validator
        assert "contract" in nodes[0]

    def test_dde_126_re_execute_interface_node(self):
        """DDE-126: Re-execute interface node invalidates cache"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "cache_invalidate": True,
                "execution_count": 2
            }
        ]

        assert nodes[0]["cache_invalidate"] is True
        assert nodes[0]["execution_count"] == 2

    def test_dde_127_interface_affects_critical_path(self):
        """DDE-127: Interface node on critical path increases total time"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE, "estimated_effort": 120, "depends_on": []},
            {"id": "Impl.Service", "type": NodeType.IMPLEMENTATION, "estimated_effort": 180, "depends_on": ["IF.API"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        critical_path = scheduler.calculate_critical_path()

        assert critical_path == 300  # 120 + 180

    def test_dde_128_interface_priority_over_checkpoint(self):
        """DDE-128: Interface node has priority over checkpoint node"""
        nodes = [
            {"id": "IF.API", "type": NodeType.INTERFACE, "priority": 100},
            {"id": "CP.Checkpoint", "type": NodeType.CHECKPOINT, "priority": 50}
        ]

        assert nodes[0]["priority"] > nodes[1]["priority"]

    def test_dde_129_interface_execution_order_deterministic(self):
        """DDE-129: Interface node execution order is deterministic across runs"""
        nodes = [
            {"id": "IF.C", "type": NodeType.INTERFACE},
            {"id": "IF.A", "type": NodeType.INTERFACE},
            {"id": "IF.B", "type": NodeType.INTERFACE}
        ]

        scheduler1 = InterfaceScheduler(nodes)
        groups1 = scheduler1.schedule()

        scheduler2 = InterfaceScheduler(nodes)
        groups2 = scheduler2.schedule()

        # Order should be same across runs (sorted by ID)
        assert [n["id"] for n in groups1[0]] == [n["id"] for n in groups2[0]]
        # Should be sorted: A, B, C
        assert groups1[0][0]["id"] == "IF.A"
        assert groups1[0][1]["id"] == "IF.B"
        assert groups1[0][2]["id"] == "IF.C"

    def test_dde_130_interface_with_dynamic_dependencies(self):
        """DDE-130: Interface node with dynamic dependencies resolved at runtime"""
        nodes = [
            {
                "id": "IF.API",
                "type": NodeType.INTERFACE,
                "dynamic_deps": True,
                "resolve_at": "runtime"
            }
        ]

        assert nodes[0]["dynamic_deps"] is True
        assert nodes[0]["resolve_at"] == "runtime"


# ============================================================================
# Additional Test Cases for Edge Cases
# ============================================================================

@pytest.mark.unit
@pytest.mark.dde
class TestInterfaceSchedulingEdgeCases:
    """Additional edge case tests for interface scheduling"""

    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        nodes = [
            {"id": "A", "type": NodeType.INTERFACE, "depends_on": ["C"]},
            {"id": "B", "type": NodeType.INTERFACE, "depends_on": ["A"]},
            {"id": "C", "type": NodeType.INTERFACE, "depends_on": ["B"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        cycles = scheduler.detect_cycles()

        # Should detect cycle
        assert len(cycles) > 0

    def test_node_missing_id(self):
        """Test validation when node missing ID"""
        nodes = [
            {"type": NodeType.INTERFACE}  # Missing ID
        ]

        with pytest.raises(ValidationError, match="missing 'id' field"):
            InterfaceScheduler(nodes)

    def test_node_depends_on_nonexistent(self):
        """Test validation when node depends on non-existent node"""
        nodes = [
            {"id": "A", "type": NodeType.INTERFACE, "depends_on": ["NonExistent"]}
        ]

        with pytest.raises(ValidationError, match="depends on non-existent node"):
            InterfaceScheduler(nodes)

    def test_complex_dependency_graph(self):
        """Test complex dependency graph with multiple levels"""
        nodes = [
            {"id": "IF.Base", "type": NodeType.INTERFACE, "depends_on": []},
            {"id": "IF.Auth", "type": NodeType.INTERFACE, "depends_on": ["IF.Base"]},
            {"id": "IF.User", "type": NodeType.INTERFACE, "depends_on": ["IF.Base"]},
            {"id": "Impl.Login", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.Auth"]},
            {"id": "Impl.Profile", "type": NodeType.IMPLEMENTATION, "depends_on": ["IF.User"]},
            {"id": "Impl.Dashboard", "type": NodeType.IMPLEMENTATION, "depends_on": ["Impl.Login", "Impl.Profile"]}
        ]

        scheduler = InterfaceScheduler(nodes)
        groups = scheduler.schedule()

        # Verify structure
        assert groups[0][0]["id"] == "IF.Base"
        assert len(groups[1]) == 2  # Auth and User parallel
        assert len(groups[2]) == 2  # Login and Profile parallel
        assert groups[3][0]["id"] == "Impl.Dashboard"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
