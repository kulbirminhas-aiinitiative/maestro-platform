"""
Model Explainability Data Models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExplanationType(str, Enum):
    """Type of explanation"""

    SHAP = "shap"
    LIME = "lime"
    FEATURE_IMPORTANCE = "feature_importance"
    PARTIAL_DEPENDENCE = "partial_dependence"
    COUNTERFACTUAL = "counterfactual"
    ANCHOR = "anchor"


class ModelType(str, Enum):
    """Supported model types"""

    TREE_BASED = "tree_based"  # XGBoost, LightGBM, RandomForest
    LINEAR = "linear"  # Linear/Logistic Regression
    NEURAL_NETWORK = "neural_network"  # Deep learning
    SVM = "svm"
    ENSEMBLE = "ensemble"
    BLACK_BOX = "black_box"  # Any model


class FeatureImportance(BaseModel):
    """Feature importance score"""

    feature_name: str
    importance: float
    rank: int
    std: Optional[float] = None  # Standard deviation across samples
    confidence_interval: Optional[tuple[float, float]] = None


class LocalExplanation(BaseModel):
    """
    Local explanation for a single prediction

    Explains why the model made a specific prediction for one instance.
    """

    instance_id: Optional[str] = None
    prediction: float
    expected_value: Optional[float] = None  # Baseline/average prediction

    # Feature contributions
    feature_contributions: dict[str, float] = Field(
        default_factory=dict,
        description="How much each feature contributed to this prediction",
    )

    # Feature values for this instance
    feature_values: dict[str, Any] = Field(default_factory=dict)

    # Top contributing features
    top_positive_features: list[tuple[str, float]] = Field(
        default_factory=list, description="Features that increased the prediction"
    )
    top_negative_features: list[tuple[str, float]] = Field(
        default_factory=list, description="Features that decreased the prediction"
    )

    # Explanation metadata
    explanation_type: ExplanationType
    model_type: Optional[ModelType] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GlobalExplanation(BaseModel):
    """
    Global explanation for the entire model

    Explains overall model behavior across all predictions.
    """

    # Feature importance across all predictions
    feature_importances: list[FeatureImportance]

    # Summary statistics
    num_instances: int
    prediction_mean: float
    prediction_std: float

    # Interactions (if available)
    feature_interactions: Optional[dict[str, float]] = Field(
        None, description="Interaction effects between features"
    )

    # Explanation metadata
    explanation_type: ExplanationType
    model_type: Optional[ModelType] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CounterfactualExplanation(BaseModel):
    """
    Counterfactual explanation

    'What would need to change to get a different prediction?'
    """

    instance_id: Optional[str] = None
    original_prediction: float
    desired_prediction: float

    # Original feature values
    original_features: dict[str, Any]

    # Counterfactual feature values
    counterfactual_features: dict[str, Any]

    # Changes required
    changes: dict[str, tuple[Any, Any]] = Field(
        default_factory=dict, description="feature_name -> (original_value, new_value)"
    )

    # Cost/feasibility of changes
    change_cost: Optional[float] = None
    is_feasible: bool = True

    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Explanation(BaseModel):
    """
    Unified explanation container

    Can contain local, global, or counterfactual explanations.
    """

    explanation_id: str
    model_name: str
    model_version: str

    # Explanation content (one of these will be set)
    local_explanation: Optional[LocalExplanation] = None
    global_explanation: Optional[GlobalExplanation] = None
    counterfactual_explanation: Optional[CounterfactualExplanation] = None

    # Metadata
    explanation_type: ExplanationType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")

    # Additional context
    dataset_name: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SHAPValues(BaseModel):
    """SHAP values for a prediction"""

    base_value: float  # Expected value (average prediction)
    shap_values: dict[str, float]  # Feature -> SHAP value
    feature_values: dict[str, Any]  # Feature -> actual value
    prediction: float


class LIMEExplanation(BaseModel):
    """LIME explanation result"""

    intercept: float
    coefficients: dict[str, float]  # Feature -> coefficient in local linear model
    score: float  # R² score of local linear model
    local_prediction: float
    prediction_proba: Optional[list[float]] = None  # For classification


class PartialDependencePlot(BaseModel):
    """Partial dependence plot data"""

    feature_name: str
    feature_values: list[float]
    partial_dependence: list[float]
    ice_curves: Optional[list[list[float]]] = Field(
        None, description="Individual Conditional Expectation curves"
    )


class AnchorExplanation(BaseModel):
    """Anchor explanation (IF-THEN rules)"""

    anchor_rules: list[str]  # e.g., ["age > 30", "income > 50000"]
    precision: float  # How often the rule holds
    coverage: float  # % of instances covered by this rule
    examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Example instances covered by this anchor"
    )
