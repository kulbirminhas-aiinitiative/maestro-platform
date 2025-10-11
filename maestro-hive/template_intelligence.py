#!/usr/bin/env python3
"""
Template Intelligence Layer - Smart Decision Making for Template Management

This module provides intelligent decision-making capabilities for the automated
template workflow system, including:

1. TemplateSimilarityAnalyzer - Finds similar existing templates
2. VariantDecisionEngine - Decides: reuse/variant/new
3. QualityGateValidator - Ensures production-ready templates
4. TemplateFitnessScorer - Tracks template effectiveness

Industry Best Practices Implemented:
- DRY Principle (Don't Repeat Yourself)
- Template Composition over Duplication
- Quality Gates (Syntax, Best Practices, Completeness, Security)
- Similarity Thresholds (Reuse: >80%, Variant: 50-80%, New: <50%)
- SDLC Integration Validation
"""

import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
import math

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SimilarityResult:
    """Result of similarity analysis"""
    template_id: str
    template_name: str
    similarity_score: float  # 0.0 - 1.0
    tfidf_score: float
    structural_score: float
    matching_keywords: List[str]
    recommendation: str  # "reuse", "variant", "new"


@dataclass
class VariantDecision:
    """Decision about template creation strategy"""
    action: str  # "REUSE", "VARIANT", "CREATE_NEW"
    confidence: float  # 0.0 - 1.0
    reasoning: str
    base_template_id: Optional[str] = None
    base_template_name: Optional[str] = None
    parameters_to_change: List[str] = field(default_factory=list)
    similarity_score: float = 0.0


@dataclass
class ValidationResult:
    """Result of quality gate validation"""
    gate_name: str
    passed: bool
    score: float  # 0-100
    issues: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)


@dataclass
class QualityGateReport:
    """Overall quality gate validation report"""
    overall_passed: bool
    overall_score: float  # 0-100
    gate_results: List[ValidationResult] = field(default_factory=list)

    def get_failed_gates(self) -> List[str]:
        return [r.gate_name for r in self.gate_results if not r.passed]


# =============================================================================
# 1. TEMPLATE SIMILARITY ANALYZER
# =============================================================================

