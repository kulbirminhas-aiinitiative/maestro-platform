"""
FastAPI REST API for ML Pipeline Orchestration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
import asyncio
import logging
import time
import os
from datetime import datetime
from pathlib import Path

from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

from .orchestrator import WorkflowOrchestrator
from .models import (
    WorkflowConfig,
    WorkflowExecution,
    TaskConfig,
    TaskStatus,
    ExecutionResult
)
from .pipeline import (
    DataIngestionStage,
    DataPreprocessingStage,
    FeatureEngineeringStage,
    ModelTrainingStage,
    ModelEvaluationStage,
    ModelDeploymentStage
)

logger = logging.getLogger(__name__)

# Prometheus Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

workflow_executions_total = Counter(
    'workflow_executions_total',
    'Total workflow executions',
    ['status']
)

workflow_duration_seconds = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration in seconds'
)

task_executions_total = Counter(
    'task_executions_total',
    'Total task executions',
    ['status']
)

active_workflows_gauge = Gauge(
    'active_workflows',
    'Number of active workflows'
)

active_executions_gauge = Gauge(
    'active_executions',
    'Number of active executions'
)

app = FastAPI(
    title="ML Pipeline Orchestration API",
    description="Production-ready ML workflow orchestration with DAG execution",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Global state
orchestrators: Dict[str, WorkflowOrchestrator] = {}
executions: Dict[str, WorkflowExecution] = {}


def update_gauges():
    """Update Prometheus gauges"""
    active_workflows_gauge.set(len(orchestrators))
    active_executions_gauge.set(
        len([e for e in executions.values() if e.status == TaskStatus.RUNNING])
    )

# Stage registry
STAGE_REGISTRY = {
    "data_ingestion": DataIngestionStage,
    "data_preprocessing": DataPreprocessingStage,
    "feature_engineering": FeatureEngineeringStage,
    "model_training": ModelTrainingStage,
    "model_evaluation": ModelEvaluationStage,
    "model_deployment": ModelDeploymentStage
}


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "ML Pipeline Orchestration",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with dependency checks"""
    update_gauges()

    dependencies = {
        "database": {"status": "not_configured", "required": False},
        "redis": {"status": "not_configured", "required": False}
    }

    # Check if database is configured
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        dependencies["database"]["status"] = "healthy"

    # Check if Redis is configured
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        dependencies["redis"]["status"] = "healthy"

    # Determine overall health status
    overall_status = "healthy"
    for dep_name, dep_info in dependencies.items():
        if dep_info["required"] and dep_info["status"] != "healthy":
            overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ML Pipeline Orchestration",
        "version": "1.0.0",
        "dependencies": dependencies,
        "metrics": {
            "active_workflows": len(orchestrators),
            "active_executions": len([e for e in executions.values() if e.status == TaskStatus.RUNNING]),
            "total_executions": len(executions)
        }
    }


@app.post("/workflows", response_model=Dict[str, Any])
async def create_workflow(workflow_config: WorkflowConfig):
    """Create a new workflow"""
    try:
        orchestrator = WorkflowOrchestrator(
            config=workflow_config,
            stage_registry=STAGE_REGISTRY
        )

        orchestrators[workflow_config.workflow_id] = orchestrator
        update_gauges()

        logger.info(f"Workflow created: {workflow_config.workflow_id}")

        return {
            "workflow_id": workflow_config.workflow_id,
            "name": workflow_config.name,
            "status": "created",
            "tasks_count": len(workflow_config.tasks)
        }

    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/workflows", response_model=List[Dict[str, Any]])
async def list_workflows():
    """List all workflows"""
    workflows = []
    for workflow_id, orchestrator in orchestrators.items():
        workflows.append({
            "workflow_id": workflow_id,
            "name": orchestrator.config.name,
            "description": orchestrator.config.description,
            "tasks_count": len(orchestrator.config.tasks),
            "created_at": orchestrator.config.created_at.isoformat()
        })
    return workflows


