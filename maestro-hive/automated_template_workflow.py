#!/usr/bin/env python3
"""
Automated Template Workflow System - Self-Learning Template Enhancement

This system provides continuous monitoring and automated enhancement of the
template library based on real-world scenario coverage analysis.

Features:
- Continuous monitoring of template coverage
- Automatic gap identification
- Smart template generation based on gaps
- Web research integration for industry best practices
- Safe mode (recommendations only) and Auto mode (auto-create)
- Performance tracking and metrics
- Rollback capability

Architecture:
    AutomatedWorkflowOrchestrator
        ├─> RealWorldRAGTester (test_rag_real_world.py)
        ├─> GapAnalyzer
        ├─> TemplateEnhancementEngine
        ├─> TemplateGenerator
        └─> ImprovementTracker

Usage:
    # Safe mode (recommendations only)
    python automated_template_workflow.py --mode safe --interval 3600

    # Auto mode (auto-generate templates)
    python automated_template_workflow.py --mode auto --interval 7200

    # One-shot run
    python automated_template_workflow.py --once
"""

import asyncio
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import subprocess
import shutil

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

# Import intelligence layer
try:
    from template_intelligence import (
        TemplateSimilarityAnalyzer,
        VariantDecisionEngine,
        QualityGateValidator,
        TemplateFitnessScorer,
        VariantDecision
    )
    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Intelligence layer not available: {e}")
    INTELLIGENCE_AVAILABLE = False

