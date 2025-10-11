# ML Data Pipeline

Complete data pipeline framework for ingestion, validation, and feature extraction.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌─────────┐
│   Sources   │────▶│  Ingestion   │────▶│   Validation     │────▶│ Feast   │
│ DB/API/S3   │     │   Framework  │     │    Framework     │     │ Features│
└─────────────┘     └──────────────┘     └──────────────────┘     └─────────┘
                            │                       │
                            ▼                       ▼
                    ┌──────────────┐       ┌──────────────┐
                    │   Feature    │       │  Validation  │
                    │  Extraction  │       │   Reports    │
                    └──────────────┘       └──────────────┘
```

## Components

### 1. Data Ingestion (`ingestion/`)

**Purpose**: Extract data from multiple sources with consistent interface

**Supported Sources**:
- PostgreSQL / MySQL databases
- REST APIs
- S3 / MinIO object storage
- Streaming sources (planned)

**Features**:
- Automatic schema detection
- Batch processing
- Deduplication
- Error handling & retries
- Metrics tracking

**Example**:
```python
from ingestion import DatabaseIngestion, IngestionConfig, DataSourceType

config = IngestionConfig(
    source_type=DataSourceType.DATABASE,
    source_config={
        'connection_string': 'postgresql://user:pass@host:5432/db',
        'table': 'users',
        'required_columns': ['user_id', 'email'],
    },
    target_path='/data/raw_users.parquet',
    batch_size=1000
)

ingestion = DatabaseIngestion(config)
metrics = ingestion.run()

print(f"Ingested {metrics.records_written} records in {metrics.duration_seconds}s")
```

### 2. Data Validation (`validation/`)

**Purpose**: Ensure data quality before processing

**Validation Types**:
- **Schema Validation**: Column names, data types
- **Completeness**: Null value checks
- **Uniqueness**: Duplicate detection
- **Range Validation**: Numeric bounds
- **Categorical**: Allowed value sets
- **Freshness**: Data age checks
- **Distribution**: Statistical drift detection

**Severity Levels**:
- `ERROR`: Blocks pipeline execution
- `WARNING`: Logged but continues
- `INFO`: Informational only

**Example**:
```python
from validation.data_validator import DataValidator

validator = DataValidator()

validation_config = {
    'schema': {
        'user_id': 'string',
        'age': 'int',
        'email': 'string'
    },
    'required_columns': ['user_id', 'email'],
    'unique_columns': ['user_id', 'email'],
    'range_constraints': {
        'age': (0, 120)
    },
    'categorical_constraints': {
        'status': ['active', 'inactive', 'pending']
    }
}

passed, results = validator.validate_all(data, validation_config)

if not passed:
    print(validator.generate_report())
```

### 3. Feature Extraction (`feature_extraction/`)

**Purpose**: Transform raw data into ML-ready features

**Feature Categories**:

#### User Features
- Skill scores (backend, frontend, database, devops)
- Workload metrics (current hours, capacity %)
- Velocity (tasks/week, avg completion time)
- Collaboration patterns
- Quality metrics (bug rate)
- Experience level

#### Task Features
- Complexity score
- Priority mapping
- Effort estimation
- Required skills
- Dependencies count
- Deadline urgency

#### Project Features
- Size metrics (total/completed/blocked tasks)
- Progress percentage
- Velocity (tasks per week)
- Risk score
- Team size
- Budget utilization

#### Team Features
- Team size
- Skill diversity
- Experience distribution
- Workload balance
- Collaboration score

**Example**:
```python
from feature_extraction.feature_extractor import FeatureExtractor, FeatureExtractionConfig

config = FeatureExtractionConfig(
    feature_definitions={},
    aggregation_window="7d",
    normalize=True,
    handle_missing="impute"
)

extractor = FeatureExtractor(config)

# Extract user features
user_features = extractor.extract_user_features(user_data, activity_data)

# Normalize
user_features = extractor.normalize_features(user_features)

# Handle missing
user_features = extractor.handle_missing_values(user_features)
```

## End-to-End Pipeline

See `examples/end_to_end_pipeline.py` for complete example:

```bash
# Run example pipeline
python mlops/data_pipeline/examples/end_to_end_pipeline.py
```

**Pipeline Flow**:
1. **Ingest** raw data from source
2. **Validate** data quality
3. **Extract** ML features
4. **Save** to Feast offline store
5. **Materialize** to online store
6. **Serve** for training/inference

## Integration with Airflow

Create DAGs for automated pipeline execution:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def run_user_pipeline():
    # Import pipeline components
    from data_pipeline.examples.end_to_end_pipeline import example_user_data_pipeline
    return example_user_data_pipeline()

with DAG(
    'user_feature_pipeline',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=datetime(2025, 1, 1),
    catchup=False
) as dag:

    ingest_and_extract = PythonOperator(
        task_id='ingest_and_extract_features',
        python_callable=run_user_pipeline
    )
```

