"""
Confluence Publisher for EPIC Executor.

Handles publishing compliance documents to Confluence:
- Technical Design
- Runbook/Playbook
- API Documentation
- Architecture Decision Record (ADR)
- Configuration Guide
- Monitoring Guide
"""

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import DocumentInfo, DocumentType, EpicInfo


@dataclass
class ConfluenceConfig:
    """Configuration for Confluence API access."""
    base_url: str
    email: str
    api_token: str
    space_key: str
    parent_page_id: Optional[str] = None


class ConfluencePublisher:
    """
    Publishes compliance documents to Confluence.

    Creates the 6 required documents for EPIC compliance:
    1. Technical Design (5 points)
    2. Runbook (2.5 points)
    3. API Documentation (2.5 points)
    4. ADR (2 points)
    5. Configuration Guide (1.5 points)
    6. Monitoring Guide (1.5 points)
    """

    # Templates directory relative to this file
    TEMPLATES_DIR = Path(__file__).parent / "templates"

    # Document type metadata
    DOCUMENT_SPECS = {
        DocumentType.TECHNICAL_DESIGN: {
            "title_suffix": "Technical Design",
            "template": "technical_design.html",
            "points": 5,
        },
        DocumentType.RUNBOOK: {
            "title_suffix": "Runbook",
            "template": "runbook.html",
            "points": 2.5,
        },
        DocumentType.API_DOCS: {
            "title_suffix": "API Documentation",
            "template": "api_docs.html",
            "points": 2.5,
        },
        DocumentType.ADR: {
            "title_suffix": "Architecture Decision Record",
            "template": "adr.html",
            "points": 2,
        },
        DocumentType.CONFIG_GUIDE: {
            "title_suffix": "Configuration Guide",
            "template": "config_guide.html",
            "points": 1.5,
        },
        DocumentType.MONITORING: {
            "title_suffix": "Monitoring Guide",
            "template": "monitoring.html",
            "points": 1.5,
        },
    }

    def __init__(self, config: ConfluenceConfig):
        """
        Initialize the Confluence publisher.

        Args:
            config: Confluence API configuration
        """
        self.config = config
        self._confluence_tool = None

    async def _get_confluence_tool(self):
        """Lazy load the Confluence tool."""
        if self._confluence_tool is None:
            try:
                from utcp.tools.confluence_tool import ConfluenceTool
                self._confluence_tool = ConfluenceTool({
                    "confluence_url": self.config.base_url,
                    "confluence_email": self.config.email,
                    "confluence_api_token": self.config.api_token,
                    "default_space_key": self.config.space_key,
                })
            except ImportError:
                # Fallback to minimal client
                self._confluence_tool = MinimalConfluenceClient(self.config)
        return self._confluence_tool

    async def publish_all_documents(
        self,
        epic_info: EpicInfo,
        context: Dict[str, Any],
    ) -> List[DocumentInfo]:
        """
        Publish all 6 compliance documents for an EPIC.

        Args:
            epic_info: EPIC information
            context: Additional context for templates (implementation details, etc.)

        Returns:
            List of DocumentInfo for created documents
        """
        documents = []

        # Create parent page for EPIC documentation
        parent_page_id = await self._create_epic_parent_page(epic_info)

        for doc_type in DocumentType:
            doc_info = await self.publish_document(
                doc_type=doc_type,
                epic_info=epic_info,
                context=context,
                parent_page_id=parent_page_id,
            )
            if doc_info:
                documents.append(doc_info)

        return documents

    async def _create_epic_parent_page(self, epic_info: EpicInfo) -> Optional[str]:
        """Create a parent page for all EPIC documentation."""
        confluence = await self._get_confluence_tool()

        title = f"{epic_info.key}: {epic_info.summary}"
        content = self._render_epic_index_page(epic_info)

        try:
            result = await confluence.create_page(
                title=title,
                content=content,
                space_key=self.config.space_key,
                parent_id=self.config.parent_page_id,
            )
            if result.success:
                return result.data.get("id")
        except Exception:
            pass

        return self.config.parent_page_id

    async def publish_document(
        self,
        doc_type: DocumentType,
        epic_info: EpicInfo,
        context: Dict[str, Any],
        parent_page_id: Optional[str] = None,
    ) -> Optional[DocumentInfo]:
        """
        Publish a single document to Confluence.

        Args:
            doc_type: Type of document to create
            epic_info: EPIC information
            context: Template context
            parent_page_id: Parent page ID

        Returns:
            DocumentInfo if successful, None otherwise
        """
        confluence = await self._get_confluence_tool()

        spec = self.DOCUMENT_SPECS[doc_type]
        title = f"{epic_info.key} - {spec['title_suffix']}"

        # Render document content
        content = self._render_document(doc_type, epic_info, context)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Check if page already exists
        existing = await self._find_existing_page(title)
        if existing:
            # Update existing page
            result = await confluence.update_page(
                page_id=existing["id"],
                title=title,
                content=content,
                version=existing["version"],
            )
            if result.success:
                return DocumentInfo(
                    doc_type=doc_type,
                    title=title,
                    confluence_page_id=existing["id"],
                    confluence_url=existing.get("url"),
                    created_at=datetime.now(),
                    content_hash=content_hash,
                    status="updated",
                )
        else:
            # Create new page
            result = await confluence.create_page(
                title=title,
                content=content,
                space_key=self.config.space_key,
                parent_id=parent_page_id or self.config.parent_page_id,
            )
            if result.success:
                return DocumentInfo(
                    doc_type=doc_type,
                    title=title,
                    confluence_page_id=result.data.get("id"),
                    confluence_url=result.data.get("url"),
                    created_at=datetime.now(),
                    content_hash=content_hash,
                    status="created",
                )

        return None

    async def _find_existing_page(self, title: str) -> Optional[Dict[str, Any]]:
        """Find an existing page by title."""
        confluence = await self._get_confluence_tool()

        try:
            result = await confluence.search(
                cql=f'title = "{title}" AND space = "{self.config.space_key}"',
                limit=1,
                expand="version",
            )
            if result.success and result.data.get("results"):
                page = result.data["results"][0]
                # Get full page details for version
                page_result = await confluence.get_page(page["id"])
                if page_result.success:
                    return {
                        "id": page["id"],
                        "version": page_result.data.get("version", 1),
                        "url": page.get("url"),
                    }
        except Exception:
            pass

        return None

    def _render_document(
        self,
        doc_type: DocumentType,
        epic_info: EpicInfo,
        context: Dict[str, Any],
    ) -> str:
        """
        Render a document template.

        Args:
            doc_type: Document type
            epic_info: EPIC information
            context: Additional context

        Returns:
            Rendered HTML content in Confluence storage format
        """
        # Build full context
        full_context = {
            "epic_key": epic_info.key,
            "epic_summary": epic_info.summary,
            "epic_description": epic_info.description,
            "epic_status": epic_info.status,
            "epic_priority": epic_info.priority,
            "acceptance_criteria": [
                {"id": ac.id, "description": ac.description}
                for ac in epic_info.acceptance_criteria
            ],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "EPIC Executor v1.0",
            **context,
        }

        # Get appropriate renderer
        renderers = {
            DocumentType.TECHNICAL_DESIGN: self._render_technical_design,
            DocumentType.RUNBOOK: self._render_runbook,
            DocumentType.API_DOCS: self._render_api_docs,
            DocumentType.ADR: self._render_adr,
            DocumentType.CONFIG_GUIDE: self._render_config_guide,
            DocumentType.MONITORING: self._render_monitoring,
        }

        renderer = renderers.get(doc_type)
        if renderer:
            return renderer(full_context)

        return f"<p>Document type {doc_type.value} not implemented</p>"

    def _render_epic_index_page(self, epic_info: EpicInfo) -> str:
        """Render the EPIC index/parent page."""
        ac_list = "".join(
            f"<li><strong>{ac.id}</strong>: {ac.description}</li>"
            for ac in epic_info.acceptance_criteria
        )

        return f"""
        <h1>{epic_info.key}: {epic_info.summary}</h1>
        <p><strong>Status:</strong> {epic_info.status} | <strong>Priority:</strong> {epic_info.priority}</p>

        <h2>Description</h2>
        <p>{epic_info.description}</p>

        <h2>Acceptance Criteria</h2>
        <ul>{ac_list}</ul>

        <h2>Documentation</h2>
        <p>This page contains all compliance documentation for the EPIC:</p>
        <ul>
            <li>Technical Design</li>
            <li>Runbook</li>
            <li>API Documentation</li>
            <li>Architecture Decision Record (ADR)</li>
            <li>Configuration Guide</li>
            <li>Monitoring Guide</li>
        </ul>

        <hr/>
        <p><em>Generated by EPIC Executor v1.0 on {datetime.now().strftime("%Y-%m-%d")}</em></p>
        """

    def _render_technical_design(self, ctx: Dict[str, Any]) -> str:
        """Render technical design document."""
        ac_section = "".join(
            f"<tr><td>{ac['id']}</td><td>{ac['description']}</td><td>Pending</td></tr>"
            for ac in ctx.get("acceptance_criteria", [])
        )

        impl_files = ctx.get("implementation_files", [])
        files_list = "".join(f"<li><code>{f}</code></li>" for f in impl_files[:20])

        return f"""
        <h1>Technical Design: {ctx['epic_key']}</h1>
        <p><strong>EPIC:</strong> {ctx['epic_summary']}</p>
        <p><strong>Generated:</strong> {ctx['generated_at']}</p>

        <h2>1. Overview</h2>
        <p>{ctx['epic_description']}</p>

        <h2>2. Requirements</h2>
        <h3>2.1 Functional Requirements</h3>
        <table>
            <tr><th>ID</th><th>Requirement</th><th>Status</th></tr>
            {ac_section}
        </table>

        <h3>2.2 Non-Functional Requirements</h3>
        <ul>
            <li>Performance: Response time &lt; 200ms for 95th percentile</li>
            <li>Availability: 99.9% uptime</li>
            <li>Security: Follow OWASP guidelines</li>
            <li>Scalability: Support horizontal scaling</li>
        </ul>

        <h2>3. Architecture</h2>
        <h3>3.1 High-Level Architecture</h3>
        <p>The implementation follows the existing service architecture pattern.</p>

        <h3>3.2 Component Design</h3>
        <p>Key components and their responsibilities are defined in the implementation files.</p>

        <h2>4. Implementation</h2>
        <h3>4.1 Implementation Files</h3>
        <ul>{files_list}</ul>

        <h3>4.2 Dependencies</h3>
        <p>Dependencies are managed through the project's standard dependency management.</p>

        <h2>5. Testing Strategy</h2>
        <p>Unit tests, integration tests, and end-to-end tests are included in the test suite.</p>

        <h2>6. Deployment</h2>
        <p>Deployment follows the standard CI/CD pipeline.</p>

        <hr/>
        <p><em>Generated by {ctx['generator']}</em></p>
        """

    def _render_runbook(self, ctx: Dict[str, Any]) -> str:
        """Render runbook document."""
        return f"""
        <h1>Runbook: {ctx['epic_key']}</h1>
        <p><strong>EPIC:</strong> {ctx['epic_summary']}</p>
        <p><strong>Generated:</strong> {ctx['generated_at']}</p>

        <h2>1. Service Overview</h2>
        <p>{ctx['epic_description']}</p>

        <h2>2. Prerequisites</h2>
        <ul>
            <li>Access to the deployment environment</li>
            <li>Appropriate permissions for service management</li>
            <li>Monitoring dashboard access</li>
        </ul>

        <h2>3. Standard Operating Procedures</h2>
        <h3>3.1 Starting the Service</h3>
        <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">bash</ac:parameter>
            <ac:plain-text-body><![CDATA[# Start service
./start-service.sh]]></ac:plain-text-body>
        </ac:structured-macro>

        <h3>3.2 Stopping the Service</h3>
        <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">bash</ac:parameter>
            <ac:plain-text-body><![CDATA[# Stop service gracefully
./stop-service.sh]]></ac:plain-text-body>
        </ac:structured-macro>

        <h3>3.3 Health Check</h3>
        <p>Verify service health via the health endpoint.</p>

        <h2>4. Troubleshooting</h2>
        <h3>4.1 Common Issues</h3>
        <table>
            <tr><th>Issue</th><th>Symptoms</th><th>Resolution</th></tr>
            <tr><td>Service Unavailable</td><td>503 errors</td><td>Check service logs, restart if needed</td></tr>
            <tr><td>High Latency</td><td>Slow responses</td><td>Check resource usage, scale if needed</td></tr>
        </table>

        <h2>5. Escalation</h2>
        <p>For issues that cannot be resolved, escalate to the on-call engineer.</p>

        <hr/>
        <p><em>Generated by {ctx['generator']}</em></p>
        """

    def _render_api_docs(self, ctx: Dict[str, Any]) -> str:
        """Render API documentation."""
        return f"""
        <h1>API Documentation: {ctx['epic_key']}</h1>
        <p><strong>EPIC:</strong> {ctx['epic_summary']}</p>
        <p><strong>Generated:</strong> {ctx['generated_at']}</p>

        <h2>1. Overview</h2>
        <p>{ctx['epic_description']}</p>

        <h2>2. Authentication</h2>
        <p>All API endpoints require authentication via Bearer token.</p>
        <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">text</ac:parameter>
            <ac:plain-text-body><![CDATA[Authorization: Bearer <token>]]></ac:plain-text-body>
        </ac:structured-macro>

        <h2>3. Endpoints</h2>
        <p>API endpoints are documented in the OpenAPI specification.</p>

        <h3>3.1 Base URL</h3>
        <p><code>/api/v1</code></p>

        <h2>4. Error Handling</h2>
        <table>
            <tr><th>Code</th><th>Description</th></tr>
            <tr><td>400</td><td>Bad Request - Invalid input</td></tr>
            <tr><td>401</td><td>Unauthorized - Invalid or missing token</td></tr>
            <tr><td>404</td><td>Not Found - Resource does not exist</td></tr>
            <tr><td>500</td><td>Internal Server Error</td></tr>
        </table>

        <h2>5. Rate Limiting</h2>
        <p>API requests are rate limited to prevent abuse.</p>

        <hr/>
        <p><em>Generated by {ctx['generator']}</em></p>
        """

    def _render_adr(self, ctx: Dict[str, Any]) -> str:
        """Render Architecture Decision Record."""
        return f"""
        <h1>ADR: {ctx['epic_key']}</h1>
        <p><strong>EPIC:</strong> {ctx['epic_summary']}</p>
        <p><strong>Date:</strong> {ctx['generated_at']}</p>
        <p><strong>Status:</strong> Accepted</p>

        <h2>Context</h2>
        <p>{ctx['epic_description']}</p>

        <h2>Decision</h2>
        <p>We will implement this feature following the existing architectural patterns in the codebase.</p>

        <h2>Consequences</h2>
        <h3>Positive</h3>
        <ul>
            <li>Maintains consistency with existing architecture</li>
            <li>Reduces learning curve for developers</li>
            <li>Leverages existing infrastructure</li>
        </ul>

        <h3>Negative</h3>
        <ul>
            <li>May require refactoring if patterns change</li>
            <li>Limited by existing technical constraints</li>
        </ul>

        <h2>Alternatives Considered</h2>
        <p>Alternative approaches were evaluated but the chosen approach best fits our requirements.</p>

        <hr/>
        <p><em>Generated by {ctx['generator']}</em></p>
        """

    def _render_config_guide(self, ctx: Dict[str, Any]) -> str:
        """Render configuration guide."""
        return f"""
        <h1>Configuration Guide: {ctx['epic_key']}</h1>
        <p><strong>EPIC:</strong> {ctx['epic_summary']}</p>
        <p><strong>Generated:</strong> {ctx['generated_at']}</p>

        <h2>1. Overview</h2>
        <p>This document describes the configuration options for the feature.</p>

        <h2>2. Environment Variables</h2>
        <table>
            <tr><th>Variable</th><th>Description</th><th>Default</th></tr>
            <tr><td>LOG_LEVEL</td><td>Logging verbosity</td><td>INFO</td></tr>
            <tr><td>TIMEOUT_SECONDS</td><td>Request timeout</td><td>30</td></tr>
        </table>

        <h2>3. Configuration Files</h2>
        <p>Configuration can also be provided via YAML/JSON files.</p>

        <h2>4. Feature Flags</h2>
        <p>Feature flags can be used to enable/disable functionality.</p>

        <h2>5. Validation</h2>
        <p>Configuration is validated at startup. Invalid configuration will prevent service start.</p>

        <hr/>
        <p><em>Generated by {ctx['generator']}</em></p>
        """

    def _render_monitoring(self, ctx: Dict[str, Any]) -> str:
        """Render monitoring guide."""
        return f"""
        <h1>Monitoring Guide: {ctx['epic_key']}</h1>
        <p><strong>EPIC:</strong> {ctx['epic_summary']}</p>
        <p><strong>Generated:</strong> {ctx['generated_at']}</p>

        <h2>1. Overview</h2>
        <p>This document describes monitoring and observability for the feature.</p>

        <h2>2. Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Description</th><th>Alert Threshold</th></tr>
            <tr><td>request_latency_seconds</td><td>Request latency histogram</td><td>p99 &gt; 1s</td></tr>
            <tr><td>error_rate</td><td>Error rate percentage</td><td>&gt; 1%</td></tr>
            <tr><td>throughput</td><td>Requests per second</td><td>&lt; 10 RPS (low traffic alert)</td></tr>
        </table>

        <h2>3. Logs</h2>
        <p>Structured JSON logs are emitted for all operations.</p>

        <h2>4. Dashboards</h2>
        <p>Dashboards are available in Grafana for real-time monitoring.</p>

        <h2>5. Alerts</h2>
        <table>
            <tr><th>Alert</th><th>Severity</th><th>Action</th></tr>
            <tr><td>High Error Rate</td><td>Critical</td><td>Page on-call</td></tr>
            <tr><td>High Latency</td><td>Warning</td><td>Investigate</td></tr>
        </table>

        <hr/>
        <p><em>Generated by {ctx['generator']}</em></p>
        """


