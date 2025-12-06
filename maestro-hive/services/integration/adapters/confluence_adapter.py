"""
Confluence Adapter Implementation (MD-2111)

Implements IDocumentAdapter for Atlassian Confluence.
Migrated from routes to adapter pattern for consistent API.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..interfaces import (
    IDocumentAdapter,
    DocumentData,
    AdapterResult
)

logger = logging.getLogger(__name__)


class ConfluenceAdapter(IDocumentAdapter):
    """
    Confluence adapter for document management.

    Configuration:
        base_url: Confluence API URL
        username: Confluence username (email)
        api_token: Confluence API token
        default_space: Default space key
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        default_space: Optional[str] = None
    ):
        """
        Initialize Confluence adapter.

        Args:
            base_url: Confluence base URL (e.g., https://yoursite.atlassian.net)
            username: Confluence username (email)
            api_token: Confluence API token
            default_space: Default space key
        """
        self._base_url = base_url.rstrip('/') + '/wiki/rest/api'
        self._username = username
        self._api_token = api_token
        self._default_space = default_space
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"ConfluenceAdapter initialized for {base_url}")

    @property
    def adapter_name(self) -> str:
        return "confluence"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                auth=(self._username, self._api_token)
            )
        return self._client

    def _parse_page(self, data: Dict[str, Any]) -> DocumentData:
        """Parse Confluence API response to DocumentData"""
        # Extract content if available
        content = ""
        if 'body' in data:
            if 'storage' in data['body']:
                content = data['body']['storage'].get('value', '')
            elif 'view' in data['body']:
                content = data['body']['view'].get('value', '')

        # Extract space info
        space_id = None
        if 'space' in data:
            space_id = data['space'].get('key')

        # Extract version
        version = 1
        if 'version' in data:
            version = data['version'].get('number', 1)

        # Extract labels
        labels = []
        if 'metadata' in data and 'labels' in data['metadata']:
            labels = [
                label.get('name', '')
                for label in data['metadata']['labels'].get('results', [])
            ]

        # Get deep link
        deep_link = None
        if '_links' in data:
            base = data['_links'].get('base', '')
            webui = data['_links'].get('webui', '')
            if base and webui:
                deep_link = f"{base}{webui}"

        return DocumentData(
            id=str(data.get('id', '')),
            external_id=str(data.get('id', '')),
            title=data.get('title', ''),
            content=content,
            space_id=space_id,
            parent_id=str(data.get('ancestors', [{}])[-1].get('id', '')) if data.get('ancestors') else None,
            version=version,
            author=data.get('history', {}).get('createdBy', {}).get('displayName'),
            created_at=datetime.fromisoformat(data['history']['createdDate'].replace('Z', '+00:00')) if data.get('history', {}).get('createdDate') else None,
            updated_at=datetime.fromisoformat(data['version']['when'].replace('Z', '+00:00')) if data.get('version', {}).get('when') else None,
            deep_link=deep_link,
            labels=labels,
            metadata={
                'type': data.get('type'),
                'status': data.get('status')
            }
        )

    async def create_page(
        self,
        title: str,
        content: str,
        space_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """Create a new Confluence page"""
        try:
            client = await self._get_client()

            space_key = space_id or self._default_space
            if not space_key:
                return AdapterResult(
                    success=False,
                    error="Space key is required"
                )

            payload: Dict[str, Any] = {
                "type": "page",
                "title": title,
                "space": {"key": space_key},
                "body": {
                    "storage": {
                        "value": content,
                        "representation": "storage"
                    }
                }
            }

            if parent_id:
                payload["ancestors"] = [{"id": parent_id}]

            response = await client.post(
                f"{self._base_url}/content",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            page_data = response.json()

            # Add labels if provided
            if labels:
                page_id = page_data.get('id')
                await self._add_labels(page_id, labels)

            # Fetch full page with expanded content
            result = await self.get_page(page_data.get('id'))
            return result

        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            try:
                error_data = e.response.json()
                error_msg = error_data.get('message', str(e))
            except:
                pass
            logger.exception(f"Failed to create page: {error_msg}")
            return AdapterResult(success=False, error=error_msg)

        except Exception as e:
            logger.exception(f"Failed to create page: {e}")
            return AdapterResult(success=False, error=str(e))

    async def _add_labels(self, page_id: str, labels: List[str]) -> None:
        """Add labels to a page"""
        try:
            client = await self._get_client()
            label_data = [{"prefix": "global", "name": label} for label in labels]

            await client.post(
                f"{self._base_url}/content/{page_id}/label",
                json=label_data,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            logger.warning(f"Failed to add labels: {e}")

    async def update_page(
        self,
        page_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """Update an existing page"""
        try:
            client = await self._get_client()

            # First get current page to get version
            current = await self.get_page(page_id)
            if not current.success:
                return current

            current_page: DocumentData = current.data
            new_version = current_page.version + 1

            payload: Dict[str, Any] = {
                "type": "page",
                "title": title or current_page.title,
                "version": {"number": new_version}
            }

            if content is not None:
                payload["body"] = {
                    "storage": {
                        "value": content,
                        "representation": "storage"
                    }
                }

            response = await client.put(
                f"{self._base_url}/content/{page_id}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            # Update labels if provided
            if labels is not None:
                # Remove existing labels
                await self._remove_all_labels(page_id)
                # Add new labels
                if labels:
                    await self._add_labels(page_id, labels)

            # Fetch updated page
            return await self.get_page(page_id)

        except Exception as e:
            logger.exception(f"Failed to update page: {e}")
            return AdapterResult(success=False, error=str(e))

    async def _remove_all_labels(self, page_id: str) -> None:
        """Remove all labels from a page"""
        try:
            client = await self._get_client()

            # Get current labels
            response = await client.get(
                f"{self._base_url}/content/{page_id}/label"
            )
            if response.status_code == 200:
                labels_data = response.json()
                for label in labels_data.get('results', []):
                    await client.delete(
                        f"{self._base_url}/content/{page_id}/label/{label['name']}"
                    )
        except Exception as e:
            logger.warning(f"Failed to remove labels: {e}")

    async def get_page(self, page_id: str) -> AdapterResult:
        """Get a page by ID"""
        try:
            client = await self._get_client()

            response = await client.get(
                f"{self._base_url}/content/{page_id}",
                params={
                    "expand": "body.storage,space,version,history,metadata.labels,ancestors"
                }
            )
            response.raise_for_status()

            page_data = response.json()
            page = self._parse_page(page_data)
            return AdapterResult(success=True, data=page)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return AdapterResult(
                    success=False,
                    error=f"Page {page_id} not found"
                )
            logger.exception(f"Failed to get page: {e}")
            return AdapterResult(success=False, error=str(e))

        except Exception as e:
            logger.exception(f"Failed to get page: {e}")
            return AdapterResult(success=False, error=str(e))

    async def delete_page(self, page_id: str) -> AdapterResult:
        """Delete a page"""
        try:
            client = await self._get_client()

            response = await client.delete(
                f"{self._base_url}/content/{page_id}"
            )
            response.raise_for_status()

            return AdapterResult(success=True)

        except Exception as e:
            logger.exception(f"Failed to delete page: {e}")
            return AdapterResult(success=False, error=str(e))

    async def search_pages(
        self,
        query: str,
        space_id: Optional[str] = None,
        limit: int = 50
    ) -> AdapterResult:
        """Search for pages"""
        try:
            client = await self._get_client()

            cql = f'type=page AND text ~ "{query}"'
            if space_id:
                cql += f' AND space.key="{space_id}"'

            response = await client.get(
                f"{self._base_url}/content/search",
                params={
                    "cql": cql,
                    "limit": limit,
                    "expand": "space,version"
                }
            )
            response.raise_for_status()

            results = response.json()
            pages = [
                self._parse_page(item)
                for item in results.get('results', [])
            ]

            return AdapterResult(success=True, data=pages)

        except Exception as e:
            logger.exception(f"Failed to search pages: {e}")
            return AdapterResult(success=False, error=str(e))

    async def get_page_children(
        self,
        page_id: str,
        limit: int = 50
    ) -> AdapterResult:
        """Get child pages"""
        try:
            client = await self._get_client()

            response = await client.get(
                f"{self._base_url}/content/{page_id}/child/page",
                params={
                    "limit": limit,
                    "expand": "space,version"
                }
            )
            response.raise_for_status()

            results = response.json()
            pages = [
                self._parse_page(item)
                for item in results.get('results', [])
            ]

            return AdapterResult(success=True, data=pages)

        except Exception as e:
            logger.exception(f"Failed to get child pages: {e}")
            return AdapterResult(success=False, error=str(e))

    async def health_check(self) -> AdapterResult:
        """Check adapter health"""
        try:
            client = await self._get_client()

            response = await client.get(
                f"{self._base_url}/space",
                params={"limit": 1}
            )

            if response.status_code == 200:
                return AdapterResult(
                    success=True,
                    data={'status': 'healthy', 'adapter': 'confluence'}
                )
            else:
                return AdapterResult(
                    success=False,
                    error=f"Health check failed: {response.status_code}"
                )

        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
