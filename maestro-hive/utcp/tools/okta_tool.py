"""
UTCP Okta Integration Tool

Provides Okta integration for AI agents:
- Manage users and groups
- Handle authentication
- Manage applications
- Search directory

Part of MD-433: Build Okta Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class OktaTool(UTCPTool):
    """Okta integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="okta",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
                ToolCapability.DELETE,
            ],
            required_credentials=["okta_domain", "okta_api_token"],
            optional_credentials=[],
            rate_limit=600,  # Okta rate limit per minute
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        domain = credentials["okta_domain"].rstrip("/")
        if not domain.startswith("https://"):
            domain = f"https://{domain}"
        self.base_url = f"{domain}/api/v1"
        self.api_token = credentials["okta_api_token"]

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make Okta API call."""
        headers = {
            "Authorization": f"SSWS {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.base_url}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Okta error: {text}", code=f"OKTA_{response.status}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Okta error: {text}", code=f"OKTA_{response.status}")
                    return await response.json()
            elif method == "PUT":
                async with session.put(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Okta error: {text}", code=f"OKTA_{response.status}")
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Okta error: {text}", code=f"OKTA_{response.status}")
                    return {}

    async def health_check(self) -> ToolResult:
        """Check Okta API connectivity."""
        try:
            result = await self._api_call("GET", "users", params={"limit": 1})
            return ToolResult.ok({
                "connected": True,
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def get_user(self, user_id: str) -> ToolResult:
        """
        Get user details.

        Args:
            user_id: User ID or login

        Returns:
            ToolResult with user details
        """
        try:
            result = await self._api_call("GET", f"users/{user_id}")

            return ToolResult.ok({
                "id": result.get("id"),
                "status": result.get("status"),
                "login": result.get("profile", {}).get("login"),
                "email": result.get("profile", {}).get("email"),
                "first_name": result.get("profile", {}).get("firstName"),
                "last_name": result.get("profile", {}).get("lastName"),
                "created": result.get("created"),
                "last_login": result.get("lastLogin"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_USER_FAILED")

    async def create_user(
        self,
        login: str,
        email: str,
        first_name: str,
        last_name: str,
        password: Optional[str] = None,
        activate: bool = True,
        groups: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        Create a new user.

        Args:
            login: User login (usually email)
            email: Email address
            first_name: First name
            last_name: Last name
            password: Initial password
            activate: Activate immediately
            groups: Group IDs to add user to

        Returns:
            ToolResult with user info
        """
        try:
            user_data = {
                "profile": {
                    "login": login,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                }
            }

            if password:
                user_data["credentials"] = {
                    "password": {"value": password}
                }

            if groups:
                user_data["groupIds"] = groups

            params = {"activate": str(activate).lower()}

            result = await self._api_call("POST", "users", json=user_data, params=params)

            return ToolResult.ok({
                "created": True,
                "id": result.get("id"),
                "login": result.get("profile", {}).get("login"),
                "status": result.get("status"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_USER_FAILED")

    async def update_user(
        self,
        user_id: str,
        profile: Dict[str, str],
    ) -> ToolResult:
        """
        Update user profile.

        Args:
            user_id: User ID
            profile: Profile fields to update

        Returns:
            ToolResult with update status
        """
        try:
            result = await self._api_call("POST", f"users/{user_id}", json={
                "profile": profile
            })

            return ToolResult.ok({
                "updated": True,
                "id": result.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_USER_FAILED")

    async def deactivate_user(self, user_id: str) -> ToolResult:
        """
        Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            ToolResult with deactivation status
        """
        try:
            await self._api_call("POST", f"users/{user_id}/lifecycle/deactivate")
            return ToolResult.ok({"deactivated": True, "id": user_id})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DEACTIVATE_USER_FAILED")

    async def activate_user(self, user_id: str, send_email: bool = True) -> ToolResult:
        """
        Activate a user.

        Args:
            user_id: User ID
            send_email: Send activation email

        Returns:
            ToolResult with activation status
        """
        try:
            await self._api_call("POST", f"users/{user_id}/lifecycle/activate", params={
                "sendEmail": str(send_email).lower()
            })
            return ToolResult.ok({"activated": True, "id": user_id})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ACTIVATE_USER_FAILED")

    async def list_users(
        self,
        search: Optional[str] = None,
        filter: Optional[str] = None,
        limit: int = 200,
    ) -> ToolResult:
        """
        List users.

        Args:
            search: Search query
            filter: SCIM filter
            limit: Maximum results

        Returns:
            ToolResult with user list
        """
        try:
            params = {"limit": limit}
            if search:
                params["search"] = search
            if filter:
                params["filter"] = filter

            result = await self._api_call("GET", "users", params=params)

            users = [
                {
                    "id": u.get("id"),
                    "login": u.get("profile", {}).get("login"),
                    "email": u.get("profile", {}).get("email"),
                    "first_name": u.get("profile", {}).get("firstName"),
                    "last_name": u.get("profile", {}).get("lastName"),
                    "status": u.get("status"),
                }
                for u in result
            ]

            return ToolResult.ok({"users": users})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_USERS_FAILED")

    async def get_group(self, group_id: str) -> ToolResult:
        """
        Get group details.

        Args:
            group_id: Group ID

        Returns:
            ToolResult with group details
        """
        try:
            result = await self._api_call("GET", f"groups/{group_id}")

            return ToolResult.ok({
                "id": result.get("id"),
                "name": result.get("profile", {}).get("name"),
                "description": result.get("profile", {}).get("description"),
                "type": result.get("type"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_GROUP_FAILED")

    async def list_groups(
        self,
        search: Optional[str] = None,
        filter: Optional[str] = None,
        limit: int = 200,
    ) -> ToolResult:
        """
        List groups.

        Args:
            search: Search query
            filter: SCIM filter
            limit: Maximum results

        Returns:
            ToolResult with group list
        """
        try:
            params = {"limit": limit}
            if search:
                params["q"] = search
            if filter:
                params["filter"] = filter

            result = await self._api_call("GET", "groups", params=params)

            groups = [
                {
                    "id": g.get("id"),
                    "name": g.get("profile", {}).get("name"),
                    "description": g.get("profile", {}).get("description"),
                    "type": g.get("type"),
                }
                for g in result
            ]

            return ToolResult.ok({"groups": groups})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_GROUPS_FAILED")

    async def add_user_to_group(self, group_id: str, user_id: str) -> ToolResult:
        """
        Add user to group.

        Args:
            group_id: Group ID
            user_id: User ID

        Returns:
            ToolResult with status
        """
        try:
            await self._api_call("PUT", f"groups/{group_id}/users/{user_id}")
            return ToolResult.ok({
                "added": True,
                "group_id": group_id,
                "user_id": user_id,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_USER_TO_GROUP_FAILED")

    async def remove_user_from_group(self, group_id: str, user_id: str) -> ToolResult:
        """
        Remove user from group.

        Args:
            group_id: Group ID
            user_id: User ID

        Returns:
            ToolResult with status
        """
        try:
            await self._api_call("DELETE", f"groups/{group_id}/users/{user_id}")
            return ToolResult.ok({
                "removed": True,
                "group_id": group_id,
                "user_id": user_id,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="REMOVE_USER_FROM_GROUP_FAILED")

    async def list_group_members(self, group_id: str) -> ToolResult:
        """
        List group members.

        Args:
            group_id: Group ID

        Returns:
            ToolResult with member list
        """
        try:
            result = await self._api_call("GET", f"groups/{group_id}/users")

            members = [
                {
                    "id": u.get("id"),
                    "login": u.get("profile", {}).get("login"),
                    "email": u.get("profile", {}).get("email"),
                    "first_name": u.get("profile", {}).get("firstName"),
                    "last_name": u.get("profile", {}).get("lastName"),
                }
                for u in result
            ]

            return ToolResult.ok({"members": members})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_GROUP_MEMBERS_FAILED")

    async def list_applications(self, limit: int = 200) -> ToolResult:
        """
        List applications.

        Args:
            limit: Maximum results

        Returns:
            ToolResult with application list
        """
        try:
            result = await self._api_call("GET", "apps", params={"limit": limit})

            apps = [
                {
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "label": a.get("label"),
                    "status": a.get("status"),
                    "sign_on_mode": a.get("signOnMode"),
                }
                for a in result
            ]

            return ToolResult.ok({"applications": apps})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_APPLICATIONS_FAILED")

    async def assign_user_to_app(
        self,
        app_id: str,
        user_id: str,
        scope: str = "USER",
    ) -> ToolResult:
        """
        Assign user to application.

        Args:
            app_id: Application ID
            user_id: User ID
            scope: Assignment scope

        Returns:
            ToolResult with assignment status
        """
        try:
            result = await self._api_call("POST", f"apps/{app_id}/users", json={
                "id": user_id,
                "scope": scope,
            })

            return ToolResult.ok({
                "assigned": True,
                "app_id": app_id,
                "user_id": user_id,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ASSIGN_USER_TO_APP_FAILED")

    async def reset_password(
        self,
        user_id: str,
        send_email: bool = True,
    ) -> ToolResult:
        """
        Reset user password.

        Args:
            user_id: User ID
            send_email: Send reset email

        Returns:
            ToolResult with reset status
        """
        try:
            result = await self._api_call("POST", f"users/{user_id}/lifecycle/reset_password", params={
                "sendEmail": str(send_email).lower()
            })

            return ToolResult.ok({
                "reset": True,
                "reset_password_url": result.get("resetPasswordUrl"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="RESET_PASSWORD_FAILED")
