"""Domain Onboarding Framework - Onboard new domains to the AI Foundry."""
from .models import DomainProfile, OnboardingTask, DomainRequirement
from .analyzer import DomainAnalyzer
from .generator import AssetGenerator
from .validator import DomainValidator

__version__ = "1.0.0"
__all__ = ["DomainProfile", "OnboardingTask", "DomainRequirement",
           "DomainAnalyzer", "AssetGenerator", "DomainValidator"]
