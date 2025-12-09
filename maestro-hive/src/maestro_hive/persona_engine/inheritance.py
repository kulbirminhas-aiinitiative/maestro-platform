"""
Persona Inheritance - Capability inheritance and composition

Implements:
- AC-2542-4: Inherit capabilities from parent personas
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from .models import (
    Persona,
    PersonaCapability,
    PersonaConfig,
    PersonaConstraint,
    ToneProfile,
    CapabilityLevel,
)


logger = logging.getLogger(__name__)


@dataclass
class InheritanceRule:
    """Rules for how inheritance is applied."""
    merge_capabilities: bool = True  # Inherit parent capabilities
    merge_constraints: bool = True  # Inherit parent constraints
    inherit_tone: bool = True  # Start with parent's tone
    inherit_config: bool = True  # Start with parent's config
    allow_override: bool = True  # Child can override parent values
    require_explicit_remove: bool = True  # Must explicitly remove inherited items


class PersonaInheritance:
    """
    Manages persona inheritance and composition.
    
    Features:
    - Single and multiple inheritance
    - Capability merging and overriding
    - Conflict resolution
    - Inheritance validation
    """
    
    def __init__(
        self,
        default_rules: Optional[InheritanceRule] = None,
    ):
        """
        Initialize inheritance manager.
        
        Args:
            default_rules: Default inheritance rules
        """
        self.default_rules = default_rules or InheritanceRule()
        self._parent_cache: Dict[UUID, Persona] = {}
        
        logger.info("PersonaInheritance initialized")
    
    def create_child(
        self,
        parent: Persona,
        name: str,
        description: str,
        role: Optional[str] = None,
        rules: Optional[InheritanceRule] = None,
        capability_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        additional_capabilities: Optional[List[Dict[str, Any]]] = None,
        removed_capabilities: Optional[List[str]] = None,
        tone_overrides: Optional[Dict[str, float]] = None,
        constraint_overrides: Optional[List[Dict[str, Any]]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> Persona:
        """
        Create a child persona that inherits from a parent.
        
        Args:
            parent: Parent persona to inherit from
            name: Name for child persona
            description: Description for child persona
            role: Role (defaults to parent's role)
            rules: Inheritance rules to apply
            capability_overrides: Override specific capabilities
            additional_capabilities: New capabilities to add
            removed_capabilities: Capabilities to remove from parent
            tone_overrides: Tone adjustments
            constraint_overrides: Constraint modifications
            config_overrides: Config modifications
            tags: Tags for child
            created_by: Creator identifier
        
        Returns:
            New child persona
        """
        rules = rules or self.default_rules
        
        # Start with base persona
        child = Persona(
            name=name,
            description=description,
            role=role or parent.role,
            parent_id=parent.id,
            created_by=created_by,
            tags=list(parent.tags) + (tags or []),
        )
        
        # Cache parent for future lookups
        self._parent_cache[parent.id] = parent
        
        # Merge capabilities
        if rules.merge_capabilities:
            child.capabilities = self._merge_capabilities(
                parent_caps=parent.capabilities,
                overrides=capability_overrides or {},
                additions=additional_capabilities or [],
                removals=removed_capabilities or [],
            )
        
        # Merge constraints
        if rules.merge_constraints:
            child.constraints = self._merge_constraints(
                parent_constraints=parent.constraints,
                overrides=constraint_overrides or [],
            )
        
        # Inherit tone
        if rules.inherit_tone:
            child.tone = self._merge_tone(
                parent_tone=parent.tone,
                overrides=tone_overrides or {},
            )
        
        # Inherit config
        if rules.inherit_config:
            child.config = self._merge_config(
                parent_config=parent.config,
                overrides=config_overrides or {},
            )
        
        # Update parent's children list
        if child.id not in parent.children_ids:
            parent.children_ids.append(child.id)
        
        logger.info(
            "Created child persona %s from parent %s",
            child.id,
            parent.id,
        )
        
        return child
    
    def _merge_capabilities(
        self,
        parent_caps: List[PersonaCapability],
        overrides: Dict[str, Dict[str, Any]],
        additions: List[Dict[str, Any]],
        removals: List[str],
    ) -> List[PersonaCapability]:
        """Merge parent capabilities with overrides and additions."""
        merged = []
        
        # Process parent capabilities
        for cap in parent_caps:
            if cap.name in removals:
                continue
            
            if cap.name in overrides:
                # Apply override
                override = overrides[cap.name]
                merged_cap = PersonaCapability(
                    name=cap.name,
                    description=override.get("description", cap.description),
                    level=CapabilityLevel(override.get("level", cap.level.value)),
                    domain=override.get("domain", cap.domain),
                    tools=override.get("tools", cap.tools),
                    constraints=override.get("constraints", cap.constraints),
                    inherited_from=str(cap.inherited_from) if cap.inherited_from else None,
                )
            else:
                # Copy with inheritance marker
                merged_cap = PersonaCapability(
                    name=cap.name,
                    description=cap.description,
                    level=cap.level,
                    domain=cap.domain,
                    tools=list(cap.tools),
                    constraints=dict(cap.constraints),
                    inherited_from=str(cap.inherited_from) if cap.inherited_from else "parent",
                )
            
            merged.append(merged_cap)
        
        # Add new capabilities
        existing_names = {c.name for c in merged}
        for add in additions:
            if add["name"] not in existing_names:
                merged.append(PersonaCapability(
                    name=add["name"],
                    description=add.get("description", ""),
                    level=CapabilityLevel(add.get("level", "intermediate")),
                    domain=add.get("domain"),
                    tools=add.get("tools", []),
                    constraints=add.get("constraints", {}),
                ))
        
        return merged
    
    def _merge_constraints(
        self,
        parent_constraints: List[PersonaConstraint],
        overrides: List[Dict[str, Any]],
    ) -> List[PersonaConstraint]:
        """Merge parent constraints with overrides."""
        merged = []
        override_names = {o["name"] for o in overrides}
        
        # Keep non-overridden parent constraints
        for con in parent_constraints:
            if con.name not in override_names:
                merged.append(PersonaConstraint(
                    name=con.name,
                    rule=con.rule,
                    severity=con.severity,
                    scope=con.scope,
                    metadata={**con.metadata, "inherited": True},
                ))
        
        # Add overrides and new constraints
        for override in overrides:
            merged.append(PersonaConstraint(
                name=override["name"],
                rule=override["rule"],
                severity=override.get("severity", "warning"),
                scope=override.get("scope", "all"),
                metadata=override.get("metadata", {}),
            ))
        
        return merged
    
    def _merge_tone(
        self,
        parent_tone: ToneProfile,
        overrides: Dict[str, float],
    ) -> ToneProfile:
        """Merge parent tone with overrides."""
        return ToneProfile(
            formality=overrides.get("formality", parent_tone.formality),
            verbosity=overrides.get("verbosity", parent_tone.verbosity),
            empathy=overrides.get("empathy", parent_tone.empathy),
            humor=overrides.get("humor", parent_tone.humor),
            technical_depth=overrides.get("technical_depth", parent_tone.technical_depth),
            custom_traits={
                **parent_tone.custom_traits,
                **overrides.get("custom_traits", {}),
            },
        )
    
    def _merge_config(
        self,
        parent_config: PersonaConfig,
        overrides: Dict[str, Any],
    ) -> PersonaConfig:
        """Merge parent config with overrides."""
        return PersonaConfig(
            max_response_tokens=overrides.get("max_response_tokens", parent_config.max_response_tokens),
            temperature=overrides.get("temperature", parent_config.temperature),
            top_p=overrides.get("top_p", parent_config.top_p),
            allowed_tools=overrides.get("allowed_tools", list(parent_config.allowed_tools)),
            blocked_tools=overrides.get("blocked_tools", list(parent_config.blocked_tools)),
            allowed_domains=overrides.get("allowed_domains", list(parent_config.allowed_domains)),
            blocked_domains=overrides.get("blocked_domains", list(parent_config.blocked_domains)),
            rate_limits=overrides.get("rate_limits", dict(parent_config.rate_limits)),
            custom_settings={
                **parent_config.custom_settings,
                **overrides.get("custom_settings", {}),
            },
        )
    
    def get_inheritance_chain(
        self,
        persona: Persona,
        registry_lookup: Optional[callable] = None,
    ) -> List[UUID]:
        """
        Get the full inheritance chain for a persona.
        
        Args:
            persona: Persona to trace
            registry_lookup: Function to lookup persona by ID
        
        Returns:
            List of persona IDs from root to current
        """
        chain = []
        current = persona
        
        while current:
            chain.append(current.id)
            
            if current.parent_id:
                # Try cache first
                parent = self._parent_cache.get(current.parent_id)
                
                # Use registry lookup if not cached
                if not parent and registry_lookup:
                    parent = registry_lookup(current.parent_id)
                    if parent:
                        self._parent_cache[current.parent_id] = parent
                
                current = parent
            else:
                break
        
        return list(reversed(chain))
    
    def get_effective_capabilities(
        self,
        persona: Persona,
        registry_lookup: Optional[callable] = None,
    ) -> List[PersonaCapability]:
        """
        Get all effective capabilities including inherited ones.
        
        This resolves the full inheritance chain and returns
        the final merged capability set.
        """
        # For now, return current capabilities as inheritance
        # is already resolved at creation time
        return persona.capabilities
    
    def validate_inheritance(
        self,
        child: Persona,
        parent: Persona,
    ) -> Dict[str, Any]:
        """
        Validate that inheritance relationship is valid.
        
        Args:
            child: Child persona
            parent: Parent persona
        
        Returns:
            Validation results
        """
        issues = []
        warnings = []
        
        # Check for circular inheritance
        if child.id == parent.id:
            issues.append("Circular inheritance: persona cannot be its own parent")
        
        if parent.parent_id == child.id:
            issues.append("Circular inheritance: parent's parent is the child")
        
        # Check for capability conflicts
        child_cap_names = {c.name for c in child.capabilities}
        parent_cap_names = {c.name for c in parent.capabilities}
        
        # Missing inherited capabilities
        if not child_cap_names.issuperset(parent_cap_names):
            missing = parent_cap_names - child_cap_names
            warnings.append(f"Child is missing parent capabilities: {missing}")
        
        # Check constraint compatibility
        child_severity = {c.name: c.severity for c in child.constraints}
        for pc in parent.constraints:
            if pc.name in child_severity:
                if pc.severity == "block" and child_severity[pc.name] != "block":
                    issues.append(
                        f"Child cannot relax blocking constraint: {pc.name}"
                    )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }
    
    def compose_personas(
        self,
        personas: List[Persona],
        name: str,
        description: str,
        role: str,
        conflict_resolution: str = "last_wins",
        created_by: Optional[str] = None,
    ) -> Persona:
        """
        Compose multiple personas into a new hybrid persona.
        
        Args:
            personas: List of personas to compose
            name: Name for composed persona
            description: Description for composed persona
            role: Role for composed persona
            conflict_resolution: How to handle conflicts ('last_wins', 'first_wins', 'highest_level')
            created_by: Creator identifier
        
        Returns:
            New composed persona
        """
        composed = Persona(
            name=name,
            description=description,
            role=role,
            created_by=created_by,
        )
        
        # Merge capabilities from all personas
        all_caps: Dict[str, PersonaCapability] = {}
        for persona in personas:
            for cap in persona.capabilities:
                if cap.name in all_caps:
                    existing = all_caps[cap.name]
                    if conflict_resolution == "last_wins":
                        all_caps[cap.name] = cap
                    elif conflict_resolution == "highest_level":
                        level_order = [
                            CapabilityLevel.NOVICE,
                            CapabilityLevel.INTERMEDIATE,
                            CapabilityLevel.ADVANCED,
                            CapabilityLevel.EXPERT,
                            CapabilityLevel.MASTER,
                        ]
                        if level_order.index(cap.level) > level_order.index(existing.level):
                            all_caps[cap.name] = cap
                    # first_wins: keep existing
                else:
                    all_caps[cap.name] = cap
        
        composed.capabilities = list(all_caps.values())
        
        # Merge constraints (union)
        all_constraints: Dict[str, PersonaConstraint] = {}
        for persona in personas:
            for con in persona.constraints:
                if con.name not in all_constraints:
                    all_constraints[con.name] = con
        
        composed.constraints = list(all_constraints.values())
        
        # Average tone profiles
        if personas:
            composed.tone = ToneProfile(
                formality=sum(p.tone.formality for p in personas) / len(personas),
                verbosity=sum(p.tone.verbosity for p in personas) / len(personas),
                empathy=sum(p.tone.empathy for p in personas) / len(personas),
                humor=sum(p.tone.humor for p in personas) / len(personas),
                technical_depth=sum(p.tone.technical_depth for p in personas) / len(personas),
            )
        
        # Merge tags
        all_tags = set()
        for persona in personas:
            all_tags.update(persona.tags)
        composed.tags = list(all_tags)
        
        # Record composition in metadata
        composed.metadata["composed_from"] = [str(p.id) for p in personas]
        composed.metadata["composition_method"] = conflict_resolution
        
        logger.info(
            "Composed persona %s from %d source personas",
            composed.id,
            len(personas),
        )
        
        return composed
