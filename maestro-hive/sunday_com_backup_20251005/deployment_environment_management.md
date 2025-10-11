# Sunday.com Deployment Environment Management System

## Table of Contents

1. [Overview](#overview)
2. [Environment Architecture](#environment-architecture)
3. [Environment Lifecycle Management](#environment-lifecycle-management)
4. [Configuration Management](#configuration-management)
5. [Environment Promotion Pipeline](#environment-promotion-pipeline)
6. [Infrastructure as Code](#infrastructure-as-code)
7. [Environment Validation and Testing](#environment-validation-and-testing)
8. [Resource Management and Optimization](#resource-management-and-optimization)

---

## Overview

The Sunday.com Deployment Environment Management System provides comprehensive lifecycle management for all deployment environments, ensuring consistency, reliability, and efficient resource utilization across development, staging, production, and disaster recovery environments.

### System Objectives

- **Environment Consistency**: Identical configurations across all environments
- **Automated Provisioning**: Infrastructure as Code for all environments
- **Resource Optimization**: Cost-effective resource allocation and scaling
- **Security Compliance**: Consistent security policies and configurations
- **Rapid Recovery**: Fast environment recreation and disaster recovery

### Environment Hierarchy

```
Production Environment
├── Primary Region (us-east-1)
│   ├── Production Cluster
│   ├── Blue Environment
│   └── Green Environment
├── Secondary Region (us-west-2)
│   └── Disaster Recovery Cluster
└── Edge Locations
    ├── CDN Endpoints
    └── Edge Computing Nodes

Non-Production Environments
├── Staging (us-east-1)
│   ├── Full Production Mirror
│   └── Performance Testing
├── Development (us-east-1)
│   ├── Feature Development
│   └── Integration Testing
└── Ephemeral Environments
    ├── Feature Branches
    ├── Pull Request Previews
    └── Testing Sandboxes
```

---

## Environment Architecture

### Environment Configuration Matrix

```yaml
# config/environment-matrix.yaml
environments:
  production:
    regions:
      primary: us-east-1
      secondary: us-west-2
    clusters:
      - name: sunday-production
        region: us-east-1
        node_groups:
          - name: compute-optimized
            instance_type: c5.2xlarge
            min_size: 3
            max_size: 20
            desired_size: 5
          - name: memory-optimized
            instance_type: r5.xlarge
            min_size: 2
            max_size: 10
            desired_size: 3
    databases:
      primary:
        engine: postgresql
        version: "14.9"
        instance_class: db.r5.4xlarge
        multi_az: true
        backup_retention: 30
      cache:
        engine: redis
        node_type: cache.r6g.xlarge
        num_cache_nodes: 3
    storage:
      type: s3
      versioning: enabled
      encryption: AES256
      lifecycle_policies: enabled
    networking:
      vpc_cidr: 10.0.0.0/16
      availability_zones: 3
      public_subnets: 3
      private_subnets: 3
      nat_gateways: 3
    monitoring:
      prometheus: enabled
      grafana: enabled
      jaeger: enabled
      elk_stack: enabled
    security:
      kms_encryption: enabled
      secrets_manager: enabled
      iam_roles: strict
      network_policies: enabled

  staging:
    regions:
      primary: us-east-1
    clusters:
      - name: sunday-staging
        region: us-east-1
        node_groups:
          - name: general-purpose
            instance_type: m5.large
            min_size: 2
            max_size: 10
            desired_size: 3
    databases:
      primary:
        engine: postgresql
        version: "14.9"
        instance_class: db.r5.large
        multi_az: false
        backup_retention: 7
      cache:
        engine: redis
        node_type: cache.t3.medium
        num_cache_nodes: 1
    storage:
      type: s3
      versioning: enabled
      encryption: AES256
    networking:
      vpc_cidr: 10.1.0.0/16
      availability_zones: 2
      public_subnets: 2
      private_subnets: 2
      nat_gateways: 1
    monitoring:
      prometheus: enabled
      grafana: enabled
      jaeger: disabled
      elk_stack: basic
    security:
      kms_encryption: enabled
      secrets_manager: enabled
      iam_roles: standard
      network_policies: basic

  development:
    regions:
      primary: us-east-1
    clusters:
      - name: sunday-development
        region: us-east-1
        node_groups:
          - name: general-purpose
            instance_type: t3.medium
            min_size: 1
            max_size: 5
            desired_size: 2
    databases:
      primary:
        engine: postgresql
        version: "14.9"
        instance_class: db.t3.medium
        multi_az: false
        backup_retention: 3
      cache:
        engine: redis
        node_type: cache.t3.micro
        num_cache_nodes: 1
    storage:
      type: s3
      versioning: disabled
      encryption: AES256
    networking:
      vpc_cidr: 10.2.0.0/16
      availability_zones: 1
      public_subnets: 1
      private_subnets: 1
      nat_gateways: 1
    monitoring:
      prometheus: basic
      grafana: disabled
      jaeger: disabled
      elk_stack: disabled
    security:
      kms_encryption: basic
      secrets_manager: enabled
      iam_roles: basic
      network_policies: disabled

deployment_strategies:
  production:
    primary: blue_green
    alternatives: [canary]
    validation_required: comprehensive
    approval_required: true
  staging:
    primary: rolling
    alternatives: [blue_green]
    validation_required: standard
    approval_required: false
  development:
    primary: recreate
    alternatives: [rolling]
    validation_required: basic
    approval_required: false
```

### Environment Management Controller

```python
#!/usr/bin/env python3
# scripts/environment-manager.py

import json
import yaml
import subprocess
import boto3
import time
from typing import Dict, List, Optional
from datetime import datetime
import jinja2

class EnvironmentManager:
    def __init__(self, config_file: str = "config/environment-matrix.yaml"):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        self.aws_session = boto3.Session()
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('templates/infrastructure')
        )

    def create_environment(self, env_name: str, region: str = None) -> bool:
        """Create a new environment"""

        print(f"🚀 Creating environment: {env_name}")

        if env_name not in self.config['environments']:
            print(f"❌ Environment {env_name} not found in configuration")
            return False

        env_config = self.config['environments'][env_name]
        primary_region = region or env_config['regions']['primary']

        try:
            # Create infrastructure
            if not self.provision_infrastructure(env_name, env_config, primary_region):
                print(f"❌ Failed to provision infrastructure for {env_name}")
                return False

            # Deploy applications
            if not self.deploy_applications(env_name, env_config):
                print(f"❌ Failed to deploy applications to {env_name}")
                return False

            # Configure monitoring
            if not self.setup_monitoring(env_name, env_config):
                print(f"❌ Failed to setup monitoring for {env_name}")
                return False

            # Validate environment
            if not self.validate_environment(env_name):
                print(f"❌ Environment validation failed for {env_name}")
                return False

            print(f"✅ Environment {env_name} created successfully")
            return True

        except Exception as e:
            print(f"❌ Error creating environment {env_name}: {str(e)}")
            return False

    def provision_infrastructure(self, env_name: str, config: Dict, region: str) -> bool:
        """Provision infrastructure using Terraform"""

        print(f"🏗️ Provisioning infrastructure for {env_name}")

        # Generate Terraform configuration
        tf_config = self.generate_terraform_config(env_name, config, region)

        # Write Terraform files
        tf_dir = f"infrastructure/environments/{env_name}"
        subprocess.run(['mkdir', '-p', tf_dir], check=True)

        with open(f"{tf_dir}/main.tf", 'w') as f:
            f.write(tf_config)

        # Initialize and apply Terraform
        commands = [
            ['terraform', 'init'],
            ['terraform', 'plan', '-out=tfplan'],
            ['terraform', 'apply', '-auto-approve', 'tfplan']
        ]

        for cmd in commands:
            result = subprocess.run(
                cmd,
                cwd=tf_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"❌ Terraform command failed: {' '.join(cmd)}")
                print(f"Error: {result.stderr}")
                return False

        print(f"✅ Infrastructure provisioned for {env_name}")
        return True

    def generate_terraform_config(self, env_name: str, config: Dict, region: str) -> str:
        """Generate Terraform configuration from environment config"""

        template = self.template_env.get_template('main.tf.j2')

        return template.render(
            environment=env_name,
            config=config,
            region=region,
            timestamp=datetime.now().isoformat()
        )

    def deploy_applications(self, env_name: str, config: Dict) -> bool:
        """Deploy applications to the environment"""

        print(f"📦 Deploying applications to {env_name}")

        # Update kubeconfig
        cluster_name = f"sunday-{env_name}"
        region = config['regions']['primary']

        subprocess.run([
            'aws', 'eks', 'update-kubeconfig',
            '--name', cluster_name,
            '--region', region
        ], check=True)

        # Apply Kubernetes manifests
        manifest_dir = f"k8s/environments/{env_name}"

        if not self.apply_kubernetes_manifests(manifest_dir):
            return False

        # Wait for deployments to be ready
        if not self.wait_for_deployments(env_name):
            return False

        print(f"✅ Applications deployed to {env_name}")
        return True

    def apply_kubernetes_manifests(self, manifest_dir: str) -> bool:
        """Apply Kubernetes manifests"""

        try:
            result = subprocess.run([
                'kubectl', 'apply', '-R', '-f', manifest_dir
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to apply manifests: {result.stderr}")
                return False

            return True
        except Exception as e:
            print(f"❌ Error applying manifests: {str(e)}")
            return False

    def wait_for_deployments(self, env_name: str, timeout: int = 600) -> bool:
        """Wait for all deployments to be ready"""

        namespace = f"sunday-{env_name}"
        deployments = ['backend-deployment', 'frontend-deployment']

        for deployment in deployments:
            print(f"⏳ Waiting for {deployment} to be ready...")

            result = subprocess.run([
                'kubectl', 'rollout', 'status',
                f'deployment/{deployment}',
                '-n', namespace,
                f'--timeout={timeout}s'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Deployment {deployment} failed to become ready")
                return False

        print("✅ All deployments are ready")
        return True

    def setup_monitoring(self, env_name: str, config: Dict) -> bool:
        """Setup monitoring for the environment"""

        print(f"📊 Setting up monitoring for {env_name}")

        monitoring_config = config.get('monitoring', {})

        if monitoring_config.get('prometheus'):
            if not self.deploy_prometheus(env_name):
                return False

        if monitoring_config.get('grafana'):
            if not self.deploy_grafana(env_name):
                return False

        if monitoring_config.get('jaeger'):
            if not self.deploy_jaeger(env_name):
                return False

        print(f"✅ Monitoring setup completed for {env_name}")
        return True

    def deploy_prometheus(self, env_name: str) -> bool:
        """Deploy Prometheus monitoring"""

        try:
            # Add Prometheus Helm repo
            subprocess.run([
                'helm', 'repo', 'add', 'prometheus-community',
                'https://prometheus-community.github.io/helm-charts'
            ], check=True)

            subprocess.run(['helm', 'repo', 'update'], check=True)

            # Install Prometheus
            result = subprocess.run([
                'helm', 'upgrade', '--install', 'prometheus',
                'prometheus-community/kube-prometheus-stack',
                '--namespace', 'monitoring',
                '--create-namespace',
                '--values', f'config/monitoring/prometheus-{env_name}.yaml'
            ], capture_output=True, text=True)

            return result.returncode == 0

        except Exception as e:
            print(f"❌ Error deploying Prometheus: {str(e)}")
            return False

    def validate_environment(self, env_name: str) -> bool:
        """Validate environment health and functionality"""

        print(f"🔍 Validating environment {env_name}")

        validations = [
            self.validate_infrastructure,
            self.validate_applications,
            self.validate_networking,
            self.validate_security,
            self.validate_monitoring
        ]

        for validation in validations:
            if not validation(env_name):
                return False

        print(f"✅ Environment {env_name} validation completed")
        return True

    def validate_infrastructure(self, env_name: str) -> bool:
        """Validate infrastructure components"""

        print("🏗️ Validating infrastructure...")

        # Check EKS cluster
        cluster_name = f"sunday-{env_name}"

        try:
            result = subprocess.run([
                'aws', 'eks', 'describe-cluster',
                '--name', cluster_name
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ EKS cluster {cluster_name} not found")
                return False

            cluster_info = json.loads(result.stdout)
            if cluster_info['cluster']['status'] != 'ACTIVE':
                print(f"❌ EKS cluster {cluster_name} is not active")
                return False

        except Exception as e:
            print(f"❌ Error validating EKS cluster: {str(e)}")
            return False

        print("✅ Infrastructure validation passed")
        return True

    def validate_applications(self, env_name: str) -> bool:
        """Validate application deployments"""

        print("📦 Validating applications...")

        namespace = f"sunday-{env_name}"

        try:
            # Check pod status
            result = subprocess.run([
                'kubectl', 'get', 'pods', '-n', namespace,
                '--no-headers'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to get pods in namespace {namespace}")
                return False

            pods = result.stdout.strip().split('\n')
            for pod_line in pods:
                if pod_line:
                    parts = pod_line.split()
                    if len(parts) >= 3 and parts[2] != 'Running':
                        print(f"❌ Pod {parts[0]} is not running: {parts[2]}")
                        return False

        except Exception as e:
            print(f"❌ Error validating applications: {str(e)}")
            return False

        print("✅ Application validation passed")
        return True

    def destroy_environment(self, env_name: str, force: bool = False) -> bool:
        """Destroy an environment"""

        print(f"🗑️ Destroying environment: {env_name}")

        if not force:
            confirmation = input(f"Are you sure you want to destroy {env_name}? (yes/no): ")
            if confirmation.lower() != 'yes':
                print("❌ Environment destruction cancelled")
                return False

        try:
            # Destroy Kubernetes resources
            namespace = f"sunday-{env_name}"
            subprocess.run([
                'kubectl', 'delete', 'namespace', namespace
            ], check=False)  # Don't fail if namespace doesn't exist

            # Destroy infrastructure
            tf_dir = f"infrastructure/environments/{env_name}"
            result = subprocess.run([
                'terraform', 'destroy', '-auto-approve'
            ], cwd=tf_dir, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to destroy infrastructure: {result.stderr}")
                return False

            print(f"✅ Environment {env_name} destroyed successfully")
            return True

        except Exception as e:
            print(f"❌ Error destroying environment: {str(e)}")
            return False

    def sync_environments(self, source_env: str, target_env: str,
                         sync_type: str = "config") -> bool:
        """Sync configurations between environments"""

        print(f"🔄 Syncing {source_env} → {target_env} (type: {sync_type})")

        if sync_type == "config":
            return self.sync_configuration(source_env, target_env)
        elif sync_type == "data":
            return self.sync_data(source_env, target_env)
        elif sync_type == "both":
            return (self.sync_configuration(source_env, target_env) and
                   self.sync_data(source_env, target_env))
        else:
            print(f"❌ Invalid sync type: {sync_type}")
            return False

    def sync_configuration(self, source_env: str, target_env: str) -> bool:
        """Sync configuration between environments"""

        try:
            # Export configurations from source
            source_namespace = f"sunday-{source_env}"
            target_namespace = f"sunday-{target_env}"

            # ConfigMaps
            result = subprocess.run([
                'kubectl', 'get', 'configmaps', '-n', source_namespace,
                '-o', 'yaml'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                configs = yaml.safe_load(result.stdout)

                # Update namespace in configs
                for item in configs.get('items', []):
                    item['metadata']['namespace'] = target_namespace

                # Apply to target
                config_yaml = yaml.dump(configs)
                subprocess.run([
                    'kubectl', 'apply', '-f', '-'
                ], input=config_yaml, text=True, check=True)

            print(f"✅ Configuration sync completed: {source_env} → {target_env}")
            return True

        except Exception as e:
            print(f"❌ Error syncing configuration: {str(e)}")
            return False

    def list_environments(self) -> List[Dict]:
        """List all environments and their status"""

        environments = []

        for env_name in self.config['environments'].keys():
            env_info = self.get_environment_info(env_name)
            environments.append(env_info)

        return environments

    def get_environment_info(self, env_name: str) -> Dict:
        """Get detailed information about an environment"""

        info = {
            "name": env_name,
            "status": "unknown",
            "region": None,
            "cluster": None,
            "applications": {},
            "last_deployment": None
        }

        try:
            env_config = self.config['environments'][env_name]
            info["region"] = env_config['regions']['primary']

            cluster_name = f"sunday-{env_name}"
            info["cluster"] = cluster_name

            # Check cluster status
            result = subprocess.run([
                'aws', 'eks', 'describe-cluster',
                '--name', cluster_name,
                '--region', info["region"]
            ], capture_output=True, text=True)

            if result.returncode == 0:
                cluster_info = json.loads(result.stdout)
                info["status"] = cluster_info['cluster']['status'].lower()

                # Check application status
                namespace = f"sunday-{env_name}"
                app_result = subprocess.run([
                    'kubectl', 'get', 'deployments', '-n', namespace,
                    '-o', 'json'
                ], capture_output=True, text=True)

                if app_result.returncode == 0:
                    deployments = json.loads(app_result.stdout)
                    for deployment in deployments.get('items', []):
                        name = deployment['metadata']['name']
                        status = deployment['status']
                        ready_replicas = status.get('readyReplicas', 0)
                        desired_replicas = status.get('replicas', 0)

                        info["applications"][name] = {
                            "ready": ready_replicas,
                            "desired": desired_replicas,
                            "healthy": ready_replicas == desired_replicas
                        }
            else:
                info["status"] = "not_found"

        except Exception as e:
            info["status"] = "error"
            info["error"] = str(e)

        return info

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Sunday.com Environment Manager')
    parser.add_argument('action', choices=[
        'create', 'destroy', 'sync', 'list', 'validate', 'info'
    ])
    parser.add_argument('--environment', '-e', help='Environment name')
    parser.add_argument('--source', help='Source environment for sync')
    parser.add_argument('--target', help='Target environment for sync')
    parser.add_argument('--sync-type', choices=['config', 'data', 'both'],
                       default='config', help='Type of sync to perform')
    parser.add_argument('--force', action='store_true',
                       help='Force action without confirmation')

    args = parser.parse_args()

    manager = EnvironmentManager()

    if args.action == 'create':
        if not args.environment:
            print("❌ Environment name required for create action")
            return 1
        success = manager.create_environment(args.environment)
        return 0 if success else 1

    elif args.action == 'destroy':
        if not args.environment:
            print("❌ Environment name required for destroy action")
            return 1
        success = manager.destroy_environment(args.environment, args.force)
        return 0 if success else 1

    elif args.action == 'sync':
        if not args.source or not args.target:
            print("❌ Source and target environments required for sync")
            return 1
        success = manager.sync_environments(args.source, args.target, args.sync_type)
        return 0 if success else 1

    elif args.action == 'list':
        environments = manager.list_environments()
        print("\n📋 Environment Status:")
        for env in environments:
            status_icon = "✅" if env["status"] == "active" else "❌"
            print(f"  {status_icon} {env['name']}: {env['status']}")
            if env.get("applications"):
                for app, info in env["applications"].items():
                    app_icon = "✅" if info["healthy"] else "❌"
                    print(f"    {app_icon} {app}: {info['ready']}/{info['desired']}")
        return 0

    elif args.action == 'validate':
        if not args.environment:
            print("❌ Environment name required for validate action")
            return 1
        success = manager.validate_environment(args.environment)
        return 0 if success else 1

    elif args.action == 'info':
        if not args.environment:
            print("❌ Environment name required for info action")
            return 1
        info = manager.get_environment_info(args.environment)
        print(json.dumps(info, indent=2))
        return 0

if __name__ == "__main__":
    exit(main())
```

---

## Environment Lifecycle Management

### Automated Environment Provisioning

```bash
#!/bin/bash
# scripts/environment-lifecycle.sh

COMMAND=${1}
ENVIRONMENT=${2}
ADDITIONAL_ARGS=${@:3}

case $COMMAND in
    "create")
        create_environment "$ENVIRONMENT" $ADDITIONAL_ARGS
        ;;
    "update")
        update_environment "$ENVIRONMENT" $ADDITIONAL_ARGS
        ;;
    "destroy")
        destroy_environment "$ENVIRONMENT" $ADDITIONAL_ARGS
        ;;
    "clone")
        clone_environment "$ENVIRONMENT" $ADDITIONAL_ARGS
        ;;
    "backup")
        backup_environment "$ENVIRONMENT" $ADDITIONAL_ARGS
        ;;
    "restore")
        restore_environment "$ENVIRONMENT" $ADDITIONAL_ARGS
        ;;
    *)
        echo "Usage: $0 {create|update|destroy|clone|backup|restore} <environment> [options]"
        exit 1
        ;;
esac

create_environment() {
    local env_name=$1
    local template=${2:-"standard"}

    echo "🚀 Creating environment: $env_name (template: $template)"

    # Validate environment name
    if ! validate_environment_name "$env_name"; then
        echo "❌ Invalid environment name: $env_name"
        exit 1
    fi

    # Check if environment already exists
    if environment_exists "$env_name"; then
        echo "❌ Environment $env_name already exists"
        exit 1
    fi

    # Create environment directory structure
    mkdir -p "environments/$env_name"/{terraform,kubernetes,config,secrets}

    # Generate environment configuration
    generate_environment_config "$env_name" "$template"

    # Provision infrastructure
    provision_environment_infrastructure "$env_name"

    # Deploy applications
    deploy_environment_applications "$env_name"

    # Setup monitoring
    setup_environment_monitoring "$env_name"

    # Validate deployment
    validate_environment_deployment "$env_name"

    echo "✅ Environment $env_name created successfully"
}

generate_environment_config() {
    local env_name=$1
    local template=$2

    echo "📋 Generating configuration for $env_name using template $template"

    # Copy template configuration
    cp -r "templates/environments/$template"/* "environments/$env_name/"

    # Replace placeholders
    find "environments/$env_name" -type f -name "*.yaml" -o -name "*.tf" | \
    while read file; do
        sed -i "s/{{ENVIRONMENT_NAME}}/$env_name/g" "$file"
        sed -i "s/{{TIMESTAMP}}/$(date -Iseconds)/g" "$file"
        sed -i "s/{{CREATOR}}/$(whoami)/g" "$file"
    done

    echo "✅ Configuration generated for $env_name"
}

provision_environment_infrastructure() {
    local env_name=$1

    echo "🏗️ Provisioning infrastructure for $env_name"

    cd "environments/$env_name/terraform"

    # Initialize Terraform
    terraform init -backend-config="key=environments/$env_name/terraform.tfstate"

    # Plan infrastructure
    terraform plan -out=tfplan -var="environment=$env_name"

    # Apply infrastructure
    terraform apply -auto-approve tfplan

    if [ $? -eq 0 ]; then
        echo "✅ Infrastructure provisioned for $env_name"
        cd - > /dev/null
        return 0
    else
        echo "❌ Infrastructure provisioning failed for $env_name"
        cd - > /dev/null
        return 1
    fi
}

clone_environment() {
    local source_env=$1
    local target_env=$2
    local include_data=${3:-false}

    echo "📋 Cloning environment: $source_env → $target_env"

    if ! environment_exists "$source_env"; then
        echo "❌ Source environment $source_env does not exist"
        exit 1
    fi

    if environment_exists "$target_env"; then
        echo "❌ Target environment $target_env already exists"
        exit 1
    fi

    # Copy environment configuration
    cp -r "environments/$source_env" "environments/$target_env"

    # Update configuration for new environment
    find "environments/$target_env" -type f -name "*.yaml" -o -name "*.tf" | \
    while read file; do
        sed -i "s/$source_env/$target_env/g" "$file"
    done

    # Provision new environment
    provision_environment_infrastructure "$target_env"

    # Clone data if requested
    if [ "$include_data" = "true" ]; then
        clone_environment_data "$source_env" "$target_env"
    fi

    # Deploy applications
    deploy_environment_applications "$target_env"

    echo "✅ Environment cloned successfully: $source_env → $target_env"
}

backup_environment() {
    local env_name=$1
    local backup_type=${2:-"full"}
    local backup_id="backup-$env_name-$(date +%Y%m%d-%H%M%S)"

    echo "💾 Creating backup: $backup_id (type: $backup_type)"

    # Create backup directory
    mkdir -p "backups/$backup_id"

    case $backup_type in
        "config")
            backup_environment_config "$env_name" "$backup_id"
            ;;
        "data")
            backup_environment_data "$env_name" "$backup_id"
            ;;
        "full")
            backup_environment_config "$env_name" "$backup_id"
            backup_environment_data "$env_name" "$backup_id"
            ;;
    esac

    # Create backup manifest
    cat > "backups/$backup_id/manifest.json" << EOF
{
  "backup_id": "$backup_id",
  "source_environment": "$env_name",
  "backup_type": "$backup_type",
  "created_at": "$(date -Iseconds)",
  "created_by": "$(whoami)",
  "components": []
}
EOF

    echo "✅ Backup created: $backup_id"
}

backup_environment_config() {
    local env_name=$1
    local backup_id=$2

    echo "📋 Backing up configuration for $env_name"

    # Backup Kubernetes configurations
    kubectl get all,configmaps,secrets -n "sunday-$env_name" -o yaml > \
        "backups/$backup_id/kubernetes-config.yaml"

    # Backup Terraform state
    cp -r "environments/$env_name/terraform" "backups/$backup_id/"

    # Backup environment configuration
    cp -r "environments/$env_name/config" "backups/$backup_id/"

    echo "✅ Configuration backup completed"
}

backup_environment_data() {
    local env_name=$1
    local backup_id=$2

    echo "🗄️ Backing up data for $env_name"

    # Create database snapshot
    aws rds create-db-snapshot \
        --db-cluster-identifier "sunday-$env_name" \
        --db-snapshot-identifier "$backup_id-db"

    # Backup Redis data
    kubectl exec -n "sunday-$env_name" deployment/redis -- \
        redis-cli BGSAVE

    # Copy Redis dump
    kubectl cp "sunday-$env_name/redis-deployment-xxx:/data/dump.rdb" \
        "backups/$backup_id/redis-dump.rdb"

    # Backup S3 data
    aws s3 sync "s3://sunday-$env_name-storage" \
        "backups/$backup_id/s3-data/" \
        --exclude "*" --include "*.json" --include "*.csv"

    echo "✅ Data backup completed"
}

validate_environment_name() {
    local name=$1

    # Check format: alphanumeric and hyphens only, 3-30 characters
    if [[ $name =~ ^[a-z0-9-]{3,30}$ ]]; then
        return 0
    else
        return 1
    fi
}

environment_exists() {
    local env_name=$1

    # Check if environment directory exists
    if [ -d "environments/$env_name" ]; then
        return 0
    fi

    # Check if EKS cluster exists
    aws eks describe-cluster --name "sunday-$env_name" &>/dev/null
    return $?
}

# Utility functions
get_environment_status() {
    local env_name=$1

    # Check EKS cluster status
    local cluster_status=$(aws eks describe-cluster \
        --name "sunday-$env_name" \
        --query 'cluster.status' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    # Check application status
    local app_status="UNKNOWN"
    if [ "$cluster_status" = "ACTIVE" ]; then
        local ready_pods=$(kubectl get pods -n "sunday-$env_name" \
            --field-selector=status.phase=Running \
            --no-headers 2>/dev/null | wc -l)

        local total_pods=$(kubectl get pods -n "sunday-$env_name" \
            --no-headers 2>/dev/null | wc -l)

        if [ "$ready_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
            app_status="HEALTHY"
        else
            app_status="DEGRADED"
        fi
    fi

    echo "$cluster_status:$app_status"
}

list_environments() {
    echo "📋 Environment Status Report"
    echo "=============================="

    for env_dir in environments/*/; do
        if [ -d "$env_dir" ]; then
            env_name=$(basename "$env_dir")
            status=$(get_environment_status "$env_name")
            cluster_status=$(echo "$status" | cut -d: -f1)
            app_status=$(echo "$status" | cut -d: -f2)

            case $cluster_status in
                "ACTIVE")
                    cluster_icon="✅"
                    ;;
                "CREATING"|"UPDATING")
                    cluster_icon="🔄"
                    ;;
                "NOT_FOUND")
                    cluster_icon="❌"
                    ;;
                *)
                    cluster_icon="❓"
                    ;;
            esac

            case $app_status in
                "HEALTHY")
                    app_icon="✅"
                    ;;
                "DEGRADED")
                    app_icon="⚠️"
                    ;;
                *)
                    app_icon="❓"
                    ;;
            esac

            printf "%-20s %s %-10s %s %-10s\n" \
                "$env_name" "$cluster_icon" "$cluster_status" "$app_icon" "$app_status"
        fi
    done
}

# Execute based on arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 {create|update|destroy|clone|backup|restore|list} [options]"
    echo ""
    echo "Commands:"
    echo "  create <env-name> [template]     Create new environment"
    echo "  update <env-name>                Update existing environment"
    echo "  destroy <env-name> [--force]     Destroy environment"
    echo "  clone <source> <target> [data]   Clone environment"
    echo "  backup <env-name> [type]         Backup environment"
    echo "  restore <env-name> <backup-id>   Restore from backup"
    echo "  list                             List all environments"
    exit 1
fi

if [ "$1" = "list" ]; then
    list_environments
fi
```

---

## Configuration Management

### Environment Configuration Templates

```yaml
# templates/environments/production/config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: sunday-{{ENVIRONMENT_NAME}}
data:
  NODE_ENV: "production"
  LOG_LEVEL: "warn"
  API_RATE_LIMIT: "1000"
  DATABASE_POOL_SIZE: "20"
  REDIS_CLUSTER_MODE: "true"
  CACHE_TTL: "3600"
  MONITORING_ENABLED: "true"
  METRICS_ENDPOINT: "/metrics"
  HEALTH_CHECK_INTERVAL: "30"
  DEPLOYMENT_ENVIRONMENT: "{{ENVIRONMENT_NAME}}"
  FEATURE_FLAGS: |
    {
      "new_dashboard": true,
      "advanced_analytics": true,
      "ai_recommendations": true,
      "real_time_collaboration": true
    }
  PERFORMANCE_SETTINGS: |
    {
      "max_concurrent_requests": 1000,
      "request_timeout": 30000,
      "keep_alive_timeout": 5000,
      "max_upload_size": "100MB"
    }
  SECURITY_SETTINGS: |
    {
      "session_timeout": 3600,
      "max_login_attempts": 5,
      "password_policy": "strong",
      "encryption_algorithm": "AES-256"
    }

---
# Application-specific configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: sunday-{{ENVIRONMENT_NAME}}
data:
  server.json: |
    {
      "port": 3000,
      "host": "0.0.0.0",
      "cors": {
        "origin": ["https://sunday.com", "https://app.sunday.com"],
        "credentials": true
      },
      "rateLimit": {
        "windowMs": 900000,
        "max": 1000
      },
      "security": {
        "helmet": true,
        "xss": true,
        "noSniff": true,
        "frameguard": true
      }
    }
  database.json: |
    {
      "connection": {
        "host": "postgres.{{ENVIRONMENT_NAME}}.cluster.local",
        "port": 5432,
        "database": "sunday_{{ENVIRONMENT_NAME}}",
        "ssl": true,
        "pool": {
          "min": 5,
          "max": 20,
          "acquireTimeoutMillis": 30000,
          "idleTimeoutMillis": 30000
        }
      },
      "migrations": {
        "directory": "./migrations",
        "tableName": "migrations"
      }
    }
  redis.json: |
    {
      "connection": {
        "host": "redis.{{ENVIRONMENT_NAME}}.cluster.local",
        "port": 6379,
        "db": 0,
        "keyPrefix": "sunday:{{ENVIRONMENT_NAME}}:",
        "retryStrategy": "exponential"
      },
      "cluster": {
        "enabled": true,
        "nodes": [
          {"host": "redis-0.{{ENVIRONMENT_NAME}}.cluster.local", "port": 6379},
          {"host": "redis-1.{{ENVIRONMENT_NAME}}.cluster.local", "port": 6379},
          {"host": "redis-2.{{ENVIRONMENT_NAME}}.cluster.local", "port": 6379}
        ]
      }
    }

---
# Frontend configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: sunday-{{ENVIRONMENT_NAME}}
data:
  nginx.conf: |
    server {
        listen 80;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;

        # Gzip compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1024;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # API proxy
        location /api/ {
            proxy_pass http://backend-service:80/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        # WebSocket proxy
        location /ws/ {
            proxy_pass http://backend-service:80/ws/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Static files
        location / {
            try_files $uri $uri/ /index.html;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Health check
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
  env.js: |
    window.ENV = {
      API_URL: 'https://{{ENVIRONMENT_NAME}}.sunday.com/api',
      WS_URL: 'wss://{{ENVIRONMENT_NAME}}.sunday.com/ws',
      ENVIRONMENT: '{{ENVIRONMENT_NAME}}',
      VERSION: '{{VERSION}}',
      SENTRY_DSN: '{{SENTRY_DSN}}',
      ANALYTICS_ID: '{{ANALYTICS_ID}}',
      FEATURES: {
        NEW_DASHBOARD: true,
        ADVANCED_ANALYTICS: true,
        AI_RECOMMENDATIONS: true,
        REAL_TIME_COLLABORATION: true
      }
    };
```

---

*This Environment Management System provides comprehensive lifecycle management for all Sunday.com deployment environments, ensuring consistency, reliability, and efficient resource utilization across the entire infrastructure.*

---

*Last Updated: December 2024*
*Next Review: Q1 2025*
*Maintained by: Deployment Specialist Team*