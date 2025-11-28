"""
UTCP Google Workspace Integration Tool

Provides Google Workspace integration for AI agents:
- Gmail operations
- Google Calendar management
- Google Drive operations
- Google Docs/Sheets

Part of MD-434: Build Google Workspace Integration Adapter
"""

import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class GoogleWorkspaceTool(UTCPTool):
    """Google Workspace integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="google_workspace",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
                ToolCapability.DELETE,
            ],
            required_credentials=["google_access_token"],
            optional_credentials=["google_refresh_token", "default_calendar_id"],
            rate_limit=None,
            timeout=30,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.access_token = credentials["google_access_token"]
        self.refresh_token = credentials.get("google_refresh_token")
        self.default_calendar = credentials.get("default_calendar_id", "primary")

    async def _api_call(self, method: str, url: str, **kwargs) -> Any:
        """Make Google API call."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Google API error: {text}", code=f"GOOGLE_{response.status}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Google API error: {text}", code=f"GOOGLE_{response.status}")
                    return await response.json()
            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Google API error: {text}", code=f"GOOGLE_{response.status}")
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Google API error: {text}", code=f"GOOGLE_{response.status}")
                    return {}

    async def health_check(self) -> ToolResult:
        """Check Google API connectivity."""
        try:
            result = await self._api_call(
                "GET",
                "https://www.googleapis.com/oauth2/v1/userinfo"
            )
            return ToolResult.ok({
                "connected": True,
                "email": result.get("email"),
                "name": result.get("name"),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    # =========================================================================
    # Gmail Operations
    # =========================================================================

    async def gmail_send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        Send an email.

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            ToolResult with message ID
        """
        try:
            import base64

            # Build email
            email_lines = [
                f"To: {to}",
                f"Subject: {subject}",
            ]
            if cc:
                email_lines.append(f"Cc: {', '.join(cc)}")
            if bcc:
                email_lines.append(f"Bcc: {', '.join(bcc)}")

            email_lines.extend(["", body])
            raw_email = "\r\n".join(email_lines)
            encoded = base64.urlsafe_b64encode(raw_email.encode()).decode()

            result = await self._api_call(
                "POST",
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                json={"raw": encoded}
            )

            return ToolResult.ok({
                "sent": True,
                "message_id": result.get("id"),
                "thread_id": result.get("threadId"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GMAIL_SEND_FAILED")

    async def gmail_list(
        self,
        query: Optional[str] = None,
        max_results: int = 10,
    ) -> ToolResult:
        """
        List emails.

        Args:
            query: Gmail search query
            max_results: Maximum results

        Returns:
            ToolResult with message list
        """
        try:
            params = {"maxResults": max_results}
            if query:
                params["q"] = query

            result = await self._api_call(
                "GET",
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                params=params
            )

            messages = result.get("messages", [])

            return ToolResult.ok({
                "messages": messages,
                "result_size_estimate": result.get("resultSizeEstimate", 0),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GMAIL_LIST_FAILED")

    async def gmail_get(self, message_id: str) -> ToolResult:
        """
        Get email details.

        Args:
            message_id: Message ID

        Returns:
            ToolResult with message details
        """
        try:
            result = await self._api_call(
                "GET",
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
            )

            # Extract headers
            headers = {}
            for header in result.get("payload", {}).get("headers", []):
                headers[header["name"].lower()] = header["value"]

            return ToolResult.ok({
                "id": result.get("id"),
                "thread_id": result.get("threadId"),
                "subject": headers.get("subject"),
                "from": headers.get("from"),
                "to": headers.get("to"),
                "date": headers.get("date"),
                "snippet": result.get("snippet"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GMAIL_GET_FAILED")

    # =========================================================================
    # Google Calendar Operations
    # =========================================================================

    async def calendar_list_events(
        self,
        calendar_id: Optional[str] = None,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 10,
    ) -> ToolResult:
        """
        List calendar events.

        Args:
            calendar_id: Calendar ID
            time_min: Start time (RFC3339)
            time_max: End time (RFC3339)
            max_results: Maximum results

        Returns:
            ToolResult with event list
        """
        try:
            calendar_id = calendar_id or self.default_calendar
            params = {
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if time_min:
                params["timeMin"] = time_min
            if time_max:
                params["timeMax"] = time_max

            result = await self._api_call(
                "GET",
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                params=params
            )

            events = [
                {
                    "id": e.get("id"),
                    "summary": e.get("summary"),
                    "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                    "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                    "location": e.get("location"),
                    "description": e.get("description"),
                }
                for e in result.get("items", [])
            ]

            return ToolResult.ok({"events": events})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CALENDAR_LIST_FAILED")

    async def calendar_create_event(
        self,
        summary: str,
        start: str,
        end: str,
        calendar_id: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        Create a calendar event.

        Args:
            summary: Event title
            start: Start time (RFC3339)
            end: End time (RFC3339)
            calendar_id: Calendar ID
            description: Event description
            location: Event location
            attendees: Attendee emails

        Returns:
            ToolResult with event info
        """
        try:
            calendar_id = calendar_id or self.default_calendar

            event_data = {
                "summary": summary,
                "start": {"dateTime": start},
                "end": {"dateTime": end},
            }
            if description:
                event_data["description"] = description
            if location:
                event_data["location"] = location
            if attendees:
                event_data["attendees"] = [{"email": e} for e in attendees]

            result = await self._api_call(
                "POST",
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                json=event_data
            )

            return ToolResult.ok({
                "created": True,
                "id": result.get("id"),
                "html_link": result.get("htmlLink"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CALENDAR_CREATE_FAILED")

    async def calendar_delete_event(
        self,
        event_id: str,
        calendar_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Delete a calendar event.

        Args:
            event_id: Event ID
            calendar_id: Calendar ID

        Returns:
            ToolResult with deletion status
        """
        try:
            calendar_id = calendar_id or self.default_calendar

            await self._api_call(
                "DELETE",
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
            )

            return ToolResult.ok({"deleted": True, "id": event_id})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CALENDAR_DELETE_FAILED")

    # =========================================================================
    # Google Drive Operations
    # =========================================================================

    async def drive_list(
        self,
        query: Optional[str] = None,
        page_size: int = 10,
    ) -> ToolResult:
        """
        List Drive files.

        Args:
            query: Drive search query
            page_size: Maximum results

        Returns:
            ToolResult with file list
        """
        try:
            params = {
                "pageSize": page_size,
                "fields": "files(id,name,mimeType,modifiedTime,size)",
            }
            if query:
                params["q"] = query

            result = await self._api_call(
                "GET",
                "https://www.googleapis.com/drive/v3/files",
                params=params
            )

            files = [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "mime_type": f.get("mimeType"),
                    "modified_time": f.get("modifiedTime"),
                    "size": f.get("size"),
                }
                for f in result.get("files", [])
            ]

            return ToolResult.ok({"files": files})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DRIVE_LIST_FAILED")

    async def drive_get_file(self, file_id: str) -> ToolResult:
        """
        Get file metadata.

        Args:
            file_id: File ID

        Returns:
            ToolResult with file metadata
        """
        try:
            result = await self._api_call(
                "GET",
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={"fields": "id,name,mimeType,modifiedTime,size,webViewLink,webContentLink"}
            )

            return ToolResult.ok({
                "id": result.get("id"),
                "name": result.get("name"),
                "mime_type": result.get("mimeType"),
                "modified_time": result.get("modifiedTime"),
                "size": result.get("size"),
                "web_view_link": result.get("webViewLink"),
                "web_content_link": result.get("webContentLink"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DRIVE_GET_FILE_FAILED")

    async def drive_create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Create a folder.

        Args:
            name: Folder name
            parent_id: Parent folder ID

        Returns:
            ToolResult with folder info
        """
        try:
            file_metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                file_metadata["parents"] = [parent_id]

            result = await self._api_call(
                "POST",
                "https://www.googleapis.com/drive/v3/files",
                json=file_metadata
            )

            return ToolResult.ok({
                "created": True,
                "id": result.get("id"),
                "name": result.get("name"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DRIVE_CREATE_FOLDER_FAILED")

    async def drive_delete(self, file_id: str) -> ToolResult:
        """
        Delete a file or folder.

        Args:
            file_id: File ID

        Returns:
            ToolResult with deletion status
        """
        try:
            await self._api_call(
                "DELETE",
                f"https://www.googleapis.com/drive/v3/files/{file_id}"
            )

            return ToolResult.ok({"deleted": True, "id": file_id})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DRIVE_DELETE_FAILED")

    async def drive_share(
        self,
        file_id: str,
        email: str,
        role: str = "reader",
    ) -> ToolResult:
        """
        Share a file.

        Args:
            file_id: File ID
            email: Email to share with
            role: 'reader', 'writer', or 'commenter'

        Returns:
            ToolResult with permission info
        """
        try:
            result = await self._api_call(
                "POST",
                f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
                json={
                    "type": "user",
                    "role": role,
                    "emailAddress": email,
                }
            )

            return ToolResult.ok({
                "shared": True,
                "permission_id": result.get("id"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DRIVE_SHARE_FAILED")