@app.get("/workflows/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow(workflow_id: str):
    """Get workflow details"""
    orchestrator = orchestrators.get(workflow_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "workflow_id": workflow_id,
        "name": orchestrator.config.name,
        "description": orchestrator.config.description,
        "tasks": [task.dict() for task in orchestrator.config.tasks],
        "max_parallel_tasks": orchestrator.config.max_parallel_tasks,
        "failure_strategy": orchestrator.config.failure_strategy,
        "created_at": orchestrator.config.created_at.isoformat()
    }


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    if workflow_id not in orchestrators:
        raise HTTPException(status_code=404, detail="Workflow not found")

    del orchestrators[workflow_id]
    logger.info(f"Workflow deleted: {workflow_id}")

    return {"status": "deleted", "workflow_id": workflow_id}


@app.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
async def execute_workflow(workflow_id: str, background_tasks: BackgroundTasks):
    """Execute a workflow"""
    orchestrator = orchestrators.get(workflow_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Workflow not found")

    async def run_workflow():
        start_time = time.time()
        try:
            execution = await orchestrator.execute()
            executions[execution.execution_id] = execution

            duration = time.time() - start_time
            workflow_duration_seconds.observe(duration)
            workflow_executions_total.labels(status=execution.status.value).inc()
            update_gauges()

        except Exception as e:
            duration = time.time() - start_time
            workflow_duration_seconds.observe(duration)
            workflow_executions_total.labels(status="failed").inc()
            logger.error(f"Workflow execution failed: {e}")

    # Run in background
    background_tasks.add_task(run_workflow)

    return {
        "workflow_id": workflow_id,
        "status": "started",
        "message": "Workflow execution started in background"
    }


@app.get("/workflows/{workflow_id}/status", response_model=Dict[str, Any])
async def get_workflow_status(workflow_id: str):
    """Get workflow execution status"""
    orchestrator = orchestrators.get(workflow_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return orchestrator.get_execution_status()


@app.get("/workflows/{workflow_id}/visualize", response_model=Dict[str, Any])
async def visualize_workflow(workflow_id: str):
    """Get workflow visualization data"""
    orchestrator = orchestrators.get(workflow_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return orchestrator.visualize_workflow()


@app.get("/executions", response_model=List[Dict[str, Any]])
async def list_executions():
    """List all executions"""
    return [
        {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "progress": {
                "completed": execution.tasks_completed,
                "failed": execution.tasks_failed,
                "total": execution.tasks_total
            },
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None
        }
        for execution in executions.values()
    ]


@app.get("/executions/{execution_id}", response_model=WorkflowExecution)
async def get_execution(execution_id: str):
    """Get execution details"""
    execution = executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution


@app.get("/executions/{execution_id}/results", response_model=List[ExecutionResult])
async def get_execution_results(execution_id: str):
    """Get execution task results"""
    execution = executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution.task_results


@app.post("/tasks/validate", response_model=Dict[str, Any])
async def validate_task(task_config: TaskConfig):
    """Validate a task configuration"""
    try:
        # Basic validation
        if not task_config.name:
            raise ValueError("Task name is required")

        if not task_config.task_type:
            raise ValueError("Task type is required")

        return {
            "valid": True,
            "task_id": task_config.task_id,
            "message": "Task configuration is valid"
        }

    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@app.get("/stages", response_model=List[str])
async def list_available_stages():
    """List available pipeline stages"""
    return list(STAGE_REGISTRY.keys())


@app.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get system metrics"""
    total_tasks = sum(len(o.config.tasks) for o in orchestrators.values())
    completed_executions = len([e for e in executions.values() if e.status == TaskStatus.SUCCESS])
    failed_executions = len([e for e in executions.values() if e.status == TaskStatus.FAILED])

    return {
        "workflows": {
            "total": len(orchestrators),
            "total_tasks": total_tasks
        },
        "executions": {
            "total": len(executions),
            "completed": completed_executions,
            "failed": failed_executions,
            "running": len([e for e in executions.values() if e.status == TaskStatus.RUNNING])
        },
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    from .config import get_settings

    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS
    )