#!/usr/bin/env python3
"""
Inference Metrics Exporter
Exports ML inference metrics to Prometheus
"""

import os
import time
from prometheus_client import start_http_server, Counter, Histogram, Gauge, Info
import mlflow
from mlflow.tracking import MlflowClient
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Prometheus metrics
PREDICTION_COUNT = Counter(
    'model_predictions_total',
    'Total number of predictions',
    ['model', 'version']
)

REQUEST_LATENCY = Histogram(
    'model_request_latency_seconds',
    'Request latency in seconds',
    ['model', 'version'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

REQUEST_COUNT = Counter(
    'model_requests_total',
    'Total inference requests',
    ['model', 'version', 'status']
)

ERROR_RATE = Gauge(
    'model_error_rate',
    'Current error rate',
    ['model', 'version']
)

ACTIVE_CONNECTIONS = Gauge(
    'model_active_connections',
    'Active connections',
    ['model', 'version']
)

MODEL_INFO = Info(
    'model_version',
    'Model version information'
)

CONFIDENCE_SCORE = Histogram(
    'model_confidence_score',
    'Model confidence scores',
    ['model', 'version'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)

PREDICTION_VALUE = Histogram(
    'prediction_value',
    'Prediction values distribution',
    ['model', 'version'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


class InferenceMetricsExporter:
    """Export inference metrics to Prometheus"""

    def __init__(self, mlflow_tracking_uri: str = None, port: int = 9091):
        """
        Args:
            mlflow_tracking_uri: MLflow tracking URI
            port: Prometheus metrics port
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri or os.environ.get(
            'MLFLOW_TRACKING_URI',
            'http://mlflow.ml-platform.svc.cluster.local:5000'
        )
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        self.client = MlflowClient()
        self.port = port

    def export_model_info(self, model_name: str, model_stage: str = "Production"):
        """Export model version information"""
        try:
            versions = self.client.get_latest_versions(model_name, stages=[model_stage])
            if versions:
                version = versions[0]
                MODEL_INFO.info({
                    'model_name': model_name,
                    'version': version.version,
                    'stage': model_stage,
                    'run_id': version.run_id
                })
                logger.info(f"Exported model info: {model_name} v{version.version}")
        except Exception as e:
            logger.error(f"Error exporting model info: {e}")

    def record_prediction(
        self,
        model_name: str,
        model_version: str,
        latency: float,
        status: str = "success",
        prediction_value: float = None,
        confidence: float = None
    ):
        """
        Record prediction metrics

        Args:
            model_name: Model name
            model_version: Model version
            latency: Prediction latency in seconds
            status: Request status (success/error)
            prediction_value: Prediction value (0-1)
            confidence: Confidence score (0-1)
        """
        # Record metrics
        PREDICTION_COUNT.labels(model=model_name, version=model_version).inc()
        REQUEST_LATENCY.labels(model=model_name, version=model_version).observe(latency)
        REQUEST_COUNT.labels(model=model_name, version=model_version, status=status).inc()

        if prediction_value is not None:
            PREDICTION_VALUE.labels(model=model_name, version=model_version).observe(prediction_value)

        if confidence is not None:
            CONFIDENCE_SCORE.labels(model=model_name, version=model_version).observe(confidence)

    def calculate_error_rate(self, model_name: str, model_version: str):
        """Calculate and export error rate"""
        # This is a simplified version - in production, query Prometheus for actual rates
        # For now, just export a placeholder
        ERROR_RATE.labels(model=model_name, version=model_version).set(0.005)

    def update_active_connections(self, model_name: str, model_version: str, count: int):
        """Update active connections count"""
        ACTIVE_CONNECTIONS.labels(model=model_name, version=model_version).set(count)

    def start_server(self):
        """Start Prometheus metrics server"""
        logger.info(f"Starting metrics server on port {self.port}")
        start_http_server(self.port)

        # Keep server running
        while True:
            time.sleep(60)
            logger.debug("Metrics server running...")


def main():
    exporter = InferenceMetricsExporter(port=9091)

    # Export initial model info
    exporter.export_model_info("production-model", "Production")

    # Start metrics server
    logger.info("Starting inference metrics exporter")
    exporter.start_server()


if __name__ == '__main__':
    main()
