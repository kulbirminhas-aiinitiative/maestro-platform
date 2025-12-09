"""Asset Generator - Generate domain-specific assets."""
import logging
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from .models import DomainProfile, DomainRequirement, OnboardingTask, OnboardingStatus, RequirementType

logger = logging.getLogger(__name__)


class AssetGenerator:
    """Generates assets for domain onboarding."""
    
    def __init__(self):
        self._generated: Dict[UUID, List[Dict]] = {}
    
    def generate_for_requirement(self, profile: DomainProfile, requirement: DomainRequirement) -> OnboardingTask:
        """Generate assets for a requirement."""
        task = OnboardingTask(
            domain_id=profile.id,
            name=f"Generate {requirement.name}",
            requirement_id=requirement.id,
            status=OnboardingStatus.GENERATING
        )
        profile.add_task(task)
        
        # Generate based on requirement type
        assets = []
        if requirement.req_type == RequirementType.KNOWLEDGE:
            assets = self._generate_knowledge(profile, requirement)
        elif requirement.req_type == RequirementType.PERSONA:
            assets = self._generate_persona(profile, requirement)
        elif requirement.req_type == RequirementType.TOOL:
            assets = self._generate_tool_config(profile, requirement)
        
        # Record generated assets
        asset_type = requirement.req_type.value
        if asset_type not in profile.generated_assets:
            profile.generated_assets[asset_type] = []
        
        for asset in assets:
            asset_id = uuid4()
            profile.generated_assets[asset_type].append(asset_id)
            requirement.artifacts.append(asset_id)
        
        task.complete({"assets_generated": len(assets), "asset_ids": [str(a) for a in requirement.artifacts]})
        requirement.satisfied = True
        
        logger.info("Generated %d assets for requirement %s", len(assets), requirement.name)
        return task
    
    def _generate_knowledge(self, profile: DomainProfile, req: DomainRequirement) -> List[Dict]:
        """Generate knowledge artifacts."""
        return [
            {"type": "knowledge", "title": f"{profile.name} Core Concepts", "domain": profile.name},
            {"type": "knowledge", "title": f"{profile.name} Best Practices", "domain": profile.name},
            {"type": "knowledge", "title": f"{profile.name} Common Patterns", "domain": profile.name},
        ]
    
    def _generate_persona(self, profile: DomainProfile, req: DomainRequirement) -> List[Dict]:
        """Generate persona artifacts."""
        return [
            {"type": "persona", "name": f"{profile.name} Expert", "role": "domain_expert",
             "capabilities": ["domain_knowledge", "analysis", "recommendation"]}
        ]
    
    def _generate_tool_config(self, profile: DomainProfile, req: DomainRequirement) -> List[Dict]:
        """Generate tool configuration artifacts."""
        return [
            {"type": "tool_config", "name": f"{profile.name} Analyzer", "category": "analysis"},
            {"type": "tool_config", "name": f"{profile.name} Reporter", "category": "reporting"},
        ]
    
    def generate_all(self, profile: DomainProfile) -> List[OnboardingTask]:
        """Generate assets for all requirements."""
        profile.status = OnboardingStatus.GENERATING
        tasks = []
        
        for req in profile.requirements:
            if not req.satisfied:
                task = self.generate_for_requirement(profile, req)
                tasks.append(task)
        
        return tasks
