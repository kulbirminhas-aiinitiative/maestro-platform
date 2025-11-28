# Variables for Terraform infrastructure configuration

# General
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "simple-test-requirement"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "DevOps Team"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# EKS Cluster
variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "app_node_group_desired_size" {
  description = "Desired number of nodes in application node group"
  type        = number
  default     = 3
}

variable "app_node_group_min_size" {
  description = "Minimum number of nodes in application node group"
  type        = number
  default     = 2
}

variable "app_node_group_max_size" {
  description = "Maximum number of nodes in application node group"
  type        = number
  default     = 10
}

variable "app_node_instance_types" {
  description = "Instance types for application node group"
  type        = list(string)
  default     = ["t3.large"]
}

# RDS Database
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 50
}

variable "rds_max_allocated_storage" {
  description = "Maximum allocated storage for RDS in GB"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "myapp"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "dbadmin"
  sensitive   = true
}

# Redis
variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.medium"
}

# Domain
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "example.com"
}
