"""
Test Template Models - MD-2523

Core data models for test templates in the Block Library.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class TestType(Enum):
    """Types of tests supported by the template library."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BDD = "bdd"
    API = "api"
    CONTRACT = "contract"


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    JEST = "jest"
    CYPRESS = "cypress"
    PLAYWRIGHT = "playwright"
    K6 = "k6"
    BEHAVE = "behave"
    CUCUMBER = "cucumber"
    OWASP_ZAP = "owasp_zap"


@dataclass
class TestFixture:
    """Represents a test fixture definition."""
    name: str
    scope: str  # function, class, module, session
    description: str
    setup_code: str
    teardown_code: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    autouse: bool = False


@dataclass
class TestAssertion:
    """Represents an assertion pattern."""
    name: str
    description: str
    pattern: str
    example: str
    assertion_type: str  # equality, contains, raises, etc.


@dataclass
class MockPattern:
    """Represents a mocking pattern."""
    name: str
    description: str
    mock_type: str  # patch, mock, stub, fake
    pattern: str
    example: str
    framework_specific: Dict[str, str] = field(default_factory=dict)


@dataclass
class CoverageConfig:
    """Coverage configuration for tests."""
    enabled: bool = True
    minimum_threshold: float = 80.0
    fail_under: float = 80.0
    source_dirs: List[str] = field(default_factory=lambda: ["src"])
    omit_patterns: List[str] = field(default_factory=lambda: ["**/tests/*", "**/__pycache__/*"])
    report_formats: List[str] = field(default_factory=lambda: ["html", "xml", "json"])
    branch_coverage: bool = True


@dataclass
class TestSuiteConfig:
    """Configuration for a test suite."""
    name: str
    test_type: TestType
    framework: TestFramework
    coverage_config: CoverageConfig = field(default_factory=CoverageConfig)
    timeout_seconds: int = 300
    parallel: bool = True
    max_workers: int = 4
    retry_failed: int = 2
    markers: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class TestTemplate:
    """Base class for all test templates."""
    name: str
    description: str
    test_type: TestType
    framework: TestFramework
    version: str = "1.0.0"
    author: str = "Maestro Test Templates"
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Template content
    template_content: str = ""
    file_extension: str = ".py"

    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)

    # Configuration
    config: TestSuiteConfig = None
    fixtures: List[TestFixture] = field(default_factory=list)
    assertions: List[TestAssertion] = field(default_factory=list)
    mocks: List[MockPattern] = field(default_factory=list)

    # Variables for template rendering
    variables: Dict[str, Any] = field(default_factory=dict)

    # Tags for discovery
    tags: List[str] = field(default_factory=list)

    def render(self, **kwargs) -> str:
        """Render the template with provided variables."""
        content = self.template_content
        merged_vars = {**self.variables, **kwargs}

        for key, value in merged_vars.items():
            placeholder = f"{{{{ {key} }}}}"
            content = content.replace(placeholder, str(value))

        return content

    def validate(self) -> List[str]:
        """Validate the template structure."""
        errors = []

        if not self.name:
            errors.append("Template name is required")

        if not self.template_content:
            errors.append("Template content is required")

        if self.config and self.config.coverage_config.minimum_threshold > 100:
            errors.append("Coverage threshold cannot exceed 100%")

        return errors

    def get_required_dependencies(self) -> List[str]:
        """Get all required dependencies for this template."""
        deps = list(self.dependencies)

        # Add framework-specific dependencies
        framework_deps = {
            TestFramework.PYTEST: ["pytest", "pytest-cov", "pytest-xdist"],
            TestFramework.CYPRESS: ["cypress"],
            TestFramework.JEST: ["jest", "@types/jest"],
            TestFramework.BEHAVE: ["behave", "behave-html-formatter"],
            TestFramework.OWASP_ZAP: ["python-owasp-zap-v2.4"],
        }

        if self.framework in framework_deps:
            deps.extend(framework_deps[self.framework])

        return list(set(deps))
