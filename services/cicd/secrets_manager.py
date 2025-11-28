#!/usr/bin/env python3
"""
AWS Secrets Manager Integration for Maestro Services

Handles secure secret management:
- Fetching secrets from AWS Secrets Manager
- Runtime secret injection (no filesystem storage)
- Secret rotation support
- Environment-specific secret paths
- Fallback to local .env for development
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


@dataclass
class SecretConfig:
    """Secret configuration"""

    service_id: str
    secret_name: str
    environment: str
    region: str


class SecretsManager:
    """Manages secrets for Maestro services"""

    def __init__(
        self,
        project_root: Path,
        environment: str,
        region: str = "us-east-1",
        use_local_fallback: bool = True,
    ):
        self.project_root = project_root
        self.environment = environment
        self.region = region
        self.use_local_fallback = use_local_fallback
        self.registry_path = project_root / "maestro_services_registry.json"
        self.registry = self._load_registry()

        # Initialize AWS client if available
        self.secrets_client = None
        if BOTO3_AVAILABLE:
            try:
                self.secrets_client = boto3.client(
                    "secretsmanager", region_name=self.region
                )
            except Exception as e:
                print(f"⚠️  Could not initialize AWS Secrets Manager: {e}")
                if not self.use_local_fallback:
                    raise

    def _load_registry(self) -> dict:
        """Load service registry"""
        with open(self.registry_path) as f:
            return json.load(f)

    def get_secret_name(self, service_id: str) -> str:
        """
        Generate AWS Secrets Manager secret name

        Format: maestro/{environment}/{service_id}
        Examples:
            - maestro/production/automation-service
            - maestro/demo/template-service
        """
        return f"maestro/{self.environment}/{service_id}"

    def fetch_secret_from_aws(self, secret_name: str) -> Optional[Dict[str, str]]:
        """
        Fetch secret from AWS Secrets Manager

        Args:
            secret_name: Name of the secret

        Returns:
            Dict of secret key-value pairs, or None if not found
        """
        if not self.secrets_client:
            print(f"⚠️  AWS Secrets Manager not available for {secret_name}")
            return None

        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)

            # Parse secret string (JSON format expected)
            if "SecretString" in response:
                secret_data = json.loads(response["SecretString"])
                return secret_data
            elif "SecretBinary" in response:
                # Binary secrets not supported in this implementation
                print(f"⚠️  Binary secret not supported: {secret_name}")
                return None

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                print(f"⚠️  Secret not found in AWS: {secret_name}")
            elif error_code == "AccessDeniedException":
                print(f"⚠️  Access denied to secret: {secret_name}")
            else:
                print(f"⚠️  Error fetching secret {secret_name}: {e}")
            return None
        except Exception as e:
            print(f"⚠️  Unexpected error fetching secret {secret_name}: {e}")
            return None

    def load_local_env_file(self, service_path: Path) -> Optional[Dict[str, str]]:
        """
        Load secrets from local .env file (development fallback)

        Args:
            service_path: Path to service directory

        Returns:
            Dict of environment variables
        """
        env_file = service_path / ".env"
        if not env_file.exists():
            env_example = service_path / ".env.example"
            if env_example.exists():
                print(f"⚠️  .env not found, using .env.example for {service_path.name}")
                env_file = env_example
            else:
                return None

        env_vars = {}
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue

                    # Parse KEY=VALUE
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        env_vars[key.strip()] = value

            return env_vars

        except Exception as e:
            print(f"⚠️  Error loading .env file: {e}")
            return None

    def get_service_secrets(self, service: dict) -> Dict[str, str]:
        """
        Get secrets for a service

        Priority:
        1. AWS Secrets Manager (production/demo)
        2. Local .env file (development fallback)

        Args:
            service: Service configuration from registry

        Returns:
            Dict of secret key-value pairs
        """
        service_id = service["id"]
        service_name = service["name"]
        service_path = self.project_root / service["source_path"]

        print(f"🔐 Fetching secrets for {service_name}")

        secrets = {}

        # Try AWS Secrets Manager first (if not development)
        if self.environment != "development" and self.secrets_client:
            secret_name = self.get_secret_name(service_id)
            aws_secrets = self.fetch_secret_from_aws(secret_name)

            if aws_secrets:
                secrets.update(aws_secrets)
                print(f"   ✅ Loaded {len(aws_secrets)} secrets from AWS")
                return secrets
            else:
                print(f"   ⚠️  AWS secrets not found, trying local fallback")

        # Fallback to local .env file
        if self.use_local_fallback:
            local_secrets = self.load_local_env_file(service_path)
            if local_secrets:
                secrets.update(local_secrets)
                print(f"   ✅ Loaded {len(local_secrets)} secrets from local .env")
                return secrets
            else:
                print(f"   ⚠️  No local .env file found")

        # No secrets found
        if not secrets:
            print(f"   ⚠️  No secrets available for {service_name}")

        return secrets

    def create_env_file_for_deployment(
        self, service: dict, target_path: Path
    ) -> bool:
        """
        Create .env file for deployment with fetched secrets

        Args:
            service: Service configuration
            target_path: Path to write .env file

        Returns:
            True if successful
        """
        secrets = self.get_service_secrets(service)

        if not secrets:
            print(f"   ⚠️  No secrets to write for {service['name']}")
            return False

        try:
            env_file = target_path / ".env"
            with open(env_file, "w") as f:
                f.write(f"# Generated secrets for {service['name']}\n")
                f.write(f"# Environment: {self.environment}\n")
                f.write(f"# DO NOT COMMIT THIS FILE\n\n")

                for key, value in sorted(secrets.items()):
                    f.write(f"{key}={value}\n")

            # Set restrictive permissions (owner read/write only)
            os.chmod(env_file, 0o600)

            print(f"   ✅ Created .env file with {len(secrets)} secrets")
            return True

        except Exception as e:
            print(f"   ❌ Error creating .env file: {e}")
            return False

    def create_secret_in_aws(
        self,
        service_id: str,
        secrets: Dict[str, str],
        description: Optional[str] = None,
    ) -> bool:
        """
        Create or update a secret in AWS Secrets Manager

        Args:
            service_id: Service identifier
            secrets: Dict of secret key-value pairs
            description: Optional description

        Returns:
            True if successful
        """
        if not self.secrets_client:
            print("❌ AWS Secrets Manager not available")
            return False

        secret_name = self.get_secret_name(service_id)
        secret_string = json.dumps(secrets, indent=2)

        if not description:
            description = (
                f"Secrets for {service_id} in {self.environment} environment"
            )

        try:
            # Try to create new secret
            self.secrets_client.create_secret(
                Name=secret_name,
                Description=description,
                SecretString=secret_string,
            )
            print(f"✅ Created secret: {secret_name}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceExistsException":
                # Secret exists, update it
                try:
                    self.secrets_client.update_secret(
                        SecretId=secret_name, SecretString=secret_string
                    )
                    print(f"✅ Updated secret: {secret_name}")
                    return True
                except Exception as update_error:
                    print(f"❌ Error updating secret: {update_error}")
                    return False
            else:
                print(f"❌ Error creating secret: {e}")
                return False

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

    def upload_secrets_from_env_file(self, service: dict) -> bool:
        """
        Upload secrets from local .env file to AWS Secrets Manager

        Useful for initial secret setup or migration

        Args:
            service: Service configuration

        Returns:
            True if successful
        """
        service_path = self.project_root / service["source_path"]
        local_secrets = self.load_local_env_file(service_path)

        if not local_secrets:
            print(f"❌ No local secrets found for {service['name']}")
            return False

        print(f"📤 Uploading {len(local_secrets)} secrets to AWS")

        # Filter out non-secret values (e.g., service URLs that are public)
        # This is a basic filter - customize based on your needs
        secret_keys = [
            key
            for key in local_secrets.keys()
            if any(
                sensitive in key.lower()
                for sensitive in [
                    "password",
                    "secret",
                    "key",
                    "token",
                    "credential",
                    "api",
                ]
            )
        ]

        if not secret_keys:
            print("⚠️  No sensitive secrets detected to upload")
            return False

        secrets_to_upload = {key: local_secrets[key] for key in secret_keys}

        return self.create_secret_in_aws(service["id"], secrets_to_upload)

    def rotate_secret(self, service_id: str, new_secrets: Dict[str, str]) -> bool:
        """
        Rotate secrets for a service

        Args:
            service_id: Service identifier
            new_secrets: New secret values

        Returns:
            True if successful
        """
        print(f"🔄 Rotating secrets for {service_id}")
        return self.create_secret_in_aws(service_id, new_secrets)

    def list_all_secrets(self) -> List[str]:
        """
        List all secrets for current environment

        Returns:
            List of secret names
        """
        if not self.secrets_client:
            print("❌ AWS Secrets Manager not available")
            return []

        try:
            response = self.secrets_client.list_secrets(
                Filters=[
                    {"Key": "name", "Values": [f"maestro/{self.environment}/"]}
                ]
            )

            secret_names = [secret["Name"] for secret in response.get("SecretList", [])]
            return secret_names

        except Exception as e:
            print(f"❌ Error listing secrets: {e}")
            return []

    def prepare_all_service_secrets(self) -> bool:
        """
        Prepare secrets for all active services

        Creates .env files in deployment directory with secrets

        Returns:
            True if all successful
        """
        services = [
            s for s in self.registry["services"] if s.get("status") == "active"
        ]

        print(f"\n{'='*60}")
        print(f"Preparing Secrets - {self.environment}")
        print(f"{'='*60}\n")

        all_success = True

        for service in services:
            service_path = self.project_root / service["source_path"]
            success = self.create_env_file_for_deployment(service, service_path)
            all_success = all_success and success
            print()

        if all_success:
            print("✅ All service secrets prepared")
        else:
            print("⚠️  Some services missing secrets (non-critical)")

        return all_success


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="AWS Secrets Manager Integration for Maestro Services"
    )
    parser.add_argument(
        "action",
        choices=["fetch", "upload", "create", "list", "prepare"],
        help="Action to perform",
    )
    parser.add_argument(
        "--environment",
        "-e",
        choices=["development", "demo", "production"],
        default="development",
        help="Target environment",
    )
    parser.add_argument("--service", "-s", help="Specific service ID")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument(
        "--secrets-json", help="JSON string of secrets for create action"
    )

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Create secrets manager
    manager = SecretsManager(project_root, args.environment, args.region)

    # Execute action
    if args.action == "fetch":
        if not args.service:
            print("❌ --service required for fetch")
            sys.exit(1)

        # Find service
        service = next(
            (s for s in manager.registry["services"] if s["id"] == args.service), None
        )
        if not service:
            print(f"❌ Service not found: {args.service}")
            sys.exit(1)

        secrets = manager.get_service_secrets(service)
        print(f"\n📋 Secrets for {service['name']}:")
        for key in sorted(secrets.keys()):
            print(f"   {key}=***")

    elif args.action == "upload":
        if not args.service:
            print("❌ --service required for upload")
            sys.exit(1)

        # Find service
        service = next(
            (s for s in manager.registry["services"] if s["id"] == args.service), None
        )
        if not service:
            print(f"❌ Service not found: {args.service}")
            sys.exit(1)

        success = manager.upload_secrets_from_env_file(service)
        sys.exit(0 if success else 1)

    elif args.action == "create":
        if not args.service or not args.secrets_json:
            print("❌ --service and --secrets-json required for create")
            sys.exit(1)

        try:
            secrets = json.loads(args.secrets_json)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            sys.exit(1)

        success = manager.create_secret_in_aws(args.service, secrets)
        sys.exit(0 if success else 1)

    elif args.action == "list":
        secrets = manager.list_all_secrets()
        print(f"\n📋 Secrets in {args.environment}:\n")
        for secret in secrets:
            print(f"   {secret}")
        print(f"\nTotal: {len(secrets)}")

    elif args.action == "prepare":
        success = manager.prepare_all_service_secrets()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
