variable "network_name" {
  description = "Name of the Docker network"
  type        = string
  default     = "maestro-network"
}

variable "environment" {
  description = "Environment name (dev, demo, staging, prod)"
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR block for the network"
  type        = string
  default     = "172.28.0.0/16"
}

variable "gateway" {
  description = "Gateway IP for the network"
  type        = string
  default     = "172.28.0.1"
}
