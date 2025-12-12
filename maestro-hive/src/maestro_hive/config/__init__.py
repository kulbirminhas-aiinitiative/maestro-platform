"""Maestro Hive Configuration Module"""
from .phases import (
    SDLC_PHASES,
    PHASE_ALIASES,
    normalize_phase_name,
    get_next_phase,
    get_previous_phase,
    validate_phase_sequence
)

__all__ = [
    "SDLC_PHASES",
    "PHASE_ALIASES",
    "normalize_phase_name",
    "get_next_phase",
    "get_previous_phase",
    "validate_phase_sequence"
]
