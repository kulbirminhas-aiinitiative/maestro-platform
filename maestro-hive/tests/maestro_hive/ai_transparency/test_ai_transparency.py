"""
Comprehensive Tests for AI Transparency Module - MD-2792

Tests for:
- TransparencyConfig (configuration management)
- AgentRegistry (agent lifecycle management)
- DisclosureEngine (disclosure generation)
- AgentImageManager (agent visual identity)
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import json
import tempfile
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from maestro_hive.ai_transparency import (
    TransparencyConfig, TransparencyLevel, DisclosureFormat,
    AgentRegistry, AgentConfig,
    DisclosureEngine, DisclosureResult,
    AgentImageManager, ImageConfig,
)
from maestro_hive.ai_transparency.agent_registry import (
    AgentStatus, AgentCapability, get_registry, set_registry
)
from maestro_hive.ai_transparency.disclosure_engine import (
    ContentType, get_engine, set_engine, disclose
)
from maestro_hive.ai_transparency.agent_image_manager import (
    ImageFormat, ImageSize, ImageStyle, get_manager, set_manager
)


# ============================================================
# TransparencyConfig Tests
# ============================================================

class TestTransparencyConfig:
    """Tests for TransparencyConfig class."""

    def test_default_config_creation(self):
        """Test creating config with defaults."""
        config = TransparencyConfig()

        assert config.disclosure_enabled is True
        assert config.disclosure_format == DisclosureFormat.INLINE
        assert config.disclosure_level == TransparencyLevel.STANDARD
        assert config.eu_ai_act_compliance is True

    def test_config_from_env(self):
        """Test creating config from environment variables."""
        with patch.dict(os.environ, {
            'AI_TRANSPARENCY_ENABLED': 'true',
            'AI_DISCLOSURE_LEVEL': 'detailed',
            'AI_DISCLOSURE_FORMAT': 'footer',
            'EU_AI_ACT_COMPLIANCE': 'true'
        }):
            config = TransparencyConfig.from_env()

            assert config.disclosure_enabled is True
            assert config.disclosure_level == TransparencyLevel.DETAILED
            assert config.disclosure_format == DisclosureFormat.FOOTER

    def test_config_from_file_json(self):
        """Test loading config from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "transparency": {
                    "enabled": True,
                    "disclosure": {
                        "level": "full",
                        "format": "header",
                        "text": "Custom AI text"
                    }
                }
            }, f)
            f.flush()

            config = TransparencyConfig.from_file(f.name)
            os.unlink(f.name)

            assert config.disclosure_enabled is True
            assert config.disclosure_level == TransparencyLevel.FULL
            assert config.disclosure_format == DisclosureFormat.HEADER

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = TransparencyConfig()
        result = config.to_dict()

        assert isinstance(result, dict)
        assert 'disclosure_enabled' in result
        assert 'disclosure_format' in result
        assert 'eu_ai_act_compliance' in result
        assert result['disclosure_format'] == 'inline'

    def test_config_validation_success(self):
        """Test config validation passes for valid config."""
        config = TransparencyConfig()
        errors = config.validate()

        assert len(errors) == 0
        assert config.is_valid() is True

    def test_config_validation_failure(self):
        """Test config validation catches invalid settings."""
        config = TransparencyConfig(
            eu_ai_act_compliance=True,
            disclosure_enabled=False  # Invalid: compliance requires disclosure
        )
        errors = config.validate()

        assert len(errors) > 0
        assert config.is_valid() is False

    def test_config_update(self):
        """Test updating config creates new instance."""
        original = TransparencyConfig()
        updated = original.update(disclosure_level=TransparencyLevel.FULL)

        assert updated.disclosure_level == TransparencyLevel.FULL
        assert original.disclosure_level == TransparencyLevel.STANDARD
        assert updated.updated_at > original.created_at


# ============================================================
# AgentRegistry Tests
# ============================================================

