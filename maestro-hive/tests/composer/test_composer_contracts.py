"""
Contract Tests for Composer Engine - MD-2508

Tests all 5 Acceptance Criteria:
- AC-1: Parse compose.yaml manifest
- AC-2: Resolve block dependencies
- AC-3: Identify gaps requiring generation
- AC-4: Wire blocks together
- AC-5: Generate minimal glue code
"""

import pytest
import tempfile
import os
from pathlib import Path

# Import composer components
from maestro_hive.composer import (
    ManifestParser,
    CompositionManifest,
    BlockReference,
    DependencyResolver,
    ResolvedDependencies,
    GapAnalyzer,
    GapAnalysis,
    Gap,
    BlockWirer,
    WiredSystem,
    Connection,
    ComposerEngine,
    CompositionResult,
)
from maestro_hive.composer.manifest_parser import GenerationSpec, ValidationResult
from maestro_hive.composer.dependency_resolver import ResolvedBlock, CompatibilityResult
from maestro_hive.composer.gap_analyzer import GapType, GapSeverity
from maestro_hive.composer.block_wirer import ConnectionType, WiredBlock


# =============================================================================
# AC-1: Parse compose.yaml manifest
# =============================================================================

class TestManifestParser:
    """Contract tests for AC-1: Parse compose.yaml manifest"""

    def test_parser_initialization(self):
        """Test ManifestParser can be initialized"""
        parser = ManifestParser()
        assert parser is not None

    def test_parse_simple_manifest_string(self):
        """Test parsing a simple manifest from string"""
        parser = ManifestParser()
        yaml_content = """
version: "1.0"
compose:
  - logging@1.2.3
  - jira-adapter@3.1.0
generate:
  - VerbosityController
config:
  timeout: 30
"""
        manifest = parser.parse_string(yaml_content)

        assert manifest.version == "1.0"
        assert len(manifest.compose) == 2
        assert len(manifest.generate) == 1
        assert manifest.config.get("timeout") == 30

    def test_parse_manifest_from_file(self):
        """Test parsing manifest from file"""
        parser = ManifestParser()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
version: "1.0"
compose:
  - quality-fabric@2.0.0
config:
  strict: true
""")
            f.flush()
            temp_path = f.name

        try:
            manifest = parser.parse(temp_path)
            assert manifest.version == "1.0"
            assert len(manifest.compose) == 1
            assert manifest.compose[0].block_id == "quality-fabric"
            assert manifest.compose[0].version == "2.0.0"
        finally:
            os.unlink(temp_path)

    def test_parse_manifest_file_not_found(self):
        """Test FileNotFoundError for missing manifest"""
        parser = ManifestParser()

        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path/compose.yaml")

    def test_parse_block_reference_from_string(self):
        """Test BlockReference.from_string parsing"""
        ref = BlockReference.from_string("logging@1.2.3")
        assert ref.block_id == "logging"
        assert ref.version == "1.2.3"

    def test_parse_block_reference_caret_version(self):
        """Test caret version specification"""
        ref = BlockReference.from_string("jira-adapter@^3.0.0")
        assert ref.block_id == "jira-adapter"
        assert ref.version == "^3.0.0"

    def test_parse_block_reference_tilde_version(self):
        """Test tilde version specification"""
        ref = BlockReference.from_string("dag-executor@~2.1.0")
        assert ref.block_id == "dag-executor"
        assert ref.version == "~2.1.0"

    def test_parse_invalid_block_reference(self):
        """Test invalid block reference format raises ValueError"""
        with pytest.raises(ValueError):
            BlockReference.from_string("invalid-no-version")

    def test_parse_extended_block_format(self):
        """Test parsing extended block format with config"""
        parser = ManifestParser()
        yaml_content = """
version: "1.0"
compose:
  - block: logging
    version: "1.2.3"
    config:
      level: DEBUG
    alias: main_logger
"""
        manifest = parser.parse_string(yaml_content)

        assert len(manifest.compose) == 1
        block = manifest.compose[0]
        assert block.block_id == "logging"
        assert block.version == "1.2.3"
        assert block.config.get("level") == "DEBUG"
        assert block.alias == "main_logger"

    def test_parse_generation_spec(self):
        """Test parsing generation specifications"""
        parser = ManifestParser()
        yaml_content = """
