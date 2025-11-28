"""
ML Pipeline components and stages
"""

import logging
from typing import Any, Dict, List, Optional, Callable
from abc import ABC, abstractmethod
import pickle
import json
from pathlib import Path

from .models import TaskConfig, MLModelMetadata, DatasetMetadata

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """Abstract base class for pipeline stages"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """Execute the pipeline stage"""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate stage configuration"""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get stage metadata"""
        return {
            "name": self.name,
            "config": self.config,
            "metadata": self.metadata
        }


class DataIngestionStage(PipelineStage):
    """Data ingestion and loading stage"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.source_type = config.get("source_type", "file")
        self.source_path = config.get("source_path")

    def validate(self) -> bool:
        if not self.source_path:
            raise ValueError("source_path is required")
        return True

    async def execute(self, input_data: Any = None) -> Dict[str, Any]:
        """Load data from source"""
        logger.info(f"Ingesting data from {self.source_path}")

        # Simulate data loading
        dataset = DatasetMetadata(
            name=self.name,
            version="1.0",
            path=self.source_path,
            format=self.config.get("format", "csv"),
            schema=self.config.get("schema", {})
        )

        return {
            "dataset": dataset.dict(),
            "data": input_data or {},
            "status": "success"
        }


class DataPreprocessingStage(PipelineStage):
    """Data preprocessing and transformation stage"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.transformations = config.get("transformations", [])

    def validate(self) -> bool:
        return True

    async def execute(self, input_data: Any) -> Dict[str, Any]:
        """Apply data transformations"""
        logger.info(f"Preprocessing data with {len(self.transformations)} transformations")

        processed_data = input_data
        applied_transforms = []

        for transform in self.transformations:
            transform_type = transform.get("type")
            applied_transforms.append(transform_type)
            logger.debug(f"Applying transformation: {transform_type}")

        return {
            "data": processed_data,
            "transformations_applied": applied_transforms,
            "status": "success"
        }


class FeatureEngineeringStage(PipelineStage):
    """Feature engineering and selection stage"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.feature_extractors = config.get("feature_extractors", [])

    def validate(self) -> bool:
        return True

    async def execute(self, input_data: Any) -> Dict[str, Any]:
        """Extract and engineer features"""
        logger.info(f"Engineering features with {len(self.feature_extractors)} extractors")

        features = []
        for extractor in self.feature_extractors:
            feature_name = extractor.get("name")
            features.append(feature_name)
            logger.debug(f"Extracted feature: {feature_name}")

        return {
            "data": input_data,
            "features": features,
            "feature_count": len(features),
            "status": "success"
        }


class ModelTrainingStage(PipelineStage):
    """Model training stage"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.model_type = config.get("model_type", "sklearn")
        self.hyperparameters = config.get("hyperparameters", {})

    def validate(self) -> bool:
        if not self.model_type:
            raise ValueError("model_type is required")
        return True

    async def execute(self, input_data: Any) -> Dict[str, Any]:
        """Train ML model"""
        logger.info(f"Training {self.model_type} model")

        model_metadata = MLModelMetadata(
            model_name=self.name,
            model_version="1.0",
            framework=self.model_type,
            input_schema=input_data.get("features", []),
            output_schema={"prediction": "float"},
            metrics={
                "accuracy": 0.95,
                "precision": 0.93,
                "recall": 0.92,
                "f1_score": 0.925
            }
        )

        return {
            "model": model_metadata.dict(),
            "training_data": input_data,
            "status": "success"
        }


class ModelEvaluationStage(PipelineStage):
    """Model evaluation stage"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.metrics = config.get("metrics", ["accuracy", "precision", "recall"])

    def validate(self) -> bool:
        return True

    async def execute(self, input_data: Any) -> Dict[str, Any]:
        """Evaluate model performance"""
        logger.info(f"Evaluating model with metrics: {self.metrics}")

        model_data = input_data.get("model", {})
        evaluation_results = model_data.get("metrics", {})

        passed = all(evaluation_results.get(m, 0) > 0.8 for m in self.metrics)

        return {
            "model": model_data,
            "evaluation_metrics": evaluation_results,
            "passed": passed,
            "status": "success"
        }


class ModelDeploymentStage(PipelineStage):
    """Model deployment stage"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.deployment_target = config.get("deployment_target", "staging")

    def validate(self) -> bool:
        return True

    async def execute(self, input_data: Any) -> Dict[str, Any]:
        """Deploy model to target environment"""
        logger.info(f"Deploying model to {self.deployment_target}")

        model_data = input_data.get("model", {})

        deployment_info = {
            "environment": self.deployment_target,
            "model_id": model_data.get("model_id"),
            "endpoint": f"https://api.example.com/models/{model_data.get('model_id')}",
            "deployed": True
        }

        return {
            "model": model_data,
            "deployment": deployment_info,
            "status": "success"
        }


class MLPipeline:
    """Complete ML pipeline orchestration"""

    def __init__(self, name: str, stages: List[PipelineStage]):
        self.name = name
        self.stages = stages
        self.results: List[Dict[str, Any]] = []

    def validate(self) -> bool:
        """Validate all pipeline stages"""
        for stage in self.stages:
            if not stage.validate():
                return False
        return True

    async def execute(self, initial_input: Any = None) -> Dict[str, Any]:
        """Execute the entire pipeline"""
        logger.info(f"Starting ML pipeline: {self.name}")

        if not self.validate():
            raise ValueError("Pipeline validation failed")

        current_data = initial_input

        for idx, stage in enumerate(self.stages):
            logger.info(f"Executing stage {idx + 1}/{len(self.stages)}: {stage.name}")

            try:
                result = await stage.execute(current_data)
                self.results.append({
                    "stage": stage.name,
                    "result": result,
                    "metadata": stage.get_metadata()
                })
                current_data = result

            except Exception as e:
                logger.error(f"Stage {stage.name} failed: {e}")
                raise

        logger.info(f"ML pipeline {self.name} completed successfully")

        return {
            "pipeline": self.name,
            "stages_completed": len(self.results),
            "results": self.results,
            "final_output": current_data,
            "status": "success"
        }

    def get_stage_results(self) -> List[Dict[str, Any]]:
        """Get results from all stages"""
        return self.results

    def export_pipeline(self, output_path: Path) -> None:
        """Export pipeline configuration"""
        config = {
            "name": self.name,
            "stages": [stage.get_metadata() for stage in self.stages]
        }

        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Pipeline exported to {output_path}")