class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_agent_config_creation(self):
        """Test creating agent config."""
        config = AgentConfig(
            agent_id="test_agent_001",
            name="test_agent",
            display_name="Test Agent",
            description="A test AI agent"
        )

        assert config.agent_id == "test_agent_001"
        assert config.name == "test_agent"
        assert config.status == AgentStatus.ACTIVE
        assert config.provider == "Anthropic"

    def test_agent_config_to_dict(self):
        """Test converting agent config to dictionary."""
        config = AgentConfig(
            agent_id="test_001",
            name="test",
            display_name="Test",
            description="Test agent",
            capabilities=[AgentCapability.TEXT_GENERATION, AgentCapability.CODE_GENERATION]
        )
        result = config.to_dict()

        assert isinstance(result, dict)
        assert result['agent_id'] == "test_001"
        assert 'text_generation' in result['capabilities']

    def test_agent_config_from_dict(self):
        """Test creating agent config from dictionary."""
        data = {
            "agent_id": "from_dict_001",
            "name": "from_dict",
            "display_name": "From Dict",
            "description": "Created from dict",
            "status": "active",
            "capabilities": ["text_generation"]
        }
        config = AgentConfig.from_dict(data)

        assert config.agent_id == "from_dict_001"
        assert config.status == AgentStatus.ACTIVE
        assert AgentCapability.TEXT_GENERATION in config.capabilities


