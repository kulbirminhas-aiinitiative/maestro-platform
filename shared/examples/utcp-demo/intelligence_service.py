"""
Example Intelligence Service with UTCP Support

This demonstrates an AI-powered intelligence service that provides:
1. Code analysis and recommendations
2. Architecture suggestions
3. Technology stack recommendations
"""

from typing import Dict, Any, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from maestro_core_api import APIConfig
from maestro_core_api.utcp_extensions import UTCPEnabledAPI


# Models
class AnalysisType(str, Enum):
    """Types of analysis."""
    CODE_QUALITY = "code_quality"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PERFORMANCE = "performance"


class TechnologyDomain(str, Enum):
    """Technology domains."""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    TESTING = "testing"


class CodeAnalysisRequest(BaseModel):
    """Request for code analysis."""
    code_description: str = Field(..., description="Description of the code to analyze")
    analysis_type: AnalysisType = Field(..., description="Type of analysis to perform")
    context: Optional[str] = Field(None, description="Additional context")


class CodeAnalysisResponse(BaseModel):
    """Code analysis response."""
    analysis_id: str
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    score: int = Field(..., ge=0, le=100, description="Quality score out of 100")
    severity_breakdown: Dict[str, int]


class ArchitectureRequest(BaseModel):
    """Request for architecture suggestions."""
    project_description: str = Field(..., description="Project description")
    requirements: List[str] = Field(..., description="Key requirements")
    constraints: Optional[List[str]] = Field(default_factory=list, description="Constraints")
    scale: str = Field("medium", description="Expected scale: small/medium/large/enterprise")


class ArchitectureResponse(BaseModel):
    """Architecture suggestion response."""
    suggestion_id: str
    architecture_pattern: str
    components: List[Dict[str, str]]
    technologies: Dict[str, List[str]]
    rationale: str
    trade_offs: Dict[str, str]


class TechStackRequest(BaseModel):
    """Request for technology stack recommendation."""
    project_type: str = Field(..., description="Type of project")
    domain: TechnologyDomain = Field(..., description="Technology domain")
    requirements: List[str] = Field(..., description="Technical requirements")
    team_experience: Optional[str] = Field(None, description="Team's technology experience")


class TechStackResponse(BaseModel):
    """Technology stack recommendation."""
    recommendation_id: str
    primary_technologies: List[Dict[str, str]]
    supporting_tools: List[str]
    learning_resources: List[str]
    reasoning: str


# Create UTCP-enabled API
config = APIConfig(
    title="Intelligence Service",
    description="MAESTRO Intelligence Service - AI-powered analysis and recommendations",
    service_name="intelligence-service",
    version="1.0.0",
    host="0.0.0.0",
    port=8002
)

api = UTCPEnabledAPI(
    config,
    base_url="http://localhost:8002",
    enable_utcp_execution=True
)


