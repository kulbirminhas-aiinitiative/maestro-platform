"""
Maestro Platform - Autonomous Test Healing System
Revolutionary self-healing tests that automatically detect and fix failures
"""

from .autonomous_test_healer import (
    AutonomousTestHealer,
    HealingStrategy,
    HealingResult,
    TestFailure,
    FailurePattern
)

__all__ = [
    'AutonomousTestHealer',
    'HealingStrategy',
    'HealingResult',
    'TestFailure',
    'FailurePattern'
]

__version__ = '1.0.0'
