"""
Tests for JIT Validator (MD-3092)

Covers all acceptance criteria:
- AC-1: ast.parse() runs on all generated Python files
- AC-2: Syntax errors trigger internal retry (max 3)
- AC-3: Personas can execute tests on generated code
- AC-4: Failed tests trigger reflection + retry
- AC-5: HelpNeeded raised after exhausting retries
"""

import pytest
from maestro_hive.validation import (
    JITValidator,
    ValidationResult,
    SyntaxChecker,
    SyntaxCheckResult,
    ReflectionEngine,
    ReflectionResult,
    TestRunner,
    TestResult,
    HelpNeeded,
    ValidationError,
)


class TestSyntaxChecker:
    """Tests for SyntaxChecker - AC-1 implementation."""

    def test_valid_python_code(self):
        """AC-1: Valid Python code passes syntax check."""
        checker = SyntaxChecker()
        result = checker.check("def foo():\n    return 42")
        
        assert result.valid is True
        assert result.error_message is None
        assert result.error_line is None

    def test_simple_function(self):
        """AC-1: Simple function definition validates correctly."""
        checker = SyntaxChecker()
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
        result = checker.check(code)
        assert result.valid is True

    def test_class_definition(self):
        """AC-1: Class definitions validate correctly."""
        checker = SyntaxChecker()
        code = """
class MyClass:
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        return self.value
"""
        result = checker.check(code)
        assert result.valid is True

    def test_syntax_error_missing_colon(self):
        """AC-1: Missing colon detected."""
        checker = SyntaxChecker()
        result = checker.check("def foo()\n    return 42")
        
        assert result.valid is False
        assert result.error_line is not None
        assert "expected ':'" in result.error_message.lower() or "invalid syntax" in result.error_message.lower()

    def test_syntax_error_unmatched_parenthesis(self):
        """AC-1: Unmatched parenthesis detected."""
        checker = SyntaxChecker()
        result = checker.check("print(foo(")
        
        assert result.valid is False
        assert result.error_message is not None

    def test_syntax_error_indentation(self):
        """AC-1: Indentation error detected."""
        checker = SyntaxChecker()
        result = checker.check("def foo():\nreturn 42")
        
        assert result.valid is False
        assert "indent" in result.error_message.lower()

    def test_code_snippet_extraction(self):
        """AC-1: Code snippet is extracted around error."""
        checker = SyntaxChecker()
        code = """def foo():
    x = 1
    y = 2
    return x +
    z = 3
"""
        result = checker.check(code)
        
        assert result.valid is False
        assert result.code_snippet is not None
        assert ">>>" in result.code_snippet  # Error marker

    def test_suggestions_provided(self):
        """AC-1: Suggestions provided for common errors."""
        checker = SyntaxChecker()
        result = checker.check("def foo()\n    return 42")
        
        assert result.valid is False
        assert len(result.suggestions) > 0


class TestReflectionEngine:
    """Tests for ReflectionEngine - AC-4 implementation."""

    def test_reflect_on_syntax_error(self):
        """AC-4: Reflection provides analysis for syntax errors."""
        engine = ReflectionEngine()
        
        syntax_result = SyntaxCheckResult(
            valid=False,
            filename="test.py",
            error_message="unexpected EOF while parsing",
            error_line=5
        )
        
        reflection = engine.reflect_on_syntax_error(syntax_result)

        assert reflection.analysis is not None
        assert reflection.root_cause is not None
        # Note: suggestions come from pattern matching or fix_templates
        assert reflection.confidence > 0
        assert len(reflection.fix_templates) > 0 or reflection.root_cause != "Unknown syntax issue"

    def test_reflect_on_valid_code(self):
        """AC-4: No reflection needed for valid code."""
        engine = ReflectionEngine()
        
        syntax_result = SyntaxCheckResult(valid=True, filename="test.py")
        reflection = engine.reflect_on_syntax_error(syntax_result)
        
        assert "No syntax errors" in reflection.analysis
        assert reflection.confidence == 1.0

    def test_reflect_on_test_failure(self):
        """AC-4: Reflection provides analysis for test failures."""
        engine = ReflectionEngine()
        
        reflection = engine.reflect_on_test_failure(
            test_output="AssertionError: expected 42, got 41",
            failed_tests=["test_add"],
            code="def add(a, b): return a + b - 1"
        )
        
        assert reflection.analysis is not None
        assert "test" in reflection.analysis.lower() or "fail" in reflection.analysis.lower()
        assert len(reflection.suggestions) > 0

    def test_reflection_history(self):
        """AC-4: Reflection history is maintained."""
        engine = ReflectionEngine()
        
        syntax_result = SyntaxCheckResult(
            valid=False,
            filename="test.py",
            error_message="invalid syntax"
        )
        
        engine.reflect_on_syntax_error(syntax_result)
        engine.reflect_on_syntax_error(syntax_result)
        
        history = engine.get_history()
        assert len(history) == 2


