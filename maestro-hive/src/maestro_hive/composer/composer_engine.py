"""
ComposerEngine - AC-5: Generate minimal glue code

Main Composer Engine that orchestrates all composition steps
and generates minimal glue code for identified gaps.

Reference: MD-2508 Acceptance Criterion 5
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .manifest_parser import ManifestParser, CompositionManifest
from .dependency_resolver import DependencyResolver, ResolvedDependencies
from .gap_analyzer import GapAnalyzer, GapAnalysis, Gap, GapType
from .block_wirer import BlockWirer, WiredSystem, Connection

logger = logging.getLogger(__name__)


@dataclass
class GlueCode:
    """Generated glue code for a gap"""
    gap_id: str
    code: str
    file_path: Optional[str] = None
    language: str = "python"
    description: Optional[str] = None


@dataclass
class CompositionResult:
    """
    Result of a composition operation.

    Contains the wired system, any generated glue code,
    and metadata about the composition process.
    """
    success: bool
    manifest: CompositionManifest
    resolved: ResolvedDependencies
    gaps: GapAnalysis
    wired_system: Optional[WiredSystem]
    glue_code: List[GlueCode]
    errors: List[str]
    warnings: List[str]
    timestamp: str
    duration_ms: float

    def get_statistics(self) -> Dict[str, Any]:
        """Get composition statistics"""
        return {
            "blocks_composed": len(self.resolved.blocks) if self.resolved else 0,
            "blocks_unresolved": len(self.resolved.unresolved) if self.resolved else 0,
            "gaps_identified": self.gaps.total_gaps if self.gaps else 0,
            "gaps_critical": self.gaps.critical_count if self.gaps else 0,
            "glue_code_generated": len(self.glue_code),
            "connections": len(self.wired_system.connections) if self.wired_system else 0,
            "errors": len(self.errors),
            "warnings": len(self.warnings)
        }


class ComposerEngine:
    """
    Main Composer Engine.

    Implements the composition-first approach by:
    1. Parsing compose.yaml manifest
    2. Resolving block dependencies
    3. Identifying gaps requiring generation
    4. Wiring blocks together
    5. Generating minimal glue code

    Reference: MD-2508 Composer Engine EPIC
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ComposerEngine.

        Args:
            config: Optional configuration
                - cache_enabled: Enable dependency caching (default: True)
                - strict_mode: Fail on any warning (default: False)
                - output_dir: Directory for generated code
        """
        self._config = config or {}
        self._cache_enabled = self._config.get("cache_enabled", True)
        self._strict_mode = self._config.get("strict_mode", False)
        self._output_dir = self._config.get("output_dir", "./generated")

        # Initialize components
        self._parser = ManifestParser()
        self._resolver = DependencyResolver()
        self._analyzer = GapAnalyzer()
        self._wirer = BlockWirer()

        logger.info("ComposerEngine initialized")

    async def compose(self, manifest_path: str) -> CompositionResult:
        """
        Compose a system from a manifest file.

        Args:
            manifest_path: Path to compose.yaml

        Returns:
            CompositionResult with wired system and generated code
        """
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        glue_code = []

        try:
            # Step 1: Parse manifest (AC-1)
            logger.info(f"Parsing manifest: {manifest_path}")
            manifest = self._parser.parse(manifest_path)

            validation = self._parser.validate(manifest)
            if not validation.valid:
                errors.extend(validation.errors)
            warnings.extend(validation.warnings)

            if errors and self._strict_mode:
                return self._error_result(manifest, errors, warnings, start_time)

            # Step 2: Resolve dependencies (AC-2)
            logger.info("Resolving dependencies...")
            resolved = self._resolver.resolve(manifest)

            if resolved.unresolved:
                warnings.append(f"Unresolved blocks: {resolved.unresolved}")

            # Step 3: Analyze gaps (AC-3)
            logger.info("Analyzing gaps...")
            gaps = self._analyzer.analyze(manifest, resolved)

            if gaps.has_critical_gaps() and not gaps.can_proceed:
                errors.append(f"Critical gaps prevent composition: {gaps.critical_count}")
                if self._strict_mode:
                    return self._error_result(manifest, errors, warnings, start_time, resolved, gaps)

            # Step 4: Wire blocks (AC-4)
            logger.info("Wiring blocks...")
            wired_system = self._wirer.wire(resolved)

            wiring_validation = self._wirer.validate_wiring(wired_system)
            if not wiring_validation.valid:
                errors.extend(wiring_validation.errors)
            warnings.extend(wiring_validation.warnings)

            # Step 5: Generate glue code (AC-5)
            logger.info("Generating glue code...")
            glue_code = self._generate_glue_code(gaps)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(f"Composition complete in {duration_ms:.2f}ms")

            return CompositionResult(
                success=len(errors) == 0 or not self._strict_mode,
                manifest=manifest,
                resolved=resolved,
                gaps=gaps,
                wired_system=wired_system,
                glue_code=glue_code,
                errors=errors,
                warnings=warnings,
                timestamp=start_time.isoformat(),
                duration_ms=duration_ms
            )

        except FileNotFoundError as e:
            errors.append(f"Manifest not found: {manifest_path}")
            return self._error_result(None, errors, warnings, start_time)

        except Exception as e:
            logger.error(f"Composition failed: {e}")
            errors.append(str(e))
            return self._error_result(None, errors, warnings, start_time)

    def compose_from_dict(self, manifest_dict: Dict[str, Any]) -> CompositionResult:
        """Compose from a dictionary manifest (sync version)"""
        import asyncio

        # Create temporary manifest
        manifest = self._parser.parse_dict(manifest_dict)

        start_time = datetime.utcnow()
        errors = []
        warnings = []
        glue_code = []

        try:
            # Validate
            validation = self._parser.validate(manifest)
            if not validation.valid:
                errors.extend(validation.errors)
            warnings.extend(validation.warnings)

            # Resolve
            resolved = self._resolver.resolve(manifest)

            # Analyze
            gaps = self._analyzer.analyze(manifest, resolved)

            # Wire
            wired_system = self._wirer.wire(resolved)

            # Generate glue
            glue_code = self._generate_glue_code(gaps)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            return CompositionResult(
                success=len(errors) == 0,
                manifest=manifest,
                resolved=resolved,
                gaps=gaps,
                wired_system=wired_system,
                glue_code=glue_code,
                errors=errors,
                warnings=warnings,
                timestamp=start_time.isoformat(),
                duration_ms=duration_ms
            )

        except Exception as e:
            errors.append(str(e))
            return self._error_result(manifest, errors, warnings, start_time)

    def _generate_glue_code(self, gaps: GapAnalysis) -> List[GlueCode]:
        """
        Generate minimal glue code for identified gaps.

        Only generates code for:
        - Explicit generation requirements
        - Adapters between incompatible interfaces
        - Custom logic gaps
        """
        glue_code = []

        for gap in gaps.gaps:
            if gap.gap_type == GapType.EXPLICIT:
                code = self._generate_explicit(gap)
                if code:
                    glue_code.append(code)

            elif gap.gap_type == GapType.ADAPTER:
                code = self._generate_adapter(gap)
                if code:
                    glue_code.append(code)

            elif gap.gap_type == GapType.INTERFACE_MISMATCH:
                code = self._generate_interface_adapter(gap)
                if code:
                    glue_code.append(code)

        return glue_code

    def _generate_explicit(self, gap: Gap) -> Optional[GlueCode]:
        """Generate code for explicit generation requirement"""
        name = gap.gap_id.replace("generate-", "")

        code = f'''"""