# Configuration
LOG_DIR = Path("/tmp/maestro_workflow_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

METRICS_DIR = Path("/tmp/maestro_workflow_metrics")
METRICS_DIR.mkdir(parents=True, exist_ok=True)

RECOMMENDATIONS_DIR = Path("/tmp/maestro_workflow_recommendations")
RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"workflow_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class TemplateGap:
    """Represents a gap in template coverage"""
    gap_id: str
    gap_type: str  # "missing_persona", "low_coverage", "missing_category", "poor_quality"
    severity: str  # "critical", "high", "medium", "low"
    persona: Optional[str] = None
    category: Optional[str] = None
    scenario_ids: List[str] = field(default_factory=list)
    current_coverage: float = 0.0
    target_coverage: float = 70.0
    description: str = ""
    estimated_templates_needed: int = 0


@dataclass
class EnhancementRecommendation:
    """Recommendation for template enhancement"""
    recommendation_id: str
    gap: TemplateGap
    action_type: str  # "create_template", "enhance_template", "research_needed", "reuse", "variant"
    priority: int  # 1 (highest) to 5 (lowest)
    template_name: str = ""
    template_description: str = ""
    persona: str = ""
    category: str = ""
    language: str = ""
    framework: str = ""
    research_keywords: List[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Intelligence layer fields
    variant_decision: Optional[str] = None  # REUSE/VARIANT/CREATE_NEW
    base_template_id: Optional[str] = None
    base_template_name: Optional[str] = None
    similarity_score: float = 0.0
    quality_validated: bool = False


@dataclass
class GeneratedTemplate:
    """A template that was auto-generated"""
    template_id: str
    template_name: str
    file_path: str
    persona: str
    category: str
    gap_id: str
    quality_score: float
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    synced_to_db: bool = False
    validation_passed: bool = False


@dataclass
class WorkflowMetrics:
    """Metrics for a workflow run"""
    run_id: str
    run_timestamp: str
    mode: str  # "safe" or "auto"

    # Coverage metrics
    overall_coverage_before: float = 0.0
    overall_coverage_after: float = 0.0
    coverage_improvement: float = 0.0

    # Gap analysis
    total_gaps_identified: int = 0
    critical_gaps: int = 0
    high_priority_gaps: int = 0

    # Actions taken
    recommendations_generated: int = 0
    templates_auto_generated: int = 0
    templates_synced: int = 0

    # Intelligence metrics (new)
    templates_reused: int = 0
    templates_variants_created: int = 0
    templates_new_created: int = 0
    quality_gate_checks: int = 0
    quality_gate_failures: int = 0
    similarity_checks_performed: int = 0
    avg_template_similarity: float = 0.0

    # Performance
    execution_time_seconds: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)


# =============================================================================
# GAP ANALYZER
# =============================================================================

class GapAnalyzer:
    """Analyzes test results to identify template coverage gaps"""

    def __init__(self):
        self.gaps: List[TemplateGap] = []

    async def analyze_test_results(self, results_file: Path) -> List[TemplateGap]:
        """
        Analyze test results and identify gaps

        Returns:
            List of identified gaps sorted by severity
        """
        logger.info("🔍 Analyzing test results for gaps...")

        with open(results_file) as f:
            results = json.load(f)

        gaps = []
        gap_counter = 0

        # 1. Identify personas with zero templates
        for persona in results.get("personas_with_no_templates", []):
            gap_counter += 1
            gaps.append(TemplateGap(
                gap_id=f"GAP_{gap_counter:04d}",
                gap_type="missing_persona",
                severity="critical",
                persona=persona,
                current_coverage=0.0,
                target_coverage=70.0,
                description=f"Persona '{persona}' has ZERO templates",
                estimated_templates_needed=10
            ))

        # 2. Identify personas with low coverage
        persona_coverage = results.get("persona_coverage", {})
        for persona, stats in persona_coverage.items():
            scenarios_used = stats.get("scenarios_used", 0)
            total_templates = stats.get("total_templates", 0)

            if scenarios_used == 0:
                continue

            avg_per_scenario = total_templates / scenarios_used

            # Low coverage: < 3 templates per scenario
            if 0 < avg_per_scenario < 3 and scenarios_used >= 3:
                gap_counter += 1
                needed = max(int((3 * scenarios_used) - total_templates), 5)
                gaps.append(TemplateGap(
                    gap_id=f"GAP_{gap_counter:04d}",
                    gap_type="low_coverage",
                    severity="high" if avg_per_scenario < 2 else "medium",
                    persona=persona,
                    current_coverage=avg_per_scenario / 3 * 100,  # % of target
                    target_coverage=100.0,
                    description=f"Persona '{persona}' has low coverage: {avg_per_scenario:.1f} templates/scenario (target: 3+)",
                    estimated_templates_needed=needed
                ))

        # 3. Identify missing categories
        for category in results.get("missing_categories", []):
            gap_counter += 1
            gaps.append(TemplateGap(
                gap_id=f"GAP_{gap_counter:04d}",
                gap_type="missing_category",
                severity="medium",
                category=category,
                current_coverage=0.0,
                target_coverage=100.0,
                description=f"Category '{category}' has NO templates",
                estimated_templates_needed=5
            ))

        # 4. Identify poorly covered scenarios
        for scenario_result in results.get("scenario_results", []):
            coverage = scenario_result.get("coverage_score", 0)

            if coverage < 40:  # Poorly covered
                gap_counter += 1
                scenario_id = scenario_result.get("scenario_id")
                scenario_name = scenario_result.get("scenario_name")
                missing_personas = scenario_result.get("missing_personas", [])

                gaps.append(TemplateGap(
                    gap_id=f"GAP_{gap_counter:04d}",
                    gap_type="poor_scenario_coverage",
                    severity="high" if coverage < 20 else "medium",
                    scenario_ids=[scenario_id],
                    current_coverage=coverage,
                    target_coverage=70.0,
                    description=f"Scenario '{scenario_name}' has poor coverage: {coverage:.0f}% (missing: {', '.join(missing_personas)})",
                    estimated_templates_needed=len(missing_personas) * 3
                ))

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda g: (severity_order[g.severity], -g.estimated_templates_needed))

        logger.info(f"   ✅ Identified {len(gaps)} gaps:")
        logger.info(f"      Critical: {sum(1 for g in gaps if g.severity == 'critical')}")
        logger.info(f"      High: {sum(1 for g in gaps if g.severity == 'high')}")
        logger.info(f"      Medium: {sum(1 for g in gaps if g.severity == 'medium')}")

        self.gaps = gaps
        return gaps


# =============================================================================
# ENHANCEMENT ENGINE
# =============================================================================

