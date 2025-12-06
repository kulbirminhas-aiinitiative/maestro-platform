"""
Maestro Test Templates Library - MD-2523

Comprehensive test templates for all testing types as part of the Block Library initiative.

Templates Available:
- Pytest Unit Tests: Reusable pytest templates with fixtures and assertions
- API Integration Tests: REST/GraphQL API integration test templates
- Cypress E2E Tests: End-to-end testing templates for web applications
- Security Tests (OWASP): Security testing templates covering OWASP Top 10
- BDD/Gherkin: Behavior-driven development feature templates

Reference: MD-2523 Test Templates Library (Sub-EPIC of MD-2513 Block Library)
"""

from .models import (
    TestTemplate,
    TestType,
    TestFramework,
    TestFixture,
    TestAssertion,
    MockPattern,
    CoverageConfig,
    TestSuiteConfig,
)

from .pytest_templates import (
    PytestUnitTemplate,
    PytestIntegrationTemplate,
    PytestFixtureTemplate,
    get_pytest_conftest_template,
)

from .api_templates import (
    APIIntegrationTemplate,
    RestAPITestTemplate,
    GraphQLTestTemplate,
)

from .cypress_templates import (
    CypressE2ETemplate,
    CypressComponentTemplate,
    CypressCommandsTemplate,
)

from .security_templates import (
    OWASPSecurityTemplate,
    SecurityScanTemplate,
    VulnerabilityTestTemplate,
)

from .bdd_templates import (
    GherkinFeatureTemplate,
    StepDefinitionTemplate,
    BDDContextTemplate,
)

from .patterns import (
    SetupTeardownPattern,
    MockingPattern,
    AssertionPattern,
    CoveragePattern,
)

from .registry import TestTemplateRegistry, get_all_test_templates

__all__ = [
    # Models
    "TestTemplate",
    "TestType",
    "TestFramework",
    "TestFixture",
    "TestAssertion",
    "MockPattern",
    "CoverageConfig",
    "TestSuiteConfig",
    # Pytest
    "PytestUnitTemplate",
    "PytestIntegrationTemplate",
    "PytestFixtureTemplate",
    "get_pytest_conftest_template",
    # API
    "APIIntegrationTemplate",
    "RestAPITestTemplate",
    "GraphQLTestTemplate",
    # Cypress
    "CypressE2ETemplate",
    "CypressComponentTemplate",
    "CypressCommandsTemplate",
    # Security
    "OWASPSecurityTemplate",
    "SecurityScanTemplate",
    "VulnerabilityTestTemplate",
    # BDD
    "GherkinFeatureTemplate",
    "StepDefinitionTemplate",
    "BDDContextTemplate",
    # Patterns
    "SetupTeardownPattern",
    "MockingPattern",
    "AssertionPattern",
    "CoveragePattern",
    # Registry
    "TestTemplateRegistry",
    "get_all_test_templates",
]
