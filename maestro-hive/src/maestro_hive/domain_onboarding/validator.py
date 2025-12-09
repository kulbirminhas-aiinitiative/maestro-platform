"""Domain Validator - Validate domain onboarding."""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from .models import DomainProfile, OnboardingStatus, OnboardingTask

logger = logging.getLogger(__name__)


class DomainValidator:
    """Validates domain onboarding completeness."""
    
    def __init__(self):
        self._validations: Dict[UUID, Dict] = {}
    
    def validate(self, profile: DomainProfile) -> Dict:
        """Validate domain onboarding."""
        profile.status = OnboardingStatus.VALIDATING
        
        validation = {
            "profile_id": str(profile.id),
            "domain_name": profile.name,
            "checks": [],
            "passed": True,
            "warnings": []
        }
        
        # Check all requirements satisfied
        unsatisfied = [r for r in profile.requirements if not r.satisfied]
        if unsatisfied:
            validation["checks"].append({
                "name": "requirements_satisfied",
                "passed": False,
                "message": f"{len(unsatisfied)} requirements not satisfied"
            })
            validation["passed"] = False
        else:
            validation["checks"].append({
                "name": "requirements_satisfied",
                "passed": True,
                "message": "All requirements satisfied"
            })
        
        # Check generated assets
        total_assets = sum(len(v) for v in profile.generated_assets.values())
        if total_assets == 0:
            validation["checks"].append({
                "name": "assets_generated",
                "passed": False,
                "message": "No assets generated"
            })
            validation["passed"] = False
        else:
            validation["checks"].append({
                "name": "assets_generated",
                "passed": True,
                "message": f"{total_assets} assets generated"
            })
        
        # Check task completion
        incomplete = [t for t in profile.tasks if t.status != OnboardingStatus.COMPLETED]
        if incomplete:
            validation["warnings"].append(f"{len(incomplete)} tasks incomplete")
        
        # Update profile status
        if validation["passed"]:
            profile.status = OnboardingStatus.COMPLETED
            from datetime import datetime
            profile.completed_at = datetime.utcnow()
        else:
            profile.status = OnboardingStatus.FAILED
        
        self._validations[profile.id] = validation
        logger.info("Validated domain %s: %s", profile.name, "PASSED" if validation["passed"] else "FAILED")
        return validation
    
    def get_validation(self, profile_id: UUID) -> Optional[Dict]:
        return self._validations.get(profile_id)
    
    def get_onboarding_report(self, profile: DomainProfile) -> Dict:
        """Generate onboarding completion report."""
        return {
            "domain": profile.name,
            "industry": profile.industry,
            "status": profile.status.value,
            "progress": profile.get_progress(),
            "requirements": len(profile.requirements),
            "satisfied_requirements": sum(1 for r in profile.requirements if r.satisfied),
            "tasks_completed": sum(1 for t in profile.tasks if t.status == OnboardingStatus.COMPLETED),
            "total_tasks": len(profile.tasks),
            "generated_assets": {k: len(v) for k, v in profile.generated_assets.items()},
            "validation": self._validations.get(profile.id, {})
        }
