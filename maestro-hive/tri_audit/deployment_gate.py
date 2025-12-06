"""
Deployment Gate API

Provides deployment gate functionality for CI/CD integration:
- Pre-deployment validation
- Gate approval/blocking logic
- Integration with storage for audit history
- Webhook notifications for gate changes (placeholder for MD-2092)

Part of MD-2043: Trimodal Convergence Completion
Tasks: MD-2079 (Deployment Gate API), MD-2080 (Auto-block)

Author: Claude Code Agent
Date: 2025-12-02
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

# Import tri-audit components
try:
    from tri_audit.tri_audit import (
        tri_modal_audit,
        TriModalVerdict,
        TriAuditResult,
        load_dde_audit,
        load_bdv_audit,
        load_acc_audit
    )
except ImportError:
    tri_modal_audit = None
    TriModalVerdict = None
    TriAuditResult = None

# Import storage
try:
    from tri_audit.storage import (
        get_storage,
        save_audit_result,
        get_audit_result,
        query_failures,
        get_audit_statistics
    )
except ImportError:
    get_storage = None
    save_audit_result = None
    get_audit_result = None
    query_failures = None
    get_audit_statistics = None


class GateStatus(str, Enum):
    """Deployment gate status."""
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"
    AUTO_BLOCKED = "AUTO_BLOCKED"  # MD-2080: Auto-block on SYSTEMIC_FAILURE


class BlockReason(str, Enum):
    """Reasons for deployment block."""
    DDE_FAILED = "dde_failed"
    BDV_FAILED = "bdv_failed"
    ACC_FAILED = "acc_failed"
    SYSTEMIC_FAILURE = "systemic_failure"
    MANUAL_BLOCK = "manual_block"
    MISSING_DATA = "missing_data"


class DeploymentRequest(BaseModel):
    """Request to check deployment gate."""
    iteration_id: str = Field(..., description="Iteration identifier")
    project: str = Field(..., description="Project name")
    version: str = Field(..., description="Version to deploy")
    commit_sha: Optional[str] = Field(None, description="Git commit SHA")
    environment: str = Field("production", description="Target environment")
    force_check: bool = Field(False, description="Force re-run audit even if cached")


class DeploymentGateResponse(BaseModel):
    """Response from deployment gate check."""
    iteration_id: str
    timestamp: str
    gate_status: GateStatus
    approved: bool

    # Individual gates
    dde_gate: bool
    bdv_gate: bool
    acc_gate: bool

    # Verdict details
    verdict: Optional[str] = None
    diagnosis: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)

    # Blocking info
    blocking_reasons: List[str] = Field(default_factory=list)
    auto_blocked: bool = False

    # Request context
    project: str
    version: str
    commit_sha: Optional[str] = None
    environment: str = "production"

    # Statistics
    recent_pass_rate: Optional[float] = None


class ManualOverride(BaseModel):
    """Manual override request."""
    iteration_id: str
    action: str = Field(..., description="'approve' or 'block'")
    reason: str = Field(..., description="Reason for override")
    approved_by: str = Field(..., description="Who approved/blocked")
    expires_at: Optional[str] = Field(None, description="When override expires (ISO format)")


class OverrideResponse(BaseModel):
    """Response from manual override."""
    success: bool
    message: str
    override_id: Optional[str] = None


# In-memory override store (would use database in production)
_manual_overrides: Dict[str, Dict[str, Any]] = {}


def check_auto_block(verdict: TriModalVerdict) -> bool:
    """
    Check if verdict triggers auto-block (MD-2080).

    SYSTEMIC_FAILURE triggers automatic blocking.

    Args:
        verdict: TriModalVerdict from audit

    Returns:
        True if should auto-block
    """
    if verdict is None:
        return False
    return verdict == TriModalVerdict.SYSTEMIC_FAILURE


def get_blocking_reasons(
    dde_passed: bool,
    bdv_passed: bool,
    acc_passed: bool,
    verdict: Optional[TriModalVerdict] = None
) -> List[str]:
    """
    Get list of reasons why deployment is blocked.

    Args:
        dde_passed: DDE audit passed
        bdv_passed: BDV audit passed
        acc_passed: ACC audit passed
        verdict: Optional verdict for additional context

    Returns:
        List of blocking reason strings
    """
    reasons = []

    if not dde_passed:
        reasons.append("DDE audit failed - execution/process issues detected")

    if not bdv_passed:
        reasons.append("BDV audit failed - behavior validation not met")

    if not acc_passed:
        reasons.append("ACC audit failed - architectural violations detected")

    if verdict == TriModalVerdict.SYSTEMIC_FAILURE:
        reasons.append("SYSTEMIC FAILURE - all three audits failed, deployment auto-blocked")

    if verdict == TriModalVerdict.DESIGN_GAP:
        reasons.append("Design gap detected - built the wrong thing")

    if verdict == TriModalVerdict.ARCHITECTURAL_EROSION:
        reasons.append("Architectural erosion detected - structural issues need fixing")

    if verdict == TriModalVerdict.PROCESS_ISSUE:
        reasons.append("Process issue detected - pipeline/gate failures")

    return reasons


def check_manual_override(iteration_id: str) -> Optional[Dict[str, Any]]:
    """
    Check for manual override.

    Args:
        iteration_id: Iteration identifier

    Returns:
        Override dict if exists and not expired, None otherwise
    """
    override = _manual_overrides.get(iteration_id)
    if not override:
        return None

    # Check expiration
    expires_at = override.get("expires_at")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.utcnow() > expiry.replace(tzinfo=None):
                # Expired, remove override
                del _manual_overrides[iteration_id]
                return None
        except Exception:
            pass

    return override


def run_deployment_gate_check(request: DeploymentRequest) -> DeploymentGateResponse:
    """
    Run full deployment gate check.

    Args:
        request: DeploymentRequest with iteration details

    Returns:
        DeploymentGateResponse with gate status
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Check for manual override first
    override = check_manual_override(request.iteration_id)
    if override:
        is_approved = override["action"] == "approve"
        return DeploymentGateResponse(
            iteration_id=request.iteration_id,
            timestamp=timestamp,
            gate_status=GateStatus.APPROVED if is_approved else GateStatus.BLOCKED,
            approved=is_approved,
            dde_gate=is_approved,
            bdv_gate=is_approved,
            acc_gate=is_approved,
            verdict="manual_override",
            diagnosis=f"Manual override by {override.get('approved_by', 'unknown')}: {override.get('reason', 'No reason provided')}",
            recommendations=[],
            blocking_reasons=[] if is_approved else [f"Manual block: {override.get('reason')}"],
            auto_blocked=False,
            project=request.project,
            version=request.version,
            commit_sha=request.commit_sha,
            environment=request.environment
        )

    # Try to get cached result first (unless force_check)
    cached_result = None
    if not request.force_check and get_audit_result:
        cached_result = get_audit_result(request.iteration_id)

    # Run or use cached audit
    if cached_result and not request.force_check:
        audit_result = cached_result
    elif tri_modal_audit:
        audit_result = tri_modal_audit(request.iteration_id)
        # Save to storage
        if save_audit_result and audit_result:
            save_audit_result(audit_result)
    else:
        # No audit function available
        return DeploymentGateResponse(
            iteration_id=request.iteration_id,
            timestamp=timestamp,
            gate_status=GateStatus.PENDING,
            approved=False,
            dde_gate=False,
            bdv_gate=False,
            acc_gate=False,
            verdict="unavailable",
            diagnosis="Tri-modal audit system not available",
            recommendations=["Ensure tri_audit module is properly configured"],
            blocking_reasons=["Audit system unavailable"],
            auto_blocked=False,
            project=request.project,
            version=request.version,
            commit_sha=request.commit_sha,
            environment=request.environment
        )

    # Extract results
    dde_passed = audit_result.dde_passed if audit_result else False
    bdv_passed = audit_result.bdv_passed if audit_result else False
    acc_passed = audit_result.acc_passed if audit_result else False
    verdict = audit_result.verdict if audit_result else None

    # Check auto-block (MD-2080)
    auto_blocked = check_auto_block(verdict)

    # Determine gate status
    if audit_result and audit_result.can_deploy and not auto_blocked:
        gate_status = GateStatus.APPROVED
    elif auto_blocked:
        gate_status = GateStatus.AUTO_BLOCKED
    else:
        gate_status = GateStatus.BLOCKED

    # Get blocking reasons
    blocking_reasons = get_blocking_reasons(dde_passed, bdv_passed, acc_passed, verdict)

    # Get recent pass rate for context
    recent_pass_rate = None
    if get_audit_statistics:
        try:
            stats = get_audit_statistics(days=7)
            recent_pass_rate = stats.get("pass_rate")
        except Exception:
            pass

    verdict_value = verdict.value if hasattr(verdict, 'value') else str(verdict) if verdict else None

    return DeploymentGateResponse(
        iteration_id=request.iteration_id,
        timestamp=timestamp,
        gate_status=gate_status,
        approved=(gate_status == GateStatus.APPROVED),
        dde_gate=dde_passed,
        bdv_gate=bdv_passed,
        acc_gate=acc_passed,
        verdict=verdict_value,
        diagnosis=audit_result.diagnosis if audit_result else None,
        recommendations=audit_result.recommendations if audit_result else [],
        blocking_reasons=blocking_reasons,
        auto_blocked=auto_blocked,
        project=request.project,
        version=request.version,
        commit_sha=request.commit_sha,
        environment=request.environment,
        recent_pass_rate=recent_pass_rate
    )


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/v1/deployment-gate", tags=["deployment-gate"])


