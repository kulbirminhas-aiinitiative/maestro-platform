# DVC (Data Version Control) Quick Start Guide

## Overview

DVC provides Git-like version control for large datasets and ML models. It integrates seamlessly with Git, storing metadata in your repository while keeping large files in remote storage (MinIO for dev, S3 for production).

## Prerequisites

- Git repository initialized
- Infrastructure services running (MinIO or S3 access)
- Python 3.8+ with pip

## Installation

### Install DVC in your ML project

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive/maestro_ml
pip install dvc[s3]
```

Or add to `requirements.txt`:
```
dvc[s3]==3.48.4
```

## Initialization

### 1. Initialize DVC in your project

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive/maestro_ml
dvc init
```

This creates a `.dvc/` directory and adds it to `.gitignore`.

### 2. Copy the template configuration

```bash
cp /home/ec2-user/projects/maestro-platform/infrastructure/templates/dvc/.dvc/config .dvc/config
```

### 3. Update credentials in `.dvc/config`

For development (MinIO):
```ini
['remote "minio-dev"']
    url = s3://dvc-storage
    endpointurl = http://localhost:29000
    access_key_id = minioadmin
    secret_access_key = <your-minio-password>
```

For production (AWS S3):
```ini
['remote "s3-prod"']
    url = s3://maestro-dvc-production
    region = us-east-1
```

### 4. Commit DVC configuration

```bash
git add .dvc/.gitignore .dvc/config
git commit -m "Initialize DVC with remote storage"
```

## Basic Workflow

### Track a dataset

```bash
# Add a large dataset to DVC tracking
dvc add data/raw/train_dataset.parquet

# This creates data/raw/train_dataset.parquet.dvc
# The actual data is cached locally and pushed to remote

# Commit the .dvc metadata file
git add data/raw/train_dataset.parquet.dvc data/raw/.gitignore
git commit -m "Track training dataset with DVC"

# Push data to remote storage
dvc push
```

### Track a directory

```bash
# Track an entire directory
dvc add data/processed/

# Commit metadata
git add data/processed.dvc data/.gitignore
git commit -m "Track processed data directory"

# Push to remote
dvc push
```

### Retrieve data

```bash
# Pull latest data from remote
dvc pull

# Or pull specific file
dvc pull data/raw/train_dataset.parquet.dvc
```

### Switch between versions

```bash
# Checkout an old commit
git checkout feature-branch

# Pull the corresponding data version
dvc checkout
```

## DVC Pipelines (Advanced)

Define reproducible data processing pipelines:

### Create `dvc.yaml`

```yaml
stages:
  preprocess:
    cmd: python scripts/preprocess.py
    deps:
      - scripts/preprocess.py
      - data/raw/train_dataset.parquet
    outs:
      - data/processed/train.parquet
      - data/processed/val.parquet

  train:
    cmd: python scripts/train.py
    deps:
      - scripts/train.py
      - data/processed/train.parquet
    params:
      - train.learning_rate
      - train.epochs
    outs:
      - models/model.pkl
    metrics:
      - metrics/train_metrics.json:
          cache: false
```

### Run pipeline

```bash
# Run entire pipeline
dvc repro

# DVC automatically tracks dependencies and only re-runs changed stages
```

### Track experiments

```bash
# Run experiments with different parameters
dvc exp run -S train.learning_rate=0.001
dvc exp run -S train.learning_rate=0.0001

# Compare experiments
dvc exp show

# Apply best experiment
dvc exp apply exp-abc123
```

## Integration with MLflow

DVC complements MLflow by versioning data, while MLflow tracks experiments:

```python
import dvc.api
import mlflow

# Use DVC to load versioned data
with dvc.api.open(
    'data/train.parquet',
    repo='/home/ec2-user/projects/maestro-platform/maestro-hive/maestro_ml',
    rev='main'
) as f:
    train_data = pd.read_parquet(f)

# Track experiment in MLflow
with mlflow.start_run():
    mlflow.log_param("data_version", dvc.api.get_url('data/train.parquet'))
    mlflow.log_param("learning_rate", 0.001)

    # Train model...
    mlflow.log_metric("accuracy", accuracy)
    mlflow.sklearn.log_model(model, "model")
```

## Multi-Repository Pattern

For shared datasets across multiple repos:

### Central data repository

```bash
# Create a dedicated data repo
mkdir /home/ec2-user/projects/maestro-data
cd /home/ec2-user/projects/maestro-data
git init
dvc init

# Add shared datasets
dvc add datasets/customer_behavior.parquet
git add .
git commit -m "Add shared customer behavior dataset"
dvc push
```

### Import in ML projects

```python
import dvc.api

# Import external dataset
dvc.api.get_url(
    'datasets/customer_behavior.parquet',
    repo='https://github.com/your-org/maestro-data',
    rev='v1.0.0'
)

# Or use dvc import
# dvc import https://github.com/your-org/maestro-data datasets/customer_behavior.parquet
```

## Storage Configuration by Environment

### Development (Local + MinIO)

```bash
# Use MinIO for fast local development
dvc remote default minio-dev
dvc push
```

### CI/CD Environment

Set environment variables in your CI/CD:
```bash
export AWS_ACCESS_KEY_ID=<minio-or-s3-key>
export AWS_SECRET_ACCESS_KEY=<minio-or-s3-secret>
export DVC_REMOTE=minio-dev  # or s3-prod
```

### Production

```bash
# Switch to S3 for production
dvc remote default s3-prod
dvc push
```

## Best Practices

1. **Commit .dvc files, not data**: Always commit `.dvc` metadata files to Git, never the actual data.

2. **Use .dvcignore**: Exclude temporary files from DVC tracking:
   ```
   # .dvcignore
   *.tmp
   *.log
   __pycache__/
   ```

3. **Version datasets with tags**: Tag important dataset versions:
   ```bash
   git tag -a data-v1.0 -m "Production training dataset v1.0"
   git push origin data-v1.0
   ```

4. **Pipeline automation**: Use `dvc.yaml` for reproducible pipelines.

5. **Cache management**: Clean old cache entries:
   ```bash
   dvc gc -w  # Remove unused cache entries
   ```

6. **Large files**: DVC shines with files >10MB. For smaller files, Git LFS or regular Git may suffice.

## Troubleshooting

### Data not syncing

```bash
# Check remote configuration
dvc remote list

# Verify remote connectivity
dvc remote list --verbose

# Force push
dvc push --force
```

### Cache issues

```bash
# Clear local cache
dvc cache dir

# Rebuild cache
dvc checkout --relink
```

### MinIO connection errors

Ensure MinIO is running:
```bash
curl http://localhost:29000/minio/health/live
```

Check credentials in `.dvc/config` match `.env.infrastructure`.

## Next Steps

- [DVC Official Documentation](https://dvc.org/doc)
- [DVC Studio](https://studio.iterative.ai/) - Web UI for DVC (optional)
- Integrate DVC with CI/CD pipelines
- Set up automated data validation in pipelines

## Support

For questions or issues:
- DVC GitHub: https://github.com/iterative/dvc
- Maestro Platform team: #maestro-ml Slack channel
