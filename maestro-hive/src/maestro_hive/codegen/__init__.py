"""
Real Code Generation Module.

EPIC: MD-2496 - [MAESTRO] Sub-EPIC 3: Real Code Generation

Replaces NotImplementedError stubs with actual functional code.
"""

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

__all__ = [
    # Generator
    "RealCodeGenerator",
    "GenerationContext",
    "GeneratedCode",
    # Validator
    "SyntaxValidator",
    "ValidationResult",
    "StubLocation",
    # Templates
    "CodeTemplateRegistry",
    "CodeTemplate",
    # Type hints
    "TypeHintGenerator",
    # Quality
    "QualityFabricClient",
    "QualityResult",
    # Exceptions
    "CodeGenerationError",
    "SyntaxValidationError",
    "StubDetectedError",
    "QualityGateError",
]
