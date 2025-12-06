"""
Pipeline Template Registry

Central registry for managing CI/CD pipeline templates.

Provides:
- Template registration and lookup
- Platform-based filtering
- Pipeline type filtering
- Factory methods for common patterns

Reference: MD-2522 CI/CD Pipeline Templates
"""

from typing import Dict, List, Optional, Callable
from .models import PipelineTemplate, PipelineType, Platform, MatrixConfig
from .gitlab import GitLabPipeline, GitLabAdapter
from .azure import AzurePipeline, AzureAdapter
from .jenkins import JenkinsPipeline, JenkinsAdapter


class PipelineRegistry:
    """
    Central registry for pipeline templates.

    Manages pipeline template lifecycle including:
    - Registration by platform and type
    - Lookup by platform, type, or both
    - Factory method access
    """

    def __init__(self):
        """Initialize empty registry."""
        self._templates: Dict[str, PipelineTemplate] = {}
        self._adapters: Dict[Platform, type] = {
            Platform.GITLAB: GitLabAdapter,
            Platform.AZURE: AzureAdapter,
            Platform.JENKINS: JenkinsAdapter,
        }
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure built-in templates are registered."""
        if not self._initialized:
            self._register_builtin_templates()
            self._initialized = True

    def _register_builtin_templates(self) -> None:
        """Register all built-in templates."""
        # GitLab templates
        self.register("gitlab_build", GitLabAdapter.create_build_pipeline())
        self.register("gitlab_test", GitLabAdapter.create_test_pipeline())
        self.register("gitlab_deploy", GitLabAdapter.create_deploy_pipeline())
        self.register("gitlab_release", GitLabAdapter.create_release_pipeline())

        # Azure templates
        self.register("azure_build", AzureAdapter.create_build_pipeline())
        self.register("azure_test", AzureAdapter.create_test_pipeline())
        self.register("azure_deploy", AzureAdapter.create_deploy_pipeline())
        self.register("azure_release", AzureAdapter.create_release_pipeline())

        # Jenkins templates
        self.register("jenkins_build", JenkinsAdapter.create_build_pipeline())
        self.register("jenkins_test", JenkinsAdapter.create_test_pipeline())
        self.register("jenkins_deploy", JenkinsAdapter.create_deploy_pipeline())
        self.register("jenkins_release", JenkinsAdapter.create_release_pipeline())

    def register(self, template_id: str, template: PipelineTemplate) -> None:
        """
        Register a pipeline template.

        Args:
            template_id: Unique identifier for the template
            template: The pipeline template to register
        """
        self._templates[template_id] = template

    def get(self, template_id: str) -> Optional[PipelineTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: The template identifier

        Returns:
            The template or None if not found
        """
        self._ensure_initialized()
        return self._templates.get(template_id)

    def get_by_platform_and_type(
        self,
        platform: Platform,
        pipeline_type: PipelineType,
    ) -> Optional[PipelineTemplate]:
        """
        Get a template by platform and type.

        Args:
            platform: The CI/CD platform
            pipeline_type: The type of pipeline

        Returns:
            The template or None if not found
        """
        self._ensure_initialized()
        template_id = f"{platform.value}_{pipeline_type.value}"
        return self._templates.get(template_id)

    def list_all(self) -> List[PipelineTemplate]:
        """
        List all registered templates.

        Returns:
            List of all templates
        """
        self._ensure_initialized()
        return list(self._templates.values())

    def list_by_platform(self, platform: Platform) -> List[PipelineTemplate]:
        """
        List templates for a specific platform.

        Args:
            platform: The CI/CD platform

        Returns:
            List of templates for the platform
        """
        self._ensure_initialized()
        return [
            t for t in self._templates.values()
            if t.platform == platform
        ]

    def list_by_type(self, pipeline_type: PipelineType) -> List[PipelineTemplate]:
        """
        List templates of a specific type.

        Args:
            pipeline_type: The pipeline type

        Returns:
            List of templates of that type
        """
        self._ensure_initialized()
        return [
            t for t in self._templates.values()
            if t.pipeline_type == pipeline_type
        ]

    def get_adapter(self, platform: Platform) -> type:
        """
        Get the adapter class for a platform.

        Args:
            platform: The CI/CD platform

        Returns:
            The adapter class
        """
        return self._adapters.get(platform)

    def create_pipeline(
        self,
        platform: Platform,
        pipeline_type: PipelineType,
        **kwargs,
    ) -> PipelineTemplate:
        """
        Create a new pipeline using the appropriate adapter.

        Args:
            platform: The CI/CD platform
            pipeline_type: The type of pipeline
            **kwargs: Additional arguments for the adapter

        Returns:
            A new pipeline template
        """
        adapter = self.get_adapter(platform)
        if not adapter:
            raise ValueError(f"No adapter for platform: {platform}")

        method_name = f"create_{pipeline_type.value}_pipeline"
        factory_method = getattr(adapter, method_name, None)

        if not factory_method:
            raise ValueError(f"No factory method for type: {pipeline_type}")

        return factory_method(**kwargs)

    def get_template_ids(self) -> List[str]:
        """
        Get all registered template IDs.

        Returns:
            List of template identifiers
        """
        self._ensure_initialized()
        return list(self._templates.keys())

    def get_platforms(self) -> List[Platform]:
        """
        Get all supported platforms.

        Returns:
            List of platforms
        """
        return list(self._adapters.keys())

    def count(self) -> int:
        """
        Get total number of registered templates.

        Returns:
            Template count
        """
        self._ensure_initialized()
        return len(self._templates)

    def to_dict(self) -> Dict:
        """
        Export registry contents as dictionary.

        Returns:
            Dictionary representation of all templates
        """
        self._ensure_initialized()
        return {
            "template_count": len(self._templates),
            "platforms": [p.value for p in self.get_platforms()],
            "templates": {
                tid: {
                    "platform": t.platform.value,
                    "type": t.pipeline_type.value,
                    "stages": len(t.stages),
                }
                for tid, t in self._templates.items()
            },
        }


# Singleton registry instance
_registry: Optional[PipelineRegistry] = None


def get_pipeline_registry() -> PipelineRegistry:
    """
    Get the global pipeline registry.

    Returns:
        The singleton PipelineRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = PipelineRegistry()
    return _registry
