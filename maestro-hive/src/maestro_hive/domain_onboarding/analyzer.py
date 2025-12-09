"""Domain Analyzer - Analyze domain requirements."""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from .models import DomainProfile, DomainRequirement, RequirementType, OnboardingStatus

logger = logging.getLogger(__name__)


class DomainAnalyzer:
    """Analyzes domains to identify onboarding requirements."""
    
    COMMON_REQUIREMENTS = {
        "software": [
            ("Code Review Knowledge", RequirementType.KNOWLEDGE),
            ("Git Integration", RequirementType.TOOL),
            ("Developer Persona", RequirementType.PERSONA),
        ],
        "healthcare": [
            ("Medical Terminology", RequirementType.KNOWLEDGE),
            ("HIPAA Compliance", RequirementType.KNOWLEDGE),
            ("Healthcare Persona", RequirementType.PERSONA),
        ],
        "finance": [
            ("Financial Regulations", RequirementType.KNOWLEDGE),
            ("Risk Analysis", RequirementType.TOOL),
            ("Financial Advisor Persona", RequirementType.PERSONA),
        ],
        "default": [
            ("Domain Knowledge Base", RequirementType.KNOWLEDGE),
            ("Domain-Specific Tools", RequirementType.TOOL),
            ("Expert Persona", RequirementType.PERSONA),
        ]
    }
    
    def __init__(self):
        self._profiles: Dict[UUID, DomainProfile] = {}
    
    def create_profile(self, name: str, description: str, industry: str) -> DomainProfile:
        """Create a new domain profile."""
        profile = DomainProfile(name=name, description=description, industry=industry)
        self._profiles[profile.id] = profile
        logger.info("Created domain profile: %s", name)
        return profile
    
    def analyze(self, profile_id: UUID) -> List[DomainRequirement]:
        """Analyze domain and identify requirements."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return []
        
        profile.status = OnboardingStatus.ANALYZING
        requirements = []
        
        # Get industry-specific requirements
        industry_reqs = self.COMMON_REQUIREMENTS.get(
            profile.industry.lower(), 
            self.COMMON_REQUIREMENTS["default"]
        )
        
        for name, req_type in industry_reqs:
            req = DomainRequirement(
                req_type=req_type,
                name=f"{profile.name} {name}",
                description=f"{name} for {profile.name} domain",
                priority=5
            )
            requirements.append(req)
            profile.add_requirement(req)
        
        logger.info("Identified %d requirements for %s", len(requirements), profile.name)
        return requirements
    
    def get_profile(self, profile_id: UUID) -> Optional[DomainProfile]:
        return self._profiles.get(profile_id)
    
    def list_profiles(self) -> List[Dict]:
        return [p.to_dict() for p in self._profiles.values()]
