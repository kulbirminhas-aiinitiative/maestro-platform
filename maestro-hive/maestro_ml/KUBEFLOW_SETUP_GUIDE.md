# Kubeflow Setup Guide

## Overview

This guide covers setting up **Kubeflow Pipelines** and **Katib** for the ML platform. We use a lightweight, component-based approach that integrates with existing MLflow, Feast, and Airflow infrastructure.

## Architecture Decision

**Why Lightweight Kubeflow?**

Instead of full Kubeflow installation (which includes many overlapping components), we install:
- ✅ **Kubeflow Pipelines** - ML workflow orchestration
- ✅ **Katib** - Hyperparameter tuning
- ❌ **Not installing**: Full Kubeflow (overlaps with MLflow, Airflow, Feast)

This approach:
- Reduces operational complexity
- Avoids duplicate functionality
- Integrates cleanly with existing stack
- Faster deployment and maintenance

## Components

### 1. Kubeflow Pipelines
- **Purpose**: Define, manage, and run ML workflows as DAGs
- **Integration**: Works alongside Airflow (Kubeflow for ML-specific, Airflow for general orchestration)
- **Features**:
  - Visual pipeline builder
  - Experiment tracking
  - Pipeline versioning
  - Artifact lineage

### 2. Katib
- **Purpose**: AutoML hyperparameter tuning and neural architecture search
- **Integration**: Logs results to MLflow
- **Algorithms**: Grid search, Random search, Bayesian optimization, Hyperband

### 3. Notebook Servers (Optional)
- **Purpose**: Interactive development environment
- **Integration**: Pre-configured with MLflow, Feast clients
- **Options**: JupyterLab, VS Code, RStudio

## Installation

### Method 1: Standalone Kubeflow Pipelines (Recommended)

```bash
# 1. Install Kubeflow Pipelines standalone
export PIPELINE_VERSION=2.0.5
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=$PIPELINE_VERSION"

# 2. Wait for deployment
kubectl wait --for=condition=available --timeout=600s \
  deployment/ml-pipeline -n kubeflow

# 3. Access UI
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80

# Open: http://localhost:8080
```

### Method 2: Helm Installation (Production)

```bash
# Add Kubeflow Helm repo
helm repo add kubeflow https://kubeflow.github.io/charts
helm repo update

# Install Pipelines
helm install kubeflow-pipelines kubeflow/kubeflow-pipelines \
  --namespace kubeflow \
  --create-namespace \
  --set mysql.mysqlRootPassword=<strong-password> \
  --set mysql.mysqlPassword=<strong-password> \
  --set minio.accessKey=minio \
  --set minio.secretKey=<strong-password>

# Install Katib
helm install katib kubeflow/katib \
  --namespace kubeflow
```

### Method 3: Full Kubeflow (Not Recommended)

```bash
# Only if you need all Kubeflow components
# WARNING: Large deployment, many overlapping features

export KF_VERSION=v1.8.0
wget https://github.com/kubeflow/manifests/archive/refs/tags/${KF_VERSION}.tar.gz
tar xzf ${KF_VERSION}.tar.gz
cd manifests-${KF_VERSION}

# Install all components
kustomize build example | kubectl apply -f -
```

## Kubeflow Pipelines

### Create Your First Pipeline

**`pipelines/training_pipeline.py`**:
```python
from kfp import dsl
from kfp import compiler
from kfp.dsl import component

@component(
    base_image='python:3.11',
    packages_to_install=['mlflow', 'scikit-learn', 'pandas']
)
def train_model(
    data_path: str,
    model_path: str,
    experiment_name: str
) -> dict:
    import mlflow
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    # Load data
    df = pd.read_parquet(data_path)
    X = df.drop('target', axis=1)
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    # Train model
    mlflow.set_tracking_uri('http://mlflow.ml-platform.svc.cluster.local')
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run():
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)

        mlflow.log_metric('accuracy', accuracy)
        mlflow.sklearn.log_model(model, 'model')

        return {'accuracy': accuracy, 'model_uri': mlflow.get_artifact_uri()}

@component(
    base_image='python:3.11',
    packages_to_install=['mlflow']
)
def register_model(
    model_uri: str,
    model_name: str,
    accuracy: float
) -> str:
    import mlflow

    if accuracy > 0.85:
        mlflow.set_tracking_uri('http://mlflow.ml-platform.svc.cluster.local')
        result = mlflow.register_model(model_uri, model_name)
        return f"Registered: {result.version}"
    else:
        return "Model quality gate failed"

@dsl.pipeline(
    name='ML Training Pipeline',
    description='Train and register model'
)
def training_pipeline(
    data_path: str = 's3://ml-data/training/data.parquet',
    experiment_name: str = 'training-pipeline',
    model_name: str = 'ml-platform-model'
):
    train_task = train_model(
        data_path=data_path,
        model_path='/tmp/model',
        experiment_name=experiment_name
    )

    register_task = register_model(
        model_uri=train_task.outputs['model_uri'],
        model_name=model_name,
        accuracy=train_task.outputs['accuracy']
    )

# Compile pipeline
if __name__ == '__main__':
    compiler.Compiler().compile(
        pipeline_func=training_pipeline,
        package_path='training_pipeline.yaml'
    )
```

