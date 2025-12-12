#!/usr/bin/env python3
"""
Unit tests for SyntheticCheckpointBuilder

Tests the synthetic checkpoint builder functionality including:
- Checkpoint creation from external data
- Proper checkpoint_metadata population
- Phase result generation
- Checkpoint validation
- File saving and loading
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from maestro_hive.unified_execution.synthetic_checkpoint import (
    SyntheticCheckpointBuilder,
    SyntheticCheckpointConfig,
    SyntheticPhase,
    create_synthetic_checkpoint,
)


class TestSyntheticCheckpointBuilder:
    """Tests for SyntheticCheckpointBuilder class"""

    @pytest.fixture
    def design_data(self):
        """Sample design document data"""
        return {
            "requirement": "Build a secure REST API for user management",
            "design_summary": "Microservices architecture with JWT authentication",
            "components": ["auth_service", "user_service", "api_gateway"],
            "decisions": {
                "database": "PostgreSQL",
                "cache": "Redis",
                "auth": "JWT with refresh tokens"
            },
            "api_design": {
                "endpoints": [
                    "POST /auth/login",
                    "GET /users",
                    "POST /users"
                ]
            },
            "technology_stack": ["Python", "FastAPI", "PostgreSQL", "Docker"]
        }

    @pytest.fixture
    def requirements_data(self):
        """Sample requirements data"""
        return {
            "requirement": "E-commerce platform with shopping cart",
            "requirements": [
                "User authentication",
                "Product catalog",
                "Shopping cart",
                "Checkout flow"
            ],
            "user_stories": [
                "As a user, I can browse products",
                "As a user, I can add items to cart"
            ],
            "acceptance_criteria": [
                "Cart persists across sessions",
                "Checkout validates inventory"
            ]
        }

    def test_builder_initialization(self, design_data):
        """Test builder initializes correctly"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        assert builder.external_data == design_data
        assert builder.target_phase == "design"
        assert builder.workflow_id is not None
        assert "synthetic_design_" in builder.workflow_id
        assert builder.config is not None

    def test_builder_with_custom_workflow_id(self, design_data):
        """Test builder accepts custom workflow ID"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design",
            workflow_id="custom-workflow-123"
        )

        assert builder.workflow_id == "custom-workflow-123"

    def test_builder_with_custom_config(self, design_data):
        """Test builder accepts custom config"""
        config = SyntheticCheckpointConfig(
            default_quality_score=0.95,
            quality_gate_threshold=0.90
        )

        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design",
            config=config
        )

        assert builder.config.default_quality_score == 0.95
        assert builder.config.quality_gate_threshold == 0.90

    def test_build_creates_valid_context(self, design_data):
        """Test build() creates valid checkpoint structure"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        context = builder.build()

        # Check required top-level keys
        assert "checkpoint_metadata" in context
        assert "workflow_context" in context
        assert "team_execution_state" in context

    def test_checkpoint_metadata_populated_correctly(self, design_data):
        """Test checkpoint_metadata has all required fields"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        context = builder.build()
        metadata = context["checkpoint_metadata"]

        # Required fields
        assert metadata["version"] == "1.0"
        assert metadata["workflow_id"] == builder.workflow_id
        assert metadata["phase_completed"] == "design"
        assert metadata["awaiting_phase"] == "implementation"
        assert metadata["checkpoint_type"] == "phase_boundary"
        assert metadata["quality_gate_passed"] is True
        assert metadata["quality_score"] == 0.85

        # Synthetic-specific fields
        assert metadata["synthetic"] is True
        assert metadata["synthetic_source"] == "external_data"
        assert "design_summary" in metadata["external_data_keys"]

    def test_workflow_context_structure(self, design_data):
        """Test workflow_context has proper structure"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        context = builder.build()
        workflow = context["workflow_context"]

        # Basic fields
        assert workflow["workflow_id"] == builder.workflow_id
        assert workflow["workflow_type"] == "sdlc"
        assert workflow["execution_mode"] == "phased"
        assert workflow["current_phase"] == "design"

        # Phase results
        assert isinstance(workflow["phase_results"], dict)
        assert "requirements" in workflow["phase_results"]
        assert "design" in workflow["phase_results"]

        # Phase order
        assert workflow["phase_order"] == ["requirements", "design"]

    def test_phase_results_include_prior_phases(self, design_data):
        """Test phase results include all phases up to target"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="testing"
        )

        context = builder.build()
        workflow = context["workflow_context"]

        expected_phases = ["requirements", "design", "implementation", "testing"]
        assert workflow["phase_order"] == expected_phases

        for phase in expected_phases:
            assert phase in workflow["phase_results"]
            assert workflow["phase_results"][phase]["status"] == "completed"

    def test_phase_result_contains_external_data(self, design_data):
        """Test target phase result contains external data"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        context = builder.build()
        design_result = context["workflow_context"]["phase_results"]["design"]

        # Should have external data
        assert "external_data" in design_result["outputs"]
        assert design_result["outputs"]["external_data"] == design_data
        assert design_result["outputs"]["synthetic_source"] is True

        # Should have design-specific fields
        assert "design_summary" in design_result["outputs"]

    def test_team_execution_state_structure(self, design_data):
        """Test team_execution_state has proper structure"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        context = builder.build()
        state = context["team_execution_state"]

        # Classification
        assert state["classification"] is not None
        assert state["classification"]["requirement_type"] == "feature_development"

        # Persona results per phase
        assert isinstance(state["persona_results"], dict)
        assert "design" in state["persona_results"]

        # Quality and timing metrics
        assert isinstance(state["quality_metrics"], dict)
        assert isinstance(state["timing_metrics"], dict)

    def test_persona_results_per_phase(self, design_data):
        """Test persona results are generated for each phase"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        context = builder.build()
        persona_results = context["team_execution_state"]["persona_results"]

        # Requirements phase should have requirement_analyst
        assert "requirements" in persona_results
        assert "requirement_analyst" in persona_results["requirements"]

        # Design phase should have solution_architect and backend_developer
        assert "design" in persona_results
        assert "solution_architect" in persona_results["design"]

        # Check persona result structure
        persona = persona_results["design"]["solution_architect"]
        assert persona["success"] is True
        assert persona["quality_score"] == 0.85

    def test_validation_passes_for_valid_checkpoint(self, design_data):
        """Test validation passes for properly built checkpoint"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        builder.build()
        validation = builder.validate()

        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
        assert validation["workflow_id"] == builder.workflow_id
        assert validation["target_phase"] == "design"

    def test_validation_fails_before_build(self, design_data):
        """Test validation raises error if build() not called"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        with pytest.raises(RuntimeError, match="Context not built"):
            builder.validate()

    def test_build_raises_on_empty_data(self):
        """Test build raises error for empty external data"""
        builder = SyntheticCheckpointBuilder(
            external_data={},
            target_phase="design"
        )

        with pytest.raises(ValueError, match="external_data cannot be empty"):
            builder.build()

    def test_build_raises_on_empty_phase(self, design_data):
        """Test build raises error for empty target phase"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase=""
        )

        with pytest.raises(ValueError, match="target_phase cannot be empty"):
            builder.build()

    def test_save_creates_checkpoint_file(self, design_data):
        """Test save() creates valid checkpoint file"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = builder.save(output_dir=tmpdir)

            assert Path(filepath).exists()
            assert filepath.endswith("checkpoint_design.json")

            # Verify file content
            with open(filepath) as f:
                saved_data = json.load(f)

            assert "checkpoint_metadata" in saved_data
            assert "workflow_context" in saved_data
            assert "team_execution_state" in saved_data

    def test_save_with_custom_path(self, design_data):
        """Test save() accepts custom output path"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_checkpoint.json"
            filepath = builder.save(output_path=str(custom_path))

            assert filepath == str(custom_path)
            assert Path(filepath).exists()

    def test_save_updates_checkpoint_path_in_context(self, design_data):
        """Test save() updates checkpoint path in context"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = builder.save(output_dir=tmpdir)
            context = builder.get_context()

            assert context["checkpoint_metadata"]["checkpoint_path"] == filepath
            assert context["workflow_context"]["checkpoint_path"] == filepath

    def test_get_context_after_build(self, design_data):
        """Test get_context() returns built context"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        builder.build()
        context = builder.get_context()

        assert context is not None
        assert "checkpoint_metadata" in context

    def test_get_context_raises_before_build(self, design_data):
        """Test get_context() raises error before build"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        with pytest.raises(RuntimeError, match="Context not built"):
            builder.get_context()

    def test_repr_shows_status(self, design_data):
        """Test __repr__ shows build status"""
        builder = SyntheticCheckpointBuilder(
            external_data=design_data,
            target_phase="design"
        )

        assert "not built" in repr(builder)

        builder.build()
        assert "built" in repr(builder)
        assert "not built" not in repr(builder)


