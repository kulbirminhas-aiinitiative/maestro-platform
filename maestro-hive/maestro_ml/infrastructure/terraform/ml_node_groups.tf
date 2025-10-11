# Maestro ML Platform - ML-Specific Node Groups
# Phase 1.1.7 - GPU Node Pools for ML Training

# GPU Node Group for Training Workloads
resource "aws_eks_node_group" "ml_gpu" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-ml-gpu-nodes"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id

  # GPU instances for training
  instance_types = ["g4dn.xlarge", "g4dn.2xlarge"]  # NVIDIA T4 GPUs

  scaling_config {
    desired_size = var.ml_gpu_node_desired_size
    min_size     = var.ml_gpu_node_min_size
    max_size     = var.ml_gpu_node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  # Taints to ensure only ML workloads run on GPU nodes
  taint {
    key    = "nvidia.com/gpu"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  labels = {
    workload-type = "ml-training"
    gpu-enabled   = "true"
    node-type     = "gpu"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]

  tags = merge(
    var.tags,
    {
      "k8s.io/cluster-autoscaler/enabled"                = "true"
      "k8s.io/cluster-autoscaler/${var.project_name}"    = "owned"
      "k8s.io/cluster-autoscaler/node-template/label/gpu" = "true"
    }
  )
}

# CPU Node Group for Inference Workloads
resource "aws_eks_node_group" "ml_inference" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-ml-inference-nodes"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id

  # CPU-optimized instances for inference
  instance_types = ["c5.2xlarge", "c5.4xlarge"]

  scaling_config {
    desired_size = var.ml_inference_node_desired_size
    min_size     = var.ml_inference_node_min_size
    max_size     = var.ml_inference_node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    workload-type = "ml-inference"
    node-type     = "cpu-optimized"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]

  tags = merge(
    var.tags,
    {
      "k8s.io/cluster-autoscaler/enabled"             = "true"
      "k8s.io/cluster-autoscaler/${var.project_name}" = "owned"
    }
  )
}

# Spot Instance Node Group for Cost Optimization
# Phase 4.2.1 - Implement spot instance usage
resource "aws_eks_node_group" "ml_spot" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-ml-spot-nodes"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id

  # Mixed instance types for spot
  instance_types = ["c5.xlarge", "c5.2xlarge", "m5.xlarge", "m5.2xlarge"]
  capacity_type  = "SPOT"

  scaling_config {
    desired_size = var.ml_spot_node_desired_size
    min_size     = var.ml_spot_node_min_size
    max_size     = var.ml_spot_node_max_size
  }

  update_config {
    max_unavailable = 2
  }

  # Taint spot nodes so only fault-tolerant workloads use them
  taint {
    key    = "spot-instance"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  labels = {
    workload-type = "ml-batch"
    node-type     = "spot"
    cost-tier     = "low"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]

  tags = merge(
    var.tags,
    {
      "k8s.io/cluster-autoscaler/enabled"             = "true"
      "k8s.io/cluster-autoscaler/${var.project_name}" = "owned"
      "spot-enabled"                                  = "true"
    }
  )
}
