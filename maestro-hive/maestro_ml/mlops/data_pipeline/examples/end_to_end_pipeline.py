"""
End-to-End Data Pipeline Example
Demonstrates complete data flow: Ingestion → Validation → Feature Extraction → Feast
"""

import sys
import os
import logging
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import DatabaseIngestion, IngestionConfig, DataSourceType
from validation.data_validator import DataValidator
from feature_extraction.feature_extractor import FeatureExtractor, FeatureExtractionConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_user_data_pipeline():
    """Example: Ingest user data, validate, extract features, store to Feast"""

    logger.info("=" * 80)
    logger.info("User Data Pipeline - Complete Flow")
    logger.info("=" * 80)

    # Step 1: Configure Data Ingestion
    logger.info("\n[Step 1] Configuring Data Ingestion...")

    ingestion_config = IngestionConfig(
        source_type=DataSourceType.DATABASE,
        source_config={
            'connection_string': 'postgresql://maestro:maestro123@postgresql.storage.svc.cluster.local:5432/app_db',
            'table': 'users',
            'required_columns': ['user_id', 'email', 'created_at'],
            'critical_columns': ['user_id', 'email'],
            'column_mapping': {
                'id': 'user_id',
                'email_address': 'email'
            }
        },
        target_path='/tmp/raw_user_data.parquet',
        batch_size=1000,
        validation_enabled=True,
        deduplication_enabled=True
    )

    # For demo, create sample data instead of actual DB connection
    logger.info("Creating sample user data...")
    sample_users = pd.DataFrame({
        'user_id': [f'user_{i}' for i in range(1, 101)],
        'email': [f'user{i}@example.com' for i in range(1, 101)],
        'created_at': [datetime.now() for _ in range(100)],
        'experience_years': [i % 10 + 1 for i in range(100)]
    })

    # Step 2: Ingest Data
    logger.info("\n[Step 2] Ingesting User Data...")

    # Simulate ingestion
    sample_users.to_parquet(ingestion_config.target_path, index=False)
    logger.info(f"✓ Ingested {len(sample_users)} user records")

    # Load ingested data
    raw_data = pd.read_parquet(ingestion_config.target_path)

    # Step 3: Validate Data
    logger.info("\n[Step 3] Validating Data Quality...")

    validator = DataValidator(logger)

    validation_config = {
        'schema': {
            'user_id': 'string',
            'email': 'string',
            'created_at': 'datetime',
            'experience_years': 'int'
        },
        'required_columns': ['user_id', 'email'],
        'unique_columns': ['user_id', 'email'],
        'range_constraints': {
            'experience_years': (0, 50)
        },
        'max_null_percentage': 0.05
    }

    validation_passed, validation_results = validator.validate_all(raw_data, validation_config)

    if not validation_passed:
        logger.error("❌ Data validation failed!")
        logger.info(validator.generate_report())
        return False

    logger.info("✓ Data validation passed")

    # Step 4: Create Activity Data (for feature extraction)
    logger.info("\n[Step 4] Creating Activity Data...")

    sample_activities = pd.DataFrame({
        'user_id': [f'user_{i % 100 + 1}' for i in range(500)],
        'task_type': [['backend', 'frontend', 'database', 'devops'][i % 4] for i in range(500)],
        'completion_time': [3600 + (i * 100) % 7200 for i in range(500)],  # 1-3 hours
        'timestamp': [datetime.now() for _ in range(500)],
        'collaborators': [[] for _ in range(500)]
    })

    logger.info(f"✓ Created {len(sample_activities)} activity records")

    # Step 5: Extract Features
    logger.info("\n[Step 5] Extracting ML Features...")

    feature_config = FeatureExtractionConfig(
        feature_definitions={},
        aggregation_window="7d",
        normalize=True,
        handle_missing="impute"
    )

    feature_extractor = FeatureExtractor(feature_config, logger)

    user_features = feature_extractor.extract_user_features(raw_data, sample_activities)
    user_features = feature_extractor.handle_missing_values(user_features)
    user_features = feature_extractor.normalize_features(user_features)

    logger.info(f"✓ Extracted {len(user_features.columns)} features for {len(user_features)} users")
    logger.info(f"  Features: {list(user_features.columns)[:10]}...")

    # Step 6: Save Features for Feast
    logger.info("\n[Step 6] Saving Features for Feast Materialization...")

    output_path = '/tmp/user_features.parquet'
    user_features.to_parquet(output_path, index=False)

    logger.info(f"✓ Features saved to {output_path}")
    logger.info("\n" + "=" * 80)
    logger.info("Pipeline Complete!")
    logger.info("=" * 80)
    logger.info(f"\nNext Steps:")
    logger.info(f"1. Copy features to Feast offline store:")
    logger.info(f"   kubectl cp {output_path} feast/<pod>:/feast/offline/")
    logger.info(f"2. Materialize to online store:")
    logger.info(f"   feast materialize-incremental $(date +%Y-%m-%d)")
    logger.info(f"3. Serve features for training/inference")

    # Display sample features
    logger.info(f"\nSample Features (first 5 users):")
    logger.info("\n" + user_features.head().to_string())

    return True


