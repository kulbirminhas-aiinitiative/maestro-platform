"""
Data models for EPIC Executor.

These models track execution state, acceptance criteria, evidence collection,
and compliance scoring throughout the execution lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionPhase(Enum):
    """Phases of EPIC execution (mirrors compliance audit phases)."""
    UNDERSTANDING = "understanding"       # Phase 1: Parse EPIC, plan work
    DOCUMENTATION = "documentation"       # Phase 2: Generate Confluence docs
    IMPLEMENTATION = "implementation"     # Phase 3: AI-driven code execution
    TESTING = "testing"                   # Phase 4: Test generation
    CORRECTNESS = "correctness"           # Phase 5: TODO/FIXME audit
    BUILD = "build"                       # Phase 6: Build verification
    EVIDENCE = "evidence"                 # Phase 7: AC evidence collection
    COMPLIANCE = "compliance"             # Phase 8: Self-compliance check
    UPDATE = "update"                     # Phase 9: EPIC update


class ACStatus(Enum):
    """Status of an acceptance criterion."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    TESTED = "tested"
    VERIFIED = "verified"
    FAILED = "failed"


class DocumentType(Enum):
    """Types of required compliance documents."""
    TECHNICAL_DESIGN = "technical_design"
    RUNBOOK = "runbook"
    API_DOCS = "api_docs"
    ADR = "adr"
    CONFIG_GUIDE = "config_guide"
    MONITORING = "monitoring"


@dataclass
class AcceptanceCriterion:
    """Represents a single acceptance criterion from the EPIC."""
    id: str                               # AC-1, AC-2, etc.
    description: str                      # Full AC text
    status: ACStatus = ACStatus.PENDING
    jira_task_key: Optional[str] = None   # Child task key if created
    implementation_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    confluence_links: List[str] = field(default_factory=list)
    evidence: Optional[str] = None        # Proof of completion
    notes: Optional[str] = None


@dataclass
class ACEvidence:
    """Evidence collected for an acceptance criterion."""
    ac_id: str
    implementation_file: Optional[str] = None
    implementation_line: Optional[int] = None
    test_file: Optional[str] = None
    test_line: Optional[int] = None
    confluence_link: Optional[str] = None
    verification_output: Optional[str] = None
    verified: bool = False
    verified_at: Optional[datetime] = None


@dataclass
class DocumentInfo:
    """Information about a generated compliance document."""
    doc_type: DocumentType
    title: str
    confluence_page_id: Optional[str] = None
    confluence_url: Optional[str] = None
    local_path: Optional[str] = None       # Optional local backup
    created_at: Optional[datetime] = None
    content_hash: Optional[str] = None     # For change detection
    status: str = "pending"                # pending, created, linked


