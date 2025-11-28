#!/usr/bin/env python3
"""
Quality Fabric - Automation Service API Endpoints
API endpoints for Continuous Auto-Repair Service (CARS)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging

from .repair_orchestrator import RepairOrchestrator, RepairConfig
from .error_monitor import ErrorType, ErrorSeverity

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/automation", tags=["automation"])

# Global orchestrator instances
active_orchestrators: Dict[str, RepairOrchestrator] = {}


# ========================================================================
# Request/Response Models
# ========================================================================

class StartAutomationRequest(BaseModel):
    """Request to start automation service"""
    project_path: str
    auto_fix: bool = True
    require_approval: bool = False
    confidence_threshold: float = 0.75
    auto_commit: bool = False
    create_pr: bool = False
    max_concurrent_repairs: int = 3


class AutomationStatusResponse(BaseModel):
    """Automation service status"""
    orchestrator_id: str
    is_running: bool
    project_path: str
    active_repairs: int
    queue_size: int
    statistics: Dict[str, Any]
    config: Dict[str, Any]


class RepairHistoryResponse(BaseModel):
    """Repair history"""
    repairs: List[Dict[str, Any]]
    total_count: int


class ManualHealRequest(BaseModel):
    """Manual heal request"""
    error_type: str
    file_path: str
    error_details: Dict[str, Any]


# ========================================================================
# API Endpoints
# ========================================================================

@router.post("/start", summary="Start Continuous Auto-Repair Service")
async def start_automation(
    request: StartAutomationRequest,
    background_tasks: BackgroundTasks
):
    """Start continuous error detection and auto-repair"""
    try:
        # Create repair config
        config = RepairConfig(
            project_path=request.project_path,
            auto_fix=request.auto_fix,
            require_approval=request.require_approval,
            confidence_threshold=request.confidence_threshold,
            auto_commit=request.auto_commit,
            create_pr=request.create_pr,
            max_concurrent_repairs=request.max_concurrent_repairs
        )

        # Create orchestrator
        orchestrator = RepairOrchestrator(config)

        # Store orchestrator
        active_orchestrators[orchestrator.orchestrator_id] = orchestrator

        # Start in background
        background_tasks.add_task(orchestrator.start)

        logger.info(f"Started CARS for: {request.project_path}")

        return {
            "success": True,
            "orchestrator_id": orchestrator.orchestrator_id,
            "message": "Continuous Auto-Repair Service started",
            "config": {
                "project_path": request.project_path,
                "auto_fix": request.auto_fix,
                "confidence_threshold": request.confidence_threshold
            }
        }

    except Exception as e:
        logger.error(f"Failed to start automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", summary="Stop Continuous Auto-Repair Service")
async def stop_automation(orchestrator_id: Optional[str] = None):
    """Stop continuous auto-repair"""
    try:
        if orchestrator_id:
            # Stop specific orchestrator
            if orchestrator_id in active_orchestrators:
                orchestrator = active_orchestrators[orchestrator_id]
                await orchestrator.stop()
                del active_orchestrators[orchestrator_id]

                return {
                    "success": True,
                    "message": f"Stopped orchestrator: {orchestrator_id}"
                }
            else:
                raise HTTPException(status_code=404, detail="Orchestrator not found")
        else:
            # Stop all orchestrators
            for orch_id, orchestrator in list(active_orchestrators.items()):
                await orchestrator.stop()
                del active_orchestrators[orch_id]

            return {
                "success": True,
                "message": f"Stopped all orchestrators ({len(active_orchestrators)} total)"
            }

    except Exception as e:
        logger.error(f"Failed to stop automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=AutomationStatusResponse, summary="Get Automation Status")
async def get_automation_status(orchestrator_id: Optional[str] = None):
    """Get status of automation service"""
    try:
        if orchestrator_id:
            # Get specific orchestrator status
            if orchestrator_id in active_orchestrators:
                orchestrator = active_orchestrators[orchestrator_id]
                return orchestrator.get_status()
            else:
                raise HTTPException(status_code=404, detail="Orchestrator not found")
        else:
            # Get all orchestrators status
            if not active_orchestrators:
                raise HTTPException(status_code=404, detail="No active orchestrators")

            # Return first orchestrator (or could return list)
            orchestrator = list(active_orchestrators.values())[0]
            return orchestrator.get_status()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=RepairHistoryResponse, summary="Get Repair History")
async def get_repair_history(
    orchestrator_id: Optional[str] = None,
    limit: int = 50
):
    """Get repair history"""
    try:
        if orchestrator_id:
            if orchestrator_id in active_orchestrators:
                orchestrator = active_orchestrators[orchestrator_id]
                repairs = orchestrator.get_repair_history(limit)

                return {
                    "repairs": repairs,
                    "total_count": len(repairs)
                }
            else:
                raise HTTPException(status_code=404, detail="Orchestrator not found")
        else:
            # Aggregate from all orchestrators
            all_repairs = []
            for orchestrator in active_orchestrators.values():
                all_repairs.extend(orchestrator.get_repair_history(limit))

            # Sort by timestamp (most recent first)
            all_repairs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return {
                "repairs": all_repairs[:limit],
                "total_count": len(all_repairs)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", summary="Get Repair Statistics")
async def get_statistics(orchestrator_id: Optional[str] = None):
    """Get repair statistics"""
    try:
        if orchestrator_id:
            if orchestrator_id in active_orchestrators:
                orchestrator = active_orchestrators[orchestrator_id]
                return orchestrator.get_statistics()
            else:
                raise HTTPException(status_code=404, detail="Orchestrator not found")
        else:
            # Aggregate statistics from all orchestrators
            total_stats = {
                "total_errors_detected": 0,
                "total_repairs_attempted": 0,
                "successful_repairs": 0,
                "failed_repairs": 0,
                "skipped_repairs": 0
            }

            for orchestrator in active_orchestrators.values():
                stats = orchestrator.get_statistics()
                for key in total_stats:
                    if key in stats:
                        total_stats[key] += stats[key]

            total = total_stats["total_repairs_attempted"]
            success_rate = (total_stats["successful_repairs"] / total * 100) if total > 0 else 0
            total_stats["success_rate"] = f"{success_rate:.1f}%"

            return total_stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heal", summary="Manual Heal Request")
async def manual_heal(request: ManualHealRequest):
    """Manually trigger healing for a specific error"""
    try:
        # Find orchestrator for the file's project
        # For now, use first active orchestrator
        if not active_orchestrators:
            raise HTTPException(
                status_code=400,
                detail="No active orchestrators. Start automation service first."
            )

        orchestrator = list(active_orchestrators.values())[0]

        # Create error event
        from .error_monitor import ErrorEvent
        from datetime import datetime
        import uuid

        error = ErrorEvent(
            error_id=str(uuid.uuid4()),
            error_type=ErrorType(request.error_type),
            severity=ErrorSeverity.HIGH,
            file_path=request.file_path,
            line_number=request.error_details.get('line_number'),
            error_message=request.error_details.get('error_message', ''),
            stack_trace=request.error_details.get('stack_trace'),
            context=request.error_details,
            timestamp=datetime.now().isoformat(),
            healable=True,
            confidence=0.8
        )

        # Add to repair queue
        await orchestrator.repair_queue.put(error)

        return {
            "success": True,
            "message": "Heal request queued",
            "error_id": error.error_id,
            "queue_position": orchestrator.repair_queue.qsize()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid error_type: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue heal request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-orchestrators", summary="List Active Orchestrators")
async def list_orchestrators():
    """List all active orchestrators"""
    orchestrators = []

    for orch_id, orchestrator in active_orchestrators.items():
        status = orchestrator.get_status()
        orchestrators.append({
            "orchestrator_id": orch_id,
            "project_path": status["project_path"],
            "is_running": status["is_running"],
            "active_repairs": status["active_repairs"],
            "statistics": status["statistics"]
        })

    return {
        "count": len(orchestrators),
        "orchestrators": orchestrators
    }


# ========================================================================
# Health Check
# ========================================================================

@router.get("/health", summary="Automation Service Health Check")
async def health_check():
    """Health check for automation service"""
    return {
        "status": "healthy",
        "service": "Continuous Auto-Repair Service (CARS)",
        "version": "1.0.0",
        "active_orchestrators": len(active_orchestrators)
    }