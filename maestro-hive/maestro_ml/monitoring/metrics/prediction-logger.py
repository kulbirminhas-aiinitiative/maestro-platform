#!/usr/bin/env python3
"""
Prediction Logger
Logs predictions for analysis and audit
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionLogger:
    """Log predictions for monitoring and analysis"""

    def __init__(
        self,
        log_path: str = "/var/log/ml-predictions",
        mlflow_tracking_uri: str = None,
        log_to_mlflow: bool = True
    ):
        """
        Args:
            log_path: Path to store prediction logs
            mlflow_tracking_uri: MLflow tracking URI
            log_to_mlflow: Whether to log to MLflow
        """
        self.log_path = log_path
        self.log_to_mlflow = log_to_mlflow

        if log_to_mlflow:
            self.mlflow_tracking_uri = mlflow_tracking_uri or os.environ.get(
                'MLFLOW_TRACKING_URI',
                'http://mlflow.ml-platform.svc.cluster.local:5000'
            )
            mlflow.set_tracking_uri(self.mlflow_tracking_uri)
            self.client = MlflowClient()

        # Ensure log directory exists
        os.makedirs(log_path, exist_ok=True)

    def log_prediction(
        self,
        model_name: str,
        model_version: str,
        request_id: str,
        input_data: Any,
        prediction: Any,
        latency_ms: float,
        confidence: float = None,
        metadata: Dict = None
    ):
        """
        Log a single prediction

        Args:
            model_name: Model name
            model_version: Model version
            request_id: Unique request ID
            input_data: Input features
            prediction: Model prediction
            latency_ms: Prediction latency in milliseconds
            confidence: Prediction confidence score
            metadata: Additional metadata
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'model_name': model_name,
            'model_version': model_version,
            'input': input_data if isinstance(input_data, (dict, list)) else str(input_data),
            'prediction': prediction if isinstance(prediction, (dict, list)) else str(prediction),
            'latency_ms': latency_ms,
            'confidence': confidence,
            'metadata': metadata or {}
        }

        # Log to file
        self._log_to_file(log_entry)

        # Log to MLflow (optional)
        if self.log_to_mlflow:
            self._log_to_mlflow(log_entry)

    def _log_to_file(self, log_entry: Dict):
        """Log to JSON file"""
        log_file = os.path.join(
            self.log_path,
            f"predictions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Error logging to file: {e}")

    def _log_to_mlflow(self, log_entry: Dict):
        """Log to MLflow"""
        try:
            with mlflow.start_run(run_name=f"prediction_{log_entry['request_id']}"):
                mlflow.log_param("model_name", log_entry['model_name'])
                mlflow.log_param("model_version", log_entry['model_version'])
                mlflow.log_metric("latency_ms", log_entry['latency_ms'])

                if log_entry['confidence'] is not None:
                    mlflow.log_metric("confidence", log_entry['confidence'])

                # Log prediction as artifact
                pred_file = f"/tmp/prediction_{log_entry['request_id']}.json"
                with open(pred_file, 'w') as f:
                    json.dumps(log_entry, f, indent=2)
                mlflow.log_artifact(pred_file, 'predictions')
                os.remove(pred_file)

        except Exception as e:
            logger.error(f"Error logging to MLflow: {e}")

    def analyze_predictions(
        self,
        date: str = None,
        model_name: str = None
    ) -> pd.DataFrame:
        """
        Analyze predictions from logs

        Args:
            date: Date to analyze (YYYYMMDD format)
            model_name: Filter by model name

        Returns:
            DataFrame with prediction statistics
        """
        date = date or datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(self.log_path, f"predictions_{date}.jsonl")

        if not os.path.exists(log_file):
            logger.warning(f"Log file not found: {log_file}")
            return pd.DataFrame()

        # Load predictions
        predictions = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    pred = json.loads(line)
                    if model_name is None or pred['model_name'] == model_name:
                        predictions.append(pred)
                except Exception as e:
                    logger.error(f"Error parsing line: {e}")

        if not predictions:
            return pd.DataFrame()

        df = pd.DataFrame(predictions)

        # Calculate statistics
        stats = {
            'total_predictions': len(df),
            'avg_latency_ms': df['latency_ms'].mean(),
            'p95_latency_ms': df['latency_ms'].quantile(0.95),
            'p99_latency_ms': df['latency_ms'].quantile(0.99),
        }

        if 'confidence' in df.columns and df['confidence'].notna().any():
            stats['avg_confidence'] = df['confidence'].mean()
            stats['min_confidence'] = df['confidence'].min()

        logger.info(f"Analysis: {stats}")
        return df

    def get_recent_predictions(
        self,
        model_name: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent predictions for a model

        Args:
            model_name: Model name
            limit: Number of predictions to return

        Returns:
            List of recent predictions
        """
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(self.log_path, f"predictions_{today}.jsonl")

        if not os.path.exists(log_file):
            return []

        predictions = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    pred = json.loads(line)
                    if pred['model_name'] == model_name:
                        predictions.append(pred)
                        if len(predictions) >= limit:
                            break
                except Exception as e:
                    logger.error(f"Error parsing line: {e}")

        return predictions[-limit:]  # Return latest N


def main():
    logger = PredictionLogger()

    # Example usage
    logger.log_prediction(
        model_name="production-model",
        model_version="1",
        request_id="req_12345",
        input_data=[1, 2, 3, 4, 5],
        prediction=[0.85],
        latency_ms=45.2,
        confidence=0.92,
        metadata={"user_id": "user123"}
    )

    # Analyze predictions
    df = logger.analyze_predictions()
    print(df.head())


if __name__ == '__main__':
    main()
