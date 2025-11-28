"""
Tests for language compatibility matching

Validates that the language variant system correctly matches related languages
(e.g., TypeScript and JavaScript are treated as compatible)
"""

import pytest
from routers.templates import get_language_variants


class TestLanguageVariants:
    """Test language variant matching."""

    def test_javascript_returns_all_js_ts_variants(self):
        """JavaScript should return all JS/TS variants."""
        variants = get_language_variants("javascript")
        assert set(variants) == {"javascript", "typescript", "js", "ts"}

    def test_typescript_returns_all_js_ts_variants(self):
        """TypeScript should return all JS/TS variants."""
        variants = get_language_variants("typescript")
        assert set(variants) == {"javascript", "typescript", "js", "ts"}

    def test_js_abbreviation_returns_all_variants(self):
        """'js' abbreviation should return all JS/TS variants."""
        variants = get_language_variants("js")
        assert set(variants) == {"javascript", "typescript", "js", "ts"}

    def test_ts_abbreviation_returns_all_variants(self):
        """'ts' abbreviation should return all JS/TS variants."""
        variants = get_language_variants("ts")
        assert set(variants) == {"javascript", "typescript", "js", "ts"}

    def test_python_returns_python_variants(self):
        """Python should return all Python variants."""
        variants = get_language_variants("python")
        assert set(variants) == {"python", "python3", "py"}

    def test_python3_returns_python_variants(self):
        """Python3 should return all Python variants."""
        variants = get_language_variants("python3")
        assert set(variants) == {"python", "python3", "py"}

    def test_py_abbreviation_returns_python_variants(self):
        """'py' abbreviation should return all Python variants."""
        variants = get_language_variants("py")
        assert set(variants) == {"python", "python3", "py"}

    def test_node_returns_js_and_node_variants(self):
        """Node.js variants should return both Node and JS/TS variants."""
        variants = get_language_variants("node")
        expected = {"javascript", "typescript", "js", "ts", "node", "nodejs", "node.js"}
        assert set(variants) == expected

    def test_nodejs_returns_js_and_node_variants(self):
        """'nodejs' should return both Node and JS/TS variants."""
        variants = get_language_variants("nodejs")
        expected = {"javascript", "typescript", "js", "ts", "node", "nodejs", "node.js"}
        assert set(variants) == expected

    def test_ruby_returns_ruby_variants(self):
        """Ruby should return ruby variants."""
        variants = get_language_variants("ruby")
        assert set(variants) == {"ruby", "rb"}

    def test_go_returns_go_variants(self):
        """Go should return go variants."""
        variants = get_language_variants("go")
        assert set(variants) == {"go", "golang"}

    def test_golang_returns_go_variants(self):
        """Golang should return go variants."""
        variants = get_language_variants("golang")
        assert set(variants) == {"go", "golang"}

    def test_case_insensitive_matching(self):
        """Language matching should be case-insensitive."""
        variants_lower = get_language_variants("javascript")
        variants_upper = get_language_variants("JavaScript")
        variants_mixed = get_language_variants("JavaScript")

        assert set(variants_lower) == set(variants_upper)
        assert set(variants_lower) == set(variants_mixed)

    def test_whitespace_handling(self):
        """Should handle leading/trailing whitespace."""
        variants = get_language_variants("  javascript  ")
        assert set(variants) == {"javascript", "typescript", "js", "ts"}

    def test_unknown_language_returns_normalized(self):
        """Unknown languages should return normalized version."""
        variants = get_language_variants("rust")
        assert variants == ["rust"]

    def test_empty_string_returns_empty_list(self):
        """Empty string should return empty list."""
        variants = get_language_variants("")
        assert variants == []

    def test_none_returns_empty_list(self):
        """None should return empty list."""
        variants = get_language_variants(None)
        assert variants == []


class TestLanguageCompatibilityIntegration:
    """Integration tests for language compatibility in search scenarios."""

    @pytest.mark.parametrize("search_lang,template_lang,should_match", [
        # JavaScript/TypeScript compatibility
        ("javascript", "typescript", True),
        ("typescript", "javascript", True),
        ("js", "typescript", True),
        ("ts", "javascript", True),

        # Python variants
        ("python", "python3", True),
        ("python3", "py", True),
        ("py", "python", True),

        # Node.js variants
        ("node", "javascript", True),
        ("nodejs", "typescript", True),

        # Non-matching cases
        ("python", "javascript", False),
        ("ruby", "javascript", False),
        ("go", "python", False),
    ])
    def test_language_matching_scenarios(self, search_lang, template_lang, should_match):
        """Test various language matching scenarios."""
        search_variants = set(get_language_variants(search_lang))

        if should_match:
            assert template_lang in search_variants, \
                f"Expected {template_lang} to be in variants of {search_lang}"
        else:
            assert template_lang not in search_variants, \
                f"Expected {template_lang} NOT to be in variants of {search_lang}"


class TestRealWorldScenarios:
    """Test real-world template discovery scenarios."""

    def test_react_template_discovery_with_javascript_search(self):
        """
        Scenario: User searches for 'javascript' + 'react'
        Template is tagged as 'typescript'
        Should match due to JS/TS compatibility
        """
        search_language = "javascript"
        template_language = "typescript"

        search_variants = get_language_variants(search_language)
        assert template_language in search_variants, \
            "React TypeScript templates should be discoverable via JavaScript search"

    def test_fastapi_template_discovery_with_python_search(self):
        """
        Scenario: User searches for 'python' + 'fastapi'
        Template might be tagged as 'python3'
        Should match due to Python variant compatibility
        """
        search_language = "python"
        template_language = "python3"

        search_variants = get_language_variants(search_language)
        assert template_language in search_variants, \
            "Python3 templates should be discoverable via Python search"

    def test_graphql_resolver_discovery(self):
        """
        Scenario: REQ-006 GraphQL resolver search
        Search uses 'graphql' framework filter
        Template language could be TypeScript, should still match JS searches
        """
        search_language = "javascript"
        template_language = "typescript"

        search_variants = get_language_variants(search_language)
        assert template_language in search_variants, \
            "GraphQL TypeScript resolvers should be discoverable via JavaScript search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