class TestJITValidator:
    """Tests for JITValidator - orchestrates all ACs."""

    def test_validate_valid_code(self):
        """AC-1: Valid code passes validation."""
        validator = JITValidator(run_tests=False)
        result = validator.validate_code("def foo(): return 42")
        
        assert result.valid is True
        assert result.syntax_result is not None
        assert result.syntax_result.valid is True

    def test_validate_invalid_syntax(self):
        """AC-1: Invalid syntax fails validation."""
        validator = JITValidator(run_tests=False)
        result = validator.validate_code("def foo(\n    return 42")
        
        assert result.valid is False
        assert result.syntax_result is not None
        assert result.syntax_result.valid is False
        assert result.reflection_result is not None

    def test_max_attempts_default(self):
        """AC-2: Default max_attempts is 3."""
        validator = JITValidator()
        assert validator.max_attempts == 3

    def test_max_attempts_custom(self):
        """AC-2: Custom max_attempts can be set."""
        validator = JITValidator(max_attempts=5)
        assert validator.max_attempts == 5

    def test_help_needed_after_retries(self):
        """AC-5: HelpNeeded raised after exhausting retries."""
        validator = JITValidator(max_attempts=2, run_tests=False)
        
        # Code that cannot be fixed by simple refine
        bad_code = "def foo(\n    return"
        
        with pytest.raises(HelpNeeded) as exc_info:
            validator.validate_with_retry(
                code=bad_code,
                persona_id="test_persona"
            )
        
        assert exc_info.value.persona_id == "test_persona"
        assert exc_info.value.attempts == 2
        assert exc_info.value.max_attempts == 2

    def test_help_needed_context(self):
        """AC-5: HelpNeeded includes context information."""
        validator = JITValidator(max_attempts=1, run_tests=False)
        
        with pytest.raises(HelpNeeded) as exc_info:
            validator.validate_with_retry(
                code="def broken(",
                persona_id="test_persona"
            )
        
        context = exc_info.value.context
        assert context.last_code is not None
        assert len(context.validation_history) > 0

    def test_retry_with_refine_callback(self):
        """AC-2: Retry uses refine callback to fix code."""
        validator = JITValidator(max_attempts=3, run_tests=False)
        
        # Start with broken code
        broken_code = "def foo()\n    return 42"
        
        # Refine callback that fixes the colon
        def fix_code(code, reflection):
            return "def foo():\n    return 42"
        
        # Should pass on second attempt after fix
        result = validator.validate_with_retry(
            code=broken_code,
            refine_callback=fix_code,
            persona_id="test_persona"
        )
        
        assert result.valid is True
        assert result.attempts == 2  # Passed on second try

    def test_validation_result_to_dict(self):
        """Validation result can be serialized."""
        validator = JITValidator(run_tests=False)
        result = validator.validate_code("x = 1")
        
        data = result.to_dict()
        assert "valid" in data
        assert "syntax_result" in data
        assert "timestamp" in data


class TestTestRunner:
    """Tests for TestRunner - AC-3 implementation."""

    def test_run_syntax_test_valid(self):
        """AC-3: Syntax test passes for valid code."""
        runner = TestRunner()
        result = runner.run_syntax_test("def foo(): return 42")
        
        assert result.success is True
        assert result.tests_passed == 1

    def test_run_syntax_test_invalid(self):
        """AC-3: Syntax test fails for invalid code."""
        runner = TestRunner()
        result = runner.run_syntax_test("def foo(")
        
        assert result.success is False
        assert result.tests_failed == 1
        assert "syntax_validation" in result.failed_tests

    def test_test_result_to_dict(self):
        """AC-3: Test result can be serialized."""
        runner = TestRunner()
        result = runner.run_syntax_test("x = 1")
        
        data = result.to_dict()
        assert "success" in data
        assert "tests_total" in data
        assert "tests_passed" in data


class TestHelpNeededException:
    """Tests for HelpNeeded exception - AC-5 implementation."""

    def test_help_needed_creation(self):
        """AC-5: HelpNeeded exception created correctly."""
        exc = HelpNeeded(
            persona_id="backend_developer",
            task="Generate API endpoint",
            attempts=3,
            max_attempts=3,
            last_error="Syntax error at line 5"
        )
        
        assert exc.persona_id == "backend_developer"
        assert exc.task == "Generate API endpoint"
        assert exc.attempts == 3
        assert exc.max_attempts == 3
        assert "Syntax error" in exc.last_error

    def test_help_needed_message(self):
        """AC-5: HelpNeeded has informative message."""
        exc = HelpNeeded(
            persona_id="test",
            task="test task",
            attempts=3,
            max_attempts=3,
            last_error="test error"
        )
        
        message = str(exc)
        assert "test" in message
        assert "3" in message
        assert "help" in message.lower()

    def test_help_needed_to_dict(self):
        """AC-5: HelpNeeded can be serialized."""
        exc = HelpNeeded(
            persona_id="test",
            task="test task",
            attempts=3,
            max_attempts=3,
            last_error="test error"
        )
        
        data = exc.to_dict()
        assert data["persona_id"] == "test"
        assert data["task"] == "test task"
        assert data["attempts"] == 3

    def test_help_needed_escalation_summary(self):
        """AC-5: HelpNeeded generates escalation summary."""
        exc = HelpNeeded(
            persona_id="backend",
            task="fix bug",
            attempts=3,
            max_attempts=3,
            last_error="Could not resolve"
        )
        
        summary = exc.get_escalation_summary()
        assert "HELP NEEDED" in summary
        assert "backend" in summary
        assert "3/3" in summary
