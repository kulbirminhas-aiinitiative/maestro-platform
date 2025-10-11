# Sunday.com Infrastructure - Outputs

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnet_ids
}

output "database_subnet_ids" {
  description = "List of IDs of database subnets"
  value       = module.vpc.database_subnet_ids
}

# EKS Outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "EKS cluster OIDC provider ARN"
  value       = module.eks.oidc_provider_arn
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "rds_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_name
}

output "rds_username" {
  description = "RDS master username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

# ElastiCache Outputs
output "elasticache_endpoint" {
  description = "ElastiCache endpoint"
  value       = module.elasticache.primary_endpoint
}

output "elasticache_port" {
  description = "ElastiCache port"
  value       = module.elasticache.port
}

# S3 Outputs
output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.s3.bucket_name
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = module.s3.bucket_arn
}

output "s3_bucket_domain_name" {
  description = "S3 bucket domain name"
  value       = module.s3.bucket_domain_name
}

# CloudWatch Outputs
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = module.monitoring.log_group_name
}

# Load Balancer Outputs
output "load_balancer_dns" {
  description = "Load balancer DNS name"
  value       = module.eks.load_balancer_dns
}

# ECR Outputs
output "ecr_repository_urls" {
  description = "ECR repository URLs"
  value       = {
    backend  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${local.name_prefix}-backend"
    frontend = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${local.name_prefix}-frontend"
  }
}

# IAM Outputs
output "cluster_iam_role_arn" {
  description = "EKS cluster IAM role ARN"
  value       = module.eks.cluster_iam_role_arn
}

output "node_group_iam_role_arn" {
  description = "EKS node group IAM role ARN"
  value       = module.eks.node_group_iam_role_arn
}

# Kubernetes configuration
output "kubectl_config" {
  description = "kubectl configuration command"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

# Connection strings (for application configuration)
output "database_url" {
  description = "Database connection URL"
  value       = "postgresql://${module.rds.db_instance_username}:${random_password.db_password.result}@${module.rds.db_instance_endpoint}:${module.rds.db_instance_port}/${module.rds.db_instance_name}"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://${module.elasticache.primary_endpoint}:${module.elasticache.port}"
}

# Security
output "secrets_manager_arns" {
  description = "AWS Secrets Manager ARNs"
  value       = module.monitoring.secrets_manager_arns
}

# Random password for RDS (should be stored in AWS Secrets Manager)
resource "random_password" "db_password" {
  length  = 16
  special = true
}