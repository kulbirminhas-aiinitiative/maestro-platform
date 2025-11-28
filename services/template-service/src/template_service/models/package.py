"""
Package Registry Models
Pydantic models for package registry database records and API requests/responses
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class PackageCategory(str, Enum):
    """Package ecosystem categories"""
    PYTHON = "python"
    NPM = "npm"
    SYSTEM = "system"
    DOCKER = "docker"
    OTHER = "other"


class PackageStatus(str, Enum):
    """Package status"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EOL = "eol"
    SECURITY_RISK = "security_risk"


class SupportStatus(str, Enum):
    """Version support status"""
    SUPPORTED = "supported"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"
    UNSUPPORTED = "unsupported"


class Severity(str, Enum):
    """Security advisory severity"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CompatibilityLevel(str, Enum):
    """Compatibility level between package versions"""
    FULL = "full"
    PARTIAL = "partial"
    INCOMPATIBLE = "incompatible"
    UNTESTED = "untested"


# =============================================================================
# PACKAGE MODELS
# =============================================================================

class PackageBase(BaseModel):
    """Base package model"""
    name: str = Field(..., min_length=1, max_length=255)
    category: PackageCategory
    ecosystem: str = Field(..., max_length=50, description="pip, npm, apt, yarn, poetry, etc.")
    description: Optional[str] = None
    homepage_url: Optional[str] = Field(None, max_length=500)
    repository_url: Optional[str] = Field(None, max_length=500)
    license: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    primary_use_case: Optional[str] = Field(None, max_length=255)

    class Config:
        use_enum_values = True


class PackageCreate(PackageBase):
    """Model for creating a new package"""
    status: PackageStatus = PackageStatus.ACTIVE
    created_by: str = Field(default="system", max_length=100)


class PackageUpdate(BaseModel):
    """Model for updating package metadata"""
    description: Optional[str] = None
    homepage_url: Optional[str] = Field(None, max_length=500)
    repository_url: Optional[str] = Field(None, max_length=500)
    license: Optional[str] = Field(None, max_length=100)
    status: Optional[PackageStatus] = None
    deprecation_date: Optional[datetime] = None
    eol_date: Optional[datetime] = None
    replacement_package: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class PackageResponse(PackageBase):
    """Package API response"""
    id: UUID
    status: PackageStatus
    deprecation_date: Optional[datetime] = None
    eol_date: Optional[datetime] = None
    replacement_package: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_checked_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


# =============================================================================
# PACKAGE VERSION MODELS
# =============================================================================

class PackageVersionBase(BaseModel):
    """Base package version model"""
    version: str = Field(..., max_length=50)
    version_normalized: str = Field(..., max_length=50)
    release_date: Optional[datetime] = None
    release_notes_url: Optional[str] = Field(None, max_length=500)
    changelog_url: Optional[str] = Field(None, max_length=500)
    is_prerelease: bool = False
    is_yanked: bool = False
    yanked_reason: Optional[str] = None
    support_status: SupportStatus = SupportStatus.SUPPORTED
    support_end_date: Optional[datetime] = None
    lts_version: bool = False
    python_requires: Optional[str] = Field(None, max_length=100)
    node_requires: Optional[str] = Field(None, max_length=100)

    class Config:
        use_enum_values = True


class PackageVersionCreate(PackageVersionBase):
    """Model for creating a package version"""
    package_id: UUID


class PackageVersionUpdate(BaseModel):
    """Model for updating package version"""
    release_notes_url: Optional[str] = Field(None, max_length=500)
    changelog_url: Optional[str] = Field(None, max_length=500)
    support_status: Optional[SupportStatus] = None
    support_end_date: Optional[datetime] = None
    is_yanked: Optional[bool] = None
    yanked_reason: Optional[str] = None


class PackageVersionResponse(PackageVersionBase):
    """Package version API response"""
    id: UUID
    package_id: UUID
    has_vulnerabilities: bool
    vulnerability_count: int
    critical_vulnerability_count: int
    download_count: int
    star_count: int
    contributor_count: int
    package_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    package_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


# =============================================================================
# SECURITY ADVISORY MODELS
# =============================================================================

class SecurityAdvisoryBase(BaseModel):
    """Base security advisory model"""
    cve_id: Optional[str] = Field(None, max_length=50)
    advisory_id: Optional[str] = Field(None, max_length=100)
    advisory_url: Optional[str] = Field(None, max_length=500)
    severity: Severity
    cvss_score: Optional[Decimal] = Field(None, ge=0, le=10)
    affected_versions: List[str]
    patched_versions: Optional[List[str]] = Field(default_factory=list)
    title: str = Field(..., max_length=500)
    description: str
    vulnerability_type: Optional[str] = Field(None, max_length=100)
    cwe_ids: Optional[List[str]] = Field(default_factory=list)
    attack_vector: Optional[str] = Field(None, max_length=50)
    attack_complexity: Optional[str] = Field(None, max_length=20)
    privileges_required: Optional[str] = Field(None, max_length=20)
    user_interaction: Optional[str] = Field(None, max_length=20)
    remediation: Optional[str] = None
    workaround: Optional[str] = None
    patch_available: bool = False
    patch_release_date: Optional[datetime] = None
    published_at: datetime
    discovered_by: Optional[str] = Field(None, max_length=255)
    reported_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class SecurityAdvisoryCreate(SecurityAdvisoryBase):
    """Model for creating a security advisory"""
    package_id: UUID


class SecurityAdvisoryUpdate(BaseModel):
    """Model for updating a security advisory"""
    severity: Optional[Severity] = None
    cvss_score: Optional[Decimal] = Field(None, ge=0, le=10)
    patched_versions: Optional[List[str]] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    workaround: Optional[str] = None
    status: Optional[str] = None
    verified: Optional[bool] = None
    false_positive: Optional[bool] = None


class SecurityAdvisoryResponse(SecurityAdvisoryBase):
    """Security advisory API response"""
    id: UUID
    package_id: UUID
    status: str
    verified: bool
    false_positive: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


# =============================================================================
# DEPRECATION NOTICE MODELS
# =============================================================================

class DeprecationNoticeBase(BaseModel):
    """Base deprecation notice model"""
    deprecated_versions: List[str]
    deprecation_date: datetime
    deprecation_reason: str
    announcement_date: Optional[datetime] = None
    grace_period_end_date: Optional[datetime] = None
    eol_date: Optional[datetime] = None
    replacement_version: Optional[str] = Field(None, max_length=50)
    migration_guide_url: Optional[str] = Field(None, max_length=500)
    migration_effort: Optional[str] = Field(None, pattern="^(trivial|low|medium|high|very_high)$")
    automated_migration_available: bool = False
    codemod_available: bool = False
    codemod_url: Optional[str] = Field(None, max_length=500)
    breaking_change_severity: Optional[str] = Field(
        None, pattern="^(none|minor|moderate|major|critical)$"
    )
    official_announcement_url: Optional[str] = Field(None, max_length=500)
    community_discussion_url: Optional[str] = Field(None, max_length=500)


class DeprecationNoticeCreate(DeprecationNoticeBase):
    """Model for creating a deprecation notice"""
    package_id: UUID
    replacement_package_id: Optional[UUID] = None


class DeprecationNoticeUpdate(BaseModel):
    """Model for updating a deprecation notice"""
    grace_period_end_date: Optional[datetime] = None
    eol_date: Optional[datetime] = None
    migration_guide_url: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(announced|active|completed)$")
    affected_projects_count: Optional[int] = None


class DeprecationNoticeResponse(DeprecationNoticeBase):
    """Deprecation notice API response"""
    id: UUID
    package_id: UUID
    replacement_package_id: Optional[UUID] = None
    affected_projects_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# =============================================================================
# COMPATIBILITY MATRIX MODELS
# =============================================================================

class CompatibilityMatrixBase(BaseModel):
    """Base compatibility matrix model"""
    version_a: str = Field(..., max_length=50)
    version_b: str = Field(..., max_length=50)
    is_compatible: bool
    compatibility_level: CompatibilityLevel
    confidence_score: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)
    has_breaking_changes: bool = False
    breaking_changes_description: Optional[str] = None
    migration_complexity: Optional[str] = Field(
        None, pattern="^(trivial|easy|moderate|complex|major)$"
    )
    migration_guide_url: Optional[str] = Field(None, max_length=500)
    tested_on_platform: Optional[str] = Field(None, max_length=100)
    test_date: Optional[datetime] = None
    tested_by: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

    class Config:
        use_enum_values = True


class CompatibilityMatrixCreate(CompatibilityMatrixBase):
    """Model for creating a compatibility entry"""
    package_a_id: UUID
    package_b_id: UUID


class CompatibilityMatrixUpdate(BaseModel):
    """Model for updating compatibility entry"""
    is_compatible: Optional[bool] = None
    compatibility_level: Optional[CompatibilityLevel] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    has_breaking_changes: Optional[bool] = None
    breaking_changes_description: Optional[str] = None
    migration_guide_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class CompatibilityMatrixResponse(CompatibilityMatrixBase):
    """Compatibility matrix API response"""
    id: UUID
    package_a_id: UUID
    package_b_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


# =============================================================================
# PACKAGE USAGE MODELS
# =============================================================================

class PackageUsageBase(BaseModel):
    """Base package usage model"""
    version: str = Field(..., max_length=50)
    project_name: str = Field(..., max_length=255)
    project_path: Optional[str] = Field(None, max_length=500)
    project_type: Optional[str] = Field(None, max_length=50)
    constraint_specified: str = Field(..., max_length=200)
    resolved_version: str = Field(..., max_length=50)
    is_direct_dependency: bool
    dependency_depth: int = Field(default=0, ge=0)
    detected_via: str = Field(..., max_length=50)
    file_path: Optional[str] = Field(None, max_length=500)


class PackageUsageCreate(PackageUsageBase):
    """Model for creating package usage record"""
    package_id: UUID


class PackageUsageUpdate(BaseModel):
    """Model for updating package usage"""
    is_outdated: Optional[bool] = None
    latest_compatible_version: Optional[str] = Field(None, max_length=50)
    versions_behind: Optional[int] = Field(None, ge=0)
    has_security_issues: Optional[bool] = None


class PackageUsageResponse(PackageUsageBase):
    """Package usage API response"""
    id: UUID
    package_id: UUID
    is_outdated: bool
    latest_compatible_version: Optional[str] = None
    versions_behind: int
    has_security_issues: bool
    last_detected_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# =============================================================================
# PACKAGE SCAN MODELS
# =============================================================================

class PackageScanHistoryBase(BaseModel):
    """Base package scan history model"""
    scan_id: UUID = Field(default_factory=lambda: UUID(int=0))
    scan_type: str = Field(..., pattern="^(full|incremental|security|compatibility|dependency)$")
    scan_started_at: datetime = Field(default_factory=datetime.utcnow)
    projects_scanned: Optional[List[str]] = Field(default_factory=list)
    triggered_by: str = Field(..., max_length=100)


class PackageScanRequest(BaseModel):
    """Request to initiate a package scan"""
    scan_type: str = Field("full", pattern="^(full|incremental|security|compatibility|dependency)$")
    projects: Optional[List[str]] = None  # None = scan all projects
    include_transitive: bool = True
    check_security: bool = True
    check_compatibility: bool = True


class PackageScanResult(BaseModel):
    """Package scan result"""
    scan_id: UUID
    scan_status: str
    scan_started_at: datetime
    scan_completed_at: Optional[datetime] = None
    scan_duration_ms: Optional[int] = None
    total_packages: int = 0
    outdated_packages: int = 0
    deprecated_packages: int = 0
    vulnerable_packages: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0
    packages_requiring_update: List[str] = Field(default_factory=list)
    packages_requiring_replacement: List[str] = Field(default_factory=list)
    errors_encountered: Optional[dict] = None


# =============================================================================
# SEARCH AND FILTER MODELS
# =============================================================================

class PackageSearchQuery(BaseModel):
    """Package search query parameters"""
    query: Optional[str] = Field(None, description="Search query string")
    category: Optional[PackageCategory] = None
    ecosystem: Optional[str] = None
    status: Optional[PackageStatus] = None
    has_vulnerabilities: Optional[bool] = None
    is_deprecated: Optional[bool] = None
    min_severity: Optional[Severity] = None

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    # Sorting
    sort_by: str = Field("name", pattern="^(name|category|status|created_at|updated_at)$")
    sort_order: str = Field("asc", pattern="^(asc|desc)$")

    class Config:
        use_enum_values = True


class PackageListResponse(BaseModel):
    """Paginated list of packages"""
    total: int
    page: int
    page_size: int
    packages: List[PackageResponse]

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


# =============================================================================
# PACKAGE INVENTORY MODELS
# =============================================================================

class PackageInventoryItem(BaseModel):
    """Single item in package inventory"""
    name: str
    category: str
    ecosystem: str
    current_version: str
    latest_version: Optional[str] = None
    constraint: str
    project_name: str
    file_path: str
    status: str
    has_security_issues: bool
    vulnerabilities: List[str] = Field(default_factory=list)
    is_deprecated: bool
    eol_date: Optional[datetime] = None
    replacement_package: Optional[str] = None


class PackageInventoryReport(BaseModel):
    """Complete package inventory report"""
    scan_date: datetime
    total_packages: int
    total_projects: int
    packages_by_category: dict
    packages_by_status: dict
    security_summary: dict
    deprecation_summary: dict
    packages: List[PackageInventoryItem]


# =============================================================================
# DASHBOARD MODELS
# =============================================================================

class PackageStatusSummary(BaseModel):
    """Package status summary for dashboard"""
    total_packages: int
    active_packages: int
    deprecated_packages: int
    eol_packages: int
    packages_with_vulnerabilities: int
    critical_vulnerabilities: int
    packages_needing_update: int


class SecurityDashboard(BaseModel):
    """Security dashboard summary"""
    total_advisories: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    packages_at_risk: List[str]
    recent_advisories: List[SecurityAdvisoryResponse]


class DeprecationDashboard(BaseModel):
    """Deprecation dashboard summary"""
    total_deprecations: int
    packages_approaching_eol: List[PackageResponse]
    migration_required: List[DeprecationNoticeResponse]
    projects_affected: int
