"""Domain Onboarding Models - Core data structures."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class OnboardingStatus(Enum):
    """Status of domain onboarding."""
    NOT_STARTED = "not_started"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class RequirementType(Enum):
    """Types of domain requirements."""
    KNOWLEDGE = "knowledge"
    TOOL = "tool"
    PERSONA = "persona"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"


@dataclass
class DomainRequirement:
    """Requirement for domain onboarding."""
    id: UUID = field(default_factory=uuid4)
    req_type: RequirementType = RequirementType.KNOWLEDGE
    name: str = ""
    description: str = ""
    priority: int = 5
    satisfied: bool = False
    artifacts: List[UUID] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "type": self.req_type.value, "name": self.name,
                "description": self.description, "priority": self.priority, "satisfied": self.satisfied}


@dataclass
class OnboardingTask:
    """Task in domain onboarding process."""
    id: UUID = field(default_factory=uuid4)
    domain_id: UUID = field(default_factory=uuid4)
    name: str = ""
    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    requirement_id: Optional[UUID] = None
    progress: float = 0.0
    output: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def complete(self, output: Dict[str, Any]):
        self.status = OnboardingStatus.COMPLETED
        self.progress = 1.0
        self.output = output
        self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "name": self.name, "status": self.status.value,
                "progress": self.progress, "output": self.output}


@dataclass
class DomainProfile:
    """Profile of a domain being onboarded."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    industry: str = ""
    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    requirements: List[DomainRequirement] = field(default_factory=list)
    tasks: List[OnboardingTask] = field(default_factory=list)
    generated_assets: Dict[str, List[UUID]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def add_requirement(self, req: DomainRequirement):
        self.requirements.append(req)
    
    def add_task(self, task: OnboardingTask):
        task.domain_id = self.id
        self.tasks.append(task)
    
    def get_progress(self) -> float:
        if not self.requirements:
            return 0.0
        satisfied = sum(1 for r in self.requirements if r.satisfied)
        return satisfied / len(self.requirements)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "name": self.name, "description": self.description,
                "industry": self.industry, "status": self.status.value,
                "progress": self.get_progress(), "requirements": len(self.requirements),
                "tasks": len(self.tasks)}
