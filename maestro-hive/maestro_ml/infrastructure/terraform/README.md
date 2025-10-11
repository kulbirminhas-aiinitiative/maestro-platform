# Terraform Infrastructure

Terraform configuration for deploying Maestro ML Platform infrastructure on AWS.

## Architecture

- **VPC**: 3 public and 3 private subnets across 3 AZs
- **EKS**: Kubernetes cluster with managed node groups
- **RDS**: PostgreSQL 14 database with multi-AZ
- **ElastiCache**: Redis cluster with automatic failover
- **S3**: Artifact storage with versioning and lifecycle policies

## Prerequisites

- AWS CLI configured
- Terraform >= 1.5
- AWS account with appropriate permissions

## Setup

### 1. Create S3 Backend (One-time)

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://maestro-ml-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket maestro-ml-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name maestro-ml-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 2. Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 3. Review Configuration

```bash
# Check what will be created
terraform plan

# Save plan to file
terraform plan -out=tfplan
```

### 4. Deploy Infrastructure

```bash
# Apply configuration
terraform apply

# Or apply saved plan
terraform apply tfplan
```

Deployment takes approximately 20-30 minutes.

## Configuration

### Variables

Create `terraform.tfvars` file:

```hcl
aws_region  = "us-east-1"
environment = "production"

# EKS Configuration
eks_cluster_version     = "1.28"
eks_node_instance_types = ["t3.medium", "t3.large"]
eks_node_desired_size   = 3
eks_node_min_size       = 2
eks_node_max_size       = 10

# RDS Configuration
rds_instance_class       = "db.t3.medium"
rds_allocated_storage    = 100
rds_max_allocated_storage = 500

# ElastiCache Configuration
elasticache_node_type       = "cache.t3.micro"
elasticache_num_cache_nodes = 2

# S3 Configuration
s3_artifact_bucket_name = "maestro-ml-artifacts-prod"
```

## Post-Deployment

### Configure kubectl

```bash
aws eks update-kubeconfig --region us-east-1 --name maestro-ml
```

### Verify Cluster Access

```bash
kubectl get nodes
kubectl get namespaces
```

### Get Database Credentials

```bash
# Get RDS password from Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id maestro-ml/rds/password \
  --query SecretString \
  --output text | jq -r .password
```

### Update Kubernetes Secrets

Update the `secrets.yaml` file in `../kubernetes/` with:
- RDS endpoint (from Terraform output)
- RDS password (from Secrets Manager)
- S3 bucket name

## Resource Costs (Estimated)

Monthly costs for production environment:

- **EKS Cluster**: $75
- **EKS Nodes** (3x t3.medium): ~$90
- **RDS** (db.t3.medium): ~$70
- **ElastiCache** (2x cache.t3.micro): ~$25
- **NAT Gateways** (3): ~$100
- **S3**: Variable (storage + requests)
- **Data Transfer**: Variable

**Total**: ~$360-400/month (excluding S3 and data transfer)

### Cost Optimization

For development/staging:

```hcl
eks_node_instance_types = ["t3.small"]
eks_node_desired_size   = 2
eks_node_min_size       = 1
eks_node_max_size       = 3

rds_instance_class = "db.t3.micro"
rds_allocated_storage = 20

elasticache_node_type = "cache.t3.micro"
elasticache_num_cache_nodes = 1
```

## Maintenance

### Update Infrastructure

```bash
# Pull latest changes
git pull

# Plan changes
terraform plan

# Apply changes
terraform apply
```

### Scale Node Group

```bash
# Update variables
vim terraform.tfvars

# Apply changes
terraform apply -target=aws_eks_node_group.main
```

### Backup State

```bash
# State is automatically backed up to S3
# To manually backup:
terraform state pull > terraform.tfstate.backup
```

## Troubleshooting

### EKS Cluster Not Accessible

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name maestro-ml

# Check IAM authentication
kubectl get svc
```

### RDS Connection Issues

```bash
# Check security groups
aws ec2 describe-security-groups --group-ids <rds-sg-id>

# Test connection from EKS pod
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql postgresql://maestro:password@<rds-endpoint>:5432/maestro_ml
```

### Cost Overruns

```bash
# Check cost by service
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## Security Best Practices

- ✅ All data encrypted at rest
- ✅ All data encrypted in transit
- ✅ Private subnets for workloads
- ✅ Security groups with least privilege
- ✅ Secrets stored in Secrets Manager
- ✅ IAM roles with minimum permissions
- ✅ VPC endpoints for AWS services (optional)

## Disaster Recovery

### RDS Backup

- Automated daily backups (retention: 7 days)
- Manual snapshots available
- Point-in-time recovery enabled

### Restore from Backup

```bash
# List available snapshots
aws rds describe-db-snapshots --db-instance-identifier maestro-ml-postgres

# Restore from snapshot
terraform import aws_db_instance.main <new-instance-id>
```

## Clean Up

**WARNING**: This will destroy all resources including databases!

```bash
# Disable deletion protection on RDS
aws rds modify-db-instance \
  --db-instance-identifier maestro-ml-postgres \
  --no-deletion-protection

# Destroy infrastructure
terraform destroy
```

## Support

For issues with Terraform configuration:
- Check Terraform logs: `TF_LOG=DEBUG terraform apply`
- Review AWS CloudTrail events
- Check resource-specific logs in CloudWatch