version: "1.0"
compose: []
generate:
  - name: CustomAdapter
    type: adapter
    interface: IDataTransformer
    description: Transform data between systems
"""
        manifest = parser.parse_string(yaml_content)

        assert len(manifest.generate) == 1
        gen = manifest.generate[0]
        assert gen.name == "CustomAdapter"
        assert gen.type == "adapter"
        assert gen.interface == "IDataTransformer"
        assert gen.description == "Transform data between systems"

    def test_validate_manifest_valid(self):
        """Test validation of valid manifest"""
        parser = ManifestParser()
        manifest = CompositionManifest(
            version="1.0",
            compose=[BlockReference("logging", "1.2.3")],
            generate=[],
            config={}
        )

        result = parser.validate(manifest)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_manifest_empty(self):
        """Test validation of empty manifest"""
        parser = ManifestParser()
        manifest = CompositionManifest(
            version="1.0",
            compose=[],
            generate=[],
            config={}
        )

        result = parser.validate(manifest)
        assert result.valid is False
        assert any("at least one block" in e for e in result.errors)

    def test_validate_manifest_duplicate_blocks(self):
        """Test validation catches duplicate block IDs"""
        parser = ManifestParser()
        manifest = CompositionManifest(
            version="1.0",
            compose=[
                BlockReference("logging", "1.0.0"),
                BlockReference("logging", "2.0.0")
            ],
            generate=[],
            config={}
        )

        result = parser.validate(manifest)
        assert result.valid is False
        assert any("Duplicate" in e for e in result.errors)

    def test_validate_unsupported_version_warning(self):
        """Test validation warns on unsupported version"""
        parser = ManifestParser()
        manifest = CompositionManifest(
            version="99.0",
            compose=[BlockReference("logging", "1.0.0")],
            generate=[],
            config={}
        )

        result = parser.validate(manifest)
        assert any("Unsupported" in w for w in result.warnings)

    def test_to_yaml_roundtrip(self):
        """Test converting manifest back to YAML"""
        parser = ManifestParser()
        original = CompositionManifest(
            version="1.0",
            compose=[BlockReference("logging", "1.2.3")],
            generate=[GenerationSpec("CustomController")],
            config={"timeout": 30}
        )

        yaml_str = parser.to_yaml(original)
        assert "version: '1.0'" in yaml_str or 'version: "1.0"' in yaml_str or "version: 1.0" in yaml_str
        assert "logging@1.2.3" in yaml_str

    def test_block_reference_to_string(self):
        """Test BlockReference.to_string()"""
        ref = BlockReference("jira-adapter", "^3.0.0")
        assert ref.to_string() == "jira-adapter@^3.0.0"

    def test_composition_manifest_get_block(self):
        """Test CompositionManifest.get_block()"""
        manifest = CompositionManifest(
            version="1.0",
            compose=[
                BlockReference("logging", "1.0.0"),
                BlockReference("jira-adapter", "3.0.0")
            ],
            generate=[],
            config={}
        )

        block = manifest.get_block("jira-adapter")
        assert block is not None
        assert block.version == "3.0.0"

        missing = manifest.get_block("nonexistent")
        assert missing is None

    def test_composition_manifest_get_block_ids(self):
        """Test CompositionManifest.get_block_ids()"""
        manifest = CompositionManifest(
            version="1.0",
            compose=[
                BlockReference("logging", "1.0.0"),
                BlockReference("jira-adapter", "3.0.0")
            ],
            generate=[],
            config={}
        )

        ids = manifest.get_block_ids()
        assert "logging" in ids
        assert "jira-adapter" in ids


# =============================================================================
# AC-2: Resolve block dependencies
# =============================================================================

# Import MockRegistry for testing
from maestro_hive.composer.dependency_resolver import MockRegistry


class TestDependencyResolver:
    """Contract tests for AC-2: Resolve block dependencies"""

    def test_resolver_initialization(self):
        """Test DependencyResolver can be initialized"""
        resolver = DependencyResolver()
        assert resolver is not None

    def test_resolve_simple_manifest(self):
        """Test resolving simple manifest with mock registry"""
        # Use explicit MockRegistry to ensure consistent test behavior
        mock_registry = MockRegistry()
        resolver = DependencyResolver(registry=mock_registry)
        manifest = CompositionManifest(
            version="1.0",
            compose=[
                BlockReference("logging", "1.2.3"),
                BlockReference("jira-adapter", "3.1.0")
            ],
            generate=[],
            config={}
        )

        resolved = resolver.resolve(manifest)

        assert isinstance(resolved, ResolvedDependencies)
        assert "logging" in resolved.blocks
        assert "jira-adapter" in resolved.blocks

    def test_resolve_unresolved_blocks(self):
        """Test unresolved blocks are tracked"""
        # Use MockRegistry to get consistent behavior
        mock_registry = MockRegistry()
        resolver = DependencyResolver(registry=mock_registry)
        manifest = CompositionManifest(
            version="1.0",
            compose=[
                BlockReference("nonexistent-block", "1.0.0")
            ],
            generate=[],
            config={}
        )

        resolved = resolver.resolve(manifest)

        assert "nonexistent-block" in resolved.unresolved
        assert not resolved.is_complete()

    def test_resolve_latest_version(self):
        """Test resolving 'latest' version"""
        # Use explicit MockRegistry
        mock_registry = MockRegistry()
        resolver = DependencyResolver(registry=mock_registry)
        manifest = CompositionManifest(
            version="1.0",
            compose=[BlockReference("logging", "latest")],
            generate=[],
            config={}
        )

        resolved = resolver.resolve(manifest)

        assert "logging" in resolved.blocks
        # Should have resolved to actual version
        assert resolved.blocks["logging"].version is not None

    def test_resolution_order(self):
        """Test resolution order is computed"""
        # Use explicit MockRegistry
        mock_registry = MockRegistry()
        resolver = DependencyResolver(registry=mock_registry)
        manifest = CompositionManifest(
            version="1.0",
            compose=[
                BlockReference("logging", "1.2.3"),
                BlockReference("jira-adapter", "3.0.0")
            ],
            generate=[],
            config={}
        )

        resolved = resolver.resolve(manifest)

        assert len(resolved.resolution_order) >= 2
        assert "logging" in resolved.resolution_order
        assert "jira-adapter" in resolved.resolution_order

    def test_compatibility_check(self):
        """Test compatibility checking"""
        resolver = DependencyResolver()
        blocks = [
            ResolvedBlock("block-a", "1.0.0", None, []),
            ResolvedBlock("block-b", "2.0.0", None, [])
        ]

        result = resolver.check_compatibility(blocks)

        assert isinstance(result, CompatibilityResult)
        assert result.compatible is True

    def test_resolved_dependencies_get_block(self):
        """Test ResolvedDependencies.get_block()"""
        resolved = ResolvedDependencies(
            blocks={
                "logging": ResolvedBlock("logging", "1.0.0", None, [])
            },
            resolution_order=["logging"],
            unresolved=[],
            compatibility=CompatibilityResult(True, [])
        )

        block = resolved.get_block("logging")
        assert block is not None
        assert block.version == "1.0.0"

    def test_resolved_dependencies_get_all_versions(self):
        """Test ResolvedDependencies.get_all_versions()"""
        resolved = ResolvedDependencies(
            blocks={
                "logging": ResolvedBlock("logging", "1.0.0", None, []),
                "jira-adapter": ResolvedBlock("jira-adapter", "3.1.0", None, [])
            },
            resolution_order=["logging", "jira-adapter"],
            unresolved=[],
            compatibility=CompatibilityResult(True, [])
        )

        versions = resolved.get_all_versions()
        assert versions["logging"] == "1.0.0"
        assert versions["jira-adapter"] == "3.1.0"


# =============================================================================
# AC-3: Identify gaps requiring generation
# =============================================================================

class TestGapAnalyzer:
    """Contract tests for AC-3: Identify gaps requiring generation"""

    def test_analyzer_initialization(self):
        """Test GapAnalyzer can be initialized"""
        analyzer = GapAnalyzer()
        assert analyzer is not None

    def test_analyze_unresolved_blocks(self):
        """Test analysis identifies unresolved blocks as gaps"""
        analyzer = GapAnalyzer()
        manifest = CompositionManifest(
            version="1.0",
            compose=[BlockReference("missing-block", "1.0.0")],
            generate=[],
            config={}
        )
        resolved = ResolvedDependencies(
            blocks={},
            resolution_order=[],
            unresolved=["missing-block"],
            compatibility=CompatibilityResult(True, [])
        )

        analysis = analyzer.analyze(manifest, resolved)

        assert isinstance(analysis, GapAnalysis)
        assert analysis.total_gaps > 0

        missing_gaps = analysis.get_gaps_by_type(GapType.MISSING_BLOCK)
        assert len(missing_gaps) > 0

    def test_analyze_explicit_generation(self):
        """Test analysis identifies explicit generation requirements"""
        analyzer = GapAnalyzer()
        manifest = CompositionManifest(
            version="1.0",
            compose=[],
            generate=[GenerationSpec("CustomController", "controller", "IController")],
            config={}
        )
        resolved = ResolvedDependencies(
            blocks={},
            resolution_order=[],
            unresolved=[],
            compatibility=CompatibilityResult(True, [])
        )

        analysis = analyzer.analyze(manifest, resolved)

        explicit_gaps = analysis.get_gaps_by_type(GapType.EXPLICIT)
        assert len(explicit_gaps) == 1
        assert "CustomController" in explicit_gaps[0].gap_id

    def test_gap_severity_levels(self):
        """Test gap severity categorization"""
        gap = Gap(
            gap_id="test-gap",
            gap_type=GapType.MISSING_BLOCK,
            severity=GapSeverity.CRITICAL,
            description="Test gap",
            affected_blocks=["test-block"]
        )

        assert gap.severity == GapSeverity.CRITICAL

    def test_gap_analysis_has_critical_gaps(self):
        """Test GapAnalysis.has_critical_gaps()"""
        analysis = GapAnalysis(
            gaps=[
                Gap("gap-1", GapType.MISSING_BLOCK, GapSeverity.CRITICAL, "Critical gap", [])
            ],
            total_gaps=1,
            critical_count=1,
            can_proceed=False,
            summary={"missing_block": 1}
        )

        assert analysis.has_critical_gaps() is True

    def test_gap_analysis_get_critical_gaps(self):
        """Test GapAnalysis.get_critical_gaps()"""
        analysis = GapAnalysis(
            gaps=[
                Gap("gap-1", GapType.MISSING_BLOCK, GapSeverity.CRITICAL, "Critical", []),
                Gap("gap-2", GapType.ADAPTER, GapSeverity.LOW, "Low priority", [])
            ],
            total_gaps=2,
            critical_count=1,
            can_proceed=True,
            summary={}
        )

        critical = analysis.get_critical_gaps()
        assert len(critical) == 1
        assert critical[0].gap_id == "gap-1"

    def test_analyze_no_gaps(self):
        """Test analysis with no gaps"""
        analyzer = GapAnalyzer()
        manifest = CompositionManifest(
            version="1.0",
            compose=[BlockReference("logging", "1.0.0")],
            generate=[],
            config={}
        )
        resolved = ResolvedDependencies(
            blocks={"logging": ResolvedBlock("logging", "1.0.0", None, [])},
            resolution_order=["logging"],
            unresolved=[],
            compatibility=CompatibilityResult(True, [])
        )

        analysis = analyzer.analyze(manifest, resolved)

        assert analysis.can_proceed is True


# =============================================================================
# AC-4: Wire blocks together
# =============================================================================

class TestBlockWirer:
    """Contract tests for AC-4: Wire blocks together"""

    def test_wirer_initialization(self):
        """Test BlockWirer can be initialized"""
        wirer = BlockWirer()
        assert wirer is not None

    def test_wire_empty_blocks(self):
        """Test wiring with no blocks"""
        wirer = BlockWirer()
        resolved = ResolvedDependencies(
            blocks={},
            resolution_order=[],
            unresolved=[],
            compatibility=CompatibilityResult(True, [])
        )

        system = wirer.wire(resolved)

        assert isinstance(system, WiredSystem)
        assert len(system.blocks) == 0

    def test_wire_single_block(self):
        """Test wiring a single block"""
        wirer = BlockWirer()

        class MockInstance:
            pass

        resolved = ResolvedDependencies(
            blocks={
                "logging": ResolvedBlock("logging", "1.0.0", MockInstance(), [])
            },
            resolution_order=["logging"],
            unresolved=[],
            compatibility=CompatibilityResult(True, [])
        )

        system = wirer.wire(resolved)

        assert "logging" in system.blocks
        assert "logging" in system.entry_points
        assert "logging" in system.exit_points

    def test_wire_with_explicit_connections(self):
        """Test wiring with explicit connections"""
        wirer = BlockWirer()

        class SourceBlock:
            output = "data"

        class TargetBlock:
            input = None

        resolved = ResolvedDependencies(
            blocks={
                "source": ResolvedBlock("source", "1.0.0", SourceBlock(), []),
                "target": ResolvedBlock("target", "1.0.0", TargetBlock(), [])
            },
            resolution_order=["source", "target"],
            unresolved=[],
            compatibility=CompatibilityResult(True, [])
        )

        connections = [
            Connection(
                source_block="source",
                source_port="output",
                target_block="target",
                target_port="input",
                connection_type=ConnectionType.DIRECT
            )
        ]

        system = wirer.wire(resolved, connections)

        assert len(system.connections) == 1
        assert system.connections[0].source_block == "source"
        assert system.connections[0].target_block == "target"

    def test_wired_system_is_valid(self):
        """Test WiredSystem.is_valid()"""
        system = WiredSystem(
            blocks={},
            connections=[],
            entry_points=[],
            exit_points=[],
            wiring_errors=[]
        )

        assert system.is_valid() is True

    def test_wired_system_get_execution_order(self):
        """Test WiredSystem.get_execution_order()"""
        system = WiredSystem(
            blocks={
                "a": WiredBlock("a", None, [], []),
                "b": WiredBlock("b", None, [], [])
            },
            connections=[],
            entry_points=["a"],
            exit_points=["b"],
            wiring_errors=[]
        )

        order = system.get_execution_order()
        assert "a" in order
        assert "b" in order

    def test_validate_wiring(self):
        """Test wiring validation"""
        wirer = BlockWirer()
        system = WiredSystem(
            blocks={"block-a": WiredBlock("block-a", None, [], [])},
            connections=[],
            entry_points=["block-a"],
            exit_points=["block-a"],
            wiring_errors=[]
        )

        result = wirer.validate_wiring(system)

        assert result.valid is True

    def test_validate_wiring_disconnected_warning(self):
        """Test validation warns about disconnected blocks"""
        wirer = BlockWirer()
        system = WiredSystem(
            blocks={
                "a": WiredBlock("a", None, [], []),
                "b": WiredBlock("b", None, [], [])
            },
            connections=[],
            entry_points=["a", "b"],
            exit_points=["a", "b"],
            wiring_errors=[]
        )

        result = wirer.validate_wiring(system)

        # Both blocks are disconnected (no connections to each other)
        assert any("not connected" in w for w in result.warnings)

    def test_generate_diagram(self):
        """Test diagram generation"""
        wirer = BlockWirer()

        connection = Connection("source", "output", "target", "input")
        system = WiredSystem(
            blocks={
                "source": WiredBlock("source", None, [], [connection]),
                "target": WiredBlock("target", None, [connection], [])
            },
            connections=[connection],
            entry_points=["source"],
            exit_points=["target"],
            wiring_errors=[]
        )

        diagram = wirer.generate_diagram(system)

        assert "source" in diagram
        assert "target" in diagram
        assert "ENTRY" in diagram
        assert "EXIT" in diagram

    def test_connection_types(self):
        """Test all connection types are defined"""
        assert ConnectionType.DIRECT == "direct"
        assert ConnectionType.EVENT == "event"
        assert ConnectionType.QUEUE == "queue"
        assert ConnectionType.CALLBACK == "callback"


# =============================================================================
# AC-5: Generate minimal glue code
# =============================================================================

class TestComposerEngine:
    """Contract tests for AC-5: Generate minimal glue code"""

    def test_engine_initialization(self):
        """Test ComposerEngine can be initialized"""
        engine = ComposerEngine()
        assert engine is not None

    def test_engine_with_config(self):
        """Test ComposerEngine with configuration"""
        engine = ComposerEngine({
            "cache_enabled": False,
            "strict_mode": True,
            "output_dir": "/tmp/generated"
        })
        assert engine is not None

    def test_compose_from_dict(self):
        """Test composing from dictionary manifest"""
        engine = ComposerEngine()
        manifest_dict = {
            "version": "1.0",
            "compose": ["logging@1.2.3"],
            "config": {}
        }

        result = engine.compose_from_dict(manifest_dict)

        assert isinstance(result, CompositionResult)
        assert result.manifest is not None

    def test_composition_result_structure(self):
        """Test CompositionResult has all required fields"""
        engine = ComposerEngine()
        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": ["logging@1.2.3"],
            "config": {}
        })

        assert hasattr(result, 'success')
        assert hasattr(result, 'manifest')
        assert hasattr(result, 'resolved')
        assert hasattr(result, 'gaps')
        assert hasattr(result, 'wired_system')
        assert hasattr(result, 'glue_code')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'duration_ms')

    def test_composition_result_get_statistics(self):
        """Test CompositionResult.get_statistics()"""
        engine = ComposerEngine()
        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": ["logging@1.2.3"],
            "config": {}
        })

        stats = result.get_statistics()

        assert "blocks_composed" in stats
        assert "gaps_identified" in stats
        assert "glue_code_generated" in stats
        assert "errors" in stats

    def test_glue_code_generation_for_explicit(self):
        """Test glue code is generated for explicit generation"""
        engine = ComposerEngine()
        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": ["logging@1.2.3"],
            "generate": [
                {"name": "CustomAdapter", "type": "adapter"}
            ],
            "config": {}
        })

        # Should have generated glue code for CustomAdapter
        assert len(result.glue_code) > 0

    def test_get_composition_summary(self):
        """Test generating composition summary"""
        engine = ComposerEngine()
        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": ["logging@1.2.3"],
            "config": {}
        })

        summary = engine.get_composition_summary(result)

        assert isinstance(summary, str)
        assert "COMPOSITION SUMMARY" in summary
        assert "Blocks Composed" in summary

    @pytest.mark.asyncio
    async def test_compose_async(self):
        """Test async compose method"""
        engine = ComposerEngine()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
version: "1.0"
compose:
  - logging@1.2.3
config: {}
""")
            f.flush()
            temp_path = f.name

        try:
            result = await engine.compose(temp_path)

            assert isinstance(result, CompositionResult)
            assert result.manifest is not None
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_compose_file_not_found(self):
        """Test compose handles missing file"""
        engine = ComposerEngine()

        result = await engine.compose("/nonexistent/compose.yaml")

        assert result.success is False
        assert any("not found" in e.lower() for e in result.errors)

    def test_strict_mode_fails_on_errors(self):
        """Test strict mode fails on validation errors"""
        engine = ComposerEngine({"strict_mode": True})
        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": [],  # Empty - will cause error
            "config": {}
        })

        # With strict mode, should fail
        assert result.success is False

    def test_glue_code_has_file_path(self):
        """Test generated glue code has file path"""
        engine = ComposerEngine({"output_dir": "/tmp/test_output"})
        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": ["logging@1.2.3"],
            "generate": [
                {"name": "TestComponent", "type": "component"}
            ],
            "config": {}
        })

        if result.glue_code:
            glue = result.glue_code[0]
            assert glue.file_path is not None
            assert "/tmp/test_output" in glue.file_path


