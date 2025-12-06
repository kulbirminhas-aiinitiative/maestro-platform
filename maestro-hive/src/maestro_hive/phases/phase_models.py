#!/usr/bin/env python3
"""
Phase-Based Workflow Data Models

Defines data structures for phase-based SDLC workflow management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class SDLCPhase(str, Enum):
    """SDLC phases in execution order"""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class PhaseState(str, Enum):
    """State of a phase execution"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REWORK = "needs_rework"
    BLOCKED = "blocked"  # Entry gate failed - cannot start
    REQUIRES_REWORK = "requires_rework"  # Exit gate failed - needs rework (alias for NEEDS_REWORK)


@dataclass
class PhaseIssue:
    """Issue found during phase execution"""
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "completeness", "quality", "deliverable", "dependency"
    description: str
    affected_persona: Optional[str] = None
    affected_deliverable: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class PhaseGateResult:
    """Result of phase gate validation (entry or exit)"""
    passed: bool
    score: float  # 0.0-1.0
    criteria_met: List[str] = field(default_factory=list)
    criteria_failed: List[str] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    required_threshold: float = 1.0
    actual_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "passed": self.passed,
            "score": self.score,
            "criteria_met": self.criteria_met,
            "criteria_failed": self.criteria_failed,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "required_threshold": self.required_threshold,
            "actual_score": self.actual_score
        }


@dataclass
class PhaseExecution:
    """Execution state of a single SDLC phase"""
    phase: SDLCPhase
    state: PhaseState
    iteration: int  # Which iteration of this phase (1-based)
    started_at: datetime
    completed_at: Optional[datetime] = None
    personas_executed: List[str] = field(default_factory=list)
    personas_reused: List[str] = field(default_factory=list)
    entry_gate_result: Optional[PhaseGateResult] = None
    exit_gate_result: Optional[PhaseGateResult] = None
    quality_score: float = 0.0  # 0.0-1.0
    completeness: float = 0.0  # 0.0-1.0
    test_coverage: float = 0.0  # 0.0-1.0 (for testing phase)
    issues: List[PhaseIssue] = field(default_factory=list)
    rework_reason: Optional[str] = None
    
    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "phase": self.phase.value,
            "state": self.state.value,
            "iteration": self.iteration,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "personas_executed": self.personas_executed,
            "personas_reused": self.personas_reused,
            "entry_gate_result": self.entry_gate_result.to_dict() if self.entry_gate_result else None,
            "exit_gate_result": self.exit_gate_result.to_dict() if self.exit_gate_result else None,
            "quality_score": self.quality_score,
            "completeness": self.completeness,
            "test_coverage": self.test_coverage,
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "description": issue.description,
                    "affected_persona": issue.affected_persona,
                    "affected_deliverable": issue.affected_deliverable,
                    "recommendation": issue.recommendation
                }
                for issue in self.issues
            ],
            "rework_reason": self.rework_reason,
            "duration_seconds": self.duration_seconds()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PhaseExecution':
        """Deserialize from dictionary"""
        from datetime import datetime
        
        phase_exec = cls(
            phase=SDLCPhase(data["phase"]),
            state=PhaseState(data["state"]),
            iteration=data["iteration"],
            started_at=datetime.fromisoformat(data["started_at"])
        )
        
        if data.get("completed_at"):
            phase_exec.completed_at = datetime.fromisoformat(data["completed_at"])
        
        phase_exec.personas_executed = data.get("personas_executed", [])
        phase_exec.personas_reused = data.get("personas_reused", [])
        phase_exec.quality_score = data.get("quality_score", 0.0)
        phase_exec.completeness = data.get("completeness", 0.0)
        phase_exec.test_coverage = data.get("test_coverage", 0.0)
        phase_exec.rework_reason = data.get("rework_reason")
        
        # Deserialize gate results
        if data.get("entry_gate_result"):
            phase_exec.entry_gate_result = PhaseGateResult(**data["entry_gate_result"])
        
        if data.get("exit_gate_result"):
            phase_exec.exit_gate_result = PhaseGateResult(**data["exit_gate_result"])
        
        # Deserialize issues
        for issue_data in data.get("issues", []):
            phase_exec.issues.append(PhaseIssue(**issue_data))
        
        return phase_exec


@dataclass
class QualityThresholds:
    """Quality thresholds for a phase iteration"""
    completeness: float  # 0.0-1.0
    quality: float  # 0.0-1.0
    test_coverage: float = 0.0  # 0.0-1.0 (for testing phase)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "completeness": self.completeness,
            "quality": self.quality,
            "test_coverage": self.test_coverage
        }


@dataclass
class WorkflowResult:
    """Complete workflow execution result"""
    success: bool
    session_id: str
    total_iterations: int
    phases_completed: List[SDLCPhase]
    phase_history: List[PhaseExecution]
    total_duration_seconds: float
    total_personas_executed: int
    total_personas_reused: int
    final_quality_score: float
    final_completeness: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "session_id": self.session_id,
            "total_iterations": self.total_iterations,
            "phases_completed": [p.value for p in self.phases_completed],
            "phase_history": [p.to_dict() for p in self.phase_history],
            "total_duration_seconds": self.total_duration_seconds,
            "total_personas_executed": self.total_personas_executed,
            "total_personas_reused": self.total_personas_reused,
            "final_quality_score": self.final_quality_score,
            "final_completeness": self.final_completeness
        }
