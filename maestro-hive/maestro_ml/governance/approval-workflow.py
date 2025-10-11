#!/usr/bin/env python3
"""
Model Approval Workflow Automation
Automates the model approval process from Staging to Production
"""

import argparse
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import mlflow
from mlflow.tracking import MlflowClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TESTING = "testing"
    DEPLOYED = "deployed"


class ModelApprovalWorkflow:
    """Automated model approval workflow"""

    def __init__(self, mlflow_tracking_uri: str = None):
        """
        Args:
            mlflow_tracking_uri: MLflow tracking URI
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri or os.environ.get(
            'MLFLOW_TRACKING_URI',
            'http://mlflow.ml-platform.svc.cluster.local:5000'
        )
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        self.client = MlflowClient()

    def submit_for_approval(
        self,
        model_name: str,
        model_version: str,
        submitter: str,
        description: str = "",
        test_results: Dict = None
    ) -> Dict:
        """
        Submit model for approval

        Args:
            model_name: Model name
            model_version: Model version
            submitter: Person submitting
            description: Approval description
            test_results: Testing results

        Returns:
            dict: Approval request details
        """
        logger.info(f"Submitting model {model_name} v{model_version} for approval")

        # Get model version
        model_version_obj = self.client.get_model_version(model_name, model_version)

        # Create approval metadata
        approval_request = {
            'model_name': model_name,
            'model_version': model_version,
            'submitter': submitter,
            'submission_time': datetime.now().isoformat(),
            'description': description,
            'status': ApprovalStatus.PENDING.value,
            'test_results': test_results or {},
            'run_id': model_version_obj.run_id,
            'current_stage': model_version_obj.current_stage
        }

        # Set approval tags
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_status",
            ApprovalStatus.PENDING.value
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_submitter",
            submitter
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_submission_time",
            approval_request['submission_time']
        )

        # Update model description
        self.client.update_model_version(
            model_name,
            model_version,
            description=f"{description}\n[PENDING APPROVAL]"
        )

        logger.info(f"✓ Model submitted for approval")
        return approval_request

    def run_automated_tests(
        self,
        model_name: str,
        model_version: str,
        test_dataset_path: str = None
    ) -> Dict:
        """
        Run automated tests on model

        Args:
            model_name: Model name
            model_version: Model version
            test_dataset_path: Path to test dataset

        Returns:
            dict: Test results
        """
        logger.info(f"Running automated tests for {model_name} v{model_version}")

        # Update status to testing
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_status",
            ApprovalStatus.TESTING.value
        )

        # Load model
        model_uri = f"models:/{model_name}/{model_version}"
        model = mlflow.pyfunc.load_model(model_uri)

        test_results = {
            'test_time': datetime.now().isoformat(),
            'model_loaded': True,
            'tests_passed': [],
            'tests_failed': [],
            'metrics': {}
        }

        # Test 1: Model loading
        test_results['tests_passed'].append('model_loading')

        # Test 2: Prediction functionality
        try:
            # Create sample input based on model signature
            model_version_obj = self.client.get_model_version(model_name, model_version)
            run_id = model_version_obj.run_id
            run = self.client.get_run(run_id)

            # Try to predict
            sample_input = self._create_sample_input(run)
            if sample_input is not None:
                predictions = model.predict(sample_input)
                test_results['tests_passed'].append('prediction_functionality')
                test_results['sample_prediction_shape'] = str(predictions.shape if hasattr(predictions, 'shape') else len(predictions))
            else:
                test_results['tests_passed'].append('prediction_functionality_skipped')
        except Exception as e:
            test_results['tests_failed'].append(f'prediction_functionality: {str(e)}')

        # Test 3: Performance metrics (from training)
        try:
            metrics = run.data.metrics
            test_results['metrics'] = metrics

            # Check if accuracy meets threshold (example: > 0.7)
            if 'accuracy' in metrics and metrics['accuracy'] > 0.7:
                test_results['tests_passed'].append('accuracy_threshold')
            elif 'accuracy' in metrics:
                test_results['tests_failed'].append(f"accuracy_threshold: {metrics['accuracy']} < 0.7")
        except Exception as e:
            test_results['tests_failed'].append(f'metrics_check: {str(e)}')

        # Test 4: Latency test (simple)
        try:
            import time
            if sample_input is not None:
                start_time = time.time()
                _ = model.predict(sample_input)
                latency = time.time() - start_time
                test_results['metrics']['prediction_latency_ms'] = round(latency * 1000, 2)

                # Check latency < 1000ms
                if latency < 1.0:
                    test_results['tests_passed'].append('latency_threshold')
                else:
                    test_results['tests_failed'].append(f'latency_threshold: {latency*1000}ms > 1000ms')
        except Exception as e:
            test_results['tests_failed'].append(f'latency_test: {str(e)}')

        # Overall test status
        test_results['all_tests_passed'] = len(test_results['tests_failed']) == 0
        test_results['total_tests'] = len(test_results['tests_passed']) + len(test_results['tests_failed'])
        test_results['passed_count'] = len(test_results['tests_passed'])
        test_results['failed_count'] = len(test_results['tests_failed'])

        # Log test results to MLflow
        with mlflow.start_run(run_id=run_id):
            mlflow.log_dict(test_results, 'approval_tests/test_results.json')
            mlflow.log_metric('approval_tests_passed', test_results['passed_count'])
            mlflow.log_metric('approval_tests_failed', test_results['failed_count'])

        logger.info(f"✓ Automated tests complete: {test_results['passed_count']}/{test_results['total_tests']} passed")
        return test_results

    def approve_model(
        self,
        model_name: str,
        model_version: str,
        approver: str,
        comments: str = "",
        auto_promote: bool = True
    ) -> Dict:
        """
        Approve model for production

        Args:
            model_name: Model name
            model_version: Model version
            approver: Person approving
            comments: Approval comments
            auto_promote: Automatically promote to Production stage

        Returns:
            dict: Approval details
        """
        logger.info(f"Approving model {model_name} v{model_version}")

        approval_details = {
            'model_name': model_name,
            'model_version': model_version,
            'approver': approver,
            'approval_time': datetime.now().isoformat(),
            'comments': comments,
            'status': ApprovalStatus.APPROVED.value,
            'auto_promoted': auto_promote
        }

        # Update approval tags
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_status",
            ApprovalStatus.APPROVED.value
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_approver",
            approver
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_time",
            approval_details['approval_time']
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_comments",
            comments
        )

        # Auto-promote to Production if enabled
        if auto_promote:
            logger.info(f"Auto-promoting to Production stage")
            self.client.transition_model_version_stage(
                model_name,
                model_version,
                stage="Production",
                archive_existing_versions=True
            )
            approval_details['promoted_to_production'] = True

            # Update deployment status
            self.client.set_model_version_tag(
                model_name,
                model_version,
                "approval_status",
                ApprovalStatus.DEPLOYED.value
            )

        # Update model description
        self.client.update_model_version(
            model_name,
            model_version,
            description=f"APPROVED by {approver} on {approval_details['approval_time']}\n{comments}"
        )

        logger.info(f"✓ Model approved and {'promoted to Production' if auto_promote else 'ready for deployment'}")
        return approval_details

    def reject_model(
        self,
        model_name: str,
        model_version: str,
        reviewer: str,
        reason: str
    ) -> Dict:
        """
        Reject model

        Args:
            model_name: Model name
            model_version: Model version
            reviewer: Person rejecting
            reason: Rejection reason

        Returns:
            dict: Rejection details
        """
        logger.info(f"Rejecting model {model_name} v{model_version}")

        rejection_details = {
            'model_name': model_name,
            'model_version': model_version,
            'reviewer': reviewer,
            'rejection_time': datetime.now().isoformat(),
            'reason': reason,
            'status': ApprovalStatus.REJECTED.value
        }

        # Update tags
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_status",
            ApprovalStatus.REJECTED.value
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "approval_reviewer",
            reviewer
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "rejection_time",
            rejection_details['rejection_time']
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "rejection_reason",
            reason
        )

        # Archive version
        self.client.transition_model_version_stage(
            model_name,
            model_version,
            stage="Archived"
        )

        # Update description
        self.client.update_model_version(
            model_name,
            model_version,
            description=f"REJECTED by {reviewer}\nReason: {reason}"
        )

        logger.info(f"✓ Model rejected and archived")
        return rejection_details

    def get_approval_status(
        self,
        model_name: str,
        model_version: str
    ) -> Dict:
        """
        Get approval status

        Args:
            model_name: Model name
            model_version: Model version

        Returns:
            dict: Approval status details
        """
        model_version_obj = self.client.get_model_version(model_name, model_version)

        # Get tags
        tags = {tag.key: tag.value for tag in model_version_obj.tags}

        status = {
            'model_name': model_name,
            'model_version': model_version,
            'current_stage': model_version_obj.current_stage,
            'approval_status': tags.get('approval_status', 'unknown'),
            'submitter': tags.get('approval_submitter', 'unknown'),
            'submission_time': tags.get('approval_submission_time', 'unknown'),
            'approver': tags.get('approval_approver'),
            'approval_time': tags.get('approval_time'),
            'comments': tags.get('approval_comments'),
            'rejection_reason': tags.get('rejection_reason')
        }

        return status

    def list_pending_approvals(self) -> List[Dict]:
        """
        List all models pending approval

        Returns:
            list: Pending approval requests
        """
        pending_approvals = []

        # Get all registered models
        for rm in self.client.search_registered_models():
            # Get all versions
            for version in self.client.search_model_versions(f"name='{rm.name}'"):
                tags = {tag.key: tag.value for tag in version.tags}

                if tags.get('approval_status') == ApprovalStatus.PENDING.value:
                    pending_approvals.append({
                        'model_name': rm.name,
                        'model_version': version.version,
                        'current_stage': version.current_stage,
                        'submitter': tags.get('approval_submitter', 'unknown'),
                        'submission_time': tags.get('approval_submission_time', 'unknown')
                    })

        return pending_approvals

    def _create_sample_input(self, run):
        """Create sample input for testing"""
        import pandas as pd
        import numpy as np

        # Try to get input example from run
        try:
            artifacts = self.client.list_artifacts(run.info.run_id)
            for artifact in artifacts:
                if 'input_example' in artifact.path:
                    input_example_path = self.client.download_artifacts(run.info.run_id, artifact.path)
                    # Load and return
                    return pd.read_json(input_example_path, orient='split')
        except:
            pass

        # Fallback: create dummy input based on params
        try:
            # Create simple 2D array (1 sample, 10 features)
            return np.random.rand(1, 10)
        except:
            return None


def main(args):
    workflow = ModelApprovalWorkflow()

    if args.action == 'submit':
        # Submit for approval
        result = workflow.submit_for_approval(
            model_name=args.model_name,
            model_version=args.model_version,
            submitter=args.submitter,
            description=args.description or ""
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'test':
        # Run automated tests
        result = workflow.run_automated_tests(
            model_name=args.model_name,
            model_version=args.model_version,
            test_dataset_path=args.test_dataset
        )
        print(json.dumps(result, indent=2))

        # Print summary
        print(f"\n{'='*60}")
        print(f"TEST RESULTS: {result['passed_count']}/{result['total_tests']} passed")
        print(f"{'='*60}")
        if result['tests_failed']:
            print("Failed tests:")
            for test in result['tests_failed']:
                print(f"  ❌ {test}")
        print()

    elif args.action == 'approve':
        # Approve model
        result = workflow.approve_model(
            model_name=args.model_name,
            model_version=args.model_version,
            approver=args.approver,
            comments=args.comments or "",
            auto_promote=args.auto_promote
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'reject':
        # Reject model
        result = workflow.reject_model(
            model_name=args.model_name,
            model_version=args.model_version,
            reviewer=args.reviewer,
            reason=args.reason
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'status':
        # Get status
        result = workflow.get_approval_status(
            model_name=args.model_name,
            model_version=args.model_version
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'list-pending':
        # List pending approvals
        result = workflow.list_pending_approvals()
        print(f"\nPending Approvals: {len(result)}")
        print("="*80)
        for item in result:
            print(f"- {item['model_name']} v{item['model_version']}")
            print(f"  Stage: {item['current_stage']}")
            print(f"  Submitted by: {item['submitter']} at {item['submission_time']}")
            print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Model approval workflow')
    parser.add_argument('action', choices=['submit', 'test', 'approve', 'reject', 'status', 'list-pending'],
                       help='Workflow action')
    parser.add_argument('--model-name', help='Model name')
    parser.add_argument('--model-version', help='Model version')
    parser.add_argument('--submitter', help='Submitter name')
    parser.add_argument('--approver', help='Approver name')
    parser.add_argument('--reviewer', help='Reviewer name')
    parser.add_argument('--description', help='Submission description')
    parser.add_argument('--comments', help='Approval comments')
    parser.add_argument('--reason', help='Rejection reason')
    parser.add_argument('--test-dataset', help='Test dataset path')
    parser.add_argument('--auto-promote', action='store_true', default=True, help='Auto-promote to Production')

    args = parser.parse_args()
    main(args)
