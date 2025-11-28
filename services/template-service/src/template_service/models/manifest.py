"""
Template Manifest Models
Pydantic models for validating template manifest.yaml files
"""

import re
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class PlaceholderType(str, Enum):
    """Supported placeholder data types"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    LIST = "list"
    OBJECT = "object"


class TemplateEngine(str, Enum):
    """Supported templating engines"""
    JINJA2 = "jinja2"
    COOKIECUTTER = "cookiecutter"
    COPIER = "copier"
    CUSTOM = "custom"


class TemplateCategory(str, Enum):
    """Template categories"""
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    MOBILE = "mobile"
    DEVOPS = "devops"
    DATA = "data"
    ML = "ml"
    LIBRARY = "library"
    CLI = "cli"
    UTILITY = "utility"
    API = "api"
    BUSINESS_LOGIC = "business_logic"


class ManifestPlaceholder(BaseModel):
    """Template placeholder/variable definition"""
    variable: str = Field(..., description="Placeholder variable name")
    description: str = Field(..., description="Human-readable description")
    default: Optional[Any] = Field(None, description="Default value")
    type: PlaceholderType = Field(PlaceholderType.STRING, description="Data type")
    required: bool = Field(False, description="Whether value is required")
    pattern: Optional[str] = Field(None, description="Regex validation pattern (string types)")
    choices: Optional[List[Any]] = Field(None, description="List of allowed values")

    @field_validator('variable')
    @classmethod
    def validate_variable_name(cls, v):
        """Ensure variable name follows naming conventions"""
        if not re.match(r'^[A-Z][A-Z0-9_]*$', v):
            raise ValueError(
                f"Variable '{v}' must be UPPERCASE_SNAKE_CASE "
                "(start with letter, contain only uppercase letters, numbers, underscores)"
            )
        return v

    @field_validator('pattern')
    @classmethod
    def validate_pattern(cls, v):
        """Ensure pattern is valid regex"""
        if v:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v

    @model_validator(mode='after')
    def validate_choices_match_type(self):
        """Ensure choices match the declared type"""
        if self.choices and self.type:
            if self.type == PlaceholderType.INTEGER:
                if not all(isinstance(c, int) for c in self.choices):
                    raise ValueError("All choices must be integers for INTEGER type")
            elif self.type == PlaceholderType.BOOLEAN:
                if not all(isinstance(c, bool) for c in self.choices):
                    raise ValueError("All choices must be booleans for BOOLEAN type")
            elif self.type == PlaceholderType.FLOAT:
                if not all(isinstance(c, (int, float)) for c in self.choices):
                    raise ValueError("All choices must be numbers for FLOAT type")

        return self

    model_config = ConfigDict(use_enum_values=True)


class ManifestHooks(BaseModel):
    """Lifecycle hooks for template execution"""
    pre_generation: List[str] = Field(default_factory=list, description="Scripts before template rendering")
    post_generation: List[str] = Field(default_factory=list, description="Scripts after template rendering")
    pre_deployment: List[str] = Field(default_factory=list, description="Scripts before deployment")
    post_deployment: List[str] = Field(default_factory=list, description="Scripts after deployment")

    @field_validator('pre_generation', 'post_generation', 'pre_deployment', 'post_deployment')
    @classmethod
    def validate_script_paths(cls, v):
        """Ensure script paths are reasonable"""
        for script in v:
            if '..' in script:
                raise ValueError(f"Script path '{script}' cannot contain '..' for security")
            if script.startswith('/'):
                raise ValueError(f"Script path '{script}' must be relative, not absolute")
        return v


class ManifestMetadata(BaseModel):
    """Template metadata"""
    language: str = Field(..., description="Primary programming language")
    framework: str = Field(..., description="Framework or library name")
    category: TemplateCategory = Field(..., description="Template category")
    tags: List[str] = Field(..., min_length=1, max_length=10, description="Searchable tags")
    license: str = Field(..., description="License type")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Ensure tags are lowercase and reasonable"""
        validated = []
        for tag in v:
            cleaned = tag.lower().strip()
            if not re.match(r'^[a-z0-9-]+$', cleaned):
                raise ValueError(f"Tag '{tag}' must contain only lowercase letters, numbers, and hyphens")
            if len(cleaned) > 30:
                raise ValueError(f"Tag '{tag}' is too long (max 30 characters)")
            validated.append(cleaned)
        return validated

    @field_validator('language', 'framework')
    @classmethod
    def validate_not_empty(cls, v):
        """Ensure required strings are not empty"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    model_config = ConfigDict(use_enum_values=True)


class ManifestDependencies(BaseModel):
    """Template dependencies"""
    runtime: List[str] = Field(default_factory=list, description="Runtime dependencies")
    build: List[str] = Field(default_factory=list, description="Build-time dependencies")
    services: List[str] = Field(default_factory=list, description="External services required")


class ManifestConfiguration(BaseModel):
    """Template configuration options"""
    min_engine_version: Optional[str] = Field(None, description="Minimum templating engine version")
    supported_os: List[str] = Field(default_factory=list, description="Supported operating systems")
    architecture: List[str] = Field(default_factory=list, description="Supported CPU architectures")

    @field_validator('supported_os')
    @classmethod
    def validate_os(cls, v):
        """Ensure OS values are valid"""
        valid_os = {'linux', 'darwin', 'windows', 'freebsd', 'openbsd'}
        for os_name in v:
            if os_name.lower() not in valid_os:
                raise ValueError(f"OS '{os_name}' not recognized. Valid: {valid_os}")
        return [os.lower() for os in v]

    @field_validator('architecture')
    @classmethod
    def validate_arch(cls, v):
        """Ensure architecture values are valid"""
        valid_arch = {'amd64', 'arm64', 'arm', 'x86', 'i386'}
        for arch in v:
            if arch.lower() not in valid_arch:
                raise ValueError(f"Architecture '{arch}' not recognized. Valid: {valid_arch}")
        return [a.lower() for a in v]


class ManifestDocumentation(BaseModel):
    """Documentation links"""
    readme: Optional[str] = Field(None, description="Path to README file")
    quickstart: Optional[str] = Field(None, description="Path to quickstart guide")
    api_docs: Optional[str] = Field(None, description="Path to API documentation")
    examples: List[str] = Field(default_factory=list, description="Example implementations")


class TemplateManifest(BaseModel):
    """Complete template manifest specification"""

    # Required core fields
    name: str = Field(..., description="Template name", min_length=1, max_length=100)
    version: str = Field(..., description="Semantic version")
    description: str = Field(..., description="Template description", min_length=10, max_length=500)
    author: str = Field(..., description="Author name or organization")

    # Required metadata
    metadata: ManifestMetadata = Field(..., description="Template metadata")

    # Required engine
    engine: TemplateEngine = Field(..., description="Templating engine")

    # Optional fields
    dependencies: Optional[ManifestDependencies] = Field(None, description="Template dependencies")
    placeholders: List[ManifestPlaceholder] = Field(default_factory=list, description="Template placeholders")
    hooks: Optional[ManifestHooks] = Field(None, description="Lifecycle hooks")
    configuration: Optional[ManifestConfiguration] = Field(None, description="Configuration options")
    documentation: Optional[ManifestDocumentation] = Field(None, description="Documentation links")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name follows naming conventions"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Template name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.strip()

    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        """Ensure version follows semantic versioning"""
        semver_pattern = r'^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z-]+)?(\+[0-9A-Za-z-]+)?$'
        if not re.match(semver_pattern, v):
            raise ValueError(
                f"Version '{v}' must follow semantic versioning (e.g., '1.0.0', '2.1.3-beta')"
            )
        return v

    @field_validator('placeholders')
    @classmethod
    def validate_unique_placeholders(cls, v):
        """Ensure placeholder variables are unique"""
        variables = [p.variable for p in v]
        if len(variables) != len(set(variables)):
            duplicates = [var for var in variables if variables.count(var) > 1]
            raise ValueError(f"Duplicate placeholder variables: {set(duplicates)}")
        return v

    @model_validator(mode='after')
    def validate_required_placeholders_have_defaults(self):
        """Warn if required placeholders don't have defaults"""
        for placeholder in self.placeholders:
            if placeholder.required and placeholder.default is None:
                # This is allowed but we could log a warning
                pass
        return self

    def get_validation_score(self) -> int:
        """Calculate manifest quality score (0-100)"""
        score = 100

        # Deductions
        if not self.placeholders:
            score -= 10  # No placeholders defined

        if not self.hooks or (not self.hooks.pre_generation and not self.hooks.post_generation):
            score -= 5  # No hooks defined

        if not self.documentation or not self.documentation.readme:
            score -= 10  # No documentation

        if len(self.metadata.tags) < 3:
            score -= 5  # Too few tags

        if not self.dependencies or (not self.dependencies.runtime and not self.dependencies.services):
            score -= 5  # No dependencies specified

        if not self.configuration:
            score -= 5  # No configuration options

        # Bonuses
        if len(self.placeholders) >= 5:
            score += 5  # Good number of placeholders

        if self.documentation and len(self.documentation.examples) > 0:
            score += 5  # Has examples

        if len(self.metadata.tags) >= 7:
            score += 5  # Excellent tagging

        return max(0, min(100, score))

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "name": "python-fastapi-microservice",
                "version": "2.1.0",
                "description": "Production-ready FastAPI microservice template",
                "author": "MAESTRO Templates Team",
                "metadata": {
                    "language": "python",
                    "framework": "fastapi",
                    "category": "backend",
                    "tags": ["api", "rest", "microservice", "async"],
                    "license": "MIT"
                },
                "engine": "jinja2",
                "placeholders": [
                    {
                        "variable": "PROJECT_NAME",
                        "description": "Name of the project",
                        "default": "my-api",
                        "type": "string",
                        "required": True
                    }
                ]
            }
        }
    )