class TemplateSimilarityAnalyzer:
    """
    Analyzes similarity between requirements and existing templates

    Uses:
    - TF-IDF for keyword matching
    - Structural similarity (language, framework, category)
    - Combined weighted score

    Thresholds:
    - >= 0.80: High similarity (REUSE)
    - 0.50-0.79: Medium similarity (VARIANT)
    - < 0.50: Low similarity (CREATE NEW)
    """

    def __init__(self, templates_dir: Path = None):
        self.templates_dir = templates_dir or Path("/home/ec2-user/projects/maestro-platform/maestro-templates/storage/templates")
        self.templates_cache: List[Dict[str, Any]] = []
        self.idf_scores: Dict[str, float] = {}

        # Weights for similarity calculation
        self.TFIDF_WEIGHT = 0.50
        self.STRUCTURAL_WEIGHT = 0.30
        self.SEMANTIC_WEIGHT = 0.20

    async def initialize(self):
        """Load all templates and calculate IDF scores"""
        logger.info("📊 Initializing Template Similarity Analyzer...")

        # Load all templates
        self.templates_cache = []
        for persona_dir in self.templates_dir.iterdir():
            if persona_dir.is_dir():
                for template_file in persona_dir.glob("*.json"):
                    try:
                        with open(template_file) as f:
                            template_data = json.load(f)
                            template_data['_file_path'] = str(template_file)
                            self.templates_cache.append(template_data)
                    except Exception as e:
                        logger.warning(f"Failed to load {template_file}: {e}")

        logger.info(f"   Loaded {len(self.templates_cache)} templates")

        # Calculate IDF scores
        self._calculate_idf_scores()
        logger.info(f"   Calculated IDF scores for {len(self.idf_scores)} terms")

    def _calculate_idf_scores(self):
        """Calculate Inverse Document Frequency for all terms"""
        # Collect all terms from all templates
        all_terms = set()
        term_doc_count = Counter()

        for template in self.templates_cache:
            terms = self._extract_terms(template)
            unique_terms = set(terms)
            all_terms.update(unique_terms)

            for term in unique_terms:
                term_doc_count[term] += 1

        # Calculate IDF: log(N / df)
        N = len(self.templates_cache)
        for term in all_terms:
            df = term_doc_count[term]
            self.idf_scores[term] = math.log(N / df) if df > 0 else 0.0

    def _extract_terms(self, template: Dict[str, Any]) -> List[str]:
        """Extract searchable terms from template"""
        metadata = template.get("metadata", {})

        text = " ".join([
            metadata.get("name", ""),
            metadata.get("description", ""),
            " ".join(metadata.get("tags", [])),
            metadata.get("language", ""),
            metadata.get("framework", ""),
            metadata.get("category", ""),
        ]).lower()

        # Tokenize and clean
        terms = re.findall(r'\b\w+\b', text)
        return [t for t in terms if len(t) > 2]  # Filter short words

    async def find_similar_templates(
        self,
        requirement: str,
        persona: Optional[str] = None,
        min_similarity: float = 0.50,
        top_k: int = 5
    ) -> List[SimilarityResult]:
        """
        Find templates similar to the given requirement

        Args:
            requirement: Natural language requirement description
            persona: Filter by persona (optional)
            min_similarity: Minimum similarity threshold
            top_k: Return top K results

        Returns:
            List of similar templates sorted by similarity (highest first)
        """
        if not self.templates_cache:
            await self.initialize()

        results = []
        req_terms = self._extract_terms({"metadata": {"description": requirement}})

        for template in self.templates_cache:
            # Filter by persona if specified
            if persona and template.get("metadata", {}).get("persona") != persona:
                continue

            # Calculate similarity
            tfidf_score = self._calculate_tfidf_similarity(req_terms, template)
            structural_score = self._calculate_structural_similarity(requirement, template)

            # Combined score
            similarity = (
                self.TFIDF_WEIGHT * tfidf_score +
                self.STRUCTURAL_WEIGHT * structural_score +
                self.SEMANTIC_WEIGHT * self._calculate_semantic_similarity(requirement, template)
            )

            if similarity >= min_similarity:
                # Determine recommendation
                if similarity >= 0.80:
                    recommendation = "reuse"
                elif similarity >= 0.50:
                    recommendation = "variant"
                else:
                    recommendation = "new"

                metadata = template.get("metadata", {})
                results.append(SimilarityResult(
                    template_id=metadata.get("id", "unknown"),
                    template_name=metadata.get("name", "Unknown"),
                    similarity_score=round(similarity, 3),
                    tfidf_score=round(tfidf_score, 3),
                    structural_score=round(structural_score, 3),
                    matching_keywords=self._get_matching_keywords(req_terms, template),
                    recommendation=recommendation
                ))

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        return results[:top_k]

    def _calculate_tfidf_similarity(self, req_terms: List[str], template: Dict[str, Any]) -> float:
        """Calculate TF-IDF cosine similarity"""
        template_terms = self._extract_terms(template)

        # Calculate TF-IDF vectors
        req_vector = {}
        template_vector = {}

        # Requirement vector
        req_term_count = Counter(req_terms)
        for term in set(req_terms):
            tf = req_term_count[term] / len(req_terms) if req_terms else 0
            idf = self.idf_scores.get(term, 0.0)
            req_vector[term] = tf * idf

        # Template vector
        template_term_count = Counter(template_terms)
        for term in set(template_terms):
            tf = template_term_count[term] / len(template_terms) if template_terms else 0
            idf = self.idf_scores.get(term, 0.0)
            template_vector[term] = tf * idf

        # Cosine similarity
        dot_product = sum(req_vector.get(term, 0) * template_vector.get(term, 0) for term in set(req_terms + template_terms))

        req_magnitude = math.sqrt(sum(v**2 for v in req_vector.values()))
        template_magnitude = math.sqrt(sum(v**2 for v in template_vector.values()))

        if req_magnitude == 0 or template_magnitude == 0:
            return 0.0

        return dot_product / (req_magnitude * template_magnitude)

    def _calculate_structural_similarity(self, requirement: str, template: Dict[str, Any]) -> float:
        """Calculate structural similarity (language, framework, category match)"""
        req_lower = requirement.lower()
        metadata = template.get("metadata", {})

        score = 0.0
        matches = 0
        total_checks = 0

        # Language match
        language = metadata.get("language", "").lower()
        if language and language in req_lower:
            matches += 1
        total_checks += 1

        # Framework match
        framework = metadata.get("framework", "").lower()
        if framework and framework in req_lower:
            matches += 1
        total_checks += 1

        # Category match
        category = metadata.get("category", "").lower()
        if category and category in req_lower:
            matches += 1
        total_checks += 1

        return matches / total_checks if total_checks > 0 else 0.0

    def _calculate_semantic_similarity(self, requirement: str, template: Dict[str, Any]) -> float:
        """Calculate semantic similarity (use case, pattern match)"""
        req_lower = requirement.lower()
        metadata = template.get("metadata", {})
        description = metadata.get("description", "").lower()

        # Look for pattern keywords
        patterns = [
            "crud", "rest", "graphql", "authentication", "authorization",
            "microservice", "saga", "cqrs", "event-driven", "circuit-breaker",
            "testing", "monitoring", "logging", "deployment", "ci/cd"
        ]

        req_patterns = [p for p in patterns if p in req_lower]
        desc_patterns = [p for p in patterns if p in description]

        if not req_patterns:
            return 0.5  # Neutral score if no patterns detected

        overlap = len(set(req_patterns) & set(desc_patterns))
        return overlap / len(req_patterns)

    def _get_matching_keywords(self, req_terms: List[str], template: Dict[str, Any]) -> List[str]:
        """Get list of matching keywords"""
        template_terms = self._extract_terms(template)
        matches = set(req_terms) & set(template_terms)
        # Return top 10 most important matches (by IDF)
        sorted_matches = sorted(matches, key=lambda t: self.idf_scores.get(t, 0), reverse=True)
        return sorted_matches[:10]


