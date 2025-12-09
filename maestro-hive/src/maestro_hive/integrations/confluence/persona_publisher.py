"""
Persona Confluence Publisher

Creates and manages Confluence pages for AI persona execution artifacts
with verbosity-aware content filtering and hierarchical organization.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class VerbosityLevel(Enum):
    """Verbosity levels for content filtering."""
    LEARNING = "learning"
    OPTIMIZED = "optimized"
    PRODUCTION = "production"


class PageType(Enum):
    """Types of Confluence pages."""
    EPIC_SUMMARY = "epic_summary"
    TASK_OVERVIEW = "task_overview"
    PERSONA_DETAIL = "persona_detail"
    ARTIFACT_PAGE = "artifact"
    ERROR_REPORT = "error_report"
    MILESTONE = "milestone"
    SUMMARY = "summary"


@dataclass
class PersonaContent:
    """Content for a persona page."""
    persona_id: str
    persona_name: str
    task_id: str
    execution_summary: str
    decisions_made: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_generated: List[Dict[str, Any]] = field(default_factory=list)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    errors_encountered: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfluencePage:
    """Represents a Confluence page."""
    id: str
    title: str
    space_key: str
    parent_id: Optional[str]
    content: str
    version: int
    created: datetime
    updated: datetime


class ConfluenceContentBuilder:
    """Builder for Confluence Storage Format content."""
    
    def __init__(self):
        self.content = []
    
    def heading(self, text: str, level: int = 2) -> 'ConfluenceContentBuilder':
        """Add a heading."""
        self.content.append(f"<h{level}>{text}</h{level}>")
        return self
    
    def paragraph(self, text: str) -> 'ConfluenceContentBuilder':
        """Add a paragraph."""
        self.content.append(f"<p>{text}</p>")
        return self
    
    def code_block(self, code: str, language: str = "python") -> 'ConfluenceContentBuilder':
        """Add a code block."""
        self.content.append(
            f'<ac:structured-macro ac:name="code">'
            f'<ac:parameter ac:name="language">{language}</ac:parameter>'
            f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
            f'</ac:structured-macro>'
        )
        return self
    
    def bullet_list(self, items: List[str]) -> 'ConfluenceContentBuilder':
        """Add a bullet list."""
        list_items = "".join(f"<li>{item}</li>" for item in items)
        self.content.append(f"<ul>{list_items}</ul>")
        return self
    
    def table(self, headers: List[str], rows: List[List[str]]) -> 'ConfluenceContentBuilder':
        """Add a table."""
        header_html = "".join(f"<th>{h}</th>" for h in headers)
        rows_html = ""
        for row in rows:
            cells = "".join(f"<td>{cell}</td>" for cell in row)
            rows_html += f"<tr>{cells}</tr>"
        
        self.content.append(
            f"<table><thead><tr>{header_html}</tr></thead>"
            f"<tbody>{rows_html}</tbody></table>"
        )
        return self
    
    def status_macro(self, text: str, color: str = "Green") -> 'ConfluenceContentBuilder':
        """Add a status macro."""
        self.content.append(
            f'<ac:structured-macro ac:name="status">'
            f'<ac:parameter ac:name="colour">{color}</ac:parameter>'
            f'<ac:parameter ac:name="title">{text}</ac:parameter>'
            f'</ac:structured-macro>'
        )
        return self
    
    def expand_macro(self, title: str, content: str) -> 'ConfluenceContentBuilder':
        """Add an expand/collapse section."""
        self.content.append(
            f'<ac:structured-macro ac:name="expand">'
            f'<ac:parameter ac:name="title">{title}</ac:parameter>'
            f'<ac:rich-text-body>{content}</ac:rich-text-body>'
            f'</ac:structured-macro>'
        )
        return self
    
    def build(self) -> str:
        """Build the final content."""
        return "".join(self.content)


class PersonaConfluencePublisher:
    """
    Publisher for Confluence pages per AI persona.
    
    Creates hierarchical pages under task parents with verbosity-aware
    content filtering.
    """
    
    # Page types allowed at each verbosity level
    VERBOSITY_PAGE_TYPES: Dict[VerbosityLevel, set] = {
        VerbosityLevel.LEARNING: {
            PageType.EPIC_SUMMARY, PageType.TASK_OVERVIEW,
            PageType.PERSONA_DETAIL, PageType.ARTIFACT_PAGE,
            PageType.ERROR_REPORT, PageType.MILESTONE, PageType.SUMMARY,
        },
        VerbosityLevel.OPTIMIZED: {
            PageType.EPIC_SUMMARY, PageType.TASK_OVERVIEW,
            PageType.SUMMARY, PageType.MILESTONE, PageType.ERROR_REPORT,
        },
        VerbosityLevel.PRODUCTION: {
            PageType.ERROR_REPORT,
        },
    }
    
    def __init__(
        self,
        confluence_url: Optional[str] = None,
        confluence_email: Optional[str] = None,
        confluence_token: Optional[str] = None,
        space_key: str = "MAESTRO",
        verbosity_level: str = "learning",
    ):
        """Initialize the publisher."""
        self.confluence_url = confluence_url or os.getenv("CONFLUENCE_URL")
        self.confluence_email = confluence_email or os.getenv("CONFLUENCE_EMAIL")
        self.confluence_token = confluence_token or os.getenv("CONFLUENCE_API_TOKEN")
        self.space_key = space_key
        self._verbosity_level = VerbosityLevel(verbosity_level)
        
        self._page_cache: Dict[str, ConfluencePage] = {}
        self._task_parent_pages: Dict[str, str] = {}  # task_id -> parent_page_id
        
        logger.info(f"PersonaConfluencePublisher initialized (space: {space_key})")
    
    @property
    def verbosity_level(self) -> VerbosityLevel:
        """Get current verbosity level."""
        return self._verbosity_level
    
    @verbosity_level.setter
    def verbosity_level(self, level: str):
        """Set verbosity level."""
        self._verbosity_level = VerbosityLevel(level)
    
    def should_create_page(self, page_type: PageType) -> bool:
        """Check if page type should be created based on verbosity."""
        allowed_types = self.VERBOSITY_PAGE_TYPES.get(
            self._verbosity_level,
            self.VERBOSITY_PAGE_TYPES[VerbosityLevel.PRODUCTION]
        )
        return page_type in allowed_types
    
    def _build_persona_page_content(
        self,
        content: PersonaContent,
        detail_level: str = "full"
    ) -> str:
        """Build page content based on verbosity level."""
        builder = ConfluenceContentBuilder()
        
        # Header
        builder.heading(f"Persona: {content.persona_name}", 1)
        builder.paragraph(f"Task: {content.task_id}")
        builder.paragraph(f"Generated: {content.timestamp.isoformat()}")
        
        # Status
        if content.errors_encountered:
            builder.status_macro("Completed with Errors", "Yellow")
        else:
            builder.status_macro("Completed", "Green")
        
        # Summary
        builder.heading("Execution Summary", 2)
        builder.paragraph(content.execution_summary)
        
        # Decisions (only in LEARNING mode)
        if detail_level == "full" and content.decisions_made:
            builder.heading("Decisions Made", 2)
            decision_items = [
                f"{d.get('type', 'Decision')}: {d.get('summary', 'N/A')}"
                for d in content.decisions_made[:10]
            ]
            builder.bullet_list(decision_items)
        
        # Artifacts
        if content.artifacts_generated:
            builder.heading("Artifacts Generated", 2)
            artifact_items = [
                f"{a.get('name', 'Artifact')}: {a.get('type', 'unknown')}"
                for a in content.artifacts_generated
            ]
            builder.bullet_list(artifact_items)
        
        # Quality Metrics
        if content.quality_metrics:
            builder.heading("Quality Metrics", 2)
            metrics_rows = [
                [k, str(v)] for k, v in content.quality_metrics.items()
            ]
            builder.table(["Metric", "Value"], metrics_rows)
        
        # Errors (always included if present)
        if content.errors_encountered:
            builder.heading("Errors Encountered", 2)
            for error in content.errors_encountered:
                builder.paragraph(f"**{error.get('type', 'Error')}**: {error.get('message', 'N/A')}")
        
        return builder.build()
    
    async def publish_persona_page(
        self,
        content: PersonaContent,
        parent_page_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Publish a page for a persona's execution.
        
        Args:
            content: The persona content to publish
            parent_page_id: Optional parent page ID
            
        Returns:
            The created page ID, or None if filtered out
        """
        if not self.should_create_page(PageType.PERSONA_DETAIL):
            logger.debug(f"Skipping persona page for {content.persona_id} (verbosity)")
            return None
        
        detail_level = "full" if self._verbosity_level == VerbosityLevel.LEARNING else "summary"
        page_content = self._build_persona_page_content(content, detail_level)
        
        title = f"[{content.task_id}] Persona: {content.persona_name}"
        
        # Simulate page creation (in production, call Confluence API)
        page_id = f"page_{hash(title) % 100000}"
        
        page = ConfluencePage(
            id=page_id,
            title=title,
            space_key=self.space_key,
            parent_id=parent_page_id,
            content=page_content,
            version=1,
            created=datetime.now(),
            updated=datetime.now(),
        )
        
        self._page_cache[page_id] = page
        logger.info(f"Published persona page: {title} ({page_id})")
        
        return page_id
    
    async def publish_task_summary(
        self,
        task_id: str,
        summary: str,
        personas: List[str],
        metrics: Dict[str, Any],
    ) -> Optional[str]:
        """Publish a task summary page."""
        if not self.should_create_page(PageType.SUMMARY):
            return None
        
        builder = ConfluenceContentBuilder()
        builder.heading(f"Task Summary: {task_id}", 1)
        builder.paragraph(summary)
        
        builder.heading("Personas Involved", 2)
        builder.bullet_list(personas)
        
        builder.heading("Metrics", 2)
        metrics_rows = [[k, str(v)] for k, v in metrics.items()]
        builder.table(["Metric", "Value"], metrics_rows)
        
        title = f"[{task_id}] Task Summary"
        page_id = f"summary_{hash(title) % 100000}"
        
        page = ConfluencePage(
            id=page_id,
            title=title,
            space_key=self.space_key,
            parent_id=None,
            content=builder.build(),
            version=1,
            created=datetime.now(),
            updated=datetime.now(),
        )
        
        self._page_cache[page_id] = page
        self._task_parent_pages[task_id] = page_id
        
        return page_id
    
    async def publish_error_report(
        self,
        task_id: str,
        errors: List[Dict[str, Any]],
    ) -> str:
        """Publish an error report page (always created)."""
        builder = ConfluenceContentBuilder()
        builder.heading(f"Error Report: {task_id}", 1)
        builder.status_macro("Errors Detected", "Red")
        
        for i, error in enumerate(errors, 1):
            builder.heading(f"Error {i}: {error.get('type', 'Unknown')}", 3)
            builder.paragraph(error.get("message", "No message"))
            if error.get("stack"):
                builder.code_block(error["stack"], "text")
        
        title = f"[{task_id}] Error Report"
        page_id = f"error_{hash(title) % 100000}"
        
        page = ConfluencePage(
            id=page_id,
            title=title,
            space_key=self.space_key,
            parent_id=self._task_parent_pages.get(task_id),
            content=builder.build(),
            version=1,
            created=datetime.now(),
            updated=datetime.now(),
        )
        
        self._page_cache[page_id] = page
        logger.info(f"Published error report: {title}")
        
        return page_id
    
    async def get_page(self, page_id: str) -> Optional[ConfluencePage]:
        """Get a page by ID."""
        return self._page_cache.get(page_id)
    
    async def list_task_pages(self, task_id: str) -> List[ConfluencePage]:
        """List all pages for a task."""
        return [
            page for page in self._page_cache.values()
            if task_id in page.title
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get publishing statistics."""
        pages = list(self._page_cache.values())
        
        by_type = {}
        for page in pages:
            if "Error Report" in page.title:
                ptype = "error_report"
            elif "Summary" in page.title:
                ptype = "summary"
            elif "Persona:" in page.title:
                ptype = "persona"
            else:
                ptype = "other"
            by_type[ptype] = by_type.get(ptype, 0) + 1
        
        return {
            "total_pages": len(pages),
            "by_type": by_type,
            "verbosity_level": self._verbosity_level.value,
            "space_key": self.space_key,
        }
