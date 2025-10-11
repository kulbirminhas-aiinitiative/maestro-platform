# CI/CD Pipelines

GitHub Actions workflows for Maestro ML Platform.

## Workflows

### CI Pipeline (`ci.yml`)

Runs on every push and pull request to `main` and `develop` branches.

**Jobs:**
1. **Lint** - Code quality checks
   - Black (code formatting)
   - Flake8 (linting)
   - MyPy (type checking)

2. **Test** - Unit and integration tests
   - pytest with PostgreSQL and Redis
   - Code coverage reporting
   - Upload to Codecov

3. **Security** - Vulnerability scanning
   - Trivy filesystem scan
   - Upload results to GitHub Security

4. **Build** - Docker image build
   - Builds container image
   - Caches layers for faster builds
   - No push (test build only)

### CD Pipeline (`cd.yml`)

Runs on push to `main` branch or version tags.

**Jobs:**
1. **Deploy** - Production deployment
   - Build and push to AWS ECR
   - Update kubeconfig for EKS
   - Run database migrations
   - Deploy to Kubernetes
   - Verify rollout
   - Run smoke tests
   - Notify via Slack

## Setup

### Required Secrets

Configure these secrets in GitHub repository settings:

```
AWS_ACCESS_KEY_ID          # AWS IAM access key
AWS_SECRET_ACCESS_KEY      # AWS IAM secret key
DATABASE_URL               # PostgreSQL connection string
SLACK_WEBHOOK              # Slack notification webhook (optional)
```

### AWS IAM Permissions

The AWS IAM user needs these permissions:
- ECR: Push images
- EKS: Update kubeconfig, deploy
- S3: Access for artifacts (if needed)

Example IAM policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    }
  ]
}
```

### Branch Protection

Recommended branch protection rules for `main`:

- ✅ Require pull request reviews (1 approver)
- ✅ Require status checks to pass
  - lint
  - test
  - build
- ✅ Require branches to be up to date
- ✅ Restrict who can push to matching branches

## Local Testing

### Run CI Checks Locally

```bash
# Lint
black --check .
flake8 .
mypy maestro_ml --ignore-missing-imports

# Tests
docker-compose up -d postgres redis
pytest tests/ -v --cov=maestro_ml

# Build
docker build -t maestro-ml/api:local .
```

### Test with Act

Run GitHub Actions locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run CI workflow
act push

# Run specific job
act -j test
```

## Deployment Process

### Automatic Deployment

1. Merge PR to `main` branch
2. CI pipeline runs automatically
3. If all checks pass, CD pipeline deploys to production
4. Deployment includes:
   - Docker image build and push
   - Database migrations
   - Rolling update to EKS
   - Smoke tests
   - Slack notification

### Manual Deployment

Trigger deployment manually via GitHub Actions UI:

1. Go to Actions tab
2. Select "CD Pipeline"
3. Click "Run workflow"
4. Select branch and run

### Rollback

If deployment fails:

```bash
# Rollback Kubernetes deployment
kubectl rollout undo deployment/maestro-api -n maestro-ml

# Or rollback to specific revision
kubectl rollout history deployment/maestro-api -n maestro-ml
kubectl rollout undo deployment/maestro-api --to-revision=<N> -n maestro-ml
```

## Monitoring

### View Logs

```bash
# View workflow logs in GitHub UI
# Or via CLI
gh run list
gh run view <run-id>
gh run view <run-id> --log
```

### Check Deployment Status

```bash
kubectl get deployments -n maestro-ml
kubectl get pods -n maestro-ml
kubectl logs -f deployment/maestro-api -n maestro-ml
```

## Troubleshooting

### CI Failures

**Lint failures:**
```bash
# Auto-fix formatting
black .

# Check specific errors
flake8 . --show-source
```

**Test failures:**
```bash
# Run tests locally
docker-compose up -d postgres redis
pytest tests/ -v -s  # -s shows print statements
```

### CD Failures

**Image push failed:**
- Check AWS credentials
- Verify ECR repository exists
- Check IAM permissions

**Migration failed:**
```bash
# Check migration logs
kubectl logs job/maestro-migrate-<sha> -n maestro-ml

# Rollback migration
kubectl exec -it deployment/maestro-api -n maestro-ml -- alembic downgrade -1
```

**Deployment timeout:**
```bash
# Check pod status
kubectl describe pod <pod-name> -n maestro-ml

# Check events
kubectl get events -n maestro-ml --sort-by='.lastTimestamp'
```

## Best Practices

1. **Always run tests locally before pushing**
2. **Keep CI pipeline fast** (<10 minutes)
3. **Use caching** for dependencies and Docker layers
4. **Monitor pipeline success rate**
5. **Set up Slack notifications** for failures
6. **Review security scan results** regularly
7. **Keep secrets secure** - never commit them
8. **Test deployments in staging** before production
