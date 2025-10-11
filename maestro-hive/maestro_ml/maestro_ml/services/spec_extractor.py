#!/usr/bin/env python3
"""
Spec Extractor Service

Parses REQUIREMENTS.md files created by requirement_analyst
and extracts structured specifications for ML similarity analysis.

Extracts:
- User stories
- Functional requirements
- Non-functional requirements
- Data models
- API endpoints
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path


class SpecExtractor:
    """
    Extract structured specs from REQUIREMENTS.md.

    Parses markdown sections and converts to structured format
    suitable for ML similarity analysis.
    """

    def extract_from_file(self, requirements_path: Path) -> Dict[str, Any]:
        """
        Extract specs from REQUIREMENTS.md file.

        Args:
            requirements_path: Path to REQUIREMENTS.md

        Returns:
            Structured specs dict
        """

        if not requirements_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

        content = requirements_path.read_text()

        return self.extract_from_text(content)

    def extract_from_text(self, content: str) -> Dict[str, Any]:
        """
        Extract specs from requirements document text.

        Args:
            content: Raw markdown content

        Returns:
            {
                "user_stories": [...],
                "functional_requirements": [...],
                "non_functional_requirements": [...],
                "data_models": [...],
                "api_endpoints": [...]
            }
        """

        specs = {
            "user_stories": self._extract_user_stories(content),
            "functional_requirements": self._extract_functional_requirements(content),
            "non_functional_requirements": self._extract_non_functional_requirements(content),
            "data_models": self._extract_data_models(content),
            "api_endpoints": self._extract_api_endpoints(content)
        }

        return specs

    def _extract_user_stories(self, content: str) -> List[str]:
        """
        Extract user stories from content.

        Looks for patterns like:
        - "As a [role], I want [feature], so that [benefit]"
        - Numbered/bulleted lists in "User Stories" section
        """

        stories = []

        # Find User Stories section
        user_story_section = self._extract_section(content, "User Stories")

        if user_story_section:
            # Pattern 1: "As a ... I want ... so that ..."
            as_a_pattern = r'(?:^|\n)\s*[-*]?\s*(As (?:a|an) .+?(?:so that|in order to).+?)(?:\n|$)'
            matches = re.findall(as_a_pattern, user_story_section, re.IGNORECASE | re.MULTILINE)
            stories.extend([m.strip() for m in matches])

            # Pattern 2: Numbered/bulleted lists
            if not stories:
                list_pattern = r'(?:^|\n)\s*(?:\d+\.|[-*])\s*(.+?)(?=\n\s*(?:\d+\.|[-*])|\n\n|\Z)'
                matches = re.findall(list_pattern, user_story_section, re.MULTILINE | re.DOTALL)
                stories.extend([m.strip() for m in matches if len(m.strip()) > 20])

        # Also check for standalone "As a" patterns anywhere in document
        if not stories:
            as_a_pattern = r'(?:^|\n)\s*[-*]?\s*(As (?:a|an) .+?(?:so that|in order to|\.)\s*.+?)(?:\n|$)'
            matches = re.findall(as_a_pattern, content, re.IGNORECASE | re.MULTILINE)
            stories.extend([m.strip() for m in matches][:50])  # Limit to 50

        return stories[:100]  # Max 100 stories

    def _extract_functional_requirements(self, content: str) -> List[str]:
        """
        Extract functional requirements.

        Looks for:
        - "Functional Requirements" section
        - "The system shall/must/should..." patterns
        - Numbered/bulleted requirement lists
        """

        requirements = []

        # Find Functional Requirements section
        fr_section = self._extract_section(content, "Functional Requirements")

        if fr_section:
            # Pattern: "The system shall/must/should..."
            shall_pattern = r'(?:^|\n)\s*[-*]?\s*((?:The system|System|Application|Platform) (?:shall|must|should|will) .+?)(?:\n|$)'
            matches = re.findall(shall_pattern, fr_section, re.IGNORECASE | re.MULTILINE)
            requirements.extend([m.strip() for m in matches])

            # Pattern: Numbered/bulleted lists
            if not requirements:
                list_pattern = r'(?:^|\n)\s*(?:\d+\.|[-*])\s*(.+?)(?=\n\s*(?:\d+\.|[-*])|\n\n|\Z)'
                matches = re.findall(list_pattern, fr_section, re.MULTILINE | re.DOTALL)
                requirements.extend([m.strip() for m in matches if len(m.strip()) > 15])

        # Also check for "shall" patterns anywhere
        if not requirements:
            shall_pattern = r'(?:^|\n)\s*[-*]?\s*((?:The system|System|Application) (?:shall|must|should) .+?)(?:\n|$)'
            matches = re.findall(shall_pattern, content, re.IGNORECASE | re.MULTILINE)
            requirements.extend([m.strip() for m in matches][:150])

        return requirements[:200]  # Max 200 requirements

    def _extract_non_functional_requirements(self, content: str) -> List[str]:
        """
        Extract non-functional requirements (performance, security, etc.)
        """

        nfrs = []

        # Find Non-Functional Requirements section
        nfr_section = self._extract_section(content, "Non-Functional Requirements")

        if nfr_section:
            list_pattern = r'(?:^|\n)\s*(?:\d+\.|[-*])\s*(.+?)(?=\n\s*(?:\d+\.|[-*])|\n\n|\Z)'
            matches = re.findall(list_pattern, nfr_section, re.MULTILINE | re.DOTALL)
            nfrs.extend([m.strip() for m in matches if len(m.strip()) > 15])

        return nfrs[:100]

    def _extract_data_models(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract data models (entities and fields).

        Looks for:
        - "Data Models" section
        - Entity definitions with fields
        """

        models = []

        # Find Data Models section
        dm_section = self._extract_section(content, "Data Models")

        if dm_section:
            # Pattern: Entity name followed by fields
            # E.g., "User:", "Task Entity:", etc.
            entity_pattern = r'(?:^|\n)\s*(?:###|##)?\s*(\w+)\s*(?:Entity|Model)?:\s*\n((?:[-*]\s*.+?\n)+)'
            matches = re.findall(entity_pattern, dm_section, re.MULTILINE)

            for entity_name, fields_block in matches:
                # Extract field names
                field_pattern = r'[-*]\s*(\w+(?:\s+\w+)?)'
                fields = re.findall(field_pattern, fields_block)

                if fields:
                    models.append({
                        "entity": entity_name.strip(),
                        "fields": fields[:50]  # Max 50 fields per entity
                    })

        # Also try table format
        if not models:
            # Pattern: | Entity | Field | Type |
            table_pattern = r'\|\s*(\w+)\s*\|\s*(\w+)\s*\|'
            matches = re.findall(table_pattern, dm_section or content)

            entity_fields = {}
            for entity, field in matches:
                if entity not in entity_fields:
                    entity_fields[entity] = []
                entity_fields[entity].append(field)

            for entity, fields in entity_fields.items():
                models.append({
                    "entity": entity,
                    "fields": fields[:50]
                })

        return models[:50]  # Max 50 models

    def _extract_api_endpoints(self, content: str) -> List[Dict[str, str]]:
        """
        Extract API endpoints (method + path).

        Looks for:
        - "API Endpoints" section
        - HTTP method + path patterns (GET /users, POST /tasks)
        """

        endpoints = []

        # Find API Endpoints section
        api_section = self._extract_section(content, "API Endpoints")

        if api_section:
            # Pattern: METHOD /path
            # E.g., "GET /users", "POST /tasks", "PUT /tasks/{id}"
            endpoint_pattern = r'(GET|POST|PUT|PATCH|DELETE)\s+(/[\w/{}:-]*)'
            matches = re.findall(endpoint_pattern, api_section, re.IGNORECASE)

            for method, path in matches:
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "purpose": self._infer_purpose(method, path)
                })

        # Also try table format
        if not endpoints:
            # Pattern: | Method | Path | Purpose |
            table_pattern = r'\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*(/[\w/{}:-]*)\s*\|\s*(.+?)\s*\|'
            matches = re.findall(table_pattern, api_section or content, re.IGNORECASE)

            for method, path, purpose in matches:
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "purpose": purpose.strip()
                })

        return endpoints[:100]  # Max 100 endpoints

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """
        Extract content from a specific markdown section.

        Args:
            content: Full markdown content
            section_name: Section heading to find

        Returns:
            Section content or None
        """

        # Try different heading levels
        patterns = [
            rf'^##\s+{re.escape(section_name)}\s*\n(.+?)(?=\n##|\Z)',
            rf'^###\s+{re.escape(section_name)}\s*\n(.+?)(?=\n###|\n##|\Z)',
            rf'^#\s+{re.escape(section_name)}\s*\n(.+?)(?=\n#|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _infer_purpose(self, method: str, path: str) -> str:
        """Infer purpose from method and path"""
        method = method.upper()

        # Extract resource name from path
        resource = path.split('/')[-1].replace('{', '').replace('}', '').strip('-')

        if method == "GET":
            if '{' in path or 'id' in path.lower():
                return f"Get {resource} by ID"
            else:
                return f"List {resource}"
        elif method == "POST":
            return f"Create {resource}"
        elif method == "PUT" or method == "PATCH":
            return f"Update {resource}"
        elif method == "DELETE":
            return f"Delete {resource}"
        else:
            return f"{method} {resource}"

    def validate_specs(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted specs and return quality metrics.

        Returns:
            {
                "valid": bool,
                "completeness_score": float (0-1),
                "issues": List[str]
            }
        """

        issues = []
        scores = []

        # Check user stories
        if not specs.get("user_stories"):
            issues.append("No user stories found")
            scores.append(0)
        else:
            scores.append(min(len(specs["user_stories"]) / 20, 1.0))  # Target 20+

        # Check functional requirements
        if not specs.get("functional_requirements"):
            issues.append("No functional requirements found")
            scores.append(0)
        else:
            scores.append(min(len(specs["functional_requirements"]) / 50, 1.0))  # Target 50+

        # Check data models
        if not specs.get("data_models"):
            issues.append("No data models found")
            scores.append(0)
        else:
            scores.append(min(len(specs["data_models"]) / 5, 1.0))  # Target 5+

        # Check API endpoints
        if not specs.get("api_endpoints"):
            issues.append("No API endpoints found (may be okay for some projects)")
            scores.append(0.5)  # Half penalty
        else:
            scores.append(min(len(specs["api_endpoints"]) / 20, 1.0))  # Target 20+

        completeness_score = sum(scores) / len(scores) if scores else 0

        return {
            "valid": completeness_score >= 0.3,  # At least 30% complete
            "completeness_score": completeness_score,
            "issues": issues,
            "stats": {
                "user_stories": len(specs.get("user_stories", [])),
                "functional_requirements": len(specs.get("functional_requirements", [])),
                "non_functional_requirements": len(specs.get("non_functional_requirements", [])),
                "data_models": len(specs.get("data_models", [])),
                "api_endpoints": len(specs.get("api_endpoints", []))
            }
        }