# Intelligence endpoints
@api.post(
    "/analyze/code",
    response_model=CodeAnalysisResponse,
    summary="Analyze code quality",
    description="Performs intelligent code analysis and provides recommendations",
    tags=["Analysis"]
)
async def analyze_code(request: CodeAnalysisRequest) -> CodeAnalysisResponse:
    """
    Analyze code and provide intelligent recommendations.

    Performs various types of analysis including quality, security,
    performance, and architectural concerns.
    """
    analysis_id = f"analysis-{hash(request.code_description) % 10000:04d}"

    # Simulate findings based on analysis type
    findings_map = {
        AnalysisType.CODE_QUALITY: [
            {"type": "complexity", "severity": "medium", "message": "Function complexity could be reduced"},
            {"type": "duplication", "severity": "low", "message": "Minor code duplication detected"},
            {"type": "naming", "severity": "low", "message": "Some variable names could be more descriptive"}
        ],
        AnalysisType.ARCHITECTURE: [
            {"type": "coupling", "severity": "high", "message": "High coupling between modules detected"},
            {"type": "separation", "severity": "medium", "message": "Business logic mixed with presentation layer"},
            {"type": "scalability", "severity": "medium", "message": "Current design may not scale beyond 10K users"}
        ],
        AnalysisType.SECURITY: [
            {"type": "authentication", "severity": "critical", "message": "Missing authentication on sensitive endpoints"},
            {"type": "injection", "severity": "high", "message": "SQL injection vulnerability detected"},
            {"type": "encryption", "severity": "medium", "message": "Data at rest not encrypted"}
        ],
        AnalysisType.PERFORMANCE: [
            {"type": "database", "severity": "high", "message": "N+1 query problem detected"},
            {"type": "caching", "severity": "medium", "message": "No caching strategy implemented"},
            {"type": "async", "severity": "low", "message": "Blocking operations in async context"}
        ]
    }

    findings = findings_map[request.analysis_type]

    # Generate recommendations
    recommendations = [
        f"Refactor code to address {findings[0]['type']} issues",
        f"Implement automated testing for {request.analysis_type.value}",
        "Consider using static analysis tools in CI/CD pipeline",
        "Regular code reviews with focus on identified patterns"
    ]

    # Calculate score (inverse to severity)
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        severity_counts[finding["severity"]] += 1

    score = max(0, 100 - (
        severity_counts["critical"] * 30 +
        severity_counts["high"] * 20 +
        severity_counts["medium"] * 10 +
        severity_counts["low"] * 5
    ))

    return CodeAnalysisResponse(
        analysis_id=analysis_id,
        findings=findings,
        recommendations=recommendations,
        score=score,
        severity_breakdown=severity_counts
    )


@api.post(
    "/suggest/architecture",
    response_model=ArchitectureResponse,
    summary="Suggest architecture",
    description="Provides intelligent architecture suggestions based on requirements",
    tags=["Architecture"]
)
async def suggest_architecture(request: ArchitectureRequest) -> ArchitectureResponse:
    """
    Suggest optimal architecture based on project requirements.

    Analyzes requirements and constraints to recommend appropriate
    architectural patterns and technologies.
    """
    suggestion_id = f"arch-{hash(request.project_description) % 10000:04d}"

    # Determine pattern based on scale
    scale_patterns = {
        "small": ("Monolithic", "Single deployable unit with layered architecture"),
        "medium": ("Modular Monolith", "Organized into distinct modules with clear boundaries"),
        "large": ("Microservices", "Distributed services with independent deployment"),
        "enterprise": ("Event-Driven Microservices", "Microservices with event sourcing and CQRS")
    }

    pattern_name, pattern_desc = scale_patterns.get(request.scale, scale_patterns["medium"])

    # Generate components
    components = [
        {"name": "API Gateway", "purpose": "Single entry point for all client requests"},
        {"name": "Service Layer", "purpose": "Business logic and service orchestration"},
        {"name": "Data Layer", "purpose": "Data access and persistence"},
        {"name": "Cache Layer", "purpose": "Performance optimization"},
        {"name": "Message Queue", "purpose": "Asynchronous processing"}
    ]

    # Technology recommendations
    technologies = {
        "backend": ["Python/FastAPI", "Node.js/Express", "Go"],
        "frontend": ["React", "Vue.js", "Next.js"],
        "database": ["PostgreSQL", "MongoDB", "Redis (cache)"],
        "infrastructure": ["Docker", "Kubernetes", "Terraform"],
        "messaging": ["RabbitMQ", "Apache Kafka", "Redis Streams"]
    }

    rationale = f"""
Recommended {pattern_name} architecture for {request.scale} scale project.

Key considerations:
- Supports requirements: {', '.join(request.requirements[:3])}
- Optimized for {request.scale} scale operations
- Allows for future growth and evolution
- Balance between complexity and maintainability
"""

    trade_offs = {
        "Pros": f"{pattern_name} provides good balance for your scale",
        "Cons": "Initial setup complexity, requires skilled team",
        "Complexity": f"{'Low' if request.scale == 'small' else 'Medium' if request.scale in ['medium', 'large'] else 'High'}",
        "Scalability": f"{'Vertical' if request.scale == 'small' else 'Horizontal'}"
    }

    return ArchitectureResponse(
        suggestion_id=suggestion_id,
        architecture_pattern=pattern_name,
        components=components,
        technologies=technologies,
        rationale=rationale.strip(),
        trade_offs=trade_offs
    )


