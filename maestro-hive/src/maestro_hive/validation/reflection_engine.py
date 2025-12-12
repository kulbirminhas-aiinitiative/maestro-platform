"""
Reflection Engine - Analyze Failures and Suggest Fixes (MD-3092)

AC-4: Failed tests trigger reflection + retry

This module implements the reflection component of the 
Generate → Test → Reflect → Refine loop.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .syntax_checker import SyntaxCheckResult
from .exceptions import ReflectionError


logger = logging.getLogger(__name__)


@dataclass
class ReflectionResult:
    """
    Result of a reflection/analysis operation.
    
    Attributes:
        analysis: Analysis of what went wrong
        root_cause: Identified root cause
        suggestions: List of suggestions to fix the issue
        confidence: Confidence level (0.0-1.0)
        fix_templates: Optional code fix templates
        requires_human: Whether human intervention is recommended
        reflection_time_ms: Time taken for reflection
    """
    analysis: str
    root_cause: str
    suggestions: List[str]
    confidence: float = 0.5
    fix_templates: List[str] = field(default_factory=list)
    requires_human: bool = False
    reflection_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "analysis": self.analysis,
            "root_cause": self.root_cause,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "fix_templates": self.fix_templates,
            "requires_human": self.requires_human,
            "reflection_time_ms": self.reflection_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class ReflectionEngine:
    """
    Reflection engine for analyzing failures and suggesting fixes.
    
    Implements AC-4: Failed tests trigger reflection + retry.
    
    The reflection engine:
    1. Analyzes error messages and test outputs
    2. Identifies root causes using pattern matching
    3. Suggests fixes based on common error patterns
    4. Provides fix templates when applicable
    
    Example:
        >>> engine = ReflectionEngine()
        >>> result = engine.reflect_on_syntax_error(syntax_result)
        >>> print(result.suggestions)
    """
    
    # Error patterns and their analyses
    ERROR_PATTERNS: Dict[str, Dict[str, Any]] = {
        r"SyntaxError.*unexpected EOF": {
            "root_cause": "Incomplete code structure - missing closing brackets or statements",
            "suggestions": [
                "Add missing closing parentheses, brackets, or braces",
                "Complete function/class definitions",
                "Check for unclosed string literals"
            ],
            "confidence": 0.8
        },
        r"IndentationError": {
            "root_cause": "Inconsistent or incorrect indentation",
            "suggestions": [
                "Use consistent 4-space indentation",
                "Don't mix tabs and spaces",
                "Ensure all blocks after : are indented"
            ],
            "confidence": 0.9
        },
        r"NameError.*not defined": {
            "root_cause": "Reference to undefined variable or function",
            "suggestions": [
                "Check spelling of variable/function names",
                "Ensure the variable is defined before use",
                "Check import statements"
            ],
            "confidence": 0.85
        },
        r"TypeError.*argument": {
            "root_cause": "Function called with wrong number or type of arguments",
            "suggestions": [
                "Check function signature and call arguments",
                "Verify required vs optional parameters",
                "Check for type mismatches"
            ],
            "confidence": 0.75
        },
        r"AttributeError": {
            "root_cause": "Accessing non-existent attribute or method",
            "suggestions": [
                "Check that the object has the expected type",
                "Verify method/attribute names",
                "Add null checks if needed"
            ],
            "confidence": 0.7
        },
        r"ImportError|ModuleNotFoundError": {
            "root_cause": "Missing or incorrect import",
            "suggestions": [
                "Install the missing package",
                "Check the import path",
                "Verify module name spelling"
            ],
            "confidence": 0.85
        },
        r"KeyError": {
            "root_cause": "Dictionary key doesn't exist",
            "suggestions": [
                "Use .get() method with default value",
                "Check key spelling",
                "Ensure key exists before access"
            ],
            "confidence": 0.8
        },
        r"AssertionError": {
            "root_cause": "Test assertion failed - expected != actual",
            "suggestions": [
                "Review the expected vs actual values",
                "Check test setup and fixtures",
                "Verify the implementation logic"
            ],
            "confidence": 0.7
        }
    }
    
    def __init__(self, max_suggestions: int = 5):
        """
        Initialize the reflection engine.
        
        Args:
            max_suggestions: Maximum number of suggestions to return
        """
        self.max_suggestions = max_suggestions
        self._history: List[ReflectionResult] = []
    
    def reflect_on_syntax_error(
        self,
        result: SyntaxCheckResult
    ) -> ReflectionResult:
        """
        Reflect on a syntax check failure.
        
        Args:
            result: SyntaxCheckResult from syntax checker
        
        Returns:
            ReflectionResult with analysis and suggestions
        """
        import time
        start_time = time.perf_counter()
        
        if result.valid:
            return ReflectionResult(
                analysis="No syntax errors found",
                root_cause="N/A - code is valid",
                suggestions=[],
                confidence=1.0,
                reflection_time_ms=(time.perf_counter() - start_time) * 1000
            )
        
        # Analyze error message
        error_msg = result.error_message or "Unknown syntax error"
        analysis = f"Syntax error at {result.filename}:{result.error_line}: {error_msg}"
        
        # Find matching patterns
        root_cause = "Unknown syntax issue"
        suggestions = list(result.suggestions)  # Start with checker suggestions
        confidence = 0.5
        
        for pattern, data in self.ERROR_PATTERNS.items():
            if re.search(pattern, error_msg, re.IGNORECASE):
                root_cause = data["root_cause"]
                suggestions.extend(data["suggestions"])
                confidence = data["confidence"]
                break
        
        # Generate fix templates
        fix_templates = self._generate_fix_templates(result)
        
        # Deduplicate and limit suggestions
        suggestions = list(dict.fromkeys(suggestions))[:self.max_suggestions]
        
        reflection_time = (time.perf_counter() - start_time) * 1000
        
        result = ReflectionResult(
            analysis=analysis,
            root_cause=root_cause,
            suggestions=suggestions,
            confidence=confidence,
            fix_templates=fix_templates,
            requires_human=confidence < 0.5,
            reflection_time_ms=reflection_time
        )
        
        self._history.append(result)
        logger.info(f"Reflection complete: {root_cause} (confidence: {confidence:.2f})")
        
        return result
    
    def reflect_on_test_failure(
        self,
        test_output: str,
        failed_tests: List[str],
        code: str
    ) -> ReflectionResult:
        """
        Reflect on test execution failures.
        
        Implements AC-4: Failed tests trigger reflection + retry.
        
        Args:
            test_output: Raw output from test execution
            failed_tests: List of failed test names
            code: The code being tested
        
        Returns:
            ReflectionResult with analysis and suggestions
        """
        import time
        start_time = time.perf_counter()
        
        analysis_parts = [f"Test failure analysis: {len(failed_tests)} test(s) failed"]
        suggestions = []
        confidence = 0.5
        root_cause = "Test assertions did not pass"
        
        # Analyze test output
        for pattern, data in self.ERROR_PATTERNS.items():
            if re.search(pattern, test_output, re.IGNORECASE):
                root_cause = data["root_cause"]
                suggestions.extend(data["suggestions"])
                confidence = max(confidence, data["confidence"] - 0.1)
                analysis_parts.append(f"Detected pattern: {pattern}")
        
        # Look for assertion errors
        assertion_matches = re.findall(
            r"assert(?:ion)?.*(?:Error|Failed).*?:(.*?)(?:\n|$)",
            test_output,
            re.IGNORECASE | re.DOTALL
        )
        if assertion_matches:
            analysis_parts.append(f"Found {len(assertion_matches)} assertion failures")
            suggestions.append("Review assertion messages for expected vs actual values")
        
        # Look for specific failed tests
        for test_name in failed_tests[:3]:
            analysis_parts.append(f"Failed: {test_name}")
        
        # Deduplicate suggestions
        suggestions = list(dict.fromkeys(suggestions))[:self.max_suggestions]
        
        if not suggestions:
            suggestions = [
                "Review the test assertions and expected values",
                "Check that test fixtures are set up correctly",
                "Verify the implementation matches the requirements"
            ]
        
        reflection_time = (time.perf_counter() - start_time) * 1000
        
        result = ReflectionResult(
            analysis="\n".join(analysis_parts),
            root_cause=root_cause,
            suggestions=suggestions,
            confidence=confidence,
            requires_human=len(failed_tests) > 3 or confidence < 0.4,
            reflection_time_ms=reflection_time
        )
        
        self._history.append(result)
        return result
    
    def _generate_fix_templates(
        self,
        result: SyntaxCheckResult
    ) -> List[str]:
        """Generate code fix templates based on the error."""
        templates = []
        error_msg = result.error_message or ""
        
        if "expected ':'" in error_msg.lower():
            templates.append("# Add colon at end of line:\n# def function_name():")
        
        if "expected an indented block" in error_msg.lower():
            templates.append("# Add indented block:\n#     pass  # or actual implementation")
        
        if "unexpected eof" in error_msg.lower():
            templates.append("# Complete the structure:\n# )")  # closing bracket
        
        return templates
    
    def get_history(self) -> List[ReflectionResult]:
        """Get reflection history."""
        return list(self._history)
    
    def clear_history(self) -> None:
        """Clear reflection history."""
        self._history.clear()
