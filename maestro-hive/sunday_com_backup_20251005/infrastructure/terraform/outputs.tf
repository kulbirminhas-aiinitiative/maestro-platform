# Outputs for Sunday.com Infrastructure

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

# EKS Outputs
output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.main.arn
}

output "eks_cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_security_group.eks_cluster.id
}

output "eks_cluster_version" {
  description = "The Kubernetes version for the EKS cluster"
  value       = aws_eks_cluster.main.version
}

output "eks_cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

output "eks_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

output "eks_node_group_arn" {
  description = "Amazon Resource Name (ARN) of the EKS Node Group"
  value       = aws_eks_node_group.main.arn
}

output "eks_node_group_status" {
  description = "Status of the EKS Node Group"
  value       = aws_eks_node_group.main.status
}

# Database Outputs
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_username" {
  description = "RDS database username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "database_url" {
  description = "Database connection URL"
  value       = "postgresql://${aws_db_instance.main.username}:${var.db_password}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

# Redis Outputs
output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.main.configuration_endpoint_address != "" ? aws_elasticache_replication_group.main.configuration_endpoint_address : aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_port" {
  description = "Redis cluster port"
  value       = aws_elasticache_replication_group.main.port
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.configuration_endpoint_address != "" ? aws_elasticache_replication_group.main.configuration_endpoint_address : aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  sensitive   = true
}

# Load Balancer Outputs
output "load_balancer_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

# Security Group Outputs
output "eks_cluster_security_group_ids" {
  description = "Security group IDs attached to the EKS cluster"
  value       = [aws_security_group.eks_cluster.id]
}

output "eks_node_group_security_group_ids" {
  description = "Security group IDs attached to the EKS node group"
  value       = [aws_security_group.eks_node_group.id]
}

output "rds_security_group_id" {
  description = "Security group ID attached to the RDS instance"
  value       = aws_security_group.rds.id
}

output "redis_security_group_id" {
  description = "Security group ID attached to the Redis cluster"
  value       = aws_security_group.redis.id
}

# IAM Role Outputs
output "eks_cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_group_role_arn" {
  description = "ARN of the EKS node group IAM role"
  value       = aws_iam_role.eks_node_group.arn
}

output "aws_load_balancer_controller_role_arn" {
  description = "ARN of the AWS Load Balancer Controller IAM role"
  value       = aws_iam_role.aws_load_balancer_controller.arn
}

output "external_dns_role_arn" {
  description = "ARN of the External DNS IAM role"
  value       = aws_iam_role.external_dns.arn
}

output "cluster_autoscaler_role_arn" {
  description = "ARN of the Cluster Autoscaler IAM role"
  value       = aws_iam_role.cluster_autoscaler.arn
}

# KMS Key Outputs
output "eks_kms_key_id" {
  description = "KMS key ID for EKS encryption"
  value       = aws_kms_key.eks.key_id
}

output "eks_kms_key_arn" {
  description = "KMS key ARN for EKS encryption"
  value       = aws_kms_key.eks.arn
}

output "rds_kms_key_id" {
  description = "KMS key ID for RDS encryption"
  value       = aws_kms_key.rds.key_id
}

output "rds_kms_key_arn" {
  description = "KMS key ARN for RDS encryption"
  value       = aws_kms_key.rds.arn
}

# CloudWatch Outputs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for EKS"
  value       = aws_cloudwatch_log_group.eks_cluster.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group for EKS"
  value       = aws_cloudwatch_log_group.eks_cluster.arn
}

# Availability Zone Outputs
output "availability_zones" {
  description = "List of availability zones used"
  value       = local.azs
}

# Environment Information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "project_name" {
  description = "Project name"
  value       = "sunday-com"
}

# Kubectl Configuration Command
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}

# Connection Information for Applications
output "connection_info" {
  description = "Connection information for applications"
  value = {
    database_url = "postgresql://${aws_db_instance.main.username}:${var.db_password}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
    redis_url    = "redis://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.configuration_endpoint_address != "" ? aws_elasticache_replication_group.main.configuration_endpoint_address : aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
    eks_cluster  = aws_eks_cluster.main.name
    environment  = var.environment
    region       = var.aws_region
  }
  sensitive = true
}

# Resource Tags
output "common_tags" {
  description = "Common tags applied to all resources"
  value       = local.common_tags
}

# Monitoring Endpoints
output "monitoring_endpoints" {
  description = "Monitoring service endpoints"
  value = {
    prometheus_url = "http://prometheus.${var.domain_name}"
    grafana_url    = "http://grafana.${var.domain_name}"
    kibana_url     = "http://kibana.${var.domain_name}"
  }
}

# Application URLs
output "application_urls" {
  description = "Application URLs"
  value = {
    frontend_url = "https://${var.domain_name}"
    backend_url  = "https://api.${var.domain_name}"
    admin_url    = "https://admin.${var.domain_name}"
  }
}

# Cost Optimization Information
output "cost_optimization_info" {
  description = "Information about cost optimization features"
  value = {
    spot_instances_enabled = var.enable_spot_instances
    single_nat_gateway     = var.single_nat_gateway
    backup_retention_days  = var.backup_retention_days
    log_retention_days     = var.log_retention_days
  }
}

# Security Information
output "security_info" {
  description = "Security configuration information"
  value = {
    encryption_at_rest     = var.enable_encryption_at_rest
    encryption_in_transit  = var.enable_encryption_in_transit
    waf_enabled           = var.enable_waf
    guardduty_enabled     = var.enable_guardduty
    compliance_framework  = var.compliance_framework
  }
}