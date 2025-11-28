"""
Quality Fabric - Continuous Auto-Repair Service (CARS)
Autonomous error detection, analysis, and healing system
"""

from .error_monitor import ErrorMonitor, ErrorType, ErrorEvent
from .repair_orchestrator import RepairOrchestrator, RepairConfig, RepairResult
from .validation_engine import ValidationEngine, ValidationResult
from .notification_service import NotificationService, NotificationChannel

__all__ = [
    'ErrorMonitor',
    'ErrorType',
    'ErrorEvent',
    'RepairOrchestrator',
    'RepairConfig',
    'RepairResult',
    'ValidationEngine',
    'ValidationResult',
    'NotificationService',
    'NotificationChannel'
]

__version__ = '1.0.0'