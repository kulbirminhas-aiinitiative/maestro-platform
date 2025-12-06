"""
Auto-Refactoring Engine for Self-Healing Mechanism.

Applies automated fixes based on detected failure patterns.

Implements AC-2: Auto-refactoring block for common issues
"""

import ast
import logging
import re
import difflib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import uuid

from .models import (
    FailureType,
    ActionType,
    FailurePattern,
    HealingAction,
)

logger = logging.getLogger(__name__)


@dataclass
class RefactorResult:
    """Result of a refactoring operation."""
    success: bool
    original_code: str
    fixed_code: str
    diff: str
    action_type: ActionType
    confidence: float
    description: str
    warnings: List[str]


class AutoRefactorEngine:
    """
    Engine for applying automated refactoring fixes.

    This component:
    1. Takes a failure pattern and source code
    2. Generates an appropriate fix
    3. Validates the fix (syntax check)
    4. Returns a diff for application
    """

    def __init__(
        self,
        min_confidence: float = 0.7,
        validate_syntax: bool = True,
        max_diff_size: int = 100,
    ):
        """
        Initialize the refactoring engine.

        Args:
            min_confidence: Minimum confidence to apply fix
            validate_syntax: Whether to validate Python syntax
            max_diff_size: Maximum lines changed in a single fix
        """
        self.min_confidence = min_confidence
        self.validate_syntax = validate_syntax
        self.max_diff_size = max_diff_size

        # Register fix handlers
        self._fix_handlers = {
            FailureType.SYNTAX: self._fix_syntax_error,
            FailureType.RUNTIME: self._fix_runtime_error,
            FailureType.DEPENDENCY: self._fix_dependency_error,
            FailureType.LOGIC: self._fix_logic_error,
        }

    def generate_fix(
        self,
        pattern: FailurePattern,
        source_code: str,
        error_context: Dict[str, Any],
    ) -> Optional[RefactorResult]:
        """
        Generate a fix for the given pattern and source code.

        Args:
            pattern: The detected failure pattern
            source_code: The source code to fix
            error_context: Context about the error (line, file, etc.)

        Returns:
            RefactorResult if fix generated, None otherwise
        """
        if pattern.confidence_score < self.min_confidence:
            logger.debug(
                f"Pattern confidence {pattern.confidence_score} below threshold {self.min_confidence}"
            )
            return None

        # Get appropriate handler
        handler = self._fix_handlers.get(pattern.pattern_type)
        if not handler:
            logger.debug(f"No handler for failure type: {pattern.pattern_type}")
            return None

        try:
            result = handler(pattern, source_code, error_context)
            if result and self.validate_syntax:
                if not self._validate_python_syntax(result.fixed_code):
                    logger.warning("Generated fix has invalid Python syntax")
                    result.warnings.append("Fix generated but syntax validation failed")
                    result.success = False

            return result

        except Exception as e:
            logger.error(f"Error generating fix: {e}")
            return None

    def _fix_syntax_error(
        self,
        pattern: FailurePattern,
        source_code: str,
        context: Dict[str, Any],
    ) -> Optional[RefactorResult]:
        """Fix syntax errors like missing parentheses, colons, etc."""
        lines = source_code.split('\n')
        error_line = context.get("line", 0) - 1  # 0-indexed

        if error_line < 0 or error_line >= len(lines):
            return None

        fixed_lines = lines.copy()
        line = lines[error_line]
        warnings = []

        # Missing colon at end of control statements
        if re.match(r'^\s*(if|elif|else|for|while|def|class|try|except|finally|with)\b.*[^:]$', line):
            fixed_lines[error_line] = line + ':'
            description = "Added missing colon"

        # Unbalanced parentheses
        elif line.count('(') > line.count(')'):
            fixed_lines[error_line] = line + ')' * (line.count('(') - line.count(')'))
            description = "Balanced parentheses"

        elif line.count(')') > line.count('('):
            # Find and remove extra closing paren
            diff = line.count(')') - line.count('(')
            for _ in range(diff):
                idx = line.rfind(')')
                if idx != -1:
                    line = line[:idx] + line[idx+1:]
            fixed_lines[error_line] = line
            description = "Removed extra parentheses"

        # Unbalanced brackets
        elif line.count('[') > line.count(']'):
            fixed_lines[error_line] = line + ']' * (line.count('[') - line.count(']'))
            description = "Balanced brackets"

        # Unbalanced braces
        elif line.count('{') > line.count('}'):
            fixed_lines[error_line] = line + '}' * (line.count('{') - line.count('}'))
            description = "Balanced braces"

        # Missing quotes
        elif line.count('"') % 2 == 1:
            fixed_lines[error_line] = line + '"'
            description = "Added missing quote"

        elif line.count("'") % 2 == 1:
            fixed_lines[error_line] = line + "'"
            description = "Added missing quote"

        else:
            return None

        fixed_code = '\n'.join(fixed_lines)
        diff = self._generate_diff(source_code, fixed_code)

        return RefactorResult(
            success=True,
            original_code=source_code,
            fixed_code=fixed_code,
            diff=diff,
            action_type=ActionType.PATCH,
            confidence=pattern.confidence_score,
            description=description,
            warnings=warnings,
        )

    def _fix_runtime_error(
        self,
        pattern: FailurePattern,
        source_code: str,
        context: Dict[str, Any],
    ) -> Optional[RefactorResult]:
        """Fix runtime errors like NameError, KeyError, etc."""
        lines = source_code.split('\n')
        error_line = context.get("line", 0) - 1
        error_message = context.get("error_message", "")
        warnings = []

        if error_line < 0 or error_line >= len(lines):
            return None

        fixed_lines = lines.copy()
        line = lines[error_line]

        # NameError - undefined variable (might be missing import)
        if "NameError" in error_message:
            match = re.search(r"name '(\w+)' is not defined", error_message)
            if match:
                name = match.group(1)
                # Check for common modules
                common_imports = {
                    "json": "import json",
                    "os": "import os",
                    "sys": "import sys",
                    "re": "import re",
                    "datetime": "from datetime import datetime",
                    "Path": "from pathlib import Path",
                    "Dict": "from typing import Dict",
                    "List": "from typing import List",
                    "Optional": "from typing import Optional",
                    "Any": "from typing import Any",
                }
                if name in common_imports:
                    # Add import at the top
                    import_stmt = common_imports[name]
                    fixed_lines.insert(0, import_stmt)
                    fixed_code = '\n'.join(fixed_lines)
                    diff = self._generate_diff(source_code, fixed_code)
                    return RefactorResult(
                        success=True,
                        original_code=source_code,
                        fixed_code=fixed_code,
                        diff=diff,
                        action_type=ActionType.PATCH,
                        confidence=pattern.confidence_score,
                        description=f"Added missing import for '{name}'",
                        warnings=warnings,
                    )

        # KeyError - add .get() with default
        if "KeyError" in error_message:
            # Find dictionary access pattern
            match = re.search(r"(\w+)\[(['\"])(\w+)\2\]", line)
            if match:
                dict_name, quote, key = match.groups()
                old_access = f"{dict_name}[{quote}{key}{quote}]"
                new_access = f"{dict_name}.get({quote}{key}{quote})"
                fixed_lines[error_line] = line.replace(old_access, new_access)
                fixed_code = '\n'.join(fixed_lines)
                diff = self._generate_diff(source_code, fixed_code)
                return RefactorResult(
                    success=True,
                    original_code=source_code,
                    fixed_code=fixed_code,
                    diff=diff,
                    action_type=ActionType.REFACTOR,
                    confidence=pattern.confidence_score,
                    description=f"Changed dictionary access to use .get() for '{key}'",
                    warnings=warnings,
                )

        # AttributeError on None - add null check
        if "AttributeError" in error_message and "NoneType" in error_message:
            # Find the attribute access
            match = re.search(r"(\w+)\.(\w+)", line)
            if match:
                obj_name, attr = match.groups()
                old_expr = f"{obj_name}.{attr}"
                new_expr = f"({obj_name}.{attr} if {obj_name} else None)"
                fixed_lines[error_line] = line.replace(old_expr, new_expr, 1)
                fixed_code = '\n'.join(fixed_lines)
                diff = self._generate_diff(source_code, fixed_code)
                return RefactorResult(
                    success=True,
                    original_code=source_code,
                    fixed_code=fixed_code,
                    diff=diff,
                    action_type=ActionType.REFACTOR,
                    confidence=pattern.confidence_score * 0.8,  # Lower confidence for this
                    description=f"Added null check for '{obj_name}'",
                    warnings=["Consider refactoring to handle None explicitly"],
                )

        # TypeError - type conversion issues
        if "TypeError" in error_message:
            if "unsupported operand" in error_message or "cannot be interpreted" in error_message:
                # Try to wrap with str() or int()
                warnings.append("Type conversion may need manual review")

        return None

    def _fix_dependency_error(
        self,
        pattern: FailurePattern,
        source_code: str,
        context: Dict[str, Any],
    ) -> Optional[RefactorResult]:
        """Fix dependency errors like ModuleNotFoundError."""
        error_message = context.get("error_message", "")

        # ModuleNotFoundError
        match = re.search(r"No module named '([\w.]+)'", error_message)
        if match:
            module_name = match.group(1)
            # We can't auto-install, but we can suggest try/except
            lines = source_code.split('\n')
            import_lines = []
            other_lines = []

            for line in lines:
                if line.strip().startswith(('import ', 'from ')):
                    import_lines.append(line)
                else:
                    other_lines.append(line)

            # Wrap imports in try/except
            if import_lines:
                wrapped = ["try:"] + ["    " + line for line in import_lines]
                wrapped.append(f"except ImportError as e:")
                wrapped.append(f"    raise ImportError(f\"Required module missing: {{e}}. Install with: pip install {module_name}\")")
                wrapped.append("")

                fixed_lines = wrapped + other_lines
                fixed_code = '\n'.join(fixed_lines)
                diff = self._generate_diff(source_code, fixed_code)

                return RefactorResult(
                    success=True,
                    original_code=source_code,
                    fixed_code=fixed_code,
                    diff=diff,
                    action_type=ActionType.REFACTOR,
                    confidence=pattern.confidence_score * 0.7,
                    description=f"Wrapped imports with try/except for missing '{module_name}'",
                    warnings=[f"Install missing module with: pip install {module_name}"],
                )

        return None

    def _fix_logic_error(
        self,
        pattern: FailurePattern,
        source_code: str,
        context: Dict[str, Any],
    ) -> Optional[RefactorResult]:
        """Fix logic errors (limited automatic fixing)."""
        # Logic errors are difficult to auto-fix
        # We can suggest debugging helpers
        error_message = context.get("error_message", "")
        error_line = context.get("line", 0) - 1

        if "AssertionError" in error_message:
            lines = source_code.split('\n')
            if error_line >= 0 and error_line < len(lines):
                line = lines[error_line]
                # Add more verbose assertion
                if line.strip().startswith("assert "):
                    expr = line.strip()[7:]
                    if "," not in expr:  # No message yet
                        fixed_lines = lines.copy()
                        fixed_lines[error_line] = f'{line}, f"Assertion failed: {expr} = {{{expr}}}"'
                        fixed_code = '\n'.join(fixed_lines)
                        diff = self._generate_diff(source_code, fixed_code)

                        return RefactorResult(
                            success=True,
                            original_code=source_code,
                            fixed_code=fixed_code,
                            diff=diff,
                            action_type=ActionType.PATCH,
                            confidence=pattern.confidence_score * 0.5,
                            description="Added verbose assertion message",
                            warnings=["Logic error requires manual review"],
                        )

        return None

    def _validate_python_syntax(self, code: str) -> bool:
        """Validate that Python code has correct syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _generate_diff(self, original: str, fixed: str) -> str:
        """Generate a unified diff between original and fixed code."""
        original_lines = original.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile="original",
            tofile="fixed",
        )
        return "".join(diff)

    def create_healing_action(
        self,
        pattern: FailurePattern,
        result: RefactorResult,
        target_file: str,
    ) -> HealingAction:
        """Create a HealingAction from a RefactorResult."""
        return HealingAction(
            action_id=f"act-{uuid.uuid4().hex[:8]}",
            pattern_id=pattern.pattern_id,
            action_type=result.action_type,
            code_diff=result.diff,
            target_file=target_file,
            success_rate=pattern.confidence_score,
        )

    def apply_action(
        self,
        action: HealingAction,
        source_code: str,
    ) -> Tuple[bool, str]:
        """
        Apply a healing action to source code.

        Args:
            action: The healing action to apply
            source_code: The source code to modify

        Returns:
            Tuple of (success, result_code_or_error)
        """
        try:
            # Parse the diff and apply changes
            # For simplicity, we store the fixed code in the diff
            # In production, you'd properly parse and apply the diff
            lines = action.code_diff.split('\n')
            new_lines = []

            for line in lines:
                if line.startswith('+') and not line.startswith('+++'):
                    new_lines.append(line[1:])
                elif line.startswith('-') and not line.startswith('---'):
                    continue  # Skip removed lines
                elif not line.startswith(('@@', '---', '+++')):
                    new_lines.append(line)

            result_code = '\n'.join(new_lines)

            if self.validate_syntax and not self._validate_python_syntax(result_code):
                return False, "Applied code has invalid syntax"

            action.mark_success()
            return True, result_code

        except Exception as e:
            action.mark_failure(str(e))
            return False, str(e)
