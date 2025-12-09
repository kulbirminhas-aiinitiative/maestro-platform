"""
Requirement Handler
===================

Handles processing of free-form requirement text.

Implements: AC-2 (Support EPIC ID or free-form requirement)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib
import re

try:
    from .session_manager import Session
except ImportError:
    from session_manager import Session


@dataclass
class ParsedRequirement:
    """Parsed requirement details."""
    original_text: str
    title: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    complexity: str = "medium"  # low, medium, high
    estimated_tasks: int = 1


@dataclass
class RequirementResult:
    """Result of requirement processing."""
    requirement_id: str
    status: str
    score: Optional[float] = None
    artifacts: dict = field(default_factory=dict)
    error: Optional[str] = None


class RequirementHandler:
    """
    Handler for free-form requirement processing.

    Parses ad-hoc requirements and executes them through the SDLC pipeline
    without requiring a JIRA ticket. This enables quick prototyping and
    experimentation.
    """

    def __init__(self):
        """Initialize the requirement handler."""
        self._complexity_keywords = {
            "high": ["complex", "multiple", "integrate", "system", "architecture"],
            "low": ["simple", "basic", "small", "quick", "minor"],
        }

    def process(self, requirement_text: str, session: Session) -> RequirementResult:
        """
        Process a free-form requirement.

        Args:
            requirement_text: The requirement text
            session: The current session

        Returns:
            RequirementResult with processing status
        """
        # Generate requirement ID
        req_id = self._generate_requirement_id(requirement_text)

        session.input_data = requirement_text
        session.command_type_str = "requirement"

        try:
            # Step 1: Parse requirement
            session.current_step = 1
            parsed = self._parse_requirement(requirement_text)

            # Step 2: Generate acceptance criteria if not present
            session.current_step = 2
            if not parsed.acceptance_criteria:
                parsed.acceptance_criteria = self._generate_acceptance_criteria(parsed)

            # Step 3: Execute SDLC
            session.current_step = 3
            artifacts = self._execute_sdlc(parsed, session)

            # Step 4: Calculate score
            session.current_step = 4
            score = self._calculate_score(artifacts)

            return RequirementResult(
                requirement_id=req_id,
                status="completed",
                score=score,
                artifacts=artifacts,
            )

        except Exception as e:
            return RequirementResult(
                requirement_id=req_id,
                status="failed",
                error=str(e),
            )

    def resume(self, session: Session) -> RequirementResult:
        """
        Resume requirement processing from checkpoint.

        Args:
            session: The session to resume

        Returns:
            RequirementResult with resumed processing status
        """
        requirement_text = session.input_data
        req_id = self._generate_requirement_id(requirement_text)

        try:
            checkpoint = session.checkpoint_data or {}

            # Load parsed requirement from checkpoint
            parsed_data = checkpoint.get("parsed_requirement")
            if parsed_data:
                parsed = ParsedRequirement(**parsed_data)
            else:
                parsed = self._parse_requirement(requirement_text)

            # Continue from checkpoint
            artifacts = checkpoint.get("artifacts", {})
            artifacts = self._continue_sdlc(parsed, artifacts, session)

            score = self._calculate_score(artifacts)

            return RequirementResult(
                requirement_id=req_id,
                status="completed",
                score=score,
                artifacts=artifacts,
            )

        except Exception as e:
            return RequirementResult(
                requirement_id=req_id,
                status="failed",
                error=str(e),
            )

    def _generate_requirement_id(self, text: str) -> str:
        """
        Generate a unique requirement ID from text.

        Args:
            text: The requirement text

        Returns:
            Unique requirement ID
        """
        # Create hash-based ID
        hash_str = hashlib.sha256(text.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"REQ-{timestamp}-{hash_str.upper()}"

    def _parse_requirement(self, text: str) -> ParsedRequirement:
        """
        Parse free-form requirement text.

        Args:
            text: The raw requirement text

        Returns:
            ParsedRequirement with extracted details
        """
        # Clean up text
        cleaned = text.strip()

        # Extract title (first sentence or line)
        title = self._extract_title(cleaned)

        # Full description
        description = cleaned

        # Detect complexity
        complexity = self._detect_complexity(cleaned)

        # Estimate number of tasks
        estimated_tasks = self._estimate_tasks(complexity)

        # Try to extract any inline acceptance criteria
        acceptance_criteria = self._extract_inline_criteria(cleaned)

        return ParsedRequirement(
            original_text=text,
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            complexity=complexity,
            estimated_tasks=estimated_tasks,
        )

    def _extract_title(self, text: str) -> str:
        """Extract title from requirement text."""
        # First line or first sentence
        lines = text.split('\n')
        first_line = lines[0].strip()

        # Limit to reasonable length
        if len(first_line) > 100:
            # Find first sentence
            sentences = re.split(r'[.!?]', first_line)
            if sentences:
                return sentences[0].strip()[:100]

        return first_line[:100]

    def _detect_complexity(self, text: str) -> str:
        """Detect requirement complexity from text."""
        text_lower = text.lower()

        # Check for high complexity keywords
        high_count = sum(
            1 for kw in self._complexity_keywords["high"]
            if kw in text_lower
        )

        # Check for low complexity keywords
        low_count = sum(
            1 for kw in self._complexity_keywords["low"]
            if kw in text_lower
        )

        if high_count > low_count:
            return "high"
        elif low_count > high_count:
            return "low"
        return "medium"

    def _estimate_tasks(self, complexity: str) -> int:
        """Estimate number of tasks based on complexity."""
        estimates = {
            "low": 2,
            "medium": 5,
            "high": 10,
        }
        return estimates.get(complexity, 5)

    def _extract_inline_criteria(self, text: str) -> list[str]:
        """Extract any inline acceptance criteria from text."""
        criteria = []

        # Look for numbered or bulleted criteria
        patterns = [
            r'(?:AC|Acceptance Criterion)\s*\d*[:\-]\s*(.+)',
            r'(?:Criteria|Requirements?)[:\-]\s*\n((?:\s*[-*]\s*.+\n?)+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, str):
                    # Split on bullets if needed
                    for item in re.split(r'\n\s*[-*]\s*', match):
                        item = item.strip()
                        if item:
                            criteria.append(item)

        return criteria

    def _generate_acceptance_criteria(self, parsed: ParsedRequirement) -> list[str]:
        """
        Generate acceptance criteria for a requirement.

        Args:
            parsed: The parsed requirement

        Returns:
            List of generated acceptance criteria
        """
        criteria = []

        # Basic functional criterion
        criteria.append(f"The system shall {parsed.title.lower()}")

        # Add validation criterion
        criteria.append("Input validation shall be implemented")

        # Add error handling criterion
        criteria.append("Appropriate error handling shall be in place")

        # Add testing criterion based on complexity
        if parsed.complexity == "high":
            criteria.append("Unit and integration tests shall achieve 80% coverage")
        else:
            criteria.append("Unit tests shall be provided")

        return criteria

    def _execute_sdlc(self, parsed: ParsedRequirement, session: Session) -> dict:
        """
        Execute SDLC pipeline for requirement.

        Args:
            parsed: The parsed requirement
            session: Current session

        Returns:
            Dictionary of artifacts
        """
        artifacts = {
            "parsed_requirement": {
                "original_text": parsed.original_text,
                "title": parsed.title,
                "description": parsed.description,
                "acceptance_criteria": parsed.acceptance_criteria,
                "complexity": parsed.complexity,
                "estimated_tasks": parsed.estimated_tasks,
            },
            "documentation": [],
            "implementation": [],
            "tests": [],
        }

        # Generate documentation
        session.current_step = 5
        artifacts["documentation"] = self._generate_documentation(parsed)

        # Generate implementation
        session.current_step = 6
        artifacts["implementation"] = self._generate_implementation(parsed)

        # Generate tests
        session.current_step = 7
        artifacts["tests"] = self._generate_tests(parsed)

        # Validate
        session.current_step = 8
        artifacts["validation"] = self._validate_artifacts(artifacts)

        return artifacts

    def _continue_sdlc(
        self,
        parsed: ParsedRequirement,
        artifacts: dict,
        session: Session
    ) -> dict:
        """Continue SDLC from checkpoint."""
        if "validation" not in artifacts:
            artifacts["validation"] = self._validate_artifacts(artifacts)
        return artifacts

    def _generate_documentation(self, parsed: ParsedRequirement) -> list[str]:
        """Generate documentation for requirement."""
        return [
            f"spec_{parsed.title[:20].replace(' ', '_')}.md",
            f"design_{parsed.title[:20].replace(' ', '_')}.md",
        ]

    def _generate_implementation(self, parsed: ParsedRequirement) -> list[str]:
        """Generate implementation for requirement."""
        return [
            f"impl_{parsed.title[:20].replace(' ', '_')}.py",
        ]

    def _generate_tests(self, parsed: ParsedRequirement) -> list[str]:
        """Generate tests for requirement."""
        return [
            f"test_{parsed.title[:20].replace(' ', '_')}.py",
        ]

    def _validate_artifacts(self, artifacts: dict) -> dict:
        """Validate generated artifacts."""
        return {
            "documentation_valid": len(artifacts.get("documentation", [])) > 0,
            "implementation_valid": len(artifacts.get("implementation", [])) > 0,
            "tests_valid": len(artifacts.get("tests", [])) > 0,
            "all_valid": True,
        }

    def _calculate_score(self, artifacts: dict) -> float:
        """Calculate compliance score for requirement."""
        score = 0.0

        if artifacts.get("documentation"):
            score += 15.0
        if artifacts.get("implementation"):
            score += 25.0
        if artifacts.get("tests"):
            score += 20.0
        if artifacts.get("validation", {}).get("all_valid"):
            score += 10.0
        if artifacts.get("parsed_requirement"):
            score += 25.0
        score += 5.0

        return min(score, 100.0)
