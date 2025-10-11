# Sunday.com Infrastructure - Main Terraform Configuration

terraform {
  required_version = ">= 1.6"

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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket         = "sunday-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "sunday-terraform-locks"
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Sunday.com"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "DevOps"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  vpc_cidr = var.environment == "production" ? "10.0.0.0/16" : "10.1.0.0/16"

  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  name_prefix = local.name_prefix
  vpc_cidr    = local.vpc_cidr
  azs         = local.azs

  tags = local.common_tags
}

# EKS Module
module "eks" {
  source = "./modules/eks"

  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.private_subnet_ids

  node_groups = var.eks_node_groups

  tags = local.common_tags
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.database_subnet_ids
  security_groups = [module.eks.cluster_security_group_id]

  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage

  tags = local.common_tags
}

# ElastiCache Module
module "elasticache" {
  source = "./modules/elasticache"

  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.database_subnet_ids
  security_groups = [module.eks.cluster_security_group_id]

  node_type    = var.elasticache_node_type
  num_cache_nodes = var.elasticache_num_nodes

  tags = local.common_tags
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  name_prefix = local.name_prefix
  environment = var.environment

  tags = local.common_tags
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"

  name_prefix      = local.name_prefix
  vpc_id           = module.vpc.vpc_id
  subnet_ids       = module.vpc.private_subnet_ids
  cluster_name     = module.eks.cluster_name

  tags = local.common_tags
}