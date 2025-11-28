"""
Workflow Models
Pydantic models for workflow recommendations and approval
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class GapSeverity(str, Enum):
    """Gap severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GapType(str, Enum):
    """Gap types"""
    MISSING_PERSONA = "missing_persona"
    LOW_COVERAGE = "low_coverage"
    MISSING_CATEGORY = "missing_category"
    MISSING_FRAMEWORK = "missing_framework"


class ActionType(str, Enum):
    """Recommendation action types"""
    VARIANT = "variant"
    CREATE_TEMPLATE = "create_template"
    REUSE = "reuse"
    RESEARCH_NEEDED = "research_needed"  # For backward compatibility


class VariantDecision(str, Enum):
    """Variant decision types from intelligence layer"""
    REUSE = "REUSE"
    VARIANT = "VARIANT"
    CREATE_NEW = "CREATE_NEW"


class RecommendationStatus(str, Enum):
    """Recommendation approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Gap(BaseModel):
    """Gap analysis result"""
    gap_id: str
    gap_type: GapType
    severity: GapSeverity
    persona: Optional[str] = None
    category: Optional[str] = None
    scenario_ids: List[str] = Field(default_factory=list)
    current_coverage: float = 0.0
    target_coverage: float = 70.0
    description: str
    estimated_templates_needed: int = 1

    class Config:
        use_enum_values = True


class RecommendationBase(BaseModel):
    """Base recommendation model"""
    recommendation_id: str
    gap: Gap
    action_type: ActionType
    priority: int
    template_name: str
    template_description: str
    persona: str
    category: str
    language: str
    framework: Optional[str] = None
    research_keywords: List[str] = Field(default_factory=list)
    confidence: float = Field(0.8, ge=0.0, le=1.0)

    # Intelligence layer fields
    variant_decision: Optional[VariantDecision] = None
    base_template_id: Optional[str] = None
    base_template_name: Optional[str] = None
    similarity_score: float = 0.0
    quality_validated: bool = False

    class Config:
        use_enum_values = True


class Recommendation(RecommendationBase):
    """Full recommendation with metadata"""
    created_at: datetime
    run_id: str = "UNKNOWN"

    # Approval tracking
    status: RecommendationStatus = RecommendationStatus.PENDING
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Implementation tracking
    implementation_started_at: Optional[datetime] = None
    implementation_completed_at: Optional[datetime] = None
    created_template_id: Optional[UUID] = None


class RecommendationApprovalRequest(BaseModel):
    """Request to approve a recommendation"""
    approved_by: str = Field(..., min_length=1, max_length=100, description="Username approving the recommendation")
    notes: Optional[str] = Field(None, max_length=500, description="Optional approval notes")


class RecommendationRejectionRequest(BaseModel):
    """Request to reject a recommendation"""
    rejected_by: str = Field(..., min_length=1, max_length=100, description="Username rejecting the recommendation")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for rejection")


class RecommendationListResponse(BaseModel):
    """Paginated list of recommendations"""
    total: int = Field(..., description="Total number of recommendations")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    recommendations: List[Recommendation] = Field(..., description="List of recommendations")

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there's a next page"""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1


class WorkflowRunSummary(BaseModel):
    """Summary of a workflow run"""
    run_id: str
    run_timestamp: datetime
    mode: str
    overall_coverage_before: float
    overall_coverage_after: float
    coverage_improvement: float
    total_gaps_identified: int
    critical_gaps: int
    high_priority_gaps: int
    recommendations_generated: int
    templates_auto_generated: int
    templates_synced: int
    templates_reused: int
    templates_variants_created: int
    templates_new_created: int
    quality_gate_checks: int
    quality_gate_failures: int
    similarity_checks_performed: int
    avg_template_similarity: float
    execution_time_seconds: float
    success: bool
    errors: List[str] = Field(default_factory=list)


class WorkflowRunListResponse(BaseModel):
    """List of workflow runs"""
    total: int
    runs: List[WorkflowRunSummary]
