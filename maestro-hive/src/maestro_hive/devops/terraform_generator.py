#!/usr/bin/env python3
"""
Terraform Generator: Generates Infrastructure as Code for deployments.

This module handles:
- IaC generation for cloud resources
- Multi-cloud support (AWS, GCP, Azure)
- Resource templating
- Disaster recovery configurations
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    LOCAL = "local"


class ResourceType(Enum):
    """Types of infrastructure resources."""
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORK = "network"
    CONTAINER = "container"
    SERVERLESS = "serverless"
    QUEUE = "queue"
    CACHE = "cache"


@dataclass
class ResourceSpec:
    """Specification for an infrastructure resource."""
    resource_id: str
    name: str
    resource_type: ResourceType
    provider: CloudProvider
    config: Dict[str, Any]
    tags: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TerraformModule:
    """A generated Terraform module."""
    module_id: str
    name: str
    resources: List[ResourceSpec]
    variables: Dict[str, Any]
    outputs: Dict[str, str]
    code: str
    provider_config: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InfrastructurePlan:
    """A complete infrastructure plan."""
    plan_id: str
    name: str
    modules: List[TerraformModule]
    environment: str
    provider: CloudProvider
    estimated_cost: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class TerraformGenerator:
    """
    Generates Terraform configurations for infrastructure.

    Implements:
    - iac_generation: Generate Infrastructure as Code
    - cloud_integration: Support multiple cloud providers
    - disaster_recovery: Generate DR configurations
    - scalability_planning: Plan for scaling
    """

    # Resource templates by provider
    TEMPLATES = {
        CloudProvider.AWS: {
            ResourceType.COMPUTE: '''
resource "aws_instance" "{name}" {{
  ami           = var.ami_id
  instance_type = "{instance_type}"

  tags = {{
    Name = "{name}"
    Environment = var.environment
{tags}
  }}
}}
''',
            ResourceType.DATABASE: '''
resource "aws_db_instance" "{name}" {{
  identifier     = "{name}"
  engine         = "{engine}"
  engine_version = "{engine_version}"
  instance_class = "{instance_class}"

  allocated_storage = {storage_gb}

  tags = {{
    Name = "{name}"
    Environment = var.environment
  }}
}}
''',
            ResourceType.CONTAINER: '''
resource "aws_ecs_cluster" "{name}" {{
  name = "{name}"

  setting {{
    name  = "containerInsights"
    value = "enabled"
  }}

  tags = {{
    Name = "{name}"
    Environment = var.environment
  }}
}}
''',
        },
        CloudProvider.GCP: {
            ResourceType.COMPUTE: '''
resource "google_compute_instance" "{name}" {{
  name         = "{name}"
  machine_type = "{machine_type}"
  zone         = var.zone

  boot_disk {{
    initialize_params {{
      image = var.image
    }}
  }}

  labels = {{
    environment = var.environment
  }}
}}
''',
        },
        CloudProvider.AZURE: {
            ResourceType.COMPUTE: '''
resource "azurerm_virtual_machine" "{name}" {{
  name                  = "{name}"
  location              = var.location
  resource_group_name   = var.resource_group
  vm_size              = "{vm_size}"

  tags = {{
    environment = var.environment
  }}
}}
''',
        }
    }

    def __init__(self, default_provider: CloudProvider = CloudProvider.AWS):
        """Initialize the generator."""
        self.default_provider = default_provider
        self._modules: Dict[str, TerraformModule] = {}
        self._plans: Dict[str, InfrastructurePlan] = {}

    def generate_resource(
        self,
        name: str,
        resource_type: ResourceType,
        config: Dict[str, Any],
        provider: Optional[CloudProvider] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate Terraform code for a single resource.

        Implements iac_generation.
        """
        provider = provider or self.default_provider
        tags = tags or {}

        template = self.TEMPLATES.get(provider, {}).get(resource_type)
        if not template:
            logger.warning(f"No template for {provider.value}/{resource_type.value}")
            return self._generate_generic_resource(name, resource_type, config, tags)

        # Format tags
        tag_lines = "\n".join(f'    {k} = "{v}"' for k, v in tags.items())

        # Apply template
        code = template.format(
            name=name,
            tags=tag_lines,
            **config
        )

        return code.strip()

    def _generate_generic_resource(
        self,
        name: str,
        resource_type: ResourceType,
        config: Dict[str, Any],
        tags: Dict[str, str]
    ) -> str:
        """Generate a generic resource block."""
        config_lines = "\n  ".join(f'{k} = "{v}"' for k, v in config.items())
        tag_lines = "\n    ".join(f'{k} = "{v}"' for k, v in tags.items())

        return f'''
resource "{resource_type.value}" "{name}" {{
  {config_lines}

  tags = {{
    {tag_lines}
  }}
}}
'''.strip()

    def generate_module(
        self,
        name: str,
        resources: List[ResourceSpec],
        environment: str = "dev"
    ) -> TerraformModule:
        """
        Generate a complete Terraform module.

        Implements cloud_integration across resources.
        """
        resource_codes = []
        variables = {}
        outputs = {}

        # Determine provider from resources
        providers = set(r.provider for r in resources)
        primary_provider = list(providers)[0] if providers else self.default_provider

        # Generate provider config
        provider_config = self._generate_provider_config(primary_provider)

        # Generate each resource
        for resource in resources:
            code = self.generate_resource(
                name=resource.name,
                resource_type=resource.resource_type,
                config=resource.config,
                provider=resource.provider,
                tags=resource.tags
            )
            resource_codes.append(code)

            # Add outputs for the resource
            outputs[f"{resource.name}_id"] = f"${{{resource.resource_type.value}.{resource.name}.id}}"

        # Common variables
        variables = {
            "environment": {"default": environment, "type": "string"},
            "region": {"type": "string"},
            "project": {"type": "string"}
        }

        # Combine code
        full_code = "\n\n".join([provider_config] + resource_codes)

        module = TerraformModule(
            module_id=str(uuid.uuid4()),
            name=name,
            resources=resources,
            variables=variables,
            outputs=outputs,
            code=full_code,
            provider_config=provider_config
        )

        self._modules[module.module_id] = module
        logger.info(f"Generated module: {name} with {len(resources)} resources")

        return module

    def _generate_provider_config(self, provider: CloudProvider) -> str:
        """Generate provider configuration block."""
        configs = {
            CloudProvider.AWS: '''
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}
''',
            CloudProvider.GCP: '''
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}
''',
            CloudProvider.AZURE: '''
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}
'''
        }
        return configs.get(provider, "").strip()

    def generate_dr_config(
        self,
        primary_module: TerraformModule,
        dr_region: str
    ) -> TerraformModule:
        """
        Generate disaster recovery configuration.

        Implements disaster_recovery planning.
        """
        # Clone resources for DR region
        dr_resources = []
        for resource in primary_module.resources:
            dr_resource = ResourceSpec(
                resource_id=f"dr-{resource.resource_id}",
                name=f"{resource.name}-dr",
                resource_type=resource.resource_type,
                provider=resource.provider,
                config={**resource.config},
                tags={**resource.tags, "dr": "true"},
                dependencies=resource.dependencies
            )
            dr_resources.append(dr_resource)

        dr_module = self.generate_module(
            name=f"{primary_module.name}-dr",
            resources=dr_resources,
            environment="dr"
        )

        # Add replication configuration
        dr_module.code += "\n\n# DR Replication Configuration\n"
        dr_module.code += f"# Primary Region: var.region\n"
        dr_module.code += f"# DR Region: {dr_region}\n"

        logger.info(f"Generated DR config for module: {primary_module.name}")
        return dr_module

    def generate_scaling_config(
        self,
        resource_name: str,
        min_capacity: int,
        max_capacity: int,
        target_cpu: int = 70
    ) -> str:
        """
        Generate auto-scaling configuration.

        Implements scalability_planning.
        """
        return f'''
resource "aws_appautoscaling_target" "{resource_name}_target" {{
  max_capacity       = {max_capacity}
  min_capacity       = {min_capacity}
  resource_id        = "service/{resource_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}}

resource "aws_appautoscaling_policy" "{resource_name}_policy" {{
  name               = "{resource_name}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.{resource_name}_target.resource_id
  scalable_dimension = aws_appautoscaling_target.{resource_name}_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.{resource_name}_target.service_namespace

  target_tracking_scaling_policy_configuration {{
    predefined_metric_specification {{
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }}
    target_value = {target_cpu}
  }}
}}
'''

    def create_plan(
        self,
        name: str,
        modules: List[TerraformModule],
        environment: str,
        provider: CloudProvider
    ) -> InfrastructurePlan:
        """Create a complete infrastructure plan."""
        plan = InfrastructurePlan(
            plan_id=str(uuid.uuid4()),
            name=name,
            modules=modules,
            environment=environment,
            provider=provider
        )
        self._plans[plan.plan_id] = plan
        return plan

    def export_plan(self, plan_id: str) -> Dict[str, str]:
        """Export plan as file contents."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {}

        files = {}
        for module in plan.modules:
            files[f"modules/{module.name}/main.tf"] = module.code
            files[f"modules/{module.name}/variables.tf"] = self._generate_variables_file(module.variables)
            files[f"modules/{module.name}/outputs.tf"] = self._generate_outputs_file(module.outputs)

        return files

    def _generate_variables_file(self, variables: Dict[str, Any]) -> str:
        """Generate variables.tf content."""
        lines = []
        for name, config in variables.items():
            var_type = config.get("type", "string")
            default = config.get("default")
            default_line = f'default = "{default}"' if default else ""
            lines.append(f'''
variable "{name}" {{
  type    = {var_type}
  {default_line}
}}
''')
        return "\n".join(lines)

    def _generate_outputs_file(self, outputs: Dict[str, str]) -> str:
        """Generate outputs.tf content."""
        lines = []
        for name, value in outputs.items():
            lines.append(f'''
output "{name}" {{
  value = {value}
}}
''')
        return "\n".join(lines)


# Factory function
def create_terraform_generator(
    default_provider: CloudProvider = CloudProvider.AWS
) -> TerraformGenerator:
    """Create a new TerraformGenerator instance."""
    return TerraformGenerator(default_provider=default_provider)
