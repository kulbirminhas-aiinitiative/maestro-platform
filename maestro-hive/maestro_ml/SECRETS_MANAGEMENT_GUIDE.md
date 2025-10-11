# Secrets Management Guide

## Overview

The ML platform uses **External Secrets Operator (ESO)** for production to sync secrets from AWS Secrets Manager, and simple Kubernetes secrets for minikube testing.

## Architecture

```
┌────────────────────────────────────────────────────────┐
│              Secrets Management Flow                    │
└────────────────────────────────────────────────────────┘

Production:
┌──────────────────────┐
│  AWS Secrets Manager │
│                      │
│ • Database passwords │
│ • API keys           │
│ • TLS certificates   │
│ • SSH keys           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ External Secrets     │
│     Operator         │
│                      │
│ • Poll secrets       │
│ • Sync to K8s        │
│ • Auto-rotate        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Kubernetes Secrets  │
│                      │
│ • Mounted as files   │
│ • Env variables      │
│ • Auto-reloaded      │
└──────────────────────┘

Minikube:
┌──────────────────────┐
│  Kubernetes Secrets  │
│  (plaintext YAML)    │
│                      │
│ • Dev credentials    │
│ • No rotation        │
│ • Simple setup       │
└──────────────────────┘
```

## Components

### 1. External Secrets Operator (Production)
- **Purpose**: Sync secrets from external sources to Kubernetes
- **Supported Backends**: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault, GCP Secret Manager
- **Features**: Auto-refresh, rotation, templating

### 2. AWS Secrets Manager (Production)
- **Purpose**: Centralized secret storage with encryption
- **Encryption**: KMS encrypted at rest
- **Access**: IAM-based with IRSA (IAM Roles for Service Accounts)

### 3. Kubernetes Secrets (Minikube)
- **Purpose**: Simple development secrets
- **Warning**: Not encrypted in etcd by default
- **Use**: Development and testing only

## Installation

### Production: External Secrets Operator

```bash
# 1. Install CRDs
kubectl apply -f https://raw.githubusercontent.com/external-secrets/external-secrets/main/deploy/crds/bundle.yaml

# 2. Add Helm repo
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

# 3. Install operator
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace \
  --set installCRDs=false

# 4. Verify installation
kubectl get pods -n external-secrets-system
kubectl get crd | grep external-secrets
```

### Minikube: Simple Secrets

```bash
# Apply development secrets
kubectl apply -f infrastructure/minikube/secrets.yaml

# Verify
kubectl get secrets -n ml-platform
kubectl get secrets -n airflow
kubectl get secrets -n storage
```

## AWS Secrets Manager Setup

### 1. Create IAM Role for IRSA

```bash
# Create IAM policy
cat > external-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecrets"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:ml-platform/*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name ExternalSecretsPolicy \
  --policy-document file://external-secrets-policy.json

# Create IAM role with IRSA
eksctl create iamserviceaccount \
  --name external-secrets-sa \
  --namespace ml-platform \
  --cluster ml-platform-cluster \
  --attach-policy-arn arn:aws:iam::ACCOUNT_ID:policy/ExternalSecretsPolicy \
  --approve
```

### 2. Create Secrets in AWS

```bash
# MLflow database password
aws secretsmanager create-secret \
  --name ml-platform/mlflow/database \
  --description "MLflow database credentials" \
  --secret-string '{"password":"STRONG_PASSWORD_HERE"}'

# MLflow S3 credentials
aws secretsmanager create-secret \
  --name ml-platform/mlflow/s3 \
  --secret-string '{"access_key":"ACCESS_KEY","secret_key":"SECRET_KEY"}'

# Feast database password
aws secretsmanager create-secret \
  --name ml-platform/feast/database \
  --secret-string '{"password":"STRONG_PASSWORD_HERE"}'

# Airflow fernet key
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
aws secretsmanager create-secret \
  --name ml-platform/airflow/fernet \
  --secret-string "{\"key\":\"$FERNET_KEY\"}"

# API keys
aws secretsmanager create-secret \
  --name ml-platform/api-keys \
  --secret-string '{"openai":"sk-...","huggingface":"hf_..."}'
```

### 3. Deploy SecretStore

```bash
# Apply production secrets management
kubectl apply -f infrastructure/kubernetes/secrets-management.yaml

# Verify SecretStore
kubectl get secretstore -n ml-platform
kubectl describe secretstore aws-secrets-manager -n ml-platform
```

