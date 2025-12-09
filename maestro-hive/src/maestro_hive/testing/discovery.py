#!/usr/bin/env python3
"""
Test Discovery: Automatic test discovery utilities.

Implements AC-2: Test discovery and execution utilities.
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .framework import TestCase

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryConfig:
    """Test discovery configuration."""
    patterns: List[str] = field(default_factory=lambda: ["test_*.py", "*_test.py"])
    exclude_patterns: List[str] = field(default_factory=lambda: ["__pycache__", ".git", "venv"])
    recursive: bool = True
    include_docstrings: bool = True
    max_depth: int = 10


class TestDiscovery:
    """
    Automatic test discovery.

    AC-2: Test discovery implementation.

    Features:
    - Pattern-based file discovery
    - AST-based function extraction
    - Docstring parsing for descriptions
    - Tag extraction from decorators
    """

    def __init__(self, config: Optional[DiscoveryConfig] = None):
        self.config = config or DiscoveryConfig()
        self._discovered: List[TestCase] = []

    def discover_tests(self, path: str) -> List[TestCase]:
        """
        Discover all tests in the given path.

        Returns list of TestCase objects.
        """
        self._discovered = []
        root_path = Path(path)

        if not root_path.exists():
            logger.warning(f"Path does not exist: {path}")
            return []

        if root_path.is_file():
            self._process_file(root_path)
        else:
            self._discover_in_directory(root_path, depth=0)

        logger.info(f"Discovered {len(self._discovered)} tests")
        return self._discovered

    def discover_modules(self, path: str) -> List[str]:
        """Discover Python modules in path."""
        modules = []
        root_path = Path(path)

        for py_file in root_path.rglob("*.py"):
            if self._should_exclude(py_file):
                continue

            # Convert file path to module name
            relative = py_file.relative_to(root_path)
            module = str(relative).replace(os.sep, ".").replace(".py", "")
            modules.append(module)

        return modules

    def _discover_in_directory(self, directory: Path, depth: int) -> None:
        """Recursively discover tests in directory."""
        if depth > self.config.max_depth:
            return

        for item in directory.iterdir():
            if self._should_exclude(item):
                continue

            if item.is_file() and self._matches_pattern(item.name):
                self._process_file(item)
            elif item.is_dir() and self.config.recursive:
                self._discover_in_directory(item, depth + 1)

    def _process_file(self, file_path: Path) -> None:
        """Extract test cases from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if self._is_test_function(node.name):
                        test_case = self._create_test_case(node, file_path)
                        self._discovered.append(test_case)

                elif isinstance(node, ast.ClassDef):
                    if self._is_test_class(node.name):
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                if self._is_test_function(item.name):
                                    test_case = self._create_test_case(
                                        item, file_path, class_name=node.name
                                    )
                                    self._discovered.append(test_case)

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    def _create_test_case(
        self,
        node: ast.FunctionDef,
        file_path: Path,
        class_name: Optional[str] = None
    ) -> TestCase:
        """Create a TestCase from an AST node."""
        # Extract docstring
        description = ""
        if self.config.include_docstrings:
            docstring = ast.get_docstring(node)
            if docstring:
                description = docstring.split('\n')[0]

        # Extract tags from decorators
        tags = self._extract_tags(node)

        # Build module name
        module = str(file_path).replace(os.sep, ".").replace(".py", "")
        if class_name:
            module = f"{module}.{class_name}"

        # Generate unique ID
        test_id = f"{module}.{node.name}"

        return TestCase(
            id=test_id,
            name=node.name,
            module=module,
            file_path=str(file_path),
            line_number=node.lineno,
            description=description,
            tags=tags
        )

    def _extract_tags(self, node: ast.FunctionDef) -> List[str]:
        """Extract tags from pytest markers and decorators."""
        tags = []

        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "mark":
                        # Extract marker name
                        for keyword in decorator.keywords:
                            tags.append(keyword.arg)
                    else:
                        tags.append(decorator.func.attr)
            elif isinstance(decorator, ast.Attribute):
                tags.append(decorator.attr)
            elif isinstance(decorator, ast.Name):
                tags.append(decorator.id)

        return tags

    def _is_test_function(self, name: str) -> bool:
        """Check if function name indicates a test."""
        return name.startswith("test_") or name.startswith("test")

    def _is_test_class(self, name: str) -> bool:
        """Check if class name indicates a test class."""
        return name.startswith("Test") or name.endswith("Test")

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches any test pattern."""
        import fnmatch
        return any(
            fnmatch.fnmatch(filename, pattern)
            for pattern in self.config.patterns
        )

    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        name = path.name
        return any(
            pattern in str(path) or name == pattern
            for pattern in self.config.exclude_patterns
        )

    def get_test_count(self) -> int:
        """Get count of discovered tests."""
        return len(self._discovered)

    def get_tests_by_tag(self, tag: str) -> List[TestCase]:
        """Filter tests by tag."""
        return [tc for tc in self._discovered if tag in tc.tags]

    def get_tests_by_module(self, module: str) -> List[TestCase]:
        """Filter tests by module."""
        return [tc for tc in self._discovered if module in tc.module]


def discover_tests(path: str, **kwargs) -> List[TestCase]:
    """Convenience function to discover tests."""
    config = DiscoveryConfig(**kwargs) if kwargs else None
    discovery = TestDiscovery(config=config)
    return discovery.discover_tests(path)