class TestSyntheticCheckpointPhaseHandling:
    """Tests for phase-specific handling"""

    def test_requirements_phase(self):
        """Test requirements phase checkpoint"""
        data = {
            "requirements": ["Feature A", "Feature B"],
            "user_stories": ["Story 1", "Story 2"]
        }

        builder = SyntheticCheckpointBuilder(
            external_data=data,
            target_phase="requirements"
        )

        context = builder.build()

        assert context["checkpoint_metadata"]["phase_completed"] == "requirements"
        assert context["checkpoint_metadata"]["awaiting_phase"] == "design"
        assert context["workflow_context"]["phase_order"] == ["requirements"]

    def test_implementation_phase(self):
        """Test implementation phase includes prior phases"""
        data = {"implementation": {"modules": ["auth", "api"]}}

        builder = SyntheticCheckpointBuilder(
            external_data=data,
            target_phase="implementation"
        )

        context = builder.build()

        expected_phases = ["requirements", "design", "implementation"]
        assert context["workflow_context"]["phase_order"] == expected_phases
        assert context["checkpoint_metadata"]["awaiting_phase"] == "testing"

    def test_deployment_phase_no_next_phase(self):
        """Test deployment phase has no awaiting_phase"""
        data = {"deployment": {"target": "production"}}

        builder = SyntheticCheckpointBuilder(
            external_data=data,
            target_phase="deployment"
        )

        context = builder.build()

        assert context["checkpoint_metadata"]["awaiting_phase"] is None

    def test_custom_phase(self):
        """Test handling of non-standard phase"""
        data = {"custom_analysis": {"results": [1, 2, 3]}}

        builder = SyntheticCheckpointBuilder(
            external_data=data,
            target_phase="custom_analysis"
        )

        context = builder.build()

        # Custom phase should be treated as standalone
        assert context["checkpoint_metadata"]["phase_completed"] == "custom_analysis"
        assert "custom_analysis" in context["workflow_context"]["phase_results"]


