"""
Test Template Manifest Validation
Tests for the TemplateManifest Pydantic model and validation logic
"""

import pytest
from pydantic import ValidationError

from models.manifest import (
    TemplateManifest,
    ManifestMetadata,
    ManifestPlaceholder,
    ManifestHooks,
    TemplateEngine
)


class TestManifestValidation:
    """Test manifest validation and scoring."""

    def test_minimal_valid_manifest(self):
        """Test minimal valid manifest."""
        data = {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template for validation",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["api", "rest"],
                "license": "MIT"
            },
            "engine": "jinja2",
            "placeholders": []
        }

        manifest = TemplateManifest(**data)
        assert manifest.name == "test-template"
        assert manifest.version == "1.0.0"
        assert manifest.engine == TemplateEngine.JINJA2

    def test_complete_manifest(self):
        """Test complete manifest with all fields."""
        data = {
            "name": "complete-template",
            "version": "2.1.0",
            "description": "Complete test template with all fields",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["api", "rest", "microservice"],
                "license": "MIT"
            },
            "engine": "jinja2",
            "placeholders": [
                {
                    "variable": "PROJECT_NAME",
                    "description": "Name of the project",
                    "default": "my-api",
                    "type": "string",
                    "required": True,
                    "pattern": "^[a-z][a-z0-9-]*$"
                },
                {
                    "variable": "PORT",
                    "description": "Service port",
                    "default": 8000,
                    "type": "integer",
                    "required": False
                }
            ],
            "hooks": {
                "pre_generation": ["scripts/validate.sh"],
                "post_generation": ["scripts/setup.sh"]
            },
            "dependencies": {
                "runtime": ["python>=3.9", "postgresql>=13"],
                "build": ["poetry>=1.5"]
            }
        }

        manifest = TemplateManifest(**data)
        assert manifest.name == "complete-template"
        assert len(manifest.placeholders) == 2
        assert manifest.metadata.license == "MIT"

    def test_invalid_version(self):
        """Test that invalid semantic version is rejected."""
        data = {
            "name": "test-template",
            "version": "invalid-version",  # Not semver
            "description": "Test template description",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["test"],
                "license": "MIT"
            },
            "engine": "jinja2"
        }

        with pytest.raises(ValidationError) as exc_info:
            TemplateManifest(**data)

        assert "version" in str(exc_info.value).lower()

    def test_invalid_placeholder_variable_name(self):
        """Test that lowercase placeholder variables are rejected."""
        data = {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template description",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["test"],
                "license": "MIT"
            },
            "engine": "jinja2",
            "placeholders": [
                {
                    "variable": "lowercase_var",  # Should be UPPERCASE_VAR
                    "description": "Test variable description",
                    "type": "string"
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            TemplateManifest(**data)

        assert "variable" in str(exc_info.value).lower()

    def test_placeholder_choice_validation(self):
        """Test placeholder with choices."""
        data = {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template description",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["test"],
                "license": "MIT"
            },
            "engine": "jinja2",
            "placeholders": [
                {
                    "variable": "DATABASE_TYPE",
                    "description": "Database type selection",
                    "type": "string",
                    "choices": ["postgresql", "mysql", "sqlite"],
                    "default": "postgresql"
                }
            ]
        }

        manifest = TemplateManifest(**data)
        assert manifest.placeholders[0].choices == ["postgresql", "mysql", "sqlite"]
        assert manifest.placeholders[0].default == "postgresql"

    def test_manifest_validation_score(self):
        """Test quality score calculation."""
        # Minimal manifest (should have lower score)
        minimal_data = {
            "name": "minimal",
            "version": "1.0.0",
            "description": "Minimal test template",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["test"],
                "license": "MIT"
            },
            "engine": "jinja2"
        }
        minimal_manifest = TemplateManifest(**minimal_data)
        minimal_score = minimal_manifest.get_validation_score()

        # Complete manifest (should have higher score)
        complete_data = {
            "name": "complete",
            "version": "1.0.0",
            "description": "Complete test template with all features",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["api", "rest", "microservice"],
                "license": "MIT"
            },
            "engine": "jinja2",
            "placeholders": [
                {
                    "variable": "PROJECT_NAME",
                    "description": "Project name",
                    "type": "string",
                    "required": True
                }
            ],
            "hooks": {
                "post_generation": ["setup.sh"]
            },
            "dependencies": {
                "runtime": ["python>=3.9"]
            },
            "documentation": {
                "readme": "README.md",
                "examples": ["docs/getting-started.md"]
            }
        }
        complete_manifest = TemplateManifest(**complete_data)
        complete_score = complete_manifest.get_validation_score()

        # Complete manifest should have higher score
        assert complete_score > minimal_score
        assert 0 <= minimal_score <= 100
        assert 0 <= complete_score <= 100

    def test_invalid_url(self):
        """Test that invalid name format is rejected."""
        data = {
            "name": "test template",  # Invalid name (contains space)
            "version": "1.0.0",
            "description": "Test template description",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["test"],
                "license": "MIT"
            },
            "engine": "jinja2"
        }

        with pytest.raises(ValidationError) as exc_info:
            TemplateManifest(**data)

        assert "name" in str(exc_info.value).lower()

    def test_boolean_placeholder(self):
        """Test boolean placeholder type."""
        data = {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template description",
            "author": "Test Author",
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "category": "backend",
                "tags": ["test"],
                "license": "MIT"
            },
            "engine": "jinja2",
            "placeholders": [
                {
                    "variable": "USE_DOCKER",
                    "description": "Include Docker configuration",
                    "type": "boolean",
                    "default": True
                }
            ]
        }

        manifest = TemplateManifest(**data)
        assert manifest.placeholders[0].type == "boolean"
        assert manifest.placeholders[0].default == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])