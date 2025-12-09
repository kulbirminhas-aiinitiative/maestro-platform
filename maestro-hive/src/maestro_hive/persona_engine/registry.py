"""
Persona Registry - Central registry for persona management.

EPIC: MD-2554
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

from .schema import PersonaSchema, PersonaCategory
from .validator import PersonaValidator, ValidationResult


logger = logging.getLogger(__name__)


class PersonaRegistry:
    """
    Central registry for persona management.
    
    Provides:
    - Loading personas from JSON files
    - Registration of new personas
    - Retrieval by ID or category
    - Validation on registration
    """
    
    _instance: Optional["PersonaRegistry"] = None
    _personas: Dict[str, PersonaSchema] = {}
    _loaded: bool = False
    
    def __new__(cls) -> "PersonaRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._personas = {}
            cls._loaded = False
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the registry (useful for testing)."""
        cls._instance = None
        cls._personas = {}
        cls._loaded = False
    
    def load_from_directory(self, directory: str) -> int:
        """
        Load all persona JSON files from a directory.
        
        Args:
            directory: Path to directory containing persona JSON files
            
        Returns:
            Number of personas loaded
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Directory not found: {directory}")
            return 0
        
        count = 0
        for json_file in dir_path.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                
                # Validate and register
                validation = PersonaValidator.validate(data)
                if validation.is_valid:
                    persona = PersonaSchema.model_validate(data)
                    self.register(persona)
                    count += 1
                    logger.info(f"Loaded persona: {persona.persona_id}")
                else:
                    logger.warning(f"Invalid persona in {json_file}: {validation.errors}")
            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")
        
        self._loaded = True
        return count
    
    def register(self, persona: PersonaSchema) -> bool:
        """
        Register a persona in the registry.
        
        Args:
            persona: PersonaSchema instance to register
            
        Returns:
            True if registered successfully
        """
        if persona.persona_id in self._personas:
            logger.warning(f"Overwriting existing persona: {persona.persona_id}")
        
        self._personas[persona.persona_id] = persona
        return True
    
    def get(self, persona_id: str) -> Optional[PersonaSchema]:
        """Get persona by ID."""
        return self._personas.get(persona_id)
    
    def get_all(self) -> Dict[str, PersonaSchema]:
        """Get all registered personas."""
        return self._personas.copy()
    
    def get_by_category(self, category: PersonaCategory) -> List[PersonaSchema]:
        """Get all personas in a category."""
        return [
            p for p in self._personas.values()
            if p.identity.category == category
        ]
    
    def get_ids(self) -> List[str]:
        """Get all registered persona IDs."""
        return list(self._personas.keys())
    
    def count(self) -> int:
        """Get count of registered personas."""
        return len(self._personas)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check registry health.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy" if self._loaded else "not_loaded",
            "persona_count": self.count(),
            "schema_version": "4.0",
            "categories": {
                cat.value: len(self.get_by_category(cat))
                for cat in PersonaCategory
                if self.get_by_category(cat)
            }
        }
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Export all personas as dictionary."""
        return {
            pid: persona.to_dict()
            for pid, persona in self._personas.items()
        }
    
    def to_json(self) -> str:
        """Export all personas as JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def get_registry() -> PersonaRegistry:
    """Get the singleton registry instance."""
    return PersonaRegistry()
