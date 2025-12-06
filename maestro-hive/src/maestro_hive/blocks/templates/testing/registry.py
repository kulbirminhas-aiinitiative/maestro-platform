"""
Test Template Registry - MD-2523

Central registry for discovering and accessing test templates.
"""

from typing import Dict, List, Optional, Type
from dataclasses import dataclass, field

from .models import TestTemplate, TestType, TestFramework
from .pytest_templates import (
    PytestUnitTemplate,
    PytestIntegrationTemplate,
    PytestFixtureTemplate,
)
from .api_templates import (
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


@dataclass
class TemplateMetadata:
    """Metadata about a template for discovery."""
    name: str
    description: str
    test_type: TestType
    framework: TestFramework
    template_class: Type[TestTemplate]
    tags: List[str] = field(default_factory=list)


class TestTemplateRegistry:
    """Registry for managing and discovering test templates."""

    _templates: Dict[str, TemplateMetadata] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize the registry with all templates."""
        if cls._initialized:
            return

        # Register Pytest templates
        cls.register(PytestUnitTemplate)
        cls.register(PytestIntegrationTemplate)
        cls.register(PytestFixtureTemplate)

        # Register API templates
        cls.register(RestAPITestTemplate)
        cls.register(GraphQLTestTemplate)

        # Register Cypress templates
        cls.register(CypressE2ETemplate)
        cls.register(CypressComponentTemplate)
        cls.register(CypressCommandsTemplate)

        # Register Security templates
        cls.register(OWASPSecurityTemplate)
        cls.register(SecurityScanTemplate)
        cls.register(VulnerabilityTestTemplate)

        # Register BDD templates
        cls.register(GherkinFeatureTemplate)
        cls.register(StepDefinitionTemplate)
        cls.register(BDDContextTemplate)

        cls._initialized = True

    @classmethod
    def register(cls, template_class: Type[TestTemplate]) -> None:
        """Register a template class."""
        # Create instance to get metadata
        instance = template_class()

        metadata = TemplateMetadata(
            name=instance.name,
            description=instance.description,
            test_type=instance.test_type,
            framework=instance.framework,
            template_class=template_class,
            tags=instance.tags,
        )

        cls._templates[instance.name] = metadata

    @classmethod
    def get(cls, name: str) -> Optional[TestTemplate]:
        """Get a template by name."""
        cls.initialize()

        metadata = cls._templates.get(name)
        if metadata:
            return metadata.template_class()
        return None

    @classmethod
    def list_all(cls) -> List[TemplateMetadata]:
        """List all registered templates."""
        cls.initialize()
        return list(cls._templates.values())

    @classmethod
    def find_by_type(cls, test_type: TestType) -> List[TemplateMetadata]:
        """Find templates by test type."""
        cls.initialize()
        return [
            meta for meta in cls._templates.values()
            if meta.test_type == test_type
        ]

    @classmethod
    def find_by_framework(cls, framework: TestFramework) -> List[TemplateMetadata]:
        """Find templates by framework."""
        cls.initialize()
        return [
            meta for meta in cls._templates.values()
            if meta.framework == framework
        ]

    @classmethod
    def find_by_tags(cls, tags: List[str]) -> List[TemplateMetadata]:
        """Find templates by tags (any match)."""
        cls.initialize()
        return [
            meta for meta in cls._templates.values()
            if any(tag in meta.tags for tag in tags)
        ]

    @classmethod
    def search(
        cls,
        query: Optional[str] = None,
        test_type: Optional[TestType] = None,
        framework: Optional[TestFramework] = None,
        tags: Optional[List[str]] = None,
    ) -> List[TemplateMetadata]:
        """Search templates with multiple criteria."""
        cls.initialize()

        results = list(cls._templates.values())

        if test_type:
            results = [m for m in results if m.test_type == test_type]

        if framework:
            results = [m for m in results if m.framework == framework]

        if tags:
            results = [m for m in results if any(t in m.tags for t in tags)]

        if query:
            query_lower = query.lower()
            results = [
                m for m in results
                if query_lower in m.name.lower()
                or query_lower in m.description.lower()
            ]

        return results

    @classmethod
    def get_statistics(cls) -> Dict[str, int]:
        """Get statistics about registered templates."""
        cls.initialize()

        stats = {
            "total": len(cls._templates),
            "by_type": {},
            "by_framework": {},
        }

        for meta in cls._templates.values():
            type_name = meta.test_type.value
            framework_name = meta.framework.value

            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            stats["by_framework"][framework_name] = stats["by_framework"].get(framework_name, 0) + 1

        return stats


def get_all_test_templates() -> List[TestTemplate]:
    """Get all test templates as instances."""
    TestTemplateRegistry.initialize()

    return [
        meta.template_class()
        for meta in TestTemplateRegistry.list_all()
    ]


def get_template(name: str) -> Optional[TestTemplate]:
    """Get a specific template by name."""
    return TestTemplateRegistry.get(name)


def list_templates_by_category() -> Dict[str, List[str]]:
    """List templates organized by category."""
    TestTemplateRegistry.initialize()

    categories = {
        "Unit Testing": ["pytest_unit_template", "pytest_fixture_template"],
        "Integration Testing": ["pytest_integration_template", "rest_api_test_template", "graphql_test_template"],
        "E2E Testing": ["cypress_e2e_template", "cypress_component_template", "cypress_commands_template"],
        "Security Testing": ["owasp_security_template", "security_scan_template", "vulnerability_test_template"],
        "BDD Testing": ["gherkin_feature_template", "step_definition_template", "bdd_context_template"],
    }

    return categories