class TemplateEnhancementEngine:
    """Makes decisions about template enhancements based on gaps with INTELLIGENCE"""

    def __init__(self, use_intelligence: bool = True):
        self.recommendations: List[EnhancementRecommendation] = []
        self.use_intelligence = use_intelligence and INTELLIGENCE_AVAILABLE

        # Initialize intelligence components
        if self.use_intelligence:
            self.similarity_analyzer = TemplateSimilarityAnalyzer()
            self.variant_engine = VariantDecisionEngine(self.similarity_analyzer)
            self.quality_validator = QualityGateValidator()
            self.fitness_scorer = TemplateFitnessScorer()
            logger.info("   🧠 Intelligence layer activated")
        else:
            logger.info("   ⚠️  Running without intelligence layer")

    async def initialize(self):
        """Initialize intelligence components"""
        if self.use_intelligence:
            await self.similarity_analyzer.initialize()
            logger.info("   ✅ Intelligence components initialized")

    async def generate_recommendations(
        self,
        gaps: List[TemplateGap],
        max_recommendations: int = 20
    ) -> List[EnhancementRecommendation]:
        """
        Generate INTELLIGENT enhancement recommendations from identified gaps

        Uses:
        - Template similarity analysis
        - Variant decision engine
        - Quality gates
        - Fitness scoring

        Returns:
            List of recommendations sorted by priority
        """
        logger.info("💡 Generating intelligent enhancement recommendations...")

        if self.use_intelligence and not self.similarity_analyzer.templates_cache:
            await self.initialize()

        recommendations = []
        rec_counter = 0

        # Intelligence metrics tracking
        similarity_checks = 0
        reuse_count = 0
        variant_count = 0
        new_count = 0
        total_similarity = 0.0

        for gap in gaps[:max_recommendations]:
            # Determine severity-based priority
            priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
            base_priority = priority_map.get(gap.severity, 3)

            # Generate recommendation based on gap type
            if gap.gap_type == "missing_persona":
                # Need to create multiple templates for this persona
                templates_to_create = self._plan_persona_templates(gap.persona, gap.estimated_templates_needed)

                for template_spec in templates_to_create:
                    rec_counter += 1

                    # INTELLIGENT DECISION: Check if similar template exists
                    if self.use_intelligence:
                        requirement = f"{template_spec['name']}: {template_spec['description']}"
                        decision = await self.variant_engine.analyze_requirement(
                            requirement=requirement,
                            persona=gap.persona
                        )
                        similarity_checks += 1

                        if decision.similarity_score > 0:
                            total_similarity += decision.similarity_score

                        # Determine action based on decision
                        if decision.action == "REUSE":
                            action_type = "reuse"
                            reuse_count += 1
                        elif decision.action == "VARIANT":
                            action_type = "variant"
                            variant_count += 1
                        else:  # CREATE_NEW
                            action_type = "create_template"
                            new_count += 1

                        recommendations.append(EnhancementRecommendation(
                            recommendation_id=f"REC_{rec_counter:04d}",
                            gap=gap,
                            action_type=action_type,
                            priority=base_priority,
                            template_name=template_spec["name"],
                            template_description=template_spec["description"],
                            persona=gap.persona,
                            category=template_spec["category"],
                            language=template_spec["language"],
                            framework=template_spec["framework"],
                            research_keywords=template_spec["research_keywords"],
                            confidence=decision.confidence,
                            # Intelligence fields
                            variant_decision=decision.action,
                            base_template_id=decision.base_template_id,
                            base_template_name=decision.base_template_name,
                            similarity_score=decision.similarity_score,
                            quality_validated=False  # Will be validated if generated
                        ))
                    else:
                        # Fallback: No intelligence - just create
                        new_count += 1
                        recommendations.append(EnhancementRecommendation(
                            recommendation_id=f"REC_{rec_counter:04d}",
                            gap=gap,
                            action_type="create_template",
                            priority=base_priority,
                            template_name=template_spec["name"],
                            template_description=template_spec["description"],
                            persona=gap.persona,
                            category=template_spec["category"],
                            language=template_spec["language"],
                            framework=template_spec["framework"],
                            research_keywords=template_spec["research_keywords"],
                            confidence=0.85
                        ))

            elif gap.gap_type == "low_coverage":
                # Expand existing templates for persona
                templates_to_create = self._plan_expansion_templates(gap.persona, gap.estimated_templates_needed)

                for template_spec in templates_to_create:
                    rec_counter += 1

                    # INTELLIGENT DECISION: Check if similar template exists
                    if self.use_intelligence:
                        requirement = f"{template_spec['name']}: {template_spec['description']}"
                        decision = await self.variant_engine.analyze_requirement(
                            requirement=requirement,
                            persona=gap.persona
                        )
                        similarity_checks += 1

                        if decision.similarity_score > 0:
                            total_similarity += decision.similarity_score

                        # Determine action
                        if decision.action == "REUSE":
                            action_type = "reuse"
                            reuse_count += 1
                        elif decision.action == "VARIANT":
                            action_type = "variant"
                            variant_count += 1
                        else:  # CREATE_NEW
                            action_type = "create_template"
                            new_count += 1

                        recommendations.append(EnhancementRecommendation(
                            recommendation_id=f"REC_{rec_counter:04d}",
                            gap=gap,
                            action_type=action_type,
                            priority=base_priority,
                            template_name=template_spec["name"],
                            template_description=template_spec["description"],
                            persona=gap.persona,
                            category=template_spec["category"],
                            language=template_spec["language"],
                            framework=template_spec["framework"],
                            research_keywords=template_spec["research_keywords"],
                            confidence=decision.confidence,
                            # Intelligence fields
                            variant_decision=decision.action,
                            base_template_id=decision.base_template_id,
                            base_template_name=decision.base_template_name,
                            similarity_score=decision.similarity_score,
                            quality_validated=False
                        ))
                    else:
                        # Fallback: No intelligence
                        new_count += 1
                        recommendations.append(EnhancementRecommendation(
                            recommendation_id=f"REC_{rec_counter:04d}",
                            gap=gap,
                            action_type="create_template",
                            priority=base_priority,
                            template_name=template_spec["name"],
                            template_description=template_spec["description"],
                            persona=gap.persona,
                            category=template_spec["category"],
                            language=template_spec["language"],
                            framework=template_spec["framework"],
                            research_keywords=template_spec["research_keywords"],
                            confidence=0.80
                        ))

            elif gap.gap_type == "missing_category":
                # Create templates for missing category
                rec_counter += 1
                recommendations.append(EnhancementRecommendation(
                    recommendation_id=f"REC_{rec_counter:04d}",
                    gap=gap,
                    action_type="research_needed",
                    priority=base_priority,
                    template_name=f"{gap.category.replace('_', ' ').title()} Template",
                    template_description=f"Template for {gap.category} category",
                    category=gap.category,
                    research_keywords=[gap.category, "best practices", "2025"],
                    confidence=0.70
                ))

        # Log intelligence metrics
        if self.use_intelligence and similarity_checks > 0:
            avg_similarity = total_similarity / similarity_checks
            logger.info(f"   🧠 Intelligence Analysis:")
            logger.info(f"      Similarity checks: {similarity_checks}")
            logger.info(f"      REUSE decisions: {reuse_count}")
            logger.info(f"      VARIANT decisions: {variant_count}")
            logger.info(f"      CREATE_NEW decisions: {new_count}")
            logger.info(f"      Avg similarity: {avg_similarity:.1%}")

            # Store metrics for reporting (attach to engine for access by orchestrator)
            self.last_intelligence_metrics = {
                "similarity_checks": similarity_checks,
                "reuse_count": reuse_count,
                "variant_count": variant_count,
                "new_count": new_count,
                "avg_similarity": avg_similarity
            }

        logger.info(f"   ✅ Generated {len(recommendations)} recommendations")

        self.recommendations = recommendations
        return recommendations

    def _plan_persona_templates(self, persona: str, count: int) -> List[Dict[str, Any]]:
        """Plan what templates to create for a persona"""
        # Template planning based on persona
        PERSONA_TEMPLATES = {
            "database_specialist": [
                {"name": "Normalized Schema Design (3NF)", "category": "backend", "language": "sql", "framework": "postgresql",
                 "description": "Database normalization to 3NF with practical examples",
                 "research_keywords": ["database normalization", "3NF", "schema design", "postgresql"]},
                {"name": "Zero-Downtime Database Migration", "category": "backend", "language": "sql", "framework": "postgresql",
                 "description": "Expand-contract pattern for safe production migrations",
                 "research_keywords": ["zero-downtime migration", "expand-contract", "database migration"]},
                {"name": "Database Indexing Strategy", "category": "backend", "language": "sql", "framework": "postgresql",
                 "description": "Strategic indexing for query optimization",
                 "research_keywords": ["database indexing", "b-tree", "query optimization", "postgresql"]},
                {"name": "Database Sharding Pattern", "category": "backend", "language": "python", "framework": "sqlalchemy",
                 "description": "Horizontal partitioning for scalability",
                 "research_keywords": ["database sharding", "horizontal partitioning", "scalability"]},
                {"name": "Time-Series Database Schema", "category": "backend", "language": "sql", "framework": "timescaledb",
                 "description": "Optimized schema design for time-series data",
                 "research_keywords": ["time-series database", "timescaledb", "iot data"]},
                {"name": "Multi-Tenant Database Design", "category": "backend", "language": "sql", "framework": "postgresql",
                 "description": "Row-level security and tenant isolation",
                 "research_keywords": ["multi-tenant database", "row-level security", "tenant isolation"]},
                {"name": "Query Performance Optimization", "category": "backend", "language": "sql", "framework": "postgresql",
                 "description": "Execution plan analysis and query tuning",
                 "research_keywords": ["query optimization", "execution plan", "explain analyze"]},
                {"name": "Database Backup and Recovery", "category": "backend", "language": "bash", "framework": "postgresql",
                 "description": "PITR, replication, disaster recovery",
                 "research_keywords": ["database backup", "point-in-time recovery", "disaster recovery"]},
                {"name": "Connection Pooling Configuration", "category": "backend", "language": "python", "framework": "pgbouncer",
                 "description": "Optimal connection pooling setup",
                 "research_keywords": ["connection pooling", "pgbouncer", "database performance"]},
                {"name": "Database Monitoring and Alerting", "category": "backend", "language": "python", "framework": "prometheus",
                 "description": "Monitoring queries, locks, and performance",
                 "research_keywords": ["database monitoring", "prometheus", "performance metrics"]},
            ],
            "qa_engineer": [
                {"name": "Test Pyramid Strategy", "category": "testing", "language": "python", "framework": "pytest",
                 "description": "Balanced test suite with unit, integration, E2E",
                 "research_keywords": ["test pyramid", "testing strategy", "pytest"]},
                {"name": "API Test Automation", "category": "testing", "language": "python", "framework": "pytest",
                 "description": "Comprehensive API testing with pytest",
                 "research_keywords": ["api testing", "rest api testing", "pytest"]},
                {"name": "E2E Test Automation (Selenium)", "category": "testing", "language": "python", "framework": "selenium",
                 "description": "End-to-end UI testing with Selenium",
                 "research_keywords": ["selenium", "e2e testing", "ui automation"]},
                {"name": "Performance Test (Locust)", "category": "testing", "language": "python", "framework": "locust",
                 "description": "Load testing and performance benchmarking",
                 "research_keywords": ["load testing", "locust", "performance testing"]},
                {"name": "Contract Testing (Pact)", "category": "testing", "language": "python", "framework": "pact",
                 "description": "Consumer-driven contract testing",
                 "research_keywords": ["contract testing", "pact", "microservices testing"]},
                {"name": "Test Data Factory Pattern", "category": "testing", "language": "python", "framework": "factory-boy",
                 "description": "Generate test data efficiently",
                 "research_keywords": ["test data factory", "factory-boy", "test fixtures"]},
                {"name": "Mutation Testing", "category": "testing", "language": "python", "framework": "mutmut",
                 "description": "Verify test suite effectiveness",
                 "research_keywords": ["mutation testing", "mutmut", "test quality"]},
                {"name": "Security Testing (OWASP)", "category": "testing", "language": "python", "framework": "zap",
                 "description": "OWASP Top 10 security testing",
                 "research_keywords": ["security testing", "owasp", "penetration testing"]},
                {"name": "Visual Regression Testing", "category": "testing", "language": "javascript", "framework": "percy",
                 "description": "Automated visual testing",
                 "research_keywords": ["visual regression", "screenshot testing", "percy"]},
                {"name": "Test Coverage Analysis", "category": "testing", "language": "python", "framework": "coverage.py",
                 "description": "Measure and improve test coverage",
                 "research_keywords": ["test coverage", "coverage analysis", "code coverage"]},
            ],
            "frontend_developer": [
                {"name": "React Compound Component Pattern", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "Flexible, composable React components",
                 "research_keywords": ["react patterns", "compound component", "typescript"]},
                {"name": "State Management with Zustand", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "Lightweight state management",
                 "research_keywords": ["zustand", "state management", "react"]},
                {"name": "Form Handling with React Hook Form", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "Performant form validation",
                 "research_keywords": ["react hook form", "form validation", "react"]},
                {"name": "Infinite Scroll Component", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "Virtualized infinite scrolling",
                 "research_keywords": ["infinite scroll", "virtualization", "react"]},
                {"name": "Accessibility (WCAG 2.1)", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "WCAG compliant components",
                 "research_keywords": ["accessibility", "wcag", "aria", "react"]},
                {"name": "Animation with Framer Motion", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "Smooth animations and transitions",
                 "research_keywords": ["framer motion", "react animations", "transitions"]},
                {"name": "Data Fetching with React Query", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "Server state management",
                 "research_keywords": ["react query", "data fetching", "cache management"]},
                {"name": "Responsive Design System", "category": "frontend", "language": "typescript", "framework": "react",
                 "description": "Mobile-first responsive components",
                 "research_keywords": ["responsive design", "mobile-first", "design system"]},
            ],
            "iot_specialist": [
                {"name": "MQTT Device Communication", "category": "iot", "language": "python", "framework": "paho-mqtt",
                 "description": "IoT device messaging with MQTT",
                 "research_keywords": ["mqtt", "iot messaging", "device communication"]},
                {"name": "Device Provisioning Flow", "category": "iot", "language": "python", "framework": "fastapi",
                 "description": "Secure device onboarding",
                 "research_keywords": ["device provisioning", "iot security", "onboarding"]},
                {"name": "Time-Series Data Ingestion", "category": "iot", "language": "python", "framework": "kafka",
                 "description": "High-throughput sensor data pipeline",
                 "research_keywords": ["time-series ingestion", "kafka", "iot data"]},
                {"name": "Device Shadow Pattern", "category": "iot", "language": "python", "framework": "aws-iot",
                 "description": "Device state synchronization",
                 "research_keywords": ["device shadow", "aws iot", "state sync"]},
                {"name": "OTA Firmware Update", "category": "iot", "language": "python", "framework": "fastapi",
                 "description": "Over-the-air firmware deployment",
                 "research_keywords": ["ota update", "firmware update", "iot"]},
            ],
            "sre": [
                {"name": "Prometheus Metrics Collection", "category": "monitoring", "language": "python", "framework": "prometheus",
                 "description": "Application and infrastructure metrics",
                 "research_keywords": ["prometheus", "metrics", "observability"]},
                {"name": "Distributed Tracing (OpenTelemetry)", "category": "monitoring", "language": "python", "framework": "opentelemetry",
                 "description": "End-to-end request tracing",
                 "research_keywords": ["opentelemetry", "distributed tracing", "observability"]},
                {"name": "Log Aggregation (ELK)", "category": "monitoring", "language": "python", "framework": "elasticsearch",
                 "description": "Centralized logging with ELK stack",
                 "research_keywords": ["elk stack", "log aggregation", "elasticsearch"]},
                {"name": "Incident Response Runbook", "category": "documentation", "language": "markdown", "framework": "generic",
                 "description": "Standardized incident response procedures",
                 "research_keywords": ["incident response", "runbook", "sre"]},
                {"name": "SLO/SLI Definition Template", "category": "documentation", "language": "yaml", "framework": "generic",
                 "description": "Service level objectives and indicators",
                 "research_keywords": ["slo", "sli", "service level", "sre"]},
            ]
        }

        templates = PERSONA_TEMPLATES.get(persona, [])
        return templates[:count]

    def _plan_expansion_templates(self, persona: str, count: int) -> List[Dict[str, Any]]:
        """Plan expansion templates for persona with existing coverage"""
        # Similar to above but focuses on advanced/specialized templates
        templates = self._plan_persona_templates(persona, count + 5)
        # Return templates not yet created (assuming first ones are created)
        return templates[5:5+count] if len(templates) > 5 else templates[:count]


