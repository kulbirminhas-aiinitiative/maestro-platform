"""
DAG Workflow Auto-Fixer

Automatically fixes common DAG validation issues.
Provides intelligent repairs for structural and configuration problems.

Author: Maestro Platform Team
Date: October 19, 2025
"""

import logging
import uuid
from typing import Dict, List, Any, Set, Tuple
from copy import deepcopy

from dag_validator_service import (
    DAGValidator,
    ValidationIssue,
    IssueType,
    IssueSeverity
)

logger = logging.getLogger(__name__)


class DAGAutoFixer:
    """Automatically fixes DAG validation issues"""

    # Default AI model
    DEFAULT_AI_MODEL = "claude-3-5-sonnet-20241022"

    # Phase type to default team mapping
    PHASE_TYPE_TEAMS = {
        "requirements": ["Product Manager", "Business Analyst"],
        "architecture": ["System Architect", "Tech Lead"],
        "implementation": ["Software Engineer", "Developer"],
        "testing": ["QA Engineer", "Test Automation Engineer"],
        "deployment": ["DevOps Engineer", "Site Reliability Engineer"],
        "monitoring": ["DevOps Engineer", "System Administrator"],
        "documentation": ["Technical Writer", "Developer"],
        "review": ["Tech Lead", "Senior Engineer"],
        "planning": ["Project Manager", "Product Manager"],
        "design": ["UX Designer", "UI Designer"],
        "qa": ["QA Engineer", "Quality Assurance Lead"],
        "security": ["Security Engineer", "Security Analyst"],
        "optimization": ["Performance Engineer", "Software Engineer"]
    }

    def __init__(self):
        self.fixes_applied: List[str] = []

    def auto_fix(self, workflow: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Automatically fix workflow issues

        Args:
            workflow: Workflow dictionary with nodes and edges

        Returns:
            Tuple of (fixed_workflow, list_of_fixes_applied)
        """
        self.fixes_applied = []
        fixed_workflow = deepcopy(workflow)

        # Validate first to identify issues
        validator = DAGValidator()
        issues = validator.validate(fixed_workflow)

        # Apply fixes for auto-fixable issues
        for issue in issues:
            if issue.auto_fixable:
                self._apply_fix(fixed_workflow, issue)

        logger.info(f"Auto-fix complete: {len(self.fixes_applied)} fixes applied")
        return fixed_workflow, self.fixes_applied

    def _apply_fix(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """Apply a specific fix based on issue type"""
        try:
            if issue.issue_type == IssueType.INVALID_EDGE:
                self._fix_invalid_edge(workflow, issue)
            elif issue.issue_type == IssueType.DUPLICATE_ID:
                self._fix_duplicate_id(workflow, issue)
            elif issue.issue_type == IssueType.MISSING_FIELD:
                self._fix_missing_field(workflow, issue)
            elif issue.issue_type == IssueType.MISSING_CONFIG:
                self._fix_missing_config(workflow, issue)
            elif issue.issue_type == IssueType.MISSING_TEAM:
                self._fix_missing_team(workflow, issue)
            elif issue.issue_type == IssueType.MISSING_AI:
                self._fix_missing_ai(workflow, issue)
            elif issue.issue_type == IssueType.ORPHANED_NODE:
                self._fix_orphaned_node(workflow, issue)
        except Exception as e:
            logger.error(f"Failed to apply fix for {issue.issue_type}: {e}")

    def _fix_invalid_edge(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """Remove invalid edges"""
        edges = workflow.get("edges", [])
        edge_id = issue.edge_id

        # Extract message to find the invalid target/source
        # Message format: "Edge 'edge-X' has invalid target: 'node-Y'"
        nodes = workflow.get("nodes", [])
        node_ids = {node.get("id") for node in nodes}

        # Remove edges that have invalid source or target
        original_count = len(edges)
        valid_edges = []
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in node_ids and target in node_ids:
                valid_edges.append(edge)
            else:
                logger.info(f"Removing invalid edge: {source} -> {target}")

        workflow["edges"] = valid_edges

        if len(workflow["edges"]) < original_count:
            removed_count = original_count - len(workflow["edges"])
            self.fixes_applied.append(f"Removed {removed_count} invalid edge(s)")
            logger.info(f"Fixed: Removed {removed_count} invalid edge(s)")

    def _fix_duplicate_id(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """Generate unique IDs for duplicate nodes"""
        nodes = workflow.get("nodes", [])
        node_id = issue.node_id

        # Find all nodes with duplicate ID
        duplicates = [n for n in nodes if n.get("id") == node_id]

        if len(duplicates) > 1:
            # Keep first, rename others
            for i, node in enumerate(duplicates[1:], start=1):
                new_id = f"{node_id}-{uuid.uuid4().hex[:8]}"
                old_id = node["id"]
                node["id"] = new_id

                # Update edges referencing this node
                for edge in workflow.get("edges", []):
                    if edge.get("source") == old_id:
                        edge["source"] = new_id
                    if edge.get("target") == old_id:
                        edge["target"] = new_id

                self.fixes_applied.append(f"Renamed duplicate node '{old_id}' to '{new_id}'")
                logger.info(f"Fixed: Renamed duplicate node {old_id} → {new_id}")

    def _fix_missing_field(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """Add missing required fields with defaults"""
        nodes = workflow.get("nodes", [])
        node_id = issue.node_id
        field = issue.field

        for node in nodes:
            if node.get("id") == node_id:
                if field == "label":
                    # Generate label from phase_type
                    phase_type = node.get("phase_type", "Unknown")
                    node["label"] = phase_type.replace("_", " ").title()
                    self.fixes_applied.append(f"Added missing label to node '{node_id}'")
                    logger.info(f"Fixed: Added label to node {node_id}")
                break

    def _fix_missing_config(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """Create default phase_config"""
        nodes = workflow.get("nodes", [])
        node_id = issue.node_id

        for node in nodes:
            if node.get("id") == node_id:
                phase_type = node.get("phase_type", "implementation")

                node["phase_config"] = {
                    "assigned_team": self.PHASE_TYPE_TEAMS.get(
                        phase_type,
                        ["Software Engineer"]
                    ),
                    "executor_ai": self.DEFAULT_AI_MODEL,
                    "requirementText": f"Default requirements for {phase_type} phase"
                }

                self.fixes_applied.append(f"Created default phase_config for node '{node_id}'")
                logger.info(f"Fixed: Added phase_config to node {node_id}")
                break

    def _fix_missing_team(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """Assign default team based on phase_type"""
        nodes = workflow.get("nodes", [])
        node_id = issue.node_id

        for node in nodes:
            if node.get("id") == node_id:
                phase_type = node.get("phase_type", "implementation")
                phase_config = node.get("phase_config", {})

                default_team = self.PHASE_TYPE_TEAMS.get(
                    phase_type,
                    ["Software Engineer"]
                )

                phase_config["assigned_team"] = default_team
                node["phase_config"] = phase_config

                self.fixes_applied.append(
                    f"Assigned default team to node '{node_id}': {default_team}"
                )
                logger.info(f"Fixed: Added team to node {node_id}")
                break

    def _fix_missing_ai(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """Set default AI model"""
        nodes = workflow.get("nodes", [])
        node_id = issue.node_id

        for node in nodes:
            if node.get("id") == node_id:
                phase_config = node.get("phase_config", {})
                phase_config["executor_ai"] = self.DEFAULT_AI_MODEL
                node["phase_config"] = phase_config

                self.fixes_applied.append(
                    f"Set default AI model for node '{node_id}': {self.DEFAULT_AI_MODEL}"
                )
                logger.info(f"Fixed: Added executor_ai to node {node_id}")
                break

    def _fix_orphaned_node(self, workflow: Dict[str, Any], issue: ValidationIssue) -> None:
        """
        Handle orphaned nodes - mark for user attention rather than auto-delete
        (User might want to connect it)
        """
        # For now, just log - don't auto-delete as user might want to connect it
        logger.info(f"Orphaned node detected: {issue.node_id} (not auto-removed)")
        self.fixes_applied.append(
            f"Note: Node '{issue.node_id}' is orphaned - consider connecting it or removing it"
        )


def auto_fix_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to auto-fix a workflow

    Args:
        workflow: Workflow dictionary

    Returns:
        Fixed workflow with applied fixes
    """
    fixer = DAGAutoFixer()
    fixed_workflow, fixes = fixer.auto_fix(workflow)

    return {
        "workflow": fixed_workflow,
        "fixes_applied": fixes,
        "fix_count": len(fixes)
    }
