"""
Exception classes for Maestro ML SDK
"""


class MaestroMLException(Exception):
    """Base exception for all Maestro ML SDK errors"""
    pass


class ConfigurationException(MaestroMLException):
    """Raised when configuration is invalid or missing"""
    pass


class ModelNotFoundException(MaestroMLException):
    """Raised when a model cannot be found in the registry"""
    pass


class ModelVersionNotFoundException(MaestroMLException):
    """Raised when a specific model version cannot be found"""
    pass


class DeploymentException(MaestroMLException):
    """Raised when model deployment fails"""
    pass


class TrainingException(MaestroMLException):
    """Raised when training job submission or execution fails"""
    pass


class ExperimentNotFoundException(MaestroMLException):
    """Raised when an experiment cannot be found"""
    pass


class KubernetesException(MaestroMLException):
    """Raised when Kubernetes operations fail"""
    pass


class MLflowException(MaestroMLException):
    """Raised when MLflow operations fail"""
    pass


class ValidationException(MaestroMLException):
    """Raised when input validation fails"""
    pass


class AuthenticationException(MaestroMLException):
    """Raised when authentication fails"""
    pass


class AuthorizationException(MaestroMLException):
    """Raised when user lacks permissions for an operation"""
    pass
