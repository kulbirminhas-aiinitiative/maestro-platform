"""
Feature Materialization

Handles scheduled materialization of features from offline to online store.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from .feast_client import FeatureStoreClient

logger = logging.getLogger(__name__)


class MaterializationJob:
    """
    Feature materialization job

    Handles incremental and full materialization of features
    with scheduling and monitoring.
    """

    def __init__(
        self,
        client: Optional[FeatureStoreClient] = None,
        feature_views: Optional[list[str]] = None
    ):
        """
        Initialize materialization job

        Args:
            client: FeatureStoreClient instance
            feature_views: Feature views to materialize (None = all)
        """
        self.client = client or FeatureStoreClient()
        self.feature_views = feature_views
        self.stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "last_run_time": None,
            "last_success_time": None,
            "last_error": None
        }

    def run_incremental(self) -> dict:
        """
        Run incremental materialization

        Materializes features from last materialization to now.

        Returns:
            Materialization result
        """
        logger.info("Starting incremental materialization...")
        self.stats["total_runs"] += 1
        self.stats["last_run_time"] = datetime.utcnow()

        start_time = time.time()

        try:
            result = self.client.materialize_incremental(
                end_date=datetime.utcnow(),
                feature_views=self.feature_views
            )

            if result["status"] == "success":
                self.stats["successful_runs"] += 1
                self.stats["last_success_time"] = datetime.utcnow()
                logger.info(f"Incremental materialization completed in {time.time() - start_time:.2f}s")
            else:
                self.stats["failed_runs"] += 1
                self.stats["last_error"] = result.get("error")
                logger.error(f"Incremental materialization failed: {result.get('error')}")

            result["duration_seconds"] = time.time() - start_time
            return result

        except Exception as e:
            self.stats["failed_runs"] += 1
            self.stats["last_error"] = str(e)
            logger.error(f"Incremental materialization error: {e}")

            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": time.time() - start_time
            }

    def run_full(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """
        Run full materialization

        Args:
            start_date: Start of materialization window
            end_date: End of materialization window

        Returns:
            Materialization result
        """
        logger.info("Starting full materialization...")
        self.stats["total_runs"] += 1
        self.stats["last_run_time"] = datetime.utcnow()

        start_time = time.time()

        try:
            result = self.client.materialize(
                start_date=start_date,
                end_date=end_date,
                feature_views=self.feature_views
            )

            if result["status"] == "success":
                self.stats["successful_runs"] += 1
                self.stats["last_success_time"] = datetime.utcnow()
                logger.info(f"Full materialization completed in {time.time() - start_time:.2f}s")
            else:
                self.stats["failed_runs"] += 1
                self.stats["last_error"] = result.get("error")
                logger.error(f"Full materialization failed: {result.get('error')}")

            result["duration_seconds"] = time.time() - start_time
            return result

        except Exception as e:
            self.stats["failed_runs"] += 1
            self.stats["last_error"] = str(e)
            logger.error(f"Full materialization error: {e}")

            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": time.time() - start_time
            }

    def get_stats(self) -> dict:
        """Get materialization statistics"""
        return self.stats.copy()


class MaterializationScheduler:
    """
    Scheduler for periodic feature materialization

    Runs materialization jobs on a schedule (e.g., hourly, daily).
    """

    def __init__(
        self,
        client: Optional[FeatureStoreClient] = None,
        interval_minutes: int = 60
    ):
        """
        Initialize scheduler

        Args:
            client: FeatureStoreClient instance
            interval_minutes: Materialization interval in minutes
        """
        self.client = client or FeatureStoreClient()
        self.interval_minutes = interval_minutes
        self.jobs: dict[str, MaterializationJob] = {}
        self.running = False

    def register_job(
        self,
        job_name: str,
        feature_views: Optional[list[str]] = None
    ):
        """
        Register a materialization job

        Args:
            job_name: Unique job name
            feature_views: Feature views to materialize
        """
        self.jobs[job_name] = MaterializationJob(
            client=self.client,
            feature_views=feature_views
        )
        logger.info(f"Registered job '{job_name}' for feature views: {feature_views or 'all'}")

    def run_once(self):
        """Run all registered jobs once"""
        logger.info(f"Running {len(self.jobs)} materialization jobs...")

        results = {}
        for job_name, job in self.jobs.items():
            logger.info(f"Running job: {job_name}")
            result = job.run_incremental()
            results[job_name] = result

        return results

    def run_continuously(self):
        """
        Run jobs continuously on schedule

        Warning: This is a blocking call. Use with threading or as a background job.
        """
        self.running = True
        logger.info(f"Starting continuous materialization (interval: {self.interval_minutes} min)")

        while self.running:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in scheduled run: {e}")

            # Sleep until next run
            logger.info(f"Sleeping for {self.interval_minutes} minutes...")
            for _ in range(self.interval_minutes * 60):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Materialization scheduler stopped")

    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping materialization scheduler...")
        self.running = False

    def get_all_stats(self) -> dict:
        """Get statistics for all jobs"""
        return {
            job_name: job.get_stats()
            for job_name, job in self.jobs.items()
        }


def setup_materialization_cron():
    """
    Example: Setup materialization as a cron job

    This shows how to configure periodic materialization.
    In production, use Airflow, Kubernetes CronJob, or similar.
    """
    print("Materialization Cron Setup")
    print("=" * 80)
    print()
    print("Option 1: Linux Cron")
    print("-" * 80)
    print("Add to crontab (crontab -e):")
    print()
    print("# Materialize features every hour")
    print("0 * * * * cd /path/to/maestro_ml && python -m features.materialization_cli run")
    print()
    print("# Materialize features every 15 minutes")
    print("*/15 * * * * cd /path/to/maestro_ml && python -m features.materialization_cli run")
    print()
    print()
    print("Option 2: Kubernetes CronJob")
    print("-" * 80)
    print("""
apiVersion: batch/v1
kind: CronJob
metadata:
  name: feast-materialization
spec:
  schedule: "0 * * * *"  # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: materialization
            image: maestro-ml:latest
            command:
            - python
            - -m
            - features.materialization_cli
            - run
          restartPolicy: OnFailure
""")
    print()
    print("Option 3: Airflow DAG")
    print("-" * 80)
    print("""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def materialize_features():
    from features.materialization import MaterializationJob
    job = MaterializationJob()
    result = job.run_incremental()
    print(f"Materialization result: {result}")

dag = DAG(
    'feast_materialization',
    default_args={
        'owner': 'ml-platform',
        'retries': 3,
        'retry_delay': timedelta(minutes=5),
    },
    description='Materialize Feast features',
    schedule_interval='@hourly',
    start_date=datetime(2024, 1, 1),
    catchup=False,
)

materialize_task = PythonOperator(
    task_id='materialize_features',
    python_callable=materialize_features,
    dag=dag,
)
""")


if __name__ == "__main__":
    # Example usage
    scheduler = MaterializationScheduler(interval_minutes=60)

    # Register jobs for different feature views
    scheduler.register_job("user_features_job", feature_views=["user_features"])
    scheduler.register_job("model_metrics_job", feature_views=["model_performance_features"])
    scheduler.register_job("all_features_job", feature_views=None)

    # Run once
    results = scheduler.run_once()
    print("Materialization results:", results)

    # Get stats
    stats = scheduler.get_all_stats()
    print("Job statistics:", stats)
