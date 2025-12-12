"""
Syntax Checker - AST-based Python Syntax Validation (MD-3092)

AC-1: ast.parse() runs on all generated Python files
AC-2: Syntax errors trigger internal retry (max 3)

This module provides syntax validation using Python's AST module.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import SyntaxValidationError


logger = logging.getLogger(__name__)


@dataclass
class SyntaxCheckResult:
    """
    Result of a syntax check operation.
    
    Attributes:
        valid: Whether the code has valid syntax
        filename: Name of the file being checked
        error_message: Error message if invalid
        error_line: Line number of the error
        error_column: Column offset of the error
        code_snippet: Snippet of code around the error
        suggestions: List of suggestions to fix the error
        check_time_ms: Time taken for the check in milliseconds
    """
    valid: bool
    filename: str
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    error_column: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    check_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "valid": self.valid,
            "filename": self.filename,
            "error_message": self.error_message,
            "error_line": self.error_line,
            "error_column": self.error_column,
            "code_snippet": self.code_snippet,
            "suggestions": self.suggestions,
            "check_time_ms": self.check_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class SyntaxChecker:
    """
    AST-based syntax checker for Python code.
    
    Implements AC-1: ast.parse() runs on all generated Python files.
    
    Features:
        - Fast AST-based syntax validation
        - Detailed error location reporting
        - Code snippet extraction around errors
        - Suggestions for common syntax errors
    
    Example:
        >>> checker = SyntaxChecker()
        >>> result = checker.check("def foo():\n    return 42")
        >>> print(result.valid)  # True
        >>> 
        >>> result = checker.check("def foo(\n    return 42")
        >>> print(result.valid)  # False
        >>> print(result.error_message)
    """
    
    # Common syntax error patterns and suggestions
    COMMON_ERRORS: Dict[str, List[str]] = {
        "unexpected EOF": [
            "Check for missing closing brackets: ), ], }",
            "Check for unclosed string literals",
            "Check for incomplete function/class definitions"
        ],
        "invalid syntax": [
            "Check for missing colons after def/if/for/while/class",
            "Check for incorrect indentation",
            "Check for mismatched parentheses or brackets"
        ],
        "expected ':'": [
            "Add a colon at the end of the statement",
            "This usually occurs after def, if, for, while, class, try, except"
        ],
        "expected an indented block": [
            "Add indentation (4 spaces) after the colon",
            "Make sure the block is not empty - use 'pass' if needed"
        ],
        "unindent does not match": [
            "Ensure consistent indentation (use 4 spaces)",
            "Don't mix tabs and spaces"
        ],
        "'return' outside function": [
            "The return statement must be inside a function definition",
            "Check indentation - return may be misaligned"
        ],
        "cannot assign to": [
            "Cannot assign to function calls or literals",
            "Check for = vs == confusion in conditions"
        ]
    }
    
    def __init__(self, max_snippet_lines: int = 5):
        """
        Initialize the syntax checker.
        
        Args:
            max_snippet_lines: Maximum lines to include in code snippets
        """
        self.max_snippet_lines = max_snippet_lines
    
    def check(
        self,
        code: str,
        filename: str = "<generated>",
        mode: str = "exec"
    ) -> SyntaxCheckResult:
        """
        Check Python code for syntax errors.
        
        Implements AC-1: ast.parse() validation.
        
        Args:
            code: Python source code to check
            filename: Filename for error reporting
            mode: Compilation mode ('exec', 'eval', 'single')
        
        Returns:
            SyntaxCheckResult with validation details
        """
        import time
        start_time = time.perf_counter()
        
        try:
            ast.parse(code, filename=filename, mode=mode)
            
            check_time = (time.perf_counter() - start_time) * 1000
            
            logger.debug(f"Syntax check PASSED for {filename}")
            
            return SyntaxCheckResult(
                valid=True,
                filename=filename,
                check_time_ms=check_time
            )
            
        except SyntaxError as e:
            check_time = (time.perf_counter() - start_time) * 1000
            
            # Extract error details
            error_line = e.lineno
            error_column = e.offset
            error_message = str(e.msg) if hasattr(e, 'msg') else str(e)
            
            # Extract code snippet
            snippet = self._extract_snippet(code, error_line)
            
            # Get suggestions
            suggestions = self._get_suggestions(error_message)
            
            logger.warning(
                f"Syntax error in {filename} at line {error_line}: {error_message}"
            )
            
            return SyntaxCheckResult(
                valid=False,
                filename=filename,
                error_message=error_message,
                error_line=error_line,
                error_column=error_column,
                code_snippet=snippet,
                suggestions=suggestions,
                check_time_ms=check_time
            )
    
    def check_file(self, filepath: str) -> SyntaxCheckResult:
        """
        Check a Python file for syntax errors.
        
        Args:
            filepath: Path to the Python file
        
        Returns:
            SyntaxCheckResult with validation details
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            return self.check(code, filename=filepath)
        except FileNotFoundError:
            return SyntaxCheckResult(
                valid=False,
                filename=filepath,
                error_message=f"File not found: {filepath}",
                suggestions=["Verify the file path is correct"]
            )
        except IOError as e:
            return SyntaxCheckResult(
                valid=False,
                filename=filepath,
                error_message=f"Cannot read file: {e}",
                suggestions=["Check file permissions"]
            )
    
    def check_multiple(
        self,
        code_files: Dict[str, str]
    ) -> Dict[str, SyntaxCheckResult]:
        """
        Check multiple code snippets for syntax errors.
        
        Args:
            code_files: Dict mapping filename to code content
        
        Returns:
            Dict mapping filename to SyntaxCheckResult
        """
        results = {}
        for filename, code in code_files.items():
            results[filename] = self.check(code, filename=filename)
        return results
    
    def _extract_snippet(
        self,
        code: str,
        error_line: Optional[int]
    ) -> Optional[str]:
        """Extract code snippet around the error line."""
        if error_line is None:
            return None
        
        lines = code.split('\n')
        total_lines = len(lines)
        
        # Calculate snippet range
        half_window = self.max_snippet_lines // 2
        start = max(0, error_line - 1 - half_window)
        end = min(total_lines, error_line + half_window)
        
        # Build snippet with line numbers
        snippet_lines = []
        for i in range(start, end):
            line_num = i + 1
            marker = ">>>" if line_num == error_line else "   "
            snippet_lines.append(f"{marker} {line_num:4d} | {lines[i]}")
        
        return '\n'.join(snippet_lines)
    
    def _get_suggestions(self, error_message: str) -> List[str]:
        """Get suggestions based on the error message."""
        suggestions = []
        error_lower = error_message.lower()
        
        for pattern, pattern_suggestions in self.COMMON_ERRORS.items():
            if pattern.lower() in error_lower:
                suggestions.extend(pattern_suggestions)
        
        if not suggestions:
            suggestions = [
                "Review the syntax near the reported line",
                "Check for missing or extra punctuation",
                "Verify proper indentation"
            ]
        
        return suggestions


def validate_python_syntax(code: str, filename: str = "<generated>") -> SyntaxCheckResult:
    """
    Convenience function for quick syntax validation.
    
    Args:
        code: Python source code to validate
        filename: Filename for error reporting
    
    Returns:
        SyntaxCheckResult with validation details
    """
    checker = SyntaxChecker()
    return checker.check(code, filename)
