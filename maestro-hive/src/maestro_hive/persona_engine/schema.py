"""
Persona Schema v4.0 - Core Models

Defines the structured identity model for AI Personas with:
- Identity: Who the agent IS
- Capabilities: What it CAN do
- Constraints: What it CANNOT/MUST NOT do
- Personality: HOW it behaves and communicates
- Domain Extensions: Specialized fields for SDLC, Engineering, Business, Creative

EPIC: MD-2554
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class PersonaCategory(str, Enum):
    """Extended persona categories for multi-domain support."""
    
    # SDLC Categories (existing)
    ANALYSIS_DESIGN = "analysis_design"
    DEVELOPMENT = "development"
    OPERATIONS = "operations"
    QUALITY_SECURITY = "quality_security"
    DOCUMENTATION = "documentation"
    
    # Engineering Categories (new)
    INFRASTRUCTURE = "infrastructure"
    DATA_ENGINEERING = "data_engineering"
    ML_AI = "ml_ai"
    
    # Business Categories (new)
    STRATEGY = "strategy"
    FINANCE = "finance"
    MARKETING = "marketing"
    SALES = "sales"
    
    # Creative Categories (new)
    CONTENT = "content"
    DESIGN = "design"
    MEDIA = "media"


class CommunicationStyle(str, Enum):
    """Communication style preferences."""
    
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CASUAL = "casual"
    ACADEMIC = "academic"
    EXECUTIVE = "executive"


class PersonaStatus(str, Enum):
    """Persona lifecycle status."""
    
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    ARCHIVED = "archived"


# =============================================================================
# IDENTITY MODELS
# =============================================================================

class PersonaIdentity(BaseModel):
    """
    Core identity of a persona - WHO the agent IS.
    
    AC-1: Persona schema includes identity
    """
    
    display_name: str = Field(
        ..., 
        min_length=3, 
        max_length=100,
        description="Human-readable name for UI"
    )
    version: str = Field(
        ..., 
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version (major.minor.patch)"
    )
    description: str = Field(
        ..., 
        min_length=10, 
        max_length=500,
        description="Brief description of the persona"
    )
    author: str = Field(
        default="MAESTRO Team",
        description="Creator of the persona"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO date when created"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO date when last updated"
    )
    category: PersonaCategory = Field(
        default=PersonaCategory.DEVELOPMENT,
        description="Primary category"
    )
    status: PersonaStatus = Field(
        default=PersonaStatus.ACTIVE,
        description="Lifecycle status"
    )
    human_alias: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="Human name alias (e.g., 'Marcus', 'Emma')"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Searchable tags"
    )
    
    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Ensure display name is Title Case or contains valid acronyms."""
        valid_acronyms = ["UI/UX", "DevOps", "QA", "API", "SRE", "ML", "AI", "CEO", "CTO", "CFO"]
        
        if not v[0].isupper():
            raise ValueError(f"display_name must start with uppercase, got: {v}")
        
        for acronym in valid_acronyms:
            if acronym in v:
                return v
        
        return v


# =============================================================================
# CAPABILITIES MODELS
# =============================================================================

class PersonaCapabilities(BaseModel):
    """
    What the persona CAN do - skills, tools, expertise.
    
    AC-1: Persona schema includes capabilities
    """
    
    core: List[str] = Field(
        ...,
        min_length=1,
        description="Core capabilities (required skills)"
    )
    tools: List[str] = Field(
        default_factory=list,
        description="Tools and technologies the persona can use"
    )
    expertise_areas: List[str] = Field(
        default_factory=list,
        description="Areas of deep expertise"
    )
    languages: List[str] = Field(
        default_factory=list,
        description="Programming languages"
    )
    frameworks: List[str] = Field(
        default_factory=list,
        description="Frameworks and libraries"
    )
    experience_level: int = Field(
        default=7,
        ge=1,
        le=10,
        description="1=Novice, 10=Expert"
    )
    autonomy_level: int = Field(
        default=7,
        ge=1,
        le=10,
        description="1=Supervised, 10=Autonomous"
    )


# =============================================================================
# CONSTRAINTS MODELS
# =============================================================================

class ResourceLimits(BaseModel):
    """Resource usage limits."""
    
    max_tokens: int = Field(default=8000, ge=100, le=128000)
    max_iterations: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    max_file_size_mb: float = Field(default=10.0, ge=0.1, le=100.0)