# =============================================================================
# 2. VARIANT DECISION ENGINE
# =============================================================================

class VariantDecisionEngine:
    """
    Decides whether to: REUSE / CREATE VARIANT / CREATE NEW

    Decision Criteria:
    - REUSE (>= 80%): Same pattern, different parameters only
    - VARIANT (50-79%): Similar pattern, different use case/tool
    - CREATE_NEW (< 50%): Fundamentally different pattern

    Based on: DRY principle, Template Composition, Code Reuse best practices
    """

    def __init__(self, similarity_analyzer: TemplateSimilarityAnalyzer):
        self.similarity_analyzer = similarity_analyzer

        # Thresholds
        self.REUSE_THRESHOLD = 0.80
        self.VARIANT_THRESHOLD = 0.50

    async def analyze_requirement(
        self,
        requirement: str,
        persona: Optional[str] = None
    ) -> VariantDecision:
        """
        Analyze requirement and decide on template strategy

        Returns:
            VariantDecision with action: REUSE/VARIANT/CREATE_NEW
        """
        # Find similar templates
        similar_templates = await self.similarity_analyzer.find_similar_templates(
            requirement=requirement,
            persona=persona,
            min_similarity=self.VARIANT_THRESHOLD,
            top_k=3
        )

        if not similar_templates:
            # No similar templates found
            return VariantDecision(
                action="CREATE_NEW",
                confidence=0.95,
                reasoning="No similar templates found (similarity < 50%). Creating new template is the best approach.",
                similarity_score=0.0
            )

        # Get best match
        best_match = similar_templates[0]

        # Decision logic
        if best_match.similarity_score >= self.REUSE_THRESHOLD:
            # REUSE: Very high similarity
            parameters = self._identify_parameters_to_change(requirement, best_match)

            return VariantDecision(
                action="REUSE",
                confidence=0.90,
                reasoning=f"Found highly similar template '{best_match.template_name}' ({best_match.similarity_score:.0%} similar). Recommend parameterizing instead of creating new template.",
                base_template_id=best_match.template_id,
                base_template_name=best_match.template_name,
                parameters_to_change=parameters,
                similarity_score=best_match.similarity_score
            )

        elif best_match.similarity_score >= self.VARIANT_THRESHOLD:
            # VARIANT: Medium similarity
            return VariantDecision(
                action="VARIANT",
                confidence=0.80,
                reasoning=f"Found similar template '{best_match.template_name}' ({best_match.similarity_score:.0%} similar). Recommend creating variant (fork and modify).",
                base_template_id=best_match.template_id,
                base_template_name=best_match.template_name,
                similarity_score=best_match.similarity_score
            )

        else:
            # CREATE_NEW: Low similarity
            return VariantDecision(
                action="CREATE_NEW",
                confidence=0.85,
                reasoning=f"Best match '{best_match.template_name}' has only {best_match.similarity_score:.0%} similarity. Creating new template recommended.",
                similarity_score=best_match.similarity_score
            )

    def _identify_parameters_to_change(self, requirement: str, similar: SimilarityResult) -> List[str]:
        """Identify which parameters would need to change for reuse"""
        req_lower = requirement.lower()
        parameters = []

        # Check for technology changes
        if any(db in req_lower for db in ["postgresql", "mysql", "mongodb", "redis"]):
            parameters.append("DATABASE_TYPE")

        if any(fw in req_lower for fw in ["react", "vue", "angular", "nextjs"]):
            parameters.append("FRAMEWORK")

        if any(lang in req_lower for lang in ["python", "typescript", "javascript", "java", "go"]):
            parameters.append("LANGUAGE")

        if any(auth in req_lower for auth in ["jwt", "oauth", "session", "saml"]):
            parameters.append("AUTH_METHOD")

        return parameters if parameters else ["CONFIGURATION_PARAMETERS"]


