"""
AutoML Tests

Comprehensive test suite for AutoML functionality.
"""

import time

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification, make_regression

from automl import AutoMLConfig, AutoMLEngine, AutoMLResult, TaskType, TrialResult


class TestAutoMLConfig:
    """Test AutoML configuration"""

    def test_default_config(self):
        """Test default configuration creation"""
        config = AutoMLConfig(task=TaskType.CLASSIFICATION)

        assert config.task == TaskType.CLASSIFICATION
        assert config.metric == "accuracy"
        assert config.time_budget_seconds == 3600
        assert config.max_trials == 100
        assert config.ensemble is True
        assert config.cv_folds == 5

    def test_custom_config(self):
        """Test custom configuration"""
        config = AutoMLConfig(
            task=TaskType.REGRESSION,
            metric="r2",
            time_budget_seconds=1800,
            max_trials=50,
            ensemble=False,
            cv_folds=3
        )

        assert config.task == TaskType.REGRESSION
        assert config.metric == "r2"
        assert config.time_budget_seconds == 1800
        assert config.max_trials == 50
        assert config.ensemble is False
        assert config.cv_folds == 3

    def test_model_selection(self):
        """Test include/exclude estimators"""
        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            include_estimators=["random_forest", "gradient_boosting"]
        )

        assert config.include_estimators == ["random_forest", "gradient_boosting"]

        config2 = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            exclude_estimators=["svm", "knn"]
        )

        assert config2.exclude_estimators == ["svm", "knn"]


