"""
Syntax Validator for Generated Code.

EPIC: MD-2496
AC-2: Generated code passes syntax validation
AC-1: No NotImplementedError stubs in output
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from maestro_hive.codegen.exceptions import SyntaxValidationError

logger = logging.getLogger(__name__)


@dataclass
class StubLocation:
    """Location of a NotImplementedError stub in code."""

    line: int
    column: int
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    code_snippet: str = ""


@dataclass
class ValidationResult:
    """Result of syntax validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ast_node_count: int = 0
    has_stubs: bool = False
    stub_locations: List[StubLocation] = field(default_factory=list)


class SyntaxValidator:
    """
    Validate code syntax using AST parsing.

    AC-2: Ensures generated code passes syntax validation.
    AC-1: Detects NotImplementedError stubs.
    """

    # Patterns that indicate incomplete implementation
    STUB_PATTERNS = [
        r"raise\s+NotImplementedError",
        r"raise\s+NotImplemented\b",
        r"pass\s*#\s*TODO",
        r"pass\s*#\s*FIXME",
        r"\.\.\.\s*#\s*TODO",
        r"# TODO: implement",
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize validator.

        Args:
            strict_mode: If True, stubs are treated as errors
        """
        self.strict_mode = strict_mode
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.STUB_PATTERNS
        ]

    def validate(
        self,
        code: str,
        language: str = "python",
    ) -> ValidationResult:
        """
        Validate code syntax.

        Args:
            code: Source code to validate
            language: Programming language

        Returns:
            ValidationResult with validation status
        """
        if language.lower() != "python":
            # For non-Python, do basic validation
            return self._validate_generic(code)

        return self._validate_python(code)

    def _validate_python(self, code: str) -> ValidationResult:
        """Validate Python code using AST."""
        errors: List[str] = []
        warnings: List[str] = []
        ast_node_count = 0

        # Step 1: Parse AST (AC-2)
        try:
            tree = ast.parse(code)
            ast_node_count = sum(1 for _ in ast.walk(tree))
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return ValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                ast_node_count=0,
                has_stubs=False,
            )

        # Step 2: Check for stubs (AC-1)
        stub_locations = self._find_stubs(code, tree)
        has_stubs = len(stub_locations) > 0

        if has_stubs:
            for stub in stub_locations:
                location = f"line {stub.line}"
                if stub.function_name:
                    location += f" in function '{stub.function_name}'"
                if stub.class_name:
                    location += f" (class '{stub.class_name}')"

                if self.strict_mode:
                    errors.append(f"NotImplementedError stub at {location}")
                else:
                    warnings.append(f"NotImplementedError stub at {location}")

        # Step 3: Additional checks
        additional_warnings = self._check_code_quality(tree, code)
        warnings.extend(additional_warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            ast_node_count=ast_node_count,
            has_stubs=has_stubs,
            stub_locations=stub_locations,
        )

    def _find_stubs(
        self,
        code: str,
        tree: ast.AST,
    ) -> List[StubLocation]:
        """Find NotImplementedError stubs in code."""
        stubs: List[StubLocation] = []
        lines = code.split("\n")

        # Method 1: Regex pattern matching
        for i, line in enumerate(lines, 1):
            for pattern in self._compiled_patterns:
                if pattern.search(line):
                    # Get context
                    function_name, class_name = self._get_context(tree, i)
                    stubs.append(
                        StubLocation(
                            line=i,
                            column=0,
                            function_name=function_name,
                            class_name=class_name,
                            code_snippet=line.strip(),
                        )
                    )
                    break

        # Method 2: AST walking for Raise nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                if self._is_not_implemented_raise(node):
                    if not any(s.line == node.lineno for s in stubs):
                        function_name, class_name = self._get_context(tree, node.lineno)
                        stubs.append(
                            StubLocation(
                                line=node.lineno,
                                column=node.col_offset,
                                function_name=function_name,
                                class_name=class_name,
                                code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                            )
                        )

        return stubs

    def _is_not_implemented_raise(self, node: ast.Raise) -> bool:
        """Check if Raise node is NotImplementedError."""
        if node.exc is None:
            return False

        # Check for raise NotImplementedError
        if isinstance(node.exc, ast.Call):
            if isinstance(node.exc.func, ast.Name):
                return node.exc.func.id in ("NotImplementedError", "NotImplemented")
        elif isinstance(node.exc, ast.Name):
            return node.exc.id in ("NotImplementedError", "NotImplemented")

        return False

    def _get_context(
        self,
        tree: ast.AST,
        line_number: int,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get function and class context for a line number."""
        function_name = None
        class_name = None

        for node in ast.walk(tree):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                if node.lineno <= line_number <= (node.end_lineno or node.lineno):
                    if isinstance(node, ast.FunctionDef):
                        function_name = node.name
                    elif isinstance(node, ast.AsyncFunctionDef):
                        function_name = node.name
                    elif isinstance(node, ast.ClassDef):
                        class_name = node.name

        return function_name, class_name

    def _check_code_quality(
        self,
        tree: ast.AST,
        code: str,
    ) -> List[str]:
        """Check for additional code quality issues."""
        warnings: List[str] = []

        # Check for empty functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if body is just pass or Ellipsis
                if len(node.body) == 1:
                    body = node.body[0]
                    if isinstance(body, ast.Pass):
                        warnings.append(
                            f"Empty function '{node.name}' at line {node.lineno}"
                        )
                    elif isinstance(body, ast.Expr) and isinstance(body.value, ast.Constant):
                        if body.value.value is ...:  # Ellipsis
                            warnings.append(
                                f"Ellipsis-only function '{node.name}' at line {node.lineno}"
                            )

        # Check for missing docstrings in public functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):  # Public function
                    if not self._has_docstring(node):
                        warnings.append(
                            f"Missing docstring in '{node.name}' at line {node.lineno}"
                        )

        return warnings

    def _has_docstring(self, node: ast.AST) -> bool:
        """Check if function/class has a docstring."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    if isinstance(first.value.value, str):
                        return True
        return False

    def _validate_generic(self, code: str) -> ValidationResult:
        """Basic validation for non-Python code."""
        warnings: List[str] = []
        stub_locations: List[StubLocation] = []

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            for pattern in self._compiled_patterns:
                if pattern.search(line):
                    stub_locations.append(
                        StubLocation(
                            line=i,
                            column=0,
                            code_snippet=line.strip(),
                        )
                    )
                    warnings.append(f"Possible stub at line {i}")
                    break

        return ValidationResult(
            valid=True,  # Can't validate non-Python syntax
            errors=[],
            warnings=warnings,
            ast_node_count=0,
            has_stubs=len(stub_locations) > 0,
            stub_locations=stub_locations,
        )

    def check_for_stubs(self, code: str) -> List[StubLocation]:
        """
        Check code for NotImplementedError stubs.

        AC-1: No NotImplementedError stubs in output.

        Args:
            code: Source code to check

        Returns:
            List of stub locations found
        """
        result = self.validate(code)
        return result.stub_locations
