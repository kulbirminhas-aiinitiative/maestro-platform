"""
Persona Validator - Ensures persona schema consistency.

AC-3: Validation rules ensure persona consistency

EPIC: MD-2554
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import ValidationError

from .schema import (
    PersonaSchema,
    PersonaIdentity,
    PersonaCapabilities,
    PersonaConstraints,
    PersonalityTraits,
)


class ValidationResult:
    """Result of persona validation."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid: bool = True
        self.score: float = 100.0
    
    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False
        self.score -= 10.0
    
    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)
        self.score -= 2.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "score": max(0.0, self.score),
            "errors": self.errors,
            "warnings": self.warnings,
        }


class PersonaValidator:
    """
    Validates persona schemas for consistency and completeness.
    
    AC-3: Validation rules ensure persona consistency
    """
    
    # Required core capabilities by category
    REQUIRED_CAPABILITIES = {
        "development": ["code_generation", "code_review"],
        "quality_security": ["testing", "validation"],
        "documentation": ["technical_writing"],
    }
    
    # Forbidden capability combinations
    FORBIDDEN_COMBINATIONS = [
        ("delete_production_data", "autonomous_deployment"),
    ]
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate persona data against schema and business rules.
        
        Args:
            data: Persona data dictionary
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Step 1: Pydantic schema validation
        try:
            persona = PersonaSchema.model_validate(data)
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                result.add_error(f"Schema validation: {field} - {error['msg']}")
            return result
        
        # Step 2: Business rule validation
        cls._validate_identity_rules(persona.identity, result)
        cls._validate_capability_rules(persona.capabilities, result)
        cls._validate_constraint_rules(persona.constraints, result)
        cls._validate_personality_rules(persona.personality, result)
        cls._validate_cross_field_rules(persona, result)
        
        return result
    
    @classmethod
    def _validate_identity_rules(cls, identity: PersonaIdentity, result: ValidationResult):
        """Validate identity-specific rules."""
        # Check for meaningful description
        if len(identity.description.split()) < 5:
            result.add_warning("Description should be at least 5 words for clarity")
        
        # Check version format
        parts = identity.version.split(".")
        if int(parts[0]) == 0:
            result.add_warning("Major version 0 indicates unstable persona")
    
    @classmethod
    def _validate_capability_rules(cls, capabilities: PersonaCapabilities, result: ValidationResult):
        """Validate capability-specific rules."""
        # Check for minimum capabilities
        if len(capabilities.core) < 2:
            result.add_warning("Personas should have at least 2 core capabilities")
        
        # Check experience vs capability count
        if capabilities.experience_level > 8 and len(capabilities.core) < 4:
            result.add_warning(
                f"High experience level ({capabilities.experience_level}) "
                f"but only {len(capabilities.core)} core capabilities"
            )
        
        # Check autonomy vs experience
        if capabilities.autonomy_level > capabilities.experience_level + 2:
            result.add_warning(
                "Autonomy level significantly exceeds experience level"
            )
    
    @classmethod
    def _validate_constraint_rules(cls, constraints: PersonaConstraints, result: ValidationResult):
        """Validate constraint-specific rules."""
        # Check for at least one safety constraint
        if not constraints.forbidden_actions and not constraints.safety_rules:
            result.add_warning(
                "Persona has no forbidden_actions or safety_rules defined"
            )
        
        # Check resource limits
        if constraints.resource_limits.max_tokens > 32000:
            result.add_warning(
                f"Very high max_tokens ({constraints.resource_limits.max_tokens}) "
                "may impact cost and latency"
            )
    
    @classmethod
    def _validate_personality_rules(cls, personality: PersonalityTraits, result: ValidationResult):
        """Validate personality trait rules."""
        # Check for extreme combinations
        if personality.formality > 0.9 and personality.creativity > 0.9:
            result.add_warning(
                "High formality with high creativity is an unusual combination"
            )
        
        if personality.assertiveness > 0.9 and personality.empathy > 0.9:
            result.add_warning(
                "High assertiveness with high empathy may create conflicting behaviors"
            )
        
        # Check risk tolerance for autonomous personas
        if personality.risk_tolerance > 0.7:
            result.add_warning(
                "High risk_tolerance may lead to unexpected behavior in production"
            )
    
    @classmethod
    def _validate_cross_field_rules(cls, persona: PersonaSchema, result: ValidationResult):
        """Validate rules that span multiple fields."""
        # Check capability-constraint alignment
        for capability in persona.capabilities.core:
            for action in persona.constraints.forbidden_actions:
                if capability.lower() in action.lower():
                    result.add_error(
                        f"Conflict: capability '{capability}' conflicts with "
                        f"forbidden action '{action}'"
                    )
        
        # Check personality-constraints alignment
        if persona.personality.risk_tolerance > 0.7 and len(persona.constraints.requires_approval_for) == 0:
            result.add_warning(
                "High risk tolerance without approval requirements may be unsafe"
            )
        
        # Check prompts exist and are meaningful
        if len(persona.prompts.system_prompt) < 100:
            result.add_warning(
                "System prompt is quite short, may lack sufficient context"
            )
    
    @classmethod
    def validate_json(cls, json_str: str) -> ValidationResult:
        """Validate persona from JSON string."""
        import json
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            result = ValidationResult()
            result.add_error(f"Invalid JSON: {e}")
            return result
        return cls.validate(data)
    
    @classmethod
    def validate_file(cls, file_path: str) -> ValidationResult:
        """Validate persona from JSON file."""
        try:
            with open(file_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            result = ValidationResult()
            result.add_error(f"File not found: {file_path}")
            return result
        return cls.validate_json(content)
