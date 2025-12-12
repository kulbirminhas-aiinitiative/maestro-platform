#!/usr/bin/env python3
"""
Centralized SDLC Phase Configuration

Single source of truth for phase names across the platform.
Addresses Gap G-004 from DESIGN_REVIEW_PHASED_EXECUTION.md.

Usage:
    from maestro_hive.config.phases import SDLC_PHASES, normalize_phase_name
"""

from typing import List, Optional

# Standard SDLC phases (canonical names)
SDLC_PHASES: List[str] = [
    "requirements",
    "design",
    "implementation",
    "testing",
    "deployment"
]

# Aliases for backward compatibility
PHASE_ALIASES = {
    # Legacy names from resume_failed_workflow.py
    "backend_development": "implementation",
    "frontend_development": "implementation",
    "review": "testing",
    # Common alternatives
    "coding": "implementation",
    "development": "implementation",
    "qa": "testing",
    "verification": "testing",
    "deploy": "deployment",
    "release": "deployment",
    "analysis": "requirements",
    "specification": "requirements",
    "architecture": "design",
}


def normalize_phase_name(phase: str) -> str:
    """
    Normalize a phase name to its canonical form.

    Args:
        phase: Phase name (may be alias)

    Returns:
        Canonical phase name

    Raises:
        ValueError: If phase is unknown
    """
    phase_lower = phase.lower().strip()

    # Check if already canonical
    if phase_lower in SDLC_PHASES:
        return phase_lower

    # Check aliases
    if phase_lower in PHASE_ALIASES:
        return PHASE_ALIASES[phase_lower]

    raise ValueError(f"Unknown phase: '{phase}'. Valid phases: {SDLC_PHASES}")


def get_next_phase(current_phase: str) -> Optional[str]:
    """
    Get the phase that follows the current one.

    Args:
        current_phase: Current phase name

    Returns:
        Next phase name, or None if current is last phase
    """
    normalized = normalize_phase_name(current_phase)
    idx = SDLC_PHASES.index(normalized)

    if idx < len(SDLC_PHASES) - 1:
        return SDLC_PHASES[idx + 1]
    return None


def get_previous_phase(current_phase: str) -> Optional[str]:
    """
    Get the phase that precedes the current one.

    Args:
        current_phase: Current phase name

    Returns:
        Previous phase name, or None if current is first phase
    """
    normalized = normalize_phase_name(current_phase)
    idx = SDLC_PHASES.index(normalized)

    if idx > 0:
        return SDLC_PHASES[idx - 1]
    return None


def validate_phase_sequence(phases: List[str]) -> bool:
    """
    Validate that phases are in correct order.

    Args:
        phases: List of phase names

    Returns:
        True if valid sequence
    """
    if not phases:
        return True

    normalized = [normalize_phase_name(p) for p in phases]
    indices = [SDLC_PHASES.index(p) for p in normalized]

    return indices == sorted(indices)


# Re-export for convenience
__all__ = [
    "SDLC_PHASES",
    "PHASE_ALIASES",
    "normalize_phase_name",
    "get_next_phase",
    "get_previous_phase",
    "validate_phase_sequence"
]
