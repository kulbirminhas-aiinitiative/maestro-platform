"""
Persona Engine - Core runtime for AI Personas

Implements:
- AC-2542-1: Define persona with capabilities, tone, constraints
- AC-2542-5: Export persona as JSON/YAML
- AC-2542-3: Evolution tracking with performance metrics
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import yaml

from .models import (
    Persona,
    PersonaCapability,
    PersonaConfig,
    PersonaConstraint,
    PersonaStatus,
    PersonaVersion,
    ToneProfile,
    CapabilityLevel,
)


logger = logging.getLogger(__name__)


class PersonaEngine:
    """
    Core engine for creating, managing, and operating AI personas.
    
    The PersonaEngine provides:
    - Persona creation and configuration
    - Runtime capability checking
    - Constraint enforcement
    - Tone profile application
    - Export/import functionality
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the Persona Engine.
        
        Args:
            storage_path: Optional path for persona storage
        """
        self.storage_path = storage_path or Path("/tmp/personas")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._active_personas: Dict[UUID, Persona] = {}
        self._metrics: Dict[UUID, Dict[str, Any]] = {}
        logger.info("PersonaEngine initialized with storage: %s", self.storage_path)
    
    def create_persona(
        self,
        name: str,
        description: str,
        role: str,
        capabilities: Optional[List[Dict[str, Any]]] = None,
        tone: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        parent_id: Optional[UUID] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Persona:
        """
        Create a new persona with specified attributes.
        
        Args:
            name: Display name for the persona
            description: Detailed description of persona's purpose
            role: Primary role/function of the persona
            capabilities: List of capability definitions
            tone: Tone profile settings
            constraints: List of constraint definitions
            config: Configuration settings
            parent_id: ID of parent persona for inheritance
            created_by: Creator identifier
            tags: Classification tags
        
        Returns:
            Newly created Persona instance
        """
        # Parse capabilities
        parsed_capabilities = []
        for cap in (capabilities or []):
            parsed_capabilities.append(PersonaCapability(
                name=cap["name"],
                description=cap.get("description", ""),
                level=CapabilityLevel(cap.get("level", "intermediate")),
                domain=cap.get("domain"),
                tools=cap.get("tools", []),
                constraints=cap.get("constraints", {}),
            ))
        
        # Parse constraints
        parsed_constraints = []
        for con in (constraints or []):
            parsed_constraints.append(PersonaConstraint(
                name=con["name"],
                rule=con["rule"],
                severity=con.get("severity", "warning"),
                scope=con.get("scope", "all"),
                metadata=con.get("metadata", {}),
            ))
        
        # Create persona
        persona = Persona(
            name=name,
            description=description,
            role=role,
            capabilities=parsed_capabilities,
            tone=ToneProfile.from_dict(tone or {}),
            constraints=parsed_constraints,
            config=PersonaConfig.from_dict(config or {}),
            parent_id=parent_id,
            created_by=created_by,
            tags=tags or [],
        )
        
        # Initialize metrics
        self._metrics[persona.id] = {
            "created_at": datetime.utcnow().isoformat(),
            "invocations": 0,
            "successful_responses": 0,
            "constraint_violations": 0,
            "capability_usage": {},
        }
        
        logger.info("Created persona: %s (ID: %s)", name, persona.id)
        return persona
    
    def activate_persona(self, persona: Persona) -> bool:
        """
        Activate a persona for runtime use.
        
        Args:
            persona: Persona to activate
        
        Returns:
            True if activation successful
        """
        if persona.status == PersonaStatus.ARCHIVED:
            logger.error("Cannot activate archived persona: %s", persona.id)
            return False
        
        persona.activate()
        self._active_personas[persona.id] = persona
        logger.info("Activated persona: %s", persona.id)
        return True
    
    def deactivate_persona(self, persona_id: UUID) -> bool:
        """
        Deactivate a persona from runtime.
        
        Args:
            persona_id: ID of persona to deactivate
        
        Returns:
            True if deactivation successful
        """
        if persona_id in self._active_personas:
            del self._active_personas[persona_id]
            logger.info("Deactivated persona: %s", persona_id)
            return True
        return False
    
    def get_active_persona(self, persona_id: UUID) -> Optional[Persona]:
        """Get an active persona by ID."""
        return self._active_personas.get(persona_id)
    
    def check_capability(
        self, 
        persona: Persona, 
        capability_name: str,
        required_level: Optional[CapabilityLevel] = None,
    ) -> bool:
        """
        Check if persona has a specific capability.
        
        Args:
            persona: Persona to check
            capability_name: Name of capability to check
            required_level: Minimum required proficiency level
        
        Returns:
            True if persona has capability at required level
        """
        cap = persona.get_capability(capability_name)
        if not cap:
            return False
        
        if required_level:
            level_order = [
                CapabilityLevel.NOVICE,
                CapabilityLevel.INTERMEDIATE,
                CapabilityLevel.ADVANCED,
                CapabilityLevel.EXPERT,
                CapabilityLevel.MASTER,
            ]
            return level_order.index(cap.level) >= level_order.index(required_level)
        
        return True
    
    def check_constraints(
        self,
        persona: Persona,
        action: str,
        context: Dict[str, Any],
    ) -> List[PersonaConstraint]:
        """
        Check which constraints would be violated by an action.
        
        Args:
            persona: Persona to check constraints for
            action: Proposed action
            context: Context of the action
        
        Returns:
            List of violated constraints
        """
        violations = []
        for constraint in persona.constraints:
            if self._evaluate_constraint(constraint, action, context):
                violations.append(constraint)
                self._record_constraint_violation(persona.id, constraint)
        
        return violations
    
    def _evaluate_constraint(
        self,
        constraint: PersonaConstraint,
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate if a constraint is violated."""
        # Simple keyword-based evaluation
        rule_lower = constraint.rule.lower()
        action_lower = action.lower()
        
        # Check for blocked keywords
        if "block" in rule_lower or "deny" in rule_lower:
            blocked_terms = constraint.metadata.get("blocked_terms", [])
            for term in blocked_terms:
                if term.lower() in action_lower:
                    return True
        
        # Check domain scope
        if constraint.scope != "all":
            current_domain = context.get("domain")
            if current_domain and current_domain not in constraint.scope:
                return False
        
        return False
    
    def _record_constraint_violation(
        self,
        persona_id: UUID,
        constraint: PersonaConstraint,
    ) -> None:
        """Record a constraint violation in metrics."""
        if persona_id in self._metrics:
            self._metrics[persona_id]["constraint_violations"] += 1
            logger.warning(
                "Constraint violation for persona %s: %s",
                persona_id,
                constraint.name,
            )
    
    def apply_tone(
        self,
        persona: Persona,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate tone guidance for message generation.
        
        Args:
            persona: Persona whose tone to apply
            message: Input message to process
            context: Additional context
        
        Returns:
            Tone guidance dictionary
        """
        tone = persona.tone
        guidance = {
            "formality": "formal" if tone.formality > 0.7 else "casual" if tone.formality < 0.3 else "neutral",
            "length": "detailed" if tone.verbosity > 0.7 else "concise" if tone.verbosity < 0.3 else "moderate",
            "style": "empathetic" if tone.empathy > 0.7 else "direct" if tone.empathy < 0.3 else "balanced",
            "humor_allowed": tone.humor > 0.5,
            "technical_level": "expert" if tone.technical_depth > 0.7 else "beginner" if tone.technical_depth < 0.3 else "intermediate",
            "custom_traits": tone.custom_traits,
        }
        
        return guidance
    
    def record_invocation(
        self,
        persona_id: UUID,
        success: bool,
        capabilities_used: List[str],
    ) -> None:
        """
        Record a persona invocation for metrics.
        
        Args:
            persona_id: ID of persona invoked
            success: Whether invocation was successful
            capabilities_used: List of capabilities used
        """
        if persona_id not in self._metrics:
            return
        
        metrics = self._metrics[persona_id]
        metrics["invocations"] += 1
        if success:
            metrics["successful_responses"] += 1
        
        for cap in capabilities_used:
            if cap not in metrics["capability_usage"]:
                metrics["capability_usage"][cap] = 0
            metrics["capability_usage"][cap] += 1
    
    def get_metrics(self, persona_id: UUID) -> Optional[Dict[str, Any]]:
        """Get metrics for a persona."""
        return self._metrics.get(persona_id)
    
    def export_persona(
        self,
        persona: Persona,
        format: str = "json",
        path: Optional[Path] = None,
    ) -> Union[str, Path]:
        """
        Export persona to JSON or YAML format.
        
        Args:
            persona: Persona to export
            format: Export format ('json' or 'yaml')
            path: Optional output path
        
        Returns:
            Serialized string or path to exported file
        """
        data = persona.to_dict()
        
        if format == "yaml":
            content = yaml.dump(data, default_flow_style=False, sort_keys=False)
            ext = ".yaml"
        else:
            content = json.dumps(data, indent=2, default=str)
            ext = ".json"
        
        if path:
            output_path = path
        else:
            output_path = self.storage_path / f"{persona.id}{ext}"
        
        output_path.write_text(content)
        logger.info("Exported persona %s to %s", persona.id, output_path)
        return output_path
    
    def import_persona(
        self,
        path: Path,
        format: Optional[str] = None,
    ) -> Persona:
        """
        Import persona from JSON or YAML file.
        
        Args:
            path: Path to import from
            format: Optional format override
        
        Returns:
            Imported Persona instance
        """
        content = path.read_text()
        
        if format == "yaml" or path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        
        persona = Persona.from_dict(data)
        logger.info("Imported persona %s from %s", persona.id, path)
        return persona
    
    def list_active_personas(self) -> List[Dict[str, Any]]:
        """List all active personas with summary info."""
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "role": p.role,
                "status": p.status.value,
                "version": str(p.version),
                "capability_count": len(p.capabilities),
            }
            for p in self._active_personas.values()
        ]
