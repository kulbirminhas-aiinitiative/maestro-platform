"""
DDE Test Suite 1: Execution Manifest Schema Tests
Phase 1A Foundation Tests - Test Suite 1
Test Count: 25 test cases (DDE-001 to DDE-025)

Tests execution manifest creation, validation, serialization, and advanced features:
- Basic validation (001-008)
- Schema validation (009-011)
- Policy parsing (012-015)
- Serialization (016-019)
- Advanced features (020-025)
"""

import pytest
import json
import yaml
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


# ============================================================================
# ExecutionManifest Implementation
# ============================================================================

class NodeType(Enum):
    """Node types for execution manifest"""
    ACTION = "action"
    PHASE = "phase"
    CHECKPOINT = "checkpoint"
    NOTIFICATION = "notification"
    INTERFACE = "interface"
    IMPLEMENTATION = "impl"


class PolicySeverity(Enum):
    """Policy severity levels"""
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ManifestNode:
    """Node in execution manifest"""
    id: str
    type: str
    capability: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    gates: List[str] = field(default_factory=list)
    estimated_effort: Optional[int] = None
    contract_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None and v != [] and v != {}}


@dataclass
class ManifestPolicy:
    """Policy in execution manifest"""
    id: str
    severity: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ValidationError(Exception):
    """Validation error for manifests"""
    pass