# =============================================================================
# AUTOMATED WORKFLOW ORCHESTRATOR
# =============================================================================

class AutomatedWorkflowOrchestrator:
    """
    Main orchestrator for automated template enhancement workflow

    Runs continuously and:
    1. Executes real-world test suite
    2. Analyzes gaps
    3. Generates recommendations
    4. (Optionally) Auto-generates templates
    5. Syncs to database
    6. Tracks metrics
    """

    def __init__(
        self,
        mode: str = "safe",  # "safe" or "auto"
        interval_seconds: int = 3600,
        once: bool = False
    ):
        self.mode = mode
        self.interval = interval_seconds
        self.once = once

        self.gap_analyzer = GapAnalyzer()
        self.enhancement_engine = TemplateEnhancementEngine()

        self.run_counter = 0
        self.metrics_history: List[WorkflowMetrics] = []

        logger.info(f"🤖 Automated Workflow Orchestrator initialized")
        logger.info(f"   Mode: {self.mode}")
        logger.info(f"   Interval: {self.interval}s")
        logger.info(f"   Run once: {self.once}")

    async def start(self):
        """Start the automated workflow"""
        logger.info("="*80)
        logger.info("🚀 STARTING AUTOMATED TEMPLATE WORKFLOW")
        logger.info("="*80)

        if self.once:
            await self.run_workflow_cycle()
        else:
            # Continuous mode
            while True:
                await self.run_workflow_cycle()

                logger.info(f"\n⏰ Next run in {self.interval} seconds...")
                await asyncio.sleep(self.interval)

    async def run_workflow_cycle(self):
        """Run a single workflow cycle"""
        self.run_counter += 1
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.run_counter:04d}"

        start_time = datetime.now()

        logger.info(f"\n{'='*80}")
        logger.info(f"📊 WORKFLOW CYCLE #{self.run_counter} - {run_id}")
        logger.info(f"{'='*80}")

        metrics = WorkflowMetrics(
            run_id=run_id,
            run_timestamp=start_time.isoformat(),
            mode=self.mode
        )

        try:
            # Step 1: Run real-world test suite
            logger.info("\n📋 Step 1: Running real-world test suite...")
            coverage_before = await self.run_test_suite()
            metrics.overall_coverage_before = coverage_before

            # Step 2: Analyze gaps
            logger.info("\n🔍 Step 2: Analyzing coverage gaps...")
            results_file = Path("real_world_test_results.json")
            gaps = await self.gap_analyzer.analyze_test_results(results_file)
            metrics.total_gaps_identified = len(gaps)
            metrics.critical_gaps = sum(1 for g in gaps if g.severity == "critical")
            metrics.high_priority_gaps = sum(1 for g in gaps if g.severity == "high")

            # Step 3: Generate recommendations
            logger.info("\n💡 Step 3: Generating enhancement recommendations...")
            recommendations = await self.enhancement_engine.generate_recommendations(gaps)
            metrics.recommendations_generated = len(recommendations)

            # Collect intelligence metrics from enhancement engine
            if hasattr(self.enhancement_engine, 'last_intelligence_metrics'):
                intel_metrics = self.enhancement_engine.last_intelligence_metrics
                metrics.similarity_checks_performed = intel_metrics.get("similarity_checks", 0)
                metrics.templates_reused = intel_metrics.get("reuse_count", 0)
                metrics.templates_variants_created = intel_metrics.get("variant_count", 0)
                metrics.templates_new_created = intel_metrics.get("new_count", 0)
                metrics.avg_template_similarity = intel_metrics.get("avg_similarity", 0.0)

            # Save recommendations
            self.save_recommendations(run_id, recommendations)

            # Step 4: Take action based on mode
            if self.mode == "auto" and recommendations:
                logger.info("\n🤖 Step 4: Auto-generating templates...")
                # In real implementation, this would call template generation
                # For now, just log what would be created
                logger.info(f"   AUTO MODE: Would generate {len(recommendations[:10])} templates")
                for rec in recommendations[:10]:
                    logger.info(f"      - {rec.template_name} ({rec.persona})")

                # TODO: Implement actual template generation
                # generated = await self.generate_templates(recommendations[:10])
                # metrics.templates_auto_generated = len(generated)

            else:
                logger.info("\n📝 Step 4: Safe mode - recommendations saved for review")
                logger.info(f"   See: {RECOMMENDATIONS_DIR / f'{run_id}_recommendations.json'}")

            # Step 5: Track metrics
            end_time = datetime.now()
            metrics.execution_time_seconds = (end_time - start_time).total_seconds()
            metrics.success = True

            self.metrics_history.append(metrics)
            self.save_metrics(metrics)

            # Summary
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ WORKFLOW CYCLE COMPLETE")
            logger.info(f"{'='*80}")
            logger.info(f"Coverage: {metrics.overall_coverage_before:.1f}%")
            logger.info(f"Gaps identified: {metrics.total_gaps_identified} (Critical: {metrics.critical_gaps}, High: {metrics.high_priority_gaps})")
            logger.info(f"Recommendations: {metrics.recommendations_generated}")

            # Show intelligence metrics if available
            if metrics.similarity_checks_performed > 0:
                logger.info(f"Intelligence decisions: REUSE={metrics.templates_reused}, VARIANT={metrics.templates_variants_created}, NEW={metrics.templates_new_created}")
                logger.info(f"Avg similarity: {metrics.avg_template_similarity:.1%}")

            logger.info(f"Execution time: {metrics.execution_time_seconds:.1f}s")
            logger.info(f"{'='*80}")

        except Exception as e:
            logger.error(f"❌ Workflow cycle failed: {e}", exc_info=True)
            metrics.success = False
            metrics.errors.append(str(e))
            self.save_metrics(metrics)

    async def run_test_suite(self) -> float:
        """Run the real-world test suite"""
        try:
            # Clear RAG cache for fresh results
            cache_dir = Path("/tmp/maestro_rag_cache")
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logger.info("   🗑️  Cleared RAG cache")

            # Run test suite
            result = subprocess.run(
                ["python3", "test_rag_real_world.py"],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Parse coverage from results
            results_file = Path("real_world_test_results.json")
            if results_file.exists():
                with open(results_file) as f:
                    data = json.load(f)
                    coverage = data.get("overall_coverage_score", 0.0)
                    logger.info(f"   ✅ Test suite complete. Coverage: {coverage:.1f}%")
                    return coverage
            else:
                logger.warning("   ⚠️  Results file not found")
                return 0.0

        except Exception as e:
            logger.error(f"   ❌ Test suite failed: {e}")
            return 0.0

    def save_recommendations(self, run_id: str, recommendations: List[EnhancementRecommendation]):
        """Save recommendations to file"""
        output_file = RECOMMENDATIONS_DIR / f"{run_id}_recommendations.json"

        data = {
            "run_id": run_id,
            "generated_at": datetime.now().isoformat(),
            "mode": self.mode,
            "total_recommendations": len(recommendations),
            "recommendations": [asdict(r) for r in recommendations]
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"   💾 Recommendations saved: {output_file}")

    def save_metrics(self, metrics: WorkflowMetrics):
        """Save metrics to file"""
        output_file = METRICS_DIR / f"{metrics.run_id}_metrics.json"

        with open(output_file, "w") as f:
            json.dump(asdict(metrics), f, indent=2, default=str)

        logger.info(f"   📈 Metrics saved: {output_file}")


# =============================================================================
# CLI
# =============================================================================

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Automated Template Workflow System")
    parser.add_argument(
        "--mode",
        choices=["safe", "auto"],
        default="safe",
        help="Operating mode: 'safe' (recommendations only) or 'auto' (auto-generate templates)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval between runs in seconds (default: 3600 = 1 hour)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (instead of continuous mode)"
    )

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = AutomatedWorkflowOrchestrator(
        mode=args.mode,
        interval_seconds=args.interval,
        once=args.once
    )

    # Start workflow
    await orchestrator.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Workflow stopped by user")
        sys.exit(0)
