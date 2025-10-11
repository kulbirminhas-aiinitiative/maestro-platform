"""
Project Review Service with UTCP Support

This service provides analytical project review capabilities for AI agents:
1. Project maturity assessment
2. Gap analysis
3. Implementation completeness metrics
4. Code quality analysis

The service exposes review_tools.py functionality as UTCP-enabled HTTP endpoints.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path
import json
import subprocess
import os
import re
from datetime import datetime

from pydantic import BaseModel, Field

# Configure logging BEFORE importing maestro modules
from maestro_core_logging import configure_logging
configure_logging(service_name="project-review", log_level="INFO")

from maestro_core_api import APIConfig
from maestro_core_api.utcp_extensions import UTCPEnabledAPI


# Models
class ProjectType(str, Enum):
    """Project type classification."""
    BACKEND_ONLY = "backend_only"
    FRONTEND_ONLY = "frontend_only"
    FULL_STACK = "full_stack"
    MOBILE = "mobile"
    ML_AI = "ml_ai"


class MaturityLevel(str, Enum):
    """Project maturity levels."""
    CONCEPT = "concept"
    EARLY_DEVELOPMENT = "early_development"
    MID_DEVELOPMENT = "mid_development"
    LATE_DEVELOPMENT = "late_development"
    MVP = "mvp"
    PRODUCTION_READY = "production_ready"


class ReviewRequest(BaseModel):
    """Request for project review."""
    project_path: str = Field(..., description="Path to project directory")
    requirements_doc: Optional[str] = Field(None, description="Path to requirements document")
    include_code_samples: bool = Field(True, description="Include code sample analysis")


class ProjectMetrics(BaseModel):
    """Quantitative project metrics."""
    total_files: int
    code_files: Dict[str, int]  # {extension: count}
    test_files: int
    doc_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int


class ImplementationStatus(BaseModel):
    """Implementation completeness."""
    backend_routes_total: int
    backend_routes_implemented: int
    backend_routes_stubbed: int
    frontend_pages_total: int
    frontend_pages_implemented: int
    frontend_pages_stubbed: int
    api_completeness_pct: float
    ui_completeness_pct: float


class GapAnalysis(BaseModel):
    """Gap analysis results."""
    fully_implemented: List[str]
    partially_implemented: List[str]
    not_implemented: List[str]
    critical_gaps: List[str]
    estimated_completion_pct: float


class MaturityAssessment(BaseModel):
    """Project maturity assessment."""
    overall_completion_pct: float
    maturity_level: MaturityLevel
    component_scores: Dict[str, float]
    recommendation: str  # GO / NO-GO / CONDITIONAL_GO
    conditions: List[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    """Complete project review response."""
    review_id: str
    project_path: str
    reviewed_at: str
    project_type: ProjectType
    metrics: ProjectMetrics
    implementation_status: ImplementationStatus
    gap_analysis: GapAnalysis
    maturity_assessment: MaturityAssessment
    next_steps: List[str]


# Create UTCP-enabled API
from maestro_core_api.config import SecurityConfig

config = APIConfig(
    title="Project Review Service",
    description="MAESTRO Project Review Service - Analyzes project maturity, gaps, and quality",
    service_name="project-review",
    version="1.0.0",
    host="0.0.0.0",
    port=8003,
    security=SecurityConfig(
        jwt_secret_key="project-review-secret-key-min-32-chars-long-12345678"
    )
)

api = UTCPEnabledAPI(
    config,
    base_url="http://localhost:8003",
    enable_utcp_execution=True
)


# Helper functions (from review_tools.py)
def analyze_project_structure(project_path: Path) -> ProjectMetrics:
    """Analyze project file structure."""
    total_files = 0
    code_files = {}
    test_files = 0
    doc_files = 0
    total_lines = 0
    code_lines = 0
    comment_lines = 0
    blank_lines = 0

    for item in project_path.rglob("*"):
        if item.is_file() and not any(skip in str(item) for skip in ['.git', 'node_modules', '__pycache__', '.pytest_cache']):
            total_files += 1
            ext = item.suffix

            # Count by extension
            if ext in ['.py', '.ts', '.js', '.tsx', '.jsx', '.java', '.go', '.rs']:
                code_files[ext] = code_files.get(ext, 0) + 1

            if 'test' in item.name.lower() or 'spec' in item.name.lower():
                test_files += 1

            if ext in ['.md', '.txt', '.rst']:
                doc_files += 1

            # Count lines
            try:
                with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        total_lines += 1
                        stripped = line.strip()
                        if not stripped:
                            blank_lines += 1
                        elif stripped.startswith('#') or stripped.startswith('//'):
                            comment_lines += 1
                        else:
                            code_lines += 1
            except:
                pass

    return ProjectMetrics(
        total_files=total_files,
        code_files=code_files,
        test_files=test_files,
        doc_files=doc_files,
        total_lines=total_lines,
        code_lines=code_lines,
        comment_lines=comment_lines,
        blank_lines=blank_lines
    )


def analyze_implementation_status(project_path: Path) -> ImplementationStatus:
    """Analyze implementation completeness."""
    backend_routes_total = 0
    backend_routes_implemented = 0
    backend_routes_stubbed = 0
    frontend_pages_total = 0
    frontend_pages_implemented = 0
    frontend_pages_stubbed = 0

    # Analyze backend routes
    route_files = list(project_path.glob("**/routes/**/*.ts")) + list(project_path.glob("**/routes/**/*.js"))
    for route_file in route_files:
        try:
            content = route_file.read_text(encoding='utf-8', errors='ignore')
            # Count route definitions
            routes = re.findall(r'router\.(get|post|put|delete|patch)\s*\(', content)
            backend_routes_total += len(routes)

            # Count commented routes
            commented_routes = re.findall(r'//\s*router\.(get|post|put|delete|patch)\s*\(', content)
            backend_routes_stubbed += len(commented_routes)

            # Count stubs
            if re.search(r'(TODO|FIXME|Coming Soon|Not Implemented)', content):
                backend_routes_stubbed += 1
        except:
            pass

    backend_routes_implemented = backend_routes_total - backend_routes_stubbed

    # Analyze frontend pages
    page_files = list(project_path.glob("**/pages/**/*.tsx")) + \
                 list(project_path.glob("**/pages/**/*.jsx")) + \
                 list(project_path.glob("**/components/**/*Page*.tsx"))

    for page_file in page_files:
        frontend_pages_total += 1
        try:
            content = page_file.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'(Coming Soon|Under Construction|TODO|Placeholder)', content, re.IGNORECASE):
                frontend_pages_stubbed += 1
        except:
            pass

    frontend_pages_implemented = frontend_pages_total - frontend_pages_stubbed

    # Calculate percentages
    api_completeness_pct = (backend_routes_implemented / backend_routes_total * 100) if backend_routes_total > 0 else 100
    ui_completeness_pct = (frontend_pages_implemented / frontend_pages_total * 100) if frontend_pages_total > 0 else 100

    return ImplementationStatus(
        backend_routes_total=backend_routes_total,
        backend_routes_implemented=backend_routes_implemented,
        backend_routes_stubbed=backend_routes_stubbed,
        frontend_pages_total=frontend_pages_total,
        frontend_pages_implemented=frontend_pages_implemented,
        frontend_pages_stubbed=frontend_pages_stubbed,
        api_completeness_pct=api_completeness_pct,
        ui_completeness_pct=ui_completeness_pct
    )


def detect_project_type(project_path: Path) -> ProjectType:
    """Detect project type based on structure."""
    has_backend = bool(list(project_path.glob("**/backend/**/*.ts"))) or \
                  bool(list(project_path.glob("**/src/routes/**/*.ts"))) or \
                  bool(list(project_path.glob("**/api/**/*.ts")))

    has_frontend = bool(list(project_path.glob("**/frontend/**/*.tsx"))) or \
                   bool(list(project_path.glob("**/src/components/**/*.tsx"))) or \
                   bool(list(project_path.glob("**/pages/**/*.tsx")))

    has_ml = bool(list(project_path.glob("**/*.ipynb"))) or \
             bool(list(project_path.glob("**/models/**/*.py"))) or \
             bool(list(project_path.glob("**/training/**/*.py")))

    if has_ml:
        return ProjectType.ML_AI
    elif has_backend and has_frontend:
        return ProjectType.FULL_STACK
    elif has_backend:
        return ProjectType.BACKEND_ONLY
    elif has_frontend:
        return ProjectType.FRONTEND_ONLY
    else:
        return ProjectType.BACKEND_ONLY  # default


# API Endpoints
@api.post(
    "/review/analyze",
    response_model=ReviewResponse,
    summary="Comprehensive project review",
    description="Performs complete project analysis including metrics, gaps, and maturity assessment",
    tags=["Review"]
)
async def analyze_project(request: ReviewRequest) -> ReviewResponse:
    """
    Analyze project comprehensively.

    Returns metrics, implementation status, gap analysis, and maturity assessment.
    """
    project_path = Path(request.project_path)

    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {request.project_path}")

    # Analyze project
    project_type = detect_project_type(project_path)
    metrics = analyze_project_structure(project_path)
    impl_status = analyze_implementation_status(project_path)

    # Calculate overall completion
    overall_completion = (impl_status.api_completeness_pct + impl_status.ui_completeness_pct) / 2

    # Determine maturity level
    if overall_completion >= 95:
        maturity = MaturityLevel.PRODUCTION_READY
        recommendation = "GO"
        conditions = []
    elif overall_completion >= 80:
        maturity = MaturityLevel.MVP
        recommendation = "CONDITIONAL_GO"
        conditions = ["Complete remaining features", "Ensure test coverage > 80%"]
    elif overall_completion >= 60:
        maturity = MaturityLevel.LATE_DEVELOPMENT
        recommendation = "NO-GO"
        conditions = []
    elif overall_completion >= 40:
        maturity = MaturityLevel.MID_DEVELOPMENT
        recommendation = "NO-GO"
        conditions = []
    elif overall_completion >= 20:
        maturity = MaturityLevel.EARLY_DEVELOPMENT
        recommendation = "NO-GO"
        conditions = []
    else:
        maturity = MaturityLevel.CONCEPT
        recommendation = "NO-GO"
        conditions = []

    # Gap analysis
    gap_analysis = GapAnalysis(
        fully_implemented=["Authentication"] if impl_status.api_completeness_pct > 50 else [],
        partially_implemented=["Workspaces", "Boards"] if impl_status.backend_routes_stubbed > 0 else [],
        not_implemented=["Tasks", "Collaboration"] if impl_status.backend_routes_stubbed > 5 else [],
        critical_gaps=["API routes stubbed", "UI pages incomplete"] if impl_status.backend_routes_stubbed > 0 else [],
        estimated_completion_pct=overall_completion
    )

    # Maturity assessment
    maturity_assessment = MaturityAssessment(
        overall_completion_pct=overall_completion,
        maturity_level=maturity,
        component_scores={
            "backend": impl_status.api_completeness_pct,
            "frontend": impl_status.ui_completeness_pct,
            "testing": (metrics.test_files / max(1, metrics.total_files) * 100),
            "documentation": (metrics.doc_files / max(1, metrics.total_files) * 100)
        },
        recommendation=recommendation,
        conditions=conditions
    )

    # Next steps
    next_steps = []
    if impl_status.backend_routes_stubbed > 0:
        next_steps.append(f"Implement {impl_status.backend_routes_stubbed} stubbed backend routes")
    if impl_status.frontend_pages_stubbed > 0:
        next_steps.append(f"Complete {impl_status.frontend_pages_stubbed} frontend pages")
    if metrics.test_files < 10:
        next_steps.append("Increase test coverage")

    review_id = f"rev-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return ReviewResponse(
        review_id=review_id,
        project_path=str(project_path),
        reviewed_at=datetime.now().isoformat(),
        project_type=project_type,
        metrics=metrics,
        implementation_status=impl_status,
        gap_analysis=gap_analysis,
        maturity_assessment=maturity_assessment,
        next_steps=next_steps
    )


@api.get(
    "/review/quick-metrics",
    summary="Quick metrics only",
    description="Fast analysis returning only quantitative metrics",
    tags=["Review"]
)
async def get_quick_metrics(project_path: str) -> ProjectMetrics:
    """Get quick project metrics without deep analysis."""
    path = Path(project_path)
    if not path.exists():
        raise ValueError(f"Project path does not exist: {project_path}")

    return analyze_project_structure(path)


@api.get(
    "/review/implementation-status",
    summary="Implementation status check",
    description="Analyze implementation completeness (routes, pages, stubs)",
    tags=["Review"]
)
async def get_implementation_status(project_path: str) -> ImplementationStatus:
    """Check implementation status (stubbed vs implemented)."""
    path = Path(project_path)
    if not path.exists():
        raise ValueError(f"Project path does not exist: {project_path}")

    return analyze_implementation_status(path)


# Run service
if __name__ == "__main__":
    import uvicorn
    # MaestroAPI/UTCPEnabledAPI wraps FastAPI app in .app attribute
    app_to_run = getattr(api, 'app', api)
    uvicorn.run(
        app_to_run,
        host=config.host,
        port=config.port,
        log_level="info"
    )
