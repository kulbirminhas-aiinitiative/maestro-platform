"""
ML Model Cards Generator for Maestro ML Platform

Auto-generates model documentation following Google's Model Cards standard
with automatic extraction from MLflow metadata.

Quick Start:
    >>> from governance.model_cards import ModelCardGenerator
    >>> generator = ModelCardGenerator(mlflow_uri="http://localhost:5000")
    >>> card = generator.generate_from_mlflow("fraud-detector", "3")
    >>> generator.save_markdown(card, "fraud-detector-v3.md")
    >>> generator.save_pdf(card, "fraud-detector-v3.pdf")

CLI Usage:
    $ python -m governance.model_cards.cli generate fraud-detector 3
    $ python -m governance.model_cards.cli generate fraud-detector 3 --format pdf
    $ python -m governance.model_cards.cli list
"""

from .card_generator import ModelCardGenerator
from .model_card_schema import (
    ModelCard,
    ModelDetails,
    IntendedUse,
    PerformanceMetrics,
    TrainingData,
    EvaluationData,
    EthicalConsiderations,
    CaveatsAndRecommendations,
    Factor,
    Metric,
    ModelType,
)

__version__ = "1.0.0"
__author__ = "Maestro ML Platform Team"

__all__ = [
    "ModelCardGenerator",
    "ModelCard",
    "ModelDetails",
    "IntendedUse",
    "PerformanceMetrics",
    "TrainingData",
    "EvaluationData",
    "EthicalConsiderations",
    "CaveatsAndRecommendations",
    "Factor",
    "Metric",
    "ModelType",
]