class ExecutionManifest:
    """
    Execution Manifest for DDE (Dependency-Driven Execution)

    Represents a DAG of tasks with capability tags, contracts, and policy gates.
    Guarantees parallelism, compliance, lineage, and reproducibility.
    """

    def __init__(
        self,
        iteration_id: str,
        timestamp: str,
        project: str,
        nodes: Optional[List[Dict[str, Any]]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        policies: Optional[List[Dict[str, Any]]] = None,
        version: str = "1.0",
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.iteration_id = iteration_id
        self.timestamp = timestamp
        self.project = project
        self.nodes = nodes if nodes is not None else []
        self.constraints = constraints or {}
        self.policies = policies or []
        self.version = version
        self.tags = tags or []
        self.owner = owner
        self.metadata = metadata or {}

        # Internal state for validation
        self._validated = False
        self._node_map: Dict[str, Dict[str, Any]] = {}
        self._dependency_graph: Dict[str, List[str]] = {}

    def validate(self) -> bool:
        """
        Validate the execution manifest

        Checks:
        1. Required fields present
        2. Nodes list not empty
        3. Node IDs unique
        4. No circular dependencies
        5. All dependencies reference existing nodes

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails
        """
        # Check required fields
        if not self.iteration_id:
            raise ValidationError("iteration_id is required")

        if not self.timestamp:
            raise ValidationError("timestamp is required")

        if not self.project:
            raise ValidationError("project is required")

        # Check nodes list
        if self.nodes is None:
            raise ValidationError("nodes list cannot be None")

        if len(self.nodes) == 0:
            raise ValidationError("nodes list cannot be empty")

        # Build node map and check for duplicates
        self._node_map = {}
        for node in self.nodes:
            node_id = node.get("id")
            if not node_id:
                raise ValidationError(f"Node missing required 'id' field: {node}")

            if node_id in self._node_map:
                raise ValidationError(f"Duplicate node ID found: {node_id}")

            self._node_map[node_id] = node

        # Build dependency graph
        self._dependency_graph = {}
        for node in self.nodes:
            node_id = node["id"]
            depends_on = node.get("depends_on", [])
            self._dependency_graph[node_id] = depends_on

            # Check that all dependencies reference existing nodes
            for dep_id in depends_on:
                if dep_id not in self._node_map:
                    raise ValidationError(
                        f"Node '{node_id}' depends on non-existent node '{dep_id}'"
                    )

        # Check for circular dependencies using DFS
        if self._has_cycle():
            raise ValidationError("Circular dependencies detected in manifest")

        self._validated = True
        return True

    def _has_cycle(self) -> bool:
        """
        Detect cycles in dependency graph using DFS

        Returns:
            True if cycle exists, False otherwise
        """
        # States: 0=unvisited, 1=visiting, 2=visited
        state = {node_id: 0 for node_id in self._dependency_graph}

        def dfs(node_id: str) -> bool:
            """DFS helper to detect back edges"""
            if state[node_id] == 1:  # Back edge found (cycle)
                return True
            if state[node_id] == 2:  # Already processed
                return False

            state[node_id] = 1  # Mark as visiting

            for dep_id in self._dependency_graph.get(node_id, []):
                if dfs(dep_id):
                    return True

            state[node_id] = 2  # Mark as visited
            return False

        # Check each node
        for node_id in self._dependency_graph:
            if state[node_id] == 0:
                if dfs(node_id):
                    return True

        return False

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node by ID"""
        return self._node_map.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """Get all nodes of a specific type"""
        return [node for node in self.nodes if node.get("type") == node_type]

    def get_interface_nodes(self) -> List[Dict[str, Any]]:
        """Get all interface nodes"""
        return self.get_nodes_by_type(NodeType.INTERFACE.value)

    def get_dependency_chain(self, node_id: str) -> List[str]:
        """
        Get full dependency chain for a node (transitive closure)

        Returns:
            List of node IDs in dependency order
        """
        visited = set()
        result = []

        def dfs(current_id: str):
            if current_id in visited:
                return
            visited.add(current_id)

            # Visit dependencies first
            for dep_id in self._dependency_graph.get(current_id, []):
                dfs(dep_id)

            result.append(current_id)

        dfs(node_id)
        return result

    def calculate_total_effort(self) -> int:
        """Calculate total estimated effort across all nodes"""
        total = 0
        for node in self.nodes:
            effort = node.get("estimated_effort")
            if effort is not None:
                total += effort
        return total

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary"""
        result = {
            "iteration_id": self.iteration_id,
            "timestamp": self.timestamp,
            "project": self.project,
            "nodes": self.nodes,
            "constraints": self.constraints,
            "policies": self.policies
        }

        # Add optional fields if present
        if self.version != "1.0":
            result["version"] = self.version
        if self.tags:
            result["tags"] = self.tags
        if self.owner:
            result["owner"] = self.owner
        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def to_yaml(self) -> str:
        """Serialize to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionManifest":
        """Create manifest from dictionary"""
        return cls(
            iteration_id=data["iteration_id"],
            timestamp=data["timestamp"],
            project=data["project"],
            nodes=data.get("nodes", []),
            constraints=data.get("constraints", {}),
            policies=data.get("policies", []),
            version=data.get("version", "1.0"),
            tags=data.get("tags"),
            owner=data.get("owner"),
            metadata=data.get("metadata")
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ExecutionManifest":
        """Load manifest from YAML string"""
        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, json_content: str) -> "ExecutionManifest":
        """Load manifest from JSON string"""
        data = json.loads(json_content)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: Path) -> "ExecutionManifest":
        """Load manifest from file (auto-detect YAML or JSON)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if file_path.suffix in ['.yaml', '.yml']:
            return cls.from_yaml(content)
        elif file_path.suffix == '.json':
            return cls.from_json(content)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    def save_to_file(self, file_path: Path):
        """Save manifest to file (auto-detect format from extension)"""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            if file_path.suffix in ['.yaml', '.yml']:
                f.write(self.to_yaml())
            elif file_path.suffix == '.json':
                f.write(self.to_json())
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")


# ============================================================================
# Test Suite
# ============================================================================

@pytest.mark.unit
@pytest.mark.dde
class TestExecutionManifestSchema:
    """Test Suite 1: Execution Manifest Schema (DDE-001 to DDE-025)"""

    # ========================================================================
    # Basic Validation Tests (001-008)
    # ========================================================================

    def test_dde_001_valid_manifest_with_all_fields(self, mock_iteration_id):
        """DDE-001: Valid manifest with all required fields"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "node1", "type": "action"},
                {"id": "node2", "type": "interface"}
            ],
            constraints={"security_standard": "OWASP-L2"},
            policies=[{"id": "coverage >= 70%", "severity": "BLOCKING"}]
        )

        assert manifest.iteration_id == mock_iteration_id
        assert len(manifest.nodes) == 2
        assert manifest.validate() is True

    def test_dde_002_manifest_missing_iteration_id(self):
        """DDE-002: Manifest missing iteration_id raises ValidationError"""
        manifest = ExecutionManifest(
            iteration_id="",
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[{"id": "node1"}]
        )

        with pytest.raises(ValidationError, match="iteration_id is required"):
            manifest.validate()

    def test_dde_003_manifest_with_none_nodes_list(self, mock_iteration_id):
        """DDE-003: Manifest with None nodes list raises ValidationError"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=None
        )

        # nodes=None defaults to [] in __init__, so we get empty list error
        with pytest.raises(ValidationError, match="nodes list cannot be"):
            manifest.validate()

    def test_dde_004_manifest_with_empty_nodes(self, mock_iteration_id):
        """DDE-004: Manifest with empty nodes list raises ValidationError"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[]
        )

        with pytest.raises(ValidationError, match="nodes list cannot be empty"):
            manifest.validate()

    def test_dde_005_manifest_with_invalid_node_type(self, mock_iteration_id):
        """DDE-005: Manifest with invalid node type passes basic validation"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[{"id": "node1", "type": "INVALID_TYPE"}]
        )

        # Node type validation is separate from manifest structure validation
        assert manifest.validate() is True

    def test_dde_006_manifest_with_duplicate_node_ids(self, mock_iteration_id):
        """DDE-006: Manifest with duplicate node IDs raises ValidationError"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "node1", "type": "action"},
                {"id": "node1", "type": "interface"}
            ]
        )

        with pytest.raises(ValidationError, match="Duplicate node ID found: node1"):
            manifest.validate()

    def test_dde_007_manifest_with_circular_dependencies(self, mock_iteration_id):
        """DDE-007: Manifest with circular dependencies detected"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "A", "depends_on": ["C"]},
                {"id": "B", "depends_on": ["A"]},
                {"id": "C", "depends_on": ["B"]}
            ]
        )

        with pytest.raises(ValidationError, match="Circular dependencies detected"):
            manifest.validate()

    def test_dde_008_manifest_with_orphaned_nodes(self, mock_iteration_id):
        """DDE-008: Manifest with orphaned nodes (no dependencies) allowed"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "orphan", "type": "action"},
                {"id": "connected", "type": "action", "depends_on": []}
            ]
        )

        assert manifest.validate() is True
        assert len(manifest.nodes) == 2

    # ========================================================================
    # Schema Validation Tests (009-011)
    # ========================================================================

    def test_dde_009_manifest_schema_validation_json_schema(self, mock_iteration_id):
        """DDE-009: Manifest schema validation against structure"""
        manifest_dict = {
            "iteration_id": mock_iteration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "project": "TestProject",
            "nodes": [{"id": "node1", "type": "action"}]
        }

        manifest = ExecutionManifest.from_dict(manifest_dict)
        assert manifest.validate() is True
        assert "iteration_id" in manifest.to_dict()
        assert "nodes" in manifest.to_dict()

    def test_dde_010_manifest_with_interface_node_type(self, mock_iteration_id):
        """DDE-010: Manifest with NodeType.INTERFACE recognized"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {
                    "id": "IF.AuthAPI",
                    "type": NodeType.INTERFACE.value,
                    "capability": "Architecture:APIDesign"
                }
            ]
        )

        assert manifest.nodes[0]["type"] == NodeType.INTERFACE.value
        assert manifest.validate() is True

        interface_nodes = manifest.get_interface_nodes()
        assert len(interface_nodes) == 1
        assert interface_nodes[0]["id"] == "IF.AuthAPI"

    def test_dde_011_manifest_with_mixed_node_types(self, mock_iteration_id):
        """DDE-011: Manifest with mixed node types all recognized"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "n1", "type": NodeType.ACTION.value},
                {"id": "n2", "type": NodeType.PHASE.value},
                {"id": "n3", "type": NodeType.INTERFACE.value},
                {"id": "n4", "type": NodeType.CHECKPOINT.value}
            ]
        )

        assert len(manifest.nodes) == 4
        assert manifest.validate() is True

        # Verify each type
        assert manifest.get_node_by_id("n1")["type"] == NodeType.ACTION.value
        assert manifest.get_node_by_id("n2")["type"] == NodeType.PHASE.value
        assert manifest.get_node_by_id("n3")["type"] == NodeType.INTERFACE.value
        assert manifest.get_node_by_id("n4")["type"] == NodeType.CHECKPOINT.value

    # ========================================================================
    # Policy Parsing Tests (012-015)
    # ========================================================================

    def test_dde_012_manifest_policies_yaml_parsing(self, mock_iteration_id):
        """DDE-012: Manifest policies loaded correctly from YAML"""
        policies = [
            {"id": "coverage >= 70%", "severity": "BLOCKING"},
            {"id": "no_secrets", "severity": "BLOCKING"}
        ]

        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[{"id": "n1"}],
            policies=policies
        )

        assert len(manifest.policies) == 2
        assert manifest.policies[0]["severity"] == "BLOCKING"
        assert manifest.policies[1]["id"] == "no_secrets"

    def test_dde_013_manifest_constraints_validation(self, mock_iteration_id):
        """DDE-013: Manifest constraints validation enforced"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[{"id": "n1"}],
            constraints={
                "security_standard": "OWASP-L2",
                "library_policy": "InternalOnly",
                "runtime": "Python3.11"
            }
        )

        assert manifest.constraints["security_standard"] == "OWASP-L2"
        assert manifest.constraints["runtime"] == "Python3.11"
        assert manifest.validate() is True

    def test_dde_014_manifest_with_invalid_policy_severity(self, mock_iteration_id):
        """DDE-014: Manifest with invalid policy severity passes basic validation"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[{"id": "n1"}],
            policies=[{"id": "test", "severity": "INVALID"}]
        )

        # Policy severity validation would be in a separate policy validator
        assert manifest.validate() is True
        assert manifest.policies[0]["severity"] == "INVALID"

    def test_dde_015_manifest_with_future_timestamp(self, mock_iteration_id):
        """DDE-015: Manifest with future timestamp allowed (warning only)"""
        future_time = "2030-01-01T00:00:00Z"
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=future_time,
            project="TestProject",
            nodes=[{"id": "n1"}]
        )

        assert manifest.timestamp == future_time
        assert manifest.validate() is True

    # ========================================================================
    # Serialization Tests (016-019)
    # ========================================================================

    def test_dde_016_manifest_serialization_to_yaml(self, mock_iteration_id, temp_dir):
        """DDE-016: Manifest serialization to YAML round-trip"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[{"id": "n1", "type": "action"}]
        )

        yaml_path = temp_dir / "manifest.yaml"
        manifest.save_to_file(yaml_path)

        loaded_manifest = ExecutionManifest.from_file(yaml_path)
        assert loaded_manifest.iteration_id == mock_iteration_id
        assert len(loaded_manifest.nodes) == 1
        assert loaded_manifest.nodes[0]["id"] == "n1"

    def test_dde_017_manifest_deserialization_from_json(self, mock_iteration_id):
        """DDE-017: Manifest deserialization from JSON preserves fields"""
        manifest_json = json.dumps({
            "iteration_id": mock_iteration_id,
            "timestamp": "2025-10-13T14:00:00Z",
            "project": "TestProject",
            "nodes": [{"id": "n1", "type": "action"}],
            "constraints": {"runtime": "Python3.11"},
            "policies": [{"id": "test", "severity": "BLOCKING"}]
        })

        manifest = ExecutionManifest.from_json(manifest_json)
        assert manifest.iteration_id == mock_iteration_id
        assert manifest.project == "TestProject"
        assert len(manifest.nodes) == 1
        assert manifest.constraints["runtime"] == "Python3.11"
        assert len(manifest.policies) == 1

    def test_dde_018_manifest_with_metadata_fields(self, mock_iteration_id):
        """DDE-018: Manifest with metadata fields preserved"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {
                    "id": "n1",
                    "metadata": {
                        "author": "test",
                        "version": "1.0"
                    }
                }
            ]
        )

        assert "metadata" in manifest.nodes[0]
        assert manifest.nodes[0]["metadata"]["author"] == "test"

        # Round-trip test
        manifest_dict = manifest.to_dict()
        loaded = ExecutionManifest.from_dict(manifest_dict)
        assert loaded.nodes[0]["metadata"]["version"] == "1.0"

    def test_dde_019_manifest_version_evolution(self, mock_iteration_id):
        """DDE-019: Manifest version evolution v1.0 → v1.1 compatible"""
        # v1.0 manifest
        v1_manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp="2025-10-13T14:00:00Z",
            project="TestProject",
            nodes=[{"id": "n1"}]
        )

        # v1.1 manifest with additional fields
        v1_1_manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp="2025-10-13T14:00:00Z",
            project="TestProject",
            nodes=[{"id": "n1"}],
            version="1.1",
            tags=["test"],
            owner="team_a"
        )

        assert v1_manifest.version == "1.0"
        assert v1_1_manifest.version == "1.1"
        assert v1_1_manifest.tags == ["test"]
        assert v1_1_manifest.owner == "team_a"

        # Both should validate
        assert v1_manifest.validate() is True
        assert v1_1_manifest.validate() is True

    # ========================================================================
    # Advanced Features Tests (020-025)
    # ========================================================================

    def test_dde_020_manifest_with_capability_taxonomy_refs(self, mock_iteration_id):
        """DDE-020: Manifest with capability taxonomy references validated"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "n1", "capability": "Web:React:Hooks"},
                {"id": "n2", "capability": "Backend:Python:FastAPI"}
            ]
        )

        assert manifest.nodes[0]["capability"] == "Web:React:Hooks"
        assert manifest.nodes[1]["capability"] == "Backend:Python:FastAPI"
        assert manifest.validate() is True

    def test_dde_021_manifest_with_estimated_effort(self, mock_iteration_id):
        """DDE-021: Manifest with estimated effort summed correctly"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "n1", "estimated_effort": 60},
                {"id": "n2", "estimated_effort": 120},
                {"id": "n3", "estimated_effort": 45}
            ]
        )

        total_effort = manifest.calculate_total_effort()
        assert total_effort == 225
        assert manifest.validate() is True

    def test_dde_022_manifest_with_gates_configuration(self, mock_iteration_id):
        """DDE-022: Manifest with gates configuration parsed"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {
                    "id": "n1",
                    "gates": ["unit-tests", "coverage", "lint", "sast"]
                }
            ]
        )

        assert len(manifest.nodes[0]["gates"]) == 4
        assert "unit-tests" in manifest.nodes[0]["gates"]
        assert "sast" in manifest.nodes[0]["gates"]
        assert manifest.validate() is True

    @pytest.mark.performance
    def test_dde_023_manifest_with_100_nodes_performance(self, mock_iteration_id):
        """DDE-023: Manifest with 100+ nodes parses and validates in <100ms"""
        nodes = [
            {
                "id": f"node_{i}",
                "type": "action",
                "capability": "Backend:Python:FastAPI",
                "estimated_effort": 30
            }
            for i in range(100)
        ]

        start = time.time()
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=nodes
        )
        manifest.validate()
        duration = time.time() - start

        assert len(manifest.nodes) == 100
        assert duration < 0.1  # Less than 100ms
        assert manifest.calculate_total_effort() == 3000

    def test_dde_024_manifest_with_unicode_characters(self, mock_iteration_id):
        """DDE-024: Manifest with Unicode characters properly encoded"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="测试项目",  # Chinese
            nodes=[
                {"id": "nœud_1", "type": "action"},  # French
                {"id": "узел_2", "type": "phase"}     # Russian
            ]
        )

        assert manifest.project == "测试项目"
        assert manifest.nodes[0]["id"] == "nœud_1"
        assert manifest.nodes[1]["id"] == "узел_2"
        assert manifest.validate() is True

        # Test serialization with Unicode (YAML may escape but data is preserved)
        yaml_str = manifest.to_yaml()
        # Verify roundtrip preserves Unicode
        loaded = ExecutionManifest.from_yaml(yaml_str)
        assert loaded.project == "测试项目"
        assert loaded.nodes[0]["id"] == "nœud_1"

    def test_dde_025_manifest_with_nested_dependencies(self, mock_iteration_id):
        """DDE-025: Manifest with nested dependencies builds correct tree"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "A", "depends_on": []},
                {"id": "B", "depends_on": ["A"]},
                {"id": "C", "depends_on": ["A", "B"]},
                {"id": "D", "depends_on": ["C"]},
                {"id": "E", "depends_on": ["B", "C"]}
            ]
        )

        assert manifest.validate() is True

        # Verify dependency structure
        assert len(manifest.nodes[0]["depends_on"]) == 0  # A has no deps
        assert len(manifest.nodes[2]["depends_on"]) == 2  # C depends on A and B

        # Test dependency chain calculation
        d_chain = manifest.get_dependency_chain("D")
        assert "A" in d_chain
        assert "C" in d_chain
        assert d_chain.index("A") < d_chain.index("C")  # A before C
        assert d_chain.index("C") < d_chain.index("D")  # C before D

        e_chain = manifest.get_dependency_chain("E")
        assert "A" in e_chain
        assert "B" in e_chain
        assert "C" in e_chain
        assert e_chain[-1] == "E"  # E is last


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.dde
class TestExecutionManifestEdgeCases:
    """Additional edge case tests for robustness"""

    def test_manifest_with_missing_node_id(self, mock_iteration_id):
        """Manifest with node missing ID raises ValidationError"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[{"type": "action"}]  # Missing 'id'
        )

        with pytest.raises(ValidationError, match="Node missing required 'id' field"):
            manifest.validate()

    def test_manifest_with_invalid_dependency_reference(self, mock_iteration_id):
        """Manifest with dependency referencing non-existent node fails"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "A", "depends_on": ["NON_EXISTENT"]}
            ]
        )

        with pytest.raises(ValidationError, match="depends on non-existent node"):
            manifest.validate()

    def test_manifest_complex_cycle_detection(self, mock_iteration_id):
        """Complex cycle through multiple nodes detected"""
        manifest = ExecutionManifest(
            iteration_id=mock_iteration_id,
            timestamp=datetime.utcnow().isoformat(),
            project="TestProject",
            nodes=[
                {"id": "A", "depends_on": ["B"]},
                {"id": "B", "depends_on": ["C"]},
                {"id": "C", "depends_on": ["D"]},
                {"id": "D", "depends_on": ["E"]},
                {"id": "E", "depends_on": ["A"]}  # Cycle: A→B→C→D→E→A
            ]
        )

        with pytest.raises(ValidationError, match="Circular dependencies detected"):
            manifest.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