class TestSyntheticCheckpointDataInference:
    """Tests for data inference from external data"""

    def test_infer_complexity_from_components(self):
        """Test complexity inference from component count"""
        # Many components = complex
        data = {"requirement": "Build API", "components": ["a", "b", "c", "d", "e", "f"]}
        builder = SyntheticCheckpointBuilder(data, "design")
        context = builder.build()
        assert context["team_execution_state"]["classification"]["complexity"] == "complex"

        # Few components = simple
        data = {"requirement": "Build API", "components": ["a"]}
        builder = SyntheticCheckpointBuilder(data, "design")
        context = builder.build()
        assert context["team_execution_state"]["classification"]["complexity"] == "simple"

    def test_infer_expertise_from_tech_stack(self):
        """Test expertise inference from technology stack"""
        data = {
            "requirement": "Build API",
            "technology_stack": ["Python", "FastAPI", "PostgreSQL", "Docker"]
        }

        builder = SyntheticCheckpointBuilder(data, "design")
        context = builder.build()

        expertise = context["team_execution_state"]["classification"]["required_expertise"]
        assert "python" in expertise
        assert "database" in expertise
        assert "devops" in expertise

    def test_infer_source_type_from_keys(self):
        """Test source type inference from data keys"""
        # Design doc
        data = {"design_summary": "Architecture overview"}
        builder = SyntheticCheckpointBuilder(data, "design")
        builder.build()
        assert builder._infer_source_type() == "design_document"

        # API spec
        data = {"api_design": {"endpoints": []}}
        builder = SyntheticCheckpointBuilder(data, "design")
        builder.build()
        assert builder._infer_source_type() == "api_specification"

        # Requirements doc
        data = {"requirements": []}
        builder = SyntheticCheckpointBuilder(data, "requirements")
        builder.build()
        assert builder._infer_source_type() == "requirements_document"


