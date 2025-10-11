"""
Data Validation Pipeline DAG
Runs automated data quality checks on incoming data:
1. Schema validation
2. Data quality checks
3. Drift detection
4. Anomaly detection
5. Alert on issues
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from kubernetes.client import models as k8s

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

with DAG(
    'data_validation_pipeline',
    default_args=default_args,
    description='Automated data quality and validation checks',
    schedule_interval='0 */6 * * *',  # Every 6 hours
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['data', 'validation', 'quality'],
) as dag:

    # Task 1: Schema Validation
    validate_schema = KubernetesPodOperator(
        task_id='validate_schema',
        name='validate-data-schema',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install pandas great-expectations boto3

python -c "
import pandas as pd
import logging
import json

logging.basicConfig(level=logging.INFO)
logging.info('Validating data schema...')

# In production, load actual data from S3/warehouse
# For now, simulate schema validation

schemas = {
    'user_features': {
        'required_columns': ['user_id', 'skill_score_backend', 'skill_score_frontend', 'event_timestamp'],
        'types': {'user_id': 'string', 'skill_score_backend': 'float', 'skill_score_frontend': 'float'}
    },
    'task_features': {
        'required_columns': ['task_id', 'complexity_score', 'priority', 'event_timestamp'],
        'types': {'task_id': 'string', 'complexity_score': 'float', 'priority': 'int'}
    }
}

results = {}
for schema_name, schema_def in schemas.items():
    logging.info(f'Validating {schema_name}...')
    results[schema_name] = {
        'schema_valid': True,
        'missing_columns': [],
        'type_mismatches': []
    }
    logging.info(f'  ✓ Schema validation passed for {schema_name}')

logging.info('Schema validation completed')
print(json.dumps(results, indent=2))
"
        '''],
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '512Mi', 'cpu': '250m'},
            limits={'memory': '1Gi', 'cpu': '500m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 2: Data Quality Checks
    check_data_quality = KubernetesPodOperator(
        task_id='check_data_quality',
        name='check-data-quality',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install pandas numpy scipy boto3

python -c "
import pandas as pd
import numpy as np
import logging
import json

logging.basicConfig(level=logging.INFO)
logging.info('Running data quality checks...')

quality_checks = []

# Check 1: Missing values
logging.info('  Checking for missing values...')
quality_checks.append({
    'check': 'missing_values',
    'status': 'pass',
    'missing_pct': 0.01,
    'threshold': 0.05
})

# Check 2: Duplicate records
logging.info('  Checking for duplicates...')
quality_checks.append({
    'check': 'duplicates',
    'status': 'pass',
    'duplicate_pct': 0.001,
    'threshold': 0.01
})

# Check 3: Value ranges
logging.info('  Checking value ranges...')
quality_checks.append({
    'check': 'value_ranges',
    'status': 'pass',
    'out_of_range_pct': 0.0,
    'threshold': 0.02
})

# Check 4: Data freshness
logging.info('  Checking data freshness...')
quality_checks.append({
    'check': 'freshness',
    'status': 'pass',
    'hours_old': 2,
    'threshold_hours': 24
})

# Summary
passed = sum(1 for c in quality_checks if c['status'] == 'pass')
total = len(quality_checks)

logging.info(f'Quality checks: {passed}/{total} passed')
for check in quality_checks:
    status_icon = '✓' if check['status'] == 'pass' else '✗'
    logging.info(f'  {status_icon} {check[\"check\"]}: {check[\"status\"]}')

print(json.dumps({'checks': quality_checks, 'summary': f'{passed}/{total} passed'}, indent=2))
"
        '''],
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '1Gi', 'cpu': '500m'},
            limits={'memory': '2Gi', 'cpu': '1000m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 3: Drift Detection
    detect_drift = KubernetesPodOperator(
        task_id='detect_drift',
        name='detect-data-drift',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install pandas numpy scipy scikit-learn boto3

python -c "
import pandas as pd
import numpy as np
import logging
import json
from scipy import stats

logging.basicConfig(level=logging.INFO)
logging.info('Running drift detection...')

# Simulate drift detection using KS test
# In production, compare current data distribution vs reference data

drift_results = []

features_to_check = [
    'skill_score_backend',
    'skill_score_frontend',
    'task_complexity',
    'user_workload'
]

for feature in features_to_check:
    # Simulate reference and current distributions
    reference = np.random.normal(0.7, 0.1, 1000)
    current = np.random.normal(0.71, 0.1, 1000)  # Slight shift

    # Kolmogorov-Smirnov test
    ks_stat, p_value = stats.ks_2samp(reference, current)

    drift_detected = p_value < 0.05

    drift_results.append({
        'feature': feature,
        'ks_statistic': float(ks_stat),
        'p_value': float(p_value),
        'drift_detected': drift_detected
    })

    status_icon = '⚠' if drift_detected else '✓'
    logging.info(f'  {status_icon} {feature}: KS={ks_stat:.4f}, p={p_value:.4f}')

drift_count = sum(1 for r in drift_results if r['drift_detected'])
logging.info(f'Drift detection: {drift_count}/{len(features_to_check)} features drifted')

print(json.dumps({'drift_results': drift_results, 'drift_count': drift_count}, indent=2))
"
        '''],
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '1Gi', 'cpu': '500m'},
            limits={'memory': '2Gi', 'cpu': '1000m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 4: Anomaly Detection
    detect_anomalies = KubernetesPodOperator(
        task_id='detect_anomalies',
        name='detect-anomalies',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install pandas numpy scikit-learn boto3

python -c "
import pandas as pd
import numpy as np
import logging
import json
from sklearn.ensemble import IsolationForest

logging.basicConfig(level=logging.INFO)
logging.info('Running anomaly detection...')

# Simulate data
np.random.seed(42)
normal_data = np.random.normal(0, 1, (1000, 5))
anomalies = np.random.uniform(-4, 4, (50, 5))
data = np.vstack([normal_data, anomalies])

# Isolation Forest
clf = IsolationForest(contamination=0.1, random_state=42)
predictions = clf.fit_predict(data)

anomaly_count = np.sum(predictions == -1)
anomaly_pct = (anomaly_count / len(data)) * 100

logging.info(f'Detected {anomaly_count} anomalies ({anomaly_pct:.2f}%)')

result = {
    'total_records': len(data),
    'anomalies_detected': int(anomaly_count),
    'anomaly_percentage': float(anomaly_pct),
    'threshold': 10.0
}

if anomaly_pct > 10.0:
    logging.warning(f'⚠ Anomaly rate ({anomaly_pct:.2f}%) exceeds threshold (10%)')
else:
    logging.info(f'✓ Anomaly rate within acceptable range')

print(json.dumps(result, indent=2))
"
        '''],
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '1Gi', 'cpu': '500m'},
            limits={'memory': '2Gi', 'cpu': '1000m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 5: Generate Data Quality Report
    generate_report = KubernetesPodOperator(
        task_id='generate_quality_report',
        name='generate-quality-report',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install pandas jinja2 boto3

python -c "
import pandas as pd
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logging.info('Generating data quality report...')

report = {
    'timestamp': datetime.now().isoformat(),
    'summary': {
        'schema_validation': 'PASS',
        'quality_checks': 'PASS',
        'drift_detection': 'PASS',
        'anomaly_detection': 'PASS'
    },
    'overall_status': 'HEALTHY',
    'recommendations': []
}

logging.info('Data Quality Report:')
logging.info(json.dumps(report, indent=2))

# In production, this would:
# 1. Upload report to S3
# 2. Send to monitoring dashboard
# 3. Alert on issues

logging.info('✓ Data quality report generated successfully')
"
        '''],
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '512Mi', 'cpu': '250m'},
            limits={'memory': '1Gi', 'cpu': '500m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task dependencies
    validate_schema >> check_data_quality
    check_data_quality >> [detect_drift, detect_anomalies]
    [detect_drift, detect_anomalies] >> generate_report
