"""
Context Formatter for RAG Service.

Formats extracted patterns for injection into persona prompts.

EPIC: MD-2499
AC-4: Format context for persona injection
"""

import logging
from typing import List, Optional

from maestro_hive.rag.models import (
    ContextConfig,
    FailurePattern,
    FormattedContext,
    PatternSummary,
    SuccessPattern,
)

logger = logging.getLogger(__name__)


class ContextFormatter:
    """
    Formats extracted patterns into prompt-ready context.

    Supports multiple output formats and respects token limits.
    """

    # Approximate characters per token for estimation
    CHARS_PER_TOKEN = 4

    def __init__(self):
        """Initialize context formatter."""
        pass

    def format(
        self,
        patterns: PatternSummary,
        config: Optional[ContextConfig] = None,
    ) -> FormattedContext:
        """
        Format patterns for prompt injection.

        Implements AC-4: Format context for persona injection.

        Args:
            patterns: Extracted pattern summary
            config: Optional formatting configuration

        Returns:
            FormattedContext ready for persona injection
        """
        config = config or ContextConfig()

        if config.format_style == "structured":
            text = self._format_structured(patterns, config)
        elif config.format_style == "narrative":
            text = self._format_narrative(patterns, config)
        elif config.format_style == "bullet":
            text = self._format_bullet(patterns, config)
        else:
            text = self._format_structured(patterns, config)

        # Estimate token count
        token_count = len(text) // self.CHARS_PER_TOKEN

        # Truncate if needed
        truncated = False
        if token_count > config.max_tokens:
            max_chars = config.max_tokens * self.CHARS_PER_TOKEN
            text = self._truncate_text(text, max_chars)
            token_count = config.max_tokens
            truncated = True

        patterns_included = len(patterns.success_patterns) + len(patterns.failure_patterns)

        return FormattedContext(
            formatted_text=text,
            token_count=token_count,
            execution_count=patterns.total_executions_analyzed,
            patterns_included=patterns_included,
            truncated=truncated,
        )

    def format_for_persona(
        self,
        patterns: PatternSummary,
        persona_type: str,
    ) -> str:
        """
        Format patterns optimized for specific persona type.

        Args:
            patterns: Extracted pattern summary
            persona_type: Type of persona (architect, developer, tester, reviewer)

        Returns:
            Formatted string optimized for the persona
        """
        if persona_type == "architect":
            return self._format_for_architect(patterns)
        elif persona_type == "developer":
            return self._format_for_developer(patterns)
        elif persona_type == "tester":
            return self._format_for_tester(patterns)
        elif persona_type == "reviewer":
            return self._format_for_reviewer(patterns)
        else:
            return self._format_structured(patterns, ContextConfig())

    def _format_structured(
        self,
        patterns: PatternSummary,
        config: ContextConfig,
    ) -> str:
        """Format patterns in a structured markdown format."""
        sections = []

        # Header
        sections.append("## Historical Execution Context")
        sections.append(f"*Based on {patterns.total_executions_analyzed} similar past executions*")
        sections.append(f"*Confidence: {patterns.confidence_score:.0%}*")
        sections.append("")

        # Failure patterns first if prioritized
        if config.prioritize_failures and patterns.failure_patterns:
            sections.append("### Failure Patterns to Avoid")
            for fp in patterns.failure_patterns:
                sections.append(f"- **{fp.description}** ({fp.failure_type})")
                sections.append(f"  - Frequency: {fp.frequency} occurrences ({fp.confidence:.0%} of failures)")
                if fp.mitigation:
                    sections.append(f"  - Mitigation: {fp.mitigation}")
            sections.append("")

        # Success patterns
        if patterns.success_patterns:
            sections.append("### Success Patterns to Follow")
            for sp in patterns.success_patterns:
                sections.append(f"- **{sp.description}**")
                sections.append(f"  - Frequency: {sp.frequency} occurrences ({sp.confidence:.0%} confidence)")
                if sp.context:
                    for key, value in sp.context.items():
                        if key not in ["phase_name"]:
                            sections.append(f"  - {key}: {value}")
            sections.append("")

        # Remaining failure patterns if not prioritized
        if not config.prioritize_failures and patterns.failure_patterns:
            sections.append("### Failure Patterns to Avoid")
            for fp in patterns.failure_patterns:
                sections.append(f"- **{fp.description}** ({fp.failure_type})")
                if fp.mitigation:
                    sections.append(f"  - Mitigation: {fp.mitigation}")
            sections.append("")

        return "\n".join(sections)

    def _format_narrative(
        self,
        patterns: PatternSummary,
        config: ContextConfig,
    ) -> str:
        """Format patterns as a narrative summary."""
        parts = []

        total = patterns.total_executions_analyzed
        confidence = patterns.confidence_score

        parts.append(
            f"Analysis of {total} similar past executions (confidence: {confidence:.0%}) "
            f"reveals the following insights:"
        )
        parts.append("")

        # Success insights
        if patterns.success_patterns:
            parts.append("Successful executions commonly:")
            for sp in patterns.success_patterns[:5]:
                parts.append(f"  - {sp.description.lower()}")
            parts.append("")

        # Failure insights
        if patterns.failure_patterns:
            parts.append("Watch out for these common failure modes:")
            for fp in patterns.failure_patterns[:5]:
                if fp.mitigation:
                    parts.append(f"  - {fp.description}: {fp.mitigation}")
                else:
                    parts.append(f"  - {fp.description}")
            parts.append("")

        return "\n".join(parts)

    def _format_bullet(
        self,
        patterns: PatternSummary,
        config: ContextConfig,
    ) -> str:
        """Format patterns as simple bullet points."""
        bullets = []

        bullets.append(f"Context from {patterns.total_executions_analyzed} similar executions:")
        bullets.append("")

        # Prioritize failures if configured
        if config.prioritize_failures and patterns.failure_patterns:
            bullets.append("AVOID:")
            for fp in patterns.failure_patterns[:5]:
                bullets.append(f"  - {fp.description}")
            bullets.append("")

        if patterns.success_patterns:
            bullets.append("DO:")
            for sp in patterns.success_patterns[:5]:
                bullets.append(f"  - {sp.description}")
            bullets.append("")

        if not config.prioritize_failures and patterns.failure_patterns:
            bullets.append("AVOID:")
            for fp in patterns.failure_patterns[:5]:
                bullets.append(f"  - {fp.description}")

        return "\n".join(bullets)

    def _format_for_architect(self, patterns: PatternSummary) -> str:
        """Format for architect persona - focus on design patterns."""
        sections = []
        sections.append("### Architecture Insights from Past Executions")
        sections.append("")

        # Focus on structural patterns
        for sp in patterns.success_patterns:
            if any(kw in sp.description.lower() for kw in ["design", "architecture", "structure", "pattern"]):
                sections.append(f"- {sp.description}")

        # Highlight architectural failures
        for fp in patterns.failure_patterns:
            if fp.failure_type in ["build_error", "resource_exhaustion"]:
                sections.append(f"- RISK: {fp.description}")
                if fp.mitigation:
                    sections.append(f"  - Recommendation: {fp.mitigation}")

        return "\n".join(sections) if len(sections) > 2 else "No specific architecture patterns found."

    def _format_for_developer(self, patterns: PatternSummary) -> str:
        """Format for developer persona - focus on implementation details."""
        sections = []
        sections.append("### Implementation Guidance from Past Executions")
        sections.append("")

        # Duration insights
        for sp in patterns.success_patterns:
            if "duration" in sp.pattern_id or "time" in sp.description.lower():
                sections.append(f"- {sp.description}")

        # Common implementation failures
        for fp in patterns.failure_patterns:
            if fp.failure_type in ["build_error", "test_failure"]:
                sections.append(f"- WATCH: {fp.description}")
                if fp.mitigation:
                    sections.append(f"  - Fix: {fp.mitigation}")

        return "\n".join(sections) if len(sections) > 2 else "No specific implementation patterns found."

    def _format_for_tester(self, patterns: PatternSummary) -> str:
        """Format for tester persona - focus on test patterns."""
        sections = []
        sections.append("### Testing Insights from Past Executions")
        sections.append("")

        # Test-related success patterns
        for sp in patterns.success_patterns:
            if any(kw in sp.description.lower() for kw in ["test", "coverage", "validation"]):
                sections.append(f"- {sp.description}")

        # Test failures
        for fp in patterns.failure_patterns:
            if fp.failure_type == "test_failure":
                sections.append(f"- COMMON FAILURE: {fp.description}")
                if fp.examples:
                    sections.append(f"  - Example: {fp.examples[0][:100]}...")

        return "\n".join(sections) if len(sections) > 2 else "No specific testing patterns found."

    def _format_for_reviewer(self, patterns: PatternSummary) -> str:
        """Format for reviewer persona - focus on quality patterns."""
        sections = []
        sections.append("### Quality Review Context from Past Executions")
        sections.append("")

        sections.append(f"*Analyzing {patterns.total_executions_analyzed} similar executions*")
        sections.append("")

        # All failure patterns are relevant for reviewers
        if patterns.failure_patterns:
            sections.append("Key failure patterns to check against:")
            for fp in patterns.failure_patterns:
                sections.append(f"- {fp.description} ({fp.confidence:.0%} occurrence)")

        return "\n".join(sections) if len(sections) > 3 else "No specific quality patterns found."

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncate text to max characters while preserving structure."""
        if len(text) <= max_chars:
            return text

        # Try to truncate at a section boundary
        truncated = text[:max_chars]

        # Find last complete section
        last_section = truncated.rfind("\n###")
        if last_section > max_chars * 0.5:
            truncated = truncated[:last_section]

        # Or at least at a paragraph
        last_para = truncated.rfind("\n\n")
        if last_para > max_chars * 0.7:
            truncated = truncated[:last_para]

        return truncated + "\n\n*[Context truncated due to length]*"


def format_rag_context(
    patterns: PatternSummary,
    max_tokens: int = 2000,
    style: str = "structured",
) -> FormattedContext:
    """
    Convenience function to format RAG context.

    Args:
        patterns: Pattern summary to format
        max_tokens: Maximum token count
        style: Format style (structured, narrative, bullet)

    Returns:
        FormattedContext
    """
    formatter = ContextFormatter()
    config = ContextConfig(max_tokens=max_tokens, format_style=style)
    return formatter.format(patterns, config)
