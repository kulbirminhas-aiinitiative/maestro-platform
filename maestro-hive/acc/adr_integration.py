"""
ACC ADR Integration (MD-2086)

Integrates Architecture Decision Records (ADRs) with suppressions.
All suppressions must reference a valid ADR document.

Features:
- ADRReference: Metadata about linked ADR
- ADRValidator: Validates ADR existence and status
- ADR-linked suppression expiry
- Support for standard ADR markdown format
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ADRStatus(str, Enum):
    """Status of an ADR document."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


@dataclass
class ADRReference:
    """
    Reference to an Architecture Decision Record.

    ADRs are stored in docs/adr/ with format:
    - 0001-record-architecture-decisions.md
    - 0023-allow-legacy-coupling.md
    """
    adr_id: str  # e.g., "ADR-0023" or "0023"
    adr_path: str  # Full path to ADR file
    adr_title: str  # Title from ADR
    adr_status: ADRStatus  # Current status
    adr_date: Optional[datetime] = None  # Decision date
    review_date: Optional[datetime] = None  # Next review date
    superseded_by: Optional[str] = None  # If superseded
    context: str = ""  # ADR context section
    decision: str = ""  # ADR decision section
    consequences: str = ""  # ADR consequences section

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'adr_id': self.adr_id,
            'adr_path': self.adr_path,
            'adr_title': self.adr_title,
            'adr_status': self.adr_status.value,
            'adr_date': self.adr_date.isoformat() if self.adr_date else None,
            'review_date': self.review_date.isoformat() if self.review_date else None,
            'superseded_by': self.superseded_by,
            'context': self.context[:200] if self.context else "",
            'decision': self.decision[:200] if self.decision else "",
            'consequences': self.consequences[:200] if self.consequences else ""
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ADRReference':
        """Create from dictionary."""
        return cls(
            adr_id=data['adr_id'],
            adr_path=data['adr_path'],
            adr_title=data['adr_title'],
            adr_status=ADRStatus(data.get('adr_status', 'unknown')),
            adr_date=datetime.fromisoformat(data['adr_date']) if data.get('adr_date') else None,
            review_date=datetime.fromisoformat(data['review_date']) if data.get('review_date') else None,
            superseded_by=data.get('superseded_by'),
            context=data.get('context', ''),
            decision=data.get('decision', ''),
            consequences=data.get('consequences', '')
        )


@dataclass
class ADRValidationResult:
    """Result of ADR validation."""
    valid: bool
    adr_reference: Optional[ADRReference] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'valid': self.valid,
            'adr_reference': self.adr_reference.to_dict() if self.adr_reference else None,
            'error_message': self.error_message,
            'warnings': self.warnings
        }


