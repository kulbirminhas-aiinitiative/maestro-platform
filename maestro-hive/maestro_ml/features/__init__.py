"""
Features Module

Feast feature store integration for ML feature management.
"""

from .feast_client import FeatureStoreClient
from .materialization import MaterializationJob, MaterializationScheduler

__all__ = [
    "FeatureStoreClient",
    "MaterializationJob",
    "MaterializationScheduler",
]
