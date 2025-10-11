# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = var.tags
}

# ElastiCache Security Group
resource "aws_security_group" "elasticache" {
  name        = "${var.project_name}-redis-sg"
  description = "Security group for ElastiCache Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
    description     = "Allow Redis from EKS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-redis-sg"
    }
  )
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.project_name}-redis7"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = var.tags
}

# ElastiCache Replication Group
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.project_name}-redis"
  replication_group_description = "Redis cluster for Maestro ML"

  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.elasticache_node_type
  num_cache_clusters   = var.elasticache_num_cache_nodes
  parameter_group_name = aws_elasticache_parameter_group.main.name
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]

  automatic_failover_enabled = true
  multi_az_enabled           = true

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  snapshot_retention_limit = 5
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "mon:05:00-mon:07:00"

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  tags = var.tags
}

# CloudWatch Log Group for Redis
resource "aws_cloudwatch_log_group" "redis" {
  name              = "/aws/elasticache/${var.project_name}-redis"
  retention_in_days = 7

  tags = var.tags
}