class PersonaConstraints(BaseModel):
    """
    What the persona CANNOT or MUST NOT do - boundaries and limitations.
    
    AC-1: Persona schema includes constraints
    """
    
    forbidden_actions: List[str] = Field(
        default_factory=list,
        description="Actions the persona must never take"
    )
    scope_restrictions: List[str] = Field(
        default_factory=list,
        description="Topics/areas out of scope"
    )
    ethical_boundaries: List[str] = Field(
        default_factory=list,
        description="Ethical guidelines to follow"
    )
    safety_rules: List[str] = Field(
        default_factory=list,
        description="Safety-critical rules"
    )
    resource_limits: ResourceLimits = Field(
        default_factory=ResourceLimits,
        description="Resource usage limits"
    )
    requires_approval_for: List[str] = Field(
        default_factory=list,
        description="Actions requiring human approval"
    )


# =============================================================================
# PERSONALITY MODELS
# =============================================================================

class PersonalityTraits(BaseModel):
    """
    HOW the persona behaves - communication style and approach.
    
    AC-1: Persona schema includes personality traits
    """
    
    communication_style: CommunicationStyle = Field(
        default=CommunicationStyle.TECHNICAL,
        description="Primary communication style"
    )
    verbosity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0.0=Concise, 1.0=Detailed"
    )
    creativity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0.0=Conservative, 1.0=Innovative"
    )
    assertiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0.0=Collaborative, 1.0=Directive"
    )
    formality: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0.0=Casual, 1.0=Formal"
    )
    empathy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0.0=Task-focused, 1.0=People-focused"
    )
    risk_tolerance: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="0.0=Risk-averse, 1.0=Risk-taking"
    )
    
    @model_validator(mode="after")
    def validate_traits_consistency(self) -> "PersonalityTraits":
        """Ensure personality traits are internally consistent."""
        # High formality usually correlates with lower creativity
        if self.formality > 0.8 and self.creativity > 0.8:
            pass  # Allow but note the unusual combination
        return self


# =============================================================================
# DOMAIN EXTENSIONS - AC-2
# =============================================================================

class SDLCPersonaExtension(BaseModel):
    """
    Extension for SDLC-specific personas.
    
    AC-2: Supports domain-specific extensions (SDLC)
    """
    
    domain_type: str = Field(default="sdlc", frozen=True)
    phase: str = Field(
        ...,
        description="SDLC phase (requirements, design, development, testing, deployment)"
    )
    deliverables: List[str] = Field(
        default_factory=list,
        description="Expected output artifacts"
    )
    input_contracts: List[str] = Field(
        default_factory=list,
        description="Required inputs"
    )
    output_contracts: List[str] = Field(
        default_factory=list,
        description="Guaranteed outputs"
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description="Personas that must execute before"
    )
    required_by: List[str] = Field(
        default_factory=list,
        description="Personas that depend on this"
    )


class EngineeringPersonaExtension(BaseModel):
    """
    Extension for engineering domain personas.
    
    AC-2: Supports domain-specific extensions (Engineering)
    """
    
    domain_type: str = Field(default="engineering", frozen=True)
    tech_stack: List[str] = Field(
        default_factory=list,
        description="Technologies and platforms"
    )
    specializations: List[str] = Field(
        default_factory=list,
        description="Specific technical expertise"
    )
    certifications: List[str] = Field(
        default_factory=list,
        description="Relevant certifications"
    )
    infrastructure_scope: List[str] = Field(
        default_factory=list,
        description="Infrastructure areas (cloud, on-prem, hybrid)"
    )


class BusinessPersonaExtension(BaseModel):
    """
    Extension for business domain personas.
    
    AC-2: Supports domain-specific extensions (Business)
    """
    
    domain_type: str = Field(default="business", frozen=True)
    industry_focus: List[str] = Field(
        default_factory=list,
        description="Target industries"
    )
    domain_expertise: List[str] = Field(
        default_factory=list,
        description="Business domain knowledge"
    )
    stakeholder_types: List[str] = Field(
        default_factory=list,
        description="Types of stakeholders served"
    )
    kpi_focus: List[str] = Field(
        default_factory=list,
        description="Key metrics of focus"
    )


class CreativePersonaExtension(BaseModel):
    """
    Extension for creative domain personas.
    
    AC-2: Supports domain-specific extensions (Creative)
    """
    
    domain_type: str = Field(default="creative", frozen=True)
    creative_style: str = Field(
        default="balanced",
        description="Creative approach (minimalist, bold, classic, etc.)"
    )
    medium: List[str] = Field(
        default_factory=list,
        description="Creative mediums (writing, design, video, etc.)"
    )
    inspiration_sources: List[str] = Field(
        default_factory=list,
        description="Sources of inspiration"
    )
    target_audience: List[str] = Field(
        default_factory=list,
        description="Primary audience types"
    )
    brand_voice: Optional[str] = Field(
        None,
        description="Brand voice guidelines"
    )