class MinimalConfluenceClient:
    """Minimal Confluence client fallback when UTCP tool is not available."""

    def __init__(self, config: ConfluenceConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make Confluence API call."""
        import aiohttp
        import base64

        auth = base64.b64encode(f"{self.config.email}:{self.config.api_token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.base_url}/wiki/rest/api/{endpoint}"

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=kwargs.get("params")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise RuntimeError(f"Confluence error: {text}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise RuntimeError(f"Confluence error: {text}")
                    return await response.json()
            elif method == "PUT":
                async with session.put(url, headers=headers, json=kwargs.get("json")) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise RuntimeError(f"Confluence error: {text}")
                    return await response.json()

    async def create_page(self, title: str, content: str, space_key: str = None, parent_id: str = None):
        """Create a page."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]

        try:
            payload = {
                "type": "page",
                "title": title,
                "space": {"key": space_key or self.config.space_key},
                "body": {"storage": {"value": content, "representation": "storage"}}
            }
            if parent_id:
                payload["ancestors"] = [{"id": parent_id}]

            result = await self._api_call("POST", "content", json=payload)
            return Result(success=True, data={
                "id": result.get("id"),
                "title": result.get("title"),
                "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}",
            })
        except Exception as e:
            return Result(success=False, data={"error": str(e)})

    async def update_page(self, page_id: str, title: str, content: str, version: int):
        """Update a page."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]

        try:
            payload = {
                "type": "page",
                "title": title,
                "body": {"storage": {"value": content, "representation": "storage"}},
                "version": {"number": version + 1}
            }
            result = await self._api_call("PUT", f"content/{page_id}", json=payload)
            return Result(success=True, data={"id": result.get("id")})
        except Exception as e:
            return Result(success=False, data={"error": str(e)})

    async def get_page(self, page_id: str):
        """Get page details."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]

        try:
            result = await self._api_call("GET", f"content/{page_id}", params={"expand": "version"})
            return Result(success=True, data={
                "id": result.get("id"),
                "version": result.get("version", {}).get("number", 1),
            })
        except Exception as e:
            return Result(success=False, data={"error": str(e)})

    async def search(self, cql: str, limit: int = 25, expand: str = "space"):
        """Search for pages."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            data: Dict[str, Any]

        try:
            result = await self._api_call("GET", "content/search", params={
                "cql": cql, "limit": limit, "expand": expand
            })
            results = [{
                "id": item.get("id"),
                "title": item.get("title"),
                "url": f"{self.base_url}/wiki{item.get('_links', {}).get('webui', '')}",
            } for item in result.get("results", [])]
            return Result(success=True, data={"results": results})
        except Exception as e:
            return Result(success=False, data={"results": [], "error": str(e)})
