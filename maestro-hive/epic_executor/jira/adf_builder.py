"""
Atlassian Document Format (ADF) Builder.

Provides a fluent interface for constructing JIRA-compatible ADF documents.
Used for rich text formatting in EPIC descriptions and comments.

ADF Spec: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ADFDocument:
    """Represents an ADF document ready for JIRA API."""
    content: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JIRA-compatible ADF format."""
        return {
            "type": "doc",
            "version": 1,
            "content": self.content
        }

    def is_empty(self) -> bool:
        """Check if document has no content."""
        return len(self.content) == 0


class ADFBuilder:
    """
    Fluent builder for Atlassian Document Format (ADF) documents.

    Usage:
        doc = (ADFBuilder()
            .heading("Summary", level=2)
            .paragraph("This is the summary.")
            .bullet_list(["Item 1", "Item 2", "Item 3"])
            .table([
                ["Header 1", "Header 2"],
                ["Value 1", "Value 2"],
            ], has_header=True)
            .build())
    """

    def __init__(self):
        self._content: List[Dict[str, Any]] = []

    def paragraph(self, text: str, bold: bool = False, italic: bool = False,
                  code: bool = False, color: Optional[str] = None) -> "ADFBuilder":
        """Add a paragraph with optional formatting."""
        marks = []
        if bold:
            marks.append({"type": "strong"})
        if italic:
            marks.append({"type": "em"})
        if code:
            marks.append({"type": "code"})
        if color:
            marks.append({"type": "textColor", "attrs": {"color": color}})

        text_node: Dict[str, Any] = {"type": "text", "text": text}
        if marks:
            text_node["marks"] = marks

        self._content.append({
            "type": "paragraph",
            "content": [text_node]
        })
        return self

    def rich_paragraph(self, *parts: Dict[str, Any]) -> "ADFBuilder":
        """
        Add a paragraph with mixed formatting.

        Args:
            parts: Text node dictionaries from text_node() method
        """
        self._content.append({
            "type": "paragraph",
            "content": list(parts)
        })
        return self

    @staticmethod
    def text_node(text: str, bold: bool = False, italic: bool = False,
                  code: bool = False, color: Optional[str] = None) -> Dict[str, Any]:
        """Create a text node for use in rich_paragraph."""
        marks = []
        if bold:
            marks.append({"type": "strong"})
        if italic:
            marks.append({"type": "em"})
        if code:
            marks.append({"type": "code"})
        if color:
            marks.append({"type": "textColor", "attrs": {"color": color}})

        node: Dict[str, Any] = {"type": "text", "text": text}
        if marks:
            node["marks"] = marks
        return node

    def heading(self, text: str, level: int = 2, bold: bool = False) -> "ADFBuilder":
        """Add a heading (level 1-6)."""
        text_node: Dict[str, Any] = {"type": "text", "text": text}
        if bold:
            text_node["marks"] = [{"type": "strong"}]

        self._content.append({
            "type": "heading",
            "attrs": {"level": min(max(level, 1), 6)},
            "content": [text_node]
        })
        return self

    def bullet_list(self, items: List[Union[str, Dict[str, Any]]]) -> "ADFBuilder":
        """
        Add a bullet list.

        Args:
            items: List of strings or pre-built content dictionaries
        """
        list_items = []
        for item in items:
            if isinstance(item, str):
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": item}]
                    }]
                })
            else:
                list_items.append({
                    "type": "listItem",
                    "content": [item]
                })

        self._content.append({
            "type": "bulletList",
            "content": list_items
        })
        return self

    def ordered_list(self, items: List[Union[str, Dict[str, Any]]]) -> "ADFBuilder":
        """Add a numbered list."""
        list_items = []
        for item in items:
            if isinstance(item, str):
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": item}]
                    }]
                })
            else:
                list_items.append({
                    "type": "listItem",
                    "content": [item]
                })

        self._content.append({
            "type": "orderedList",
            "content": list_items
        })
        return self

    def table(self, rows: List[List[str]], has_header: bool = True) -> "ADFBuilder":
        """
        Add a table.

        Args:
            rows: 2D list of cell values (first row is header if has_header=True)
            has_header: Whether first row should be formatted as header
        """
        if not rows:
            return self

        table_rows = []
        for i, row in enumerate(rows):
            cells = []
            cell_type = "tableHeader" if (has_header and i == 0) else "tableCell"

            for cell_value in row:
                text_node: Dict[str, Any] = {"type": "text", "text": str(cell_value)}
                if has_header and i == 0:
                    text_node["marks"] = [{"type": "strong"}]

                cells.append({
                    "type": cell_type,
                    "content": [{
                        "type": "paragraph",
                        "content": [text_node]
                    }]
                })

            table_rows.append({
                "type": "tableRow",
                "content": cells
            })

        self._content.append({
            "type": "table",
            "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
            "content": table_rows
        })
        return self

    def rule(self) -> "ADFBuilder":
        """Add a horizontal rule (divider)."""
        self._content.append({"type": "rule"})
        return self

    def code_block(self, code: str, language: str = "python") -> "ADFBuilder":
        """Add a code block with syntax highlighting."""
        self._content.append({
            "type": "codeBlock",
            "attrs": {"language": language},
            "content": [{"type": "text", "text": code}]
        })
        return self

    def blockquote(self, text: str) -> "ADFBuilder":
        """Add a blockquote."""
        self._content.append({
            "type": "blockquote",
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": text}]
            }]
        })
        return self

    def panel(self, text: str, panel_type: str = "info") -> "ADFBuilder":
        """
        Add a panel (info box).

        Args:
            text: Panel content
            panel_type: One of 'info', 'note', 'warning', 'error', 'success'
        """
        self._content.append({
            "type": "panel",
            "attrs": {"panelType": panel_type},
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": text}]
            }]
        })
        return self

    def status_badge(self, text: str, color: str = "blue") -> "ADFBuilder":
        """
        Add a status badge/lozenge.

        Args:
            text: Badge text
            color: One of 'neutral', 'purple', 'blue', 'red', 'yellow', 'green'
        """
        self._content.append({
            "type": "paragraph",
            "content": [{
                "type": "status",
                "attrs": {
                    "text": text,
                    "color": color
                }
            }]
        })
        return self

    def mention(self, account_id: str, text: str) -> "ADFBuilder":
        """Add a user mention."""
        self._content.append({
            "type": "paragraph",
            "content": [{
                "type": "mention",
                "attrs": {
                    "id": account_id,
                    "text": text,
                    "userType": "DEFAULT"
                }
            }]
        })
        return self

    def link(self, text: str, url: str) -> "ADFBuilder":
        """Add a text link in a paragraph."""
        self._content.append({
            "type": "paragraph",
            "content": [{
                "type": "text",
                "text": text,
                "marks": [{
                    "type": "link",
                    "attrs": {"href": url}
                }]
            }]
        })
        return self

    def raw(self, content: Dict[str, Any]) -> "ADFBuilder":
        """Add raw ADF content directly."""
        self._content.append(content)
        return self

    def extend(self, other: "ADFBuilder") -> "ADFBuilder":
        """Extend with content from another builder."""
        self._content.extend(other._content)
        return self

    def build(self) -> ADFDocument:
        """Build the final ADF document."""
        return ADFDocument(content=self._content.copy())

    def to_dict(self) -> Dict[str, Any]:
        """Shorthand for build().to_dict()."""
        return self.build().to_dict()