class TestCreateSyntheticCheckpointFunction:
    """Tests for convenience function"""

    def test_create_synthetic_checkpoint_basic(self):
        """Test create_synthetic_checkpoint function"""
        data = {"design_summary": "Test design"}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = create_synthetic_checkpoint(
                external_data=data,
                target_phase="design",
                output_path=f"{tmpdir}/test.json"
            )

            assert Path(path).exists()

            with open(path) as f:
                content = json.load(f)

            assert content["checkpoint_metadata"]["phase_completed"] == "design"

    def test_create_synthetic_checkpoint_with_workflow_id(self):
        """Test create_synthetic_checkpoint with custom workflow ID"""
        data = {"design_summary": "Test design"}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = create_synthetic_checkpoint(
                external_data=data,
                target_phase="design",
                output_path=f"{tmpdir}/test.json",
                workflow_id="custom-id-456"
            )

            with open(path) as f:
                content = json.load(f)

            assert content["checkpoint_metadata"]["workflow_id"] == "custom-id-456"


class TestSyntheticPhaseEnum:
    """Tests for SyntheticPhase enum"""

    def test_enum_values(self):
        """Test enum has expected values"""
        assert SyntheticPhase.REQUIREMENTS.value == "requirements"
        assert SyntheticPhase.DESIGN.value == "design"
        assert SyntheticPhase.IMPLEMENTATION.value == "implementation"
        assert SyntheticPhase.TESTING.value == "testing"
        assert SyntheticPhase.DEPLOYMENT.value == "deployment"

    def test_enum_usage_with_builder(self):
        """Test enum can be used with builder"""
        data = {"design_summary": "Test"}

        builder = SyntheticCheckpointBuilder(
            external_data=data,
            target_phase=SyntheticPhase.DESIGN.value
        )

        context = builder.build()
        assert context["checkpoint_metadata"]["phase_completed"] == "design"


class TestSyntheticCheckpointConfig:
    """Tests for SyntheticCheckpointConfig"""

    def test_default_config_values(self):
        """Test default config values"""
        config = SyntheticCheckpointConfig()

        assert config.version == "1.0"
        assert config.default_quality_score == 0.85
        assert config.quality_gate_threshold == 0.80
        assert config.execution_mode == "phased"
        assert config.workflow_type == "sdlc"
        assert len(config.standard_phases) == 5

    def test_custom_config_affects_output(self):
        """Test custom config affects generated checkpoint"""
        config = SyntheticCheckpointConfig(
            default_quality_score=0.95,
            version="2.0"
        )

        builder = SyntheticCheckpointBuilder(
            external_data={"test": "data"},
            target_phase="design",
            config=config
        )

        context = builder.build()

        assert context["checkpoint_metadata"]["version"] == "2.0"
        assert context["checkpoint_metadata"]["quality_score"] == 0.95