### 4. Deploy ExternalSecrets

```bash
# ExternalSecrets will automatically sync
kubectl get externalsecrets -n ml-platform
kubectl get secrets -n ml-platform

# Check sync status
kubectl describe externalsecret mlflow-credentials -n ml-platform
```

## Using Secrets in Deployments

### As Environment Variables

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow
  namespace: ml-platform
spec:
  template:
    spec:
      containers:
      - name: mlflow
        image: mlflow:latest
        env:
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mlflow-credentials
              key: database-password
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: mlflow-credentials
              key: s3-access-key
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: mlflow-credentials
              key: s3-secret-key
```

### As Mounted Files

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: training-job
  namespace: ml-platform
spec:
  template:
    spec:
      containers:
      - name: trainer
        image: training:latest
        volumeMounts:
        - name: api-keys
          mountPath: /secrets
          readOnly: true
      volumes:
      - name: api-keys
        secret:
          secretName: api-keys
          items:
          - key: openai-api-key
            path: openai_key
          - key: huggingface-token
            path: hf_token
```

### In Airflow DAGs

```python
from airflow import DAG
from airflow.kubernetes.secret import Secret

# Define secret
api_key_secret = Secret(
    deploy_type='env',
    deploy_target='OPENAI_API_KEY',
    secret='api-keys',
    key='openai-api-key'
)

# Use in KubernetesPodOperator
train_task = KubernetesPodOperator(
    task_id='train_model',
    namespace='ml-platform',
    image='training:v1.0',
    secrets=[api_key_secret],
    ...
)
```

## Secret Rotation

### Automatic Rotation (Production)

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: rotated-secret
  namespace: ml-platform
spec:
  refreshInterval: 15m  # Check every 15 minutes
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: rotated-secret
    creationPolicy: Owner
  data:
  - secretKey: database-password
    remoteRef:
      key: ml-platform/database
      property: password
```

### Automatic Pod Reload

Install Reloader to auto-restart pods on secret changes:

```bash
# Install Reloader
helm repo add stakater https://stakater.github.io/stakater-charts
helm install reloader stakater/reloader \
  --namespace kube-system \
  --set reloader.watchGlobally=true
```

Annotate deployments:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow
  namespace: ml-platform
  annotations:
    reloader.stakater.com/auto: "true"  # Auto-reload on any secret change
    # OR
    reloader.stakater.com/search: "true"  # Reload on specific secrets
spec:
  ...
```

### Manual Rotation

```bash
# 1. Update secret in AWS
aws secretsmanager update-secret \
  --secret-id ml-platform/mlflow/database \
  --secret-string '{"password":"NEW_PASSWORD"}'

# 2. Force sync (or wait for refreshInterval)
kubectl annotate externalsecret mlflow-credentials \
  force-sync=$(date +%s) \
  -n ml-platform

# 3. Restart pods
kubectl rollout restart deployment mlflow -n ml-platform
```

## Security Best Practices

### Production

1. **Use External Secrets Operator**: Never commit secrets to Git
2. **Enable Encryption**: Enable etcd encryption at rest
3. **Use IRSA**: No static credentials in pods
4. **Least Privilege**: Grant minimal IAM permissions
5. **Audit Access**: Enable CloudTrail for Secrets Manager
6. **Rotate Regularly**: Set up automatic rotation (30-90 days)
7. **Use Strong Passwords**: Generate with `openssl rand -base64 32`
8. **Separate Environments**: Different secrets per env (dev/staging/prod)

### Minikube

1. **Never Use in Production**: Development only
2. **Use Placeholders**: Don't use real credentials
3. **Don't Commit**: Add to .gitignore
4. **Generate Fresh**: Create new secrets for each environment

## Secret Categories

### Database Credentials

```bash
# PostgreSQL
aws secretsmanager create-secret \
  --name ml-platform/postgres/mlflow \
  --secret-string '{"username":"mlflow","password":"STRONG_PASS"}'

# Redis
aws secretsmanager create-secret \
  --name ml-platform/redis/feast \
  --secret-string '{"password":"STRONG_PASS"}'
```

### API Keys