@router.post("/check", response_model=DeploymentGateResponse)
async def check_deployment_gate(request: DeploymentRequest) -> DeploymentGateResponse:
    """
    Check deployment gate status.

    This is the primary endpoint for CI/CD integration.
    Returns whether deployment is approved, blocked, or pending.

    **Usage in CI/CD:**
    ```bash
    curl -X POST /api/v1/deployment-gate/check \\
      -H "Content-Type: application/json" \\
      -d '{"iteration_id": "iter-123", "project": "myapp", "version": "1.0.0"}'
    ```

    **Response Codes:**
    - 200: Gate check completed (check 'approved' field)
    - 500: Internal error

    **Gate Status Values:**
    - APPROVED: All audits pass, safe to deploy
    - BLOCKED: One or more audits failed
    - AUTO_BLOCKED: SYSTEMIC_FAILURE detected (MD-2080)
    - PENDING: Audit data not yet available
    """
    return run_deployment_gate_check(request)


@router.get("/check/{iteration_id}", response_model=DeploymentGateResponse)
async def check_deployment_gate_simple(
    iteration_id: str,
    project: str = Query(..., description="Project name"),
    version: str = Query(..., description="Version to deploy"),
    commit_sha: Optional[str] = Query(None, description="Git commit SHA"),
    environment: str = Query("production", description="Target environment")
) -> DeploymentGateResponse:
    """
    Simple GET endpoint for deployment gate check.

    Same as POST /check but uses query parameters.

    **Usage:**
    ```bash
    curl "/api/v1/deployment-gate/check/iter-123?project=myapp&version=1.0.0"
    ```
    """
    request = DeploymentRequest(
        iteration_id=iteration_id,
        project=project,
        version=version,
        commit_sha=commit_sha,
        environment=environment
    )
    return run_deployment_gate_check(request)


