terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "user-management/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "user-management-api"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  environment         = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  private_subnets    = var.private_subnets
  public_subnets     = var.public_subnets
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"

  environment        = var.environment
  cluster_name       = "${var.project_name}-${var.environment}"
  cluster_version    = var.eks_cluster_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_groups        = var.node_groups
}

# RDS Database Module
module "rds" {
  source = "./modules/rds"

  environment          = var.environment
  db_name              = var.db_name
  db_instance_class    = var.db_instance_class
  db_allocated_storage = var.db_allocated_storage
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  allowed_security_groups = [module.eks.cluster_security_group_id]
}

# ElastiCache Redis Module
module "redis" {
  source = "./modules/redis"

  environment             = var.environment
  node_type               = var.redis_node_type
  num_cache_nodes         = var.redis_num_nodes
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  allowed_security_groups = [module.eks.cluster_security_group_id]
}

# S3 Bucket for Application Assets
resource "aws_s3_bucket" "app_assets" {
  bucket = "${var.project_name}-${var.environment}-assets"
}

resource "aws_s3_bucket_versioning" "app_assets" {
  bucket = aws_s3_bucket.app_assets.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "app_assets" {
  bucket = aws_s3_bucket.app_assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/eks/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days
}

# IAM Role for Application
resource "aws_iam_role" "app_role" {
  name = "${var.project_name}-${var.environment}-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = module.eks.oidc_provider_arn
        }
        Condition = {
          StringEquals = {
            "${module.eks.oidc_provider}:sub" = "system:serviceaccount:user-management:user-mgmt-api-sa"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app_s3_policy" {
  role       = aws_iam_role.app_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# Secrets Manager for sensitive data
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "${var.project_name}-${var.environment}-secrets"

  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    database_password = random_password.db_password.result
    secret_key        = random_password.secret_key.result
  })
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "random_password" "secret_key" {
  length  = 64
  special = true
}
