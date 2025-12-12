"""
Vision Analyzer for External Project Gap Analysis.

Uses AI-powered analysis to understand code structure, patterns, and quality.

EPIC: MD-3022
Child Task: MD-2921
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CodePattern(Enum):
    """Detected code patterns."""
    MVC = "mvc"
    REPOSITORY = "repository"
    FACTORY = "factory"
    SINGLETON = "singleton"
    OBSERVER = "observer"
    DECORATOR = "decorator"
    STRATEGY = "strategy"
    SERVICE_LAYER = "service_layer"
    DEPENDENCY_INJECTION = "dependency_injection"
    EVENT_DRIVEN = "event_driven"
    MICROSERVICES = "microservices"
    MONOLITH = "monolith"


class CodeQuality(Enum):
    """Code quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class ArchitectureStyle(Enum):
    """Architecture styles."""
    LAYERED = "layered"
    HEXAGONAL = "hexagonal"
    CLEAN = "clean"
    ONION = "onion"
    EVENT_SOURCING = "event_sourcing"
    CQRS = "cqrs"
    SERVERLESS = "serverless"
    TRADITIONAL = "traditional"


@dataclass
class PatternMatch:
    """Detected pattern match."""
    pattern: CodePattern
    confidence: float  # 0.0 to 1.0
    locations: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern.value,
            "confidence": self.confidence,
            "locations": self.locations,
            "evidence": self.evidence[:5],  # Limit evidence
        }


@dataclass
class QualityIndicator:
    """Code quality indicator."""
    name: str
    score: float  # 0.0 to 100.0
    description: str
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "description": self.description,
            "recommendations": self.recommendations,
        }


@dataclass
class ArchitectureAnalysis:
    """Architecture analysis result."""
    primary_style: ArchitectureStyle
    confidence: float
    detected_layers: List[str]
    coupling_score: float  # 0.0 (tight) to 100.0 (loose)
    cohesion_score: float  # 0.0 (low) to 100.0 (high)
    modularity_score: float
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_style": self.primary_style.value,
            "confidence": self.confidence,
            "detected_layers": self.detected_layers,
            "coupling_score": self.coupling_score,
            "cohesion_score": self.cohesion_score,
            "modularity_score": self.modularity_score,
            "recommendations": self.recommendations,
        }


@dataclass
class VisionAnalysisResult:
    """Complete vision analysis result."""
    project_path: str
    patterns: List[PatternMatch]
    quality_indicators: List[QualityIndicator]
    architecture: Optional[ArchitectureAnalysis]
    overall_quality: CodeQuality
    overall_score: float
    insights: List[str]
    analyzed_files: int
    analysis_time_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "patterns": [p.to_dict() for p in self.patterns],
            "quality_indicators": [q.to_dict() for q in self.quality_indicators],
            "architecture": self.architecture.to_dict() if self.architecture else None,
            "overall_quality": self.overall_quality.value,
            "overall_score": self.overall_score,
            "insights": self.insights,
            "analyzed_files": self.analyzed_files,
            "analysis_time_seconds": self.analysis_time_seconds,
        }


@dataclass
class VisionConfig:
    """Configuration for vision analyzer."""
    max_files: int = 500
    max_file_size_kb: int = 500
    analyze_patterns: bool = True
    analyze_quality: bool = True
    analyze_architecture: bool = True
    min_confidence: float = 0.5
    file_extensions: Set[str] = field(default_factory=lambda: {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb"
    })