## Integration with Feast

### Offline Store (Training)

```python
# Save extracted features to offline store
user_features.to_parquet('/feast/offline/user_features.parquet')

# Feast will read from offline store for training
from feast import FeatureStore

store = FeatureStore(repo_path="/feast/feature_repo")
training_data = store.get_historical_features(
    entity_df=entity_df,
    features=[
        "user_profile_features:skill_score_backend",
        "user_profile_features:current_workload_hours"
    ]
).to_df()
```

### Online Store (Inference)

```bash
# Materialize features to online store
feast materialize-incremental $(date +%Y-%m-%d)

# Get online features for inference
online_features = store.get_online_features(
    features=["user_profile_features:skill_score_backend"],
    entity_rows=[{"user_id": "user_123"}]
).to_dict()
```

## Metrics & Monitoring

### Ingestion Metrics
- `records_read`: Source records
- `records_written`: Target records
- `records_failed`: Failed records
- `bytes_processed`: Data volume
- `duration_seconds`: Execution time
- `error_rate`: Failure percentage

### Validation Metrics
- `total_checks`: Number of validations
- `passed`: Successful checks
- `failed`: Failed checks
- `errors`: Critical failures
- `warnings`: Non-critical issues

### Feature Extraction Metrics
- Feature counts by entity type
- Normalization ranges
- Missing value handling stats
- Execution time

## Configuration Files

### Ingestion Config (`config/ingestion_config.yaml`)

```yaml
sources:
  user_data:
    type: database
    connection_string: postgresql://...
    table: users
    required_columns: [user_id, email]
    batch_size: 1000

  task_data:
    type: api
    url: https://api.example.com/tasks
    headers:
      Authorization: Bearer ${API_TOKEN}
    data_key: tasks
```

### Validation Config (`config/validation_config.yaml`)

```yaml
user_data:
  schema:
    user_id: string
    email: string
    age: int

  required_columns: [user_id, email]
  unique_columns: [user_id, email]

  range_constraints:
    age: [0, 120]

  categorical_constraints:
    status: [active, inactive, pending]

  freshness:
    timestamp_column: created_at
    max_age_hours: 24
```

### Feature Extraction Config (`config/feature_config.yaml`)

```yaml
user_features:
  aggregation_window: 7d
  normalize: true
  handle_missing: impute

  features:
    - skill_score_backend
    - skill_score_frontend
    - current_workload_hours
    - tasks_completed_7d
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest mlops/data_pipeline/tests/

# Run specific test
pytest mlops/data_pipeline/tests/test_validation.py
```

### Example Tests

```python
def test_database_ingestion():
    config = IngestionConfig(...)
    ingestion = DatabaseIngestion(config)
    metrics = ingestion.run()

    assert metrics.records_written > 0
    assert metrics.error_rate < 0.05

def test_data_validation():
    validator = DataValidator()
    passed, results = validator.validate_all(test_data, validation_config)

    assert passed == True
    assert len(results) > 0
```

## Performance Optimization

### Batch Processing

```python
# Process large datasets in batches
for batch in pd.read_csv('large_file.csv', chunksize=10000):
    features = extractor.extract_user_features(batch, activity_data)
    features.to_parquet(f'/output/batch_{i}.parquet')
```

### Parallel Processing

```python
from concurrent.futures import ProcessPoolExecutor

def process_user_batch(user_ids):
    # Process batch
    return features

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_user_batch, user_id_batches))
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_skills(user_id):
    # Expensive computation
    return skills
```

## Troubleshooting

### Common Issues

**Issue**: Ingestion fails with connection error
```bash
# Check connectivity
kubectl exec -it <pod> -- psql -h postgresql.storage.svc.cluster.local -U maestro -d app_db
```

**Issue**: Validation fails with schema mismatch
```python
# Debug schema
print(data.dtypes)
print(data.columns)
```

**Issue**: Feature extraction produces NaN values
```python
# Check missing value handling
config.handle_missing = "impute"  # or "zero", "drop"
```

## Next Steps

1. ✅ Data ingestion framework complete
2. ✅ Validation framework complete
3. ✅ Feature extraction complete
4. ➡️ Integrate with Airflow DAGs
5. ➡️ Set up monitoring dashboards
6. ➡️ Add streaming support
7. ➡️ Implement feature store integration
8. ➡️ Add data lineage tracking

---

**Documentation Version**: 1.0
**Last Updated**: 2025-10-04
**Status**: Production Ready ✅
