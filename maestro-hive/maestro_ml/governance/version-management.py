#!/usr/bin/env python3
"""
Model Version Management
Manages model version lifecycle: Development → Staging → Production → Archived
"""

import argparse
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.entities.model_registry import ModelVersion
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelStage(Enum):
    """Model lifecycle stages"""
    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class VersionManagement:
    """Model version lifecycle management"""

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

    def promote_version(
        self,
        model_name: str,
        model_version: str,
        target_stage: str,
        archive_existing: bool = True
    ) -> Dict:
        """
        Promote model version to target stage

        Args:
            model_name: Model name
            model_version: Model version
            target_stage: Target stage (Staging, Production)
            archive_existing: Archive existing versions in target stage

        Returns:
            dict: Promotion details
        """
        logger.info(f"Promoting {model_name} v{model_version} to {target_stage}")

        # Validate stage
        if target_stage not in [ModelStage.STAGING.value, ModelStage.PRODUCTION.value]:
            raise ValueError(f"Invalid target stage: {target_stage}")

        # Get current version info
        model_version_obj = self.client.get_model_version(model_name, model_version)

        # Transition to target stage
        self.client.transition_model_version_stage(
            name=model_name,
            version=model_version,
            stage=target_stage,
            archive_existing_versions=archive_existing
        )

        # Update tags
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "promotion_timestamp",
            datetime.now().isoformat()
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            f"promoted_to_{target_stage.lower()}",
            "true"
        )

        promotion_details = {
            'model_name': model_name,
            'model_version': model_version,
            'previous_stage': model_version_obj.current_stage,
            'target_stage': target_stage,
            'archived_existing': archive_existing,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"✓ Promoted from {model_version_obj.current_stage} to {target_stage}")
        return promotion_details

    def archive_version(
        self,
        model_name: str,
        model_version: str,
        reason: str = ""
    ) -> Dict:
        """
        Archive model version

        Args:
            model_name: Model name
            model_version: Model version
            reason: Archive reason

        Returns:
            dict: Archive details
        """
        logger.info(f"Archiving {model_name} v{model_version}")

        # Get current version info
        model_version_obj = self.client.get_model_version(model_name, model_version)

        # Transition to Archived
        self.client.transition_model_version_stage(
            name=model_name,
            version=model_version,
            stage=ModelStage.ARCHIVED.value
        )

        # Update tags
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "archive_timestamp",
            datetime.now().isoformat()
        )
        self.client.set_model_version_tag(
            model_name,
            model_version,
            "archive_reason",
            reason
        )

        archive_details = {
            'model_name': model_name,
            'model_version': model_version,
            'previous_stage': model_version_obj.current_stage,
            'archived_stage': ModelStage.ARCHIVED.value,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"✓ Archived from {model_version_obj.current_stage}")
        return archive_details

    def delete_version(
        self,
        model_name: str,
        model_version: str
    ) -> Dict:
        """
        Delete model version (permanent)

        Args:
            model_name: Model name
            model_version: Model version

        Returns:
            dict: Deletion details
        """
        logger.warning(f"Deleting {model_name} v{model_version} (permanent)")

        # Get version info before deletion
        model_version_obj = self.client.get_model_version(model_name, model_version)

        # Delete version
        self.client.delete_model_version(
            name=model_name,
            version=model_version
        )

        deletion_details = {
            'model_name': model_name,
            'model_version': model_version,
            'previous_stage': model_version_obj.current_stage,
            'deleted': True,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"✓ Deleted version {model_version}")
        return deletion_details

    def list_versions(
        self,
        model_name: str,
        stage: str = None
    ) -> List[Dict]:
        """
        List model versions

        Args:
            model_name: Model name
            stage: Filter by stage (optional)

        Returns:
            list: Model versions
        """
        # Build filter
        filter_string = f"name='{model_name}'"

        # Get versions
        versions = self.client.search_model_versions(filter_string)

        # Filter by stage if specified
        if stage:
            versions = [v for v in versions if v.current_stage == stage]

        # Convert to dict
        version_list = []
        for v in versions:
            tags = {tag.key: tag.value for tag in v.tags}
            version_list.append({
                'version': v.version,
                'stage': v.current_stage,
                'run_id': v.run_id,
                'creation_timestamp': v.creation_timestamp,
                'last_updated_timestamp': v.last_updated_timestamp,
                'description': v.description,
                'tags': tags
            })

        # Sort by version (descending)
        version_list.sort(key=lambda x: int(x['version']), reverse=True)

        return version_list

    def get_production_version(self, model_name: str) -> Optional[Dict]:
        """Get current production version"""
        versions = self.list_versions(model_name, stage=ModelStage.PRODUCTION.value)
        return versions[0] if versions else None

    def get_staging_versions(self, model_name: str) -> List[Dict]:
        """Get all staging versions"""
        return self.list_versions(model_name, stage=ModelStage.STAGING.value)

    def auto_archive_old_versions(
        self,
        model_name: str,
        days_old: int = 30,
        keep_last_n: int = 5,
        dry_run: bool = False
    ) -> Dict:
        """
        Automatically archive old versions

        Args:
            model_name: Model name
            days_old: Archive versions older than N days
            keep_last_n: Keep at least N latest versions
            dry_run: Don't actually archive, just report

        Returns:
            dict: Archive summary
        """
        logger.info(f"Auto-archiving old versions for {model_name}")

        # Get all non-production, non-archived versions
        all_versions = self.list_versions(model_name)
        candidates = [
            v for v in all_versions
            if v['stage'] not in [ModelStage.PRODUCTION.value, ModelStage.ARCHIVED.value]
        ]

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cutoff_timestamp = int(cutoff_date.timestamp() * 1000)

        # Find versions to archive
        to_archive = []
        for v in candidates:
            # Skip if in top N latest
            if int(v['version']) in [int(x['version']) for x in candidates[:keep_last_n]]:
                continue

            # Check age
            if v['last_updated_timestamp'] < cutoff_timestamp:
                to_archive.append(v)

        # Archive versions
        archived_versions = []
        if not dry_run:
            for v in to_archive:
                try:
                    self.archive_version(
                        model_name=model_name,
                        model_version=v['version'],
                        reason=f"Auto-archived: older than {days_old} days"
                    )
                    archived_versions.append(v['version'])
                except Exception as e:
                    logger.error(f"Failed to archive version {v['version']}: {e}")

        summary = {
            'model_name': model_name,
            'total_versions': len(all_versions),
            'candidates': len(candidates),
            'to_archive': len(to_archive),
            'archived': len(archived_versions) if not dry_run else 0,
            'archived_versions': archived_versions if not dry_run else [v['version'] for v in to_archive],
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat()
        }

        if dry_run:
            logger.info(f"DRY RUN: Would archive {len(to_archive)} versions")
        else:
            logger.info(f"✓ Archived {len(archived_versions)} versions")

        return summary

    def compare_versions(
        self,
        model_name: str,
        version_a: str,
        version_b: str
    ) -> Dict:
        """
        Compare two model versions

        Args:
            model_name: Model name
            version_a: First version
            version_b: Second version

        Returns:
            dict: Comparison results
        """
        logger.info(f"Comparing {model_name} v{version_a} vs v{version_b}")

        # Get version info
        version_a_obj = self.client.get_model_version(model_name, version_a)
        version_b_obj = self.client.get_model_version(model_name, version_b)

        # Get run metrics
        run_a = self.client.get_run(version_a_obj.run_id)
        run_b = self.client.get_run(version_b_obj.run_id)

        metrics_a = run_a.data.metrics
        metrics_b = run_b.data.metrics

        # Compare metrics
        metric_comparison = {}
        all_metrics = set(metrics_a.keys()) | set(metrics_b.keys())

        for metric in all_metrics:
            val_a = metrics_a.get(metric)
            val_b = metrics_b.get(metric)

            if val_a is not None and val_b is not None:
                diff = val_b - val_a
                pct_change = (diff / val_a * 100) if val_a != 0 else 0
                metric_comparison[metric] = {
                    'version_a': val_a,
                    'version_b': val_b,
                    'difference': diff,
                    'percent_change': pct_change,
                    'better': 'b' if val_b > val_a else 'a' if val_a > val_b else 'equal'
                }
            elif val_a is not None:
                metric_comparison[metric] = {'version_a': val_a, 'version_b': None}
            else:
                metric_comparison[metric] = {'version_a': None, 'version_b': val_b}

        comparison = {
            'model_name': model_name,
            'version_a': {
                'version': version_a,
                'stage': version_a_obj.current_stage,
                'run_id': version_a_obj.run_id,
                'creation_timestamp': version_a_obj.creation_timestamp
            },
            'version_b': {
                'version': version_b,
                'stage': version_b_obj.current_stage,
                'run_id': version_b_obj.run_id,
                'creation_timestamp': version_b_obj.creation_timestamp
            },
            'metrics': metric_comparison,
            'timestamp': datetime.now().isoformat()
        }

        # Print comparison
        print(f"\n{'='*80}")
        print(f"VERSION COMPARISON: {model_name}")
        print(f"{'='*80}")
        print(f"Version A: v{version_a} ({version_a_obj.current_stage})")
        print(f"Version B: v{version_b} ({version_b_obj.current_stage})")
        print(f"\nMetric Comparison:")
        print(f"{'-'*80}")

        for metric, data in metric_comparison.items():
            if 'difference' in data:
                print(f"{metric:30} | A: {data['version_a']:.4f} | B: {data['version_b']:.4f} | "
                      f"Δ: {data['difference']:+.4f} ({data['percent_change']:+.2f}%)")
            else:
                print(f"{metric:30} | A: {data['version_a']} | B: {data['version_b']}")

        return comparison

    def get_version_lineage(
        self,
        model_name: str,
        model_version: str
    ) -> Dict:
        """
        Get complete version lineage

        Args:
            model_name: Model name
            model_version: Model version

        Returns:
            dict: Version lineage
        """
        version_obj = self.client.get_model_version(model_name, model_version)
        run = self.client.get_run(version_obj.run_id)

        # Get lineage from run tags
        tags = run.data.tags
        lineage = {
            'model_name': model_name,
            'model_version': model_version,
            'run_id': version_obj.run_id,
            'stage': version_obj.current_stage,
            'data_lineage': json.loads(tags.get('data_lineage', '{}')),
            'feature_lineage': json.loads(tags.get('feature_lineage', '{}')),
            'model_lineage': json.loads(tags.get('model_lineage', '{}')),
            'deployment_lineage': json.loads(tags.get('deployment_lineage', '{}'))
        }

        return lineage


