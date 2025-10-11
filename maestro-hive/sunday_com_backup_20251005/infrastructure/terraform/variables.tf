# Variables for Sunday.com Infrastructure

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

# EKS Configuration
variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "eks_public_access_cidrs" {
  description = "List of CIDR blocks that can access the EKS public API server endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Node Group Configuration
variable "node_instance_types" {
  description = "List of instance types for EKS node group"
  type        = list(string)
  default     = ["t3.medium", "t3.large"]
}

variable "node_desired_size" {
  description = "Desired number of nodes in the EKS node group"
  type        = number
  default     = 3

  validation {
    condition     = var.node_desired_size >= 1 && var.node_desired_size <= 20
    error_message = "Node desired size must be between 1 and 20."
  }
}

variable "node_max_size" {
  description = "Maximum number of nodes in the EKS node group"
  type        = number
  default     = 10

  validation {
    condition     = var.node_max_size >= 1 && var.node_max_size <= 50
    error_message = "Node max size must be between 1 and 50."
  }
}

variable "node_min_size" {
  description = "Minimum number of nodes in the EKS node group"
  type        = number
  default     = 1

  validation {
    condition     = var.node_min_size >= 1 && var.node_min_size <= 10
    error_message = "Node min size must be between 1 and 10."
  }
}

variable "node_disk_size" {
  description = "Disk size in GiB for EKS node group instances"
  type        = number
  default     = 50

  validation {
    condition     = var.node_disk_size >= 20 && var.node_disk_size <= 100
    error_message = "Node disk size must be between 20 and 100 GiB."
  }
}

# Database Configuration
variable "db_allocated_storage" {
  description = "The allocated storage in gigabytes for RDS instance"
  type        = number
  default     = 100

  validation {
    condition     = var.db_allocated_storage >= 20 && var.db_allocated_storage <= 1000
    error_message = "DB allocated storage must be between 20 and 1000 GB."
  }
}

variable "db_max_allocated_storage" {
  description = "The upper limit to which Amazon RDS can automatically scale the storage"
  type        = number
  default     = 500

  validation {
    condition     = var.db_max_allocated_storage >= 100 && var.db_max_allocated_storage <= 2000
    error_message = "DB max allocated storage must be between 100 and 2000 GB."
  }
}

variable "db_instance_class" {
  description = "The instance type of the RDS instance"
  type        = string
  default     = "db.t3.medium"
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15.4"
}

variable "db_name" {
  description = "The name of the database"
  type        = string
  default     = "sunday_db"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.db_name))
    error_message = "Database name must start with a letter and contain only alphanumeric characters and underscores."
  }
}

variable "db_username" {
  description = "Username for the master DB user"
  type        = string
  default     = "sunday_user"
  sensitive   = true

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.db_username))
    error_message = "Database username must start with a letter and contain only alphanumeric characters and underscores."
  }
}

variable "db_password" {
  description = "Password for the master DB user"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 8 && length(var.db_password) <= 128
    error_message = "Database password must be between 8 and 128 characters."
  }
}

variable "db_backup_retention_period" {
  description = "The days to retain backups for"
  type        = number
  default     = 7

  validation {
    condition     = var.db_backup_retention_period >= 1 && var.db_backup_retention_period <= 35
    error_message = "Backup retention period must be between 1 and 35 days."
  }
}

# Redis Configuration
variable "redis_node_type" {
  description = "Instance type for Redis nodes"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes in the Redis cluster"
  type        = number
  default     = 1

  validation {
    condition     = var.redis_num_cache_nodes >= 1 && var.redis_num_cache_nodes <= 6
    error_message = "Number of cache nodes must be between 1 and 6."
  }
}

variable "redis_auth_token" {
  description = "Auth token for Redis cluster"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.redis_auth_token) >= 16 && length(var.redis_auth_token) <= 128
    error_message = "Redis auth token must be between 16 and 128 characters."
  }
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14

  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# Domain Configuration
variable "domain_name" {
  description = "Primary domain name for the application"
  type        = string
  default     = "sunday.com"
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for the domain"
  type        = string
  default     = ""
}

# Certificate Configuration
variable "certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS"
  type        = string
  default     = ""
}

# Backup Configuration
variable "backup_enabled" {
  description = "Enable AWS Backup for RDS and other resources"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}

# Monitoring and Alerting
variable "enable_cloudwatch_insights" {
  description = "Enable CloudWatch Container Insights for EKS"
  type        = bool
  default     = true
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  type        = string
  default     = ""
}

# Security Configuration
variable "enable_waf" {
  description = "Enable AWS WAF for the application"
  type        = bool
  default     = true
}

variable "enable_guardduty" {
  description = "Enable AWS GuardDuty for threat detection"
  type        = bool
  default     = true
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = false
}

variable "spot_instance_percentage" {
  description = "Percentage of spot instances in the node group"
  type        = number
  default     = 50

  validation {
    condition     = var.spot_instance_percentage >= 0 && var.spot_instance_percentage <= 100
    error_message = "Spot instance percentage must be between 0 and 100."
  }
}

# Application Configuration
variable "application_secrets" {
  description = "Application secrets for the Sunday.com platform"
  type = object({
    jwt_secret         = string
    jwt_refresh_secret = string
    session_secret     = string
    webhook_secret     = string
    openai_api_key     = string
    smtp_password      = string
  })
  sensitive = true
  default = {
    jwt_secret         = ""
    jwt_refresh_secret = ""
    session_secret     = ""
    webhook_secret     = ""
    openai_api_key     = ""
    smtp_password      = ""
  }
}

# Feature Flags
variable "enable_elasticsearch" {
  description = "Enable Elasticsearch for search functionality"
  type        = bool
  default     = true
}

variable "enable_clickhouse" {
  description = "Enable ClickHouse for analytics"
  type        = bool
  default     = true
}

variable "enable_monitoring_stack" {
  description = "Deploy Prometheus and Grafana monitoring stack"
  type        = bool
  default     = true
}

# Performance Configuration
variable "enable_cdn" {
  description = "Enable CloudFront CDN for static assets"
  type        = bool
  default     = true
}

variable "cdn_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_All", "PriceClass_200", "PriceClass_100"], var.cdn_price_class)
    error_message = "CDN price class must be one of: PriceClass_All, PriceClass_200, PriceClass_100."
  }
}

# Network Configuration
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

# Disaster Recovery
variable "enable_cross_region_backup" {
  description = "Enable cross-region backup replication"
  type        = bool
  default     = true
}

variable "backup_region" {
  description = "Region for backup replication"
  type        = string
  default     = "us-east-1"
}

# Compliance
variable "enable_encryption_at_rest" {
  description = "Enable encryption at rest for all resources"
  type        = bool
  default     = true
}

variable "enable_encryption_in_transit" {
  description = "Enable encryption in transit for all communications"
  type        = bool
  default     = true
}

variable "compliance_framework" {
  description = "Compliance framework to adhere to"
  type        = string
  default     = "SOC2"

  validation {
    condition     = contains(["SOC2", "GDPR", "HIPAA", "PCI-DSS"], var.compliance_framework)
    error_message = "Compliance framework must be one of: SOC2, GDPR, HIPAA, PCI-DSS."
  }
}