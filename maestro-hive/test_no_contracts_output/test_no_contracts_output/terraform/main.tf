# Main Terraform configuration for Simple Test Requirement infrastructure
# This is a template that can be adapted for AWS, Azure, or GCP

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

  # Remote state configuration
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "simple-test-requirement/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# Local variables
locals {
  cluster_name = "${var.project_name}-${var.environment}-cluster"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name        = var.project_name
  environment         = var.environment
  vpc_cidr            = var.vpc_cidr
  availability_zones  = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets     = var.private_subnets
  public_subnets      = var.public_subnets
  enable_nat_gateway  = true
  single_nat_gateway  = var.environment == "dev" ? true : false
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = local.common_tags
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"

  cluster_name    = local.cluster_name
  cluster_version = var.eks_cluster_version
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  # Node groups configuration
  node_groups = {
    application = {
      desired_size   = var.app_node_group_desired_size
      min_size       = var.app_node_group_min_size
      max_size       = var.app_node_group_max_size
      instance_types = var.app_node_instance_types
      capacity_type  = "ON_DEMAND"
      disk_size      = 50

      labels = {
        role = "application"
      }

      tags = merge(
        local.common_tags,
        {
          Name = "${local.cluster_name}-application-node"
        }
      )
    }

    system = {
      desired_size   = 2
      min_size       = 2
      max_size       = 4
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      disk_size      = 30

      labels = {
        role = "system"
      }

      taints = [
        {
          key    = "CriticalAddonsOnly"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]

      tags = merge(
        local.common_tags,
        {
          Name = "${local.cluster_name}-system-node"
        }
      )
    }
  }

  tags = local.common_tags
}

# RDS Database Module
module "rds" {
  source = "./modules/rds"

  identifier     = "${var.project_name}-${var.environment}-db"
  engine         = "postgres"
  engine_version = "16.1"
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  # Password should be managed via AWS Secrets Manager
  manage_master_user_password = true

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  allowed_cidr_blocks = module.vpc.private_subnets_cidr_blocks

  # High availability configuration
  multi_az               = var.environment == "production" ? true : false
  backup_retention_period = var.environment == "production" ? 30 : 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  # Performance Insights
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled    = true
  performance_insights_retention_period = 7

  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  tags = local.common_tags
}

# ElastiCache Redis Module
module "redis" {
  source = "./modules/redis"

  cluster_id           = "${var.project_name}-${var.environment}-redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = var.environment == "production" ? 3 : 1
  parameter_group_name = "default.redis7"

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  allowed_cidr_blocks = module.vpc.private_subnets_cidr_blocks

  # High availability
  automatic_failover_enabled = var.environment == "production" ? true : false
  multi_az_enabled          = var.environment == "production" ? true : false

  # Security
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true

  # Maintenance
  maintenance_window = "Sun:05:00-Sun:06:00"
  snapshot_window    = "03:00-04:00"
  snapshot_retention_limit = var.environment == "production" ? 7 : 1

  tags = local.common_tags
}

# S3 Bucket for Application Assets
module "s3" {
  source = "./modules/s3"

  bucket_name = "${var.project_name}-${var.environment}-assets"

  # Versioning
  versioning_enabled = true

  # Lifecycle rules
  lifecycle_rules = [
    {
      id      = "delete-old-versions"
      enabled = true
      noncurrent_version_expiration = {
        days = 90
      }
    },
    {
      id      = "transition-to-ia"
      enabled = true
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        }
      ]
    }
  ]

  # Encryption
  encryption_enabled = true
  kms_master_key_id  = aws_kms_key.s3.arn

  # Access logging
  logging_enabled = true
  logging_target_bucket = "${var.project_name}-${var.environment}-logs"
  logging_target_prefix = "s3-access-logs/"

  # CORS configuration for web application
  cors_rules = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "HEAD"]
      allowed_origins = ["https://${var.domain_name}"]
      expose_headers  = ["ETag"]
      max_age_seconds = 3000
    }
  ]

  tags = local.common_tags
}

# CloudFront CDN
resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name}-${var.environment} CDN"
  default_root_object = "index.html"
  price_class         = var.environment == "production" ? "PriceClass_All" : "PriceClass_100"

  origin {
    domain_name = module.s3.bucket_regional_domain_name
    origin_id   = "S3-${module.s3.bucket_id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.cdn.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${module.s3.bucket_id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.common_tags
}

resource "aws_cloudfront_origin_access_identity" "cdn" {
  comment = "${var.project_name}-${var.environment} CDN OAI"
}

# KMS Keys for Encryption
resource "aws_kms_key" "s3" {
  description             = "${var.project_name}-${var.environment} S3 encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = local.common_tags
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.project_name}-${var.environment}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# IAM Role for RDS Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-${var.environment}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Security Group for Application Load Balancer
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-${var.environment}-alb-"
  description = "Security group for Application Load Balancer"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-alb-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Application Load Balancer
resource "aws_lb" "application" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = var.environment == "production" ? true : false
  enable_http2              = true
  enable_cross_zone_load_balancing = true

  access_logs {
    bucket  = "${var.project_name}-${var.environment}-logs"
    prefix  = "alb-access-logs"
    enabled = true
  }

  tags = local.common_tags
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.s3.bucket_id
}

output "cloudfront_distribution_domain" {
  description = "CloudFront distribution domain"
  value       = aws_cloudfront_distribution.cdn.domain_name
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.application.dns_name
}
