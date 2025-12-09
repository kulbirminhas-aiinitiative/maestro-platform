#!/usr/bin/env python3
"""Tests for Requirements Ingestion module."""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.requirements.ingestion import (
    RequirementsIngester,
    Requirement,
    RequirementType,
    RequirementPriority,
    IngestionResult,
    ingest_requirements
)


class TestRequirement:
    """Tests for Requirement dataclass."""

    def test_requirement_creation(self):
        """Test creating a Requirement."""
        req = Requirement(
            id="REQ-001",
            title="Test Requirement",
            description="A test requirement",
            type=RequirementType.FUNCTIONAL
        )

        assert req.id == "REQ-001"
        assert req.type == RequirementType.FUNCTIONAL
        assert req.priority == RequirementPriority.MEDIUM

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        req = Requirement(
            id="REQ-002",
            title="Test",
            description="Test desc",
            type=RequirementType.USER_STORY,
            priority=RequirementPriority.HIGH,
            tags=["tag1", "tag2"]
        )

        data = req.to_dict()
        restored = Requirement.from_dict(data)

        assert restored.id == req.id
        assert restored.type == RequirementType.USER_STORY
        assert restored.priority == RequirementPriority.HIGH


class TestRequirementsIngester:
    """Tests for RequirementsIngester class."""

    def test_ingest_markdown_user_story(self):
        """Test ingesting markdown user stories."""
        markdown = """
## User Story: Login Feature
As a user, I want to login with my credentials so that I can access my account.

### Acceptance Criteria
- [ ] User can enter email and password
- [ ] System validates credentials
- [ ] User is redirected to dashboard on success

#authentication #security
"""
        ingester = RequirementsIngester()
        result = ingester.ingest_markdown(markdown)

        assert len(result.requirements) >= 1
        req = result.requirements[0]
        assert req.type == RequirementType.USER_STORY
        assert len(req.acceptance_criteria) >= 1
        assert "authentication" in req.tags or "security" in req.tags

    def test_ingest_markdown_multiple_stories(self):
        """Test ingesting multiple user stories."""
        markdown = """
## Feature 1
As a admin, I want to manage users so that I can control access.

## Feature 2
As a user, I want to reset my password so that I can regain access.
"""
        ingester = RequirementsIngester()
        result = ingester.ingest_markdown(markdown)

        assert len(result.requirements) >= 2

    def test_ingest_markdown_empty(self):
        """Test ingesting empty markdown."""
        ingester = RequirementsIngester()
        result = ingester.ingest_markdown("No user stories here")

        assert len(result.requirements) == 0
        assert len(result.warnings) >= 1

    def test_ingest_jira_mock(self):
        """Test JIRA ingestion without client."""
        ingester = RequirementsIngester()
        result = ingester.ingest_jira("TEST-123")

        assert len(result.requirements) >= 1
        assert len(result.warnings) >= 1  # Should warn about mock

    def test_ingest_bdd_feature(self):
        """Test ingesting BDD feature file."""
        feature_content = """
Feature: User Authentication
  As a user I want to authenticate

  @login @security
  Scenario: Successful login
    Given I am on the login page
    When I enter valid credentials
    And I click the login button
    Then I should see the dashboard

  @logout
  Scenario: Logout
    Given I am logged in
    When I click logout
    Then I should see the login page
"""
        with tempfile.NamedTemporaryFile(suffix=".feature", mode='w', delete=False) as f:
            f.write(feature_content)
            feature_path = Path(f.name)

        try:
            ingester = RequirementsIngester()
            result = ingester.ingest_bdd(feature_path)

            assert len(result.requirements) >= 2
            assert result.requirements[0].type == RequirementType.ACCEPTANCE_CRITERIA
            assert "login" in result.requirements[0].tags or "security" in result.requirements[0].tags
        finally:
            feature_path.unlink()

    def test_parse_natural_language_functional(self):
        """Test parsing natural language requirements."""
        text = """
The system must validate user input before processing.
Users should be able to export data in CSV format.
The application must handle 1000 concurrent users.
"""
        ingester = RequirementsIngester()
        result = ingester.parse_natural_language(text)

        assert len(result.requirements) >= 1
        # Check that requirements are identified
        assert any(r.type == RequirementType.FUNCTIONAL for r in result.requirements)

    def test_parse_natural_language_priority(self):
        """Test priority detection in natural language."""
        text = "The system must have a critical security feature that is essential."

        ingester = RequirementsIngester()
        result = ingester.parse_natural_language(text)

        if result.requirements:
            # Should detect high priority keywords
            assert result.requirements[0].priority in [
                RequirementPriority.CRITICAL,
                RequirementPriority.HIGH
            ]

    def test_generate_unique_ids(self):
        """Test that generated IDs are unique."""
        ingester = RequirementsIngester()

        # Generate multiple requirements
        result1 = ingester.ingest_markdown("## Story 1\nAs a user...")
        result2 = ingester.ingest_markdown("## Story 2\nAs a admin...")

        if result1.requirements and result2.requirements:
            assert result1.requirements[0].id != result2.requirements[0].id


class TestIngestRequirementsFunction:
    """Tests for convenience function."""

    def test_auto_detect_markdown(self):
        """Test auto-detection of markdown."""
        content = "## User Story\nAs a user..."
        result = ingest_requirements(content, source_type="auto")
        assert result.source_type == "markdown"

    def test_auto_detect_jira(self):
        """Test auto-detection of JIRA key."""
        result = ingest_requirements("MD-123", source_type="auto")
        assert result.source_type == "jira"

    def test_explicit_type(self):
        """Test explicit source type."""
        result = ingest_requirements("Some text", source_type="natural_language")
        assert result.source_type == "natural_language"


class TestIngestionResult:
    """Tests for IngestionResult dataclass."""

    def test_result_structure(self):
        """Test IngestionResult structure."""
        result = IngestionResult(
            requirements=[],
            source="test",
            source_type="test",
            parse_errors=["Error 1"],
            warnings=["Warning 1"],
            metadata={"key": "value"}
        )

        assert result.source == "test"
        assert len(result.parse_errors) == 1
        assert len(result.warnings) == 1
        assert "key" in result.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
