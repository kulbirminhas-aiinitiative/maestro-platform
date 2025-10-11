"""
Model Explainability Module

Interpret and explain ML model predictions using SHAP, LIME, and other techniques.
"""

from .explainers.feature_importance import FeatureImportanceAnalyzer
from .explainers.lime_explainer import LIMEExplainer
from .explainers.shap_explainer import SHAPExplainer
from .models.explanation_models import (
    CounterfactualExplanation,
    Explanation,
    ExplanationType,
    FeatureImportance,
    GlobalExplanation,
    LocalExplanation,
)

__all__ = [
    "Explanation",
    "ExplanationType",
    "FeatureImportance",
    "LocalExplanation",
    "GlobalExplanation",
    "CounterfactualExplanation",
    "SHAPExplainer",
    "LIMEExplainer",
    "FeatureImportanceAnalyzer",
]
