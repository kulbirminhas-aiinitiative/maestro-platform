"""
Tests for ML Pipeline
"""

import pytest
import asyncio
from ml_pipeline.pipeline import (
    MLPipeline,
    DataIngestionStage,
    DataPreprocessingStage,
    FeatureEngineeringStage,
    ModelTrainingStage,
    ModelEvaluationStage
)


@pytest.mark.asyncio
async def test_data_ingestion_stage():
    """Test data ingestion stage"""
    config = {
        "source_path": "/data/input.csv",
        "format": "csv",
        "schema": {}
    }

    stage = DataIngestionStage("data_ingestion", config)
    assert stage.validate()

    result = await stage.execute()
    assert result["status"] == "success"
    assert "dataset" in result


@pytest.mark.asyncio
async def test_data_preprocessing_stage():
    """Test data preprocessing stage"""
    config = {
        "transformations": [
            {"type": "normalize"},
            {"type": "fill_missing"}
        ]
    }

    stage = DataPreprocessingStage("preprocessing", config)
    assert stage.validate()

    result = await stage.execute({"data": "test"})
    assert result["status"] == "success"
    assert len(result["transformations_applied"]) == 2


@pytest.mark.asyncio
async def test_feature_engineering_stage():
    """Test feature engineering stage"""
    config = {
        "feature_extractors": [
            {"name": "feature1", "type": "numeric"},
            {"name": "feature2", "type": "categorical"}
        ]
    }

    stage = FeatureEngineeringStage("feature_engineering", config)
    assert stage.validate()

    result = await stage.execute({"data": "test"})
    assert result["status"] == "success"
    assert result["feature_count"] == 2


@pytest.mark.asyncio
async def test_model_training_stage():
    """Test model training stage"""
    config = {
        "model_type": "sklearn",
        "hyperparameters": {
            "max_depth": 10,
            "n_estimators": 100
        }
    }

    stage = ModelTrainingStage("model_training", config)
    assert stage.validate()

    input_data = {"features": ["f1", "f2"]}
    result = await stage.execute(input_data)
    assert result["status"] == "success"
    assert "model" in result


@pytest.mark.asyncio
async def test_model_evaluation_stage():
    """Test model evaluation stage"""
    config = {
        "metrics": ["accuracy", "precision", "recall"]
    }

    stage = ModelEvaluationStage("evaluation", config)
    assert stage.validate()

    input_data = {
        "model": {
            "metrics": {
                "accuracy": 0.95,
                "precision": 0.93,
                "recall": 0.92
            }
        }
    }

    result = await stage.execute(input_data)
    assert result["status"] == "success"
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_complete_pipeline():
    """Test complete ML pipeline"""
    stages = [
        DataIngestionStage("ingestion", {
            "source_path": "/data/input.csv",
            "format": "csv"
        }),
        DataPreprocessingStage("preprocessing", {
            "transformations": [{"type": "normalize"}]
        }),
        FeatureEngineeringStage("features", {
            "feature_extractors": [{"name": "f1"}]
        }),
        ModelTrainingStage("training", {
            "model_type": "sklearn"
        }),
        ModelEvaluationStage("evaluation", {
            "metrics": ["accuracy"]
        })
    ]

    pipeline = MLPipeline("test_pipeline", stages)
    assert pipeline.validate()

    result = await pipeline.execute()
    assert result["status"] == "success"
    assert result["stages_completed"] == 5


@pytest.mark.asyncio
async def test_pipeline_stage_failure():
    """Test pipeline behavior on stage failure"""

    class FailingStage(DataIngestionStage):
        async def execute(self, input_data=None):
            raise Exception("Stage failed")

    stages = [
        FailingStage("failing", {"source_path": "/data/test.csv"})
    ]

    pipeline = MLPipeline("failing_pipeline", stages)

    with pytest.raises(Exception):
        await pipeline.execute()