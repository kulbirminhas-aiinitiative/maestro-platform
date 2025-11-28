"""
UTCP Confluence Integration Tool

Provides Confluence integration for AI agents:
- Create/update pages
- Search content
- Manage spaces
- Handle attachments

Part of MD-428: Build Confluence Integration Adapter
"""

import aiohttp
import base64
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class ConfluenceTool(UTCPTool):
    """Confluence integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="confluence",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
                ToolCapability.DELETE,
            ],
            required_credentials=["confluence_url", "confluence_email", "confluence_api_token"],
            optional_credentials=["default_space_key"],
            rate_limit=None,
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = credentials["confluence_url"].rstrip("/")
        self.email = credentials["confluence_email"]
        self.api_token = credentials["confluence_api_token"]
        self.default_space = credentials.get("default_space_key")
        self._auth = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make Confluence API call."""
        headers = {
            "Authorization": f"Basic {self._auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.base_url}/wiki/rest/api/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Confluence error: {text}", code=f"CONFLUENCE_{response.status}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Confluence error: {text}", code=f"CONFLUENCE_{response.status}")
                    return await response.json()
            elif method == "PUT":
                async with session.put(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Confluence error: {text}", code=f"CONFLUENCE_{response.status}")
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Confluence error: {text}", code=f"CONFLUENCE_{response.status}")
                    return {}

    async def health_check(self) -> ToolResult:
        """Check Confluence API connectivity."""
        try:
            result = await self._api_call("GET", "space", params={"limit": 1})
            return ToolResult.ok({
                "connected": True,
                "spaces_count": result.get("size", 0),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def create_page(
        self,
        title: str,
        content: str,
        space_key: Optional[str] = None,
        parent_id: Optional[str] = None,
        content_format: str = "storage",
    ) -> ToolResult:
        """
        Create a new Confluence page.

        Args:
            title: Page title
            content: Page content (storage format or wiki markup)
            space_key: Space key
            parent_id: Parent page ID (for nested pages)
            content_format: 'storage' or 'wiki'

        Returns:
            ToolResult with page info
        """
        try:
            space_key = space_key or self.default_space
            if not space_key:
                return ToolResult.fail("space_key required", code="MISSING_SPACE")

            payload = {
                "type": "page",
                "title": title,
                "space": {"key": space_key},
                "body": {
                    content_format: {
                        "value": content,
                        "representation": content_format,
                    }
                }
            }

            if parent_id:
                payload["ancestors"] = [{"id": parent_id}]

            result = await self._api_call("POST", "content", json=payload)

            return ToolResult.ok({
                "created": True,
                "id": result.get("id"),
                "title": result.get("title"),
                "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}",
                "version": result.get("version", {}).get("number"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_PAGE_FAILED")

    async def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        version: int,
        content_format: str = "storage",
    ) -> ToolResult:
        """
        Update an existing page.

        Args:
            page_id: Page ID
            title: New title
            content: New content
            version: Current version number (incremented automatically)
            content_format: 'storage' or 'wiki'

        Returns:
            ToolResult with updated page info
        """
        try:
            payload = {
                "type": "page",
                "title": title,
                "body": {
                    content_format: {
                        "value": content,
                        "representation": content_format,
                    }
                },
                "version": {
                    "number": version + 1,
                }
            }

            result = await self._api_call("PUT", f"content/{page_id}", json=payload)

            return ToolResult.ok({
                "updated": True,
                "id": result.get("id"),
                "title": result.get("title"),
                "version": result.get("version", {}).get("number"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_PAGE_FAILED")

    async def get_page(
        self,
        page_id: str,
        expand: str = "body.storage,version",
    ) -> ToolResult:
        """
        Get page details.

        Args:
            page_id: Page ID
            expand: Fields to expand

        Returns:
            ToolResult with page details
        """
        try:
            result = await self._api_call("GET", f"content/{page_id}", params={"expand": expand})

            return ToolResult.ok({
                "id": result.get("id"),
                "title": result.get("title"),
                "space": result.get("space", {}).get("key"),
                "version": result.get("version", {}).get("number"),
                "content": result.get("body", {}).get("storage", {}).get("value"),
                "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}",
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_PAGE_FAILED")

    async def delete_page(self, page_id: str) -> ToolResult:
        """
        Delete a page.

        Args:
            page_id: Page ID

        Returns:
            ToolResult with deletion status
        """
        try:
            await self._api_call("DELETE", f"content/{page_id}")
            return ToolResult.ok({"deleted": True, "id": page_id})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DELETE_PAGE_FAILED")

    async def search(
        self,
        cql: str,
        limit: int = 25,
        expand: str = "space",
    ) -> ToolResult:
        """
        Search Confluence using CQL.

        Args:
            cql: Confluence Query Language query
            limit: Maximum results
            expand: Fields to expand

        Returns:
            ToolResult with search results
        """
        try:
            result = await self._api_call("GET", "content/search", params={
                "cql": cql,
                "limit": limit,
                "expand": expand,
            })

            results = [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "type": item.get("type"),
                    "space": item.get("space", {}).get("key"),
                    "url": f"{self.base_url}/wiki{item.get('_links', {}).get('webui', '')}",
                }
                for item in result.get("results", [])
            ]

            return ToolResult.ok({
                "results": results,
                "total": result.get("totalSize", 0),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEARCH_FAILED")

    async def list_spaces(self, limit: int = 100) -> ToolResult:
        """
        List all spaces.

        Args:
            limit: Maximum results

        Returns:
            ToolResult with space list
        """
        try:
            result = await self._api_call("GET", "space", params={"limit": limit})

            spaces = [
                {
                    "key": space.get("key"),
                    "name": space.get("name"),
                    "type": space.get("type"),
                }
                for space in result.get("results", [])
            ]

            return ToolResult.ok({"spaces": spaces})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_SPACES_FAILED")

    async def get_space_pages(
        self,
        space_key: str,
        limit: int = 100,
    ) -> ToolResult:
        """
        Get all pages in a space.

        Args:
            space_key: Space key
            limit: Maximum results

        Returns:
            ToolResult with page list
        """
        try:
            result = await self._api_call("GET", "content", params={
                "spaceKey": space_key,
                "type": "page",
                "limit": limit,
            })

            pages = [
                {
                    "id": page.get("id"),
                    "title": page.get("title"),
                }
                for page in result.get("results", [])
            ]

            return ToolResult.ok({"pages": pages, "space": space_key})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_SPACE_PAGES_FAILED")

    async def add_comment(
        self,
        page_id: str,
        content: str,
        parent_comment_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Add a comment to a page.

        Args:
            page_id: Page ID
            content: Comment content
            parent_comment_id: Parent comment ID for replies

        Returns:
            ToolResult with comment info
        """
        try:
            payload = {
                "type": "comment",
                "container": {"id": page_id, "type": "page"},
                "body": {
                    "storage": {
                        "value": content,
                        "representation": "storage",
                    }
                }
            }

            if parent_comment_id:
                payload["ancestors"] = [{"id": parent_comment_id}]

            result = await self._api_call("POST", "content", json=payload)

            return ToolResult.ok({
                "added": True,
                "comment_id": result.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_COMMENT_FAILED")

    async def get_page_children(self, page_id: str) -> ToolResult:
        """
        Get child pages.

        Args:
            page_id: Parent page ID

        Returns:
            ToolResult with child pages
        """
        try:
            result = await self._api_call("GET", f"content/{page_id}/child/page")

            children = [
                {
                    "id": page.get("id"),
                    "title": page.get("title"),
                }
                for page in result.get("results", [])
            ]

            return ToolResult.ok({"children": children})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_CHILDREN_FAILED")
