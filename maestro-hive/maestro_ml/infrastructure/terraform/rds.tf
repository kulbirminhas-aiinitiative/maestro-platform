# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-db-subnet-group"
    }
  )
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
    description     = "Allow PostgreSQL from EKS"
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
      Name = "${var.project_name}-rds-sg"
    }
  )
}

# RDS Parameter Group
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-postgres14"
  family = "postgres14"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_duration"
    value = "1"
  }

  tags = var.tags
}

# Random password for RDS
resource "random_password" "rds_password" {
  length  = 32
  special = true
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-postgres"
  engine         = "postgres"
  engine_version = "14.9"
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.rds_database_name
  username = var.rds_username
  password = random_password.rds_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.project_name}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  deletion_protection = true

  tags = var.tags
}

# Store RDS password in Secrets Manager
resource "aws_secretsmanager_secret" "rds_password" {
  name = "${var.project_name}/rds/password"

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "rds_password" {
  secret_id = aws_secretsmanager_secret.rds_password.id
  secret_string = jsonencode({
    username = var.rds_username
    password = random_password.rds_password.result
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = var.rds_database_name
  })
}
