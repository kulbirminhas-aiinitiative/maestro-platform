# Sunday.com Infrastructure - Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "sunday"
}

# EKS Variables
variable "eks_node_groups" {
  description = "EKS node groups configuration"
  type = map(object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    capacity_type  = string
    disk_size      = number
  }))
  default = {
    general = {
      instance_types = ["c5.large"]
      min_size       = 1
      max_size       = 10
      desired_size   = 3
      capacity_type  = "ON_DEMAND"
      disk_size      = 50
    }
    compute = {
      instance_types = ["c5.xlarge"]
      min_size       = 0
      max_size       = 5
      desired_size   = 1
      capacity_type  = "SPOT"
      disk_size      = 50
    }
  }
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

# RDS Variables
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "rds_max_allocated_storage" {
  description = "RDS maximum allocated storage in GB"
  type        = number
  default     = 1000
}

variable "rds_backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

variable "rds_multi_az" {
  description = "Enable RDS Multi-AZ deployment"
  type        = bool
  default     = false
}

# ElastiCache Variables
variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "elasticache_num_nodes" {
  description = "Number of ElastiCache nodes"
  type        = number
  default     = 1
}

variable "elasticache_parameter_group_name" {
  description = "ElastiCache parameter group name"
  type        = string
  default     = "default.redis7"
}

# S3 Variables
variable "s3_versioning_enabled" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "s3_lifecycle_rules" {
  description = "S3 lifecycle rules"
  type = list(object({
    id      = string
    enabled = bool
    expiration = object({
      days = number
    })
    noncurrent_version_expiration = object({
      noncurrent_days = number
    })
  }))
  default = [
    {
      id      = "delete_old_versions"
      enabled = true
      expiration = {
        days = 365
      }
      noncurrent_version_expiration = {
        noncurrent_days = 30
      }
    }
  ]
}

# Monitoring Variables
variable "enable_cloudwatch_insights" {
  description = "Enable CloudWatch Insights"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Network Variables
variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use a single NAT Gateway for all private subnets"
  type        = bool
  default     = false
}

# Security Variables
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the cluster"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_irsa" {
  description = "Enable IAM Roles for Service Accounts"
  type        = bool
  default     = true
}

# Cost Optimization Variables
variable "enable_cluster_autoscaler" {
  description = "Enable Cluster Autoscaler"
  type        = bool
  default     = true
}

variable "enable_vertical_pod_autoscaler" {
  description = "Enable Vertical Pod Autoscaler"
  type        = bool
  default     = false
}