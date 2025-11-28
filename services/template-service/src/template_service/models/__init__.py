"""
MAESTRO Templates - Pydantic Models
Validation models for templates, manifests, and API requests/responses
"""

from .manifest import (
    ManifestPlaceholder,
    ManifestHooks,
    ManifestMetadata,
    ManifestDependencies,
    ManifestConfiguration,
    ManifestDocumentation,
    TemplateManifest
)

from .template import (
    TemplateBase,
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
    TemplateSearchQuery,
    TemplateCacheInfo
)

from .workflow import (
    Gap,
    GapSeverity,
    GapType,
    ActionType,
    VariantDecision,
    RecommendationStatus,
    RecommendationBase,
    Recommendation,
    RecommendationApprovalRequest,
    RecommendationRejectionRequest,
    RecommendationListResponse,
    WorkflowRunSummary,
    WorkflowRunListResponse
)

from .package import (
    # Enums
    PackageCategory,
    PackageStatus,
    SupportStatus,
    Severity,
    CompatibilityLevel,
    # Package models
    PackageBase,
    PackageCreate,
    PackageUpdate,
    PackageResponse,
    PackageListResponse,
    # Package version models
    PackageVersionBase,
    PackageVersionCreate,
    PackageVersionUpdate,
    PackageVersionResponse,
    # Security models
    SecurityAdvisoryBase,
    SecurityAdvisoryCreate,
    SecurityAdvisoryUpdate,
    SecurityAdvisoryResponse,
    # Deprecation models
    DeprecationNoticeBase,
    DeprecationNoticeCreate,
    DeprecationNoticeUpdate,
    DeprecationNoticeResponse,
    # Compatibility models
    CompatibilityMatrixBase,
    CompatibilityMatrixCreate,
    CompatibilityMatrixUpdate,
    CompatibilityMatrixResponse,
    # Usage models
    PackageUsageBase,
    PackageUsageCreate,
    PackageUsageUpdate,
    PackageUsageResponse,
    # Scan models
    PackageScanHistoryBase,
    PackageScanRequest,
    PackageScanResult,
    # Search models
    PackageSearchQuery,
    # Inventory models
    PackageInventoryItem,
    PackageInventoryReport,
    # Dashboard models
    PackageStatusSummary,
    SecurityDashboard,
    DeprecationDashboard,
)

__all__ = [
    # Manifest models
    "ManifestPlaceholder",
    "ManifestHooks",
    "ManifestMetadata",
    "ManifestDependencies",
    "ManifestConfiguration",
    "ManifestDocumentation",
    "TemplateManifest",

    # Template models
    "TemplateBase",
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateResponse",
    "TemplateListResponse",
    "TemplateSearchQuery",
    "TemplateCacheInfo",

    # Workflow models
    "Gap",
    "GapSeverity",
    "GapType",
    "ActionType",
    "VariantDecision",
    "RecommendationStatus",
    "RecommendationBase",
    "Recommendation",
    "RecommendationApprovalRequest",
    "RecommendationRejectionRequest",
    "RecommendationListResponse",
    "WorkflowRunSummary",
    "WorkflowRunListResponse",

    # Package enums
    "PackageCategory",
    "PackageStatus",
    "SupportStatus",
    "Severity",
    "CompatibilityLevel",
    # Package models
    "PackageBase",
    "PackageCreate",
    "PackageUpdate",
    "PackageResponse",
    "PackageListResponse",
    "PackageVersionBase",
    "PackageVersionCreate",
    "PackageVersionUpdate",
    "PackageVersionResponse",
    "SecurityAdvisoryBase",
    "SecurityAdvisoryCreate",
    "SecurityAdvisoryUpdate",
    "SecurityAdvisoryResponse",
    "DeprecationNoticeBase",
    "DeprecationNoticeCreate",
    "DeprecationNoticeUpdate",
    "DeprecationNoticeResponse",
    "CompatibilityMatrixBase",
    "CompatibilityMatrixCreate",
    "CompatibilityMatrixUpdate",
    "CompatibilityMatrixResponse",
    "PackageUsageBase",
    "PackageUsageCreate",
    "PackageUsageUpdate",
    "PackageUsageResponse",
    "PackageScanHistoryBase",
    "PackageScanRequest",
    "PackageScanResult",
    "PackageSearchQuery",
    "PackageInventoryItem",
    "PackageInventoryReport",
    "PackageStatusSummary",
    "SecurityDashboard",
    "DeprecationDashboard",
]