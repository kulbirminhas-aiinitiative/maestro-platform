"""
UTCP Datadog Integration Tool

Provides Datadog integration for AI agents:
- Query metrics
- Create/update monitors
- Send events
- Manage dashboards

Part of MD-431: Build Datadog Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class DatadogTool(UTCPTool):
    """Datadog integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="datadog",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
            ],
            required_credentials=["dd_api_key", "dd_app_key"],
            optional_credentials=["dd_site"],
            rate_limit=300,  # Datadog rate limit per minute
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_key = credentials["dd_api_key"]
        self.app_key = credentials["dd_app_key"]
        site = credentials.get("dd_site", "datadoghq.com")
        self.base_url = f"https://api.{site}/api/v1"
        self.base_url_v2 = f"https://api.{site}/api/v2"

    async def _api_call(self, method: str, endpoint: str, v2: bool = False, **kwargs) -> Any:
        """Make Datadog API call."""
        headers = {
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json",
        }

        base = self.base_url_v2 if v2 else self.base_url
        url = f"{base}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Datadog error: {text}", code=f"DD_{response.status}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Datadog error: {text}", code=f"DD_{response.status}")
                    return await response.json()
            elif method == "PUT":
                async with session.put(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Datadog error: {text}", code=f"DD_{response.status}")
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Datadog error: {text}", code=f"DD_{response.status}")
                    return {}

    async def health_check(self) -> ToolResult:
        """Check Datadog API connectivity."""
        try:
            result = await self._api_call("GET", "validate")
            return ToolResult.ok({
                "connected": True,
                "valid": result.get("valid", False),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def query_metrics(
        self,
        query: str,
        from_time: int,
        to_time: int,
    ) -> ToolResult:
        """
        Query metrics.

        Args:
            query: Metrics query string
            from_time: Start timestamp (epoch seconds)
            to_time: End timestamp (epoch seconds)

        Returns:
            ToolResult with metric series
        """
        try:
            result = await self._api_call("GET", "query", params={
                "query": query,
                "from": from_time,
                "to": to_time,
            })

            series = [
                {
                    "metric": s.get("metric"),
                    "scope": s.get("scope"),
                    "pointlist": s.get("pointlist", []),
                    "unit": s.get("unit"),
                }
                for s in result.get("series", [])
            ]

            return ToolResult.ok({
                "series": series,
                "query": result.get("query"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="QUERY_METRICS_FAILED")

    async def send_event(
        self,
        title: str,
        text: str,
        alert_type: str = "info",
        tags: Optional[List[str]] = None,
        priority: str = "normal",
        source_type_name: str = "maestro",
    ) -> ToolResult:
        """
        Send an event.

        Args:
            title: Event title
            text: Event text
            alert_type: 'error', 'warning', 'info', or 'success'
            tags: Event tags
            priority: 'normal' or 'low'
            source_type_name: Source type

        Returns:
            ToolResult with event ID
        """
        try:
            result = await self._api_call("POST", "events", json={
                "title": title,
                "text": text,
                "alert_type": alert_type,
                "priority": priority,
                "tags": tags or [],
                "source_type_name": source_type_name,
            })

            return ToolResult.ok({
                "sent": True,
                "event_id": result.get("event", {}).get("id"),
                "url": result.get("event", {}).get("url"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEND_EVENT_FAILED")

    async def create_monitor(
        self,
        name: str,
        query: str,
        monitor_type: str = "metric alert",
        message: str = "",
        tags: Optional[List[str]] = None,
        options: Optional[Dict] = None,
    ) -> ToolResult:
        """
        Create a monitor.

        Args:
            name: Monitor name
            query: Monitor query
            monitor_type: Monitor type
            message: Alert message
            tags: Monitor tags
            options: Monitor options

        Returns:
            ToolResult with monitor ID
        """
        try:
            payload = {
                "name": name,
                "type": monitor_type,
                "query": query,
                "message": message,
                "tags": tags or [],
            }
            if options:
                payload["options"] = options

            result = await self._api_call("POST", "monitor", json=payload)

            return ToolResult.ok({
                "created": True,
                "id": result.get("id"),
                "name": result.get("name"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_MONITOR_FAILED")

    async def get_monitor(self, monitor_id: int) -> ToolResult:
        """
        Get monitor details.

        Args:
            monitor_id: Monitor ID

        Returns:
            ToolResult with monitor details
        """
        try:
            result = await self._api_call("GET", f"monitor/{monitor_id}")

            return ToolResult.ok({
                "id": result.get("id"),
                "name": result.get("name"),
                "type": result.get("type"),
                "query": result.get("query"),
                "message": result.get("message"),
                "tags": result.get("tags", []),
                "overall_state": result.get("overall_state"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_MONITOR_FAILED")

    async def update_monitor(
        self,
        monitor_id: int,
        name: Optional[str] = None,
        query: Optional[str] = None,
        message: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        Update a monitor.

        Args:
            monitor_id: Monitor ID
            name: New name
            query: New query
            message: New message
            tags: New tags

        Returns:
            ToolResult with update status
        """
        try:
            payload = {}
            if name:
                payload["name"] = name
            if query:
                payload["query"] = query
            if message:
                payload["message"] = message
            if tags:
                payload["tags"] = tags

            result = await self._api_call("PUT", f"monitor/{monitor_id}", json=payload)

            return ToolResult.ok({
                "updated": True,
                "id": result.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_MONITOR_FAILED")

    async def delete_monitor(self, monitor_id: int) -> ToolResult:
        """
        Delete a monitor.

        Args:
            monitor_id: Monitor ID

        Returns:
            ToolResult with deletion status
        """
        try:
            await self._api_call("DELETE", f"monitor/{monitor_id}")
            return ToolResult.ok({"deleted": True, "id": monitor_id})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DELETE_MONITOR_FAILED")

    async def list_monitors(
        self,
        tags: Optional[List[str]] = None,
        name: Optional[str] = None,
    ) -> ToolResult:
        """
        List monitors.

        Args:
            tags: Filter by tags
            name: Filter by name

        Returns:
            ToolResult with monitor list
        """
        try:
            params = {}
            if tags:
                params["monitor_tags"] = ",".join(tags)
            if name:
                params["name"] = name

            result = await self._api_call("GET", "monitor", params=params)

            monitors = [
                {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "type": m.get("type"),
                    "overall_state": m.get("overall_state"),
                    "tags": m.get("tags", []),
                }
                for m in result
            ]

            return ToolResult.ok({"monitors": monitors})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_MONITORS_FAILED")

    async def get_dashboard(self, dashboard_id: str) -> ToolResult:
        """
        Get dashboard details.

        Args:
            dashboard_id: Dashboard ID

        Returns:
            ToolResult with dashboard details
        """
        try:
            result = await self._api_call("GET", f"dashboard/{dashboard_id}")

            return ToolResult.ok({
                "id": result.get("id"),
                "title": result.get("title"),
                "description": result.get("description"),
                "widgets": len(result.get("widgets", [])),
                "url": result.get("url"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_DASHBOARD_FAILED")

    async def list_dashboards(self) -> ToolResult:
        """List all dashboards."""
        try:
            result = await self._api_call("GET", "dashboard")

            dashboards = [
                {
                    "id": d.get("id"),
                    "title": d.get("title"),
                    "author": d.get("author_name"),
                }
                for d in result.get("dashboards", [])
            ]

            return ToolResult.ok({"dashboards": dashboards})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_DASHBOARDS_FAILED")

    async def mute_monitor(
        self,
        monitor_id: int,
        end: Optional[int] = None,
        scope: Optional[str] = None,
    ) -> ToolResult:
        """
        Mute a monitor.

        Args:
            monitor_id: Monitor ID
            end: End timestamp (epoch seconds)
            scope: Scope to mute

        Returns:
            ToolResult with mute status
        """
        try:
            payload = {}
            if end:
                payload["end"] = end
            if scope:
                payload["scope"] = scope

            result = await self._api_call("POST", f"monitor/{monitor_id}/mute", json=payload)

            return ToolResult.ok({
                "muted": True,
                "id": result.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="MUTE_MONITOR_FAILED")

    async def search_hosts(
        self,
        filter: Optional[str] = None,
        count: int = 100,
    ) -> ToolResult:
        """
        Search for hosts.

        Args:
            filter: Filter string
            count: Maximum results

        Returns:
            ToolResult with host list
        """
        try:
            params = {"count": count}
            if filter:
                params["filter"] = filter

            result = await self._api_call("GET", "hosts", params=params)

            hosts = [
                {
                    "name": h.get("name"),
                    "id": h.get("id"),
                    "apps": h.get("apps", []),
                    "is_muted": h.get("is_muted", False),
                    "last_reported_time": h.get("last_reported_time"),
                }
                for h in result.get("host_list", [])
            ]

            return ToolResult.ok({
                "hosts": hosts,
                "total_matching": result.get("total_matching", 0),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEARCH_HOSTS_FAILED")
