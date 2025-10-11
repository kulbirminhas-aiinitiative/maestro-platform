output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_password_secret_arn" {
  description = "ARN of Secrets Manager secret containing RDS password"
  value       = aws_secretsmanager_secret.rds_password.arn
}

output "elasticache_endpoint" {
  description = "ElastiCache endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "s3_artifacts_bucket" {
  description = "S3 artifacts bucket name"
  value       = aws_s3_bucket.artifacts.id
}

output "s3_artifacts_bucket_arn" {
  description = "S3 artifacts bucket ARN"
  value       = aws_s3_bucket.artifacts.arn
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}