# =============================================================================
# 3. QUALITY GATE VALIDATOR
# =============================================================================

class QualityGateValidator:
    """
    Validates templates against production-ready quality gates

    Gates:
    1. Syntax Validation - No syntax errors
    2. Best Practices - Follows conventions
    3. Completeness - Has all required sections
    4. Security - No vulnerabilities
    5. SDLC Integration - Proper documentation

    Minimum Passing Score: 70/100 overall
    """

    def __init__(self):
        self.PASSING_SCORE = 70.0

    async def validate_template(self, template: Dict[str, Any]) -> QualityGateReport:
        """
        Run all quality gates on a template

        Returns:
            QualityGateReport with overall pass/fail and individual gate results
        """
        logger.info(f"🔍 Running quality gates on template...")

        gates = [
            await self.validate_syntax(template),
            await self.check_best_practices(template),
            await self.verify_completeness(template),
            await self.security_scan(template),
            await self.validate_sdlc_integration(template)
        ]

        # Calculate overall score (weighted average)
        weights = [0.25, 0.20, 0.25, 0.20, 0.10]  # Syntax and completeness are most important
        overall_score = sum(gate.score * weight for gate, weight in zip(gates, weights))
        overall_passed = all(gate.passed for gate in gates) and overall_score >= self.PASSING_SCORE

        return QualityGateReport(
            overall_passed=overall_passed,
            overall_score=round(overall_score, 1),
            gate_results=gates
        )

    async def validate_syntax(self, template: Dict[str, Any]) -> ValidationResult:
        """Gate 1: Syntax validation"""
        issues = []
        score = 100.0

        # Check JSON structure
        required_top_level = ["metadata", "content"]
        for key in required_top_level:
            if key not in template:
                issues.append({
                    "severity": "critical",
                    "message": f"Missing required field: {key}"
                })
                score -= 30

        # Check metadata structure
        metadata = template.get("metadata", {})
        required_metadata = ["id", "name", "description", "category", "language", "persona"]
        for key in required_metadata:
            if key not in metadata:
                issues.append({
                    "severity": "high",
                    "message": f"Missing required metadata: {key}"
                })
                score -= 10

        # Check content is not empty
        content = template.get("content", "")
        if not content or len(content.strip()) < 50:
            issues.append({
                "severity": "critical",
                "message": "Content is empty or too short"
            })
            score -= 30

        passed = score >= 70
        return ValidationResult(
            gate_name="Syntax Validation",
            passed=passed,
            score=max(0, score),
            issues=issues,
            critical_issues=[i["message"] for i in issues if i["severity"] == "critical"]
        )

    async def check_best_practices(self, template: Dict[str, Any]) -> ValidationResult:
        """Gate 2: Best practices check"""
        warnings = []
        score = 100.0

        metadata = template.get("metadata", {})
        content = template.get("content", "")

        # Check for quality scores
        quality_fields = ["quality_score", "security_score", "performance_score", "maintainability_score"]
        for field in quality_fields:
            if field not in metadata:
                warnings.append(f"Missing quality metric: {field}")
                score -= 5

        # Check for tags
        if not metadata.get("tags") or len(metadata.get("tags", [])) < 3:
            warnings.append("Should have at least 3 descriptive tags")
            score -= 10

        # Check content follows conventions
        if "TODO" in content or "FIXME" in content:
            warnings.append("Contains TODO/FIXME comments - should be production-ready")
            score -= 10

        # Check for error handling patterns
        error_patterns = ["try", "catch", "except", "error", "Error"]
        if not any(pattern in content for pattern in error_patterns):
            warnings.append("No error handling found - consider adding error handling patterns")
            score -= 10

        # Check for logging
        log_patterns = ["logger", "log", "console", "print"]
        if not any(pattern in content for pattern in log_patterns):
            warnings.append("No logging found - consider adding logging for debugging")
            score -= 5

        passed = score >= 70
        return ValidationResult(
            gate_name="Best Practices",
            passed=passed,
            score=max(0, score),
            warnings=warnings
        )

    async def verify_completeness(self, template: Dict[str, Any]) -> ValidationResult:
        """Gate 3: Completeness check"""
        issues = []
        score = 100.0

        metadata = template.get("metadata", {})

        # Check for variables
        if "variables" not in template:
            issues.append({
                "severity": "medium",
                "message": "No variables defined - template may not be flexible"
            })
            score -= 15

        # Check for workflow context
        if "workflow_context" not in template:
            issues.append({
                "severity": "medium",
                "message": "Missing workflow_context - unclear how to use template"
            })
            score -= 15
        else:
            workflow = template.get("workflow_context", {})
            if "typical_use_cases" not in workflow:
                score -= 5
            if "prerequisites" not in workflow:
                score -= 5
            if "team_composition" not in workflow:
                score -= 5

        # Check description quality
        description = metadata.get("description", "")
        if len(description) < 50:
            issues.append({
                "severity": "medium",
                "message": "Description too short - should be more descriptive"
            })
            score -= 10

        # Check for dependencies
        if "dependencies" not in template:
            issues.append({
                "severity": "low",
                "message": "No dependencies listed"
            })
            score -= 5

        passed = score >= 70
        return ValidationResult(
            gate_name="Completeness",
            passed=passed,
            score=max(0, score),
            issues=issues
        )

    async def security_scan(self, template: Dict[str, Any]) -> ValidationResult:
        """Gate 4: Security scan"""
        issues = []
        score = 100.0

        content = template.get("content", "")

        # Check for hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password found"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key found"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret found"),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded token found"),
        ]

        for pattern, message in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append({
                    "severity": "critical",
                    "message": message
                })
                score -= 25

        # Check for SQL injection risks
        if re.search(r'execute\s*\(\s*["\'].*%s', content, re.IGNORECASE):
            issues.append({
                "severity": "high",
                "message": "Potential SQL injection risk - use parameterized queries"
            })
            score -= 15

        # Check for XSS risks
        if "innerHTML" in content or "dangerouslySetInnerHTML" in content:
            issues.append({
                "severity": "medium",
                "message": "Potential XSS risk - validate and sanitize user input"
            })
            score -= 10

        passed = score >= 70
        critical = [i["message"] for i in issues if i["severity"] == "critical"]

        return ValidationResult(
            gate_name="Security Scan",
            passed=passed,
            score=max(0, score),
            issues=issues,
            critical_issues=critical
        )

    async def validate_sdlc_integration(self, template: Dict[str, Any]) -> ValidationResult:
        """Gate 5: SDLC integration validation"""
        warnings = []
        score = 100.0

        content = template.get("content", "")
        workflow = template.get("workflow_context", {})

        # Check for usage documentation
        doc_keywords = ["usage", "example", "how to", "getting started"]
        has_docs = any(keyword in content.lower() for keyword in doc_keywords)
        if not has_docs:
            warnings.append("Missing usage documentation or examples")
            score -= 15

        # Check for test coverage indication
        test_keywords = ["test", "testing", "coverage"]
        has_test_info = any(keyword in content.lower() for keyword in test_keywords)
        if not has_test_info and "test_coverage" not in template.get("metadata", {}):
            warnings.append("No test coverage information")
            score -= 10

        # Check for prerequisites
        if "prerequisites" not in workflow:
            warnings.append("Missing prerequisites - unclear what's needed before using")
            score -= 10

        # Check for related templates
        if "related_templates" not in workflow:
            warnings.append("No related templates listed - missing integration context")
            score -= 5

        passed = score >= 70
        return ValidationResult(
            gate_name="SDLC Integration",
            passed=passed,
            score=max(0, score),
            warnings=warnings
        )


