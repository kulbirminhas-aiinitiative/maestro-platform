"""
DAG Workflow Validator Service

Validates DAG structure, detects issues, and provides auto-fix suggestions.
Ensures all workflows (internal, external, blueprints) meet quality standards.

Author: Maestro Platform Team
Date: October 19, 2025
"""

import logging
from typing import Dict, List, Any, Set, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Issue severity levels"""
    ERROR = "error"      # Blocks execution
    WARNING = "warning"  # Can execute but not recommended
    INFO = "info"        # Best practice suggestions


class IssueType(str, Enum):
    """Types of validation issues"""
    CYCLE = "cycle"
    ORPHANED_NODE = "orphaned_node"
    MISSING_FIELD = "missing_field"
    INVALID_EDGE = "invalid_edge"
    INVALID_PHASE_TYPE = "invalid_phase_type"
    DUPLICATE_ID = "duplicate_id"
    MISSING_CONFIG = "missing_config"
    INVALID_CONFIG = "invalid_config"
    EMPTY_WORKFLOW = "empty_workflow"
    MISSING_TEAM = "missing_team"
    MISSING_AI = "missing_ai"


@dataclass
class ValidationIssue:
    """Represents a validation issue in the DAG"""
    severity: IssueSeverity
    issue_type: IssueType
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    field: Optional[str] = None
    auto_fixable: bool = False
    fix_description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "severity": self.severity.value,
            "issue_type": self.issue_type.value,
            "message": self.message,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "field": self.field,
            "auto_fixable": self.auto_fixable,
            "fix_description": self.fix_description
        }


class DAGValidator:
    """Validates DAG workflow structure and configuration"""

    # Valid phase types
    VALID_PHASE_TYPES = {
        "requirements", "architecture", "implementation", "testing",
        "deployment", "monitoring", "documentation", "review",
        "planning", "design", "qa", "security", "optimization"
    }

    # Required fields for nodes
    REQUIRED_NODE_FIELDS = {"id", "phase_type", "label"}

    # Required fields in phase_config
    REQUIRED_CONFIG_FIELDS = {"assigned_team", "executor_ai"}

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate(self, workflow: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate a complete workflow

        Args:
            workflow: Workflow dictionary with nodes and edges

        Returns:
            List of validation issues found
        """
        self.issues = []

        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])

        # Run all validation checks
        self._validate_empty_workflow(nodes)
        self._validate_node_structure(nodes)
        self._validate_duplicate_ids(nodes)
        self._validate_phase_types(nodes)
        self._validate_phase_configs(nodes)
        self._validate_edges(nodes, edges)
        self._validate_cycles(nodes, edges)
        self._validate_orphaned_nodes(nodes, edges)

        logger.info(f"Validation complete: {len(self.issues)} issues found")
        return self.issues

    def _validate_empty_workflow(self, nodes: List[Dict]) -> None:
        """Check if workflow has at least one node"""
        if not nodes or len(nodes) == 0:
            self.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                issue_type=IssueType.EMPTY_WORKFLOW,
                message="Workflow must contain at least one phase node",
                auto_fixable=False
            ))

    def _validate_node_structure(self, nodes: List[Dict]) -> None:
        """Validate that all nodes have required fields"""
        for node in nodes:
            node_id = node.get("id", "unknown")

            # Check required fields
            for field in self.REQUIRED_NODE_FIELDS:
                if field not in node or not node[field]:
                    self.issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        issue_type=IssueType.MISSING_FIELD,
                        message=f"Node '{node_id}' is missing required field '{field}'",
                        node_id=node_id,
                        field=field,
                        auto_fixable=field == "label",
                        fix_description=f"Set default label based on phase_type" if field == "label" else None
                    ))

    def _validate_duplicate_ids(self, nodes: List[Dict]) -> None:
        """Check for duplicate node IDs"""
        seen_ids: Set[str] = set()

        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue

            if node_id in seen_ids:
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    issue_type=IssueType.DUPLICATE_ID,
                    message=f"Duplicate node ID found: '{node_id}'",
                    node_id=node_id,
                    auto_fixable=True,
                    fix_description="Generate unique ID for duplicate nodes"
                ))

            seen_ids.add(node_id)

    def _validate_phase_types(self, nodes: List[Dict]) -> None:
        """Validate that phase types are valid"""
        for node in nodes:
            node_id = node.get("id", "unknown")
            phase_type = node.get("phase_type")

            if not phase_type:
                continue

            if phase_type not in self.VALID_PHASE_TYPES:
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    issue_type=IssueType.INVALID_PHASE_TYPE,
                    message=f"Node '{node_id}' has unknown phase_type: '{phase_type}'",
                    node_id=node_id,
                    field="phase_type",
                    auto_fixable=False
                ))

    def _validate_phase_configs(self, nodes: List[Dict]) -> None:
        """Validate phase_config structure"""
        for node in nodes:
            node_id = node.get("id", "unknown")
            phase_config = node.get("phase_config", {})

            if not phase_config or not isinstance(phase_config, dict):
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    issue_type=IssueType.MISSING_CONFIG,
                    message=f"Node '{node_id}' is missing phase_config",
                    node_id=node_id,
                    field="phase_config",
                    auto_fixable=True,
                    fix_description="Create default phase_config with required fields"
                ))
                continue

            # Check required config fields
            if "assigned_team" not in phase_config or not phase_config["assigned_team"]:
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    issue_type=IssueType.MISSING_TEAM,
                    message=f"Node '{node_id}' has no assigned team",
                    node_id=node_id,
                    field="phase_config.assigned_team",
                    auto_fixable=True,
                    fix_description="Assign default team based on phase_type"
                ))

            if "executor_ai" not in phase_config or not phase_config["executor_ai"]:
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    issue_type=IssueType.MISSING_AI,
                    message=f"Node '{node_id}' has no executor AI specified",
                    node_id=node_id,
                    field="phase_config.executor_ai",
                    auto_fixable=True,
                    fix_description="Set default AI model (claude-3-5-sonnet-20241022)"
                ))

    def _validate_edges(self, nodes: List[Dict], edges: List[Dict]) -> None:
        """Validate that all edges connect to existing nodes"""
        node_ids = {node.get("id") for node in nodes}

        for idx, edge in enumerate(edges):
            source = edge.get("source")
            target = edge.get("target")
            edge_id = edge.get("id", f"edge-{idx}")

            if not source or source not in node_ids:
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    issue_type=IssueType.INVALID_EDGE,
                    message=f"Edge '{edge_id}' has invalid source: '{source}'",
                    edge_id=edge_id,
                    auto_fixable=True,
                    fix_description="Remove edge with invalid source"
                ))

            if not target or target not in node_ids:
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    issue_type=IssueType.INVALID_EDGE,
                    message=f"Edge '{edge_id}' has invalid target: '{target}'",
                    edge_id=edge_id,
                    auto_fixable=True,
                    fix_description="Remove edge with invalid target"
                ))

    def _validate_cycles(self, nodes: List[Dict], edges: List[Dict]) -> None:
        """Detect cycles in the DAG"""
        if not edges:
            return

        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        for node in nodes:
            node_id = node.get("id")
            if node_id:
                graph[node_id] = []

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target and source in graph:
                graph[source].append(target)

        # DFS to detect cycles
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(node: str, path: List[str]) -> Optional[List[str]]:
            """DFS helper to detect cycle and return path"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle_path = has_cycle(neighbor, path.copy())
                    if cycle_path:
                        return cycle_path
                elif neighbor in rec_stack:
                    # Cycle found
                    cycle_start_idx = path.index(neighbor)
                    return path[cycle_start_idx:] + [neighbor]

            rec_stack.remove(node)
            return None

        for node_id in graph:
            if node_id not in visited:
                cycle_path = has_cycle(node_id, [])
                if cycle_path:
                    cycle_str = " → ".join(cycle_path)
                    self.issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        issue_type=IssueType.CYCLE,
                        message=f"Cycle detected in workflow: {cycle_str}",
                        node_id=cycle_path[0] if cycle_path else None,
                        auto_fixable=False
                    ))
                    break  # Report only first cycle

    def _validate_orphaned_nodes(self, nodes: List[Dict], edges: List[Dict]) -> None:
        """Detect orphaned nodes (nodes with no incoming or outgoing edges)"""
        if len(nodes) <= 1:
            return  # Single node or empty is OK

        node_ids = {node.get("id") for node in nodes}
        connected_nodes: Set[str] = set()

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source:
                connected_nodes.add(source)
            if target:
                connected_nodes.add(target)

        orphaned = node_ids - connected_nodes

        for node_id in orphaned:
            if node_id:
                self.issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    issue_type=IssueType.ORPHANED_NODE,
                    message=f"Node '{node_id}' has no connections (orphaned)",
                    node_id=node_id,
                    auto_fixable=True,
                    fix_description="Remove orphaned node or connect it to the workflow"
                ))

    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary statistics"""
        errors = sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)
        info = sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)
        auto_fixable = sum(1 for i in self.issues if i.auto_fixable)

        return {
            "total_issues": len(self.issues),
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "auto_fixable": auto_fixable,
            "is_valid": errors == 0
        }


# Singleton instance
_validator_instance = None

def get_validator() -> DAGValidator:
    """Get or create validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DAGValidator()
    return _validator_instance
