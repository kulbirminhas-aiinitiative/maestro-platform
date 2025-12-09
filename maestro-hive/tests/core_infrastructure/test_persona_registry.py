#!/usr/bin/env python3
"""Tests for PersonaRegistry module."""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.personas.persona_registry import (
    PersonaRegistry,
    PersonaDefinition,
    PersonaStatus,
    ModelConfig,
    get_persona_registry
)


class TestPersonaDefinition:
    """Tests for PersonaDefinition dataclass."""

    def test_persona_creation(self):
        """Test creating a PersonaDefinition."""
        config = ModelConfig(model_id="test-model")
        persona = PersonaDefinition(
            id="test_persona",
            name="Test Persona",
            description="A test persona",
            capabilities=["testing", "validation"],
            system_prompt="You are a test persona",
            model_config=config
        )

        assert persona.id == "test_persona"
        assert persona.name == "Test Persona"
        assert len(persona.capabilities) == 2

    def test_has_capability(self):
        """Test capability checking."""
        config = ModelConfig(model_id="test-model")
        persona = PersonaDefinition(
            id="test",
            name="Test",
            description="Test",
            capabilities=["Coding", "Review", "testing"],
            system_prompt="Test",
            model_config=config
        )

        assert persona.has_capability("coding") is True
        assert persona.has_capability("REVIEW") is True
        assert persona.has_capability("debugging") is False

    def test_has_any_capability(self):
        """Test checking for any capability."""
        config = ModelConfig(model_id="test-model")
        persona = PersonaDefinition(
            id="test",
            name="Test",
            description="Test",
            capabilities=["coding", "review"],
            system_prompt="Test",
            model_config=config
        )

        assert persona.has_any_capability(["coding", "unknown"]) is True
        assert persona.has_any_capability(["unknown", "other"]) is False

    def test_has_all_capabilities(self):
        """Test checking for all capabilities."""
        config = ModelConfig(model_id="test-model")
        persona = PersonaDefinition(
            id="test",
            name="Test",
            description="Test",
            capabilities=["coding", "review", "testing"],
            system_prompt="Test",
            model_config=config
        )

        assert persona.has_all_capabilities(["coding", "review"]) is True
        assert persona.has_all_capabilities(["coding", "unknown"]) is False

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        config = ModelConfig(model_id="test-model", temperature=0.5)
        persona = PersonaDefinition(
            id="test",
            name="Test",
            description="Test desc",
            capabilities=["cap1"],
            system_prompt="prompt",
            model_config=config,
            tags=["tag1"]
        )

        data = persona.to_dict()
        restored = PersonaDefinition.from_dict(data)

        assert restored.id == persona.id
        assert restored.name == persona.name
        assert restored.model_config.temperature == 0.5


class TestPersonaRegistry:
    """Tests for PersonaRegistry class."""

    def setup_method(self):
        """Reset singleton for each test."""
        PersonaRegistry._instance = None

    def test_singleton_pattern(self):
        """Test that PersonaRegistry is a singleton."""
        reg1 = PersonaRegistry()
        reg2 = PersonaRegistry()
        assert reg1 is reg2

    def test_default_personas_registered(self):
        """Test that default personas are registered."""
        reg = PersonaRegistry()
        personas = reg.list_all()

        # Should have at least the default personas
        persona_ids = [p.id for p in personas]
        assert "architect" in persona_ids
        assert "developer" in persona_ids
        assert "qa_engineer" in persona_ids

    def test_register_persona(self):
        """Test registering a new persona."""
        reg = PersonaRegistry()
        config = ModelConfig(model_id="test-model")
        persona = PersonaDefinition(
            id="custom_persona",
            name="Custom Persona",
            description="A custom persona",
            capabilities=["custom_capability"],
            system_prompt="Custom prompt",
            model_config=config
        )

        assert reg.register(persona) is True
        retrieved = reg.get("custom_persona")
        assert retrieved is not None
        assert retrieved.name == "Custom Persona"

    def test_register_duplicate_fails(self):
        """Test that registering duplicate fails without overwrite."""
        reg = PersonaRegistry()
        config = ModelConfig(model_id="test-model")
        persona = PersonaDefinition(
            id="dup_test",
            name="Dup Test",
            description="Test",
            capabilities=[],
            system_prompt="Test",
            model_config=config
        )

        assert reg.register(persona) is True
        assert reg.register(persona) is False  # Should fail

    def test_register_overwrite(self):
        """Test overwriting existing persona."""
        reg = PersonaRegistry()
        config = ModelConfig(model_id="test-model")
        persona1 = PersonaDefinition(
            id="overwrite_test",
            name="Original",
            description="Test",
            capabilities=[],
            system_prompt="Test",
            model_config=config
        )
        persona2 = PersonaDefinition(
            id="overwrite_test",
            name="Updated",
            description="Test",
            capabilities=[],
            system_prompt="Test",
            model_config=config
        )

        reg.register(persona1)
        assert reg.register(persona2, overwrite=True) is True
        retrieved = reg.get("overwrite_test")
        assert retrieved.name == "Updated"

    def test_unregister_persona(self):
        """Test unregistering a persona."""
        reg = PersonaRegistry()
        config = ModelConfig(model_id="test-model")
        persona = PersonaDefinition(
            id="to_remove",
            name="To Remove",
            description="Test",
            capabilities=[],
            system_prompt="Test",
            model_config=config
        )

        reg.register(persona)
        assert reg.unregister("to_remove") is True
        assert reg.get("to_remove") is None

    def test_find_by_capability(self):
        """Test finding personas by capability."""
        reg = PersonaRegistry()

        # Find by coding capability
        coders = reg.find_by_capability("coding")
        assert len(coders) >= 1
        assert all(p.has_capability("coding") for p in coders)

    def test_find_by_capabilities_match_all(self):
        """Test finding by multiple capabilities with match_all."""
        reg = PersonaRegistry()

        # Find personas with both testing and qa capabilities
        qa_personas = reg.find_by_capabilities(["testing", "qa"], match_all=True)
        for p in qa_personas:
            assert p.has_all_capabilities(["testing", "qa"])

    def test_find_by_capabilities_match_any(self):
        """Test finding by multiple capabilities with match_any."""
        reg = PersonaRegistry()

        matches = reg.find_by_capabilities(["coding", "testing"], match_all=False)
        for p in matches:
            assert p.has_any_capability(["coding", "testing"])

    def test_find_by_tag(self):
        """Test finding personas by tag."""
        reg = PersonaRegistry()

        # Default personas have 'default' tag
        defaults = reg.find_by_tag("default")
        assert len(defaults) >= 1

    def test_update_status(self):
        """Test updating persona status."""
        reg = PersonaRegistry()

        assert reg.update_status("developer", PersonaStatus.INACTIVE) is True
        persona = reg.get("developer")
        assert persona.status == PersonaStatus.INACTIVE

    def test_get_all_capabilities(self):
        """Test getting all unique capabilities."""
        reg = PersonaRegistry()
        caps = reg.get_all_capabilities()

        assert len(caps) > 0
        assert "coding" in caps or "architecture" in caps

    def test_persistence(self):
        """Test persistence to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            PersonaRegistry._instance = None
            persistence_path = Path(tmpdir) / "personas.json"
            reg = PersonaRegistry(persistence_path=str(persistence_path))

            config = ModelConfig(model_id="test")
            persona = PersonaDefinition(
                id="persist_test",
                name="Persist Test",
                description="Test",
                capabilities=["persist"],
                system_prompt="Test",
                model_config=config
            )
            reg.register(persona)

            # Check file was created
            assert persistence_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
