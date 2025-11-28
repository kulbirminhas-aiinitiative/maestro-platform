"""
Quality-Fabric Integration Router
Endpoints for automated template quality validation
"""

import httpx
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from ..security import verify_api_key
from ..dependencies import get_db_pool

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])

# Quality-Fabric Configuration
QUALITY_FABRIC_URL = "http://localhost:8080"  # Default, can be overridden via env
QUALITY_FABRIC_TIMEOUT = 300  # 5 minutes for validation


class ValidationRequest(BaseModel):
    """Request to validate a template"""
    template_id: UUID
    validation_type: str = Field("full", pattern="^(quick|full|security|performance)$")
    priority: str = Field("normal", pattern="^(low|normal|high|critical)$")


class ValidationResult(BaseModel):
    """Quality validation result"""
    template_id: UUID
    status: str  # pending, running, completed, failed
    validation_type: str

    # Scores
    quality_score: Optional[float] = None
    security_score: Optional[float] = None
    performance_score: Optional[float] = None
    maintainability_score: Optional[float] = None

    # Results
    passed: Optional[bool] = None
    tests_run: Optional[int] = None
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None

    # Feedback
    issues: list[Dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Metadata
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "validation_type": "full",
                "quality_score": 92.5,
                "security_score": 95.0,
                "performance_score": 88.0,
                "maintainability_score": 90.0,
                "passed": True,
                "tests_run": 25,
                "tests_passed": 24,
                "tests_failed": 1,
                "issues": [
                    {
                        "severity": "warning",
                        "type": "code_smell",
                        "message": "Complex function detected",
                        "file": "main.py",
                        "line": 42
                    }
                ],
                "recommendations": [
                    "Consider breaking down complex functions",
                    "Add more comprehensive error handling"
                ],
                "started_at": "2025-10-01T09:00:00Z",
                "completed_at": "2025-10-01T09:05:30Z",
                "duration_seconds": 330.5
            }
        }


