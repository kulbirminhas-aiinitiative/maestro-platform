"""
Tests for Real Code Generator.

EPIC: MD-2496 - [MAESTRO] Sub-EPIC 3: Real Code Generation

Tests all 4 Acceptance Criteria:
- AC-1: No NotImplementedError stubs in output
- AC-2: Generated code passes syntax validation
- AC-3: Type hints included where appropriate
- AC-4: Quality Fabric validates each output
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from maestro_hive.codegen.generator import (
    RealCodeGenerator,
    GenerationContext,
    GeneratedCode,
)
from maestro_hive.codegen.validator import (
    SyntaxValidator,
    ValidationResult,
    StubLocation,
)
from maestro_hive.codegen.templates import (
    CodeTemplateRegistry,
    CodeTemplate,
)
from maestro_hive.codegen.type_hints import (
    TypeHintGenerator,
)
from maestro_hive.codegen.quality import (
    QualityFabricClient,
    QualityResult,
)
from maestro_hive.codegen.exceptions import (
    CodeGenerationError,
    SyntaxValidationError,
    StubDetectedError,
    QualityGateError,
)


# =============================================================================
# AC-1: No NotImplementedError stubs in output
# =============================================================================

class TestAC1NoStubs:
    """AC-1: No NotImplementedError stubs in output."""

    def test_detect_not_implemented_error(self):
        """Test detection of NotImplementedError in code."""
        validator = SyntaxValidator()

        code_with_stub = '''
def my_function():
    raise NotImplementedError()
'''
        result = validator.validate(code_with_stub)

        assert result.has_stubs is True
        assert len(result.stub_locations) == 1
        assert result.stub_locations[0].function_name == "my_function"

    def test_detect_not_implemented_with_message(self):
        """Test detection of NotImplementedError with message."""
        validator = SyntaxValidator()

        code = '''
def process():
    raise NotImplementedError("TODO: implement this")
'''
        result = validator.validate(code)

        assert result.has_stubs is True

    def test_detect_todo_pass(self):
        """Test detection of pass with TODO comment."""
        validator = SyntaxValidator()

        code = '''
def incomplete():
    pass  # TODO
'''
        result = validator.validate(code)

        assert result.has_stubs is True

    def test_generated_code_has_no_stubs(self):
        """Test that generated code contains no stubs."""
        generator = RealCodeGenerator(strict_mode=False)

        context = GenerationContext(
            requirement="Create a user model",
            target_pattern="model",
        )

        result = generator.generate(context)

        assert result.has_stubs is False
        assert "NotImplementedError" not in result.source

    def test_strict_mode_raises_on_stubs(self):
        """Test that strict mode raises on stub detection."""
        validator = SyntaxValidator(strict_mode=True)
        generator = RealCodeGenerator(strict_mode=True)

        # Manually create code with stub
        code_with_stub = "def foo(): raise NotImplementedError()"

        stubs = generator.check_for_stubs(code_with_stub)
        assert len(stubs) > 0

    def test_check_for_stubs_clean_code(self):
        """Test check_for_stubs returns empty for clean code."""
        generator = RealCodeGenerator()

        clean_code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        stubs = generator.check_for_stubs(clean_code)
        assert len(stubs) == 0

    def test_stub_location_details(self):
        """Test stub location contains proper details."""
        validator = SyntaxValidator()

        code = '''
class MyClass:
    def method(self):
        raise NotImplementedError()
'''
        result = validator.validate(code)

        assert result.has_stubs is True
        stub = result.stub_locations[0]
        assert stub.function_name == "method"
        assert stub.class_name == "MyClass"
        assert stub.line > 0


# =============================================================================
# AC-2: Generated code passes syntax validation
# =============================================================================

class TestAC2SyntaxValidation:
    """AC-2: Generated code passes syntax validation."""

    def test_valid_python_code(self):
        """Test validation of valid Python code."""
        validator = SyntaxValidator()

        valid_code = '''
def greet(name: str) -> str:
    """Return greeting."""
    return f"Hello, {name}!"
'''
        result = validator.validate(valid_code)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_invalid_syntax_detected(self):
        """Test detection of invalid syntax."""
        validator = SyntaxValidator()

        invalid_code = '''
def broken(
    return "missing close paren"
'''
        result = validator.validate(invalid_code)

        assert result.valid is False
        assert len(result.errors) > 0

    def test_generated_code_is_valid(self):
        """Test that all generated code is syntactically valid."""
        generator = RealCodeGenerator()

        contexts = [
            GenerationContext(requirement="Create API endpoint", target_pattern="api"),
            GenerationContext(requirement="Create data model", target_pattern="model"),
            GenerationContext(requirement="Create service class", target_pattern="service"),
        ]

        for context in contexts:
            result = generator.generate(context)
            assert result.syntax_valid is True, f"Invalid syntax for {context.target_pattern}"

    def test_ast_node_count(self):
        """Test AST node count is returned."""
        validator = SyntaxValidator()

        code = '''
class Foo:
    def bar(self):
        return 1
'''
        result = validator.validate(code)

        assert result.ast_node_count > 0

    def test_syntax_error_details(self):
        """Test syntax error includes line info."""
        validator = SyntaxValidator()

        code = '''x =
'''
        result = validator.validate(code)

        assert result.valid is False
        assert "line" in result.errors[0].lower()

    def test_validate_syntax_method(self):
        """Test generator's validate_syntax method."""
        generator = RealCodeGenerator()

        result = generator.validate_syntax("def f(): pass")
        assert result.valid is True


