#!/usr/bin/env python3
"""
PRD Feature Extractor - Week 7-8 Requirements Traceability

Parses PRD documents and extracts structured feature requirements.
Handles various PRD formats and missing/incomplete documents.

Key Features:
- Parse markdown structure (headers, lists, tables)
- Extract feature descriptions
- Identify acceptance criteria
- Tag priorities and categories
- Handle multiple PRD formats
- Gracefully handle missing PRDs
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class FeaturePriority(Enum):
    """Feature priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NICE_TO_HAVE = "nice_to_have"


@dataclass
class AcceptanceCriterion:
    """Represents an acceptance criterion for a feature"""
    description: str
    testable: bool = True


@dataclass
class PRDFeature:
    """Represents a feature extracted from PRD"""
    id: str  # F1, F2, etc.
    title: str  # "User Authentication"
    description: str  # Full feature description
    category: Optional[str] = None  # "authentication", "user_management"
    priority: FeaturePriority = FeaturePriority.MEDIUM
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    source_file: Optional[str] = None
    section: Optional[str] = None  # Which section of PRD

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['priority'] = self.priority.value
        return data


class PRDFeatureExtractor:
    """Extracts features from PRD documents"""

    def __init__(self, requirements_dir: Path):
        self.requirements_dir = requirements_dir
        self.design_dir = requirements_dir.parent / "design" if requirements_dir.parent else None
        self.features: List[PRDFeature] = []

    async def extract(self) -> List[PRDFeature]:
        """Run complete PRD extraction"""
        logger.info(f"📋 Extracting features from PRD documents")

        if not self.requirements_dir.exists():
            logger.warning(f"  No requirements directory found at {self.requirements_dir}")
            return []

        # Find all markdown files in requirements and design directories
        prd_files = self._find_prd_files()

        if not prd_files:
            logger.warning("  No PRD documents found")
            return []

        logger.info(f"  Found {len(prd_files)} PRD document(s)")

        # Extract features from each file
        feature_id = 1
        for file in prd_files:
            try:
                content = file.read_text()
                file_features = await self._extract_features_from_file(
                    content,
                    str(file.relative_to(self.requirements_dir.parent)),
                    feature_id
                )
                self.features.extend(file_features)
                feature_id += len(file_features)
            except Exception as e:
                logger.warning(f"  Error parsing {file.name}: {e}")

        logger.info(f"✅ Extracted {len(self.features)} features from PRD")

        return self.features

    def _find_prd_files(self) -> List[Path]:
        """Find all PRD/requirements documents"""
        prd_files = []

        # Check requirements directory
        if self.requirements_dir.exists():
            prd_files.extend(list(self.requirements_dir.glob("*.md")))
            prd_files.extend(list(self.requirements_dir.glob("*.txt")))

        # Check design directory
        if self.design_dir and self.design_dir.exists():
            prd_files.extend(list(self.design_dir.glob("*.md")))
            prd_files.extend(list(self.design_dir.glob("*.txt")))

        return prd_files

    async def _extract_features_from_file(
        self,
        content: str,
        file_path: str,
        start_id: int
    ) -> List[PRDFeature]:
        """Extract features from a single PRD file"""
        features = []

        # Strategy 1: Extract from headers and sections
        header_features = self._extract_from_headers(content, file_path, start_id)
        features.extend(header_features)

        # Strategy 2: Extract from numbered lists
        if not features:
            list_features = self._extract_from_lists(content, file_path, start_id)
            features.extend(list_features)

        # Strategy 3: Extract from tables
        if not features:
            table_features = self._extract_from_tables(content, file_path, start_id)
            features.extend(table_features)

        # Strategy 4: Extract from "Feature:" or "Requirement:" patterns
        if not features:
            pattern_features = self._extract_from_patterns(content, file_path, start_id)
            features.extend(pattern_features)

        return features

    def _extract_from_headers(
        self,
        content: str,
        file_path: str,
        start_id: int
    ) -> List[PRDFeature]:
        """Extract features from markdown headers"""
        features = []

        # Parse markdown structure
        lines = content.split('\n')
        current_section = None
        current_feature = None
        current_description = []
        current_acceptance_criteria = []
        feature_id = start_id

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for headers (## Feature Name or ### Feature Name)
            header_match = re.match(r'^(#{2,4})\s+(.+)$', line)
            if header_match:
                # Save previous feature if exists
                if current_feature:
                    feature = self._create_feature(
                        feature_id,
                        current_feature,
                        '\n'.join(current_description),
                        current_acceptance_criteria,
                        file_path,
                        current_section
                    )
                    features.append(feature)
                    feature_id += 1

                # Start new feature
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # Skip common non-feature headers
                if self._is_feature_header(title):
                    current_feature = title
                    current_description = []
                    current_acceptance_criteria = []
                elif level == 2:
                    current_section = title
                    current_feature = None
                    current_description = []
                    current_acceptance_criteria = []

                i += 1
                continue

            # Collect feature description
            if current_feature and line:
                # Check if this is acceptance criteria
                if self._is_acceptance_criteria_header(line):
                    # Next lines are acceptance criteria
                    i += 1
                    while i < len(lines):
                        ac_line = lines[i].strip()
                        if not ac_line:
                            break
                        if ac_line.startswith('-') or ac_line.startswith('*') or re.match(r'^\d+\.', ac_line):
                            criterion_text = re.sub(r'^[-*\d.]+\s*', '', ac_line)
                            if criterion_text:
                                current_acceptance_criteria.append(
                                    AcceptanceCriterion(description=criterion_text)
                                )
                        else:
                            break
                        i += 1
                    continue
                else:
                    # Regular description line
                    if not line.startswith('#'):
                        current_description.append(line)

            i += 1

        # Save last feature
        if current_feature:
            feature = self._create_feature(
                feature_id,
                current_feature,
                '\n'.join(current_description),
                current_acceptance_criteria,
                file_path,
                current_section
            )
            features.append(feature)

        return features

    def _extract_from_lists(
        self,
        content: str,
        file_path: str,
        start_id: int
    ) -> List[PRDFeature]:
        """Extract features from bulleted or numbered lists"""
        features = []
        feature_id = start_id

        # Pattern: - Feature: Description or 1. Feature: Description
        pattern = r'^(?:[-*]|\d+\.)\s*(?:Feature|Requirement)?:?\s*(.+)$'

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                feature_text = match.group(1).strip()

                # Split into title and description if possible
                if ':' in feature_text:
                    parts = feature_text.split(':', 1)
                    title = parts[0].strip()
                    description = parts[1].strip()
                else:
                    title = feature_text
                    description = ""

                if title:
                    feature = PRDFeature(
                        id=f"F{feature_id}",
                        title=title,
                        description=description,
                        source_file=file_path,
                        priority=self._infer_priority(title + " " + description)
                    )
                    features.append(feature)
                    feature_id += 1

        return features

    def _extract_from_tables(
        self,
        content: str,
        file_path: str,
        start_id: int
    ) -> List[PRDFeature]:
        """Extract features from markdown tables"""
        features = []
        feature_id = start_id

        # Find markdown tables
        lines = content.split('\n')
        in_table = False
        header_row = []

        for line in lines:
            line = line.strip()

            # Check if this is a table row
            if '|' in line:
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]

                # Check if this is a separator row (|---|---|)
                if all(re.match(r'^-+$', cell) for cell in cells):
                    in_table = True
                    continue

                # If we're in a table and this isn't the header
                if in_table and cells:
                    # Try to extract feature info from cells
                    if len(cells) >= 2:
                        # Assume first column is feature name, second is description
                        title = cells[0]
                        description = cells[1] if len(cells) > 1 else ""
                        priority_str = cells[2] if len(cells) > 2 else ""

                        if title and not title.lower() in ['feature', 'name', 'title']:
                            feature = PRDFeature(
                                id=f"F{feature_id}",
                                title=title,
                                description=description,
                                source_file=file_path,
                                priority=self._parse_priority(priority_str)
                            )
                            features.append(feature)
                            feature_id += 1
                elif not in_table and cells:
                    # This might be the header row
                    header_row = cells
            else:
                in_table = False

        return features

    def _extract_from_patterns(
        self,
        content: str,
        file_path: str,
        start_id: int
    ) -> List[PRDFeature]:
        """Extract features using keyword patterns"""
        features = []
        feature_id = start_id

        # Patterns to look for
        patterns = [
            r'(?:Feature|Requirement)\s*:\s*(.+)',
            r'(?:FR|NFR)-\d+\s*:\s*(.+)',
            r'(?:User Story|Story)\s*:\s*(?:As a .+?,\s*)?(.+)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                feature_text = match.group(1).strip()

                if feature_text:
                    # Extract first sentence as title
                    sentences = re.split(r'[.!?]', feature_text)
                    title = sentences[0].strip() if sentences else feature_text
                    description = feature_text if len(feature_text) > len(title) else ""

                    feature = PRDFeature(
                        id=f"F{feature_id}",
                        title=title[:100],  # Limit title length
                        description=description,
                        source_file=file_path,
                        priority=self._infer_priority(feature_text)
                    )
                    features.append(feature)
                    feature_id += 1

        return features

    def _create_feature(
        self,
        feature_id: int,
        title: str,
        description: str,
        acceptance_criteria: List[AcceptanceCriterion],
        file_path: str,
        section: Optional[str]
    ) -> PRDFeature:
        """Create a PRDFeature object"""
        # Clean up title
        title = re.sub(r'^#+\s*', '', title).strip()

        # Infer category from title
        category = self._infer_category(title)

        # Infer priority
        priority = self._infer_priority(title + " " + description)

        return PRDFeature(
            id=f"F{feature_id}",
            title=title,
            description=description.strip(),
            category=category,
            priority=priority,
            acceptance_criteria=acceptance_criteria,
            source_file=file_path,
            section=section
        )

    def _is_feature_header(self, title: str) -> bool:
        """Check if header is likely a feature"""
        title_lower = title.lower()

        # Skip common non-feature headers
        skip_keywords = [
            'introduction', 'overview', 'background', 'scope',
            'requirements', 'features', 'functional', 'non-functional',
            'acceptance criteria', 'success criteria', 'assumptions',
            'dependencies', 'constraints', 'glossary', 'references',
            'appendix', 'revision history', 'table of contents'
        ]

        for keyword in skip_keywords:
            if keyword in title_lower:
                return False

        # Look for feature indicators
        feature_indicators = [
            'feature', 'functionality', 'capability', 'user',
            'system', 'api', 'interface', 'authentication',
            'management', 'create', 'update', 'delete', 'view'
        ]

        for indicator in feature_indicators:
            if indicator in title_lower:
                return True

        # If title is reasonably long and doesn't match skip keywords, consider it
        return len(title.split()) >= 2 and len(title.split()) <= 8

    def _is_acceptance_criteria_header(self, line: str) -> bool:
        """Check if line is an acceptance criteria header"""
        line_lower = line.lower()
        criteria_headers = [
            'acceptance criteria',
            'success criteria',
            'definition of done',
            'requirements',
            'criteria',
            'must have',
            'should have'
        ]

        return any(header in line_lower for header in criteria_headers)

    def _infer_category(self, title: str) -> Optional[str]:
        """Infer feature category from title"""
        title_lower = title.lower()

        # Category mapping
        categories = {
            'authentication': ['auth', 'login', 'register', 'sign in', 'sign up', 'password'],
            'user_management': ['user', 'profile', 'account', 'member'],
            'search': ['search', 'find', 'filter', 'query'],
            'reporting': ['report', 'analytics', 'dashboard', 'metrics'],
            'notification': ['notification', 'alert', 'email', 'sms'],
            'payment': ['payment', 'billing', 'subscription', 'checkout'],
            'admin': ['admin', 'administration', 'settings', 'configuration'],
            'api': ['api', 'endpoint', 'integration', 'webhook'],
        }

        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category

        return None

    def _infer_priority(self, text: str) -> FeaturePriority:
        """Infer priority from text"""
        text_lower = text.lower()

        if any(word in text_lower for word in ['critical', 'must', 'required', 'essential']):
            return FeaturePriority.CRITICAL
        elif any(word in text_lower for word in ['high', 'important', 'key']):
            return FeaturePriority.HIGH
        elif any(word in text_lower for word in ['low', 'minor', 'optional']):
            return FeaturePriority.LOW
        elif any(word in text_lower for word in ['nice', 'future', 'enhancement']):
            return FeaturePriority.NICE_TO_HAVE
        else:
            return FeaturePriority.MEDIUM

    def _parse_priority(self, priority_str: str) -> FeaturePriority:
        """Parse priority from string"""
        priority_lower = priority_str.lower().strip()

        priority_map = {
            'critical': FeaturePriority.CRITICAL,
            'high': FeaturePriority.HIGH,
            'medium': FeaturePriority.MEDIUM,
            'low': FeaturePriority.LOW,
            'nice to have': FeaturePriority.NICE_TO_HAVE,
            'nice-to-have': FeaturePriority.NICE_TO_HAVE,
        }

        return priority_map.get(priority_lower, FeaturePriority.MEDIUM)


async def extract_prd_features(requirements_dir: Path) -> List[PRDFeature]:
    """Main entry point for PRD feature extraction"""
    extractor = PRDFeatureExtractor(requirements_dir)
    features = await extractor.extract()
    return features


async def generate_prd_report(requirements_dir: Path, output_file: Optional[Path] = None) -> Dict[str, Any]:
    """Generate PRD feature extraction report"""
    features = await extract_prd_features(requirements_dir)

    report = {
        "requirements_dir": str(requirements_dir),
        "total_features": len(features),
        "features": [f.to_dict() for f in features],
        "summary": {
            "by_category": {},
            "by_priority": {},
            "with_acceptance_criteria": sum(1 for f in features if f.acceptance_criteria),
        }
    }

    # Count by category
    for feature in features:
        if feature.category:
            cat = feature.category
            report["summary"]["by_category"][cat] = report["summary"]["by_category"].get(cat, 0) + 1

    # Count by priority
    for feature in features:
        priority = feature.priority.value
        report["summary"]["by_priority"][priority] = report["summary"]["by_priority"].get(priority, 0) + 1

    # Save to file if requested
    if output_file:
        output_file.write_text(json.dumps(report, indent=2))
        logger.info(f"📄 Saved PRD report to {output_file}")

    return report


if __name__ == "__main__":
    # Test on Batch 5 workflow
    import asyncio

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

    async def main():
        workflow_dir = Path("/tmp/maestro_workflow/wf-1760076571-6b932a66")
        requirements_dir = workflow_dir / "requirements"

        print("=" * 80)
        print("PRD FEATURE EXTRACTOR - TEST RUN")
        print("=" * 80)
        print(f"Analyzing: {requirements_dir}\n")

        report = await generate_prd_report(
            requirements_dir,
            workflow_dir / "PRD_FEATURE_REPORT.json"
        )

        print("\n" + "=" * 80)
        print("EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"\n📊 Summary:")
        print(f"  Total Features: {report['total_features']}")
        print(f"  With Acceptance Criteria: {report['summary']['with_acceptance_criteria']}")

        if report['summary']['by_category']:
            print(f"\n📋 Features by Category:")
            for category, count in report['summary']['by_category'].items():
                print(f"  {category}: {count}")

        if report['summary']['by_priority']:
            print(f"\n🎯 Features by Priority:")
            for priority, count in report['summary']['by_priority'].items():
                print(f"  {priority}: {count}")

        if report['features']:
            print(f"\n✅ Extracted Features:")
            for feature_data in report['features'][:5]:  # Show first 5
                print(f"\n  {feature_data['id']}: {feature_data['title']}")
                if feature_data['category']:
                    print(f"    Category: {feature_data['category']}")
                print(f"    Priority: {feature_data['priority']}")
                if feature_data['description']:
                    desc = feature_data['description'][:100]
                    print(f"    Description: {desc}...")
                if feature_data['acceptance_criteria']:
                    print(f"    Acceptance Criteria: {len(feature_data['acceptance_criteria'])}")
        else:
            print("\n⚠️  No features found in PRD documents")
            print("   This is expected for Batch 5 workflows (empty requirements)")

    asyncio.run(main())