Auto-generated component: {name}
Generated by Composer Engine for gap: {gap.gap_id}
"""

from typing import Dict, Any, Optional


class {name}:
    """
    {gap.description}

    This component was explicitly requested in compose.yaml.
    Implement the required functionality.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {{}}

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the component logic.

        Args:
            inputs: Input data

        Returns:
            Output data
        """
        # TODO: Implement {name} logic
        return {{"status": "not_implemented", "component": "{name}"}}
'''

        return GlueCode(
            gap_id=gap.gap_id,
            code=code,
            file_path=f"{self._output_dir}/{name.lower()}.py",
            description=gap.description
        )

    def _generate_adapter(self, gap: Gap) -> Optional[GlueCode]:
        """Generate adapter for version conflict"""
        blocks = "_".join(gap.affected_blocks)
        name = f"Adapter_{blocks}"

        code = f'''"""
Auto-generated adapter: {name}
Generated by Composer Engine for gap: {gap.gap_id}
"""

from typing import Dict, Any


class {name}:
    """
    Adapter to bridge version conflict.

    Affected blocks: {gap.affected_blocks}
    """

    def __init__(self):
        self._sources = {{}}

    def register_source(self, name: str, instance: Any):
        """Register a source block"""
        self._sources[name] = instance

    def adapt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt data between incompatible versions"""
        # TODO: Implement version adaptation logic
        return data