# =============================================================================
# Integration Tests
# =============================================================================

class TestComposerIntegration:
    """Integration tests for the complete composition workflow"""

    def test_full_composition_workflow(self):
        """Test complete workflow from manifest to wired system"""
        engine = ComposerEngine()

        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": [
                "logging@1.2.3",
                "jira-adapter@3.0.0"
            ],
            "generate": [
                {"name": "DataTransformer", "type": "adapter"}
            ],
            "config": {
                "timeout": 30
            }
        })

        # Verify complete workflow executed
        assert result.manifest is not None
        assert result.resolved is not None
        assert result.gaps is not None
        assert result.wired_system is not None
        assert result.duration_ms > 0

    def test_composition_with_unresolved(self):
        """Test composition handles unresolved blocks gracefully"""
        engine = ComposerEngine()

        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": [
                "logging@1.2.3",
                "nonexistent-block@1.0.0"
            ],
            "config": {}
        })

        # Should still complete (non-strict mode)
        assert result.resolved is not None
        assert "nonexistent-block" in result.resolved.unresolved
        # Gap analysis should identify missing block
        assert result.gaps.total_gaps > 0

    def test_composition_empty_manifest(self):
        """Test composition with empty manifest fails validation"""
        engine = ComposerEngine({"strict_mode": True})

        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": [],
            "generate": [],
            "config": {}
        })

        assert result.success is False

    def test_composition_timing(self):
        """Test composition records timing"""
        engine = ComposerEngine()

        result = engine.compose_from_dict({
            "version": "1.0",
            "compose": ["logging@1.2.3"],
            "config": {}
        })

        assert result.duration_ms >= 0
        assert result.timestamp is not None