@router.get("/status/{iteration_id}")
async def get_gate_status(iteration_id: str) -> Dict[str, Any]:
    """
    Get simplified gate status for quick checks.

    Returns just the essential status info.

    **Usage:**
    ```bash
    if curl -s "/api/v1/deployment-gate/status/iter-123" | jq -r '.approved' | grep -q true; then
      echo "Deploy approved"
    fi
    ```
    """
    request = DeploymentRequest(
        iteration_id=iteration_id,
        project="status-check",
        version="0.0.0"
    )
    result = run_deployment_gate_check(request)

    return {
        "iteration_id": iteration_id,
        "approved": result.approved,
        "gate_status": result.gate_status.value,
        "verdict": result.verdict,
        "auto_blocked": result.auto_blocked
    }


@router.post("/override", response_model=OverrideResponse)
async def set_manual_override(override: ManualOverride) -> OverrideResponse:
    """
    Set manual override for deployment gate.

    Allows authorized users to manually approve or block deployments.

    **IMPORTANT:** Manual overrides should be used sparingly and with proper authorization.

    **Example - Approve:**
    ```json
    {
      "iteration_id": "iter-123",
      "action": "approve",
      "reason": "Critical hotfix, BDV tests pending update",
      "approved_by": "john.doe@company.com"
    }
    ```

    **Example - Block:**
    ```json
    {
      "iteration_id": "iter-123",
      "action": "block",
      "reason": "Security review required",
      "approved_by": "security-team"
    }
    ```
    """
    if override.action not in ["approve", "block"]:
        return OverrideResponse(
            success=False,
            message="Invalid action. Must be 'approve' or 'block'"
        )

    override_id = f"override-{override.iteration_id}-{datetime.utcnow().timestamp()}"

    _manual_overrides[override.iteration_id] = {
        "override_id": override_id,
        "action": override.action,
        "reason": override.reason,
        "approved_by": override.approved_by,
        "expires_at": override.expires_at,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    return OverrideResponse(
        success=True,
        message=f"Override set: {override.action} by {override.approved_by}",
        override_id=override_id
    )


@router.delete("/override/{iteration_id}")
async def remove_manual_override(iteration_id: str) -> Dict[str, Any]:
    """
    Remove manual override for iteration.

    Returns the gate to automatic assessment.
    """
    if iteration_id in _manual_overrides:
        del _manual_overrides[iteration_id]
        return {"success": True, "message": f"Override removed for {iteration_id}"}

    return {"success": False, "message": f"No override found for {iteration_id}"}


@router.get("/overrides")
async def list_overrides() -> Dict[str, Any]:
    """
    List all active manual overrides.

    For monitoring and audit purposes.
    """
    return {
        "overrides": _manual_overrides,
        "count": len(_manual_overrides)
    }


@router.get("/statistics")
async def get_gate_statistics(
    days: int = Query(7, description="Number of days to analyze")
) -> Dict[str, Any]:
    """
    Get deployment gate statistics.

    Returns pass rates, failure breakdown, and trends.
    """
    if not get_audit_statistics:
        return {
            "error": "Statistics not available",
            "message": "Storage module not configured"
        }

    stats = get_audit_statistics(days=days)

    return {
        "period_days": days,
        "total_audits": stats.get("total_audits", 0),
        "approved_deployments": stats.get("deployable", 0),
        "blocked_deployments": stats.get("blocked", 0),
        "pass_rate": stats.get("pass_rate", 0.0),
        "verdict_breakdown": stats.get("verdict_breakdown", {}),
        "stream_pass_rates": stats.get("stream_pass_rates", {})
    }


@router.get("/recent-failures")
async def get_recent_failures(
    days: int = Query(7, description="Number of days to look back"),
    limit: int = Query(10, description="Maximum results")
) -> Dict[str, Any]:
    """
    Get recent deployment failures.

    For debugging and trend analysis.
    """
    if not query_failures:
        return {
            "error": "Query not available",
            "message": "Storage module not configured"
        }

    failures = query_failures(days=days, limit=limit)

    return {
        "period_days": days,
        "count": len(failures),
        "failures": [
            {
                "iteration_id": f.iteration_id,
                "timestamp": f.timestamp,
                "verdict": f.verdict.value if hasattr(f.verdict, 'value') else str(f.verdict),
                "dde_passed": f.dde_passed,
                "bdv_passed": f.bdv_passed,
                "acc_passed": f.acc_passed
            }
            for f in failures
        ]
    }


# ============================================================================
# CI/CD Helper Functions
# ============================================================================

def check_can_deploy(iteration_id: str, project: str, version: str) -> bool:
    """
    Simple boolean check for CI/CD scripts.

    Args:
        iteration_id: Iteration identifier
        project: Project name
        version: Version string

    Returns:
        True if deployment is approved
    """
    request = DeploymentRequest(
        iteration_id=iteration_id,
        project=project,
        version=version
    )
    result = run_deployment_gate_check(request)
    return result.approved


def get_blocking_summary(iteration_id: str) -> str:
    """
    Get human-readable blocking summary for notifications.

    Args:
        iteration_id: Iteration identifier

    Returns:
        Summary string
    """
    request = DeploymentRequest(
        iteration_id=iteration_id,
        project="summary",
        version="0.0.0"
    )
    result = run_deployment_gate_check(request)

    if result.approved:
        return f"✅ Deployment APPROVED for {iteration_id}"

    summary = f"❌ Deployment BLOCKED for {iteration_id}\n"
    summary += f"Status: {result.gate_status.value}\n"
    summary += f"Verdict: {result.verdict}\n"

    if result.blocking_reasons:
        summary += "Reasons:\n"
        for reason in result.blocking_reasons:
            summary += f"  - {reason}\n"

    if result.recommendations:
        summary += "Recommendations:\n"
        for rec in result.recommendations:
            summary += f"  - {rec}\n"

    return summary
