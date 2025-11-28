"""
UTCP Linear Integration Tool

Provides Linear integration for AI agents:
- Create/update issues
- Manage projects and cycles
- Search issues
- Update status and assignees

Part of MD-427: Build Linear Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class LinearTool(UTCPTool):
    """Linear integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="linear",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
            ],
            required_credentials=["linear_api_key"],
            optional_credentials=["default_team_id"],
            rate_limit=1500,  # Linear rate limit per hour
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_key = credentials["linear_api_key"]
        self.default_team_id = credentials.get("default_team_id")
        self.base_url = "https://api.linear.app/graphql"

    async def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL query."""
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json={"query": query, "variables": variables or {}},
            ) as response:
                result = await response.json()

                if "errors" in result:
                    raise ToolError(
                        f"Linear API error: {result['errors'][0]['message']}",
                        code="LINEAR_GRAPHQL_ERROR"
                    )

                return result.get("data", {})

    async def health_check(self) -> ToolResult:
        """Check Linear API connectivity."""
        try:
            query = """
                query {
                    viewer {
                        id
                        name
                        email
                    }
                }
            """
            result = await self._graphql(query)
            viewer = result.get("viewer", {})

            return ToolResult.ok({
                "connected": True,
                "user_id": viewer.get("id"),
                "name": viewer.get("name"),
                "email": viewer.get("email"),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def create_issue(
        self,
        title: str,
        team_id: Optional[str] = None,
        description: Optional[str] = None,
        priority: int = 0,
        state_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        cycle_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Create a new issue.

        Args:
            title: Issue title
            team_id: Team ID (uses default if not provided)
            description: Issue description (markdown)
            priority: Priority (0=none, 1=urgent, 2=high, 3=medium, 4=low)
            state_id: Workflow state ID
            assignee_id: Assignee user ID
            labels: Label IDs
            cycle_id: Cycle ID
            project_id: Project ID

        Returns:
            ToolResult with issue info
        """
        try:
            team_id = team_id or self.default_team_id
            if not team_id:
                return ToolResult.fail("team_id required", code="MISSING_TEAM_ID")

            query = """
                mutation CreateIssue($input: IssueCreateInput!) {
                    issueCreate(input: $input) {
                        success
                        issue {
                            id
                            identifier
                            title
                            url
                            state {
                                name
                            }
                        }
                    }
                }
            """

            input_data = {
                "teamId": team_id,
                "title": title,
                "priority": priority,
            }

            if description:
                input_data["description"] = description
            if state_id:
                input_data["stateId"] = state_id
            if assignee_id:
                input_data["assigneeId"] = assignee_id
            if labels:
                input_data["labelIds"] = labels
            if cycle_id:
                input_data["cycleId"] = cycle_id
            if project_id:
                input_data["projectId"] = project_id

            result = await self._graphql(query, {"input": input_data})
            issue_data = result.get("issueCreate", {})

            if not issue_data.get("success"):
                return ToolResult.fail("Failed to create issue", code="CREATE_FAILED")

            issue = issue_data.get("issue", {})
            return ToolResult.ok({
                "created": True,
                "id": issue.get("id"),
                "identifier": issue.get("identifier"),
                "title": issue.get("title"),
                "url": issue.get("url"),
                "state": issue.get("state", {}).get("name"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_ISSUE_FAILED")

    async def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        state_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Update an existing issue.

        Args:
            issue_id: Issue ID
            title: New title
            description: New description
            priority: New priority
            state_id: New state ID
            assignee_id: New assignee ID

        Returns:
            ToolResult with update status
        """
        try:
            query = """
                mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
                    issueUpdate(id: $id, input: $input) {
                        success
                        issue {
                            id
                            identifier
                            title
                            state {
                                name
                            }
                        }
                    }
                }
            """

            input_data = {}
            if title:
                input_data["title"] = title
            if description:
                input_data["description"] = description
            if priority is not None:
                input_data["priority"] = priority
            if state_id:
                input_data["stateId"] = state_id
            if assignee_id:
                input_data["assigneeId"] = assignee_id

            result = await self._graphql(query, {"id": issue_id, "input": input_data})
            update_data = result.get("issueUpdate", {})

            if not update_data.get("success"):
                return ToolResult.fail("Failed to update issue", code="UPDATE_FAILED")

            issue = update_data.get("issue", {})
            return ToolResult.ok({
                "updated": True,
                "id": issue.get("id"),
                "identifier": issue.get("identifier"),
                "state": issue.get("state", {}).get("name"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_ISSUE_FAILED")

    async def get_issue(self, issue_id: str) -> ToolResult:
        """
        Get issue details.

        Args:
            issue_id: Issue ID or identifier (e.g., "ENG-123")

        Returns:
            ToolResult with issue details
        """
        try:
            query = """
                query GetIssue($id: String!) {
                    issue(id: $id) {
                        id
                        identifier
                        title
                        description
                        priority
                        url
                        state {
                            id
                            name
                        }
                        assignee {
                            id
                            name
                        }
                        labels {
                            nodes {
                                id
                                name
                            }
                        }
                        project {
                            id
                            name
                        }
                        cycle {
                            id
                            name
                        }
                        createdAt
                        updatedAt
                    }
                }
            """

            result = await self._graphql(query, {"id": issue_id})
            issue = result.get("issue")

            if not issue:
                return ToolResult.fail(f"Issue not found: {issue_id}", code="NOT_FOUND")

            return ToolResult.ok({
                "id": issue.get("id"),
                "identifier": issue.get("identifier"),
                "title": issue.get("title"),
                "description": issue.get("description"),
                "priority": issue.get("priority"),
                "url": issue.get("url"),
                "state": issue.get("state", {}).get("name"),
                "assignee": issue.get("assignee", {}).get("name") if issue.get("assignee") else None,
                "labels": [l["name"] for l in issue.get("labels", {}).get("nodes", [])],
                "project": issue.get("project", {}).get("name") if issue.get("project") else None,
                "cycle": issue.get("cycle", {}).get("name") if issue.get("cycle") else None,
                "created_at": issue.get("createdAt"),
                "updated_at": issue.get("updatedAt"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_ISSUE_FAILED")

    async def search_issues(
        self,
        query: str,
        team_id: Optional[str] = None,
        limit: int = 50,
    ) -> ToolResult:
        """
        Search for issues.

        Args:
            query: Search query
            team_id: Filter by team
            limit: Maximum results

        Returns:
            ToolResult with matching issues
        """
        try:
            gql = """
                query SearchIssues($filter: IssueFilter, $first: Int) {
                    issues(filter: $filter, first: $first) {
                        nodes {
                            id
                            identifier
                            title
                            state {
                                name
                            }
                            assignee {
                                name
                            }
                            priority
                            url
                        }
                    }
                }
            """

            filter_data = {}
            if query:
                filter_data["or"] = [
                    {"title": {"containsIgnoreCase": query}},
                    {"description": {"containsIgnoreCase": query}},
                ]
            if team_id:
                filter_data["team"] = {"id": {"eq": team_id}}

            result = await self._graphql(gql, {"filter": filter_data, "first": limit})
            issues = result.get("issues", {}).get("nodes", [])

            return ToolResult.ok({
                "issues": [
                    {
                        "id": issue.get("id"),
                        "identifier": issue.get("identifier"),
                        "title": issue.get("title"),
                        "state": issue.get("state", {}).get("name"),
                        "assignee": issue.get("assignee", {}).get("name") if issue.get("assignee") else None,
                        "priority": issue.get("priority"),
                        "url": issue.get("url"),
                    }
                    for issue in issues
                ],
                "total": len(issues),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEARCH_ISSUES_FAILED")

    async def list_teams(self) -> ToolResult:
        """List all teams."""
        try:
            query = """
                query {
                    teams {
                        nodes {
                            id
                            name
                            key
                        }
                    }
                }
            """

            result = await self._graphql(query)
            teams = result.get("teams", {}).get("nodes", [])

            return ToolResult.ok({
                "teams": [
                    {
                        "id": team.get("id"),
                        "name": team.get("name"),
                        "key": team.get("key"),
                    }
                    for team in teams
                ]
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_TEAMS_FAILED")

    async def list_states(self, team_id: str) -> ToolResult:
        """
        List workflow states for a team.

        Args:
            team_id: Team ID

        Returns:
            ToolResult with states
        """
        try:
            query = """
                query GetStates($teamId: String!) {
                    team(id: $teamId) {
                        states {
                            nodes {
                                id
                                name
                                type
                                position
                            }
                        }
                    }
                }
            """

            result = await self._graphql(query, {"teamId": team_id})
            states = result.get("team", {}).get("states", {}).get("nodes", [])

            return ToolResult.ok({
                "states": [
                    {
                        "id": state.get("id"),
                        "name": state.get("name"),
                        "type": state.get("type"),
                        "position": state.get("position"),
                    }
                    for state in sorted(states, key=lambda x: x.get("position", 0))
                ]
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_STATES_FAILED")

    async def add_comment(self, issue_id: str, body: str) -> ToolResult:
        """
        Add a comment to an issue.

        Args:
            issue_id: Issue ID
            body: Comment body (markdown)

        Returns:
            ToolResult with comment info
        """
        try:
            query = """
                mutation CreateComment($input: CommentCreateInput!) {
                    commentCreate(input: $input) {
                        success
                        comment {
                            id
                            body
                            createdAt
                        }
                    }
                }
            """

            result = await self._graphql(query, {
                "input": {
                    "issueId": issue_id,
                    "body": body,
                }
            })
            comment_data = result.get("commentCreate", {})

            if not comment_data.get("success"):
                return ToolResult.fail("Failed to add comment", code="COMMENT_FAILED")

            comment = comment_data.get("comment", {})
            return ToolResult.ok({
                "added": True,
                "comment_id": comment.get("id"),
                "created_at": comment.get("createdAt"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_COMMENT_FAILED")
