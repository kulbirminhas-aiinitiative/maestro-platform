"""
UTCP Microsoft Teams Integration Tool

Provides Microsoft Teams integration for AI agents:
- Send messages to channels/chats
- Create/update conversations
- Upload files
- Manage teams and channels

Part of MD-423: Build Microsoft Teams Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class TeamsTool(UTCPTool):
    """Microsoft Teams integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="teams",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
            ],
            required_credentials=["tenant_id", "client_id", "client_secret"],
            optional_credentials=["default_team_id", "default_channel_id"],
            rate_limit=None,
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.tenant_id = credentials["tenant_id"]
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.default_team_id = credentials.get("default_team_id")
        self.default_channel_id = credentials.get("default_channel_id")
        self.base_url = "https://graph.microsoft.com/v1.0"
        self._access_token = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token."""
        if self._access_token:
            return self._access_token

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ToolError(f"Token error: {error_text}", code="AUTH_FAILED")

                result = await response.json()
                self._access_token = result["access_token"]
                return self._access_token

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make Microsoft Graph API call."""
        token = await self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(f"Graph API error: {error_text}", code=f"GRAPH_{response.status}")
                    return await response.json() if response.content_length else {}
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json", {})) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(f"Graph API error: {error_text}", code=f"GRAPH_{response.status}")
                    return await response.json() if response.content_length else {}
            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=kwargs.get("json", {})) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(f"Graph API error: {error_text}", code=f"GRAPH_{response.status}")
                    return await response.json() if response.content_length else {}
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(f"Graph API error: {error_text}", code=f"GRAPH_{response.status}")
                    return {}

    async def health_check(self) -> ToolResult:
        """Check Microsoft Graph API connectivity."""
        try:
            # Test token acquisition
            await self._get_access_token()

            return ToolResult.ok({
                "connected": True,
                "tenant_id": self.tenant_id,
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def send_channel_message(
        self,
        team_id: str,
        channel_id: str,
        content: str,
        content_type: str = "html",
        attachments: Optional[List[Dict]] = None,
    ) -> ToolResult:
        """
        Send a message to a Teams channel.

        Args:
            team_id: Team ID
            channel_id: Channel ID
            content: Message content
            content_type: 'text' or 'html'
            attachments: File attachments

        Returns:
            ToolResult with message ID
        """
        try:
            team_id = team_id or self.default_team_id
            channel_id = channel_id or self.default_channel_id

            payload = {
                "body": {
                    "contentType": content_type,
                    "content": content,
                }
            }

            if attachments:
                payload["attachments"] = attachments

            result = await self._api_call(
                "POST",
                f"teams/{team_id}/channels/{channel_id}/messages",
                json=payload
            )

            return ToolResult.ok({
                "sent": True,
                "message_id": result.get("id"),
                "created_datetime": result.get("createdDateTime"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEND_MESSAGE_FAILED")

    async def reply_to_message(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        content: str,
        content_type: str = "html",
    ) -> ToolResult:
        """
        Reply to a message in a thread.

        Args:
            team_id: Team ID
            channel_id: Channel ID
            message_id: Parent message ID
            content: Reply content
            content_type: 'text' or 'html'

        Returns:
            ToolResult with reply ID
        """
        try:
            result = await self._api_call(
                "POST",
                f"teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies",
                json={
                    "body": {
                        "contentType": content_type,
                        "content": content,
                    }
                }
            )

            return ToolResult.ok({
                "sent": True,
                "reply_id": result.get("id"),
                "created_datetime": result.get("createdDateTime"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="REPLY_FAILED")

    async def get_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        top: int = 50,
    ) -> ToolResult:
        """
        Get messages from a channel.

        Args:
            team_id: Team ID
            channel_id: Channel ID
            top: Number of messages

        Returns:
            ToolResult with messages
        """
        try:
            result = await self._api_call(
                "GET",
                f"teams/{team_id}/channels/{channel_id}/messages",
                params={"$top": top}
            )

            messages = [
                {
                    "id": msg.get("id"),
                    "content": msg.get("body", {}).get("content"),
                    "from": msg.get("from", {}).get("user", {}).get("displayName"),
                    "created": msg.get("createdDateTime"),
                }
                for msg in result.get("value", [])
            ]

            return ToolResult.ok({"messages": messages})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_MESSAGES_FAILED")

    async def list_teams(self) -> ToolResult:
        """
        List teams the app has access to.

        Returns:
            ToolResult with team list
        """
        try:
            result = await self._api_call("GET", "groups", params={
                "$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')",
                "$select": "id,displayName,description",
            })

            teams = [
                {
                    "id": team.get("id"),
                    "name": team.get("displayName"),
                    "description": team.get("description"),
                }
                for team in result.get("value", [])
            ]

            return ToolResult.ok({"teams": teams})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_TEAMS_FAILED")

    async def list_channels(self, team_id: str) -> ToolResult:
        """
        List channels in a team.

        Args:
            team_id: Team ID

        Returns:
            ToolResult with channel list
        """
        try:
            result = await self._api_call("GET", f"teams/{team_id}/channels")

            channels = [
                {
                    "id": ch.get("id"),
                    "name": ch.get("displayName"),
                    "description": ch.get("description"),
                    "membership_type": ch.get("membershipType"),
                }
                for ch in result.get("value", [])
            ]

            return ToolResult.ok({"channels": channels})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_CHANNELS_FAILED")

    async def create_channel(
        self,
        team_id: str,
        display_name: str,
        description: Optional[str] = None,
        membership_type: str = "standard",
    ) -> ToolResult:
        """
        Create a new channel.

        Args:
            team_id: Team ID
            display_name: Channel name
            description: Channel description
            membership_type: 'standard', 'private', or 'shared'

        Returns:
            ToolResult with channel info
        """
        try:
            payload = {
                "displayName": display_name,
                "membershipType": membership_type,
            }
            if description:
                payload["description"] = description

            result = await self._api_call("POST", f"teams/{team_id}/channels", json=payload)

            return ToolResult.ok({
                "created": True,
                "channel_id": result.get("id"),
                "name": result.get("displayName"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_CHANNEL_FAILED")

    async def send_chat_message(
        self,
        chat_id: str,
        content: str,
        content_type: str = "html",
    ) -> ToolResult:
        """
        Send a message to a chat (1:1 or group).

        Args:
            chat_id: Chat ID
            content: Message content
            content_type: 'text' or 'html'

        Returns:
            ToolResult with message ID
        """
        try:
            result = await self._api_call(
                "POST",
                f"chats/{chat_id}/messages",
                json={
                    "body": {
                        "contentType": content_type,
                        "content": content,
                    }
                }
            )

            return ToolResult.ok({
                "sent": True,
                "message_id": result.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEND_CHAT_FAILED")

    async def get_team_members(self, team_id: str) -> ToolResult:
        """
        Get members of a team.

        Args:
            team_id: Team ID

        Returns:
            ToolResult with member list
        """
        try:
            result = await self._api_call("GET", f"teams/{team_id}/members")

            members = [
                {
                    "id": member.get("id"),
                    "user_id": member.get("userId"),
                    "display_name": member.get("displayName"),
                    "email": member.get("email"),
                    "roles": member.get("roles", []),
                }
                for member in result.get("value", [])
            ]

            return ToolResult.ok({"members": members})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_MEMBERS_FAILED")

    async def update_channel(
        self,
        team_id: str,
        channel_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ToolResult:
        """
        Update channel properties.

        Args:
            team_id: Team ID
            channel_id: Channel ID
            display_name: New name
            description: New description

        Returns:
            ToolResult with update status
        """
        try:
            payload = {}
            if display_name:
                payload["displayName"] = display_name
            if description:
                payload["description"] = description

            await self._api_call("PATCH", f"teams/{team_id}/channels/{channel_id}", json=payload)

            return ToolResult.ok({
                "updated": True,
                "channel_id": channel_id,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_CHANNEL_FAILED")