class ComplianceReportBuilder:
    """
    Specialized builder for EPIC compliance reports.

    Generates standardized compliance audit reports in ADF format.
    """

    def __init__(self):
        self.builder = ADFBuilder()

    def build_report(
        self,
        score: float,
        passing: bool,
        audit_date: str,
        breakdown: Dict[str, Dict[str, Any]],
        gaps: List[str],
        child_tasks: List[str],
        implementation_files: List[str],
        auditor: str = "Claude AI (EPIC Executor v1.0)"
    ) -> ADFDocument:
        """
        Build a complete compliance audit report.

        Args:
            score: Total compliance score (0-100)
            passing: Whether score meets 95% threshold
            audit_date: Date of audit (ISO format)
            breakdown: Score breakdown by category
            gaps: List of identified gaps
            child_tasks: List of created child task keys
            implementation_files: List of implementation file paths
            auditor: Name of auditing system

        Returns:
            ADFDocument ready for JIRA
        """
        status = "PASS" if passing else "FAIL"
        status_color = "#36B37E" if passing else "#DE350B"

        # Header
        self.builder.heading("Compliance Audit Report", level=2)
        self.builder.rich_paragraph(
            ADFBuilder.text_node(f"Audit Date: {audit_date} | Score: ", bold=True),
            ADFBuilder.text_node(f"{score:.0f}/100 ({score:.0f}%)", bold=True),
            ADFBuilder.text_node(f" | Status: ", bold=True),
            ADFBuilder.text_node(status, bold=True, color=status_color)
        )

        # Score breakdown table
        self.builder.heading("Score Breakdown", level=3)
        table_rows = [["Category", "Score", "Status"]]
        for category, data in breakdown.items():
            table_rows.append([
                category.replace("_", " ").title(),
                f"{data['score']:.0f}/{data['max']}",
                data.get('status', 'OK')
            ])
        table_rows.append(["TOTAL", f"{score:.0f}/100", status])
        self.builder.table(table_rows, has_header=True)

        # Gaps identified
        if gaps:
            self.builder.heading("Gaps Identified", level=3)
            self.builder.bullet_list(gaps)

        # Implementation files
        if implementation_files:
            self.builder.heading("Implementation Files", level=3)
            self.builder.bullet_list(implementation_files[:10])  # Limit to 10
            if len(implementation_files) > 10:
                self.builder.paragraph(
                    f"... and {len(implementation_files) - 10} more files",
                    italic=True
                )

        # Child tasks
        if child_tasks:
            self.builder.heading("Child Tasks", level=3)
            self.builder.bullet_list(child_tasks)

        # Footer
        self.builder.rule()
        self.builder.paragraph(f"Auditor: {auditor}", italic=True)

        return self.builder.build()

    def build_execution_summary(
        self,
        epic_key: str,
        success: bool,
        duration_seconds: float,
        phases_completed: int,
        total_phases: int,
        documents_created: int,
        tests_generated: int,
        compliance_score: float,
        confluence_links: List[str],
    ) -> ADFDocument:
        """
        Build an execution summary for posting as EPIC comment.

        Args:
            epic_key: EPIC key
            success: Whether execution succeeded
            duration_seconds: Total execution time
            phases_completed: Number of phases completed
            total_phases: Total number of phases
            documents_created: Number of Confluence docs created
            tests_generated: Number of test files generated
            compliance_score: Final compliance score
            confluence_links: Links to created Confluence pages

        Returns:
            ADFDocument for JIRA comment
        """
        status = "SUCCESS" if success else "FAILED"
        status_color = "#36B37E" if success else "#DE350B"

        self.builder.heading("EPIC Execution Summary", level=2)
        self.builder.rich_paragraph(
            ADFBuilder.text_node(f"Status: ", bold=True),
            ADFBuilder.text_node(status, bold=True, color=status_color)
        )

        # Metrics table
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)

        self.builder.table([
            ["Metric", "Value"],
            ["Duration", f"{minutes}m {seconds}s"],
            ["Phases", f"{phases_completed}/{total_phases}"],
            ["Documents Created", str(documents_created)],
            ["Tests Generated", str(tests_generated)],
            ["Compliance Score", f"{compliance_score:.0f}%"],
        ], has_header=True)

        # Confluence links
        if confluence_links:
            self.builder.heading("Documentation", level=3)
            self.builder.bullet_list(confluence_links)

        self.builder.rule()
        self.builder.paragraph(
            "Generated by EPIC Executor v1.0",
            italic=True
        )

        return self.builder.build()
