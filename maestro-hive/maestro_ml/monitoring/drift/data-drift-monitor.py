#!/usr/bin/env python3
"""
Data Drift Monitoring with Evidently AI
Detects distribution shifts in input features
"""

import argparse
import pandas as pd
import numpy as np
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.metrics import *
import mlflow
from datetime import datetime
import json
import os


class DataDriftMonitor:
    """Monitor data drift using Evidently AI"""

    def __init__(self, reference_data: pd.DataFrame, mlflow_tracking_uri: str = None):
        """
        Args:
            reference_data: Reference (training) dataset
            mlflow_tracking_uri: MLflow URI for logging
        """
        self.reference_data = reference_data
        self.mlflow_tracking_uri = mlflow_tracking_uri or os.environ.get(
            'MLFLOW_TRACKING_URI',
            'http://mlflow.ml-platform.svc.cluster.local:5000'
        )
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)

    def detect_drift(
        self,
        current_data: pd.DataFrame,
        drift_threshold: float = 0.05,
        report_path: str = None
    ) -> dict:
        """
        Detect data drift between reference and current data

        Args:
            current_data: Current (production) dataset
            drift_threshold: P-value threshold for drift detection
            report_path: Path to save HTML report

        Returns:
            dict: Drift detection results
        """
        # Create drift report
        report = Report(metrics=[
            DataDriftPreset(stattest_threshold=drift_threshold),
            DataQualityPreset(),
            ColumnDriftMetric(column_name="all"),
            DatasetDriftMetric(),
            DatasetMissingValuesMetric(),
        ])

        report.run(
            reference_data=self.reference_data,
            current_data=current_data
        )

        # Extract metrics
        report_dict = report.as_dict()

        # Get drift results
        drift_results = {
            'timestamp': datetime.now().isoformat(),
            'dataset_drift': report_dict['metrics'][3]['result']['dataset_drift'],
            'drift_share': report_dict['metrics'][3]['result']['drift_share'],
            'number_of_drifted_columns': report_dict['metrics'][3]['result']['number_of_drifted_columns'],
            'drifted_columns': [],
            'drift_scores': {}
        }

        # Extract per-column drift
        for metric in report_dict['metrics']:
            if metric['metric'] == 'ColumnDriftMetric':
                column_name = metric['result']['column_name']
                drift_score = metric['result'].get('drift_score', 0)
                is_drifted = metric['result'].get('drift_detected', False)

                drift_results['drift_scores'][column_name] = drift_score

                if is_drifted:
                    drift_results['drifted_columns'].append({
                        'column': column_name,
                        'drift_score': drift_score,
                        'stattest': metric['result'].get('stattest_name', 'unknown')
                    })

        # Save HTML report
        if report_path:
            report.save_html(report_path)
            print(f"✓ Drift report saved: {report_path}")

        return drift_results

    def log_to_mlflow(self, drift_results: dict, model_name: str):
        """
        Log drift results to MLflow

        Args:
            drift_results: Drift detection results
            model_name: Model name for tracking
        """
        with mlflow.start_run(run_name=f"drift_detection_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            # Log metrics
            mlflow.log_metric("dataset_drift", 1 if drift_results['dataset_drift'] else 0)
            mlflow.log_metric("drift_share", drift_results['drift_share'])
            mlflow.log_metric("num_drifted_columns", drift_results['number_of_drifted_columns'])

            # Log per-column drift scores
            for column, score in drift_results['drift_scores'].items():
                mlflow.log_metric(f"drift_score_{column}", score)

            # Log drift results as JSON
            with open('/tmp/drift_results.json', 'w') as f:
                json.dump(drift_results, f, indent=2)
            mlflow.log_artifact('/tmp/drift_results.json')

            # Log tags
            mlflow.set_tag("monitoring_type", "data_drift")
            mlflow.set_tag("model_name", model_name)
            mlflow.set_tag("timestamp", drift_results['timestamp'])
            mlflow.set_tag("drift_detected", str(drift_results['dataset_drift']))

    def alert_if_drift(self, drift_results: dict, alert_threshold: float = 0.3):
        """
        Generate alert if drift exceeds threshold

        Args:
            drift_results: Drift detection results
            alert_threshold: Threshold for alerting (drift share)

        Returns:
            bool: True if alert should be triggered
        """
        if drift_results['drift_share'] >= alert_threshold:
            print("\n" + "="*80)
            print("⚠️  DRIFT ALERT")
            print("="*80)
            print(f"Drift share: {drift_results['drift_share']:.2%}")
            print(f"Drifted columns: {drift_results['number_of_drifted_columns']}")
            print(f"Threshold: {alert_threshold:.2%}")
            print("\nDrifted features:")
            for col in drift_results['drifted_columns']:
                print(f"  - {col['column']}: score={col['drift_score']:.4f} ({col['stattest']})")
            print("="*80)
            return True
        return False


def main(args):
    # Load reference data (training data)
    print("Loading reference data...")
    reference_data = pd.read_csv(args.reference_data) if args.reference_data.endswith('.csv') else pd.read_parquet(args.reference_data)

    # Load current data (production data)
    print("Loading current data...")
    current_data = pd.read_csv(args.current_data) if args.current_data.endswith('.csv') else pd.read_parquet(args.current_data)

    # Align columns
    common_columns = list(set(reference_data.columns) & set(current_data.columns))
    reference_data = reference_data[common_columns]
    current_data = current_data[common_columns]

    print(f"\nData loaded:")
    print(f"  Reference: {len(reference_data)} rows, {len(reference_data.columns)} columns")
    print(f"  Current:   {len(current_data)} rows, {len(current_data.columns)} columns")

    # Initialize monitor
    monitor = DataDriftMonitor(reference_data=reference_data)

    # Detect drift
    print("\nDetecting drift...")
    drift_results = monitor.detect_drift(
        current_data=current_data,
        drift_threshold=args.drift_threshold,
        report_path=args.report_path
    )

    # Print results
    print("\n" + "="*80)
    print("DRIFT DETECTION RESULTS")
    print("="*80)
    print(f"Dataset drift detected: {drift_results['dataset_drift']}")
    print(f"Drift share: {drift_results['drift_share']:.2%}")
    print(f"Drifted columns: {drift_results['number_of_drifted_columns']}/{len(common_columns)}")

    if drift_results['drifted_columns']:
        print("\nDrifted features:")
        for col in drift_results['drifted_columns']:
            print(f"  - {col['column']}: score={col['drift_score']:.4f}")

    # Log to MLflow
    if args.log_mlflow:
        print("\nLogging to MLflow...")
        monitor.log_to_mlflow(drift_results, args.model_name)

    # Alert if necessary
    monitor.alert_if_drift(drift_results, args.alert_threshold)

    print("\n✅ Drift detection complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Data drift monitoring')
    parser.add_argument('--reference-data', required=True, help='Reference data path (CSV/Parquet)')
    parser.add_argument('--current-data', required=True, help='Current data path (CSV/Parquet)')
    parser.add_argument('--drift-threshold', type=float, default=0.05, help='P-value threshold')
    parser.add_argument('--alert-threshold', type=float, default=0.3, help='Alert threshold (drift share)')
    parser.add_argument('--model-name', default='production-model', help='Model name')
    parser.add_argument('--report-path', default='/tmp/drift_report.html', help='HTML report path')
    parser.add_argument('--log-mlflow', action='store_true', help='Log to MLflow')

    args = parser.parse_args()
    main(args)