class TestAgentRegistry:
    """Tests for AgentRegistry class."""

    def setup_method(self):
        """Reset registry before each test."""
        self.registry = AgentRegistry()

    def test_register_agent(self):
        """Test registering a new agent."""
        config = AgentConfig(
            agent_id="reg_001",
            name="registered",
            display_name="Registered Agent",
            description="Test registration"
        )
        agent_id = self.registry.register(config)

        assert agent_id == "reg_001"
        assert self.registry.get("reg_001") is not None

    def test_register_new_agent(self):
        """Test registering with auto-generated ID."""
        config = self.registry.register_new(
            name="auto_agent",
            display_name="Auto Agent",
            description="Auto-generated ID test"
        )

        assert config.agent_id.startswith("agent_")
        assert len(config.agent_id) == 18  # "agent_" + 12 hex chars

    def test_register_duplicate_fails(self):
        """Test registering duplicate agent ID fails."""
        config = AgentConfig(
            agent_id="dup_001",
            name="duplicate",
            display_name="Duplicate",
            description="Test duplicate"
        )
        self.registry.register(config)

        with pytest.raises(ValueError):
            self.registry.register(config)

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        config = AgentConfig(
            agent_id="unreg_001",
            name="unregister",
            display_name="To Unregister",
            description="Will be unregistered"
        )
        self.registry.register(config)

        result = self.registry.unregister("unreg_001")
        assert result is True
        assert self.registry.get("unreg_001") is None

    def test_get_by_name(self):
        """Test getting agent by name."""
        config = AgentConfig(
            agent_id="name_001",
            name="findable_name",
            display_name="Find Me",
            description="Find by name test"
        )
        self.registry.register(config)

        found = self.registry.get_by_name("findable_name")
        assert found is not None
        assert found.agent_id == "name_001"

    def test_list_all(self):
        """Test listing all agents."""
        for i in range(3):
            self.registry.register_new(
                name=f"agent_{i}",
                display_name=f"Agent {i}",
                description=f"Test agent {i}"
            )

        agents = self.registry.list_all()
        assert len(agents) == 3

    def test_list_by_capability(self):
        """Test filtering agents by capability."""
        self.registry.register(AgentConfig(
            agent_id="code_001",
            name="code_agent",
            display_name="Code Agent",
            description="Generates code",
            capabilities=[AgentCapability.CODE_GENERATION]
        ))
        self.registry.register(AgentConfig(
            agent_id="text_001",
            name="text_agent",
            display_name="Text Agent",
            description="Generates text",
            capabilities=[AgentCapability.TEXT_GENERATION]
        ))

        code_agents = self.registry.list_by_capability(AgentCapability.CODE_GENERATION)
        assert len(code_agents) == 1
        assert code_agents[0].agent_id == "code_001"

    def test_update_agent(self):
        """Test updating agent configuration."""
        config = AgentConfig(
            agent_id="update_001",
            name="to_update",
            display_name="Original Name",
            description="Will be updated"
        )
        self.registry.register(config)

        updated = self.registry.update("update_001", display_name="Updated Name")
        assert updated.display_name == "Updated Name"
        assert updated.updated_at > config.created_at

    def test_set_status(self):
        """Test changing agent status."""
        config = AgentConfig(
            agent_id="status_001",
            name="status_test",
            display_name="Status Test",
            description="Status change test"
        )
        self.registry.register(config)

        result = self.registry.set_status("status_001", AgentStatus.SUSPENDED)
        assert result is True
        assert self.registry.get("status_001").status == AgentStatus.SUSPENDED

    def test_persistence(self):
        """Test saving and loading registry state."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            storage_path = f.name

        # Create registry with storage
        registry1 = AgentRegistry(storage_path=storage_path)
        registry1.register(AgentConfig(
            agent_id="persist_001",
            name="persistent",
            display_name="Persistent Agent",
            description="Should persist"
        ))

        # Create new registry that loads from same storage
        registry2 = AgentRegistry(storage_path=storage_path)
        loaded = registry2.get("persist_001")

        assert loaded is not None
        assert loaded.name == "persistent"

        os.unlink(storage_path)

    def test_export_import_registry(self):
        """Test exporting and importing registry data."""
        self.registry.register_new(
            name="export_test",
            display_name="Export Test",
            description="Will be exported"
        )

        exported = self.registry.export_registry()
        assert 'agents' in exported
        assert exported['agent_count'] == 1

        new_registry = AgentRegistry()
        imported = new_registry.import_registry(exported)
        assert imported == 1

    def test_get_statistics(self):
        """Test registry statistics."""
        self.registry.register(AgentConfig(
            agent_id="stat_001",
            name="active_agent",
            display_name="Active",
            description="Active agent",
            capabilities=[AgentCapability.TEXT_GENERATION]
        ))
        self.registry.register(AgentConfig(
            agent_id="stat_002",
            name="suspended_agent",
            display_name="Suspended",
            description="Suspended agent",
            status=AgentStatus.SUSPENDED
        ))

        stats = self.registry.get_statistics()
        assert stats['total_agents'] == 2
        assert 'active' in stats['by_status']
        assert 'suspended' in stats['by_status']


# ============================================================
# DisclosureEngine Tests
# ============================================================

class TestDisclosureResult:
    """Tests for DisclosureResult dataclass."""

    def test_disclosure_result_creation(self):
        """Test creating a disclosure result."""
        result = DisclosureResult(
            disclosure_id="disc_001",
            content_hash="abc123",
            original_content="Test content",
            disclosed_content="[AI] Test content",
            disclosure_text="AI-generated"
        )

        assert result.disclosure_id == "disc_001"
        assert result.content_type == ContentType.TEXT

    def test_disclosure_result_to_dict(self):
        """Test converting result to dictionary."""
        result = DisclosureResult(
            disclosure_id="disc_002",
            content_hash="def456",
            original_content="Original",
            disclosed_content="Disclosed",
            disclosure_text="AI"
        )
        data = result.to_dict()

        assert isinstance(data, dict)
        assert data['disclosure_id'] == "disc_002"
        assert 'timestamp' in data

    def test_disclosure_result_audit_log(self):
        """Test audit log generation excludes content."""
        result = DisclosureResult(
            disclosure_id="disc_003",
            content_hash="ghi789",
            original_content="Secret content",
            disclosed_content="[AI] Secret content",
            disclosure_text="AI"
        )
        audit = result.to_audit_log()

        assert 'original_content' not in audit
        assert 'disclosed_content' not in audit
        assert audit['content_hash'] == "ghi789"


class TestDisclosureEngine:
    """Tests for DisclosureEngine class."""

    def setup_method(self):
        """Reset engine before each test."""
        self.config = TransparencyConfig()
        self.registry = AgentRegistry()
        self.engine = DisclosureEngine(config=self.config, registry=self.registry)

    def test_basic_disclosure(self):
        """Test basic content disclosure."""
        result = self.engine.disclose("Hello, world!")

        assert result.original_content == "Hello, world!"
        assert "AI-generated" in result.disclosed_content
        assert result.disclosure_id.startswith("disc_")

    def test_disclosure_disabled(self):
        """Test disclosure when disabled."""
        config = TransparencyConfig(disclosure_enabled=False)
        engine = DisclosureEngine(config=config)

        result = engine.disclose("Test content")
        assert result.disclosed_content == "Test content"
        assert result.disclosure_text == ""

    def test_disclosure_with_agent(self):
        """Test disclosure with specific agent."""
        self.registry.register(AgentConfig(
            agent_id="disc_agent_001",
            name="disclosure_agent",
            display_name="Disclosure Agent",
            description="Test agent for disclosure",
            model_name="TestModel"
        ))

        result = self.engine.disclose(
            "Agent content",
            agent_id="disc_agent_001"
        )

        assert result.agent_id == "disc_agent_001"
        assert result.agent_name == "Disclosure Agent"

    def test_disclose_code(self):
        """Test code disclosure."""
        code = "def hello():\n    print('Hello')"
        result = self.engine.disclose_code(code, language="python")

        assert result.content_type == ContentType.CODE
        assert result.metadata.get('language') == 'python'
        assert '"""' in result.disclosed_content  # Python docstring format

    def test_disclose_document(self):
        """Test document disclosure."""
        doc = "# Title\n\nDocument content here."
        result = self.engine.disclose_document(doc, doc_type="markdown")

        assert result.content_type == ContentType.DOCUMENT
        assert result.metadata.get('doc_type') == 'markdown'

    def test_disclose_api_response(self):
        """Test API response disclosure."""
        response = {"status": "success", "data": {"key": "value"}}
        result = self.engine.disclose_api_response(response)

        assert result.content_type == ContentType.API_RESPONSE
        assert result.disclosure_format == DisclosureFormat.METADATA

    def test_disclosure_formats(self):
        """Test different disclosure formats."""
        content = "Test content"

        # Header format
        result_header = self.engine.disclose(
            content, override_format=DisclosureFormat.HEADER
        )
        assert result_header.disclosed_content.startswith("[")

        # Footer format
        result_footer = self.engine.disclose(
            content, override_format=DisclosureFormat.FOOTER
        )
        assert result_footer.disclosed_content.endswith("]")

        # Inline format
        result_inline = self.engine.disclose(
            content, override_format=DisclosureFormat.INLINE
        )
        assert result_inline.disclosed_content.startswith("[")
        assert "Test content" in result_inline.disclosed_content

    def test_disclosure_levels(self):
        """Test different disclosure levels."""
        self.registry.register(AgentConfig(
            agent_id="level_agent",
            name="level_agent",
            display_name="Level Agent",
            description="Agent for level testing",
            model_name="TestModel",
            model_version="1.0"
        ))

        # Minimal level
        result_min = self.engine.disclose(
            "Content",
            agent_id="level_agent",
            override_level=TransparencyLevel.MINIMAL
        )
        assert "AI-generated" in result_min.disclosure_text

        # Full level
        result_full = self.engine.disclose(
            "Content",
            agent_id="level_agent",
            override_level=TransparencyLevel.FULL
        )
        assert "Level Agent" in result_full.disclosure_text

    def test_disclosure_history(self):
        """Test disclosure history tracking."""
        for i in range(5):
            self.engine.disclose(f"Content {i}")

        history = self.engine.get_disclosure_history(limit=3)
        assert len(history) == 3

    def test_disclosure_statistics(self):
        """Test disclosure statistics."""
        self.engine.disclose("Text 1", content_type=ContentType.TEXT)
        self.engine.disclose("Text 2", content_type=ContentType.TEXT)
        self.engine.disclose_code("code = 1")

        stats = self.engine.get_statistics()
        assert stats['total_disclosures'] == 3
        assert stats['by_type']['text'] == 2
        assert stats['by_type']['code'] == 1

    def test_clear_history(self):
        """Test clearing disclosure history."""
        for i in range(10):
            self.engine.disclose(f"Content {i}")

        cleared = self.engine.clear_history()
        assert cleared == 10
        assert len(self.engine.get_disclosure_history()) == 0