'''

        return GlueCode(
            gap_id=gap.gap_id,
            code=code,
            file_path=f"{self._output_dir}/adapters/{name.lower()}.py",
            description=gap.description
        )

    def _generate_interface_adapter(self, gap: Gap) -> Optional[GlueCode]:
        """Generate adapter for interface mismatch"""
        interface = gap.interface_required or "Unknown"
        blocks = "_".join(gap.affected_blocks)
        name = f"InterfaceAdapter_{blocks}"

        code = f'''"""
Auto-generated interface adapter: {name}
Generated by Composer Engine for gap: {gap.gap_id}
"""

from typing import Dict, Any


class {name}:
    """
    Adapter for interface mismatch.

    Required interface: {interface}
    Affected blocks: {gap.affected_blocks}
    """

    def __init__(self, source: Any, target: Any):
        self._source = source
        self._target = target

    def adapt_call(self, method: str, *args, **kwargs) -> Any:
        """Adapt a method call between interfaces"""
        # TODO: Implement interface adaptation
        source_method = getattr(self._source, method, None)
        if source_method:
            result = source_method(*args, **kwargs)
            return self._transform_result(result)
        raise AttributeError(f"Method {{method}} not found")

    def _transform_result(self, result: Any) -> Any:
        """Transform result to target interface format"""
        return result
'''

        return GlueCode(
            gap_id=gap.gap_id,
            code=code,
            file_path=f"{self._output_dir}/adapters/{name.lower()}.py",
            description=gap.description
        )

    def _error_result(
        self,
        manifest: Optional[CompositionManifest],
        errors: List[str],
        warnings: List[str],
        start_time: datetime,
        resolved: Optional[ResolvedDependencies] = None,
        gaps: Optional[GapAnalysis] = None
    ) -> CompositionResult:
        """Create error result"""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return CompositionResult(
            success=False,
            manifest=manifest,
            resolved=resolved,
            gaps=gaps,
            wired_system=None,
            glue_code=[],
            errors=errors,
            warnings=warnings,
            timestamp=start_time.isoformat(),
            duration_ms=duration_ms
        )

    def save_glue_code(self, result: CompositionResult) -> List[str]:
        """Save generated glue code to files"""
        saved_files = []

        for glue in result.glue_code:
            if glue.file_path:
                path = Path(glue.file_path)
                path.parent.mkdir(parents=True, exist_ok=True)

                with open(path, 'w') as f:
                    f.write(glue.code)

                saved_files.append(str(path))
                logger.info(f"Saved glue code: {path}")

        return saved_files

    def get_composition_summary(self, result: CompositionResult) -> str:
        """Generate human-readable summary of composition"""
        stats = result.get_statistics()

        lines = [
            "=" * 50,
            "COMPOSITION SUMMARY",
            "=" * 50,
            f"Status: {'SUCCESS' if result.success else 'FAILED'}",
            f"Duration: {result.duration_ms:.2f}ms",
            "",
            "Statistics:",
            f"  Blocks Composed: {stats['blocks_composed']}",
            f"  Blocks Unresolved: {stats['blocks_unresolved']}",
            f"  Gaps Identified: {stats['gaps_identified']}",
            f"  Critical Gaps: {stats['gaps_critical']}",
            f"  Glue Code Generated: {stats['glue_code_generated']}",
            f"  Connections Made: {stats['connections']}",
            "",
        ]

        if result.errors:
            lines.append("Errors:")
            for err in result.errors:
                lines.append(f"  - {err}")
            lines.append("")

        if result.warnings:
            lines.append("Warnings:")
            for warn in result.warnings:
                lines.append(f"  - {warn}")
            lines.append("")

        if result.wired_system:
            lines.append("Entry Points: " + ", ".join(result.wired_system.entry_points))
            lines.append("Exit Points: " + ", ".join(result.wired_system.exit_points))

        lines.append("=" * 50)

        return "\n".join(lines)