# =============================================================================
# 4. TEMPLATE FITNESS SCORER
# =============================================================================

class TemplateFitnessScorer:
    """
    Tracks template effectiveness in real workflows

    Fitness Score = (
        0.40 * Usage Rate +        # How often selected
        0.30 * Success Rate +       # How often it works
        0.20 * Quality Score +      # Code quality metrics
        0.10 * Freshness           # Recently updated
    )

    Thresholds:
    - Excellent: >= 80
    - Good: 60-79
    - Needs Improvement: 40-59
    - Retire: < 40
    """

    def __init__(self, metrics_file: Path = None):
        self.metrics_file = metrics_file or Path("/tmp/maestro_template_fitness_metrics.json")
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self._load_metrics()

    def _load_metrics(self):
        """Load existing metrics from file"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    self.metrics = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load fitness metrics: {e}")
                self.metrics = {}

    def _save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fitness metrics: {e}")

    def track_usage(self, template_id: str, scenario_id: str):
        """Track template usage"""
        if template_id not in self.metrics:
            self.metrics[template_id] = {
                "usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "scenarios": []
            }

        self.metrics[template_id]["usage_count"] += 1
        if scenario_id not in self.metrics[template_id]["scenarios"]:
            self.metrics[template_id]["scenarios"].append(scenario_id)

        self._save_metrics()

    def record_outcome(self, template_id: str, success: bool):
        """Record template usage outcome"""
        if template_id not in self.metrics:
            self.track_usage(template_id, "unknown")

        if success:
            self.metrics[template_id]["success_count"] += 1
        else:
            self.metrics[template_id]["failure_count"] += 1

        self._save_metrics()

    def calculate_fitness_score(self, template_id: str, quality_score: float = 80.0) -> float:
        """
        Calculate template fitness score (0-100)

        Args:
            template_id: Template ID
            quality_score: Template quality score (from metadata)

        Returns:
            Fitness score (0-100)
        """
        if template_id not in self.metrics:
            return quality_score * 0.20  # New templates start with 20% of quality score

        metrics = self.metrics[template_id]

        # Usage rate (normalized to 100 uses = 100%)
        usage_rate = min(metrics["usage_count"] / 100, 1.0) * 100

        # Success rate
        total_outcomes = metrics["success_count"] + metrics["failure_count"]
        success_rate = (metrics["success_count"] / total_outcomes * 100) if total_outcomes > 0 else 50.0

        # Freshness (assume new for now, would check last_updated in production)
        freshness = 80.0

        # Calculate weighted fitness score
        fitness = (
            0.40 * usage_rate +
            0.30 * success_rate +
            0.20 * quality_score +
            0.10 * freshness
        )

        return round(fitness, 1)

    def identify_underperforming(self, threshold: float = 40.0) -> List[str]:
        """Identify templates with fitness score below threshold"""
        underperforming = []

        for template_id in self.metrics:
            fitness = self.calculate_fitness_score(template_id)
            if fitness < threshold:
                underperforming.append(template_id)

        return underperforming

    def get_top_performing(self, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get top performing templates"""
        scores = [(tid, self.calculate_fitness_score(tid)) for tid in self.metrics]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def test_intelligence_layer():
    """Test the intelligence layer components"""
    print("="*80)
    print("TEMPLATE INTELLIGENCE LAYER - TESTING")
    print("="*80)

    # Test 1: Similarity Analyzer
    print("\n📊 Test 1: Template Similarity Analyzer")
    analyzer = TemplateSimilarityAnalyzer()
    await analyzer.initialize()

    results = await analyzer.find_similar_templates(
        requirement="Build a REST API with CRUD operations using FastAPI and PostgreSQL",
        persona="backend_developer",
        min_similarity=0.50
    )

    print(f"\nFound {len(results)} similar templates:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n{i}. {result.template_name}")
        print(f"   Similarity: {result.similarity_score:.1%}")
        print(f"   Recommendation: {result.recommendation.upper()}")
        print(f"   Keywords: {', '.join(result.matching_keywords[:5])}")

    # Test 2: Variant Decision Engine
    print("\n\n🤔 Test 2: Variant Decision Engine")
    decision_engine = VariantDecisionEngine(analyzer)

    decision = await decision_engine.analyze_requirement(
        requirement="Create a REST API with FastAPI and MySQL database",
        persona="backend_developer"
    )

    print(f"\nDecision: {decision.action}")
    print(f"Confidence: {decision.confidence:.0%}")
    print(f"Reasoning: {decision.reasoning}")
    if decision.base_template_name:
        print(f"Base Template: {decision.base_template_name}")
        print(f"Parameters to Change: {', '.join(decision.parameters_to_change)}")

    # Test 3: Quality Gate Validator
    print("\n\n✅ Test 3: Quality Gate Validator")
    validator = QualityGateValidator()

    # Load a sample template
    sample_template_path = Path("/home/ec2-user/projects/maestro-platform/maestro-templates/storage/templates/requirement_analyst/srs-document-template.json")
    if sample_template_path.exists():
        with open(sample_template_path) as f:
            sample_template = json.load(f)

        report = await validator.validate_template(sample_template)

        print(f"\nOverall Score: {report.overall_score}/100")
        print(f"Passed: {'✅ YES' if report.overall_passed else '❌ NO'}")
        print("\nGate Results:")
        for gate in report.gate_results:
            status = "✅ PASS" if gate.passed else "❌ FAIL"
            print(f"  {gate.gate_name}: {status} ({gate.score:.0f}/100)")
            if gate.critical_issues:
                print(f"    Critical Issues: {len(gate.critical_issues)}")

    # Test 4: Fitness Scorer
    print("\n\n📈 Test 4: Template Fitness Scorer")
    scorer = TemplateFitnessScorer()

    # Simulate some usage
    scorer.track_usage("template-123", "scenario-01")
    scorer.record_outcome("template-123", success=True)
    scorer.track_usage("template-123", "scenario-02")
    scorer.record_outcome("template-123", success=True)

    fitness = scorer.calculate_fitness_score("template-123", quality_score=85.0)
    print(f"\nTemplate Fitness Score: {fitness}/100")

    print("\n" + "="*80)
    print("✅ All tests complete!")
    print("="*80)


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_intelligence_layer())
