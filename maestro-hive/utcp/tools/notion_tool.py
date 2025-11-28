"""
UTCP Notion Integration Tool

Provides Notion integration for AI agents:
- Create/update pages
- Query databases
- Search content
- Manage blocks

Part of MD-429: Build Notion Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class NotionTool(UTCPTool):
    """Notion integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="notion",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
                ToolCapability.DELETE,
            ],
            required_credentials=["notion_api_key"],
            optional_credentials=["default_database_id"],
            rate_limit=3,  # Notion rate limit: 3 requests/second
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_key = credentials["notion_api_key"]
        self.default_database = credentials.get("default_database_id")
        self.base_url = "https://api.notion.com/v1"

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make Notion API call."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        url = f"{self.base_url}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Notion error: {text}", code=f"NOTION_{response.status}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json", {})) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Notion error: {text}", code=f"NOTION_{response.status}")
                    return await response.json()
            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=kwargs.get("json", {})) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Notion error: {text}", code=f"NOTION_{response.status}")
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Notion error: {text}", code=f"NOTION_{response.status}")
                    return await response.json()

    async def health_check(self) -> ToolResult:
        """Check Notion API connectivity."""
        try:
            result = await self._api_call("GET", "users/me")
            return ToolResult.ok({
                "connected": True,
                "bot_id": result.get("id"),
                "name": result.get("name"),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def create_page(
        self,
        parent_id: str,
        title: str,
        properties: Optional[Dict] = None,
        children: Optional[List[Dict]] = None,
        is_database: bool = False,
    ) -> ToolResult:
        """
        Create a new page.

        Args:
            parent_id: Parent page or database ID
            title: Page title
            properties: Page properties (for database pages)
            children: Page content blocks
            is_database: Whether parent is a database

        Returns:
            ToolResult with page info
        """
        try:
            parent_type = "database_id" if is_database else "page_id"

            payload = {
                "parent": {parent_type: parent_id},
            }

            if is_database:
                # Database page: use properties
                payload["properties"] = properties or {"Name": {"title": [{"text": {"content": title}}]}}
            else:
                # Regular page: title goes in properties
                payload["properties"] = {"title": [{"text": {"content": title}}]}

            if children:
                payload["children"] = children

            result = await self._api_call("POST", "pages", json=payload)

            return ToolResult.ok({
                "created": True,
                "id": result.get("id"),
                "url": result.get("url"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_PAGE_FAILED")

    async def get_page(self, page_id: str) -> ToolResult:
        """
        Get page details.

        Args:
            page_id: Page ID

        Returns:
            ToolResult with page details
        """
        try:
            result = await self._api_call("GET", f"pages/{page_id}")

            # Extract title from properties
            title = ""
            props = result.get("properties", {})
            for prop in props.values():
                if prop.get("type") == "title":
                    title_items = prop.get("title", [])
                    if title_items:
                        title = title_items[0].get("text", {}).get("content", "")
                    break

            return ToolResult.ok({
                "id": result.get("id"),
                "title": title,
                "url": result.get("url"),
                "created_time": result.get("created_time"),
                "last_edited_time": result.get("last_edited_time"),
                "properties": props,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_PAGE_FAILED")

    async def update_page(
        self,
        page_id: str,
        properties: Dict,
    ) -> ToolResult:
        """
        Update page properties.

        Args:
            page_id: Page ID
            properties: Properties to update

        Returns:
            ToolResult with update status
        """
        try:
            result = await self._api_call("PATCH", f"pages/{page_id}", json={
                "properties": properties,
            })

            return ToolResult.ok({
                "updated": True,
                "id": result.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_PAGE_FAILED")

    async def archive_page(self, page_id: str) -> ToolResult:
        """
        Archive (soft delete) a page.

        Args:
            page_id: Page ID

        Returns:
            ToolResult with archive status
        """
        try:
            await self._api_call("PATCH", f"pages/{page_id}", json={
                "archived": True,
            })

            return ToolResult.ok({"archived": True, "id": page_id})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ARCHIVE_PAGE_FAILED")

    async def query_database(
        self,
        database_id: Optional[str] = None,
        filter: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
        page_size: int = 100,
    ) -> ToolResult:
        """
        Query a database.

        Args:
            database_id: Database ID (uses default if not provided)
            filter: Filter conditions
            sorts: Sort criteria
            page_size: Results per page

        Returns:
            ToolResult with database entries
        """
        try:
            database_id = database_id or self.default_database
            if not database_id:
                return ToolResult.fail("database_id required", code="MISSING_DATABASE")

            payload = {"page_size": page_size}
            if filter:
                payload["filter"] = filter
            if sorts:
                payload["sorts"] = sorts

            result = await self._api_call("POST", f"databases/{database_id}/query", json=payload)

            results = []
            for page in result.get("results", []):
                # Extract title
                title = ""
                for prop in page.get("properties", {}).values():
                    if prop.get("type") == "title":
                        title_items = prop.get("title", [])
                        if title_items:
                            title = title_items[0].get("text", {}).get("content", "")
                        break

                results.append({
                    "id": page.get("id"),
                    "title": title,
                    "url": page.get("url"),
                    "properties": page.get("properties"),
                })

            return ToolResult.ok({
                "results": results,
                "has_more": result.get("has_more", False),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="QUERY_DATABASE_FAILED")

    async def search(
        self,
        query: str,
        filter: Optional[Dict] = None,
        page_size: int = 100,
    ) -> ToolResult:
        """
        Search across all pages.

        Args:
            query: Search query
            filter: Filter (object type)
            page_size: Results per page

        Returns:
            ToolResult with search results
        """
        try:
            payload = {
                "query": query,
                "page_size": page_size,
            }
            if filter:
                payload["filter"] = filter

            result = await self._api_call("POST", "search", json=payload)

            results = []
            for item in result.get("results", []):
                # Extract title
                title = ""
                props = item.get("properties", {})
                for prop in props.values():
                    if prop.get("type") == "title":
                        title_items = prop.get("title", [])
                        if title_items:
                            title = title_items[0].get("text", {}).get("content", "")
                        break

                results.append({
                    "id": item.get("id"),
                    "title": title,
                    "object": item.get("object"),
                    "url": item.get("url"),
                })

            return ToolResult.ok({
                "results": results,
                "has_more": result.get("has_more", False),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEARCH_FAILED")

    async def get_block_children(
        self,
        block_id: str,
        page_size: int = 100,
    ) -> ToolResult:
        """
        Get child blocks of a page or block.

        Args:
            block_id: Page or block ID
            page_size: Results per page

        Returns:
            ToolResult with blocks
        """
        try:
            result = await self._api_call("GET", f"blocks/{block_id}/children", params={
                "page_size": page_size,
            })

            blocks = [
                {
                    "id": block.get("id"),
                    "type": block.get("type"),
                    "has_children": block.get("has_children"),
                    "content": block.get(block.get("type")),
                }
                for block in result.get("results", [])
            ]

            return ToolResult.ok({
                "blocks": blocks,
                "has_more": result.get("has_more", False),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_BLOCKS_FAILED")

    async def append_blocks(
        self,
        page_id: str,
        children: List[Dict],
    ) -> ToolResult:
        """
        Append blocks to a page.

        Args:
            page_id: Page ID
            children: Blocks to append

        Returns:
            ToolResult with append status
        """
        try:
            result = await self._api_call("PATCH", f"blocks/{page_id}/children", json={
                "children": children,
            })

            return ToolResult.ok({
                "appended": True,
                "blocks": len(result.get("results", [])),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="APPEND_BLOCKS_FAILED")

    async def get_database(self, database_id: str) -> ToolResult:
        """
        Get database schema.

        Args:
            database_id: Database ID

        Returns:
            ToolResult with database info
        """
        try:
            result = await self._api_call("GET", f"databases/{database_id}")

            # Extract title
            title = ""
            for item in result.get("title", []):
                title += item.get("text", {}).get("content", "")

            return ToolResult.ok({
                "id": result.get("id"),
                "title": title,
                "properties": result.get("properties"),
                "url": result.get("url"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_DATABASE_FAILED")
