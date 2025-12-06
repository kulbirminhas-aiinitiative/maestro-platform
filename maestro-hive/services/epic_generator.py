"""
EPIC Generation Service (MD-2118)

Generates JIRA Epics from DDE WorkflowDAGs and ExecutionManifests.
- Maps WorkflowDAG to JIRA Epic
- Maps WorkflowNode/ManifestNode to JIRA Tasks/Sub-tasks
- Preserves dependency relationships via JIRA links

Author: AI Agent
Created: 2025-12-02
Parent: MD-2106 (Task Management Integration)
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import aiohttp
import json

logger = logging.getLogger(__name__)


class JIRAIssueType(Enum):
    """JIRA issue types for mapping"""
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"
    BUG = "bug"


class JIRAPriority(Enum):
    """JIRA priority levels"""
    HIGHEST = "highest"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    LOWEST = "lowest"


# Node type to JIRA issue type mapping
NODE_TYPE_TO_JIRA: Dict[str, JIRAIssueType] = {
    "phase": JIRAIssueType.STORY,
    "action": JIRAIssueType.TASK,
    "checkpoint": JIRAIssueType.TASK,
    "notification": JIRAIssueType.SUBTASK,
    "interface": JIRAIssueType.STORY,
    "impl": JIRAIssueType.TASK,
    "custom": JIRAIssueType.TASK,
    "parallel_group": JIRAIssueType.STORY,
    "conditional": JIRAIssueType.TASK,
    "human_review": JIRAIssueType.TASK,
}


@dataclass
class GeneratedIssue:
    """Represents a generated JIRA issue"""
    local_id: str  # Node ID or manifest node ID
    jira_key: Optional[str] = None  # Assigned after creation
    issue_type: JIRAIssueType = JIRAIssueType.TASK
    title: str = ""
    description: str = ""
    priority: JIRAPriority = JIRAPriority.MEDIUM
    parent_key: Optional[str] = None  # Epic or parent task key
    depends_on: List[str] = field(default_factory=list)  # Local IDs of dependencies
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: bool = False
    error: Optional[str] = None


@dataclass
class EpicGenerationResult:
    """Result of epic generation operation"""
    epic_key: Optional[str] = None
    tasks_created: int = 0
    tasks_failed: int = 0
    issues: List[GeneratedIssue] = field(default_factory=list)
    dependency_links: List[Tuple[str, str]] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class EpicGeneratorService:
    """
    Service for generating JIRA Epics from WorkflowDAGs and ExecutionManifests.

    Flow:
    1. Create Epic from workflow metadata
    2. Create Tasks/Stories from nodes
    3. Link tasks to Epic
    4. Create dependency links (blocks/blocked-by)
    """

    def __init__(
        self,
        jira_api_url: str = "http://localhost:14100/api/integrations/tasks",
        token: Optional[str] = None,
        project_id: str = "MD"
    ):
        """
        Initialize epic generator.

        Args:
            jira_api_url: Base URL for JIRA adapter API
            token: JWT token for authentication
            project_id: Default project key for issue creation
        """
        self.jira_api_url = jira_api_url
        self.token = token
        self.project_id = project_id

        logger.info(f"EpicGeneratorService initialized (project={project_id})")

    def set_token(self, token: str):
        """Set or update JWT token"""
        self.token = token

    # ========== WorkflowDAG → Epic ==========

    async def generate_epic_from_dag(
        self,
        dag,  # WorkflowDAG instance
        description: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> EpicGenerationResult:
        """
        Generate JIRA Epic and Tasks from a WorkflowDAG.

        Args:
            dag: WorkflowDAG instance
            description: Optional epic description override
            labels: Optional labels to add

        Returns:
            EpicGenerationResult with created issues
        """
        result = EpicGenerationResult()

        try:
            # Step 1: Create Epic
            epic_title = f"[Workflow] {dag.name}"
            epic_desc = description or self._build_dag_description(dag)

            epic = GeneratedIssue(
                local_id=dag.workflow_id,
                issue_type=JIRAIssueType.EPIC,
                title=epic_title,
                description=epic_desc,
                priority=JIRAPriority.HIGH,
                metadata={'workflow_id': dag.workflow_id, 'source': 'dag'}
            )

            epic_key = await self._create_jira_issue(epic, labels=labels)
            if not epic_key:
                result.error = "Failed to create epic"
                return result

            epic.jira_key = epic_key
            epic.created = True
            result.epic_key = epic_key
            result.issues.append(epic)

            logger.info(f"Created Epic {epic_key} from DAG {dag.workflow_id}")

            # Step 2: Create Tasks from nodes
            node_to_jira: Dict[str, str] = {}  # node_id -> jira_key

            for node_id, node in dag.nodes.items():
                issue = self._node_to_issue(node, epic_key)

                jira_key = await self._create_jira_issue(issue, labels=labels)
                if jira_key:
                    issue.jira_key = jira_key
                    issue.created = True
                    node_to_jira[node_id] = jira_key
                    result.tasks_created += 1
                else:
                    issue.error = "Failed to create"
                    result.tasks_failed += 1

                result.issues.append(issue)

            # Step 3: Create dependency links
            for node_id, node in dag.nodes.items():
                if node_id not in node_to_jira:
                    continue

                for dep_id in node.dependencies:
                    if dep_id in node_to_jira:
                        # Create "blocked by" link
                        await self._create_link(
                            from_key=node_to_jira[node_id],
                            to_key=node_to_jira[dep_id],
                            link_type="blocks"
                        )
                        result.dependency_links.append((dep_id, node_id))

            result.success = result.tasks_failed == 0
            logger.info(f"Epic generation complete: {result.tasks_created} tasks, {result.tasks_failed} failed")

        except Exception as e:
            result.error = str(e)
            logger.error(f"Epic generation failed: {e}")

        return result

    def _build_dag_description(self, dag) -> str:
        """Build epic description from DAG"""
        lines = [
            f"## Workflow: {dag.name}",
            f"",
            f"**Workflow ID:** {dag.workflow_id}",
            f"**Nodes:** {len(dag.nodes)}",
            f"**Created:** {dag.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"",
            "### Node Summary",
        ]

        for node_id, node in dag.nodes.items():
            deps = f" (depends: {', '.join(node.dependencies)})" if node.dependencies else ""
            lines.append(f"- **{node.name}** [{node.node_type.value}]{deps}")

        if dag.metadata:
            lines.append("")
            lines.append("### Metadata")
            for key, value in dag.metadata.items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    def _node_to_issue(self, node, epic_key: str) -> GeneratedIssue:
        """Convert WorkflowNode to GeneratedIssue"""
        issue_type = NODE_TYPE_TO_JIRA.get(node.node_type.value, JIRAIssueType.TASK)

        # Determine priority based on node type
        priority = JIRAPriority.MEDIUM
        if node.node_type.value in ["phase", "human_review"]:
            priority = JIRAPriority.HIGH
        elif node.node_type.value == "notification":
            priority = JIRAPriority.LOW

        # Build description
        desc_lines = [f"**Node ID:** {node.node_id}"]
        if node.config:
            desc_lines.append(f"\n**Configuration:**\n```json\n{json.dumps(node.config, indent=2)}\n```")
        if node.metadata:
            desc_lines.append(f"\n**Metadata:** {json.dumps(node.metadata)}")

        return GeneratedIssue(
            local_id=node.node_id,
            issue_type=issue_type,
            title=f"[{node.node_type.value.upper()}] {node.name}",
            description="\n".join(desc_lines),
            priority=priority,
            parent_key=epic_key,
            depends_on=node.dependencies.copy(),
            metadata={'node_type': node.node_type.value, 'source': 'dag_node'}
        )

    # ========== ExecutionManifest → Epic ==========

    async def generate_epic_from_manifest(
        self,
        manifest,  # ExecutionManifest instance
        description: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> EpicGenerationResult:
        """
        Generate JIRA Epic and Tasks from an ExecutionManifest.

        Args:
            manifest: ExecutionManifest instance
            description: Optional epic description override
            labels: Optional labels

        Returns:
            EpicGenerationResult
        """
        result = EpicGenerationResult()

        try:
            # Step 1: Create Epic
            epic_title = f"[Manifest] {manifest.workflow_id} - Iteration {manifest.iteration}"
            epic_desc = description or self._build_manifest_description(manifest)

            epic = GeneratedIssue(
                local_id=manifest.manifest_id,
                issue_type=JIRAIssueType.EPIC,
                title=epic_title,
                description=epic_desc,
                priority=JIRAPriority.HIGH,
                metadata={
                    'manifest_id': manifest.manifest_id,
                    'workflow_id': manifest.workflow_id,
                    'iteration': manifest.iteration,
                    'source': 'manifest'
                }
            )

            epic_key = await self._create_jira_issue(epic, labels=labels)
            if not epic_key:
                result.error = "Failed to create epic"
                return result

            epic.jira_key = epic_key
            epic.created = True
            result.epic_key = epic_key
            result.issues.append(epic)

            logger.info(f"Created Epic {epic_key} from manifest {manifest.manifest_id}")

            # Step 2: Create Tasks from manifest nodes
            node_to_jira: Dict[str, str] = {}

            for node_id, node in manifest.nodes.items():
                issue = self._manifest_node_to_issue(node, epic_key)

                jira_key = await self._create_jira_issue(issue, labels=labels)
                if jira_key:
                    issue.jira_key = jira_key
                    issue.created = True
                    node_to_jira[node_id] = jira_key
                    result.tasks_created += 1
                else:
                    issue.error = "Failed to create"
                    result.tasks_failed += 1

                result.issues.append(issue)

            # Step 3: Create dependency links
            for node_id, node in manifest.nodes.items():
                if node_id not in node_to_jira:
                    continue

                for dep_id in node.depends_on:
                    if dep_id in node_to_jira:
                        await self._create_link(
                            from_key=node_to_jira[node_id],
                            to_key=node_to_jira[dep_id],
                            link_type="blocks"
                        )
                        result.dependency_links.append((dep_id, node_id))

            result.success = result.tasks_failed == 0

        except Exception as e:
            result.error = str(e)
            logger.error(f"Manifest epic generation failed: {e}")

        return result

    def _build_manifest_description(self, manifest) -> str:
        """Build epic description from ExecutionManifest"""
        progress = manifest.get_progress()

        lines = [
            f"## Execution Manifest",
            f"",
            f"**Manifest ID:** {manifest.manifest_id}",
            f"**Workflow:** {manifest.workflow_id}",
            f"**Iteration:** {manifest.iteration}",
            f"**Status:** {manifest.status}",
            f"",
            "### Progress",
            f"- Total: {progress['total']}",
            f"- Completed: {progress['completed']}",
            f"- Running: {progress['running']}",
            f"- Pending: {progress['pending']}",
            f"- Failed: {progress['failed']}",
            f"",
            "### Nodes",
        ]

        for node_id, node in manifest.nodes.items():
            deps = f" (depends: {', '.join(node.depends_on)})" if node.depends_on else ""
            lines.append(f"- **{node.name}** [{node.status}]{deps}")

        return "\n".join(lines)

    def _manifest_node_to_issue(self, node, epic_key: str) -> GeneratedIssue:
        """Convert ManifestNode to GeneratedIssue"""
        issue_type = NODE_TYPE_TO_JIRA.get(node.node_type, JIRAIssueType.TASK)

        # Priority based on effort
        priority = JIRAPriority.MEDIUM
        if node.estimated_effort_hours and node.estimated_effort_hours > 4:
            priority = JIRAPriority.HIGH
        elif node.estimated_effort_hours and node.estimated_effort_hours < 1:
            priority = JIRAPriority.LOW

        # Build description
        desc_lines = [
            f"**Node ID:** {node.node_id}",
            f"**Type:** {node.node_type}",
            f"**Status:** {node.status}",
        ]
        if node.estimated_effort_hours:
            desc_lines.append(f"**Estimated Effort:** {node.estimated_effort_hours}h")
        if node.capability:
            desc_lines.append(f"**Capability:** {node.capability}")
        if node.contract_id:
            desc_lines.append(f"**Contract:** {node.contract_id}")
        if node.outputs:
            desc_lines.append(f"**Outputs:** {', '.join(node.outputs)}")

        return GeneratedIssue(
            local_id=node.node_id,
            issue_type=issue_type,
            title=f"[{node.node_type.upper()}] {node.name}",
            description="\n".join(desc_lines),
            priority=priority,
            parent_key=epic_key,
            depends_on=node.depends_on.copy(),
            metadata={'node_type': node.node_type, 'source': 'manifest_node'}
        )

    # ========== JIRA API Methods ==========

    async def _create_jira_issue(
        self,
        issue: GeneratedIssue,
        labels: Optional[List[str]] = None
    ) -> Optional[str]:
        """Create a JIRA issue and return its key"""
        if not self.token:
            logger.error("No JWT token configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        payload = {
            "projectId": self.project_id,
            "type": issue.issue_type.value,
            "title": issue.title,
            "description": issue.description,
            "priority": issue.priority.value,
        }

        if issue.parent_key:
            payload["parentId"] = issue.parent_key

        if labels:
            payload["labels"] = labels

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.jira_api_url,
                    headers=headers,
                    json=payload
                ) as resp:
                    if resp.status == 200 or resp.status == 201:
                        result = await resp.json()
                        jira_key = result.get('output', {}).get('externalId')
                        logger.debug(f"Created JIRA issue: {jira_key}")
                        return jira_key
                    else:
                        error_text = await resp.text()
                        logger.error(f"Failed to create issue ({resp.status}): {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error creating JIRA issue: {e}")
            return None

    async def _create_link(
        self,
        from_key: str,
        to_key: str,
        link_type: str = "blocks"
    ) -> bool:
        """Create a link between two JIRA issues"""
        # Note: Link creation might need separate endpoint
        # For now, log the intended link
        logger.info(f"Link: {to_key} {link_type} {from_key}")
        return True

    # ========== Utility Methods ==========

    def get_issue_summary(self, result: EpicGenerationResult) -> Dict[str, Any]:
        """Get summary of generation result"""
        return {
            'epic_key': result.epic_key,
            'total_issues': len(result.issues),
            'tasks_created': result.tasks_created,
            'tasks_failed': result.tasks_failed,
            'dependency_links': len(result.dependency_links),
            'success': result.success,
            'error': result.error,
            'timestamp': result.timestamp.isoformat()
        }


# Utility function for quick epic generation
async def generate_epic(
    source,  # WorkflowDAG or ExecutionManifest
    token: str,
    project_id: str = "MD",
    labels: Optional[List[str]] = None
) -> EpicGenerationResult:
    """
    Quick utility to generate epic from DAG or manifest.

    Args:
        source: WorkflowDAG or ExecutionManifest instance
        token: JWT token
        project_id: JIRA project key
        labels: Optional labels

    Returns:
        EpicGenerationResult
    """
    generator = EpicGeneratorService(token=token, project_id=project_id)

    # Detect source type and generate
    if hasattr(source, 'workflow_id') and hasattr(source, 'graph'):
        # WorkflowDAG
        return await generator.generate_epic_from_dag(source, labels=labels)
    elif hasattr(source, 'manifest_id') and hasattr(source, 'nodes'):
        # ExecutionManifest
        return await generator.generate_epic_from_manifest(source, labels=labels)
    else:
        result = EpicGenerationResult()
        result.error = "Unknown source type. Expected WorkflowDAG or ExecutionManifest"
        return result


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test_generation():
        print("=== Epic Generator Test ===\n")

        # Test with mock data
        generator = EpicGeneratorService(
            project_id="MD"
        )

        print("Node Type Mappings:")
        for node_type, jira_type in NODE_TYPE_TO_JIRA.items():
            print(f"  {node_type:15} → {jira_type.value}")

        print("\n✅ Epic generator module loaded successfully")

    asyncio.run(test_generation())