```bash
# External services
aws secretsmanager create-secret \
  --name ml-platform/api-keys \
  --secret-string '{
    "openai": "sk-...",
    "huggingface": "hf_...",
    "github": "ghp_...",
    "wandb": "..."
  }'
```

### TLS Certificates

```bash
# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt

# Store in Secrets Manager
aws secretsmanager create-secret \
  --name ml-platform/tls/ingress \
  --secret-string "{
    \"tls.crt\": \"$(cat tls.crt | base64)\",
    \"tls.key\": \"$(cat tls.key | base64)\"
  }"
```

### SSH Keys

```bash
# Generate SSH key
ssh-keygen -t rsa -b 4096 -f git_deploy_key -N ""

# Store in Secrets Manager
aws secretsmanager create-secret \
  --name ml-platform/git/deploy-key \
  --secret-string "{
    \"private_key\": \"$(cat git_deploy_key | base64)\",
    \"public_key\": \"$(cat git_deploy_key.pub | base64)\"
  }"
```

## Monitoring and Auditing

### CloudTrail Logging

```bash
# Query secret access
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=ml-platform/mlflow/database \
  --max-results 10
```

### Kubernetes Audit

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  verbs: ["get", "list", "watch"]
  resources:
  - group: ""
    resources: ["secrets"]
  namespaces: ["ml-platform", "airflow"]
```

### Prometheus Alerts

```yaml
- alert: SecretSyncFailed
  expr: |
    external_secrets_sync_calls_error > 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "External secret sync failed"
    description: "Secret {{ $labels.name }} failed to sync"

- alert: SecretExpiringSoon
  expr: |
    (aws_secretsmanager_secret_last_rotation_timestamp + 7776000) < time()
  labels:
    severity: warning
  annotations:
    summary: "Secret expiring soon"
    description: "Secret {{ $labels.secret_name }} hasn't been rotated in 90 days"
```

## Troubleshooting

### ExternalSecret Not Syncing

```bash
# Check ExternalSecret status
kubectl get externalsecret mlflow-credentials -n ml-platform -o yaml

# Check operator logs
kubectl logs -n external-secrets-system deployment/external-secrets

# Verify IRSA
kubectl describe sa external-secrets-sa -n ml-platform
# Should have: eks.amazonaws.com/role-arn annotation

# Test IAM permissions
aws secretsmanager get-secret-value --secret-id ml-platform/mlflow/database
```

### Secret Not Found

```bash
# Verify secret exists in AWS
aws secretsmanager describe-secret --secret-id ml-platform/mlflow/database

# Check SecretStore
kubectl get secretstore -n ml-platform
kubectl describe secretstore aws-secrets-manager -n ml-platform

# Force re-sync
kubectl delete externalsecret mlflow-credentials -n ml-platform
kubectl apply -f infrastructure/kubernetes/secrets-management.yaml
```

### Pod Cannot Access Secret

```bash
# Verify secret exists
kubectl get secret mlflow-credentials -n ml-platform

# Check secret contents (base64 decode)
kubectl get secret mlflow-credentials -n ml-platform -o jsonpath='{.data.database-password}' | base64 -d

# Check pod events
kubectl describe pod <pod-name> -n ml-platform
# Look for: "Error: secret 'mlflow-credentials' not found"
```

## Migration Guide

### From Hardcoded Secrets to External Secrets

1. **Identify secrets** in deployments:
```bash
grep -r "password:" infrastructure/
grep -r "apiKey:" infrastructure/
```

2. **Create secrets in AWS**:
```bash
aws secretsmanager create-secret --name ml-platform/service/credential --secret-string '...'
```

3. **Create ExternalSecret**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: service-credentials
spec:
  secretStoreRef:
    name: aws-secrets-manager
  data:
  - secretKey: password
    remoteRef:
      key: ml-platform/service/credential
```

4. **Update deployment** to use secret:
```yaml
env:
- name: PASSWORD
  valueFrom:
    secretKeyRef:
      name: service-credentials
      key: password
```

5. **Test** and deploy

## Next Steps

1. ✅ Install External Secrets Operator
2. ✅ Create AWS Secrets Manager secrets
3. ✅ Deploy SecretStores and ExternalSecrets
4. ➡️ Migrate all hardcoded secrets
5. ➡️ Set up secret rotation policies
6. ➡️ Configure audit logging
7. ➡️ Implement automated rotation

---

**Last Updated**: 2025-10-04
**Status**: Production Ready ✅