@api.post(
    "/recommend/tech-stack",
    response_model=TechStackResponse,
    summary="Recommend technology stack",
    description="Recommends optimal technology stack for the project",
    tags=["Recommendations"]
)
async def recommend_tech_stack(request: TechStackRequest) -> TechStackResponse:
    """
    Recommend optimal technology stack.

    Considers project type, domain, requirements, and team experience
    to suggest the best technology choices.
    """
    recommendation_id = f"tech-{hash(request.project_type) % 10000:04d}"

    # Domain-specific recommendations
    domain_tech = {
        TechnologyDomain.BACKEND: [
            {"name": "FastAPI", "reason": "Modern, fast, with automatic API documentation"},
            {"name": "PostgreSQL", "reason": "Robust, ACID-compliant relational database"},
            {"name": "Redis", "reason": "High-performance caching and session storage"}
        ],
        TechnologyDomain.FRONTEND: [
            {"name": "React", "reason": "Popular, extensive ecosystem, component-based"},
            {"name": "TypeScript", "reason": "Type safety for large applications"},
            {"name": "Tailwind CSS", "reason": "Utility-first, highly customizable"}
        ],
        TechnologyDomain.DATABASE: [
            {"name": "PostgreSQL", "reason": "Feature-rich, excellent performance"},
            {"name": "TimescaleDB", "reason": "Time-series data optimization"},
            {"name": "Elasticsearch", "reason": "Full-text search capabilities"}
        ],
        TechnologyDomain.INFRASTRUCTURE: [
            {"name": "Docker", "reason": "Containerization for consistent deployments"},
            {"name": "Kubernetes", "reason": "Container orchestration at scale"},
            {"name": "Terraform", "reason": "Infrastructure as code"}
        ],
        TechnologyDomain.TESTING: [
            {"name": "Pytest", "reason": "Comprehensive Python testing framework"},
            {"name": "Playwright", "reason": "Modern end-to-end testing"},
            {"name": "k6", "reason": "Performance and load testing"}
        ]
    }

    primary_technologies = domain_tech[request.domain]

    supporting_tools = [
        "GitHub Actions (CI/CD)",
        "Prometheus (Monitoring)",
        "Grafana (Visualization)",
        "Sentry (Error tracking)",
        "Datadog (Observability)"
    ]

    learning_resources = [
        f"Official {primary_technologies[0]['name']} documentation",
        "Real-world project tutorials on GitHub",
        "Architecture patterns and best practices",
        "Team workshops and code reviews"
    ]

    reasoning = f"""
Selected technologies optimized for {request.domain.value} development:

Primary choices emphasize:
- Modern development practices
- Strong community support
- Production-ready stability
- Team productivity

{'Team experience with ' + request.team_experience + ' considered in recommendations.' if request.team_experience else 'Standard industry best practices applied.'}
"""

    return TechStackResponse(
        recommendation_id=recommendation_id,
        primary_technologies=primary_technologies,
        supporting_tools=supporting_tools,
        learning_resources=learning_resources,
        reasoning=reasoning.strip()
    )


@api.get(
    "/capabilities",
    summary="List service capabilities",
    description="Returns all capabilities this intelligence service provides",
    tags=["Service Info"]
)
async def list_capabilities() -> Dict[str, Any]:
    """List all capabilities of this service."""
    return {
        "service": "intelligence-service",
        "capabilities": [
            "Code quality analysis",
            "Architecture suggestions",
            "Security analysis",
            "Performance analysis",
            "Technology stack recommendations"
        ],
        "analysis_types": [t.value for t in AnalysisType],
        "technology_domains": [d.value for d in TechnologyDomain],
        "utcp_enabled": True
    }


if __name__ == "__main__":
    print("🧠 Starting Intelligence Service with UTCP support...")
    print(f"📡 UTCP Manual available at: http://localhost:8002/utcp-manual.json")
    print(f"🔧 Tools endpoint: http://localhost:8002/utcp/tools")
    print(f"📚 API Docs: http://localhost:8002/docs")
    print()

    api.run()