# ============================================================
# AgentImageManager Tests
# ============================================================

class TestImageConfig:
    """Tests for ImageConfig dataclass."""

    def test_image_config_defaults(self):
        """Test default image configuration."""
        config = ImageConfig()

        assert config.default_size == ImageSize.MEDIUM
        assert config.preferred_format == ImageFormat.PNG
        assert config.require_alt_text is True

    def test_image_config_to_dict(self):
        """Test converting config to dictionary."""
        config = ImageConfig()
        result = config.to_dict()

        assert isinstance(result, dict)
        assert 'base_path' in result
        assert 'default_size' in result


class TestAgentImageManager:
    """Tests for AgentImageManager class."""

    def setup_method(self):
        """Reset manager before each test."""
        self.manager = AgentImageManager()

    def test_register_image(self):
        """Test registering an agent image."""
        image = self.manager.register_image(
            agent_id="img_001",
            url="/images/agent-001.png",
            width=128,
            height=128,
            alt_text="Agent 001 Avatar"
        )

        assert image.agent_id == "img_001"
        assert image.url == "/images/agent-001.png"
        assert image.alt_text == "Agent 001 Avatar"

    def test_get_image(self):
        """Test getting an agent's image."""
        self.manager.register_image(
            agent_id="get_001",
            url="/images/get-agent.png"
        )

        image = self.manager.get_image("get_001")
        assert image is not None
        assert image.url == "/images/get-agent.png"

    def test_get_url(self):
        """Test getting image URL."""
        self.manager.register_image(
            agent_id="url_001",
            url="/images/url-agent.png",
            variants={
                "SMALL": "/images/url-agent-small.png",
                "LARGE": "/images/url-agent-large.png"
            }
        )

        # Default URL
        url = self.manager.get_url("url_001")
        assert url == "/images/url-agent.png"

        # With size variant
        url_small = self.manager.get_url("url_001", size=ImageSize.SMALL)
        assert url_small == "/images/url-agent-small.png"

    def test_get_url_fallback(self):
        """Test fallback URL for missing agent."""
        url = self.manager.get_url("nonexistent_agent")
        assert url == self.manager.config.fallback_url

    def test_generate_initials_avatar(self):
        """Test generating initials-based avatar."""
        svg = self.manager.generate_initials_avatar(
            agent_id="init_001",
            name="Test Agent"
        )

        assert svg.startswith("data:image/svg+xml,")
        assert "TA" in svg  # Initials

    def test_validate_image_success(self):
        """Test image validation passes for valid image."""
        is_valid, errors = self.manager.validate_image(
            url="/images/valid.png",
            file_size_bytes=50000,
            width=256,
            height=256
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_image_failure(self):
        """Test image validation catches issues."""
        # File too large
        is_valid, errors = self.manager.validate_image(
            url="/images/large.png",
            file_size_bytes=10000000  # 10MB
        )

        assert is_valid is False
        assert len(errors) > 0

    def test_create_placeholder(self):
        """Test creating placeholder image."""
        image = self.manager.create_placeholder(
            agent_id="placeholder_001",
            name="Placeholder Agent"
        )

        assert image.agent_id == "placeholder_001"
        assert image.format == ImageFormat.SVG
        assert image.url.startswith("data:image/svg+xml,")

    def test_update_image(self):
        """Test updating an image."""
        self.manager.register_image(
            agent_id="update_001",
            url="/images/original.png",
            alt_text="Original Alt"
        )

        updated = self.manager.update_image(
            "update_001",
            alt_text="Updated Alt"
        )

        assert updated.alt_text == "Updated Alt"

    def test_remove_image(self):
        """Test removing an image."""
        self.manager.register_image(
            agent_id="remove_001",
            url="/images/remove.png"
        )

        result = self.manager.remove_image("remove_001")
        assert result is True
        assert self.manager.get_image("remove_001") is None

    def test_list_all(self):
        """Test listing all images."""
        for i in range(3):
            self.manager.register_image(
                agent_id=f"list_{i}",
                url=f"/images/agent-{i}.png"
            )

        images = self.manager.list_all()
        assert len(images) == 3

    def test_get_statistics(self):
        """Test image statistics."""
        self.manager.register_image(
            agent_id="stat_001",
            url="/images/stat.png",
            format=ImageFormat.PNG,
            file_size_bytes=10000
        )
        self.manager.register_image(
            agent_id="stat_002",
            url="/images/stat.svg",
            format=ImageFormat.SVG,
            file_size_bytes=5000
        )

        stats = self.manager.get_statistics()
        assert stats['total_images'] == 2
        assert stats['by_format']['png'] == 1
        assert stats['by_format']['svg'] == 1
        assert stats['total_size_bytes'] == 15000

    def test_get_avatar_html(self):
        """Test generating HTML for avatar."""
        self.manager.register_image(
            agent_id="html_001",
            url="/images/html-agent.png",
            alt_text="HTML Agent"
        )

        html = self.manager.get_avatar_html(
            "html_001",
            size=ImageSize.MEDIUM,
            include_badge=True
        )

        assert '<img' in html
        assert 'HTML Agent' in html
        assert 'AI' in html  # AI badge


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """Integration tests for AI transparency module."""

    def test_full_transparency_workflow(self):
        """Test complete transparency workflow."""
        # Setup
        config = TransparencyConfig(
            disclosure_level=TransparencyLevel.DETAILED,
            include_model_info=True
        )
        registry = AgentRegistry()
        engine = DisclosureEngine(config=config, registry=registry)
        image_manager = AgentImageManager()

        # Register agent
        agent = registry.register_new(
            name="integration_agent",
            display_name="Integration Agent",
            description="Full integration test agent",
            capabilities=[AgentCapability.TEXT_GENERATION],
            model_name="Claude",
            model_version="3.5"
        )

        # Create avatar
        image_manager.create_placeholder(
            agent_id=agent.agent_id,
            name=agent.display_name
        )

        # Generate disclosure
        result = engine.disclose(
            "This is AI-generated content for testing.",
            agent_id=agent.agent_id
        )

        # Verify
        assert result.agent_id == agent.agent_id
        assert result.agent_name == "Integration Agent"
        assert "Integration Agent" in result.disclosure_text
        assert "Claude" in result.disclosure_text

        # Get avatar
        avatar_url = image_manager.get_url(agent.agent_id)
        assert avatar_url.startswith("data:image/svg+xml,")

    def test_eu_ai_act_compliance_workflow(self):
        """Test EU AI Act compliance workflow."""
        config = TransparencyConfig(
            eu_ai_act_compliance=True,
            disclosure_enabled=True,
            disclosure_level=TransparencyLevel.FULL,
            audit_logging_enabled=True
        )

        # Validate config
        assert config.is_valid()

        # Create engine with compliance config
        engine = DisclosureEngine(config=config)

        # Generate disclosure
        result = engine.disclose(
            "Compliance-required content",
            content_type=ContentType.DOCUMENT
        )

        # Verify audit trail
        assert result.disclosure_id is not None
        assert result.content_hash is not None

        # Verify audit log
        audit = result.to_audit_log()
        assert 'disclosure_id' in audit
        assert 'timestamp' in audit
        assert 'original_content' not in audit  # Privacy


# ============================================================
# Default Instance Tests
# ============================================================

class TestDefaultInstances:
    """Tests for default singleton instances."""

    def test_get_registry_singleton(self):
        """Test registry singleton access."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_set_registry(self):
        """Test setting custom registry."""
        custom = AgentRegistry()
        set_registry(custom)
        assert get_registry() is custom

    def test_get_engine_singleton(self):
        """Test engine singleton access."""
        eng1 = get_engine()
        eng2 = get_engine()
        assert eng1 is eng2

    def test_disclose_convenience_function(self):
        """Test disclose() convenience function."""
        result = disclose("Quick disclosure test")
        assert result.disclosed_content is not None

    def test_get_manager_singleton(self):
        """Test image manager singleton access."""
        mgr1 = get_manager()
        mgr2 = get_manager()
        assert mgr1 is mgr2


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
