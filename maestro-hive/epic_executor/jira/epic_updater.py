"""
EPIC Updater for EPIC Executor.

Handles all JIRA EPIC operations:
- Fetching EPIC details and extracting acceptance criteria
- Creating child tasks for each AC
- Updating EPIC description with compliance report
- Posting execution comments
- Linking Confluence pages
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    AcceptanceCriterion,
    ACStatus,
    DocumentInfo,
    EpicInfo,
    ExecutionResult,
)
from .adf_builder import ADFBuilder, ADFDocument, ComplianceReportBuilder


@dataclass
class JiraConfig:
    """Configuration for JIRA API access."""
    base_url: str
    email: str
    api_token: str
    project_key: str = "MD"


class EpicUpdater:
    """
    Handles EPIC-related JIRA operations for the executor.

    This class provides higher-level EPIC operations building on the UTCP JiraTool.
    """

    def __init__(self, config: JiraConfig):
        """
        Initialize the EPIC updater.

        Args:
            config: JIRA configuration with credentials
        """
        self.config = config
        self._jira_tool = None  # Lazy load

    async def _get_jira_tool(self):
        """Lazy load the JIRA tool."""
        if self._jira_tool is None:
            try:
                from utcp.tools.jira_tool import JiraTool
                self._jira_tool = JiraTool({
                    "base_url": self.config.base_url,
                    "email": self.config.email,
                    "api_token": self.config.api_token,
                    "project_key": self.config.project_key,
                })
            except ImportError:
                # Fallback: create minimal JIRA client
                self._jira_tool = MinimalJiraClient(self.config)
        return self._jira_tool

    async def fetch_epic(self, epic_key: str) -> EpicInfo:
        """
        Fetch EPIC details from JIRA.

        Args:
            epic_key: EPIC key (e.g., "MD-2385")

        Returns:
            EpicInfo with parsed details and acceptance criteria
        """
        jira = await self._get_jira_tool()
        result = await jira.get_issue(
            epic_key,
            fields=["summary", "description", "status", "priority", "labels",
                    "created", "updated", "subtasks", "issuelinks"]
        )

        if not result.success:
            raise RuntimeError(f"Failed to fetch EPIC {epic_key}: {result.error}")

        data = result.data
        description = data.get("description", "")

        # Parse acceptance criteria from description
        acceptance_criteria = self._extract_acceptance_criteria(description)

        # Get child tasks
        child_tasks = await self._get_child_tasks(epic_key)

        # Get linked EPICs
        linked_epics = await self._get_linked_epics(epic_key)

        return EpicInfo(
            key=epic_key,
            summary=data.get("summary", ""),
            description=description,
            status=data.get("status", "Unknown"),
            priority=data.get("priority", "Medium"),
            labels=data.get("labels", []),
            acceptance_criteria=acceptance_criteria,
            child_tasks=child_tasks,
            linked_epics=linked_epics,
            created_at=self._parse_datetime(data.get("created")),
            updated_at=self._parse_datetime(data.get("updated")),
        )

    def _extract_acceptance_criteria(self, description: str) -> List[AcceptanceCriterion]:
        """
        Extract acceptance criteria from EPIC description.

        Looks for patterns like:
        - AC-1: Description
        - [ ] Acceptance criterion text
        - * Criterion text (in AC section)
        """
        criteria = []

        # Pattern 1: AC-N: Description
        ac_pattern = re.compile(r'AC-(\d+):\s*(.+?)(?=AC-\d+:|$)', re.IGNORECASE | re.DOTALL)
        for match in ac_pattern.finditer(description):
            ac_id = f"AC-{match.group(1)}"
            ac_desc = match.group(2).strip()
            # Clean up the description
            ac_desc = re.sub(r'\s+', ' ', ac_desc)
            criteria.append(AcceptanceCriterion(
                id=ac_id,
                description=ac_desc,
                status=ACStatus.PENDING
            ))

        # Pattern 2: Bullet points under "Acceptance Criteria" heading
        if not criteria:
            ac_section = re.search(
                r'(?:acceptance\s+criteria|acceptance\s+criterion)[\s:]*(.+?)(?=\n#|\n\*\*|$)',
                description,
                re.IGNORECASE | re.DOTALL
            )
            if ac_section:
                section_text = ac_section.group(1)
                # Extract bullet points
                bullet_pattern = re.compile(r'[*\-]\s*(.+?)(?=\n[*\-]|\n\n|$)')
                for i, match in enumerate(bullet_pattern.finditer(section_text), 1):
                    ac_desc = match.group(1).strip()
                    if ac_desc and len(ac_desc) > 5:  # Skip tiny entries
                        criteria.append(AcceptanceCriterion(
                            id=f"AC-{i}",
                            description=ac_desc,
                            status=ACStatus.PENDING
                        ))

        # Pattern 3: Checkbox items
        if not criteria:
            checkbox_pattern = re.compile(r'\[[\sx]\]\s*(.+?)(?=\n|$)', re.IGNORECASE)
            for i, match in enumerate(checkbox_pattern.finditer(description), 1):
                ac_desc = match.group(1).strip()
                if ac_desc and len(ac_desc) > 5:
                    criteria.append(AcceptanceCriterion(
                        id=f"AC-{i}",
                        description=ac_desc,
                        status=ACStatus.PENDING
                    ))

        # If still no criteria, try to infer from "Gaps to Address" or similar
        if not criteria:
            gaps_section = re.search(
                r'(?:gaps?\s+to\s+address|requirements?|objectives?)[\s:]*(.+?)(?=\n#|\n\*\*|$)',
                description,
                re.IGNORECASE | re.DOTALL
            )
            if gaps_section:
                section_text = gaps_section.group(1)
                numbered_pattern = re.compile(r'\d+[.)]\s*(.+?)(?=\n\d+[.)]|\n\n|$)')
                for i, match in enumerate(numbered_pattern.finditer(section_text), 1):
                    ac_desc = match.group(1).strip()
                    if ac_desc and len(ac_desc) > 5:
                        criteria.append(AcceptanceCriterion(
                            id=f"AC-{i}",
                            description=ac_desc,
                            status=ACStatus.PENDING
                        ))

        return criteria

    async def _get_child_tasks(self, epic_key: str) -> List[str]:
        """Get child task keys for an EPIC."""
        jira = await self._get_jira_tool()
        result = await jira.search_issues(
            jql=f'parent = {epic_key} OR "Epic Link" = {epic_key}',
            max_results=100,
            fields=["key"]
        )
        if result.success:
            return [issue["key"] for issue in result.data.get("issues", [])]
        return []

    async def _get_linked_epics(self, epic_key: str) -> List[str]:
        """
        Get linked EPIC keys (parent EPICs, child EPICs, related EPICs).

        Fetches issue links from JIRA and extracts EPIC relationships including:
        - Parent/Child EPIC links (hierarchical)
        - Epic Link field references
        - "relates to" and "blocks" relationships to other EPICs

        Args:
            epic_key: The EPIC key to find links for

        Returns:
            List of linked EPIC keys
        """
        jira = await self._get_jira_tool()
        linked_epics = []

        try:
            # Fetch issue with links
            result = await jira.get_issue(epic_key, fields=["issuelinks", "parent"])

            if not result.success:
                return []

            data = result.data

            # Check parent field (for sub-EPICs)
            if isinstance(data, dict):
                # Handle MinimalJiraClient which returns flat dict
                parent_key = data.get("parent")
                if parent_key and isinstance(parent_key, str):
                    linked_epics.append(parent_key)

            # For UTCP JiraTool, we need to parse the raw response
            # Make a direct API call to get full issue link data
            if hasattr(jira, '_request'):
                raw_result = await jira._request("GET", f"issue/{epic_key}", params={"fields": "issuelinks,parent"})

                # Extract parent if present
                parent_field = raw_result.get("fields", {}).get("parent")
                if parent_field and isinstance(parent_field, dict):
                    parent_key = parent_field.get("key")
                    if parent_key and parent_key not in linked_epics:
                        linked_epics.append(parent_key)

                # Extract issue links
                issue_links = raw_result.get("fields", {}).get("issuelinks", [])
                for link in issue_links:
                    # Link types that indicate EPIC relationships
                    link_type = link.get("type", {}).get("name", "").lower()
                    relevant_types = ["parent of", "is parent of", "child of", "is child of",
                                     "epic link", "relates to", "blocks", "is blocked by",
                                     "depends on", "is depended on by"]

                    if any(rt in link_type for rt in relevant_types):
                        # Outward link (this EPIC -> other)
                        outward = link.get("outwardIssue", {})
                        if outward:
                            outward_key = outward.get("key")
                            outward_type = outward.get("fields", {}).get("issuetype", {}).get("name", "").lower()
                            if outward_key and outward_key not in linked_epics:
                                # Check if it's an EPIC
                                if "epic" in outward_type or outward_key.startswith(epic_key.split("-")[0]):
                                    linked_epics.append(outward_key)

                        # Inward link (other -> this EPIC)
                        inward = link.get("inwardIssue", {})
                        if inward:
                            inward_key = inward.get("key")
                            inward_type = inward.get("fields", {}).get("issuetype", {}).get("name", "").lower()
                            if inward_key and inward_key not in linked_epics:
                                # Check if it's an EPIC
                                if "epic" in inward_type or inward_key.startswith(epic_key.split("-")[0]):
                                    linked_epics.append(inward_key)

        except Exception as e:
            # Log but don't fail - linked EPICs are supplementary info
            import logging
            logging.warning(f"Failed to fetch linked EPICs for {epic_key}: {e}")

        return linked_epics

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse JIRA datetime string."""
        if not dt_str:
            return None
        try:
            # JIRA format: 2024-01-15T10:30:00.000+0000
            return datetime.fromisoformat(dt_str.replace('+0000', '+00:00').replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

    async def create_child_task(
        self,
        epic_key: str,
        summary: str,
        description: str,
        labels: Optional[List[str]] = None,
        priority: str = "Medium",
    ) -> str:
        """
        Create a child task under the EPIC.

        Args:
            epic_key: Parent EPIC key
            summary: Task summary
            description: Task description
            labels: Optional labels
            priority: Task priority

        Returns:
            Created task key
        """
        jira = await self._get_jira_tool()

        # Build ADF description
        adf_desc = ADFBuilder().paragraph(description).to_dict()

        result = await jira.create_issue(
            project_key=self.config.project_key,
            summary=summary,
            issue_type="Task",
            description=description,
            labels=labels or ["epic-executor", "auto-generated"],
            priority=priority,
            parent_key=epic_key,
        )

        if not result.success:
            raise RuntimeError(f"Failed to create child task: {result.error}")

        return result.data["key"]

    async def create_ac_tasks(
        self,
        epic_key: str,
        acceptance_criteria: List[AcceptanceCriterion],
    ) -> Dict[str, str]:
        """
        Create child tasks for each acceptance criterion.

        Args:
            epic_key: Parent EPIC key
            acceptance_criteria: List of ACs to create tasks for

        Returns:
            Dict mapping AC ID to created task key
        """
        ac_to_task = {}

        for ac in acceptance_criteria:
            if ac.jira_task_key:
                # Already has a task
                ac_to_task[ac.id] = ac.jira_task_key
                continue

            task_key = await self.create_child_task(
                epic_key=epic_key,
                summary=f"[{ac.id}] {ac.description[:80]}...",
                description=f"Acceptance Criterion: {ac.description}\n\nParent EPIC: {epic_key}",
                labels=["acceptance-criteria", "epic-executor"],
            )
            ac_to_task[ac.id] = task_key
            ac.jira_task_key = task_key

        return ac_to_task

    async def update_epic_description(
        self,
        epic_key: str,
        original_description: str,
        compliance_score: float,
        breakdown: Dict[str, Dict[str, Any]],
        gaps: List[str],
        child_tasks: List[str],
        implementation_files: List[str],
        confluence_links: List[str],
    ) -> bool:
        """
        Update EPIC description with compliance report.

        Appends a compliance audit report section to the EPIC description.

        Args:
            epic_key: EPIC key to update
            original_description: Original description to preserve
            compliance_score: Total compliance score
            breakdown: Score breakdown by category
            gaps: Identified gaps
            child_tasks: Created child task keys
            implementation_files: Implementation file paths
            confluence_links: Links to Confluence pages

        Returns:
            True if update succeeded
        """
        jira = await self._get_jira_tool()

        # Build the compliance report
        passing = compliance_score >= 95
        audit_date = datetime.now().strftime("%Y-%m-%d")

        report_builder = ComplianceReportBuilder()
        report = report_builder.build_report(
            score=compliance_score,
            passing=passing,
            audit_date=audit_date,
            breakdown=breakdown,
            gaps=gaps,
            child_tasks=child_tasks,
            implementation_files=implementation_files,
        )

        # Build full description with original + report
        full_desc = ADFBuilder()

        # Add original description as paragraph if it exists
        if original_description:
            full_desc.paragraph(original_description)

        # Add divider
        full_desc.rule()

        # Add compliance report
        full_desc.extend(ADFBuilder().raw(report.to_dict()))

        # Add Confluence links section if present
        if confluence_links:
            full_desc.heading("Documentation Links", level=3)
            full_desc.bullet_list(confluence_links)

        result = await jira.update_issue(
            epic_key,
            fields={"description": full_desc.to_dict()}
        )

        return result.success

    async def post_execution_comment(
        self,
        epic_key: str,
        result: ExecutionResult,
        confluence_links: List[str],
    ) -> Optional[str]:
        """
        Post an execution summary comment to the EPIC.

        Args:
            epic_key: EPIC key
            result: Execution result
            confluence_links: Links to created Confluence pages

        Returns:
            Comment ID if successful
        """
        jira = await self._get_jira_tool()

        summary_builder = ComplianceReportBuilder()
        summary = summary_builder.build_execution_summary(
            epic_key=epic_key,
            success=result.success,
            duration_seconds=result.duration_seconds,
            phases_completed=len([p for p in result.phase_results.values() if p.success]),
            total_phases=len(result.phase_results),
            documents_created=len(result.documents),
            tests_generated=len(result.test_files),
            compliance_score=result.compliance_score.total_score if result.compliance_score else 0,
            confluence_links=confluence_links,
        )

        # The JIRA API expects the comment body directly
        comment_body = summary.to_dict()

        result_obj = await jira._request(
            "POST",
            f"issue/{epic_key}/comment",
            json_data={"body": comment_body}
        )

        return result_obj.get("id")

    async def transition_task_to_done(self, task_key: str) -> bool:
        """
        Transition a task to Done status.

        Args:
            task_key: Task key to transition

        Returns:
            True if transition succeeded
        """
        jira = await self._get_jira_tool()

        # Get available transitions
        transitions_result = await jira.get_transitions(task_key)
        if not transitions_result.success:
            return False

        # Find "Done" transition
        transitions = transitions_result.data.get("transitions", [])
        done_transition = None
        for t in transitions:
            if t["to_status"].lower() in ["done", "closed", "resolved", "complete"]:
                done_transition = t
                break

        if not done_transition:
            return False

        # Execute transition
        result = await jira.transition_issue(
            task_key,
            done_transition["id"],
            comment="Completed by EPIC Executor"
        )

        return result.success

    async def link_confluence_page(
        self,
        epic_key: str,
        page_url: str,
        title: str,
    ) -> bool:
        """
        Add a Confluence page link to the EPIC.

        Note: JIRA web links require the remote link API.

        Args:
            epic_key: EPIC key
            page_url: Confluence page URL
            title: Link title

        Returns:
            True if link was added
        """
        jira = await self._get_jira_tool()

        # Use remote links API
        link_data = {
            "object": {
                "url": page_url,
                "title": title,
                "icon": {
                    "url16x16": "https://www.atlassian.com/favicon.ico",
                    "title": "Confluence"
                }
            }
        }

        try:
            await jira._request(
                "POST",
                f"issue/{epic_key}/remotelink",
                json_data=link_data
            )
            return True
        except Exception:
            return False


class MinimalJiraClient:
    """
    Minimal JIRA client fallback when UTCP tool is not available.

    Provides basic JIRA API operations without full UTCP dependency.
    """

    def __init__(self, config: JiraConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def _get_auth_header(self) -> str:
        """Generate Basic auth header."""
        import base64
        auth_str = f"{self.config.email}:{self.config.api_token}"
        encoded = base64.b64encode(auth_str.encode()).decode()
        return f"Basic {encoded}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to JIRA API."""
        import aiohttp

        url = f"{self.base_url}/rest/api/3/{endpoint}"
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                json=json_data,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise RuntimeError(f"JIRA API error: {response.status} - {error_text}")
                if response.status == 204:
                    return {}
                return await response.json()

    async def get_issue(self, issue_key: str, fields: Optional[List[str]] = None):
        """Get issue details."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]
            error: Optional[str] = None

        try:
            params = {}
            if fields:
                params["fields"] = ",".join(fields)

            result = await self._request("GET", f"issue/{issue_key}", params=params)

            # Extract parent key if present
            parent_field = result["fields"].get("parent")
            parent_key = parent_field.get("key") if isinstance(parent_field, dict) else None

            return Result(
                success=True,
                data={
                    "key": result["key"],
                    "id": result["id"],
                    "summary": result["fields"].get("summary"),
                    "status": result["fields"]["status"]["name"],
                    "priority": result["fields"].get("priority", {}).get("name") if result["fields"].get("priority") else "Medium",
                    "description": self._extract_description(result["fields"].get("description")),
                    "labels": result["fields"].get("labels", []),
                    "created": result["fields"].get("created"),
                    "updated": result["fields"].get("updated"),
                    "parent": parent_key,
                    "issuelinks": result["fields"].get("issuelinks", []),
                }
            )
        except Exception as e:
            return Result(success=False, data={}, error=str(e))

    def _extract_description(self, desc: Any) -> str:
        """Extract text from ADF description."""
        if not desc:
            return ""
        if isinstance(desc, str):
            return desc

        def extract_text(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    return node.get("text", "")
                content = node.get("content", [])
                return " ".join(extract_text(c) for c in content)
            elif isinstance(node, list):
                return " ".join(extract_text(c) for c in node)
            return ""

        return extract_text(desc)

    async def search_issues(self, jql: str, max_results: int = 50, fields: Optional[List[str]] = None):
        """Search issues using JQL."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]
            error: Optional[str] = None

        try:
            data = {
                "jql": jql,
                "maxResults": max_results,
                "fields": fields or ["key", "summary", "status"]
            }

            result = await self._request("POST", "search/jql", json_data=data)

            issues = []
            for issue in result.get("issues", []):
                issues.append({
                    "key": issue["key"],
                    "summary": issue["fields"].get("summary"),
                    "status": issue["fields"]["status"]["name"],
                })

            return Result(success=True, data={"issues": issues, "total": result.get("total", len(issues))})
        except Exception as e:
            return Result(success=False, data={"issues": []}, error=str(e))

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: Optional[str] = None,
        labels: Optional[List[str]] = None,
        priority: Optional[str] = None,
        parent_key: Optional[str] = None,
    ):
        """Create a new issue."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]
            error: Optional[str] = None

        try:
            fields: Dict[str, Any] = {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }

            if description:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": description}]}
                    ]
                }

            if labels:
                fields["labels"] = labels

            if priority:
                fields["priority"] = {"name": priority}

            if parent_key:
                fields["parent"] = {"key": parent_key}

            result = await self._request("POST", "issue", json_data={"fields": fields})

            return Result(success=True, data={"key": result["key"], "id": result["id"]})
        except Exception as e:
            return Result(success=False, data={}, error=str(e))

    async def update_issue(self, issue_key: str, fields: Dict[str, Any]):
        """Update issue fields."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            error: Optional[str] = None

        try:
            await self._request("PUT", f"issue/{issue_key}", json_data={"fields": fields})
            return Result(success=True)
        except Exception as e:
            return Result(success=False, error=str(e))

    async def get_transitions(self, issue_key: str):
        """Get available transitions."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]
            error: Optional[str] = None

        try:
            result = await self._request("GET", f"issue/{issue_key}/transitions")
            transitions = [
                {"id": t["id"], "name": t["name"], "to_status": t["to"]["name"]}
                for t in result.get("transitions", [])
            ]
            return Result(success=True, data={"transitions": transitions})
        except Exception as e:
            return Result(success=False, data={"transitions": []}, error=str(e))

    async def transition_issue(self, issue_key: str, transition_id: str, comment: Optional[str] = None):
        """Transition issue to new status."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            error: Optional[str] = None

        try:
            data: Dict[str, Any] = {"transition": {"id": transition_id}}
            if comment:
                data["update"] = {
                    "comment": [{
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
                                ]
                            }
                        }
                    }]
                }
            await self._request("POST", f"issue/{issue_key}/transitions", json_data=data)
            return Result(success=True)
        except Exception as e:
            return Result(success=False, error=str(e))
