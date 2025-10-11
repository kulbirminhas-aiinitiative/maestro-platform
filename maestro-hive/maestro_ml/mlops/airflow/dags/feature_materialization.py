"""
Feast Feature Materialization DAG
Materializes features from offline store to online store for real-time serving
Runs daily to keep features up-to-date
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from kubernetes.client import models as k8s

default_args = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def validate_feature_store():
    """Validate Feast feature store connectivity"""
    from feast import FeatureStore
    import logging

    logging.info("Validating Feast feature store...")
    store = FeatureStore(repo_path="/feast/feature_repo")

    # List all feature views
    feature_views = store.list_feature_views()
    logging.info(f"Found {len(feature_views)} feature views")

    for fv in feature_views:
        logging.info(f"  - {fv.name}: {len(fv.features)} features")

    return True

def materialize_features():
    """Materialize features from offline to online store"""
    from feast import FeatureStore
    from datetime import datetime, timedelta
    import logging

    logging.info("Starting feature materialization...")
    store = FeatureStore(repo_path="/feast/feature_repo")

    # Materialize last 7 days of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    logging.info(f"Materializing features from {start_date} to {end_date}")

    store.materialize(
        start_date=start_date,
        end_date=end_date
    )

    logging.info("Feature materialization completed successfully")
    return True

def validate_online_features():
    """Validate that features are available in online store"""
    from feast import FeatureStore
    import logging

    logging.info("Validating online features...")
    store = FeatureStore(repo_path="/feast/feature_repo")

    # Test retrieving a sample feature
    try:
        features = store.get_online_features(
            features=[
                "user_profile_features:skill_score_backend",
                "user_profile_features:skill_score_frontend",
            ],
            entity_rows=[{"user_id": "test_user"}]
        )

        logging.info("Successfully retrieved online features")
        logging.info(f"Features: {features.to_dict()}")
        return True
    except Exception as e:
        logging.error(f"Failed to retrieve online features: {e}")
        raise

with DAG(
    'feast_feature_materialization',
    default_args=default_args,
    description='Daily feature materialization from offline to online store',
    schedule_interval='0 2 * * *',  # Run at 2 AM daily
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['feast', 'features', 'ml-platform'],
) as dag:

    # Task 1: Validate feature store
    validate_task = KubernetesPodOperator(
        task_id='validate_feature_store',
        name='feast-validate',
        namespace='airflow',
        image='feastdev/feast-ci:latest',
        cmds=['python', '-c'],
        arguments=['''
from feast import FeatureStore
import logging

logging.basicConfig(level=logging.INFO)
logging.info("Validating Feast feature store...")

store = FeatureStore(repo_path="/feast/feature_repo")
feature_views = store.list_feature_views()
logging.info(f"Found {len(feature_views)} feature views")

for fv in feature_views:
    logging.info(f"  - {fv.name}: {len(fv.features)} features")
        '''],
        env_vars={
            'FEAST_FEATURE_STORE_YAML': '/feast/feature_store.yaml',
        },
        volumes=[
            k8s.V1Volume(
                name='feast-config',
                config_map=k8s.V1ConfigMapVolumeSource(name='feast-config')
            )
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name='feast-config',
                mount_path='/feast',
                read_only=True
            )
        ],
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 2: Materialize features
    materialize_task = KubernetesPodOperator(
        task_id='materialize_features',
        name='feast-materialize',
        namespace='airflow',
        image='feastdev/feast-ci:latest',
        cmds=['bash', '-c'],
        arguments=['''
cd /feast/feature_repo
feast materialize-incremental $(date +%Y-%m-%d)
        '''],
        env_vars={
            'FEAST_FEATURE_STORE_YAML': '/feast/feature_store.yaml',
        },
        volumes=[
            k8s.V1Volume(
                name='feast-config',
                config_map=k8s.V1ConfigMapVolumeSource(name='feast-config')
            )
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name='feast-config',
                mount_path='/feast',
                read_only=True
            )
        ],
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '1Gi', 'cpu': '500m'},
            limits={'memory': '2Gi', 'cpu': '1000m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 3: Validate online features
    validate_online_task = KubernetesPodOperator(
        task_id='validate_online_features',
        name='feast-validate-online',
        namespace='airflow',
        image='feastdev/feast-ci:latest',
        cmds=['python', '-c'],
        arguments=['''
from feast import FeatureStore
import logging

logging.basicConfig(level=logging.INFO)
logging.info("Validating online features...")

store = FeatureStore(repo_path="/feast/feature_repo")

# Test retrieving sample features
features = store.get_online_features(
    features=[
        "user_profile_features:skill_score_backend",
        "user_profile_features:skill_score_frontend",
    ],
    entity_rows=[{"user_id": "test_user"}]
)

logging.info("Successfully retrieved online features")
logging.info(f"Features: {features.to_dict()}")
        '''],
        env_vars={
            'FEAST_FEATURE_STORE_YAML': '/feast/feature_store.yaml',
        },
        volumes=[
            k8s.V1Volume(
                name='feast-config',
                config_map=k8s.V1ConfigMapVolumeSource(name='feast-config')
            )
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name='feast-config',
                mount_path='/feast',
                read_only=True
            )
        ],
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task dependencies
    validate_task >> materialize_task >> validate_online_task