def main(args):
    vm = VersionManagement()

    if args.action == 'promote':
        result = vm.promote_version(
            model_name=args.model_name,
            model_version=args.model_version,
            target_stage=args.target_stage,
            archive_existing=args.archive_existing
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'archive':
        result = vm.archive_version(
            model_name=args.model_name,
            model_version=args.model_version,
            reason=args.reason or ""
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'delete':
        result = vm.delete_version(
            model_name=args.model_name,
            model_version=args.model_version
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'list':
        result = vm.list_versions(
            model_name=args.model_name,
            stage=args.stage
        )
        print(f"\nVersions for {args.model_name}:")
        print("="*80)
        for v in result:
            print(f"v{v['version']:3} | {v['stage']:12} | Run: {v['run_id'][:8]}... | {v['description'][:40] if v['description'] else ''}")

    elif args.action == 'production':
        result = vm.get_production_version(args.model_name)
        print(json.dumps(result, indent=2))

    elif args.action == 'auto-archive':
        result = vm.auto_archive_old_versions(
            model_name=args.model_name,
            days_old=args.days_old,
            keep_last_n=args.keep_last_n,
            dry_run=args.dry_run
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'compare':
        result = vm.compare_versions(
            model_name=args.model_name,
            version_a=args.version_a,
            version_b=args.version_b
        )
        # Already prints comparison table

    elif args.action == 'lineage':
        result = vm.get_version_lineage(
            model_name=args.model_name,
            model_version=args.model_version
        )
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Model version management')
    parser.add_argument('action', choices=['promote', 'archive', 'delete', 'list', 'production',
                                          'auto-archive', 'compare', 'lineage'],
                       help='Action to perform')
    parser.add_argument('--model-name', help='Model name')
    parser.add_argument('--model-version', help='Model version')
    parser.add_argument('--target-stage', choices=['Staging', 'Production'], help='Target stage')
    parser.add_argument('--archive-existing', action='store_true', default=True,
                       help='Archive existing versions in target stage')
    parser.add_argument('--reason', help='Archive/delete reason')
    parser.add_argument('--stage', choices=['None', 'Staging', 'Production', 'Archived'],
                       help='Filter by stage')
    parser.add_argument('--days-old', type=int, default=30, help='Days old threshold')
    parser.add_argument('--keep-last-n', type=int, default=5, help='Keep last N versions')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no actual changes)')
    parser.add_argument('--version-a', help='First version for comparison')
    parser.add_argument('--version-b', help='Second version for comparison')

    args = parser.parse_args()
    main(args)
