"""
AutoML Engine

Core AutoML engine that orchestrates automated model selection,
hyperparameter optimization, and ensemble generation.
"""

import logging
import time
from datetime import datetime
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score

from ..models.result_models import (
    AutoMLConfig,
    AutoMLResult,
    TaskType,
    TrialResult,
)

logger = logging.getLogger(__name__)


class AutoMLEngine:
    """
    Core AutoML engine

    Orchestrates automated machine learning including:
    - Model selection
    - Hyperparameter optimization
    - Ensemble generation
    - Experiment tracking
    """

    def __init__(self, config: AutoMLConfig):
        """
        Initialize AutoML engine

        Args:
            config: AutoML configuration
        """
        self.config = config
        self.trials: list[TrialResult] = []
        self.best_model = None
        self.ensemble_model = None
        self.models_cache: dict[int, Any] = {}

        # MLflow setup
        if config.mlflow_tracking:
            try:
                import mlflow
                self.mlflow = mlflow
                mlflow.set_experiment(config.mlflow_experiment)
            except ImportError:
                logger.warning("MLflow not installed, tracking disabled")
                self.mlflow = None
        else:
            self.mlflow = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        experiment_name: Optional[str] = None
    ) -> AutoMLResult:
        """
        Run AutoML to find best model

        Args:
            X: Training features
            y: Training target
            X_val: Validation features (optional)
            y_val: Validation target (optional)
            experiment_name: Custom experiment name

        Returns:
            AutoML result with best model and statistics
        """
        start_time = time.time()
        started_at = datetime.utcnow()

        logger.info(f"Starting AutoML with config: {self.config.dict()}")

        # Get list of estimators to try
        estimators = self._get_estimators()

        logger.info(f"Testing {len(estimators)} estimators: {list(estimators.keys())}")

        # Track in MLflow
        mlflow_run_id = None
        mlflow_experiment_id = None

        if self.mlflow:
            run = self.mlflow.start_run(run_name=experiment_name or "automl-run")
            mlflow_run_id = run.info.run_id
            mlflow_experiment_id = run.info.experiment_id

            # Log config
            self.mlflow.log_params({
                "task": self.config.task.value,
                "metric": self.config.metric,
                "time_budget": self.config.time_budget_seconds,
                "max_trials": self.config.max_trials,
                "ensemble": self.config.ensemble,
                "cv_folds": self.config.cv_folds
            })

        # Try each estimator
        trial_id = 0
        for estimator_name, estimator_class in estimators.items():
            if time.time() - start_time > self.config.time_budget_seconds:
                logger.info("Time budget exceeded, stopping search")
                break

            if trial_id >= self.config.max_trials:
                logger.info("Max trials reached, stopping search")
                break

            # Get default hyperparameters
            params = self._get_default_params(estimator_name)

            # Train and evaluate
            trial_result = self._evaluate_trial(
                trial_id=trial_id,
                estimator_name=estimator_name,
                estimator_class=estimator_class,
                params=params,
                X=X,
                y=y,
                X_val=X_val,
                y_val=y_val
            )

            self.trials.append(trial_result)
            trial_id += 1

            logger.info(
                f"Trial {trial_id}: {estimator_name} - "
                f"Score: {trial_result.score:.4f} - "
                f"Time: {trial_result.training_time_seconds:.2f}s"
            )

        # Find best trial
        successful_trials = [t for t in self.trials if t.status == "completed"]

        if not successful_trials:
            raise ValueError("No successful trials found")

        best_trial = max(successful_trials, key=lambda t: t.score)

        # Build ensemble if requested
        ensemble_score = None
        if self.config.ensemble and len(successful_trials) >= 2:
            ensemble_score = self._build_ensemble(X, y)
            logger.info(f"Ensemble score: {ensemble_score:.4f}")

        # Calculate statistics
        total_time = time.time() - start_time
        successful_count = len(successful_trials)
        failed_count = len(self.trials) - successful_count

        # Create result
        result = AutoMLResult(
            best_trial_id=best_trial.trial_id,
            best_model_name=best_trial.model_name,
            best_score=best_trial.score,
            best_params=best_trial.hyperparameters,
            total_trials=len(self.trials),
            successful_trials=successful_count,
            failed_trials=failed_count,
            trials=self.trials,
            ensemble_score=ensemble_score,
            ensemble_models=[t.model_name for t in self.trials[:self.config.ensemble_size]]
            if self.config.ensemble else None,
            config=self.config,
            total_time_seconds=total_time,
            mlflow_run_id=mlflow_run_id,
            mlflow_experiment_id=mlflow_experiment_id,
            started_at=started_at,
            completed_at=datetime.utcnow()
        )

        # Log to MLflow
        if self.mlflow:
            self.mlflow.log_metric("best_score", best_trial.score)
            self.mlflow.log_metric("total_trials", len(self.trials))
            self.mlflow.log_metric("successful_trials", successful_count)
            self.mlflow.log_metric("total_time_seconds", total_time)

            if ensemble_score:
                self.mlflow.log_metric("ensemble_score", ensemble_score)

            self.mlflow.end_run()

        logger.info(f"AutoML completed in {total_time:.2f}s")
        logger.info(f"Best model: {best_trial.model_name} with score {best_trial.score:.4f}")

        return result

    def _get_estimators(self) -> dict[str, type]:
        """Get list of estimators to try based on task and config"""
        from sklearn.ensemble import (
            RandomForestClassifier,
            RandomForestRegressor,
            ExtraTreesClassifier,
            ExtraTreesRegressor,
            GradientBoostingClassifier,
            GradientBoostingRegressor
        )
        from sklearn.linear_model import LogisticRegression, Ridge, Lasso
        from sklearn.svm import SVC, SVR
        from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor

        # Default estimators by task type
        if self.config.task in [TaskType.CLASSIFICATION, TaskType.BINARY_CLASSIFICATION, TaskType.MULTICLASS_CLASSIFICATION]:
            all_estimators = {
                "random_forest": RandomForestClassifier,
                "extra_trees": ExtraTreesClassifier,
                "gradient_boosting": GradientBoostingClassifier,
                "logistic_regression": LogisticRegression,
                "svm": SVC,
                "knn": KNeighborsClassifier
            }
        else:  # Regression
            all_estimators = {
                "random_forest": RandomForestRegressor,
                "extra_trees": ExtraTreesRegressor,
                "gradient_boosting": GradientBoostingRegressor,
                "ridge": Ridge,
                "lasso": Lasso,
                "svr": SVR,
                "knn": KNeighborsRegressor
            }

        # Filter by include/exclude lists
        if self.config.include_estimators:
            estimators = {
                k: v for k, v in all_estimators.items()
                if k in self.config.include_estimators
            }
        elif self.config.exclude_estimators:
            estimators = {
                k: v for k, v in all_estimators.items()
                if k not in self.config.exclude_estimators
            }
        else:
            estimators = all_estimators

        return estimators

    def _get_default_params(self, estimator_name: str) -> dict[str, Any]:
        """Get default hyperparameters for an estimator"""
        defaults = {
            "random_forest": {"n_estimators": 100, "max_depth": 10, "random_state": self.config.random_state},
            "extra_trees": {"n_estimators": 100, "max_depth": 10, "random_state": self.config.random_state},
            "gradient_boosting": {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.1, "random_state": self.config.random_state},
            "logistic_regression": {"max_iter": 1000, "random_state": self.config.random_state},
            "ridge": {"alpha": 1.0, "random_state": self.config.random_state},
            "lasso": {"alpha": 1.0, "random_state": self.config.random_state},
            "svm": {"kernel": "rbf", "random_state": self.config.random_state},
            "svr": {"kernel": "rbf"},
            "knn": {"n_neighbors": 5}
        }

        return defaults.get(estimator_name, {})

    def _evaluate_trial(
        self,
        trial_id: int,
        estimator_name: str,
        estimator_class: type,
        params: dict[str, Any],
        X: pd.DataFrame,
        y: pd.Series,
        X_val: Optional[pd.DataFrame],
        y_val: Optional[pd.Series]
    ) -> TrialResult:
        """Evaluate a single trial"""
        started_at = datetime.utcnow()

        try:
            # Create model
            model = estimator_class(**params)

            # Cross-validation score
            start_time = time.time()

            cv_scores = cross_val_score(
                model,
                X,
                y,
                cv=self.config.cv_folds,
                scoring=self._get_scorer(),
                n_jobs=self.config.n_jobs
            )

            # Train on full training set
            model.fit(X, y)

            # Evaluate
            if X_val is not None and y_val is not None:
                score = model.score(X_val, y_val)
            else:
                score = cv_scores.mean()

            training_time = time.time() - start_time

            # Cache model
            self.models_cache[trial_id] = model

            if trial_id == 0 or score > max(t.score for t in self.trials if t.status == "completed"):
                self.best_model = model

            return TrialResult(
                trial_id=trial_id,
                model_name=estimator_name,
                hyperparameters=params,
                score=score,
                cv_scores=cv_scores.tolist(),
                cv_mean=cv_scores.mean(),
                cv_std=cv_scores.std(),
                additional_metrics={},
                training_time_seconds=training_time,
                status="completed",
                started_at=started_at,
                completed_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Trial {trial_id} failed: {str(e)}")
            return TrialResult(
                trial_id=trial_id,
                model_name=estimator_name,
                hyperparameters=params,
                score=0.0,
                training_time_seconds=0.0,
                status="failed",
                error_message=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow()
            )

    def _get_scorer(self) -> Optional[str]:
        """Get sklearn scorer name"""
        # Map common metric names to sklearn scorers
        scorers = {
            "accuracy": "accuracy",
            "f1": "f1",
            "roc_auc": "roc_auc",
            "precision": "precision",
            "recall": "recall",
            "r2": "r2",
            "neg_mean_squared_error": "neg_mean_squared_error",
            "neg_mean_absolute_error": "neg_mean_absolute_error"
        }

        return scorers.get(self.config.metric)

    def _build_ensemble(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Build voting ensemble from top models"""
        from sklearn.ensemble import VotingClassifier, VotingRegressor

        # Get top models
        top_trials = sorted(
            [t for t in self.trials if t.status == "completed"],
            key=lambda t: t.score,
            reverse=True
        )[:self.config.ensemble_size]

        # Create ensemble
        estimators = [
            (f"model_{t.trial_id}", self.models_cache[t.trial_id])
            for t in top_trials
        ]

        if self.config.task in [TaskType.CLASSIFICATION, TaskType.BINARY_CLASSIFICATION, TaskType.MULTICLASS_CLASSIFICATION]:
            ensemble = VotingClassifier(estimators=estimators, voting="soft")
        else:
            ensemble = VotingRegressor(estimators=estimators)

        # Train ensemble
        ensemble.fit(X, y)
        self.ensemble_model = ensemble

        # Evaluate
        score = ensemble.score(X, y)

        return score

    def get_best_model(self) -> Any:
        """Get the best trained model"""
        return self.best_model

    def get_ensemble_model(self) -> Optional[Any]:
        """Get the ensemble model"""
        return self.ensemble_model

    def save_model(self, filepath: str, use_ensemble: bool = False):
        """Save model to file"""
        model = self.ensemble_model if use_ensemble and self.ensemble_model else self.best_model
        joblib.dump(model, filepath)
        logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str):
        """Load model from file"""
        model = joblib.load(filepath)
        self.best_model = model
        return model