### Upload and Run Pipeline

```bash
# Install KFP SDK
pip install kfp

# Compile pipeline
python3 pipelines/training_pipeline.py

# Upload to Kubeflow
kfp pipeline upload \
  --pipeline-name "ML Training Pipeline" \
  training_pipeline.yaml

# Run pipeline
kfp run submit \
  --experiment-name "training-experiment" \
  --pipeline-name "ML Training Pipeline" \
  --run-name "training-run-001"
```

### Pipeline with Feast Integration

```python
@component(
    base_image='python:3.11',
    packages_to_install=['feast', 'pandas']
)
def get_features(entity_ids: list, feature_refs: list) -> str:
    from feast import FeatureStore
    import pandas as pd

    store = FeatureStore(repo_path='/feast/feature_repo')

    entity_df = pd.DataFrame({'entity_id': entity_ids})
    features = store.get_historical_features(
        entity_df=entity_df,
        features=feature_refs
    ).to_df()

    # Save to parquet
    output_path = '/tmp/features.parquet'
    features.to_parquet(output_path)

    return output_path
```

## Katib - Hyperparameter Tuning

### Create Katib Experiment

**`katib/hyperparameter-tuning.yaml`**:
```yaml
apiVersion: kubeflow.org/v1beta1
kind: Experiment
metadata:
  name: random-forest-tuning
  namespace: kubeflow
spec:
  objective:
    type: maximize
    goal: 0.95
    objectiveMetricName: accuracy
  algorithm:
    algorithmName: random
  parallelTrialCount: 3
  maxTrialCount: 12
  maxFailedTrialCount: 3

  parameters:
  - name: n_estimators
    parameterType: int
    feasibleSpace:
      min: "50"
      max: "200"
  - name: max_depth
    parameterType: int
    feasibleSpace:
      min: "5"
      max: "20"
  - name: min_samples_split
    parameterType: int
    feasibleSpace:
      min: "2"
      max: "10"

  trialTemplate:
    primaryContainerName: training
    trialParameters:
    - name: n_estimators
      description: Number of trees
      reference: n_estimators
    - name: max_depth
      description: Maximum depth
      reference: max_depth
    - name: min_samples_split
      description: Minimum samples to split
      reference: min_samples_split

    trialSpec:
      apiVersion: batch/v1
      kind: Job
      spec:
        template:
          spec:
            containers:
            - name: training
              image: ml-platform/training:latest
              command:
              - python3
              - /app/train.py
              - --n-estimators=${trialParameters.n_estimators}
              - --max-depth=${trialParameters.max_depth}
              - --min-samples-split=${trialParameters.min_samples_split}
              env:
              - name: MLFLOW_TRACKING_URI
                value: http://mlflow.ml-platform.svc.cluster.local
            restartPolicy: Never
```

### Run Katib Experiment

```bash
# Create experiment
kubectl apply -f katib/hyperparameter-tuning.yaml

# Watch progress
kubectl get experiment random-forest-tuning -n kubeflow -w

# Get best trial
kubectl get experiment random-forest-tuning -n kubeflow -o jsonpath='{.status.currentOptimalTrial}'

# View all trials
kubectl get trials -n kubeflow -l experiment=random-forest-tuning
```

### Katib with Bayesian Optimization

```yaml
algorithm:
  algorithmName: bayesianoptimization
  algorithmSettings:
  - name: random_state
    value: "10"
  - name: acq_func
    value: "gp_hedge"
  - name: acq_optimizer
    value: "auto"
```

### Katib Metrics Collection

Training script must print metrics in this format:
```python
# In train.py
print(f"accuracy={accuracy}")
print(f"f1_score={f1}")
```

Katib will parse these and report to the experiment.

## Integration Patterns

### Pattern 1: Kubeflow Pipeline → MLflow

```python
@component
def train_and_log():
    import mlflow

    mlflow.set_tracking_uri('http://mlflow.ml-platform.svc.cluster.local')

    with mlflow.start_run():
        # Train model
        mlflow.log_params({...})
        mlflow.log_metrics({...})
        mlflow.sklearn.log_model(model, 'model')
```

### Pattern 2: Kubeflow Pipeline → Feast

```python
@component
def materialize_features():
    from feast import FeatureStore
    from datetime import datetime

    store = FeatureStore(repo_path='/feast/feature_repo')
    store.materialize_incremental(end_date=datetime.now())
```

### Pattern 3: Airflow → Kubeflow Pipeline

```python
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

trigger_pipeline = KubernetesPodOperator(
    task_id='trigger_kubeflow_pipeline',
    name='kfp-trigger',
    namespace='kubeflow',
    image='gcr.io/ml-pipeline/api-server:2.0.5',
    cmds=['bash', '-c'],
    arguments=[
        'kfp run submit --pipeline-name "ML Training Pipeline" --run-name "airflow-triggered-$(date +%s)"'
    ]
)
```