class ADRValidator:
    """
    Validates ADR references for suppressions.

    Supports standard ADR markdown format:
    - Title: # N. Title of ADR
    - Status: Status: accepted/deprecated/superseded
    - Date: Date: YYYY-MM-DD
    - Sections: ## Context, ## Decision, ## Consequences
    """

    # Standard ADR file patterns
    ADR_FILE_PATTERNS = [
        r"^\d{4}-.+\.md$",  # 0001-record-decisions.md
        r"^ADR-\d+\.md$",  # ADR-001.md
        r"^adr-\d+\.md$",  # adr-001.md
    ]

    # ADR content patterns
    TITLE_PATTERN = r"^#\s*(\d+)\.\s*(.+)$"
    STATUS_PATTERN = r"^Status:\s*(\w+)"
    DATE_PATTERN = r"^Date:\s*(\d{4}-\d{2}-\d{2})"
    SUPERSEDED_PATTERN = r"Superseded by:?\s*\[?([^\]]+)\]?"
    REVIEW_PATTERN = r"Review Date:\s*(\d{4}-\d{2}-\d{2})"

    def __init__(
        self,
        adr_directory: str = "docs/adr",
        allow_proposed: bool = False,
        require_accepted: bool = True
    ):
        """
        Initialize ADR validator.

        Args:
            adr_directory: Directory containing ADR files
            allow_proposed: Whether to accept proposed (not yet accepted) ADRs
            require_accepted: Whether to require ADR to be in accepted status
        """
        self.adr_directory = Path(adr_directory)
        self.allow_proposed = allow_proposed
        self.require_accepted = require_accepted
        self._adr_cache: Dict[str, ADRReference] = {}

        # Index existing ADRs
        self._index_adrs()

    def _index_adrs(self):
        """Index all ADRs in the directory."""
        if not self.adr_directory.exists():
            logger.warning(f"ADR directory does not exist: {self.adr_directory}")
            return

        for adr_file in self.adr_directory.glob("*.md"):
            adr_ref = self._parse_adr_file(adr_file)
            if adr_ref:
                self._adr_cache[adr_ref.adr_id] = adr_ref
                # Also index by numeric ID without prefix
                numeric_id = re.sub(r'\D', '', adr_ref.adr_id)
                if numeric_id:
                    self._adr_cache[numeric_id] = adr_ref
                    self._adr_cache[f"ADR-{numeric_id}"] = adr_ref

        logger.info(f"Indexed {len(self._adr_cache)} ADRs from {self.adr_directory}")

    def _parse_adr_file(self, file_path: Path) -> Optional[ADRReference]:
        """Parse an ADR markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            # Extract metadata
            adr_id = None
            title = ""
            status = ADRStatus.UNKNOWN
            adr_date = None
            review_date = None
            superseded_by = None
            context = ""
            decision = ""
            consequences = ""

            current_section = None

            for line in lines:
                # Check for title
                title_match = re.match(self.TITLE_PATTERN, line.strip(), re.MULTILINE)
                if title_match:
                    adr_id = title_match.group(1)
                    title = title_match.group(2).strip()
                    continue

                # Check for status
                status_match = re.match(self.STATUS_PATTERN, line.strip(), re.IGNORECASE)
                if status_match:
                    status_str = status_match.group(1).lower()
                    try:
                        status = ADRStatus(status_str)
                    except ValueError:
                        status = ADRStatus.UNKNOWN
                    continue

                # Check for date
                date_match = re.match(self.DATE_PATTERN, line.strip())
                if date_match:
                    try:
                        adr_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                    except ValueError:
                        pass
                    continue

                # Check for review date
                review_match = re.search(self.REVIEW_PATTERN, line, re.IGNORECASE)
                if review_match:
                    try:
                        review_date = datetime.strptime(review_match.group(1), "%Y-%m-%d")
                    except ValueError:
                        pass
                    continue

                # Check for superseded by
                superseded_match = re.search(self.SUPERSEDED_PATTERN, line, re.IGNORECASE)
                if superseded_match:
                    superseded_by = superseded_match.group(1).strip()
                    continue

                # Track sections
                if line.startswith('## Context'):
                    current_section = 'context'
                elif line.startswith('## Decision'):
                    current_section = 'decision'
                elif line.startswith('## Consequences'):
                    current_section = 'consequences'
                elif line.startswith('## '):
                    current_section = None
                elif current_section:
                    if current_section == 'context':
                        context += line + '\n'
                    elif current_section == 'decision':
                        decision += line + '\n'
                    elif current_section == 'consequences':
                        consequences += line + '\n'

            # Generate ID from filename if not found in content
            if not adr_id:
                match = re.match(r'^(\d+)', file_path.stem)
                if match:
                    adr_id = match.group(1)
                else:
                    adr_id = file_path.stem

            if not title:
                title = file_path.stem.replace('-', ' ').title()

            return ADRReference(
                adr_id=adr_id,
                adr_path=str(file_path),
                adr_title=title,
                adr_status=status,
                adr_date=adr_date,
                review_date=review_date,
                superseded_by=superseded_by,
                context=context.strip(),
                decision=decision.strip(),
                consequences=consequences.strip()
            )

        except Exception as e:
            logger.warning(f"Failed to parse ADR {file_path}: {e}")
            return None

    def validate_adr(self, adr_id: str) -> ADRValidationResult:
        """
        Validate an ADR reference.

        Args:
            adr_id: ADR identifier (e.g., "0023", "ADR-0023", "23")

        Returns:
            ADRValidationResult with validation outcome
        """
        warnings = []

        # Normalize ID
        normalized_id = adr_id.strip().upper()
        if not normalized_id.startswith('ADR-'):
            # Try numeric lookup
            numeric_id = re.sub(r'\D', '', adr_id)
            if numeric_id:
                normalized_id = numeric_id

        # Look up ADR
        adr_ref = self._adr_cache.get(normalized_id)
        if not adr_ref:
            # Try alternative formats
            for cached_id, ref in self._adr_cache.items():
                if cached_id.endswith(normalized_id) or normalized_id.endswith(cached_id):
                    adr_ref = ref
                    break

        if not adr_ref:
            return ADRValidationResult(
                valid=False,
                error_message=f"ADR '{adr_id}' not found in {self.adr_directory}"
            )

        # Check status
        if self.require_accepted:
            if adr_ref.adr_status == ADRStatus.DEPRECATED:
                return ADRValidationResult(
                    valid=False,
                    adr_reference=adr_ref,
                    error_message=f"ADR '{adr_id}' is deprecated"
                )

            if adr_ref.adr_status == ADRStatus.SUPERSEDED:
                return ADRValidationResult(
                    valid=False,
                    adr_reference=adr_ref,
                    error_message=f"ADR '{adr_id}' is superseded by {adr_ref.superseded_by}"
                )

            if adr_ref.adr_status == ADRStatus.PROPOSED and not self.allow_proposed:
                return ADRValidationResult(
                    valid=False,
                    adr_reference=adr_ref,
                    error_message=f"ADR '{adr_id}' is still in proposed status"
                )

        # Check for upcoming review
        if adr_ref.review_date:
            days_until_review = (adr_ref.review_date - datetime.now()).days
            if days_until_review < 0:
                warnings.append(f"ADR '{adr_id}' is past review date ({adr_ref.review_date.date()})")
            elif days_until_review < 30:
                warnings.append(f"ADR '{adr_id}' review due in {days_until_review} days")

        return ADRValidationResult(
            valid=True,
            adr_reference=adr_ref,
            warnings=warnings
        )

    def get_adr(self, adr_id: str) -> Optional[ADRReference]:
        """Get ADR reference by ID."""
        result = self.validate_adr(adr_id)
        return result.adr_reference

    def list_adrs(self, status: Optional[ADRStatus] = None) -> List[ADRReference]:
        """
        List all ADRs, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of ADRReference objects
        """
        # Deduplicate (same ADR may be indexed multiple times)
        unique_adrs = {}
        for adr_ref in self._adr_cache.values():
            if status is None or adr_ref.adr_status == status:
                unique_adrs[adr_ref.adr_path] = adr_ref

        return list(unique_adrs.values())

    def create_adr_template(
        self,
        adr_number: int,
        title: str,
        context: str = "",
        decision: str = "",
        consequences: str = ""
    ) -> str:
        """
        Create ADR markdown template.

        Args:
            adr_number: ADR number
            title: ADR title
            context: Context section
            decision: Decision section
            consequences: Consequences section

        Returns:
            Markdown template string
        """
        date_str = datetime.now().strftime("%Y-%m-%d")

        template = f"""# {adr_number}. {title}

