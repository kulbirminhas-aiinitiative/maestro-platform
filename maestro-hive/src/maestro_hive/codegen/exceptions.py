"""
Exceptions for Code Generation Module.

EPIC: MD-2496
"""


class CodeGenerationError(Exception):
    """Raised when code generation fails."""

    def __init__(self, message: str, context: str = ""):
        super().__init__(message)
        self.context = context


class SyntaxValidationError(Exception):
    """Raised when generated code has syntax errors."""

    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(message)
        self.line = line
        self.column = column


class StubDetectedError(Exception):
    """Raised when NotImplementedError stub is detected in output."""

    def __init__(self, message: str, locations: list = None):
        super().__init__(message)
        self.locations = locations or []


class QualityGateError(Exception):
    """Raised when Quality Fabric score is below threshold."""

    def __init__(self, message: str, score: float = 0.0, threshold: float = 80.0):
        super().__init__(message)
        self.score = score
        self.threshold = threshold