class VisionAnalyzer:
    """
    AI-powered code analysis for understanding project structure and quality.

    Analyzes:
    - Design patterns used
    - Code quality metrics
    - Architecture style
    - Best practices adherence
    """

    # Pattern detection rules
    PATTERN_INDICATORS = {
        CodePattern.MVC: {
            "dirs": ["controllers", "views", "models"],
            "files": ["controller.py", "view.py", "model.py"],
            "keywords": ["Controller", "View", "Model", "render", "template"],
        },
        CodePattern.REPOSITORY: {
            "dirs": ["repositories", "repos"],
            "files": ["repository.py", "repo.py"],
            "keywords": ["Repository", "find_by", "find_all", "save", "delete"],
        },
        CodePattern.FACTORY: {
            "dirs": ["factories"],
            "files": ["factory.py"],
            "keywords": ["Factory", "create_", "build_", "make_"],
        },
        CodePattern.SERVICE_LAYER: {
            "dirs": ["services", "service"],
            "files": ["service.py", "services.py"],
            "keywords": ["Service", "Handler", "Manager", "Processor"],
        },
        CodePattern.DEPENDENCY_INJECTION: {
            "dirs": ["di", "injection", "container"],
            "files": ["container.py", "injector.py"],
            "keywords": ["@inject", "Inject", "Container", "Provider", "bind"],
        },
        CodePattern.EVENT_DRIVEN: {
            "dirs": ["events", "handlers", "listeners"],
            "files": ["event.py", "handler.py", "listener.py"],
            "keywords": ["Event", "emit", "subscribe", "publish", "Listener", "Handler"],
        },
    }

    # Quality metrics
    QUALITY_METRICS = [
        "documentation_coverage",
        "test_coverage",
        "code_complexity",
        "naming_conventions",
        "error_handling",
        "type_hints",
        "dependency_management",
    ]

    def __init__(self, config: Optional[VisionConfig] = None):
        """Initialize the vision analyzer."""
        self.config = config or VisionConfig()
        self._files_analyzed = 0

    def analyze(self, project_path: str) -> VisionAnalysisResult:
        """
        Perform comprehensive vision analysis on a project.

        Args:
            project_path: Path to project root

        Returns:
            VisionAnalysisResult with analysis findings
        """
        import time
        start_time = time.time()

        path = Path(project_path)
        if not path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Collect files
        files = self._collect_files(path)
        self._files_analyzed = len(files)

        # Analyze patterns
        patterns = []
        if self.config.analyze_patterns:
            patterns = self._detect_patterns(path, files)

        # Analyze quality
        quality_indicators = []
        if self.config.analyze_quality:
            quality_indicators = self._analyze_quality(path, files)

        # Analyze architecture
        architecture = None
        if self.config.analyze_architecture:
            architecture = self._analyze_architecture(path, files, patterns)

        # Calculate overall score
        overall_score = self._calculate_overall_score(quality_indicators)
        overall_quality = self._score_to_quality(overall_score)

        # Generate insights
        insights = self._generate_insights(patterns, quality_indicators, architecture)

        analysis_time = time.time() - start_time

        return VisionAnalysisResult(
            project_path=str(project_path),
            patterns=patterns,
            quality_indicators=quality_indicators,
            architecture=architecture,
            overall_quality=overall_quality,
            overall_score=overall_score,
            insights=insights,
            analyzed_files=self._files_analyzed,
            analysis_time_seconds=analysis_time,
        )

    def _collect_files(self, path: Path) -> List[Path]:
        """Collect analyzable files from project."""
        files = []
        for ext in self.config.file_extensions:
            files.extend(path.rglob(f"*{ext}"))

        # Filter by size and limit
        filtered = []
        for f in files:
            try:
                if f.stat().st_size <= self.config.max_file_size_kb * 1024:
                    filtered.append(f)
                    if len(filtered) >= self.config.max_files:
                        break
            except Exception:
                continue

        return filtered

    def _detect_patterns(self, root: Path, files: List[Path]) -> List[PatternMatch]:
        """Detect design patterns in the project."""
        patterns = []

        # Get directory names
        dirs = set()
        for f in files:
            for parent in f.parents:
                if parent != root:
                    dirs.add(parent.name.lower())

        # Check each pattern
        for pattern, indicators in self.PATTERN_INDICATORS.items():
            evidence = []
            locations = []

            # Check directories
            for d in indicators.get("dirs", []):
                if d.lower() in dirs:
                    evidence.append(f"Directory '{d}' exists")
                    locations.append(f"*/{d}/")

            # Check file names
            file_names = {f.name.lower() for f in files}
            for fn in indicators.get("files", []):
                if fn.lower() in file_names:
                    evidence.append(f"File '{fn}' exists")

            # Check keywords in file contents (sample)
            keywords_found = self._scan_for_keywords(
                files[:50],  # Sample first 50 files
                indicators.get("keywords", []),
            )
            evidence.extend(keywords_found)

            # Calculate confidence
            if evidence:
                confidence = min(1.0, len(evidence) / 5)  # 5 evidence points = 100%
                if confidence >= self.config.min_confidence:
                    patterns.append(PatternMatch(
                        pattern=pattern,
                        confidence=confidence,
                        locations=locations,
                        evidence=evidence,
                    ))

        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns

    def _scan_for_keywords(self, files: List[Path], keywords: List[str]) -> List[str]:
        """Scan files for keywords."""
        found = []
        for f in files:
            try:
                content = f.read_text(errors="ignore")
                for kw in keywords:
                    if kw in content:
                        found.append(f"Keyword '{kw}' found in {f.name}")
                        break  # One match per file is enough
            except Exception:
                continue
        return found[:10]  # Limit evidence

    def _analyze_quality(self, root: Path, files: List[Path]) -> List[QualityIndicator]:
        """Analyze code quality metrics."""
        indicators = []

        # Documentation coverage
        doc_score, doc_recs = self._check_documentation(files)
        indicators.append(QualityIndicator(
            name="Documentation Coverage",
            score=doc_score,
            description="Percentage of modules with docstrings",
            recommendations=doc_recs,
        ))

        # Test coverage presence
        test_score, test_recs = self._check_tests(root)
        indicators.append(QualityIndicator(
            name="Test Presence",
            score=test_score,
            description="Presence and organization of tests",
            recommendations=test_recs,
        ))

        # Code complexity (simplified)
        complexity_score, complexity_recs = self._check_complexity(files)
        indicators.append(QualityIndicator(
            name="Code Complexity",
            score=complexity_score,
            description="Average function/method complexity",
            recommendations=complexity_recs,
        ))

        # Naming conventions
        naming_score, naming_recs = self._check_naming(files)
        indicators.append(QualityIndicator(
            name="Naming Conventions",
            score=naming_score,
            description="Adherence to naming conventions",
            recommendations=naming_recs,
        ))

        # Error handling
        error_score, error_recs = self._check_error_handling(files)
        indicators.append(QualityIndicator(
            name="Error Handling",
            score=error_score,
            description="Presence of proper error handling",
            recommendations=error_recs,
        ))

        return indicators

    def _check_documentation(self, files: List[Path]) -> tuple:
        """Check documentation coverage."""
        total = 0
        documented = 0
        recs = []

        for f in files:
            if f.suffix == ".py":
                try:
                    content = f.read_text(errors="ignore")
                    total += 1
                    if '"""' in content or "'''" in content:
                        documented += 1
                except Exception:
                    continue

        score = (documented / total * 100) if total > 0 else 0

        if score < 50:
            recs.append("Add docstrings to modules and functions")
        if score < 80:
            recs.append("Consider adding type hints to function signatures")

        return score, recs

    def _check_tests(self, root: Path) -> tuple:
        """Check test presence and organization."""
        test_dirs = list(root.glob("**/test*")) + list(root.glob("**/tests"))
        test_files = list(root.glob("**/test_*.py")) + list(root.glob("**/*_test.py"))

        score = 0
        recs = []

        if test_dirs:
            score += 40
        if test_files:
            score += 30
            if len(test_files) > 10:
                score += 30

        if score < 40:
            recs.append("Create a tests/ directory")
            recs.append("Add unit tests for core functionality")
        elif score < 70:
            recs.append("Increase test coverage")
            recs.append("Add integration tests")

        return min(100, score), recs

    def _check_complexity(self, files: List[Path]) -> tuple:
        """Check code complexity (simplified analysis)."""
        long_functions = 0
        total_functions = 0
        recs = []

        for f in files:
            if f.suffix == ".py":
                try:
                    content = f.read_text(errors="ignore")
                    # Count function definitions
                    funcs = re.findall(r"def \w+\([^)]*\):", content)
                    total_functions += len(funcs)

                    # Check for long functions (> 50 lines indicator)
                    lines = content.split("\n")
                    if len(lines) > 500:
                        long_functions += 1
                except Exception:
                    continue

        # Higher score = lower complexity
        if total_functions > 0:
            complexity_ratio = long_functions / (total_functions / 10 + 1)
            score = max(0, 100 - (complexity_ratio * 20))
        else:
            score = 70  # Default

        if score < 60:
            recs.append("Break down large functions into smaller units")
            recs.append("Consider extracting helper functions")

        return score, recs

    def _check_naming(self, files: List[Path]) -> tuple:
        """Check naming conventions."""
        good_names = 0
        total_names = 0
        recs = []

        snake_case = re.compile(r"^[a-z][a-z0-9_]*$")
        pascal_case = re.compile(r"^[A-Z][a-zA-Z0-9]*$")

        for f in files:
            if f.suffix == ".py":
                try:
                    content = f.read_text(errors="ignore")

                    # Check function names
                    funcs = re.findall(r"def (\w+)\(", content)
                    for func in funcs:
                        total_names += 1
                        if snake_case.match(func) or func.startswith("_"):
                            good_names += 1

                    # Check class names
                    classes = re.findall(r"class (\w+)", content)
                    for cls in classes:
                        total_names += 1
                        if pascal_case.match(cls):
                            good_names += 1
                except Exception:
                    continue

        score = (good_names / total_names * 100) if total_names > 0 else 80

        if score < 80:
            recs.append("Use snake_case for functions and variables")
            recs.append("Use PascalCase for class names")

        return score, recs

    def _check_error_handling(self, files: List[Path]) -> tuple:
        """Check error handling patterns."""
        try_blocks = 0
        bare_excepts = 0
        recs = []

        for f in files:
            if f.suffix == ".py":
                try:
                    content = f.read_text(errors="ignore")
                    try_blocks += len(re.findall(r"\btry\s*:", content))
                    bare_excepts += len(re.findall(r"\bexcept\s*:", content))
                except Exception:
                    continue

        if try_blocks > 0:
            score = max(0, 100 - (bare_excepts / try_blocks * 50))
        else:
            score = 50
            recs.append("Add try-except blocks for error-prone operations")

        if bare_excepts > 0:
            recs.append("Avoid bare 'except:' clauses - catch specific exceptions")

        return score, recs

    def _analyze_architecture(
        self,
        root: Path,
        files: List[Path],
        patterns: List[PatternMatch],
    ) -> ArchitectureAnalysis:
        """Analyze project architecture."""
        # Detect layers
        layers = []
        layer_indicators = {
            "presentation": ["views", "controllers", "api", "routes", "handlers"],
            "business": ["services", "domain", "core", "logic"],
            "data": ["repositories", "models", "database", "db", "storage"],
            "infrastructure": ["infrastructure", "infra", "adapters", "external"],
        }

        dirs = {p.name.lower() for f in files for p in f.parents if p != root}

        for layer, indicators in layer_indicators.items():
            if any(ind in dirs for ind in indicators):
                layers.append(layer)

        # Determine architecture style
        if len(layers) >= 3:
            style = ArchitectureStyle.LAYERED
            confidence = 0.8
        elif "adapters" in dirs or "ports" in dirs:
            style = ArchitectureStyle.HEXAGONAL
            confidence = 0.7
        elif len(patterns) > 3:
            style = ArchitectureStyle.CLEAN
            confidence = 0.6
        else:
            style = ArchitectureStyle.TRADITIONAL
            confidence = 0.5

        # Calculate scores (simplified)
        coupling_score = 70 if len(layers) >= 2 else 50
        cohesion_score = 75 if len(patterns) >= 2 else 55
        modularity_score = len(layers) * 20 + len(patterns) * 10

        recs = []
        if coupling_score < 70:
            recs.append("Consider separating concerns into distinct layers")
        if cohesion_score < 70:
            recs.append("Group related functionality together")

        return ArchitectureAnalysis(
            primary_style=style,
            confidence=confidence,
            detected_layers=layers,
            coupling_score=min(100, coupling_score),
            cohesion_score=min(100, cohesion_score),
            modularity_score=min(100, modularity_score),
            recommendations=recs,
        )

    def _calculate_overall_score(self, indicators: List[QualityIndicator]) -> float:
        """Calculate overall quality score."""
        if not indicators:
            return 50.0
        return sum(i.score for i in indicators) / len(indicators)

    def _score_to_quality(self, score: float) -> CodeQuality:
        """Convert score to quality level."""
        if score >= 90:
            return CodeQuality.EXCELLENT
        elif score >= 75:
            return CodeQuality.GOOD
        elif score >= 60:
            return CodeQuality.ACCEPTABLE
        elif score >= 40:
            return CodeQuality.NEEDS_IMPROVEMENT
        else:
            return CodeQuality.POOR

    def _generate_insights(
        self,
        patterns: List[PatternMatch],
        indicators: List[QualityIndicator],
        architecture: Optional[ArchitectureAnalysis],
    ) -> List[str]:
        """Generate human-readable insights."""
        insights = []

        if patterns:
            top_patterns = [p.pattern.value for p in patterns[:3]]
            insights.append(f"Primary patterns detected: {', '.join(top_patterns)}")

        if indicators:
            low_scores = [i for i in indicators if i.score < 60]
            if low_scores:
                areas = [i.name for i in low_scores]
                insights.append(f"Areas needing improvement: {', '.join(areas)}")

            high_scores = [i for i in indicators if i.score >= 80]
            if high_scores:
                areas = [i.name for i in high_scores]
                insights.append(f"Strong areas: {', '.join(areas)}")

        if architecture:
            insights.append(
                f"Architecture style: {architecture.primary_style.value} "
                f"(confidence: {architecture.confidence:.0%})"
            )
            if architecture.detected_layers:
                insights.append(f"Detected layers: {', '.join(architecture.detected_layers)}")

        return insights


def create_vision_analyzer(config: Optional[Dict[str, Any]] = None) -> VisionAnalyzer:
    """
    Factory function to create a VisionAnalyzer instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured VisionAnalyzer instance
    """
    if config:
        vision_config = VisionConfig(
            max_files=config.get("max_files", 500),
            max_file_size_kb=config.get("max_file_size_kb", 500),
            analyze_patterns=config.get("analyze_patterns", True),
            analyze_quality=config.get("analyze_quality", True),
            analyze_architecture=config.get("analyze_architecture", True),
            min_confidence=config.get("min_confidence", 0.5),
        )
    else:
        vision_config = VisionConfig()

    return VisionAnalyzer(vision_config)
