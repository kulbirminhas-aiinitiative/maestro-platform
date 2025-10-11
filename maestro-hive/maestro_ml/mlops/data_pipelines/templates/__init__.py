"""Pipeline Templates"""

from .ingestion import create_ingestion_pipeline
from .training import create_training_pipeline

__all__ = [
    "create_ingestion_pipeline",
    "create_training_pipeline",
]
