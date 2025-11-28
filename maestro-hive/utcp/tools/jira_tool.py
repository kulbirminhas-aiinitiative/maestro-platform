"""
UTCP JIRA Tool

Provides JIRA operations for AI agents:
- Get/update issue status
- Add comments
- Attach files
- Transition issues
- Search issues

Part of MD-856: JIRA Tool - status, comments, attachments
"""

import aiohttp
import base64
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class JiraTool(UTCPTool):
    """JIRA integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="jira",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
                ToolCapability.COMMENT,
                ToolCapability.TRANSITION,
                ToolCapability.ATTACH,
            ],
            required_credentials=["base_url", "email", "api_token"],
            optional_credentials=["project_key"],
            rate_limit=60,  # JIRA Cloud rate limit
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = credentials["base_url"].rstrip("/")
        self.email = credentials["email"]
        self.api_token = credentials["api_token"]
        self.project_key = credentials.get("project_key")

    def _get_auth_header(self) -> str:
        """Generate Basic auth header."""
        auth_str = f"{self.email}:{self.api_token}"
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
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise ToolError(
                        f"JIRA API error: {response.status} - {error_text}",
                        code=f"JIRA_{response.status}"
                    )
                if response.status == 204:
                    return {}
                return await response.json()

    async def health_check(self) -> ToolResult:
        """Check JIRA connectivity."""
        try:
            result = await self._request("GET", "myself")
            return ToolResult.ok({
                "connected": True,
                "user": result.get("displayName"),
                "email": result.get("emailAddress"),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> ToolResult:
        """
        Get issue details.

        Args:
            issue_key: Issue key (e.g., "MD-123")
            fields: Optional list of fields to retrieve

        Returns:
            ToolResult with issue data
        """
        try:
            params = {}
            if fields:
                params["fields"] = ",".join(fields)

            result = await self._request("GET", f"issue/{issue_key}", params=params)

            return ToolResult.ok({
                "key": result["key"],
                "id": result["id"],
                "summary": result["fields"].get("summary"),
                "status": result["fields"]["status"]["name"],
                "assignee": result["fields"].get("assignee", {}).get("displayName") if result["fields"].get("assignee") else None,
                "priority": result["fields"].get("priority", {}).get("name") if result["fields"].get("priority") else None,
                "description": self._extract_description(result["fields"].get("description")),
                "labels": result["fields"].get("labels", []),
                "created": result["fields"].get("created"),
                "updated": result["fields"].get("updated"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_ISSUE_FAILED")

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

    async def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> ToolResult:
        """
        Update issue fields.

        Args:
            issue_key: Issue key
            fields: Fields to update (e.g., {"summary": "New title"})

        Returns:
            ToolResult with success status
        """
        try:
            await self._request("PUT", f"issue/{issue_key}", json_data={"fields": fields})
            return ToolResult.ok({"updated": True, "issue_key": issue_key})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_ISSUE_FAILED")

    async def add_comment(self, issue_key: str, comment: str) -> ToolResult:
        """
        Add comment to issue.

        Args:
            issue_key: Issue key
            comment: Comment text (can include markdown)

        Returns:
            ToolResult with comment ID
        """
        try:
            # Convert to ADF format
            adf_body = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment}]
                        }
                    ]
                }
            }

            result = await self._request("POST", f"issue/{issue_key}/comment", json_data=adf_body)

            return ToolResult.ok({
                "comment_id": result.get("id"),
                "issue_key": issue_key,
                "created": result.get("created"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_COMMENT_FAILED")

    async def get_transitions(self, issue_key: str) -> ToolResult:
        """
        Get available transitions for an issue.

        Args:
            issue_key: Issue key

        Returns:
            ToolResult with list of available transitions
        """
        try:
            result = await self._request("GET", f"issue/{issue_key}/transitions")

            transitions = [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "to_status": t["to"]["name"],
                }
                for t in result.get("transitions", [])
            ]

            return ToolResult.ok({"transitions": transitions})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_TRANSITIONS_FAILED")

    async def transition_issue(self, issue_key: str, transition_id: str, comment: Optional[str] = None) -> ToolResult:
        """
        Transition issue to new status.

        Args:
            issue_key: Issue key
            transition_id: Transition ID (from get_transitions)
            comment: Optional comment to add with transition

        Returns:
            ToolResult with success status
        """
        try:
            data: Dict[str, Any] = {"transition": {"id": transition_id}}

            if comment:
                data["update"] = {
                    "comment": [
                        {
                            "add": {
                                "body": {
                                    "type": "doc",
                                    "version": 1,
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": comment}]
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }

            await self._request("POST", f"issue/{issue_key}/transitions", json_data=data)
            return ToolResult.ok({"transitioned": True, "issue_key": issue_key})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="TRANSITION_FAILED")

    async def search_issues(self, jql: str, max_results: int = 50, fields: Optional[List[str]] = None) -> ToolResult:
        """
        Search issues using JQL.

        Args:
            jql: JQL query string
            max_results: Maximum results to return
            fields: Fields to include in results

        Returns:
            ToolResult with list of matching issues
        """
        try:
            data = {
                "jql": jql,
                "maxResults": max_results,
                "fields": fields or ["key", "summary", "status", "assignee", "priority"]
            }

            # Use POST for search (new JIRA Cloud API)
            result = await self._request("POST", "search/jql", json_data=data)

            issues = []
            for issue in result.get("issues", []):
                issues.append({
                    "key": issue["key"],
                    "summary": issue["fields"].get("summary"),
                    "status": issue["fields"]["status"]["name"],
                    "assignee": issue["fields"].get("assignee", {}).get("displayName") if issue["fields"].get("assignee") else None,
                    "priority": issue["fields"].get("priority", {}).get("name") if issue["fields"].get("priority") else None,
                })

            return ToolResult.ok({
                "issues": issues,
                "total": result.get("total", len(issues)),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEARCH_FAILED")

    async def get_comments(self, issue_key: str) -> ToolResult:
        """
        Get all comments on an issue.

        Args:
            issue_key: Issue key

        Returns:
            ToolResult with list of comments
        """
        try:
            result = await self._request("GET", f"issue/{issue_key}/comment")

            comments = []
            for comment in result.get("comments", []):
                comments.append({
                    "id": comment["id"],
                    "author": comment["author"].get("displayName"),
                    "body": self._extract_description(comment.get("body")),
                    "created": comment.get("created"),
                    "updated": comment.get("updated"),
                })

            return ToolResult.ok({"comments": comments})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_COMMENTS_FAILED")

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: Optional[str] = None,
        labels: Optional[List[str]] = None,
        priority: Optional[str] = None,
        parent_key: Optional[str] = None,
    ) -> ToolResult:
        """
        Create a new issue.

        Args:
            project_key: Project key (e.g., "MD")
            summary: Issue title
            issue_type: Issue type (Task, Bug, Story, etc.)
            description: Issue description
            labels: List of labels
            priority: Priority name
            parent_key: Parent issue key (for subtasks)

        Returns:
            ToolResult with created issue key
        """
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
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                }

            if labels:
                fields["labels"] = labels

            if priority:
                fields["priority"] = {"name": priority}

            if parent_key:
                fields["parent"] = {"key": parent_key}

            result = await self._request("POST", "issue", json_data={"fields": fields})

            return ToolResult.ok({
                "key": result["key"],
                "id": result["id"],
                "self": result["self"],
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_ISSUE_FAILED")