class TestAutoMLEngine:
    """Test AutoML engine"""

    @pytest.fixture
    def classification_data(self):
        """Generate synthetic classification data"""
        X, y = make_classification(
            n_samples=200,
            n_features=10,
            n_informative=8,
            n_redundant=2,
            random_state=42
        )
        X_df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
        y_series = pd.Series(y, name="target")

        return X_df, y_series

    @pytest.fixture
    def regression_data(self):
        """Generate synthetic regression data"""
        X, y = make_regression(
            n_samples=200,
            n_features=10,
            n_informative=8,
            random_state=42
        )
        X_df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
        y_series = pd.Series(y, name="target")

        return X_df, y_series

    def test_engine_initialization(self):
        """Test AutoML engine initialization"""
        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            mlflow_tracking=False  # Disable MLflow for tests
        )

        engine = AutoMLEngine(config)

        assert engine.config == config
        assert engine.trials == []
        assert engine.best_model is None
        assert engine.ensemble_model is None

    def test_classification_automl(self, classification_data):
        """Test AutoML on classification task"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            metric="accuracy",
            time_budget_seconds=60,  # 1 minute for testing
            max_trials=3,  # Only test 3 models
            ensemble=False,  # Disable ensemble for speed
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        # Assertions
        assert isinstance(result, AutoMLResult)
        assert result.total_trials >= 1
        assert result.successful_trials >= 1
        assert result.best_score > 0.0
        assert result.best_model_name in [
            "random_forest",
            "extra_trees",
            "gradient_boosting",
            "logistic_regression",
            "svm",
            "knn"
        ]
        assert engine.best_model is not None

    def test_regression_automl(self, regression_data):
        """Test AutoML on regression task"""
        X, y = regression_data

        config = AutoMLConfig(
            task=TaskType.REGRESSION,
            metric="r2",
            time_budget_seconds=60,
            max_trials=3,
            ensemble=False,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        assert isinstance(result, AutoMLResult)
        assert result.total_trials >= 1
        assert result.successful_trials >= 1
        assert result.best_model_name in [
            "random_forest",
            "extra_trees",
            "gradient_boosting",
            "ridge",
            "lasso",
            "svr",
            "knn"
        ]

    def test_ensemble_generation(self, classification_data):
        """Test ensemble model generation"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=60,
            max_trials=5,
            ensemble=True,
            ensemble_size=3,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        assert result.ensemble_score is not None
        assert result.ensemble_models is not None
        assert len(result.ensemble_models) <= 5
        assert engine.ensemble_model is not None

    def test_time_budget_respected(self, classification_data):
        """Test that time budget is respected"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=10,  # Very short budget
            max_trials=100,  # Many trials requested
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)

        start_time = time.time()
        result = engine.fit(X, y)
        elapsed_time = time.time() - start_time

        # Should finish around 10 seconds (give some margin)
        assert elapsed_time < 15

    def test_max_trials_respected(self, classification_data):
        """Test that max trials is respected"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=300,
            max_trials=2,  # Only 2 trials
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        assert result.total_trials == 2

    def test_model_selection_filters(self, classification_data):
        """Test include/exclude estimators"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            include_estimators=["random_forest", "logistic_regression"],
            time_budget_seconds=60,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        # All trials should be from included estimators
        for trial in result.trials:
            if trial.status == "completed":
                assert trial.model_name in ["random_forest", "logistic_regression"]

    def test_leaderboard(self, classification_data):
        """Test leaderboard generation"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=60,
            max_trials=3,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        leaderboard = result.get_leaderboard()

        assert isinstance(leaderboard, pd.DataFrame)
        assert not leaderboard.empty
        assert "rank" in leaderboard.columns
        assert "model" in leaderboard.columns
        assert "score" in leaderboard.columns
        assert leaderboard["rank"].iloc[0] == 1  # First should be rank 1

    def test_top_k_trials(self, classification_data):
        """Test get top K trials"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=60,
            max_trials=5,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        top_3 = result.get_top_k_trials(k=3)

        assert len(top_3) <= 3
        # Scores should be in descending order
        for i in range(len(top_3) - 1):
            assert top_3[i].score >= top_3[i + 1].score

    def test_save_load_model(self, classification_data, tmp_path):
        """Test model saving and loading"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=30,
            max_trials=2,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        # Save model
        model_path = tmp_path / "best_model.pkl"
        engine.save_model(str(model_path))

        assert model_path.exists()

        # Load model
        loaded_model = engine.load_model(str(model_path))

        assert loaded_model is not None

        # Predictions should match
        pred_original = engine.best_model.predict(X)
        pred_loaded = loaded_model.predict(X)

        np.testing.assert_array_equal(pred_original, pred_loaded)

    def test_cv_scores_recorded(self, classification_data):
        """Test that CV scores are recorded for each trial"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=60,
            max_trials=2,
            cv_folds=3,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        for trial in result.trials:
            if trial.status == "completed":
                assert trial.cv_scores is not None
                assert len(trial.cv_scores) == 3  # 3 folds
                assert trial.cv_mean is not None
                assert trial.cv_std is not None

    def test_result_summary(self, classification_data):
        """Test result summary generation"""
        X, y = classification_data

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=30,
            max_trials=2,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X, y)

        summary = result.summary()

        assert "best_model" in summary
        assert "best_score" in summary
        assert "total_trials" in summary
        assert "successful_trials" in summary
        assert "failed_trials" in summary
        assert "total_time_minutes" in summary
        assert summary["total_trials"] == result.total_trials

    def test_validation_set(self, classification_data):
        """Test AutoML with separate validation set"""
        X, y = classification_data

        # Split into train and validation
        split_idx = int(0.8 * len(X))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        config = AutoMLConfig(
            task=TaskType.CLASSIFICATION,
            time_budget_seconds=30,
            max_trials=2,
            mlflow_tracking=False
        )

        engine = AutoMLEngine(config)
        result = engine.fit(X_train, y_train, X_val=X_val, y_val=y_val)

        assert result.best_score > 0.0


class TestTrialResult:
    """Test trial result model"""

    def test_trial_result_creation(self):
        """Test trial result creation"""
        trial = TrialResult(
            trial_id=1,
            model_name="random_forest",
            hyperparameters={"n_estimators": 100, "max_depth": 10},
            score=0.95,
            cv_scores=[0.93, 0.94, 0.96, 0.95, 0.97],
            cv_mean=0.95,
            cv_std=0.014,
            training_time_seconds=12.5,
            status="completed"
        )

        assert trial.trial_id == 1
        assert trial.model_name == "random_forest"
        assert trial.score == 0.95
        assert len(trial.cv_scores) == 5
        assert trial.status == "completed"


class TestSearchSpace:
    """Test search space definition"""

    def test_search_space_creation(self):
        """Test search space creation"""
        from automl import SearchSpace

        space = SearchSpace(
            model="xgboost",
            hyperparameters={
                "max_depth": (3, 10, "int"),
                "learning_rate": (0.001, 0.3, "log_uniform"),
                "n_estimators": (50, 500, "int")
            }
        )

        assert space.model == "xgboost"
        assert "max_depth" in space.hyperparameters
        assert "learning_rate" in space.hyperparameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