### Pattern 4: Katib → MLflow

```python
# In training script
import mlflow

# Log to MLflow
mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI'))
with mlflow.start_run():
    mlflow.log_params({
        'n_estimators': args.n_estimators,
        'max_depth': args.max_depth
    })
    mlflow.log_metrics({'accuracy': accuracy})

# Print for Katib
print(f"accuracy={accuracy}")
```

## Notebook Servers

### Deploy JupyterLab

```yaml
apiVersion: kubeflow.org/v1
kind: Notebook
metadata:
  name: ml-notebook
  namespace: kubeflow
spec:
  template:
    spec:
      containers:
      - name: notebook
        image: jupyter/datascience-notebook:latest
        env:
        - name: MLFLOW_TRACKING_URI
          value: http://mlflow.ml-platform.svc.cluster.local
        - name: FEAST_REPO_PATH
          value: /feast/feature_repo
        volumeMounts:
        - name: workspace
          mountPath: /home/jovyan/work
        - name: feast-repo
          mountPath: /feast/feature_repo
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
            nvidia.com/gpu: "1"  # Optional GPU
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: ml-notebook-pvc
      - name: feast-repo
        configMap:
          name: feast-repo-config
```

Access:
```bash
kubectl port-forward -n kubeflow notebook/ml-notebook 8888:8888
# Open: http://localhost:8888
```

## Monitoring

### Kubeflow Pipelines Metrics

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kfp-metrics
  namespace: kubeflow
spec:
  selector:
    matchLabels:
      app: ml-pipeline
  endpoints:
  - port: http
    path: /metrics
```

### Key Metrics

- `kfp_pipeline_runs_total` - Total pipeline runs
- `kfp_pipeline_run_duration_seconds` - Pipeline duration
- `kfp_pipeline_run_status` - Success/failure rate
- `katib_experiment_trials_total` - Total trials
- `katib_experiment_duration_seconds` - Experiment duration

### Prometheus Alerts

```yaml
- alert: KubeflowPipelineFailed
  expr: kfp_pipeline_run_status{status="Failed"} > 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Kubeflow pipeline failed"

- alert: KatibExperimentStalled
  expr: |
    time() - katib_experiment_last_update_timestamp > 3600
  labels:
    severity: warning
  annotations:
    summary: "Katib experiment has not updated in 1 hour"
```

## Best Practices

### Pipeline Design

1. **Use components**: Break pipelines into reusable components
2. **Version pipelines**: Tag pipeline versions in Git
3. **Parameterize**: Use pipeline parameters for flexibility
4. **Cache steps**: Enable caching for expensive operations
5. **Error handling**: Add retry logic and failure notifications

### Hyperparameter Tuning

1. **Start small**: Begin with grid/random search
2. **Use parallelism**: Set `parallelTrialCount` appropriately
3. **Set budgets**: Use `maxTrialCount` to limit compute
4. **Early stopping**: Use Hyperband for faster results
5. **Log everything**: Send all metrics to MLflow

### Resource Management

1. **Set limits**: Define CPU/memory/GPU limits
2. **Use node selectors**: Target specific node pools
3. **Enable autoscaling**: Use HPA for pipeline components
4. **Clean up**: Delete old pipeline runs and trials

## Troubleshooting

### Pipeline Won't Start

```bash
# Check pipeline status
kubectl get pipeline -n kubeflow

# Check pod logs
kubectl logs -n kubeflow -l app=ml-pipeline --tail=100

# Common issues:
# - Insufficient resources
# - Image pull errors
# - Permission issues
```

### Katib Experiment Stuck

```bash
# Check experiment status
kubectl describe experiment <name> -n kubeflow

# Check trial status
kubectl get trials -n kubeflow -l experiment=<name>

# Check trial logs
kubectl logs -n kubeflow <trial-pod-name>
```

### Notebook Won't Connect

```bash
# Check notebook status
kubectl get notebook -n kubeflow

# Check pod status
kubectl describe pod -n kubeflow notebook/<name>

# Port-forward manually
kubectl port-forward -n kubeflow notebook/<name> 8888:8888
```

## Migration Guide

### From Airflow to Kubeflow Pipelines

**When to use Kubeflow Pipelines**:
- ML-specific workflows with complex DAGs
- Need for visual pipeline builder
- Experiment tracking integrated with pipelines
- Advanced ML features (Katib, AutoML)

**When to use Airflow**:
- General data pipelines
- External system integrations
- Cron-based scheduling
- Complex dependencies outside ML

**Hybrid Approach** (Recommended):
- Use Airflow for orchestration
- Trigger Kubeflow Pipelines for ML workflows
- Log everything to MLflow
- Store features in Feast

## Next Steps

1. ✅ Install Kubeflow Pipelines
2. ✅ Install Katib
3. ➡️ Create first ML pipeline
4. ➡️ Run hyperparameter tuning experiment
5. ➡️ Set up notebook servers
6. ➡️ Integrate with MLflow and Feast
7. ➡️ Configure monitoring and alerts

---

**Last Updated**: 2025-10-04
**Status**: Production Ready ✅
