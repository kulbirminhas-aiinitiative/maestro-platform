"""
Gap Analysis Module for External Projects

This module provides tools for scanning external codebases and analyzing
gaps against best practices.

EPIC: MD-3022 - External Project Gap Analysis Scanner

Components:
- ExternalProjectScanner: Scans external project directories
- ExternalGapAnalyzer: Analyzes scan results for gaps
- RepoManager: Manages repository cloning and caching (MD-2920)
- VisionAnalyzer: AI-powered code analysis (MD-2921)
- GapEngine: Core orchestration engine (MD-2922)
"""
from .external_scanner import (
    ExternalProjectScanner,
    ScannerConfig,
    ScanResult,
    ScanStatus,
    FileAnalysis,
    FileMetrics,
    ProjectMetrics,
    DependencyInfo,
    FileType,
    create_external_scanner,
)

from .external_analyzer import (
    ExternalGapAnalyzer,
    AnalyzerConfig,
    GapAnalysisResult,
    Gap,
    GapSeverity,
    GapCategory,
    GapSuggestion,
    AnalysisScore,
    create_gap_analyzer,
)

from .repo_manager import (
    RepoManager,
    RepoConfig,
    RepoInfo,
    RepoSource,
    RepoStatus,
    CloneResult,
    create_repo_manager,
)

from .vision_analyzer import (
    VisionAnalyzer,
    VisionConfig,
    VisionAnalysisResult,
    PatternMatch,
    CodePattern,
    CodeQuality,
    QualityIndicator,
    ArchitectureAnalysis,
    ArchitectureStyle,
    create_vision_analyzer,
)

from .gap_engine import (
    GapEngine,
    GapEngineConfig,
    GapEngineResult,
    EngineStatus,
    Recommendation,
    RecommendationPriority,
    HealthScore,
    create_gap_engine,
)

__all__ = [
    # Scanner exports
    "ExternalProjectScanner",
    "ScannerConfig",
    "ScanResult",
    "ScanStatus",
    "FileAnalysis",
    "FileMetrics",
    "ProjectMetrics",
    "DependencyInfo",
    "FileType",
    "create_external_scanner",
    # Analyzer exports
    "ExternalGapAnalyzer",
    "AnalyzerConfig",
    "GapAnalysisResult",
    "Gap",
    "GapSeverity",
    "GapCategory",
    "GapSuggestion",
    "AnalysisScore",
    "create_gap_analyzer",
    # Repo Manager exports (MD-2920)
    "RepoManager",
    "RepoConfig",
    "RepoInfo",
    "RepoSource",
    "RepoStatus",
    "CloneResult",
    "create_repo_manager",
    # Vision Analyzer exports (MD-2921)
    "VisionAnalyzer",
    "VisionConfig",
    "VisionAnalysisResult",
    "PatternMatch",
    "CodePattern",
    "CodeQuality",
    "QualityIndicator",
    "ArchitectureAnalysis",
    "ArchitectureStyle",
    "create_vision_analyzer",
    # Gap Engine exports (MD-2922)
    "GapEngine",
    "GapEngineConfig",
    "GapEngineResult",
    "EngineStatus",
    "Recommendation",
    "RecommendationPriority",
    "HealthScore",
    "create_gap_engine",
]
