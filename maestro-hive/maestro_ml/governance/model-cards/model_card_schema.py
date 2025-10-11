"""
Model Card Schema - Following Google's Model Cards standard
https://arxiv.org/abs/1810.03993
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class ModelType(str, Enum):
    """Types of ML models"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RANKING = "ranking"
    GENERATION = "generation"
    OTHER = "other"


class ModelDetails(BaseModel):
    """High-level information about the model"""
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    model_type: ModelType = Field(..., description="Type of ML model")
    date: datetime = Field(default_factory=datetime.now, description="Model creation date")
    owners: List[str] = Field(default_factory=list, description="Model owners/maintainers")
    license: Optional[str] = Field(None, description="Model license")
    references: List[str] = Field(default_factory=list, description="Papers, docs, repos")
    citation: Optional[str] = Field(None, description="How to cite this model")
    framework: Optional[str] = Field(None, description="ML framework (pytorch, tensorflow, etc)")
    algorithm: Optional[str] = Field(None, description="Algorithm used (RandomForest, BERT, etc)")


class IntendedUse(BaseModel):
    """Intended use cases and users"""
    primary_uses: List[str] = Field(default_factory=list, description="Primary intended uses")
    primary_users: List[str] = Field(default_factory=list, description="Primary intended users")
    out_of_scope: List[str] = Field(default_factory=list, description="Out-of-scope uses")


class Factor(BaseModel):
    """Factors that may affect model performance"""
    groups: List[str] = Field(default_factory=list, description="Evaluation groups")
    instrumentation: Optional[str] = Field(None, description="Measurement instruments")
    environment: Optional[str] = Field(None, description="Evaluation environment")


class Metric(BaseModel):
    """Performance metric"""
    name: str
    value: float
    threshold: Optional[float] = None
    slice: Optional[str] = None  # Data slice this metric applies to


class PerformanceMetrics(BaseModel):
    """Model performance metrics"""
    model_performance: List[Metric] = Field(default_factory=list)
    decision_thresholds: Optional[Dict[str, float]] = None
    approaches_to_uncertainty: Optional[str] = None


class TrainingData(BaseModel):
    """Information about training data"""
    dataset_name: Optional[str] = None
    dataset_version: Optional[str] = None
    data_sources: List[str] = Field(default_factory=list)
    preprocessing: List[str] = Field(default_factory=list, description="Preprocessing steps")
    num_samples: Optional[int] = None
    features: List[str] = Field(default_factory=list)
    date_range: Optional[str] = None


class EvaluationData(BaseModel):
    """Information about evaluation data"""
    dataset_name: Optional[str] = None
    num_samples: Optional[int] = None
    motivation: Optional[str] = None
    preprocessing: List[str] = Field(default_factory=list)


class EthicalConsiderations(BaseModel):
    """Ethical considerations"""
    sensitive_data: List[str] = Field(default_factory=list, description="Types of sensitive data")
    human_life_impact: Optional[str] = None
    mitigations: List[str] = Field(default_factory=list)
    risks_and_harms: List[str] = Field(default_factory=list)
    use_cases_to_avoid: List[str] = Field(default_factory=list)


class CaveatsAndRecommendations(BaseModel):
    """Caveats and recommendations for model use"""
    caveats: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    ideal_characteristics: List[str] = Field(default_factory=list)


class ModelCard(BaseModel):
    """
    Complete Model Card following Google's standard

    Automatically generated from MLflow metadata + manual annotations
    """

    # Core sections (following Google's Model Card standard)
    model_details: ModelDetails
    intended_use: IntendedUse = Field(default_factory=IntendedUse)
    factors: Factor = Field(default_factory=Factor)
    metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    training_data: TrainingData = Field(default_factory=TrainingData)
    evaluation_data: EvaluationData = Field(default_factory=EvaluationData)
    ethical_considerations: EthicalConsiderations = Field(default_factory=EthicalConsiderations)
    caveats_and_recommendations: CaveatsAndRecommendations = Field(default_factory=CaveatsAndRecommendations)

    # Maestro ML specific metadata
    mlflow_run_id: Optional[str] = None
    mlflow_model_uri: Optional[str] = None
    deployment_status: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "model_details": {
                    "name": "fraud-detector",
                    "version": "v3.0.0",
                    "model_type": "classification",
                    "framework": "pytorch",
                    "algorithm": "XGBoost",
                    "owners": ["data-science-team@company.com"],
                },
                "intended_use": {
                    "primary_uses": ["Detect fraudulent transactions in real-time"],
                    "primary_users": ["Fraud analysts", "Risk management team"],
                    "out_of_scope": ["Credit scoring", "Customer profiling"]
                },
                "metrics": {
                    "model_performance": [
                        {"name": "precision", "value": 0.95},
                        {"name": "recall", "value": 0.87},
                        {"name": "f1_score", "value": 0.91}
                    ]
                }
            }
        }
