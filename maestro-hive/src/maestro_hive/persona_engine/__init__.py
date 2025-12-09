"""
Persona Engine - Enhanced AI Persona Schema v4.0

This module defines the structured identity model for AI Personas,
capturing WHO an agent IS, WHAT it CAN do, and HOW it BEHAVES.

EPIC: MD-2554 - Persona Schema Definition

Acceptance Criteria:
- AC-1: Schema includes identity, capabilities, constraints, personality traits
- AC-2: Supports domain-specific extensions (SDLC, Engineering, Business, Creative)
- AC-3: Validation rules ensure persona consistency
- AC-4: JSON-serializable for storage and transmission
- AC-5: Existing 11+ personas migrate to new schema
"""

from .schema import (
    PersonaSchema,
    PersonaIdentity,
    PersonaCapabilities,
    PersonaConstraints,
    PersonalityTraits,
    DomainExtension,
    SDLCPersonaExtension,
    EngineeringPersonaExtension,
    BusinessPersonaExtension,
    CreativePersonaExtension,
    PersonaCategory,
    CommunicationStyle,
)
from .registry import PersonaRegistry
from .validator import PersonaValidator
from .migrator import PersonaMigrator

__version__ = "4.0.0"
__all__ = [
    "PersonaSchema",
    "PersonaIdentity",
    "PersonaCapabilities",
    "PersonaConstraints",
    "PersonalityTraits",
    "DomainExtension",
    "SDLCPersonaExtension",
    "EngineeringPersonaExtension",
    "BusinessPersonaExtension",
    "CreativePersonaExtension",
    "PersonaCategory",
    "CommunicationStyle",
    "PersonaRegistry",
    "PersonaValidator",
    "PersonaMigrator",
]
