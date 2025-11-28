"""
Data models for ML pipeline orchestration
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


class TaskStatus(str, Enum):
    """Enumeration of possible task statuses"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Priority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceRequirements(BaseModel):
    """Resource requirements for task execution"""
    cpu_cores: float = Field(default=1.0, gt=0)
    memory_mb: int = Field(default=512, gt=0)
    gpu_count: int = Field(default=0, ge=0)
    disk_mb: int = Field(default=1024, gt=0)
    timeout_seconds: int = Field(default=3600, gt=0)


class TaskConfig(BaseModel):
    """Configuration for a single task"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    task_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    retry_policy: Dict[str, Any] = Field(default_factory=lambda: {
        "max_retries": 3,
        "retry_delay": 60,
        "exponential_backoff": True
    })
    priority: Priority = Priority.MEDIUM
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Result of task execution"""
    task_id: str
    status: TaskStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    retry_count: int = 0
    resource_usage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('duration_seconds', always=True)
    def calculate_duration(cls, v, values):
        if 'start_time' in values and 'end_time' in values and values['end_time']:
            return (values['end_time'] - values['start_time']).total_seconds()
        return v


class WorkflowConfig(BaseModel):
    """Configuration for entire workflow"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    tasks: List[TaskConfig]
    schedule: Optional[str] = None  # Cron expression
    max_parallel_tasks: int = Field(default=10, gt=0)
    failure_strategy: str = Field(default="fail_fast")  # fail_fast, continue, retry_all
    notification_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('failure_strategy')
    def validate_failure_strategy(cls, v):
        allowed = ['fail_fast', 'continue', 'retry_all']
        if v not in allowed:
            raise ValueError(f"failure_strategy must be one of {allowed}")
        return v


class WorkflowExecution(BaseModel):
    """Workflow execution state"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: TaskStatus
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_total: int
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    task_results: List[ExecutionResult] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MLModelMetadata(BaseModel):
    """Metadata for ML models in pipeline"""
    model_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str
    model_version: str
    framework: str  # tensorflow, pytorch, scikit-learn, etc.
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    metrics: Dict[str, float] = Field(default_factory=dict)
    artifacts_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DatasetMetadata(BaseModel):
    """Metadata for datasets in pipeline"""
    dataset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str
    path: str
    format: str  # csv, parquet, json, etc.
    schema: Dict[str, Any]
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)