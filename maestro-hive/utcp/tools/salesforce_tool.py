"""
UTCP Salesforce Integration Tool

Provides Salesforce integration for AI agents:
- Query records with SOQL
- Create/update/delete records
- Execute Apex
- Manage metadata

Part of MD-430: Build Salesforce Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class SalesforceTool(UTCPTool):
    """Salesforce integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="salesforce",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.DELETE,
                ToolCapability.SEARCH,
                ToolCapability.EXECUTE,
            ],
            required_credentials=["sf_instance_url", "sf_access_token"],
            optional_credentials=["sf_api_version"],
            rate_limit=None,
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.instance_url = credentials["sf_instance_url"].rstrip("/")
        self.access_token = credentials["sf_access_token"]
        self.api_version = credentials.get("sf_api_version", "v58.0")

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make Salesforce API call."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.instance_url}/services/data/{self.api_version}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Salesforce error: {text}", code=f"SF_{response.status}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Salesforce error: {text}", code=f"SF_{response.status}")
                    return await response.json() if response.content_length else {}
            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Salesforce error: {text}", code=f"SF_{response.status}")
                    return {}
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Salesforce error: {text}", code=f"SF_{response.status}")
                    return {}

    async def health_check(self) -> ToolResult:
        """Check Salesforce API connectivity."""
        try:
            result = await self._api_call("GET", "")
            return ToolResult.ok({
                "connected": True,
                "instance_url": self.instance_url,
                "api_version": self.api_version,
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def query(self, soql: str) -> ToolResult:
        """
        Execute a SOQL query.

        Args:
            soql: SOQL query string

        Returns:
            ToolResult with query results
        """
        try:
            result = await self._api_call("GET", "query", params={"q": soql})

            return ToolResult.ok({
                "records": result.get("records", []),
                "total_size": result.get("totalSize", 0),
                "done": result.get("done", True),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="QUERY_FAILED")

    async def search(self, sosl: str) -> ToolResult:
        """
        Execute a SOSL search.

        Args:
            sosl: SOSL search string

        Returns:
            ToolResult with search results
        """
        try:
            result = await self._api_call("GET", "search", params={"q": sosl})

            return ToolResult.ok({
                "search_records": result.get("searchRecords", []),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SEARCH_FAILED")

    async def create_record(
        self,
        sobject: str,
        data: Dict[str, Any],
    ) -> ToolResult:
        """
        Create a new record.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact')
            data: Record data

        Returns:
            ToolResult with record ID
        """
        try:
            result = await self._api_call("POST", f"sobjects/{sobject}", json=data)

            return ToolResult.ok({
                "created": True,
                "id": result.get("id"),
                "success": result.get("success"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_RECORD_FAILED")

    async def update_record(
        self,
        sobject: str,
        record_id: str,
        data: Dict[str, Any],
    ) -> ToolResult:
        """
        Update an existing record.

        Args:
            sobject: SObject type
            record_id: Record ID
            data: Fields to update

        Returns:
            ToolResult with update status
        """
        try:
            await self._api_call("PATCH", f"sobjects/{sobject}/{record_id}", json=data)

            return ToolResult.ok({
                "updated": True,
                "id": record_id,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPDATE_RECORD_FAILED")

    async def delete_record(self, sobject: str, record_id: str) -> ToolResult:
        """
        Delete a record.

        Args:
            sobject: SObject type
            record_id: Record ID

        Returns:
            ToolResult with deletion status
        """
        try:
            await self._api_call("DELETE", f"sobjects/{sobject}/{record_id}")

            return ToolResult.ok({
                "deleted": True,
                "id": record_id,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DELETE_RECORD_FAILED")

    async def get_record(
        self,
        sobject: str,
        record_id: str,
        fields: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        Get a specific record.

        Args:
            sobject: SObject type
            record_id: Record ID
            fields: Fields to retrieve

        Returns:
            ToolResult with record data
        """
        try:
            params = {}
            if fields:
                params["fields"] = ",".join(fields)

            result = await self._api_call("GET", f"sobjects/{sobject}/{record_id}", params=params)

            return ToolResult.ok({
                "id": result.get("Id"),
                "attributes": result.get("attributes"),
                **{k: v for k, v in result.items() if k not in ["Id", "attributes"]},
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_RECORD_FAILED")

    async def describe_object(self, sobject: str) -> ToolResult:
        """
        Get metadata about an SObject.

        Args:
            sobject: SObject type

        Returns:
            ToolResult with object metadata
        """
        try:
            result = await self._api_call("GET", f"sobjects/{sobject}/describe")

            fields = [
                {
                    "name": f.get("name"),
                    "label": f.get("label"),
                    "type": f.get("type"),
                    "required": not f.get("nillable", True),
                }
                for f in result.get("fields", [])
            ]

            return ToolResult.ok({
                "name": result.get("name"),
                "label": result.get("label"),
                "fields": fields,
                "createable": result.get("createable"),
                "updateable": result.get("updateable"),
                "deletable": result.get("deletable"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DESCRIBE_FAILED")

    async def list_objects(self) -> ToolResult:
        """List all available SObjects."""
        try:
            result = await self._api_call("GET", "sobjects")

            sobjects = [
                {
                    "name": obj.get("name"),
                    "label": obj.get("label"),
                    "custom": obj.get("custom", False),
                }
                for obj in result.get("sobjects", [])
            ]

            return ToolResult.ok({"sobjects": sobjects})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_OBJECTS_FAILED")

    async def execute_apex(self, apex_code: str) -> ToolResult:
        """
        Execute anonymous Apex code.

        Args:
            apex_code: Apex code to execute

        Returns:
            ToolResult with execution result
        """
        try:
            # Use tooling API for Apex execution
            url = f"{self.instance_url}/services/data/{self.api_version}/tooling/executeAnonymous"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params={"anonymousBody": apex_code}) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Apex execution error: {text}", code=f"SF_{response.status}")

                    result = await response.json()

            return ToolResult.ok({
                "compiled": result.get("compiled"),
                "success": result.get("success"),
                "compile_problem": result.get("compileProblem"),
                "exception_message": result.get("exceptionMessage"),
                "exception_stack_trace": result.get("exceptionStackTrace"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="EXECUTE_APEX_FAILED")

    async def create_task(
        self,
        subject: str,
        what_id: Optional[str] = None,
        who_id: Optional[str] = None,
        status: str = "Not Started",
        priority: str = "Normal",
        description: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> ToolResult:
        """
        Create a Task record.

        Args:
            subject: Task subject
            what_id: Related record ID (Account, Opportunity, etc.)
            who_id: Related contact/lead ID
            status: Task status
            priority: Task priority
            description: Task description
            due_date: Due date (YYYY-MM-DD)

        Returns:
            ToolResult with task ID
        """
        try:
            data = {
                "Subject": subject,
                "Status": status,
                "Priority": priority,
            }
            if what_id:
                data["WhatId"] = what_id
            if who_id:
                data["WhoId"] = who_id
            if description:
                data["Description"] = description
            if due_date:
                data["ActivityDate"] = due_date

            return await self.create_record("Task", data)
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_TASK_FAILED")

    async def upsert_record(
        self,
        sobject: str,
        external_id_field: str,
        external_id: str,
        data: Dict[str, Any],
    ) -> ToolResult:
        """
        Upsert a record using external ID.

        Args:
            sobject: SObject type
            external_id_field: External ID field name
            external_id: External ID value
            data: Record data

        Returns:
            ToolResult with upsert status
        """
        try:
            endpoint = f"sobjects/{sobject}/{external_id_field}/{external_id}"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            url = f"{self.instance_url}/services/data/{self.api_version}/{endpoint}"

            async with aiohttp.ClientSession() as session:
                async with session.patch(url, headers=headers, json=data) as response:
                    if response.status == 201:
                        result = await response.json()
                        return ToolResult.ok({
                            "created": True,
                            "id": result.get("id"),
                        })
                    elif response.status == 204:
                        return ToolResult.ok({
                            "updated": True,
                            "external_id": external_id,
                        })
                    else:
                        text = await response.text()
                        raise ToolError(f"Upsert error: {text}", code=f"SF_{response.status}")
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="UPSERT_FAILED")
