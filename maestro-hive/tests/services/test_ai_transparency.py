"""
Tests for AI Transparency Module - MD-2155 Compliance
"""

import pytest
from unittest.mock import patch
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.ai_transparency import (
    get_ai_header,
    get_jira_disclosure,
    get_confluence_footer,
    AITransparencyConfig,
    AI_DISCLOSURE_PREFIX
)


class TestGetAIHeader:
    """Tests for get_ai_header function."""

    def test_header_contains_disclosure(self):
        """Test that header contains disclosure statement."""
        header = get_ai_header()
        assert "AI-GENERATED CONTENT" in header

    def test_header_contains_agent_name(self):
        """Test that header contains agent name."""
        header = get_ai_header(agent_name="TestAgent")
        assert "TestAgent" in header

    def test_header_contains_model(self):
        """Test that header contains model name."""
        header = get_ai_header(model="GPT-4")
        assert "GPT-4" in header

    def test_header_contains_timestamp(self):
        """Test that header contains timestamp."""
        header = get_ai_header()
        assert "Generated at:" in header

    def test_header_is_docstring_format(self):
        """Test that header is valid Python docstring format."""
        header = get_ai_header()
        assert header.startswith('\"\"\"')


class TestGetJiraDisclosure:
    """Tests for get_jira_disclosure function."""

    def test_disclosure_prefix_added(self):
        """Test that disclosure prefix is added to message."""
        message = "Test message"
        result = get_jira_disclosure(message)
        assert result.startswith(AI_DISCLOSURE_PREFIX)

    def test_original_message_preserved(self):
        """Test that original message is preserved."""
        message = "Test message"
        result = get_jira_disclosure(message)
        assert message in result


class TestGetConfluenceFooter:
    """Tests for get_confluence_footer function."""

    def test_footer_contains_disclosure(self):
        """Test that footer contains AI disclosure."""
        footer = get_confluence_footer()
        assert AI_DISCLOSURE_PREFIX in footer

    def test_footer_is_html(self):
        """Test that footer is HTML format."""
        footer = get_confluence_footer()
        assert "<hr/>" in footer or "<p>" in footer


class TestAITransparencyConfig:
    """Tests for AITransparencyConfig class."""

    def test_config_has_enabled_flag(self):
        """Test that config has enabled flag."""
        config = AITransparencyConfig()
        assert hasattr(config, 'enabled')

    def test_config_has_disclosure_prefix(self):
        """Test that config has disclosure prefix."""
        config = AITransparencyConfig()
        assert config.disclosure_prefix == AI_DISCLOSURE_PREFIX

    def test_config_to_dict(self):
        """Test that config can be exported as dict."""
        config = AITransparencyConfig()
        result = config.to_dict()
        assert isinstance(result, dict)
        assert 'enabled' in result
        assert 'disclosure_prefix' in result


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
