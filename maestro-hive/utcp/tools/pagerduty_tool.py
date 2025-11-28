"""
UTCP PagerDuty Integration Tool

Provides PagerDuty integration for AI agents:
- Create/update incidents
- Manage alerts
- List services and escalation policies
- Acknowledge/resolve incidents

Part of MD-432: Build PagerDuty Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class PagerDutyTool(UTCPTool):
    """PagerDuty integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="pagerduty",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
            ],
            required_credentials=["pd_api_key"],
            optional_credentials=["pd_from_email", "default_service_id"],
            rate_limit=200,  # PagerDuty rate limit
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_key = credentials["pd_api_key"]
        self.from_email = credentials.get("pd_from_email")
        self.default_service = credentials.get("default_service_id")
        self.base_url = "https://api.pagerduty.com"

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make PagerDuty API call."""
        headers = {
            "Authorization": f"Token token={self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
        }

        if self.from_email:
            headers["From"] = self.from_email

        url = f"{self.base_url}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"PagerDuty error: {text}", code=f"PD_{response.status}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"PagerDuty error: {text}", code=f"PD_{response.status}")
                    return await response.json()
            elif method == "PUT":
                async with session.put(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"PagerDuty error: {text}", code=f"PD_{response.status}")
                    return await response.json()

    async def health_check(self) -> ToolResult:
        """Check PagerDuty API connectivity."""
        try:
            result = await self._api_call("GET", "abilities")
            return ToolResult.ok({
                "connected": True,
                "abilities": result.get("abilities", []),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def create_incident(
        self,
        title: str,
        service_id: Optional[str] = None,
        urgency: str = "high",
        body: Optional[str] = None,
        escalation_policy_id: Optional[str] = None,
        incident_key: Optional[str] = None,
    ) -> ToolResult:
        """
        Create a new incident.

        Args:
            title: Incident title
            service_id: Service ID (uses default if not provided)
            urgency: 'high' or 'low'
            body: Incident details
            escalation_policy_id: Escalation policy ID
            incident_key: Deduplication key

        Returns:
            ToolResult with incident info
        """
        try:
            service_id = service_id or self.default_service
            if not service_id:
                return ToolResult.fail("service_id required", code="MISSING_SERVICE")

            incident_data = {
                "type": "incident",
                "title": title,
                "service": {"id": service_id, "type": "service_reference"},
                "urgency": urgency,
            }

            if body:
                incident_data["body"] = {"type": "incident_body", "details": body}
            if escalation_policy_id:
                incident_data["escalation_policy"] = {
                    "id": escalation_policy_id,
                    "type": "escalation_policy_reference"
                }
            if incident_key:
                incident_data["incident_key"] = incident_key

            result = await self._api_call("POST", "incidents", json={"incident": incident_data})

            incident = result.get("incident", {})
            return ToolResult.ok({
                "created": True,
                "id": incident.get("id"),
                "incident_number": incident.get("incident_number"),
                "status": incident.get("status"),
                "html_url": incident.get("html_url"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_INCIDENT_FAILED")

    async def get_incident(self, incident_id: str) -> ToolResult:
        """
        Get incident details.

        Args:
            incident_id: Incident ID

        Returns:
            ToolResult with incident details
        """
        try:
            result = await self._api_call("GET", f"incidents/{incident_id}")

            incident = result.get("incident", {})
            return ToolResult.ok({
                "id": incident.get("id"),
                "incident_number": incident.get("incident_number"),
                "title": incident.get("title"),
                "status": incident.get("status"),
                "urgency": incident.get("urgency"),
                "service": incident.get("service", {}).get("summary"),
                "html_url": incident.get("html_url"),
                "created_at": incident.get("created_at"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_INCIDENT_FAILED")

    async def update_incident(
        self,
        incident_id: str,
        status: Optional[str] = None,
        resolution: Optional[str] = None,
        title: Optional[str] = None,
        urgency: Optional[str] = None,
    ) -> ToolResult:
        """
        Update an incident.

        Args:
            incident_id: Incident ID
            status: 'acknowledged' or 'resolved'
            resolution: Resolution note (for resolved)
            title: New title
            urgency: 'high' or 'low'

        Returns:
            ToolResult with update status
        """
        try:
            incident_data = {
                "id": incident_id,
                "type": "incident",
            }

            if status:
                incident_data["status"] = status
            if resolution:
                incident_data["resolution"] = resolution
            if title:
                incident_data["title"] = title
            if urgency:
                incident_data["urgency"] = urgency

            result = await self._api_call("PUT", f"incidents/{incident_id}", json={
                "incident": incident_data
            })

            incident = result.get("incident", {})
            return ToolResult.ok({
                "updated": True,
                "id": incident.get("id"),
                "status": incident.get("status"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_INCIDENT_FAILED")

    async def list_incidents(
        self,
        statuses: Optional[List[str]] = None,
        service_ids: Optional[List[str]] = None,
        urgencies: Optional[List[str]] = None,
        limit: int = 25,
    ) -> ToolResult:
        """
        List incidents.

        Args:
            statuses: Filter by status
            service_ids: Filter by service
            urgencies: Filter by urgency
            limit: Maximum results

        Returns:
            ToolResult with incident list
        """
        try:
            params = {"limit": limit}
            if statuses:
                params["statuses[]"] = statuses
            if service_ids:
                params["service_ids[]"] = service_ids
            if urgencies:
                params["urgencies[]"] = urgencies

            result = await self._api_call("GET", "incidents", params=params)

            incidents = [
                {
                    "id": inc.get("id"),
                    "incident_number": inc.get("incident_number"),
                    "title": inc.get("title"),
                    "status": inc.get("status"),
                    "urgency": inc.get("urgency"),
                    "service": inc.get("service", {}).get("summary"),
                    "created_at": inc.get("created_at"),
                }
                for inc in result.get("incidents", [])
            ]

            return ToolResult.ok({"incidents": incidents})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_INCIDENTS_FAILED")

    async def list_services(self) -> ToolResult:
        """List all services."""
        try:
            result = await self._api_call("GET", "services")

            services = [
                {
                    "id": svc.get("id"),
                    "name": svc.get("name"),
                    "description": svc.get("description"),
                    "status": svc.get("status"),
                    "escalation_policy": svc.get("escalation_policy", {}).get("summary"),
                }
                for svc in result.get("services", [])
            ]

            return ToolResult.ok({"services": services})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_SERVICES_FAILED")

    async def list_escalation_policies(self) -> ToolResult:
        """List all escalation policies."""
        try:
            result = await self._api_call("GET", "escalation_policies")

            policies = [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "description": p.get("description"),
                    "num_loops": p.get("num_loops"),
                }
                for p in result.get("escalation_policies", [])
            ]

            return ToolResult.ok({"policies": policies})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_POLICIES_FAILED")

    async def list_oncalls(
        self,
        schedule_ids: Optional[List[str]] = None,
        escalation_policy_ids: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        List current on-calls.

        Args:
            schedule_ids: Filter by schedule
            escalation_policy_ids: Filter by policy

        Returns:
            ToolResult with on-call list
        """
        try:
            params = {}
            if schedule_ids:
                params["schedule_ids[]"] = schedule_ids
            if escalation_policy_ids:
                params["escalation_policy_ids[]"] = escalation_policy_ids

            result = await self._api_call("GET", "oncalls", params=params)

            oncalls = [
                {
                    "user": oc.get("user", {}).get("summary"),
                    "user_id": oc.get("user", {}).get("id"),
                    "schedule": oc.get("schedule", {}).get("summary") if oc.get("schedule") else None,
                    "escalation_policy": oc.get("escalation_policy", {}).get("summary"),
                    "start": oc.get("start"),
                    "end": oc.get("end"),
                }
                for oc in result.get("oncalls", [])
            ]

            return ToolResult.ok({"oncalls": oncalls})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_ONCALLS_FAILED")

    async def add_note(self, incident_id: str, content: str) -> ToolResult:
        """
        Add a note to an incident.

        Args:
            incident_id: Incident ID
            content: Note content

        Returns:
            ToolResult with note info
        """
        try:
            result = await self._api_call("POST", f"incidents/{incident_id}/notes", json={
                "note": {
                    "content": content,
                }
            })

            note = result.get("note", {})
            return ToolResult.ok({
                "added": True,
                "note_id": note.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_NOTE_FAILED")

    async def snooze_incident(
        self,
        incident_id: str,
        duration: int,
    ) -> ToolResult:
        """
        Snooze an incident.

        Args:
            incident_id: Incident ID
            duration: Snooze duration in seconds

        Returns:
            ToolResult with snooze status
        """
        try:
            result = await self._api_call("POST", f"incidents/{incident_id}/snooze", json={
                "duration": duration,
            })

            incident = result.get("incident", {})
            return ToolResult.ok({
                "snoozed": True,
                "id": incident.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SNOOZE_INCIDENT_FAILED")
