"""
AutoML Result Models

Data models for AutoML results, leaderboards, and configurations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """ML task type"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"


class AutoMLConfig(BaseModel):
    """AutoML configuration"""

    # Task configuration
    task: TaskType = Field(..., description="ML task type")
    metric: str = Field("accuracy", description="Optimization metric")

    # Budget constraints
    time_budget_seconds: int = Field(3600, description="Time budget in seconds")
    max_trials: int = Field(100, description="Maximum number of trials")
    memory_limit_mb: Optional[int] = Field(None, description="Memory limit in MB")

    # Model selection
    include_estimators: Optional[list[str]] = Field(None, description="Estimators to include")
    exclude_estimators: Optional[list[str]] = Field(None, description="Estimators to exclude")

    # Ensemble configuration
    ensemble: bool = Field(True, description="Build ensemble model")
    ensemble_size: int = Field(10, description="Number of models in ensemble")
    ensemble_method: str = Field("voting", description="Ensemble method: voting or stacking")

    # Optimization
    early_stopping: bool = Field(True, description="Enable early stopping")
    n_jobs: int = Field(-1, description="Number of parallel jobs")
    random_state: int = Field(42, description="Random state for reproducibility")

    # Cross-validation
    cv_folds: int = Field(5, description="Number of CV folds")
    stratified: bool = Field(True, description="Stratified CV for classification")

    # Feature engineering
    feature_engineering: bool = Field(False, description="Enable feature engineering")
    feature_selection: bool = Field(False, description="Enable feature selection")

    # MLflow integration
    mlflow_tracking: bool = Field(True, description="Track experiments in MLflow")
    mlflow_experiment: str = Field("automl-runs", description="MLflow experiment name")


class TrialResult(BaseModel):
    """Single AutoML trial result"""

    trial_id: int = Field(..., description="Trial number")
    model_name: str = Field(..., description="Model/estimator name")
    hyperparameters: dict[str, Any] = Field(..., description="Hyperparameters used")

    # Performance metrics
    score: float = Field(..., description="Primary metric score")
    cv_scores: Optional[list[float]] = Field(None, description="Cross-validation scores")
    cv_mean: Optional[float] = Field(None, description="Mean CV score")
    cv_std: Optional[float] = Field(None, description="Std dev of CV scores")

    # Additional metrics
    additional_metrics: dict[str, float] = Field(default_factory=dict, description="Other metrics")

    # Training info
    training_time_seconds: float = Field(..., description="Training time in seconds")
    status: str = Field("completed", description="Trial status")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)


class AutoMLResult(BaseModel):
    """AutoML experiment result"""

    # Best model information
    best_trial_id: int = Field(..., description="ID of best trial")
    best_model_name: str = Field(..., description="Name of best model")
    best_score: float = Field(..., description="Best score achieved")
    best_params: dict[str, Any] = Field(..., description="Best hyperparameters")

    # Trial statistics
    total_trials: int = Field(..., description="Total number of trials")
    successful_trials: int = Field(..., description="Number of successful trials")
    failed_trials: int = Field(..., description="Number of failed trials")

    # All trials
    trials: list[TrialResult] = Field(default_factory=list, description="All trial results")

    # Ensemble information
    ensemble_score: Optional[float] = Field(None, description="Ensemble model score")
    ensemble_models: Optional[list[str]] = Field(None, description="Models in ensemble")

    # Experiment metadata
    config: AutoMLConfig = Field(..., description="AutoML configuration")
    total_time_seconds: float = Field(..., description="Total experiment time")

    # MLflow tracking
    mlflow_run_id: Optional[str] = Field(None, description="MLflow run ID")
    mlflow_experiment_id: Optional[str] = Field(None, description="MLflow experiment ID")

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)

    class Config:
        arbitrary_types_allowed = True

    def get_leaderboard(self) -> pd.DataFrame:
        """
        Get leaderboard DataFrame of all trials

        Returns:
            DataFrame with trial results ranked by score
        """
        if not self.trials:
            return pd.DataFrame()

        data = []
        for trial in self.trials:
            if trial.status == "completed":
                data.append({
                    "rank": 0,  # Will be set after sorting
                    "trial_id": trial.trial_id,
                    "model": trial.model_name,
                    "score": trial.score,
                    "cv_mean": trial.cv_mean,
                    "cv_std": trial.cv_std,
                    "training_time": trial.training_time_seconds,
                    "params": str(trial.hyperparameters)[:50] + "..."
                })

        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values("score", ascending=False).reset_index(drop=True)
            df["rank"] = range(1, len(df) + 1)
            df = df[["rank", "trial_id", "model", "score", "cv_mean", "cv_std", "training_time", "params"]]

        return df

    def get_top_k_trials(self, k: int = 5) -> list[TrialResult]:
        """
        Get top K trials by score

        Args:
            k: Number of top trials to return

        Returns:
            List of top K trial results
        """
        successful_trials = [t for t in self.trials if t.status == "completed"]
        sorted_trials = sorted(successful_trials, key=lambda t: t.score, reverse=True)
        return sorted_trials[:k]

    def get_best_trial(self) -> Optional[TrialResult]:
        """Get the best trial result"""
        for trial in self.trials:
            if trial.trial_id == self.best_trial_id:
                return trial
        return None

    def summary(self) -> dict[str, Any]:
        """Get summary statistics"""
        return {
            "best_model": self.best_model_name,
            "best_score": self.best_score,
            "total_trials": self.total_trials,
            "successful_trials": self.successful_trials,
            "failed_trials": self.failed_trials,
            "ensemble_score": self.ensemble_score,
            "total_time_minutes": self.total_time_seconds / 60,
            "avg_trial_time_seconds": self.total_time_seconds / max(self.total_trials, 1)
        }


class SearchSpace(BaseModel):
    """Hyperparameter search space definition"""

    model: str = Field(..., description="Model/estimator name")
    hyperparameters: dict[str, tuple] = Field(..., description="Hyperparameter ranges")

    class Config:
        arbitrary_types_allowed = True

    def to_optuna_space(self) -> dict[str, Any]:
        """Convert to Optuna search space format"""
        # This will be implemented when we integrate with Optuna
        return self.hyperparameters
