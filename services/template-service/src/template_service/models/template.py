"""
Template Models
Pydantic models for template database records and API requests/responses
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from .manifest import TemplateEngine, TemplateCategory


class TemplateBase(BaseModel):
    """Base template model with common fields"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10, max_length=1000)
    category: TemplateCategory
    language: str = Field(..., max_length=50)
    framework: Optional[str] = Field(None, max_length=100)
    version: str = Field(..., max_length=20)
    tags: List[str] = Field(default_factory=list)
    organization: Optional[str] = Field(None, max_length=100)
    persona: Optional[str] = Field(None, max_length=255, description="Target persona for this template")

    # Git-based storage
    git_url: Optional[str] = Field(None, max_length=500, description="Git repository URL")
    git_branch: Optional[str] = Field("main", max_length=100, description="Git branch to clone")
    templating_engine: TemplateEngine = Field(TemplateEngine.JINJA2)

    # Quality scores
    quality_score: Optional[float] = Field(None, ge=0, le=100)
    security_score: Optional[int] = Field(None, ge=0, le=100)
    performance_score: Optional[int] = Field(None, ge=0, le=100)
    maintainability_score: Optional[int] = Field(None, ge=0, le=100)

    # Pinning feature for "golden" templates
    is_pinned: bool = Field(default=False, description="Whether template is pinned as recommended")
    quality_tier: Optional[str] = Field(default="standard", description="Quality tier: gold, silver, bronze, standard")
    pin_reason: Optional[str] = Field(None, max_length=500, description="Reason for pinning this template")
    pinned_at: Optional[datetime] = Field(None, description="When template was pinned")
    pinned_by: Optional[str] = Field(None, max_length=100, description="User who pinned the template")

    class Config:
        use_enum_values = True


class TemplateCreate(TemplateBase):
    """Model for creating a new template"""
    created_by: str = Field(..., max_length=100)
    file_path: Optional[str] = Field(None, max_length=500)  # For backward compatibility

    @field_validator('git_url', 'file_path')
    @classmethod
    def validate_storage(cls, v):
        """Ensure at least one storage method is provided"""
        # This will be checked at the model validator level
        return v

    @field_validator('git_url')
    @classmethod
    def validate_git_url(cls, v):
        """Basic Git URL validation"""
        if v:
            valid_prefixes = ('https://', 'http://', 'git@', 'ssh://')
            if not any(v.startswith(prefix) for prefix in valid_prefixes):
                raise ValueError(
                    f"Git URL must start with one of: {valid_prefixes}"
                )
        return v


class TemplateUpdate(BaseModel):
    """Model for updating an existing template"""
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    tags: Optional[List[str]] = None
    git_url: Optional[str] = Field(None, max_length=500)
    git_branch: Optional[str] = Field(None, max_length=100)
    quality_score: Optional[float] = Field(None, ge=0, le=100)
    security_score: Optional[int] = Field(None, ge=0, le=100)
    performance_score: Optional[int] = Field(None, ge=0, le=100)
    maintainability_score: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = Field(None, pattern="^(draft|review|approved|deprecated)$")

    # Pinning fields
    is_pinned: Optional[bool] = None
    quality_tier: Optional[str] = Field(None, pattern="^(gold|silver|bronze|standard)$")
    pin_reason: Optional[str] = Field(None, max_length=500)


class TemplateResponse(TemplateBase):
    """Model for template API responses"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: str

    # Status and validation
    status: str
    manifest_validated: bool = False
    manifest_validation_date: Optional[datetime] = None

    # Usage statistics
    usage_count: int = 0
    success_rate: Optional[float] = Field(None, ge=0, le=100)
    last_accessed_at: Optional[datetime] = None

    # Storage info
    storage_tier: int = 2
    cache_path: Optional[str] = None
    file_path: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True


class TemplateCacheInfo(BaseModel):
    """Template cache information"""
    template_id: UUID
    version: str
    git_commit_hash: Optional[str] = None
    archive_path: str
    archive_format: str
    file_size_bytes: int
    checksum_sha256: Optional[str] = None
    cached_at: datetime
    last_accessed: datetime
    access_count: int
    clone_duration_ms: Optional[int] = None
    archive_duration_ms: Optional[int] = None

    class Config:
        orm_mode = True


class TemplateListResponse(BaseModel):
    """Paginated list of templates"""
    total: int = Field(..., description="Total number of templates")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    templates: List[TemplateResponse] = Field(..., description="List of templates")

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there's a next page"""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1


class TemplateSearchQuery(BaseModel):
    """Search query parameters"""
    query: Optional[str] = Field(None, description="Search query string")
    language: Optional[str] = Field(None, description="Filter by language")
    framework: Optional[str] = Field(None, description="Filter by framework")
    category: Optional[TemplateCategory] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (AND logic)")
    min_quality_score: Optional[float] = Field(None, ge=0, le=100, description="Minimum quality score")
    status: Optional[str] = Field(None, pattern="^(draft|review|approved|deprecated)$")
    organization: Optional[str] = Field(None, description="Filter by organization")

    # Pinning filters
    pinned: Optional[bool] = Field(None, description="Filter by pinned status")
    quality_tier: Optional[str] = Field(None, pattern="^(gold|silver|bronze|standard)$", description="Filter by quality tier")

    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    # Sorting
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    class Config:
        use_enum_values = True


class TemplateDownloadRequest(BaseModel):
    """Request for downloading a template"""
    version: str = Field("main", description="Git branch/tag version to download")
    format: str = Field("tar.gz", pattern="^(tar\.gz|zip)$", description="Archive format")


class TemplateRegisterRequest(BaseModel):
    """Request for registering a new template from Git"""
    git_url: str = Field(..., max_length=500, description="Git repository URL")
    git_branch: str = Field("main", max_length=100, description="Git branch")
    organization: Optional[str] = Field(None, max_length=100, description="Organization name")
    auto_validate: bool = Field(True, description="Automatically validate manifest")

    @field_validator('git_url')
    @classmethod
    def validate_git_url(cls, v):
        """Validate Git URL format"""
        valid_prefixes = ('https://', 'http://', 'git@', 'ssh://')
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Git URL must start with one of: {valid_prefixes}")
        return v


class TemplateValidationResult(BaseModel):
    """Result of template manifest validation"""
    valid: bool
    manifest_score: Optional[int] = Field(None, ge=0, le=100)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    manifest_data: Optional[dict] = None


class SeedingReport(BaseModel):
    """Report from database seeding operation"""
    total_templates: int = 0
    templates_added: int = 0
    templates_updated: int = 0
    templates_skipped: int = 0
    templates_failed: int = 0
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CacheClearResult(BaseModel):
    """Result of cache clearing operation"""
    cache_entries_deleted: int = 0
    files_deleted: int = 0
    space_freed_bytes: int = 0
    errors: List[str] = Field(default_factory=list)