@dataclass
class PhaseResult:
    """Result from executing a single phase."""
    phase: ExecutionPhase
    success: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    artifacts_created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceScore:
    """
    Breakdown of compliance score matching epic-compliance scoring.

    Total: 100 points
    - Documentation: 15 points (6 docs)
    - Implementation: 25 points (ACs implemented)
    - Test Coverage: 20 points (test:impl ratio)
    - Acceptance Criteria: 25 points (ACs with evidence)
    - Correctness: 10 points (no blocking TODOs)
    - Build: 5 points (passes)

    Passing threshold: 95%
    """
    # Raw counts
    docs_complete: int = 0
    docs_total: int = 6
    acs_implemented: int = 0
    acs_total: int = 0
    test_files: int = 0
    impl_files: int = 0
    acs_with_evidence: int = 0
    blocking_todos: int = 0
    build_passes: bool = False

    # Calculated scores (0-max)
    documentation_score: float = 0.0      # 0-15
    implementation_score: float = 0.0     # 0-25
    test_coverage_score: float = 0.0      # 0-20
    acceptance_criteria_score: float = 0.0  # 0-25
    correctness_score: float = 0.0        # 0-10
    build_score: float = 0.0              # 0-5

    # Total
    total_score: float = 0.0              # 0-100
    passing: bool = False                 # >= 95%

    def calculate(self) -> float:
        """Calculate all scores and total."""
        # Documentation: (docs_complete / 6) * 15
        self.documentation_score = (self.docs_complete / self.docs_total) * 15 if self.docs_total > 0 else 0

        # Implementation: (acs_implemented / acs_total) * 25
        self.implementation_score = (self.acs_implemented / self.acs_total) * 25 if self.acs_total > 0 else 0

        # Test Coverage: min(1.0, test_files / impl_files) * 20
        ratio = self.test_files / self.impl_files if self.impl_files > 0 else 0
        self.test_coverage_score = min(1.0, ratio) * 20

        # Acceptance Criteria: (acs_with_evidence / acs_total) * 25
        self.acceptance_criteria_score = (self.acs_with_evidence / self.acs_total) * 25 if self.acs_total > 0 else 0

        # Correctness: max(0, 10 - (blocking_todos * 2))
        self.correctness_score = max(0, 10 - (self.blocking_todos * 2))

        # Build: 5 if passes, 0 otherwise
        self.build_score = 5 if self.build_passes else 0

        # Total
        self.total_score = (
            self.documentation_score +
            self.implementation_score +
            self.test_coverage_score +
            self.acceptance_criteria_score +
            self.correctness_score +
            self.build_score
        )

        # Passing threshold: 95%
        self.passing = self.total_score >= 95

        return self.total_score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "documentation": {"score": self.documentation_score, "max": 15, "complete": self.docs_complete, "total": self.docs_total},
            "implementation": {"score": self.implementation_score, "max": 25, "implemented": self.acs_implemented, "total": self.acs_total},
            "test_coverage": {"score": self.test_coverage_score, "max": 20, "test_files": self.test_files, "impl_files": self.impl_files},
            "acceptance_criteria": {"score": self.acceptance_criteria_score, "max": 25, "with_evidence": self.acs_with_evidence, "total": self.acs_total},
            "correctness": {"score": self.correctness_score, "max": 10, "blocking_todos": self.blocking_todos},
            "build": {"score": self.build_score, "max": 5, "passes": self.build_passes},
            "total": {"score": self.total_score, "max": 100, "passing": self.passing},
        }


@dataclass
class EpicInfo:
    """Information about the EPIC being executed."""
    key: str                              # MD-2385
    summary: str
    description: str
    status: str
    priority: str
    labels: List[str] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    child_tasks: List[str] = field(default_factory=list)
    linked_epics: List[str] = field(default_factory=list)
    confluence_space_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ExecutionConfig:
    """Configuration for EPIC execution."""
    # JIRA settings
    jira_base_url: str
    jira_email: str
    jira_api_token: str

    # Confluence settings
    confluence_base_url: str
    confluence_email: str
    confluence_api_token: str
    confluence_space_key: str

    # Optional settings (must come last)
    jira_project_key: str = "MD"
    confluence_parent_page_id: Optional[str] = None

    # Execution settings
    max_iterations: int = 3               # Max retry iterations for < 95%
    enable_ai_execution: bool = True      # Use team_execution_v2
    enable_test_generation: bool = True   # Generate tests
    output_dir: str = "/tmp"              # Local backup directory

    # Quality thresholds
    min_compliance_score: float = 95.0    # Minimum passing score
    max_blocking_todos: int = 0           # Maximum blocking TODOs allowed


@dataclass
class ExecutionResult:
    """Final result from EPIC execution."""
    epic_key: str
    success: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    iterations: int = 1

    # EPIC info
    epic_info: Optional[EpicInfo] = None

    # Phase results
    phase_results: Dict[ExecutionPhase, PhaseResult] = field(default_factory=dict)

    # Documents created
    documents: List[DocumentInfo] = field(default_factory=list)

    # Acceptance criteria tracking
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    evidence: List[ACEvidence] = field(default_factory=list)

    # Implementation tracking
    implementation_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)

    # Quality metrics
    blocking_todos: int = 0
    build_passed: bool = False

    # Compliance score
    compliance_score: Optional[ComplianceScore] = None

    # JIRA updates
    child_tasks_created: List[str] = field(default_factory=list)
    epic_updated: bool = False
    confluence_pages_linked: bool = False

    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Report paths
    execution_report_path: Optional[str] = None

    # Iteration tracking (for gap-driven iteration)
    iteration_history: List["IterationRecord"] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "epic_key": self.epic_key,
            "success": self.success,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "iterations": self.iterations,
            "compliance_score": self.compliance_score.to_dict() if self.compliance_score else None,
            "documents_created": len(self.documents),
            "acs_total": len(self.acceptance_criteria),
            "acs_verified": len([ac for ac in self.acceptance_criteria if ac.status == ACStatus.VERIFIED]),
            "implementation_files": len(self.implementation_files),
            "test_files": len(self.test_files),
            "child_tasks_created": self.child_tasks_created,
            "errors": self.errors,
            "warnings": self.warnings,
            "iteration_history": [r.to_dict() for r in self.iteration_history],
        }