@router.post("/validate", response_model=ValidationResult)
async def validate_template(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    db_pool = Depends(get_db_pool)
):
    """
    Trigger Quality-Fabric validation for a template

    This endpoint initiates an asynchronous validation process:
    1. Retrieves template code and metadata
    2. Submits to Quality-Fabric for testing
    3. Returns validation job ID
    4. Continues validation in background
    5. Updates database when complete

    **Validation Types:**
    - `quick`: Basic syntax and structure checks (~30s)
    - `full`: Comprehensive testing including unit tests (~5min)
    - `security`: Security vulnerability scanning (~2min)
    - `performance`: Performance and load testing (~10min)

    **Returns:**
    - Validation job with initial status
    - Use GET /quality/validation/{template_id} to check status
    """
    try:
        template_id = request.template_id

        # Get template from database
        if not db_pool:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )

        async with db_pool.acquire() as conn:
            template = await conn.fetchrow("""
                SELECT id, name, language, category, git_url, cache_path,
                       quality_score, security_score, performance_score
                FROM templates
                WHERE id = $1
            """, template_id)

            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template {template_id} not found"
                )

            # Create validation record
            validation_id = await conn.fetchval("""
                INSERT INTO template_validations (
                    template_id, validation_type, status, priority, started_at
                )
                VALUES ($1, $2, 'pending', $3, NOW())
                RETURNING id
            """, template_id, request.validation_type, request.priority)

            logger.info(
                "validation_initiated",
                template_id=str(template_id),
                validation_id=validation_id,
                type=request.validation_type
            )

        # Schedule background validation
        background_tasks.add_task(
            run_quality_fabric_validation,
            template_id,
            validation_id,
            request.validation_type,
            dict(template),
            db_pool
        )

        return ValidationResult(
            template_id=template_id,
            status="pending",
            validation_type=request.validation_type,
            started_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("validation_request_error", error=str(e), template_id=str(request.template_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate validation: {str(e)}"
        )


@router.get("/validation/{template_id}", response_model=ValidationResult)
async def get_validation_status(
    template_id: UUID,
    api_key: str = Depends(verify_api_key),
    db_pool = Depends(get_db_pool)
):
    """
    Get the latest validation status for a template

    Returns the most recent validation result, including:
    - Current status (pending, running, completed, failed)
    - Quality scores (if completed)
    - Issues found and recommendations
    - Execution metadata
    """
    try:
        if not db_pool:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )

        async with db_pool.acquire() as conn:
            validation = await conn.fetchrow("""
                SELECT
                    template_id, validation_type, status, priority,
                    quality_score, security_score, performance_score, maintainability_score,
                    passed, tests_run, tests_passed, tests_failed,
                    issues, recommendations,
                    started_at, completed_at,
                    EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
                FROM template_validations
                WHERE template_id = $1
                ORDER BY started_at DESC
                LIMIT 1
            """, template_id)

            if not validation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No validation found for template {template_id}"
                )

            return ValidationResult(**dict(validation))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("validation_status_error", error=str(e), template_id=str(template_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation status: {str(e)}"
        )


@router.post("/webhook/result")
async def quality_fabric_webhook(
    result: ValidationResult,
    db_pool = Depends(get_db_pool)
):
    """
    Webhook endpoint for Quality-Fabric to POST results

    This endpoint receives validation results from Quality-Fabric
    and updates the template quality scores in the database.

    **Authentication:** Uses Quality-Fabric webhook secret (TODO: implement)
    """
    try:
        template_id = result.template_id

        if not db_pool:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )

        async with db_pool.acquire() as conn:
            # Update validation record
            await conn.execute("""
                UPDATE template_validations
                SET
                    status = $2,
                    quality_score = $3,
                    security_score = $4,
                    performance_score = $5,
                    maintainability_score = $6,
                    passed = $7,
                    tests_run = $8,
                    tests_passed = $9,
                    tests_failed = $10,
                    issues = $11,
                    recommendations = $12,
                    completed_at = NOW()
                WHERE template_id = $1
                  AND status IN ('pending', 'running')
            """,
                template_id, result.status,
                result.quality_score, result.security_score,
                result.performance_score, result.maintainability_score,
                result.passed, result.tests_run, result.tests_passed, result.tests_failed,
                result.issues, result.recommendations
            )

            # Update template scores if validation passed
            if result.passed and result.quality_score:
                await conn.execute("""
                    UPDATE templates
                    SET
                        quality_score = $2,
                        security_score = $3,
                        performance_score = $4,
                        maintainability_score = $5,
                        updated_at = NOW()
                    WHERE id = $1
                """,
                    template_id,
                    result.quality_score,
                    result.security_score or 0,
                    result.performance_score or 0,
                    result.maintainability_score or 0
                )

                logger.info(
                    "template_scores_updated",
                    template_id=str(template_id),
                    quality_score=result.quality_score,
                    passed=result.passed
                )

        return {"status": "success", "message": "Validation result processed"}

    except Exception as e:
        logger.error("webhook_error", error=str(e), template_id=str(result.template_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


async def run_quality_fabric_validation(
    template_id: UUID,
    validation_id: int,
    validation_type: str,
    template_data: dict,
    db_pool
):
    """
    Background task to run Quality-Fabric validation

    This function:
    1. Prepares template code for validation
    2. Calls Quality-Fabric API
    3. Polls for completion
    4. Updates database with results
    """
    try:
        logger.info("starting_quality_fabric_validation", template_id=str(template_id))

        # Update status to running
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE template_validations
                SET status = 'running'
                WHERE id = $1
            """, validation_id)

        # Prepare validation request for Quality-Fabric
        validation_request = {
            "project_id": str(template_id),
            "project_name": template_data.get("name"),
            "language": template_data.get("language"),
            "validation_type": validation_type,
            "code_location": template_data.get("cache_path") or template_data.get("git_url"),
        }

        # Call Quality-Fabric API
        async with httpx.AsyncClient(timeout=QUALITY_FABRIC_TIMEOUT) as client:
            try:
                response = await client.post(
                    f"{QUALITY_FABRIC_URL}/api/v1/validate",
                    json=validation_request
                )
                response.raise_for_status()
                result = response.json()

                # Process results
                validation_result = ValidationResult(
                    template_id=template_id,
                    status="completed",
                    validation_type=validation_type,
                    quality_score=result.get("quality_score"),
                    security_score=result.get("security_score"),
                    performance_score=result.get("performance_score"),
                    maintainability_score=result.get("maintainability_score"),
                    passed=result.get("passed", False),
                    tests_run=result.get("tests_run", 0),
                    tests_passed=result.get("tests_passed", 0),
                    tests_failed=result.get("tests_failed", 0),
                    issues=result.get("issues", []),
                    recommendations=result.get("recommendations", []),
                    completed_at=datetime.utcnow()
                )

                # Update database via webhook (reuse logic)
                await quality_fabric_webhook(validation_result, db_pool)

                logger.info(
                    "validation_completed",
                    template_id=str(template_id),
                    passed=validation_result.passed,
                    quality_score=validation_result.quality_score
                )

            except httpx.HTTPError as e:
                # Quality-Fabric API error
                logger.error("quality_fabric_api_error", error=str(e), template_id=str(template_id))
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE template_validations
                        SET status = 'failed', completed_at = NOW()
                        WHERE id = $1
                    """, validation_id)

    except Exception as e:
        logger.error("validation_task_error", error=str(e), template_id=str(template_id))
        # Mark validation as failed
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE template_validations
                    SET status = 'failed', completed_at = NOW()
                    WHERE id = $1
                """, validation_id)
        except:
            pass