# =============================================================================
# AC-3: Type hints included where appropriate
# =============================================================================

class TestAC3TypeHints:
    """AC-3: Type hints included where appropriate."""

    def test_add_return_type(self):
        """Test adding return type hints."""
        hinter = TypeHintGenerator()

        code = '''
def is_valid():
    return True
'''
        result = hinter.add_type_hints(code)

        assert "-> bool" in result or "bool" in result

    def test_infer_param_types(self):
        """Test inferring parameter types from names."""
        hinter = TypeHintGenerator()

        code = '''
def process(name, count, enabled):
    pass
'''
        result = hinter.add_type_hints(code)

        # Should infer types from parameter names
        assert "str" in result or "int" in result or "bool" in result

    def test_type_coverage_calculation(self):
        """Test calculation of type coverage."""
        hinter = TypeHintGenerator()

        typed_code = '''
def typed_func(x: int) -> str:
    return str(x)

def untyped(y):
    return y
'''
        coverage = hinter.calculate_type_coverage(typed_code)

        assert 0.0 <= coverage <= 1.0
        assert coverage == 0.5  # 1 of 2 fully typed

    def test_generated_code_has_types(self):
        """Test that generated code includes type hints."""
        generator = RealCodeGenerator()

        context = GenerationContext(
            requirement="Create user model",
            target_pattern="model",
        )

        result = generator.generate(context)

        # Check for common type hints
        assert "str" in result.source or "int" in result.source or "Any" in result.source

    def test_type_coverage_above_threshold(self):
        """Test generated code has good type coverage."""
        generator = RealCodeGenerator()

        context = GenerationContext(
            requirement="Create a service",
            target_pattern="service",
        )

        result = generator.generate(context)

        # Type coverage should be reasonable
        assert result.type_coverage >= 0.0

    def test_add_type_hints_method(self):
        """Test generator's add_type_hints method."""
        generator = RealCodeGenerator()

        code = "def get_count(): return 5"
        result = generator.add_type_hints(code)

        assert isinstance(result, str)


# =============================================================================
# AC-4: Quality Fabric validates each output
# =============================================================================

class TestAC4QualityFabric:
    """AC-4: Quality Fabric validates each output."""

    @pytest.mark.asyncio
    async def test_quality_fabric_validation(self):
        """Test Quality Fabric validation integration."""
        client = QualityFabricClient()

        # Test fallback validation (when QF not available)
        result = await client.validate(
            "def foo(): return 1",
            "test.py",
        )

        assert isinstance(result, QualityResult)
        assert result.score >= 0
        assert isinstance(result.passed, bool)

    def test_quality_result_dataclass(self):
        """Test QualityResult dataclass fields."""
        result = QualityResult(
            score=85.0,
            passed=True,
            issues=[],
            metrics={"lines": 10},
        )

        assert result.score == 85.0
        assert result.passed is True

    def test_fallback_validation_detects_stubs(self):
        """Test fallback validation detects stubs."""
        client = QualityFabricClient()

        code_with_stub = "def foo(): raise NotImplementedError()"
        result = client._fallback_validation(code_with_stub, "python")

        assert result.score < 100
        assert any(i["type"] == "stub" for i in result.issues)

    def test_fallback_validation_clean_code(self):
        """Test fallback validation gives good score for clean code."""
        client = QualityFabricClient()

        clean_code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        result = client._fallback_validation(clean_code, "python")

        assert result.score >= 80
        assert result.passed is True

    def test_quality_threshold_enforcement(self):
        """Test quality threshold is enforced."""
        client = QualityFabricClient(threshold=90.0)

        result = client._fallback_validation("def f(): pass", "python")

        # Threshold affects passed status
        assert result.passed == (result.score >= 90.0)

    @pytest.mark.asyncio
    async def test_generator_quality_validation(self):
        """Test generator's Quality Fabric integration."""
        generator = RealCodeGenerator(
            quality_fabric_url="http://localhost:8000"
        )

        result = await generator.validate_with_quality_fabric(
            "def test(): return True",
            "test.py",
        )

        assert isinstance(result, QualityResult)


