variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "maestro-ml"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# EKS Configuration
variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "eks_node_instance_types" {
  description = "Instance types for EKS node groups"
  type        = list(string)
  default     = ["t3.medium", "t3.large"]
}

variable "eks_node_desired_size" {
  description = "Desired number of nodes in EKS node group"
  type        = number
  default     = 3
}

variable "eks_node_min_size" {
  description = "Minimum number of nodes in EKS node group"
  type        = number
  default     = 2
}

variable "eks_node_max_size" {
  description = "Maximum number of nodes in EKS node group"
  type        = number
  default     = 10
}

# RDS Configuration
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
  default     = 500
}

variable "rds_database_name" {
  description = "RDS database name"
  type        = string
  default     = "maestro_ml"
}

variable "rds_username" {
  description = "RDS master username"
  type        = string
  default     = "maestro"
}

# ElastiCache Configuration
variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "elasticache_num_cache_nodes" {
  description = "Number of ElastiCache nodes"
  type        = number
  default     = 2
}

# S3 Configuration
variable "s3_artifact_bucket_name" {
  description = "S3 bucket name for artifacts"
  type        = string
  default     = "maestro-ml-artifacts"
}

# ML GPU Node Group Configuration
variable "ml_gpu_node_desired_size" {
  description = "Desired number of GPU nodes for ML training"
  type        = number
  default     = 0  # Start with 0, scale up when needed
}

variable "ml_gpu_node_min_size" {
  description = "Minimum number of GPU nodes"
  type        = number
  default     = 0
}

variable "ml_gpu_node_max_size" {
  description = "Maximum number of GPU nodes"
  type        = number
  default     = 10
}

# ML Inference Node Group Configuration
variable "ml_inference_node_desired_size" {
  description = "Desired number of inference nodes"
  type        = number
  default     = 2
}

variable "ml_inference_node_min_size" {
  description = "Minimum number of inference nodes"
  type        = number
  default     = 1
}

variable "ml_inference_node_max_size" {
  description = "Maximum number of inference nodes"
  type        = number
  default     = 20
}

# ML Spot Instance Node Group Configuration
variable "ml_spot_node_desired_size" {
  description = "Desired number of spot instance nodes"
  type        = number
  default     = 2
}

variable "ml_spot_node_min_size" {
  description = "Minimum number of spot instance nodes"
  type        = number
  default     = 0
}

variable "ml_spot_node_max_size" {
  description = "Maximum number of spot instance nodes"
  type        = number
  default     = 50
}

# Tags
variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
