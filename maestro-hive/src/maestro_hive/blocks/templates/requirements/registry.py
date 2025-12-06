"""
Template Registry

Central registry for managing and accessing document templates.

Provides:
- Template registration and lookup
- Phase-based template filtering
- Template validation
- Batch operations

Reference: MD-2515 AC-1, AC-2, AC-3, AC-4
"""

from typing import Dict, List, Optional, Type
from .models import DocumentTemplate, PersonaRole


class TemplateRegistry:
    """
    Central registry for document templates.

    Manages template lifecycle including:
    - Registration
    - Lookup by ID, name, or phase
    - Persona filtering
    - Template enumeration
    """

    def __init__(self):
        """Initialize empty registry."""
        self._templates: Dict[str, DocumentTemplate] = {}
        self._by_phase: Dict[str, List[str]] = {}
        self._initialized = False

    def register(self, template: DocumentTemplate) -> None:
        """
        Register a template with the registry.

        Args:
            template: The template to register

        Raises:
            ValueError: If template ID already exists
        """
        if template.template_id in self._templates:
            raise ValueError(f"Template '{template.template_id}' already registered")

        self._templates[template.template_id] = template

        # Index by phase
        if template.phase not in self._by_phase:
            self._by_phase[template.phase] = []
        self._by_phase[template.phase].append(template.template_id)

    def get(self, template_id: str) -> Optional[DocumentTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: The template identifier

        Returns:
            The template or None if not found
        """
        self._ensure_initialized()
        return self._templates.get(template_id)

    def get_by_name(self, name: str) -> Optional[DocumentTemplate]:
        """
        Get a template by name.

        Args:
            name: The template name

        Returns:
            The template or None if not found
        """
        self._ensure_initialized()
        for template in self._templates.values():
            if template.name.lower() == name.lower():
                return template
        return None

    def list_all(self) -> List[DocumentTemplate]:
        """
        List all registered templates.

        Returns:
            List of all templates
        """
        self._ensure_initialized()
        return list(self._templates.values())

    def list_by_phase(self, phase: str) -> List[DocumentTemplate]:
        """
        List templates for a specific phase.

        Args:
            phase: The SDLC phase (e.g., 'requirements', 'design')

        Returns:
            List of templates for the phase
        """
        self._ensure_initialized()
        template_ids = self._by_phase.get(phase, [])
        return [self._templates[tid] for tid in template_ids]

    def list_by_persona(self, role: PersonaRole) -> List[DocumentTemplate]:
        """
        List templates where a persona has a specific role.

        Args:
            role: The persona role to filter by

        Returns:
            List of templates with the specified persona role
        """
        self._ensure_initialized()
        result = []
        for template in self._templates.values():
            if role in template.personas:
                result.append(template)
        return result

    def get_template_ids(self) -> List[str]:
        """
        Get all registered template IDs.

        Returns:
            List of template identifiers
        """
        self._ensure_initialized()
        return list(self._templates.keys())

    def get_phases(self) -> List[str]:
        """
        Get all phases with registered templates.

        Returns:
            List of phase names
        """
        self._ensure_initialized()
        return list(self._by_phase.keys())

    def count(self) -> int:
        """
        Get total number of registered templates.

        Returns:
            Template count
        """
        self._ensure_initialized()
        return len(self._templates)

    def _ensure_initialized(self) -> None:
        """Ensure built-in templates are registered."""
        if not self._initialized:
            self._register_builtin_templates()
            self._initialized = True

    def _register_builtin_templates(self) -> None:
        """Register all built-in templates."""
        from .srs_template import SoftwareRequirementsSpecTemplate
        from .charter_template import ProjectCharterTemplate
        from .stakeholder_template import StakeholderAnalysisTemplate
        from .rtm_template import RequirementsTraceabilityMatrixTemplate
        from .feasibility_template import FeasibilityStudyTemplate
        from .risk_template import RiskAssessmentTemplate

        # Register requirements phase templates
        builtin_templates = [
            SoftwareRequirementsSpecTemplate(),
            ProjectCharterTemplate(),
            StakeholderAnalysisTemplate(),
            RequirementsTraceabilityMatrixTemplate(),
            FeasibilityStudyTemplate(),
            RiskAssessmentTemplate(),
        ]

        for template in builtin_templates:
            if template.template_id not in self._templates:
                self.register(template)

    def to_dict(self) -> Dict:
        """
        Export registry contents as dictionary.

        Returns:
            Dictionary representation of all templates
        """
        self._ensure_initialized()
        return {
            "template_count": len(self._templates),
            "phases": list(self._by_phase.keys()),
            "templates": {
                tid: {
                    "name": t.name,
                    "phase": t.phase,
                    "version": t.version,
                    "sections": len(t.sections),
                    "variables": len(t.variables),
                }
                for tid, t in self._templates.items()
            },
        }


# Singleton registry instance
_registry: Optional[TemplateRegistry] = None


def get_requirements_templates() -> TemplateRegistry:
    """
    Get the global template registry.

    Returns:
        The singleton TemplateRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
    return _registry
