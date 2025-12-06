"""
ManifestParser - AC-1: Parse compose.yaml manifest

Parses YAML manifest files that declare block composition and
identifies components requiring generation.

Reference: MD-2508 Acceptance Criterion 1
"""

import yaml
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import re

logger = logging.getLogger(__name__)


@dataclass
class BlockReference:
    """Reference to a block with version specification"""
    block_id: str
    version: str
    config: Optional[Dict[str, Any]] = None
    alias: Optional[str] = None

    @classmethod
    def from_string(cls, spec: str) -> 'BlockReference':
        """
        Parse block reference from string format.

        Formats:
        - "block-id@1.2.3"
        - "block-id@^1.0.0"
        - "block-id@~1.2.0"
        """
        match = re.match(r'^([a-zA-Z0-9_-]+)@(.+)$', spec)
        if not match:
            raise ValueError(f"Invalid block reference format: {spec}")

        return cls(
            block_id=match.group(1),
            version=match.group(2)
        )

    def to_string(self) -> str:
        """Convert to string format"""
        return f"{self.block_id}@{self.version}"


@dataclass
class GenerationSpec:
    """Specification for component requiring generation"""
    name: str
    type: str = "component"
    interface: Optional[str] = None
    description: Optional[str] = None


@dataclass
class CompositionManifest:
    """
    Parsed composition manifest.

    Example compose.yaml:
        version: "1.0"
        compose:
          - logging@1.2.3
          - jira-adapter@3.1.0
        generate:
          - VerbosityController
        config:
          timeout: 30
    """
    version: str
    compose: List[BlockReference]
    generate: List[GenerationSpec]
    config: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_block(self, block_id: str) -> Optional[BlockReference]:
        """Get block reference by ID"""
        for block in self.compose:
            if block.block_id == block_id:
                return block
        return None

    def get_block_ids(self) -> List[str]:
        """Get list of all block IDs"""
        return [b.block_id for b in self.compose]


@dataclass
class ValidationResult:
    """Result of manifest validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ManifestParser:
    """
    Parser for compose.yaml manifests.

    Implements AC-1: Parse compose.yaml manifest

    Features:
    - Parse YAML manifest files
    - Validate manifest structure
    - Support for version ranges (^, ~)
    - Extract block references and generation specs
    """

    SUPPORTED_VERSIONS = ["1.0", "1.1"]

    def __init__(self):
        logger.info("ManifestParser initialized")

    def parse(self, path: str) -> CompositionManifest:
        """
        Parse a compose.yaml manifest file.

        Args:
            path: Path to compose.yaml file

        Returns:
            CompositionManifest with parsed content

        Raises:
            FileNotFoundError: If manifest file not found
            ValueError: If manifest is invalid
        """
        manifest_path = Path(path)

        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")

        with open(manifest_path, 'r') as f:
            raw = yaml.safe_load(f)

        return self.parse_dict(raw)

    def parse_dict(self, raw: Dict[str, Any]) -> CompositionManifest:
        """
        Parse manifest from dictionary.

        Args:
            raw: Raw dictionary from YAML

        Returns:
            CompositionManifest
        """
        # Extract version
        version = str(raw.get("version", "1.0"))

        # Parse compose blocks
        compose_raw = raw.get("compose", [])
        compose = []

        for item in compose_raw:
            if isinstance(item, str):
                # Simple string format: "block@version"
                compose.append(BlockReference.from_string(item))
            elif isinstance(item, dict):
                # Extended format with config
                block_spec = item.get("block", "")
                if "@" in block_spec:
                    ref = BlockReference.from_string(block_spec)
                else:
                    ref = BlockReference(
                        block_id=block_spec,
                        version=item.get("version", "latest")
                    )
                ref.config = item.get("config")
                ref.alias = item.get("alias")
                compose.append(ref)

        # Parse generate specs
        generate_raw = raw.get("generate", [])
        generate = []

        for item in generate_raw:
            if isinstance(item, str):
                generate.append(GenerationSpec(name=item))
            elif isinstance(item, dict):
                generate.append(GenerationSpec(
                    name=item.get("name", "Unknown"),
                    type=item.get("type", "component"),
                    interface=item.get("interface"),
                    description=item.get("description")
                ))

        # Extract config
        config = raw.get("config", {})

        # Extract metadata
        metadata = raw.get("metadata", {})

        manifest = CompositionManifest(
            version=version,
            compose=compose,
            generate=generate,
            config=config,
            metadata=metadata
        )

        logger.info(f"Parsed manifest: {len(compose)} blocks, {len(generate)} to generate")
        return manifest

    def parse_string(self, content: str) -> CompositionManifest:
        """Parse manifest from YAML string"""
        raw = yaml.safe_load(content)
        return self.parse_dict(raw)

    def validate(self, manifest: CompositionManifest) -> ValidationResult:
        """
        Validate a composition manifest.

        Args:
            manifest: Manifest to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check version
        if manifest.version not in self.SUPPORTED_VERSIONS:
            warnings.append(f"Unsupported manifest version: {manifest.version}")

        # Check for empty composition
        if not manifest.compose and not manifest.generate:
            errors.append("Manifest must have at least one block to compose or generate")

        # Check for duplicate block IDs
        block_ids = [b.block_id for b in manifest.compose]
        duplicates = [bid for bid in block_ids if block_ids.count(bid) > 1]
        if duplicates:
            errors.append(f"Duplicate block IDs: {set(duplicates)}")

        # Validate version formats
        for block in manifest.compose:
            if not self._is_valid_version(block.version):
                errors.append(f"Invalid version format for {block.block_id}: {block.version}")

        # Check generation specs have names
        for gen in manifest.generate:
            if not gen.name:
                errors.append("Generation spec missing name")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid"""
        # Support exact, caret, tilde, and range patterns
        patterns = [
            r'^\d+\.\d+\.\d+$',       # Exact: 1.2.3
            r'^\^\d+\.\d+\.\d+$',     # Caret: ^1.2.3
            r'^~\d+\.\d+\.\d+$',      # Tilde: ~1.2.3
            r'^>=\d+\.\d+\.\d+',      # Range: >=1.2.3
            r'^latest$',              # Latest
            r'^\*$',                  # Wildcard
        ]

        return any(re.match(p, version) for p in patterns)

    def to_yaml(self, manifest: CompositionManifest) -> str:
        """Convert manifest back to YAML string"""
        data = {
            "version": manifest.version,
            "compose": [b.to_string() for b in manifest.compose],
            "generate": [g.name for g in manifest.generate],
            "config": manifest.config
        }

        if manifest.metadata:
            data["metadata"] = manifest.metadata

        return yaml.dump(data, default_flow_style=False)
