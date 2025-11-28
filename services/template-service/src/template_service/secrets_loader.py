"""
AWS Secrets Manager and SSM Parameter Store Loader
Supports both real AWS and LocalStack for local development
"""

import os
import json
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class SecretsLoader:
    """Load secrets from AWS Secrets Manager or environment variables"""

    def __init__(self):
        self.aws_enabled = os.getenv("AWS_SECRETS_ENABLED", "false").lower() == "true"
        self.aws_endpoint = os.getenv("AWS_ENDPOINT_URL")  # For LocalStack
        self.aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.secrets_prefix = os.getenv("AWS_SECRETS_PREFIX", "maestro/dev")

        # Initialize AWS clients if enabled
        self.secrets_client = None
        self.ssm_client = None

        if self.aws_enabled:
            self._init_aws_clients()

        logger.info(
            "secrets_loader_initialized",
            aws_enabled=self.aws_enabled,
            endpoint=self.aws_endpoint or "AWS",
            region=self.aws_region
        )

    def _init_aws_clients(self):
        """Initialize AWS clients (supports LocalStack)"""
        try:
            import boto3

            # Client configuration
            client_kwargs = {
                "region_name": self.aws_region
            }

            # Add endpoint URL for LocalStack
            if self.aws_endpoint:
                client_kwargs["endpoint_url"] = self.aws_endpoint
                logger.info("using_localstack_endpoint", endpoint=self.aws_endpoint)

            # Create clients
            self.secrets_client = boto3.client("secretsmanager", **client_kwargs)
            self.ssm_client = boto3.client("ssm", **client_kwargs)

            logger.info("aws_clients_initialized")

        except ImportError:
            logger.warning(
                "boto3_not_installed",
                message="boto3 required for AWS Secrets Manager. Falling back to environment variables."
            )
            self.aws_enabled = False
        except Exception as e:
            logger.error("aws_client_init_failed", error=str(e))
            self.aws_enabled = False

    def get_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret from AWS Secrets Manager or environment variable

        Args:
            secret_name: Secret name (e.g., "jwt-secret")
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        # Try AWS Secrets Manager first
        if self.aws_enabled and self.secrets_client:
            full_secret_name = f"{self.secrets_prefix}/{secret_name}"

            try:
                response = self.secrets_client.get_secret_value(SecretId=full_secret_name)

                if "SecretString" in response:
                    secret_value = response["SecretString"]

                    # Try to parse as JSON
                    try:
                        secret_json = json.loads(secret_value)
                        # If JSON, return the first value (for simple key-value secrets)
                        if isinstance(secret_json, dict):
                            return list(secret_json.values())[0] if secret_json else default
                        return secret_value
                    except json.JSONDecodeError:
                        # Not JSON, return as-is
                        return secret_value

                logger.warning(
                    "secret_not_found_in_aws",
                    secret_name=full_secret_name,
                    using_default=default is not None
                )

            except self.secrets_client.exceptions.ResourceNotFoundException:
                logger.warning(
                    "secret_does_not_exist",
                    secret_name=full_secret_name,
                    using_default=default is not None
                )
            except Exception as e:
                logger.error(
                    "secret_fetch_error",
                    secret_name=full_secret_name,
                    error=str(e),
                    using_default=default is not None
                )

        # Fall back to environment variable
        env_var_name = secret_name.upper().replace("-", "_")
        env_value = os.getenv(env_var_name, default)

        if env_value:
            logger.info(
                "using_environment_variable",
                secret_name=secret_name,
                env_var=env_var_name
            )

        return env_value

    def get_ssm_parameter(self, parameter_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get parameter from AWS SSM Parameter Store or environment variable

        Args:
            parameter_name: Parameter name (e.g., "/maestro/dev/log-level")
            default: Default value if parameter not found

        Returns:
            Parameter value or default
        """
        # Try AWS SSM first
        if self.aws_enabled and self.ssm_client:
            try:
                response = self.ssm_client.get_parameter(
                    Name=parameter_name,
                    WithDecryption=True
                )

                parameter_value = response["Parameter"]["Value"]
                logger.info(
                    "ssm_parameter_fetched",
                    parameter_name=parameter_name
                )
                return parameter_value

            except self.ssm_client.exceptions.ParameterNotFound:
                logger.warning(
                    "ssm_parameter_not_found",
                    parameter_name=parameter_name,
                    using_default=default is not None
                )
            except Exception as e:
                logger.error(
                    "ssm_parameter_fetch_error",
                    parameter_name=parameter_name,
                    error=str(e),
                    using_default=default is not None
                )

        # Fall back to environment variable
        env_var_name = parameter_name.strip("/").upper().replace("/", "_").replace("-", "_")
        env_value = os.getenv(env_var_name, default)

        return env_value

    def load_all_secrets(self) -> Dict[str, Any]:
        """
        Load all application secrets

        Returns:
            Dictionary of secret values
        """
        secrets = {
            # JWT Configuration
            "jwt_secret_key": self.get_secret(
                "jwt-secret",
                default=os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production")
            ),
            "jwt_algorithm": self.get_ssm_parameter(
                f"{self.secrets_prefix}/jwt-algorithm",
                default=os.getenv("JWT_ALGORITHM", "HS256")
            ),

            # Database Configuration
            "database_url": self.get_secret(
                "database-url",
                default=os.getenv("DATABASE_URL")
            ),
            "db_username": self.get_secret(
                "db-username",
                default=os.getenv("DB_USERNAME")
            ),
            "db_password": self.get_secret(
                "db-password",
                default=os.getenv("DB_PASSWORD")
            ),

            # Redis Configuration
            "redis_url": self.get_secret(
                "redis-url",
                default=os.getenv("REDIS_URL")
            ),
            "redis_password": self.get_secret(
                "redis-password",
                default=os.getenv("REDIS_PASSWORD")
            ),

            # User Passwords
            "admin_password": self.get_secret(
                "admin-password",
                default=os.getenv("ADMIN_PASSWORD", "admin123")
            ),
            "developer_password": self.get_secret(
                "developer-password",
                default=os.getenv("DEVELOPER_PASSWORD", "dev123")
            ),
            "viewer_password": self.get_secret(
                "viewer-password",
                default=os.getenv("VIEWER_PASSWORD", "viewer123")
            ),

            # API Keys
            "admin_api_key": self.get_secret(
                "admin-api-key",
                default=os.getenv("ADMIN_API_KEY")
            ),

            # GitHub Token
            "github_token": self.get_secret(
                "github-token",
                default=os.getenv("GITHUB_TOKEN")
            ),
        }

        logger.info(
            "all_secrets_loaded",
            source="AWS Secrets Manager" if self.aws_enabled else "Environment Variables",
            secrets_count=len(secrets)
        )

        return secrets


# Global secrets loader instance
_secrets_loader: Optional[SecretsLoader] = None


def get_secrets_loader() -> SecretsLoader:
    """Get or create global secrets loader instance"""
    global _secrets_loader

    if _secrets_loader is None:
        _secrets_loader = SecretsLoader()

    return _secrets_loader


def load_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to load a single secret

    Args:
        secret_name: Secret name
        default: Default value

    Returns:
        Secret value or default
    """
    loader = get_secrets_loader()
    return loader.get_secret(secret_name, default)


def load_all_secrets() -> Dict[str, Any]:
    """
    Convenience function to load all secrets

    Returns:
        Dictionary of all secrets
    """
    loader = get_secrets_loader()
    return loader.load_all_secrets()


# Example usage
if __name__ == "__main__":
    import structlog

    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ]
    )

    # Load all secrets
    secrets = load_all_secrets()

    print("\n=== Loaded Secrets ===")
    for key, value in secrets.items():
        # Mask sensitive values
        if value and len(value) > 8:
            masked_value = f"{value[:4]}...{value[-4:]}"
        else:
            masked_value = "****"

        print(f"{key}: {masked_value}")

    print("\n=== Individual Secret ===")
    jwt_secret = load_secret("jwt-secret")
    print(f"JWT Secret: {jwt_secret[:10] if jwt_secret else 'None'}...")