def example_task_data_pipeline():
    """Example: Task data pipeline"""

    logger.info("\n" + "=" * 80)
    logger.info("Task Data Pipeline")
    logger.info("=" * 80)

    # Create sample task data
    sample_tasks = pd.DataFrame({
        'task_id': [f'task_{i}' for i in range(1, 51)],
        'description': [f'Implement feature {i}' * (i % 3 + 1) for i in range(1, 51)],
        'priority': [['low', 'medium', 'high', 'critical'][i % 4] for i in range(1, 51)],
        'estimated_hours': [8.0 * (i % 3 + 1) for i in range(1, 51)],
        'required_skills': ['backend,database' if i % 2 == 0 else 'frontend,testing' for i in range(1, 51)],
        'dependencies': [[] if i % 3 == 0 else [f'task_{i-1}'] for i in range(1, 51)],
        'deadline': [datetime.now() for _ in range(50)],
        'project_id': [f'proj_{i % 5 + 1}' for i in range(1, 51)]
    })

    # Validate
    validator = DataValidator(logger)

    validation_config = {
        'schema': {
            'task_id': 'string',
            'description': 'string',
            'priority': 'string',
            'estimated_hours': 'float'
        },
        'required_columns': ['task_id', 'description'],
        'unique_columns': ['task_id'],
        'categorical_constraints': {
            'priority': ['low', 'medium', 'high', 'critical']
        },
        'range_constraints': {
            'estimated_hours': (0, 160)  # Max 1 month
        }
    }

    validation_passed, results = validator.validate_all(sample_tasks, validation_config)

    if not validation_passed:
        logger.error("❌ Task data validation failed")
        return False

    logger.info("✓ Task data validated")

    # Extract features
    feature_config = FeatureExtractionConfig(feature_definitions={}, normalize=True)
    feature_extractor = FeatureExtractor(feature_config, logger)

    task_features = feature_extractor.extract_task_features(sample_tasks)

    logger.info(f"✓ Extracted {len(task_features.columns)} task features")
    logger.info(f"\nSample Task Features:")
    logger.info("\n" + task_features.head().to_string())

    return True


def run_all_examples():
    """Run all pipeline examples"""
    logger.info("\n" + "#" * 80)
    logger.info("# ML Data Pipeline - Complete Examples")
    logger.info("#" * 80)

    # User pipeline
    success = example_user_data_pipeline()

    if not success:
        logger.error("User pipeline failed")
        return

    # Task pipeline
    success = example_task_data_pipeline()

    if not success:
        logger.error("Task pipeline failed")
        return

    logger.info("\n" + "#" * 80)
    logger.info("# All Pipelines Completed Successfully!")
    logger.info("#" * 80)


if __name__ == "__main__":
    run_all_examples()
