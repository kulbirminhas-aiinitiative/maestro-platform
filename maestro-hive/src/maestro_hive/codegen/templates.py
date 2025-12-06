"""
Code Template Registry.

EPIC: MD-2496
Provides templates for generating real code implementations.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeTemplate:
    """A code generation template."""

    name: str
    language: str
    pattern: str  # Template pattern (e.g., "crud", "api", "model")
    template: str  # Template code with placeholders
    description: str = ""
    required_context: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with context.

        Args:
            context: Dictionary of values to substitute

        Returns:
            Rendered code string
        """
        code = self.template

        # Simple placeholder substitution
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            code = code.replace(placeholder, str(value))

        return code


class CodeTemplateRegistry:
    """
    Registry for code generation templates.

    Provides a library of production-ready code patterns.
    """

    def __init__(self):
        self._templates: Dict[str, Dict[str, CodeTemplate]] = {}
        self._load_default_templates()

    def register(
        self,
        name: str,
        template: CodeTemplate,
    ) -> None:
        """
        Register a code template.

        Args:
            name: Template name
            template: CodeTemplate instance
        """
        language = template.language.lower()
        if language not in self._templates:
            self._templates[language] = {}

        self._templates[language][name] = template
        logger.debug(f"Registered template: {name} ({language})")

    def get(
        self,
        name: str,
        language: str = "python",
    ) -> Optional[CodeTemplate]:
        """
        Get template by name and language.

        Args:
            name: Template name
            language: Programming language

        Returns:
            CodeTemplate if found, None otherwise
        """
        language = language.lower()
        if language in self._templates:
            return self._templates[language].get(name)
        return None

    def list_templates(
        self,
        language: Optional[str] = None,
    ) -> List[str]:
        """
        List available template names.

        Args:
            language: Filter by language (optional)

        Returns:
            List of template names
        """
        if language:
            language = language.lower()
            return list(self._templates.get(language, {}).keys())

        all_templates = []
        for lang_templates in self._templates.values():
            all_templates.extend(lang_templates.keys())
        return list(set(all_templates))

    def get_by_pattern(
        self,
        pattern: str,
        language: str = "python",
    ) -> List[CodeTemplate]:
        """
        Get templates matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "crud", "api")
            language: Programming language

        Returns:
            List of matching templates
        """
        language = language.lower()
        if language not in self._templates:
            return []

        return [
            t for t in self._templates[language].values()
            if t.pattern == pattern or pattern in t.tags
        ]

    def _load_default_templates(self) -> None:
        """Load built-in default templates."""
        # Python templates
        self._load_python_templates()

    def _load_python_templates(self) -> None:
        """Load Python code templates."""

        # Dataclass model template
        self.register(
            "dataclass_model",
            CodeTemplate(
                name="dataclass_model",
                language="python",
                pattern="model",
                description="Python dataclass model with validation",
                template='''"""{{description}}"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class {{class_name}}:
    """{{class_description}}"""

    id: str
    {{fields}}
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate the model fields."""
        if not self.id:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            {{to_dict_fields}}
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "{{class_name}}":
        """Create instance from dictionary."""
        return cls(
            id=data["id"],
            {{from_dict_fields}}
            metadata=data.get("metadata", {}),
        )
''',
                required_context=["class_name", "fields"],
                tags=["model", "dataclass", "entity"],
            )
        )

        # FastAPI endpoint template
        self.register(
            "fastapi_endpoint",
            CodeTemplate(
                name="fastapi_endpoint",
                language="python",
                pattern="api",
                description="FastAPI REST endpoint with CRUD operations",
                template='''"""{{description}}"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


router = APIRouter(prefix="{{prefix}}", tags=["{{tag}}"])


class {{model_name}}Create(BaseModel):
    """Request model for creating {{model_name}}."""
    {{create_fields}}


class {{model_name}}Response(BaseModel):
    """Response model for {{model_name}}."""
    id: str
    {{response_fields}}

    class Config:
        from_attributes = True


# In-memory storage (replace with database in production)
_storage: dict = {}


@router.get("/", response_model=List[{{model_name}}Response])
async def list_{{model_name_lower}}s():
    """List all {{model_name_lower}}s."""
    return list(_storage.values())


@router.post("/", response_model={{model_name}}Response, status_code=status.HTTP_201_CREATED)
async def create_{{model_name_lower}}(item: {{model_name}}Create):
    """Create a new {{model_name_lower}}."""
    import uuid
    item_id = str(uuid.uuid4())
    data = {"id": item_id, **item.model_dump()}
    _storage[item_id] = data
    return data


@router.get("/{item_id}", response_model={{model_name}}Response)
async def get_{{model_name_lower}}(item_id: str):
    """Get a {{model_name_lower}} by ID."""
    if item_id not in _storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{{model_name}} not found"
        )
    return _storage[item_id]


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{{model_name_lower}}(item_id: str):
    """Delete a {{model_name_lower}}."""
    if item_id not in _storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{{model_name}} not found"
        )
    del _storage[item_id]
''',
                required_context=["model_name", "prefix"],
                tags=["api", "fastapi", "rest", "crud"],
            )
        )

        # Service class template
        self.register(
            "service_class",
            CodeTemplate(
                name="service_class",
                language="python",
                pattern="service",
                description="Service class with dependency injection",
                template='''"""{{description}}"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class {{class_name}}:
    """
    {{class_description}}

    Provides business logic for {{domain}}.
    """

    def __init__(
        self,
        {{dependencies}}
    ):
        """Initialize the service."""
        {{init_assignments}}
        logger.info(f"{{class_name}} initialized")

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity."""
        logger.info(f"Creating entity with data: {data}")
        # Implement creation logic
        result = {"id": "generated-id", **data}
        return result

    async def get(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an entity by ID."""
        logger.info(f"Getting entity: {entity_id}")
        # Implement retrieval logic
        return {"id": entity_id}

    async def update(
        self,
        entity_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing entity."""
        logger.info(f"Updating entity {entity_id}: {data}")
        # Implement update logic
        return {"id": entity_id, **data}

    async def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        logger.info(f"Deleting entity: {entity_id}")
        # Implement deletion logic
        return True

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List entities with optional filtering."""
        logger.info(f"Listing entities with filters: {filters}")
        # Implement list logic
        return []
''',
                required_context=["class_name", "domain"],
                tags=["service", "business-logic"],
            )
        )

        # Unit test template
        self.register(
            "pytest_test",
            CodeTemplate(
                name="pytest_test",
                language="python",
                pattern="test",
                description="Pytest test module with fixtures",
                template='''"""Tests for {{module_name}}."""

import pytest
from unittest.mock import Mock, patch, AsyncMock


class Test{{class_name}}:
    """Test suite for {{class_name}}."""

    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return {{class_name}}({{fixture_args}})

    def test_{{method_name}}_success(self, instance):
        """Test {{method_name}} with valid input."""
        # Arrange
        {{arrange}}

        # Act
        result = instance.{{method_name}}({{test_args}})

        # Assert
        assert result is not None
        {{assertions}}

    def test_{{method_name}}_invalid_input(self, instance):
        """Test {{method_name}} with invalid input."""
        # Arrange
        invalid_input = {{invalid_input}}

        # Act & Assert
        with pytest.raises({{expected_exception}}):
            instance.{{method_name}}(invalid_input)

    @pytest.mark.asyncio
    async def test_{{async_method}}_async(self, instance):
        """Test async method."""
        # Arrange
        {{async_arrange}}

        # Act
        result = await instance.{{async_method}}({{async_args}})

        # Assert
        assert result is not None
''',
                required_context=["class_name", "method_name"],
                tags=["test", "pytest", "unit-test"],
            )
        )

        # Abstract base class template
        self.register(
            "abstract_base",
            CodeTemplate(
                name="abstract_base",
                language="python",
                pattern="abstract",
                description="Abstract base class with interface methods",
                template='''"""{{description}}"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class {{class_name}}(ABC):
    """
    {{class_description}}

    Abstract base class defining the interface for {{domain}}.
    """

    @abstractmethod
    def {{method_1}}(self, {{method_1_args}}) -> {{method_1_return}}:
        """
        {{method_1_description}}

        Args:
            {{method_1_arg_docs}}

        Returns:
            {{method_1_return_doc}}
        """
        pass

    @abstractmethod
    def {{method_2}}(self, {{method_2_args}}) -> {{method_2_return}}:
        """
        {{method_2_description}}

        Args:
            {{method_2_arg_docs}}

        Returns:
            {{method_2_return_doc}}
        """
        pass

    def validate(self) -> bool:
        """Validate the implementation. Override if needed."""
        return True
''',
                required_context=["class_name", "method_1", "method_2"],
                tags=["abstract", "interface", "base-class"],
            )
        )

        logger.info(f"Loaded {len(self._templates.get('python', {}))} Python templates")
