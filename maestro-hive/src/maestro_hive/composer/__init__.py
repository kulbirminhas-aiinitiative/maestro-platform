"""
Maestro Composer Engine - Composition-First SDLC

This module implements the Composer Engine that replaces direct code generation
with block composition and minimal glue code generation.

Components:
- ManifestParser: Parse compose.yaml manifests
- DependencyResolver: Resolve block dependencies from registry
- GapAnalyzer: Identify gaps requiring code generation
- BlockWirer: Wire blocks together via interfaces
- GlueCodeGenerator: Generate minimal connector code

Reference: MD-2508 Composer Engine EPIC
"""

from .manifest_parser import ManifestParser, CompositionManifest, BlockReference
from .dependency_resolver import DependencyResolver, ResolvedDependencies
from .gap_analyzer import GapAnalyzer, GapAnalysis, Gap
from .block_wirer import BlockWirer, WiredSystem, Connection
from .composer_engine import ComposerEngine, CompositionResult

__all__ = [
    # Parser
    "ManifestParser",
    "CompositionManifest",
    "BlockReference",
    # Resolver
    "DependencyResolver",
    "ResolvedDependencies",
    # Gap Analysis
    "GapAnalyzer",
    "GapAnalysis",
    "Gap",
    # Wiring
    "BlockWirer",
    "WiredSystem",
    "Connection",
    # Engine
    "ComposerEngine",
    "CompositionResult",
]