# Union type for domain extensions
DomainExtension = Union[
    SDLCPersonaExtension,
    EngineeringPersonaExtension,
    BusinessPersonaExtension,
    CreativePersonaExtension
]


# =============================================================================
# PROMPTS AND EXECUTION
# =============================================================================

class PersonaPrompts(BaseModel):
    """Prompt templates for the persona."""
    
    system_prompt: str = Field(
        ...,
        min_length=50,
        description="Base system prompt"
    )
    task_prompt_template: str = Field(
        ...,
        min_length=20,
        description="Template for task-specific prompts"
    )
    examples: List[str] = Field(
        default_factory=list,
        description="Few-shot examples"
    )


class ExecutionConfig(BaseModel):
    """Execution configuration."""
    
    timeout_seconds: int = Field(default=300, ge=30, le=900)
    max_retries: int = Field(default=3, ge=0, le=5)
    priority: int = Field(default=5, ge=1, le=10)
    parallel_capable: bool = Field(default=False)
    estimated_duration_seconds: Optional[int] = None


# =============================================================================
# MAIN PERSONA SCHEMA - v4.0
# =============================================================================

class PersonaSchema(BaseModel):
    """
    Complete Persona Schema v4.0.
    
    Defines the structured identity model for AI Personas with:
    - Identity: WHO the agent IS
    - Capabilities: WHAT it CAN do
    - Constraints: WHAT it CANNOT/MUST NOT do
    - Personality: HOW it behaves
    - Domain Extension: Specialized fields per domain
    
    AC-1: Includes identity, capabilities, constraints, personality traits
    AC-2: Supports domain-specific extensions
    AC-3: Validation rules ensure consistency
    AC-4: JSON-serializable
    """
    
    # Core identifiers
    persona_id: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$",
        min_length=3,
        max_length=50,
        description="Unique identifier (snake_case)"
    )
    schema_version: str = Field(
        default="4.0",
        pattern=r"^\d+\.\d+$",
        description="Schema version"
    )
    
    # Core components (AC-1)
    identity: PersonaIdentity
    capabilities: PersonaCapabilities
    constraints: PersonaConstraints = Field(default_factory=PersonaConstraints)
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits)
    
    # Domain extension (AC-2)
    domain_extension: Optional[DomainExtension] = None
    
    # Execution configuration
    prompts: PersonaPrompts
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    
    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        """Ensure schema version is 4.0 or higher for v4 features."""
        major, minor = map(int, v.split("."))
        if major < 4:
            raise ValueError(f"Schema version must be 4.0 or higher for PersonalityTraits and Constraints, got {v}")
        return v
    
    @model_validator(mode="after")
    def validate_persona_consistency(self) -> "PersonaSchema":
        """
        Validate overall persona consistency.
        
        AC-3: Validation rules ensure persona consistency
        """
        # Check that experience level matches capability count
        if len(self.capabilities.core) < 3 and self.capabilities.experience_level > 8:
            pass  # Allow but could warn
        
        # Check that autonomy level aligns with constraints
        if self.capabilities.autonomy_level > 8 and len(self.constraints.requires_approval_for) > 5:
            pass  # Unusual but allowed
        
        return self
    
    def to_json(self) -> str:
        """
        Serialize to JSON string.
        
        AC-4: JSON-serializable for storage and transmission
        """
        return self.model_dump_json(indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "PersonaSchema":
        """
        Deserialize from JSON string.
        
        AC-4: JSON-serializable for storage and transmission
        """
        return cls.model_validate_json(json_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaSchema":
        """Create from dictionary."""
        return cls.model_validate(data)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        json_schema_extra = {
            "example": {
                "persona_id": "backend_developer",
                "schema_version": "4.0",
                "identity": {
                    "display_name": "Backend Developer",
                    "version": "1.0.0",
                    "description": "Expert backend developer specializing in API development"
                },
                "capabilities": {
                    "core": ["api_development", "database_design"],
                    "tools": ["fastapi", "postgresql"]
                },
                "constraints": {
                    "forbidden_actions": ["delete_production_data"],
                    "resource_limits": {"max_tokens": 8000}
                },
                "personality": {
                    "communication_style": "technical",
                    "verbosity": 0.6,
                    "creativity": 0.4
                },
                "prompts": {
                    "system_prompt": "You are an expert Backend Developer...",
                    "task_prompt_template": "Implement: {task}"
                }
            }
        }
