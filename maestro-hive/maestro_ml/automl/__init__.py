"""
AutoML Module

Automated machine learning with model selection, hyperparameter optimization,
and ensemble generation.
"""

from .engines.automl_engine import AutoMLEngine
from .models.result_models import (
    AutoMLConfig,
    AutoMLResult,
    SearchSpace,
    TaskType,
    TrialResult,
)

__all__ = [
    "AutoMLEngine",
    "AutoMLConfig",
    "AutoMLResult",
    "SearchSpace",
    "TaskType",
    "TrialResult",
]