class GapSeverity(Enum):
    """Severity level for identified gaps."""
    CRITICAL = "critical"   # Blocks compliance, must fix
    HIGH = "high"           # Major impact on score
    MEDIUM = "medium"       # Moderate impact
    LOW = "low"             # Minor impact


@dataclass
class Gap:
    """
    Represents a gap identified during execution.

    Gaps are areas where the execution fell short of compliance requirements.
    """
    category: str           # documentation, implementation, testing, evidence, correctness, build
    description: str        # Human-readable description
    severity: GapSeverity = GapSeverity.MEDIUM
    impact_points: float = 0.0  # Estimated points lost due to this gap
    remediation: Optional[str] = None  # Suggested fix
    related_items: List[str] = field(default_factory=list)  # AC IDs, file names, etc.
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "description": self.description,
            "severity": self.severity.value,
            "impact_points": self.impact_points,
            "remediation": self.remediation,
            "related_items": self.related_items,
            "resolved": self.resolved,
        }


@dataclass
class IterationRecord:
    """
    Record of a single iteration in gap-driven execution.

    Tracks what was attempted, what gaps were found, and score progression.
    """
    iteration_number: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Score at this iteration
    compliance_score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)

    # Gaps identified
    gaps_identified: List[Gap] = field(default_factory=list)
    focus_areas: List[str] = field(default_factory=list)

    # Convergence metrics
    score_improvement: float = 0.0  # Compared to previous iteration
    gaps_resolved: int = 0
    new_gaps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "iteration_number": self.iteration_number,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "compliance_score": self.compliance_score,
            "score_breakdown": self.score_breakdown,
            "gaps_identified": [g.to_dict() for g in self.gaps_identified],
            "focus_areas": self.focus_areas,
            "score_improvement": self.score_improvement,
            "gaps_resolved": self.gaps_resolved,
            "new_gaps": self.new_gaps,
        }


@dataclass
class ConvergenceMetrics:
    """
    Metrics for detecting convergence in gap-driven iteration.

    Convergence is detected when:
    1. Compliance score >= 95% (target achieved), OR
    2. No gaps identified, OR
    3. Score improvement < threshold for N consecutive iterations, OR
    4. Maximum iterations reached
    """
    target_score: float = 95.0
    current_score: float = 0.0
    improvement_threshold: float = 2.0  # Min score improvement to continue
    stagnation_limit: int = 2  # Consecutive low-improvement iterations before stopping

    # Tracking
    iterations_completed: int = 0
    consecutive_low_improvement: int = 0
    total_gaps_remaining: int = 0
    converged: bool = False
    convergence_reason: Optional[str] = None

    def check_convergence(
        self,
        new_score: float,
        gaps_count: int,
        max_iterations: int,
    ) -> bool:
        """
        Check if iteration should stop.

        Returns:
            True if converged (should stop), False if should continue
        """
        score_improvement = new_score - self.current_score
        self.current_score = new_score
        self.total_gaps_remaining = gaps_count
        self.iterations_completed += 1

        # Check target achieved
        if new_score >= self.target_score:
            self.converged = True
            self.convergence_reason = f"Target score achieved: {new_score:.1f}% >= {self.target_score}%"
            return True

        # Check no gaps
        if gaps_count == 0:
            self.converged = True
            self.convergence_reason = "No gaps remaining"
            return True

        # Check max iterations
        if self.iterations_completed >= max_iterations:
            self.converged = True
            self.convergence_reason = f"Maximum iterations ({max_iterations}) reached"
            return True

        # Check stagnation
        if score_improvement < self.improvement_threshold:
            self.consecutive_low_improvement += 1
            if self.consecutive_low_improvement >= self.stagnation_limit:
                self.converged = True
                self.convergence_reason = f"Stagnation detected: improvement < {self.improvement_threshold}% for {self.stagnation_limit} iterations"
                return True
        else:
            self.consecutive_low_improvement = 0

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_score": self.target_score,
            "current_score": self.current_score,
            "iterations_completed": self.iterations_completed,
            "total_gaps_remaining": self.total_gaps_remaining,
            "converged": self.converged,
            "convergence_reason": self.convergence_reason,
        }
