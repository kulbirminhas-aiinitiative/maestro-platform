#!/usr/bin/env python3
"""
Real-World RAG Integration Test Suite

Tests the RAG system with 12 diverse real-world scenarios to:
1. Evaluate template usefulness and relevance
2. Identify coverage gaps (personas, categories, tech stacks)
3. Measure template match rates and quality
4. Generate strengthening roadmap

Scenarios cover:
- E-commerce, SaaS, IoT, Real-time, Serverless
- Various team compositions and tech stacks
- Different architectural patterns

Run:
    python test_rag_real_world.py

Output:
    - real_world_test_results.json (machine-readable)
    - Console report with coverage analysis
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

# Test configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# SCENARIO DEFINITIONS
# =============================================================================

@dataclass
class RealWorldScenario:
    """Real-world project scenario for testing"""
    id: str
    name: str
    requirement: str
    description: str
    team_personas: List[str]
    tech_stack: Dict[str, str]
    expected_categories: List[str]
    expected_challenges: List[str]
    project_type: str  # e-commerce, saas, iot, etc.
    complexity: int  # 1-5
    estimated_duration_hours: int


# Scenario 1: E-Commerce Platform
ECOMMERCE_SCENARIO = RealWorldScenario(
    id="SC01",
    name="E-Commerce Platform",
    requirement=(
        "Build a full-stack e-commerce platform with user authentication, "
        "product catalog with categories and search, shopping cart management, "
        "payment integration (Stripe), order management, admin dashboard for "
        "inventory and orders, email notifications, and responsive frontend."
    ),
    description="Standard e-commerce with all typical features",
    team_personas=[
        "requirement_analyst",
        "solution_architect",
        "frontend_developer",
        "backend_developer",
        "database_specialist",
        "security_specialist",
        "qa_engineer",
        "devops_engineer"
    ],
    tech_stack={
        "frontend": "React, TypeScript, TailwindCSS",
        "backend": "FastAPI, Python",
        "database": "PostgreSQL, Redis",
        "auth": "JWT with refresh tokens",
        "payments": "Stripe",
        "deployment": "Docker, Kubernetes"
    },
    expected_categories=[
        "api", "authentication", "database", "security",
        "frontend", "testing", "infrastructure", "integration"
    ],
    expected_challenges=[
        "Payment integration",
        "Inventory management",
        "Order state machine",
        "Product search optimization"
    ],
    project_type="e-commerce",
    complexity=4,
    estimated_duration_hours=120
)

# Scenario 2: Multi-Tenant SaaS
SAAS_SCENARIO = RealWorldScenario(
    id="SC02",
    name="Multi-Tenant SaaS Application",
    requirement=(
        "Build a multi-tenant SaaS platform with tenant isolation, subscription "
        "billing (Stripe), user management with RBAC, feature flags per plan, "
        "usage analytics and metering, API with rate limiting per tenant, "
        "admin portal for tenant management, and webhook system for integrations."
    ),
    description="B2B SaaS with multiple tenants and subscription management",
    team_personas=[
        "requirement_analyst",
        "solution_architect",
        "backend_developer",
        "frontend_developer",
        "database_specialist",
        "security_specialist",
        "devops_engineer"
    ],
    tech_stack={
        "frontend": "React, Next.js",
        "backend": "NestJS, TypeScript",
        "database": "PostgreSQL with row-level security",
        "cache": "Redis",
        "queue": "BullMQ",
        "deployment": "AWS ECS"
    },
    expected_categories=[
        "architecture", "api", "authentication", "authorization",
        "database", "security", "infrastructure", "integration"
    ],
    expected_challenges=[
        "Multi-tenancy data isolation",
        "Subscription billing and metering",
        "Feature flag system",
        "Per-tenant rate limiting"
    ],
    project_type="saas",
    complexity=5,
    estimated_duration_hours=200
)

# Scenario 3: Real-Time Chat System
CHAT_SCENARIO = RealWorldScenario(
    id="SC03",
    name="Real-Time Chat/Messaging System",
    requirement=(
        "Build a WebSocket-based real-time chat system with channels/rooms, "
        "direct messaging, typing indicators, read receipts, presence detection, "
        "file sharing with preview, message search, emoji reactions, and "
        "message history with pagination."
    ),
    description="Slack/Discord-like real-time messaging platform",
    team_personas=[
        "solution_architect",
        "backend_developer",
        "frontend_developer",
        "database_specialist",
        "security_specialist",
        "qa_engineer",
        "devops_engineer"
    ],
    tech_stack={
        "frontend": "React, WebSocket",
        "backend": "FastAPI, Python, WebSockets",
        "database": "PostgreSQL, Redis",
        "message_queue": "Redis Streams",
        "file_storage": "S3",
        "deployment": "Kubernetes with sticky sessions"
    },
    expected_categories=[
        "real_time", "api", "authentication", "database",
        "infrastructure", "integration", "security"
    ],
    expected_challenges=[
        "WebSocket connection management",
        "Presence detection",
        "Message delivery guarantees",
        "Scaling WebSocket connections"
    ],
    project_type="real-time",
    complexity=4,
    estimated_duration_hours=100
)

# Scenario 4: IoT Data Pipeline
IOT_SCENARIO = RealWorldScenario(
    id="SC04",
    name="IoT Data Pipeline",
    requirement=(
        "Build an IoT platform for device management with data ingestion from "
        "thousands of devices, time-series data storage, real-time alerting "
        "based on thresholds, device provisioning and authentication, "
        "data aggregation and analytics, and dashboards for monitoring."
    ),
    description="IoT device management and data processing platform",
    team_personas=[
        "solution_architect",
        "backend_developer",
        "database_specialist",
        "devops_engineer",
        "qa_engineer"
    ],
    tech_stack={
        "ingestion": "MQTT, Kafka",
        "backend": "FastAPI, Python",
        "database": "TimescaleDB, InfluxDB",
        "processing": "Apache Flink",
        "cache": "Redis",
        "deployment": "Kubernetes"
    },
    expected_categories=[
        "iot", "api", "database", "infrastructure",
        "background-processing", "real_time"
    ],
    expected_challenges=[
        "High-throughput data ingestion",
        "Time-series data optimization",
        "Device authentication at scale",
        "Real-time alerting"
    ],
    project_type="iot",
    complexity=5,
    estimated_duration_hours=150
)

# Scenario 5: API Gateway / BFF
API_GATEWAY_SCENARIO = RealWorldScenario(
    id="SC05",
    name="API Gateway with BFF Pattern",
    requirement=(
        "Build an API gateway with rate limiting per client, JWT authentication "
        "and validation, request/response transformation, service routing and "
        "load balancing, circuit breaker for downstream services, caching layer, "
        "request logging and monitoring, and API versioning support."
    ),
    description="Enterprise API gateway with multiple downstream services",
    team_personas=[
        "solution_architect",
        "backend_developer",
        "security_specialist",
        "devops_engineer"
    ],
    tech_stack={
        "gateway": "FastAPI, Python",
        "cache": "Redis",
        "database": "PostgreSQL",
        "monitoring": "Prometheus, Grafana",
        "deployment": "Kubernetes with Ingress"
    },
    expected_categories=[
        "api", "security", "authentication", "infrastructure",
        "logging", "error-handling"
    ],
    expected_challenges=[
        "Circuit breaker implementation",
        "Advanced rate limiting strategies",
        "Service discovery",
        "API versioning"
    ],
    project_type="api-gateway",
    complexity=4,
    estimated_duration_hours=80
)

# Scenario 6: ML Pipeline
ML_SCENARIO = RealWorldScenario(
    id="SC06",
    name="Machine Learning Pipeline",
    requirement=(
        "Build an ML pipeline for model training, versioning, and serving with "
        "feature store, model registry, automated retraining, A/B testing for "
        "models, model monitoring and drift detection, batch and real-time "
        "inference, and experiment tracking."
    ),
    description="End-to-end MLOps platform",
    team_personas=[
        "solution_architect",
        "backend_developer",
        "devops_engineer",
        "qa_engineer"
    ],
    tech_stack={
        "training": "PyTorch, TensorFlow",
        "serving": "FastAPI, TorchServe",
        "registry": "MLflow",
        "feature_store": "Feast",
        "monitoring": "Prometheus, Evidently",
        "deployment": "Kubernetes"
    },
    expected_categories=[
        "api", "background-processing", "infrastructure",
        "testing", "database"
    ],
    expected_challenges=[
        "Model versioning",
        "Feature engineering pipeline",
        "Model drift detection",
        "A/B testing infrastructure"
    ],
    project_type="ml-ops",
    complexity=5,
    estimated_duration_hours=180
)

# Scenario 7: Mobile Backend (BaaS)
MOBILE_BACKEND_SCENARIO = RealWorldScenario(
    id="SC07",
    name="Mobile Backend as a Service",
    requirement=(
        "Build a mobile backend with push notification service, offline sync "
        "support, file upload/download with resume, OAuth authentication with "
        "social login, background job processing, crash reporting integration, "
        "and analytics tracking."
    ),
    description="Backend for iOS/Android mobile apps",
    team_personas=[
        "backend_developer",
        "security_specialist",
        "devops_engineer",
        "qa_engineer"
    ],
    tech_stack={
        "backend": "FastAPI, Python",
        "push": "FCM, APNs",
        "database": "PostgreSQL",
        "file_storage": "S3",
        "queue": "Celery, Redis",
        "deployment": "AWS ECS"
    },
    expected_categories=[
        "api", "authentication", "background-processing",
        "integration", "security", "infrastructure"
    ],
    expected_challenges=[
        "Push notification delivery",
        "Offline sync conflict resolution",
        "File upload resume",
        "OAuth PKCE flow"
    ],
    project_type="mobile-backend",
    complexity=4,
    estimated_duration_hours=90
)

# Scenario 8: Event-Driven Microservices
EVENT_DRIVEN_SCENARIO = RealWorldScenario(
    id="SC08",
    name="Event-Driven Microservices",
    requirement=(
        "Build event-sourced microservices with CQRS pattern, saga orchestration "
        "for distributed transactions, event bus (Kafka), event replay capability, "
        "eventual consistency handling, and event schema versioning."
    ),
    description="Event-driven architecture with multiple microservices",
    team_personas=[
        "solution_architect",
        "backend_developer",
        "database_specialist",
        "devops_engineer",
        "qa_engineer"
    ],
    tech_stack={
        "services": "FastAPI, NestJS",
        "event_bus": "Apache Kafka",
        "event_store": "PostgreSQL",
        "read_models": "MongoDB",
        "deployment": "Kubernetes"
    },
    expected_categories=[
        "architecture", "api", "database", "integration",
        "infrastructure", "background-processing"
    ],
    expected_challenges=[
        "Event sourcing implementation",
        "CQRS pattern",
        "Saga coordination",
        "Event replay and versioning"
    ],
    project_type="microservices",
    complexity=5,
    estimated_duration_hours=200
)

# Scenario 9: Compliance System
COMPLIANCE_SCENARIO = RealWorldScenario(
    id="SC09",
    name="GDPR/HIPAA Compliance System",
    requirement=(
        "Build a compliant system with comprehensive audit logging, data "
        "retention and deletion policies, consent management, data encryption "
        "at rest and in transit, role-based access control with audit, "
        "data anonymization, and compliance reporting."
    ),
    description="Healthcare/finance application with strict compliance",
    team_personas=[
        "solution_architect",
        "security_specialist",
        "backend_developer",
        "database_specialist",
        "qa_engineer"
    ],
    tech_stack={
        "backend": "FastAPI, Python",
        "database": "PostgreSQL with encryption",
        "audit": "Elasticsearch",
        "encryption": "AWS KMS",
        "deployment": "AWS with compliance certifications"
    },
    expected_categories=[
        "security", "authentication", "authorization",
        "database", "logging", "api"
    ],
    expected_challenges=[
        "GDPR right to be forgotten",
        "Comprehensive audit logging",
        "Data encryption patterns",
        "Consent management"
    ],
    project_type="compliance",
    complexity=5,
    estimated_duration_hours=160
)

# Scenario 10: Serverless API
SERVERLESS_SCENARIO = RealWorldScenario(
    id="SC10",
    name="Serverless API Application",
    requirement=(
        "Build a serverless REST API on AWS Lambda with API Gateway, DynamoDB "
        "for data storage, S3 for file storage, SQS for async processing, "
        "Step Functions for workflows, CloudWatch for logging, and X-Ray for "
        "tracing."
    ),
    description="Fully serverless application on AWS",
    team_personas=[
        "backend_developer",
        "devops_engineer",
        "qa_engineer"
    ],
    tech_stack={
        "functions": "AWS Lambda, Python",
        "api": "API Gateway",
        "database": "DynamoDB",
        "storage": "S3",
        "queue": "SQS",
        "orchestration": "Step Functions"
    },
    expected_categories=[
        "api", "infrastructure", "database",
        "background-processing", "integration"
    ],
    expected_challenges=[
        "Cold start optimization",
        "Lambda function patterns",
        "DynamoDB data modeling",
        "Step Functions coordination"
    ],
    project_type="serverless",
    complexity=4,
    estimated_duration_hours=70
)

# Scenario 11: GraphQL Platform
GRAPHQL_SCENARIO = RealWorldScenario(
    id="SC11",
    name="GraphQL API Platform",
    requirement=(
        "Build a GraphQL API with schema federation across microservices, "
        "real-time subscriptions via WebSocket, query batching and caching, "
        "N+1 query optimization with DataLoader, authentication/authorization "
        "at resolver level, and schema versioning."
    ),
    description="Modern GraphQL platform with federation",
    team_personas=[
        "solution_architect",
        "backend_developer",
        "frontend_developer",
        "devops_engineer"
    ],
    tech_stack={
        "gateway": "Apollo Federation",
        "services": "NestJS with GraphQL",
        "database": "PostgreSQL",
        "cache": "Redis",
        "deployment": "Kubernetes"
    },
    expected_categories=[
        "api", "architecture", "database",
        "authentication", "infrastructure", "real_time"
    ],
    expected_challenges=[
        "Schema federation",
        "N+1 query problem",
        "GraphQL subscriptions",
        "Authorization at field level"
    ],
    project_type="graphql",
    complexity=4,
    estimated_duration_hours=100
)

# Scenario 12: Headless CMS
CMS_SCENARIO = RealWorldScenario(
    id="SC12",
    name="Headless CMS",
    requirement=(
        "Build a headless CMS with content versioning and rollback, "
        "draft/review/publish workflow, rich media management with transformations, "
        "multi-language content support, webhooks for content changes, "
        "content scheduling, and API for content delivery."
    ),
    description="Content management system with API-first approach",
    team_personas=[
        "backend_developer",
        "frontend_developer",
        "database_specialist",
        "security_specialist",
        "devops_engineer"
    ],
    tech_stack={
        "backend": "FastAPI, Python",
        "database": "PostgreSQL",
        "storage": "S3 with CloudFront",
        "cache": "Redis",
        "search": "Elasticsearch",
        "deployment": "Kubernetes"
    },
    expected_categories=[
        "api", "database", "integration",
        "authentication", "authorization", "infrastructure"
    ],
    expected_challenges=[
        "Content versioning",
        "Workflow state machine",
        "Media transformation pipeline",
        "Multi-language support"
    ],
    project_type="cms",
    complexity=4,
    estimated_duration_hours=120
)


# All scenarios
ALL_SCENARIOS = [
    ECOMMERCE_SCENARIO,
    SAAS_SCENARIO,
    CHAT_SCENARIO,
    IOT_SCENARIO,
    API_GATEWAY_SCENARIO,
    ML_SCENARIO,
    MOBILE_BACKEND_SCENARIO,
    EVENT_DRIVEN_SCENARIO,
    COMPLIANCE_SCENARIO,
    SERVERLESS_SCENARIO,
    GRAPHQL_SCENARIO,
    CMS_SCENARIO
]


# =============================================================================
# TEST RESULTS DATA STRUCTURES
# =============================================================================

@dataclass
class PersonaTemplateResult:
    """Results for a specific persona in a scenario"""
    persona_id: str
    templates_found: int = 0
    templates_high_relevance: int = 0  # >80%
    templates_medium_relevance: int = 0  # 60-80%
    templates_low_relevance: int = 0  # <60%
    top_templates: List[Dict[str, Any]] = field(default_factory=list)
    average_relevance: float = 0.0
    categories_covered: List[str] = field(default_factory=list)


@dataclass
class ScenarioTestResult:
    """Test results for a single scenario"""
    scenario_id: str
    scenario_name: str
    requirement: str
    project_type: str

    # Package-level results
    package_recommended: bool = False
    package_name: Optional[str] = None
    package_confidence: float = 0.0

    # Persona-level results
    persona_results: Dict[str, PersonaTemplateResult] = field(default_factory=dict)

    # Coverage metrics
    personas_with_templates: int = 0
    personas_with_high_relevance: int = 0
    total_templates_found: int = 0
    total_high_relevance: int = 0
    average_relevance: float = 0.0

    # Gap analysis
    missing_personas: List[str] = field(default_factory=list)
    missing_categories: List[str] = field(default_factory=list)
    coverage_score: float = 0.0  # 0-100


@dataclass
class TestSuiteResults:
    """Overall test suite results"""
    test_date: str
    total_scenarios: int

    # Scenario results
    scenario_results: List[ScenarioTestResult] = field(default_factory=list)

    # Aggregate metrics
    overall_coverage_score: float = 0.0
    scenarios_well_covered: int = 0  # Coverage >70%
    scenarios_poorly_covered: int = 0  # Coverage <40%

    # Persona analysis
    persona_coverage: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    personas_with_no_templates: List[str] = field(default_factory=list)

    # Category analysis
    category_usage: Dict[str, int] = field(default_factory=dict)
    missing_categories: List[str] = field(default_factory=list)

    # Gap analysis
    critical_gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# TEST RUNNER
# =============================================================================

class RealWorldRAGTester:
    """Test RAG system with real-world scenarios"""

    def __init__(self):
        self.rag_client = None
        self.results = TestSuiteResults(
            test_date=datetime.now().isoformat(),
            total_scenarios=len(ALL_SCENARIOS)
        )

    async def initialize(self):
        """Initialize RAG client"""
        try:
            from rag_template_client import TemplateRAGClient
            self.rag_client = TemplateRAGClient()
            logger.info("✅ RAG client initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG client: {e}")
            return False

    async def run_all_tests(self):
        """Run all scenario tests"""
        logger.info("="*80)
        logger.info("REAL-WORLD RAG TESTING SUITE")
        logger.info("="*80)
        logger.info(f"Testing {len(ALL_SCENARIOS)} diverse real-world scenarios")
        logger.info("")

        if not await self.initialize():
            logger.error("Cannot run tests without RAG client")
            return

        # Run each scenario
        for scenario in ALL_SCENARIOS:
            result = await self.test_scenario(scenario)
            self.results.scenario_results.append(result)

        # Analyze results
        await self.analyze_results()

        # Print report
        self.print_report()

        # Save results
        await self.save_results()

        # Close client
        await self.rag_client.close()

    async def test_scenario(self, scenario: RealWorldScenario) -> ScenarioTestResult:
        """Test a single scenario"""
        logger.info(f"\n{'='*80}")
        logger.info(f"TESTING SCENARIO: {scenario.name} ({scenario.id})")
        logger.info(f"{'='*80}")
        logger.info(f"Project type: {scenario.project_type}")
        logger.info(f"Complexity: {scenario.complexity}/5")
        logger.info(f"Team size: {len(scenario.team_personas)} personas")
        logger.info("")

        result = ScenarioTestResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            requirement=scenario.requirement,
            project_type=scenario.project_type
        )

        # Test project-level RAG
        logger.info("📦 Testing Project-Level RAG (Package Recommendation)...")
        package = await self.rag_client.get_recommended_package(
            requirement=scenario.requirement,
            context={"tech_stack": scenario.tech_stack}
        )

        if package:
            result.package_recommended = True
            result.package_name = package.best_match_package_name
            result.package_confidence = package.confidence
            logger.info(f"  ✅ Package: {package.best_match_package_name}")
            logger.info(f"  ✅ Confidence: {package.confidence:.0%}")
            logger.info(f"  ✅ Templates in package: {len(package.recommended_templates)}")
        else:
            logger.info(f"  ⚠️  No package recommended")

        # Test persona-level RAG
        logger.info("")
        logger.info("👥 Testing Persona-Level RAG (Template Search)...")

        for persona_id in scenario.team_personas:
            persona_result = await self.test_persona(
                scenario=scenario,
                persona_id=persona_id
            )
            result.persona_results[persona_id] = persona_result

            # Update counts
            if persona_result.templates_found > 0:
                result.personas_with_templates += 1
            if persona_result.templates_high_relevance > 0:
                result.personas_with_high_relevance += 1

            result.total_templates_found += persona_result.templates_found
            result.total_high_relevance += persona_result.templates_high_relevance

        # Calculate metrics
        if result.persona_results:
            relevances = [p.average_relevance for p in result.persona_results.values() if p.average_relevance > 0]
            result.average_relevance = sum(relevances) / len(relevances) if relevances else 0.0

        # Identify gaps
        result.missing_personas = [
            p for p, pr in result.persona_results.items()
            if pr.templates_found == 0
        ]

        # Calculate coverage score
        result.coverage_score = self.calculate_coverage_score(result, scenario)

        logger.info("")
        logger.info(f"📊 SCENARIO SUMMARY:")
        logger.info(f"  Templates found: {result.total_templates_found}")
        logger.info(f"  High relevance (>80%): {result.total_high_relevance}")
        logger.info(f"  Personas with templates: {result.personas_with_templates}/{len(scenario.team_personas)}")
        logger.info(f"  Average relevance: {result.average_relevance:.0%}")
        logger.info(f"  Coverage score: {result.coverage_score:.0%}")

        if result.missing_personas:
            logger.info(f"  ⚠️  Missing templates for: {', '.join(result.missing_personas)}")

        return result

    async def test_persona(
        self,
        scenario: RealWorldScenario,
        persona_id: str
    ) -> PersonaTemplateResult:
        """Test template search for a specific persona"""

        result = PersonaTemplateResult(persona_id=persona_id)

        # Extract relevant context from scenario
        context = {
            "project_type": scenario.project_type,
            "tech_stack": scenario.tech_stack,
            "complexity": scenario.complexity
        }

        # Search templates
        templates = await self.rag_client.search_templates_for_persona(
            persona_id=persona_id,
            requirement=scenario.requirement,
            context=context
        )

        result.templates_found = len(templates)

        if templates:
            # Categorize by relevance
            for template in templates:
                relevance = template.relevance_score

                if relevance >= 0.80:
                    result.templates_high_relevance += 1
                elif relevance >= 0.60:
                    result.templates_medium_relevance += 1
                else:
                    result.templates_low_relevance += 1

                # Track categories
                category = template.metadata.category
                if category not in result.categories_covered:
                    result.categories_covered.append(category)

            # Top templates (top 3)
            for template in templates[:3]:
                result.top_templates.append({
                    "name": template.metadata.name,
                    "category": template.metadata.category,
                    "relevance": template.relevance_score,
                    "quality": template.metadata.quality_score
                })

            # Average relevance
            result.average_relevance = sum(t.relevance_score for t in templates) / len(templates)

            logger.info(f"  {persona_id}: {result.templates_found} templates "
                       f"(high: {result.templates_high_relevance}, "
                       f"avg relevance: {result.average_relevance:.0%})")
        else:
            logger.info(f"  {persona_id}: ❌ No templates found")

        return result

    def calculate_coverage_score(
        self,
        result: ScenarioTestResult,
        scenario: RealWorldScenario
    ) -> float:
        """
        Calculate coverage score (0-100) for a scenario.

        Factors:
        - % personas with templates (40%)
        - % personas with high-relevance templates (30%)
        - Average relevance score (20%)
        - Expected category coverage (10%)
        """
        score = 0.0

        # Personas with any templates
        if len(scenario.team_personas) > 0:
            personas_coverage = result.personas_with_templates / len(scenario.team_personas)
            score += personas_coverage * 40

        # Personas with high relevance
        if len(scenario.team_personas) > 0:
            high_relevance_coverage = result.personas_with_high_relevance / len(scenario.team_personas)
            score += high_relevance_coverage * 30

        # Average relevance
        score += result.average_relevance * 20

        # Category coverage
        covered_categories = set()
        for persona_result in result.persona_results.values():
            covered_categories.update(persona_result.categories_covered)

        if scenario.expected_categories:
            category_coverage = len(covered_categories & set(scenario.expected_categories)) / len(scenario.expected_categories)
            score += category_coverage * 10

        return min(100.0, score)

    async def analyze_results(self):
        """Analyze overall test results"""
        logger.info(f"\n{'='*80}")
        logger.info("ANALYZING RESULTS")
        logger.info(f"{'='*80}")

        # Overall coverage
        coverage_scores = [r.coverage_score for r in self.results.scenario_results]
        self.results.overall_coverage_score = sum(coverage_scores) / len(coverage_scores)

        # Count well/poorly covered scenarios
        for result in self.results.scenario_results:
            if result.coverage_score >= 70:
                self.results.scenarios_well_covered += 1
            elif result.coverage_score < 40:
                self.results.scenarios_poorly_covered += 1

        # Persona analysis
        persona_stats = defaultdict(lambda: {
            "scenarios_used": 0,
            "total_templates": 0,
            "total_high_relevance": 0,
            "scenarios_with_no_templates": []
        })

        for scenario_result in self.results.scenario_results:
            for persona_id, persona_result in scenario_result.persona_results.items():
                stats = persona_stats[persona_id]
                stats["scenarios_used"] += 1
                stats["total_templates"] += persona_result.templates_found
                stats["total_high_relevance"] += persona_result.templates_high_relevance

                if persona_result.templates_found == 0:
                    stats["scenarios_with_no_templates"].append(scenario_result.scenario_name)

        self.results.persona_coverage = dict(persona_stats)

        # Identify personas with no templates
        for persona_id, stats in persona_stats.items():
            if stats["total_templates"] == 0:
                self.results.personas_with_no_templates.append(persona_id)

        # Category usage analysis
        for scenario_result in self.results.scenario_results:
            for persona_result in scenario_result.persona_results.values():
                for category in persona_result.categories_covered:
                    self.results.category_usage[category] = self.results.category_usage.get(category, 0) + 1

        # Identify critical gaps
        self.identify_critical_gaps()

        # Generate recommendations
        self.generate_recommendations()

    def identify_critical_gaps(self):
        """Identify critical gaps in template coverage"""

        # Personas with no templates
        if self.results.personas_with_no_templates:
            self.results.critical_gaps.append(
                f"Personas with ZERO templates: {', '.join(self.results.personas_with_no_templates)}"
            )

        # Personas used frequently but with low templates
        for persona_id, stats in self.results.persona_coverage.items():
            scenarios_used = stats["scenarios_used"]
            total_templates = stats["total_templates"]

            if scenarios_used >= 5 and total_templates < scenarios_used * 2:
                avg_per_scenario = total_templates / scenarios_used
                self.results.critical_gaps.append(
                    f"{persona_id}: Used in {scenarios_used} scenarios but only {total_templates} total templates "
                    f"({avg_per_scenario:.1f} avg per scenario)"
                )

        # Missing categories (expected but not found)
        all_expected_categories = set()
        for scenario in ALL_SCENARIOS:
            all_expected_categories.update(scenario.expected_categories)

        found_categories = set(self.results.category_usage.keys())
        missing = all_expected_categories - found_categories

        if missing:
            self.results.missing_categories = list(missing)
            self.results.critical_gaps.append(
                f"Expected categories with NO templates: {', '.join(sorted(missing))}"
            )

    def generate_recommendations(self):
        """Generate recommendations for improvement"""

        # Priority 1: Personas with zero templates
        if self.results.personas_with_no_templates:
            for persona in self.results.personas_with_no_templates:
                self.results.recommendations.append(
                    f"CRITICAL: Create templates for {persona} (currently has ZERO)"
                )

        # Priority 2: Heavily used personas with low coverage
        for persona_id, stats in self.results.persona_coverage.items():
            if persona_id not in self.results.personas_with_no_templates:
                scenarios_used = stats["scenarios_used"]
                total_templates = stats["total_templates"]
                avg_per_scenario = total_templates / scenarios_used if scenarios_used > 0 else 0

                if scenarios_used >= 5 and avg_per_scenario < 3:
                    self.results.recommendations.append(
                        f"HIGH: Expand {persona_id} templates (only {avg_per_scenario:.1f} per scenario)"
                    )

        # Priority 3: Missing categories
        if self.results.missing_categories:
            for category in sorted(self.results.missing_categories):
                self.results.recommendations.append(
                    f"MEDIUM: Create templates for '{category}' category"
                )

        # Priority 4: Poorly covered scenarios
        if self.results.scenarios_poorly_covered > 0:
            self.results.recommendations.append(
                f"REVIEW: {self.results.scenarios_poorly_covered} scenarios have <40% coverage"
            )

    def print_report(self):
        """Print comprehensive test report"""
        logger.info(f"\n{'='*80}")
        logger.info("REAL-WORLD RAG TEST REPORT")
        logger.info(f"{'='*80}")

        # Overall metrics
        logger.info(f"\n📊 OVERALL METRICS:")
        logger.info(f"  Total scenarios tested: {self.results.total_scenarios}")
        logger.info(f"  Overall coverage score: {self.results.overall_coverage_score:.1f}%")
        logger.info(f"  Well-covered scenarios (>70%): {self.results.scenarios_well_covered}")
        logger.info(f"  Poorly-covered scenarios (<40%): {self.results.scenarios_poorly_covered}")

        # Coverage by scenario
        logger.info(f"\n📈 COVERAGE BY SCENARIO:")
        sorted_results = sorted(
            self.results.scenario_results,
            key=lambda x: x.coverage_score,
            reverse=True
        )
        for result in sorted_results:
            icon = "✅" if result.coverage_score >= 70 else "⚠️" if result.coverage_score >= 40 else "❌"
            logger.info(
                f"  {icon} {result.scenario_id} {result.scenario_name}: "
                f"{result.coverage_score:.0%} "
                f"({result.total_high_relevance} high-relevance templates)"
            )

        # Persona coverage
        logger.info(f"\n👥 PERSONA COVERAGE:")
        sorted_personas = sorted(
            self.results.persona_coverage.items(),
            key=lambda x: x[1]["total_templates"],
            reverse=True
        )
        for persona_id, stats in sorted_personas:
            scenarios = stats["scenarios_used"]
            templates = stats["total_templates"]
            high_rel = stats["total_high_relevance"]
            avg = templates / scenarios if scenarios > 0 else 0

            icon = "✅" if avg >= 3 else "⚠️" if avg >= 1 else "❌"
            logger.info(
                f"  {icon} {persona_id}: {templates} templates across {scenarios} scenarios "
                f"(avg: {avg:.1f}, high-rel: {high_rel})"
            )

        # Category usage
        logger.info(f"\n📚 CATEGORY USAGE:")
        sorted_categories = sorted(
            self.results.category_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for category, count in sorted_categories[:15]:
            logger.info(f"  {category}: used in {count} scenarios")

        # Critical gaps
        if self.results.critical_gaps:
            logger.info(f"\n🚨 CRITICAL GAPS:")
            for gap in self.results.critical_gaps:
                logger.info(f"  ❌ {gap}")

        # Recommendations
        if self.results.recommendations:
            logger.info(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.results.recommendations[:10], 1):
                logger.info(f"  {i}. {rec}")

        logger.info(f"\n{'='*80}")

        # Summary verdict
        if self.results.overall_coverage_score >= 70:
            logger.info("✅ VERDICT: Good template coverage overall")
        elif self.results.overall_coverage_score >= 50:
            logger.info("⚠️  VERDICT: Moderate coverage - significant gaps exist")
        else:
            logger.info("❌ VERDICT: Poor coverage - major improvements needed")

        logger.info(f"{'='*80}")

    async def save_results(self):
        """Save results to JSON file"""
        output_file = Path("real_world_test_results.json")

        # Convert to dict
        results_dict = {
            "test_date": self.results.test_date,
            "total_scenarios": self.results.total_scenarios,
            "overall_coverage_score": self.results.overall_coverage_score,
            "scenarios_well_covered": self.results.scenarios_well_covered,
            "scenarios_poorly_covered": self.results.scenarios_poorly_covered,
            "personas_with_no_templates": self.results.personas_with_no_templates,
            "persona_coverage": self.results.persona_coverage,
            "category_usage": self.results.category_usage,
            "missing_categories": self.results.missing_categories,
            "critical_gaps": self.results.critical_gaps,
            "recommendations": self.results.recommendations,
            "scenario_results": [
                {
                    "scenario_id": r.scenario_id,
                    "scenario_name": r.scenario_name,
                    "project_type": r.project_type,
                    "package_recommended": r.package_recommended,
                    "package_name": r.package_name,
                    "package_confidence": r.package_confidence,
                    "total_templates_found": r.total_templates_found,
                    "total_high_relevance": r.total_high_relevance,
                    "personas_with_templates": r.personas_with_templates,
                    "personas_with_high_relevance": r.personas_with_high_relevance,
                    "average_relevance": r.average_relevance,
                    "coverage_score": r.coverage_score,
                    "missing_personas": r.missing_personas,
                    "persona_results": {
                        pid: {
                            "templates_found": pr.templates_found,
                            "templates_high_relevance": pr.templates_high_relevance,
                            "templates_medium_relevance": pr.templates_medium_relevance,
                            "templates_low_relevance": pr.templates_low_relevance,
                            "average_relevance": pr.average_relevance,
                            "categories_covered": pr.categories_covered,
                            "top_templates": pr.top_templates
                        }
                        for pid, pr in r.persona_results.items()
                    }
                }
                for r in self.results.scenario_results
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        logger.info(f"\n💾 Results saved to: {output_file}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main test runner"""
    tester = RealWorldRAGTester()
    await tester.run_all_tests()

    # Exit with appropriate code
    if tester.results.overall_coverage_score >= 50:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
