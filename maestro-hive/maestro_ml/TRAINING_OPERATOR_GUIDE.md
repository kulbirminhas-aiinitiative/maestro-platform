# KubeFlow Training Operator Guide

**Version**: 1.0
**Date**: 2025-10-04
**Component**: Phase 2 - Training Infrastructure

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Supported Frameworks](#supported-frameworks)
5. [Training Job Templates](#training-job-templates)
6. [Running Training Jobs](#running-training-jobs)
7. [MLflow Integration](#mlflow-integration)
8. [Resource Management](#resource-management)
9. [Monitoring and Debugging](#monitoring-and-debugging)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Examples](#examples)

---

## Overview

The KubeFlow Training Operator enables distributed machine learning training on Kubernetes. It supports multiple ML frameworks and integrates seamlessly with the ML platform's existing infrastructure (MLflow, Feast, Prometheus).

### Key Features

- **Multi-framework support**: TensorFlow, PyTorch, MXNet, XGBoost, PaddlePaddle
- **Distributed training**: Multi-node, multi-GPU training
- **MLflow integration**: Automatic experiment tracking
- **Resource management**: GPU/CPU allocation, quotas, priorities
- **Fault tolerance**: Automatic retries, checkpointing
- **Monitoring**: Prometheus metrics, Grafana dashboards

### When to Use

- **Distributed training**: Model too large for single GPU/node
- **Hyperparameter tuning**: Parallel trial execution
- **Production pipelines**: Automated, repeatable training
- **Team collaboration**: Shared training infrastructure

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│            KubeFlow Training Operator                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  TFJob   │  │PyTorchJob│  │  MXJob   │  ...     │
│  │Controller│  │Controller│  │Controller│          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Master  │    │ Worker  │    │ Worker  │
    │  Pod    │    │  Pod    │    │  Pod    │
    └────┬────┘    └────┬────┘    └────┬────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Shared Storage  │
              │  (PVC, S3, etc)  │
              └──────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ MLflow  │    │  Feast  │    │Prometheus│
    └─────────┘    └─────────┘    └─────────┘
```

---

## Installation

### Prerequisites

- Kubernetes cluster (minikube or production)
- kubectl configured
- Phase 1 infrastructure deployed (MLflow, Feast, etc.)

### Minikube Installation

```bash
# Deploy Training Operator
kubectl apply -f infrastructure/minikube/training-operator.yaml

# Verify deployment
kubectl get pods -n kubeflow-training
kubectl get crd | grep kubeflow.org

# Check operator logs
kubectl logs -n kubeflow-training deployment/training-operator
```

### Production Installation

```bash
# Deploy Training Operator
kubectl apply -f infrastructure/kubernetes/training-operator.yaml

# Verify deployment
kubectl get pods -n kubeflow-training -o wide
kubectl get svc -n kubeflow-training

# Check ServiceMonitor for Prometheus
kubectl get servicemonitor -n kubeflow-training
```

### Verification

```bash
# List available CRDs
kubectl get crd | grep kubeflow.org

# Expected output:
# tfjobs.kubeflow.org
# pytorchjobs.kubeflow.org
# mxjobs.kubeflow.org
# xgboostjobs.kubeflow.org

# Test with example job
kubectl apply -f training/examples/mnist-tensorflow.yaml

# Check job status
kubectl get tfjobs -n kubeflow-training
```

---

## Supported Frameworks

### TensorFlow (TFJob)

**Strategies**:
- MultiWorkerMirroredStrategy (data parallelism)
- ParameterServerStrategy (parameter server)
- CollectiveAllReduceStrategy

**Example**:
```yaml
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: tensorflow-training
spec:
  tfReplicaSpecs:
    Chief:
      replicas: 1
    Worker:
      replicas: 2
    PS:  # Parameter server (optional)
      replicas: 1
```

### PyTorch (PyTorchJob)

**Strategies**:
- DistributedDataParallel (DDP) - recommended
- DataParallel (DP)
- Elastic training (dynamic worker scaling)

**Example**:
```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: pytorch-training
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
    Worker:
      replicas: 2
  elasticPolicy:  # Optional
    minReplicas: 1
    maxReplicas: 4
```

### MXNet (MXJob)

**Example**:
```yaml
apiVersion: kubeflow.org/v1
kind: MXJob
metadata:
  name: mxnet-training
spec:
  mxReplicaSpecs:
    Scheduler:
      replicas: 1
    Server:
      replicas: 2
    Worker:
      replicas: 2
```

### XGBoost (XGBoostJob)

**Example**:
```yaml
apiVersion: kubeflow.org/v1
kind: XGBoostJob
metadata:
  name: xgboost-training
spec:
  xgbReplicaSpecs:
    Master:
      replicas: 1
    Worker:
      replicas: 2
```

---

## Training Job Templates

### Using Templates

Templates are located in `training/templates/`:
- `tensorflow-training-job.yaml` - TensorFlow distributed training
- `pytorch-training-job.yaml` - PyTorch DDP training
- `generic-training-job.yaml` - Generic Python training

**Template Variables** (replace before applying):
```yaml
{{ .JobName }}            # Job name
{{ .Namespace }}          # Kubernetes namespace
{{ .ExperimentName }}     # MLflow experiment
{{ .ModelName }}          # Model name for registry
{{ .Epochs }}             # Number of epochs
{{ .BatchSize }}          # Batch size
{{ .LearningRate }}       # Learning rate
{{ .WorkerReplicas }}     # Number of workers
{{ .CPURequest }}         # CPU request
{{ .MemoryRequest }}      # Memory request
{{ .GPUs }}               # GPUs per replica
```

**Example substitution**:
```bash
# Using sed
sed 's/{{ .JobName }}/my-training-job/g' \
    training/templates/tensorflow-training-job.yaml | \
sed 's/{{ .ExperimentName }}/my-experiment/g' | \
kubectl apply -f -

# Using envsubst
export JobName=my-training-job
export ExperimentName=my-experiment
envsubst < training/templates/tensorflow-training-job.yaml | kubectl apply -f -
```

---

## Running Training Jobs

### Step 1: Prepare Training Code

Create a ConfigMap with your training script:

```bash
kubectl create configmap my-training-code \
  --from-file=train.py=my_train_script.py \
  -n kubeflow-training
```

### Step 2: Create Training Job

```bash
# Apply job configuration
kubectl apply -f my-training-job.yaml

# Verify job created
kubectl get tfjobs -n kubeflow-training
# or
kubectl get pytorchjobs -n kubeflow-training
```

### Step 3: Monitor Training

```bash
# Watch job status
kubectl get tfjobs my-training-job -n kubeflow-training -w

# View logs
kubectl logs -n kubeflow-training my-training-job-chief-0 -f

# Check all pods
kubectl get pods -n kubeflow-training -l job-name=my-training-job
```

### Step 4: Check Results

```bash
# View MLflow experiments
# http://<mlflow-url>:30500

# Check metrics in Prometheus
# http://<prometheus-url>:30503

# View model in registry
mlflow models list --name my-model
```

---

## MLflow Integration

### Automatic Tracking

Training jobs automatically log to MLflow when environment variables are set:

```yaml
env:
- name: MLFLOW_TRACKING_URI
  value: "http://mlflow.ml-platform.svc.cluster.local:5000"
- name: MLFLOW_EXPERIMENT_NAME
  value: "my-experiment"
- name: MLFLOW_RUN_NAME
  value: "training-run-1"
```

### Training Script Integration

**Python code**:
```python
import mlflow
import os

# MLflow automatically configured via env vars
mlflow.set_tracking_uri(os.environ['MLFLOW_TRACKING_URI'])
mlflow.set_experiment(os.environ['MLFLOW_EXPERIMENT_NAME'])

with mlflow.start_run(run_name=os.environ.get('MLFLOW_RUN_NAME')):
    # Log parameters
    mlflow.log_params({
        'learning_rate': 0.001,
        'batch_size': 32,
        'epochs': 10
    })

    # Training loop
    for epoch in range(epochs):
        # ... train ...
        mlflow.log_metric('train_loss', loss, step=epoch)

    # Log model
    mlflow.pytorch.log_model(model, "model")
```

### Distributed Training Considerations

**Only log from rank 0** (master/chief):

```python
# TensorFlow
strategy = tf.distribute.MultiWorkerMirroredStrategy()
task_type = strategy.cluster_resolver.task_type
task_id = strategy.cluster_resolver.task_id

if task_type == 'chief' or (task_type == 'worker' and task_id == 0):
    mlflow.log_metric('loss', loss)

# PyTorch
import torch.distributed as dist
if dist.get_rank() == 0:
    mlflow.log_metric('loss', loss)
```

---

## Resource Management

### Resource Requests and Limits

**Best practices**:
- Set requests = expected usage
- Set limits = max allowed usage
- Leave headroom for system processes

```yaml
resources:
  requests:
    cpu: "2"          # Guaranteed CPU
    memory: "4Gi"     # Guaranteed memory
  limits:
    cpu: "4"          # Max CPU
    memory: "8Gi"     # Max memory
    nvidia.com/gpu: "1"  # GPUs (if available)
```

### Resource Quotas

Minikube quotas (from training-operator.yaml):
```yaml
# Max resources for all training jobs
requests.cpu: "8"
requests.memory: "16Gi"
limits.cpu: "12"
limits.memory: "24Gi"

# Max concurrent jobs
count/tfjobs.kubeflow.org: "3"
count/pytorchjobs.kubeflow.org: "3"
```

### GPU Allocation

**Single GPU**:
```yaml
resources:
  limits:
    nvidia.com/gpu: "1"
```

**Multi-GPU (data parallel)**:
```yaml
resources:
  limits:
    nvidia.com/gpu: "2"  # 2 GPUs per pod
```

**GPU affinity** (specific GPU):
```yaml
nodeSelector:
  gpu-type: nvidia-a100
```

### Priority and Preemption

**Create PriorityClasses**:
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: training-high-priority
value: 1000
globalDefault: false
description: "High priority for critical training jobs"
```

**Use in training job**:
```yaml
spec:
  template:
    spec:
      priorityClassName: training-high-priority
```

---

## Monitoring and Debugging

### Prometheus Metrics

Training Operator exposes metrics at `:8080/metrics`:

- `training_operator_jobs_created_total` - Jobs created
- `training_operator_jobs_failed_total` - Jobs failed
- `training_operator_jobs_succeeded_total` - Jobs succeeded
- `training_operator_jobs_running_duration_seconds` - Job duration

**Query examples**:
```promql
# Job success rate
rate(training_operator_jobs_succeeded_total[5m]) /
rate(training_operator_jobs_created_total[5m])

# Average job duration
histogram_quantile(0.95,
  rate(training_operator_jobs_running_duration_seconds_bucket[5m])
)

# Failed jobs
sum(training_operator_jobs_failed_total) by (job_type)
```

### Grafana Dashboard

Import dashboard for training jobs:
- Jobs created/succeeded/failed
- Job duration histogram
- Resource utilization
- Active training jobs

### Logging

**View operator logs**:
```bash
kubectl logs -n kubeflow-training deployment/training-operator -f
```

**View training job logs**:
```bash
# TensorFlow
kubectl logs -n kubeflow-training <job-name>-chief-0 -f
kubectl logs -n kubeflow-training <job-name>-worker-0 -f

# PyTorch
kubectl logs -n kubeflow-training <job-name>-master-0 -f
kubectl logs -n kubeflow-training <job-name>-worker-0 -f
```

**Centralized logging** (Loki):
```bash
# Query in Grafana
{namespace="kubeflow-training", app="training-job"} |= "ERROR"
{namespace="kubeflow-training", job=~".*-chief-.*"} |= "epoch"
```

### Debugging

**Job stuck in pending**:
```bash
# Check pod status
kubectl describe pod <pod-name> -n kubeflow-training

# Common issues:
# - Insufficient resources
# - Image pull errors
# - Node selector mismatch
```

**Job failing**:
```bash
# Check events
kubectl get events -n kubeflow-training --sort-by='.lastTimestamp'

# Check pod logs
kubectl logs <pod-name> -n kubeflow-training --previous

# Common issues:
# - Code errors in training script
# - OOM (out of memory)
# - NCCL/MPI communication failures
```

**Job not completing**:
```bash
# Check if pods are running
kubectl get pods -n kubeflow-training -l job-name=<job-name>

# Check if workers are communicating
kubectl exec -it <chief-pod> -n kubeflow-training -- netstat -tuln
```

---

## Best Practices

### 1. Resource Efficiency

- **Right-size resources**: Profile jobs first, then set appropriate limits
- **Use node affinity**: Place jobs on appropriate nodes (CPU vs GPU)
- **Enable autoscaling**: Scale workers based on queue depth
- **Set timeouts**: Use `activeDeadlineSeconds` to prevent stuck jobs

### 2. Data Management

- **Use shared storage**: PVC, S3, or NFS for datasets
- **Cache datasets**: Download once, mount to all pods
- **Shard data**: Distribute data across workers for parallel loading
- **Streaming**: Use data streaming for large datasets

### 3. Fault Tolerance

- **Checkpointing**: Save checkpoints regularly
- **Retry policy**: Set `backoffLimit` for automatic retries
- **Graceful shutdown**: Handle SIGTERM for cleanup
- **Health checks**: Implement liveness/readiness probes

### 4. Training Optimization

- **Gradient accumulation**: Simulate larger batch sizes
- **Mixed precision**: Use fp16/bf16 for faster training
- **Learning rate scaling**: Scale LR with number of workers
- **Warmup**: Use learning rate warmup for stable convergence

### 5. Experiment Tracking

- **Consistent naming**: Use predictable experiment/run names
- **Tag jobs**: Add metadata tags for filtering
- **Log everything**: Parameters, metrics, artifacts
- **Version control**: Track code version in MLflow

### 6. Security

- **Use secrets**: Store credentials in Kubernetes secrets
- **Network policies**: Restrict pod-to-pod communication
- **RBAC**: Limit who can create training jobs
- **Image scanning**: Scan container images for vulnerabilities

---

## Troubleshooting

### Common Issues

#### 1. "No resources available"

**Symptoms**: Pods stuck in Pending
**Cause**: Insufficient CPU/memory/GPU
**Solution**:
```bash
# Check available resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# Reduce resource requests or add nodes
```

#### 2. "ImagePullBackOff"

**Symptoms**: Pods can't pull container image
**Cause**: Image doesn't exist or auth failure
**Solution**:
```bash
# Check image exists
docker pull <image-name>

# Add image pull secret if private registry
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<user> \
  --docker-password=<pass>
```

#### 3. "OOMKilled"

**Symptoms**: Pods killed due to out of memory
**Cause**: Memory limit too low
**Solution**:
```yaml
# Increase memory limit
resources:
  limits:
    memory: "16Gi"  # Increase from 8Gi
```

#### 4. "NCCL/MPI timeout"

**Symptoms**: Distributed training hangs
**Cause**: Network communication issues
**Solution**:
```yaml
# Use gloo backend for CPU or debugging
env:
- name: NCCL_DEBUG
  value: "INFO"
- name: NCCL_TIMEOUT
  value: "3600"  # Increase timeout
```

#### 5. "Job never completes"

**Symptoms**: Job runs but never finishes
**Cause**: Training script doesn't exit properly
**Solution**:
```python
# Ensure script exits after training
if __name__ == '__main__':
    train()
    sys.exit(0)  # Explicit exit
```

### Debug Commands

```bash
# Get job details
kubectl describe tfjob <job-name> -n kubeflow-training

# Get pod details
kubectl describe pod <pod-name> -n kubeflow-training

# Get logs
kubectl logs <pod-name> -n kubeflow-training --previous

# Execute command in pod
kubectl exec -it <pod-name> -n kubeflow-training -- /bin/bash

# Check TF_CONFIG (for TensorFlow)
kubectl exec <pod-name> -n kubeflow-training -- printenv TF_CONFIG

# Check distributed env vars (for PyTorch)
kubectl exec <pod-name> -n kubeflow-training -- printenv | grep -E "MASTER|RANK|WORLD"
```

---

## Examples

### Example 1: MNIST TensorFlow (Distributed)

See `training/examples/mnist-tensorflow.yaml`

**Features**:
- MultiWorkerMirroredStrategy
- MLflow logging
- 2-node training (chief + worker)

**Deploy**:
```bash
kubectl apply -f training/examples/mnist-tensorflow.yaml
kubectl logs -n kubeflow-training mnist-tensorflow-training-chief-0 -f
```

### Example 2: CIFAR-10 PyTorch (DDP)

See `training/examples/cifar10-pytorch.yaml`

**Features**:
- DistributedDataParallel
- Data augmentation
- Cosine annealing LR
- MLflow logging

**Deploy**:
```bash
kubectl apply -f training/examples/cifar10-pytorch.yaml
kubectl logs -n kubeflow-training cifar10-pytorch-training-master-0 -f
```

### Example 3: Scikit-learn (Single Node)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sklearn-training
  namespace: kubeflow-training
spec:
  template:
    spec:
      containers:
      - name: training
        image: python:3.11-slim
        command: ["python3", "/app/train_sklearn.py"]
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow.ml-platform.svc.cluster.local:5000"
        volumeMounts:
        - name: code
          mountPath: /app
      volumes:
      - name: code
        configMap:
          name: sklearn-training-code
      restartPolicy: Never
```

### Example 4: Elastic PyTorch Training

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: elastic-pytorch-training
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
    Worker:
      replicas: 2
  elasticPolicy:
    minReplicas: 1      # Scale down to 1
    maxReplicas: 4      # Scale up to 4
    maxRestarts: 3      # Max restarts on failure
    rdzvBackend: c10d   # Rendezvous backend
```

---

## Next Steps

1. **Hyperparameter Tuning**: Integrate with Optuna (see Phase 2 plan)
2. **Model Governance**: Add lineage tracking and approval workflows
3. **A/B Testing**: Deploy champion vs challenger models
4. **Drift Detection**: Monitor data and model drift
5. **Auto-scaling**: Scale training based on queue depth

---

## References

- [KubeFlow Training Operator Docs](https://www.kubeflow.org/docs/components/training/)
- [TensorFlow Distributed Training](https://www.tensorflow.org/guide/distributed_training)
- [PyTorch Distributed Tutorial](https://pytorch.org/tutorials/intermediate/dist_tuto.html)
- [MLflow Tracking](https://mlflow.org/docs/latest/tracking.html)
- [Phase 2 Plan](PHASE2_PLAN.md)

---

**Last Updated**: 2025-10-04
**Maintained by**: ML Platform Team