Date: {date_str}

Status: proposed

## Context

{context or "Describe the context and problem statement here."}

## Decision

{decision or "Describe the decision and rationale here."}

## Consequences

{consequences or "Describe the consequences of this decision here."}

### Positive Consequences

- List positive consequences

### Negative Consequences

- List negative consequences

## References

- Link to related documents
"""
        return template

    def refresh(self):
        """Refresh ADR cache by re-indexing."""
        self._adr_cache.clear()
        self._index_adrs()


def validate_suppression_adr(
    adr_id: str,
    adr_directory: str = "docs/adr"
) -> Tuple[bool, Optional[str], Optional[ADRReference]]:
    """
    Convenience function to validate ADR for a suppression.

    Args:
        adr_id: ADR identifier
        adr_directory: ADR directory path

    Returns:
        Tuple of (is_valid, error_message, adr_reference)
    """
    validator = ADRValidator(adr_directory=adr_directory)
    result = validator.validate_adr(adr_id)

    return (
        result.valid,
        result.error_message,
        result.adr_reference
    )


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    adr_dir = sys.argv[1] if len(sys.argv) > 1 else "docs/adr"

    print(f"ADR Integration Test")
    print(f"ADR Directory: {adr_dir}")
    print("=" * 60)

    # Initialize validator
    validator = ADRValidator(adr_directory=adr_dir)

    # List ADRs
    adrs = validator.list_adrs()
    print(f"\nFound {len(adrs)} ADRs:")
    for adr in adrs:
        print(f"  - {adr.adr_id}: {adr.adr_title} ({adr.adr_status.value})")

    # Test validation
    if adrs:
        test_id = adrs[0].adr_id
        print(f"\nValidating ADR: {test_id}")
        result = validator.validate_adr(test_id)
        print(f"  Valid: {result.valid}")
        if result.error_message:
            print(f"  Error: {result.error_message}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")

    # Test non-existent ADR
    print(f"\nValidating non-existent ADR: ADR-9999")
    result = validator.validate_adr("ADR-9999")
    print(f"  Valid: {result.valid}")
    print(f"  Error: {result.error_message}")

    # Create template
    print(f"\n=== ADR Template ===")
    template = validator.create_adr_template(
        adr_number=100,
        title="Allow Legacy Coupling in Module X"
    )
    print(template[:500] + "...")
