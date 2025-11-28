"""
UTCP Slack Integration Tool

Provides Slack integration for AI agents:
- Send messages to channels
- Create/update threads
- React to messages
- Upload files
- Manage channels

Part of MD-422: Build Slack Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class SlackTool(UTCPTool):
    """Slack integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="slack",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
            ],
            required_credentials=["slack_bot_token"],
            optional_credentials=["slack_app_token", "default_channel"],
            rate_limit=50,  # Slack tier 2 rate limit
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.bot_token = credentials["slack_bot_token"]
        self.app_token = credentials.get("slack_app_token")
        self.default_channel = credentials.get("default_channel")
        self.base_url = "https://slack.com/api"

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make Slack API call."""
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    result = await response.json()
            else:
                async with session.post(url, headers=headers, json=kwargs.get("json", {})) as response:
                    result = await response.json()

            if not result.get("ok"):
                raise ToolError(
                    f"Slack API error: {result.get('error', 'Unknown error')}",
                    code=f"SLACK_{result.get('error', 'ERROR').upper()}"
                )

            return result

    async def health_check(self) -> ToolResult:
        """Check Slack API connectivity."""
        try:
            result = await self._api_call("GET", "auth.test")
            return ToolResult.ok({
                "connected": True,
                "team": result.get("team"),
                "user": result.get("user"),
                "bot_id": result.get("bot_id"),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None,
        unfurl_links: bool = True,
    ) -> ToolResult:
        """
        Send a message to a Slack channel.

        Args:
            channel: Channel ID or name
            text: Message text (fallback for blocks)
            thread_ts: Thread timestamp for replies
            blocks: Block Kit blocks for rich formatting
            attachments: Legacy attachments
            unfurl_links: Whether to unfurl URLs

        Returns:
            ToolResult with message timestamp
        """
        try:
            payload = {
                "channel": channel or self.default_channel,
                "text": text,
                "unfurl_links": unfurl_links,
            }

            if thread_ts:
                payload["thread_ts"] = thread_ts
            if blocks:
                payload["blocks"] = blocks
            if attachments:
                payload["attachments"] = attachments

            result = await self._api_call("POST", "chat.postMessage", json=payload)

            return ToolResult.ok({
                "sent": True,
                "channel": result.get("channel"),
                "ts": result.get("ts"),
                "message": result.get("message"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEND_MESSAGE_FAILED")

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
    ) -> ToolResult:
        """
        Update an existing message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            text: New message text
            blocks: New Block Kit blocks

        Returns:
            ToolResult with updated message
        """
        try:
            payload = {
                "channel": channel,
                "ts": ts,
                "text": text,
            }
            if blocks:
                payload["blocks"] = blocks

            result = await self._api_call("POST", "chat.update", json=payload)

            return ToolResult.ok({
                "updated": True,
                "channel": result.get("channel"),
                "ts": result.get("ts"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_MESSAGE_FAILED")

    async def delete_message(self, channel: str, ts: str) -> ToolResult:
        """
        Delete a message.

        Args:
            channel: Channel ID
            ts: Message timestamp

        Returns:
            ToolResult with deletion status
        """
        try:
            await self._api_call("POST", "chat.delete", json={
                "channel": channel,
                "ts": ts,
            })

            return ToolResult.ok({
                "deleted": True,
                "channel": channel,
                "ts": ts,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DELETE_MESSAGE_FAILED")

    async def add_reaction(self, channel: str, ts: str, emoji: str) -> ToolResult:
        """
        Add a reaction to a message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            emoji: Emoji name (without colons)

        Returns:
            ToolResult with reaction status
        """
        try:
            await self._api_call("POST", "reactions.add", json={
                "channel": channel,
                "timestamp": ts,
                "name": emoji,
            })

            return ToolResult.ok({
                "added": True,
                "emoji": emoji,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_REACTION_FAILED")

    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ) -> ToolResult:
        """
        Get channel message history.

        Args:
            channel: Channel ID
            limit: Number of messages
            oldest: Start of time range
            latest: End of time range

        Returns:
            ToolResult with messages
        """
        try:
            params = {
                "channel": channel,
                "limit": min(limit, 1000),
            }
            if oldest:
                params["oldest"] = oldest
            if latest:
                params["latest"] = latest

            result = await self._api_call("GET", "conversations.history", params=params)

            return ToolResult.ok({
                "messages": result.get("messages", []),
                "has_more": result.get("has_more", False),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_HISTORY_FAILED")

    async def get_thread_replies(self, channel: str, thread_ts: str) -> ToolResult:
        """
        Get replies in a thread.

        Args:
            channel: Channel ID
            thread_ts: Parent message timestamp

        Returns:
            ToolResult with thread messages
        """
        try:
            result = await self._api_call("GET", "conversations.replies", params={
                "channel": channel,
                "ts": thread_ts,
            })

            return ToolResult.ok({
                "messages": result.get("messages", []),
                "has_more": result.get("has_more", False),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_THREAD_FAILED")

    async def list_channels(
        self,
        types: str = "public_channel,private_channel",
        limit: int = 100,
    ) -> ToolResult:
        """
        List channels the bot has access to.

        Args:
            types: Channel types to include
            limit: Number of channels

        Returns:
            ToolResult with channel list
        """
        try:
            result = await self._api_call("GET", "conversations.list", params={
                "types": types,
                "limit": limit,
                "exclude_archived": True,
            })

            channels = [
                {
                    "id": ch["id"],
                    "name": ch["name"],
                    "is_private": ch.get("is_private", False),
                    "is_member": ch.get("is_member", False),
                    "num_members": ch.get("num_members", 0),
                }
                for ch in result.get("channels", [])
            ]

            return ToolResult.ok({"channels": channels})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_CHANNELS_FAILED")

    async def search_messages(
        self,
        query: str,
        count: int = 20,
        sort: str = "timestamp",
    ) -> ToolResult:
        """
        Search for messages.

        Args:
            query: Search query
            count: Number of results
            sort: Sort by (timestamp or score)

        Returns:
            ToolResult with matching messages
        """
        try:
            result = await self._api_call("GET", "search.messages", params={
                "query": query,
                "count": count,
                "sort": sort,
            })

            matches = result.get("messages", {}).get("matches", [])

            return ToolResult.ok({
                "total": result.get("messages", {}).get("total", 0),
                "messages": matches,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEARCH_FAILED")

    async def upload_file(
        self,
        channels: str,
        content: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
        thread_ts: Optional[str] = None,
    ) -> ToolResult:
        """
        Upload a file to Slack.

        Args:
            channels: Comma-separated channel IDs
            content: File content (for text files)
            filename: Filename
            title: File title
            initial_comment: Message with the file
            thread_ts: Thread to post in

        Returns:
            ToolResult with file info
        """
        try:
            payload = {
                "channels": channels,
            }
            if content:
                payload["content"] = content
            if filename:
                payload["filename"] = filename
            if title:
                payload["title"] = title
            if initial_comment:
                payload["initial_comment"] = initial_comment
            if thread_ts:
                payload["thread_ts"] = thread_ts

            result = await self._api_call("POST", "files.upload", json=payload)

            file_info = result.get("file", {})
            return ToolResult.ok({
                "uploaded": True,
                "file_id": file_info.get("id"),
                "name": file_info.get("name"),
                "url": file_info.get("url_private"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPLOAD_FILE_FAILED")

    async def get_user_info(self, user_id: str) -> ToolResult:
        """
        Get information about a user.

        Args:
            user_id: User ID

        Returns:
            ToolResult with user info
        """
        try:
            result = await self._api_call("GET", "users.info", params={
                "user": user_id,
            })

            user = result.get("user", {})
            return ToolResult.ok({
                "id": user.get("id"),
                "name": user.get("name"),
                "real_name": user.get("real_name"),
                "email": user.get("profile", {}).get("email"),
                "is_bot": user.get("is_bot", False),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_USER_FAILED")

    async def set_channel_topic(self, channel: str, topic: str) -> ToolResult:
        """
        Set channel topic.

        Args:
            channel: Channel ID
            topic: New topic

        Returns:
            ToolResult with updated topic
        """
        try:
            result = await self._api_call("POST", "conversations.setTopic", json={
                "channel": channel,
                "topic": topic,
            })

            return ToolResult.ok({
                "updated": True,
                "channel": result.get("channel", {}).get("id"),
                "topic": result.get("channel", {}).get("topic", {}).get("value"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SET_TOPIC_FAILED")