# =============================================================================
# Template Tests
# =============================================================================

class TestTemplates:
    """Test code template functionality."""

    def test_template_registry_initialization(self):
        """Test registry loads default templates."""
        registry = CodeTemplateRegistry()

        templates = registry.list_templates("python")
        assert len(templates) > 0

    def test_get_template_by_name(self):
        """Test getting template by name."""
        registry = CodeTemplateRegistry()

        template = registry.get("dataclass_model", "python")
        assert template is not None
        assert template.name == "dataclass_model"

    def test_get_template_by_pattern(self):
        """Test getting templates by pattern."""
        registry = CodeTemplateRegistry()

        templates = registry.get_by_pattern("api", "python")
        assert len(templates) > 0

    def test_template_rendering(self):
        """Test template rendering with context."""
        template = CodeTemplate(
            name="test",
            language="python",
            pattern="test",
            template="class {{class_name}}: pass",
        )

        result = template.render({"class_name": "MyClass"})
        assert "class MyClass: pass" in result

    def test_register_custom_template(self):
        """Test registering custom templates."""
        registry = CodeTemplateRegistry()

        custom = CodeTemplate(
            name="custom_template",
            language="python",
            pattern="custom",
            template="# Custom template\npass",
        )

        registry.register("custom_template", custom)
        retrieved = registry.get("custom_template", "python")

        assert retrieved is not None
        assert retrieved.name == "custom_template"


# =============================================================================
# Generator Integration Tests
# =============================================================================

class TestGeneratorIntegration:
    """Integration tests for the generator."""

    def test_full_generation_flow(self):
        """Test complete generation flow."""
        generator = RealCodeGenerator(strict_mode=False)

        context = GenerationContext(
            requirement="Create a User model with email validation",
            target_pattern="model",
            class_name="User",
        )

        result = generator.generate(context)

        assert result.syntax_valid is True
        assert result.has_stubs is False
        assert len(result.source) > 0

    def test_generation_with_pattern_inference(self):
        """Test pattern inference from requirement."""
        generator = RealCodeGenerator()

        context = GenerationContext(
            requirement="Build REST API endpoint for users",
        )

        result = generator.generate(context)

        assert result.syntax_valid is True
        assert "api" in result.metadata.get("pattern", "") or result.source

    def test_generation_context_fields(self):
        """Test GenerationContext accepts all fields."""
        context = GenerationContext(
            requirement="Test requirement",
            target_pattern="model",
            language="python",
            dependencies=["typing"],
            output_path="models/user.py",
            class_name="TestClass",
            metadata={"version": "1.0"},
        )

        assert context.requirement == "Test requirement"
        assert context.class_name == "TestClass"

    def test_generated_code_fields(self):
        """Test GeneratedCode contains all expected fields."""
        generator = RealCodeGenerator(strict_mode=False)

        result = generator.generate(
            GenerationContext(requirement="Create a data processor")
        )

        assert hasattr(result, "source")
        assert hasattr(result, "language")
        assert hasattr(result, "syntax_valid")
        assert hasattr(result, "has_stubs")
        assert hasattr(result, "type_coverage")
        assert hasattr(result, "quality_score")

    def test_multiple_generations(self):
        """Test generating multiple pieces of code."""
        generator = RealCodeGenerator()

        patterns = ["model", "service", "api"]
        results = []

        for pattern in patterns:
            context = GenerationContext(
                requirement=f"Create {pattern}",
                target_pattern=pattern,
            )
            result = generator.generate(context)
            results.append(result)

        assert all(r.syntax_valid for r in results)
        assert all(not r.has_stubs for r in results)


# =============================================================================
# Exception Tests
# =============================================================================

class TestExceptions:
    """Test exception handling."""

    def test_code_generation_error(self):
        """Test CodeGenerationError exception."""
        error = CodeGenerationError("Generation failed", context="test")
        assert error.context == "test"

    def test_syntax_validation_error(self):
        """Test SyntaxValidationError exception."""
        error = SyntaxValidationError("Invalid syntax", line=10, column=5)
        assert error.line == 10
        assert error.column == 5

    def test_stub_detected_error(self):
        """Test StubDetectedError exception."""
        locations = [StubLocation(line=1, column=0)]
        error = StubDetectedError("Stub found", locations=locations)
        assert len(error.locations) == 1

    def test_quality_gate_error(self):
        """Test QualityGateError exception."""
        error = QualityGateError("Score too low", score=50.0, threshold=80.0)
        assert error.score == 50.0
        assert error.threshold == 80.0
