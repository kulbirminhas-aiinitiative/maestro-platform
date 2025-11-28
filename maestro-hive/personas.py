"""
SDLC Team Persona Definitions - Centralized Reference

This module now references centralized JSON-based persona definitions from maestro-engine.
All persona attributes (expertise, responsibilities, deliverables) are loaded from JSON,
eliminating hardcoding and ensuring consistency across the platform.

Previously: Hardcoded persona dictionaries (~1500 lines)
Now: References maestro-engine JSON definitions (Schema v3.0)

Source: /home/ec2-user/projects/maestro-engine/src/personas/definitions/*.json

Fallback: If maestro-engine is not available, uses personas_fallback.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Try to import maestro-engine persona system
MAESTRO_ENGINE_AVAILABLE = False
try:
    # Add maestro-engine-new/src to path to access centralized personas
    # Import as a package with unique name to avoid conflict with local personas.py
    import importlib.util
    import importlib

    MAESTRO_ENGINE_PATH = Path("/home/ec2-user/projects/maestro-engine-new")
    MAESTRO_ENGINE_SRC = MAESTRO_ENGINE_PATH / "src"

    # Add to path so relative imports in adapter work
    if str(MAESTRO_ENGINE_SRC) not in sys.path:
        sys.path.insert(0, str(MAESTRO_ENGINE_SRC))

    # First load the personas package's submodules directly
    # This avoids the name conflict with our local personas.py
    models_path = MAESTRO_ENGINE_SRC / "personas" / "models.py"
    registry_path = MAESTRO_ENGINE_SRC / "personas" / "registry.py"
    adapter_path = MAESTRO_ENGINE_SRC / "personas" / "adapter.py"

    # Load models
    spec = importlib.util.spec_from_file_location("maestro_personas.models", models_path)
    models_module = importlib.util.module_from_spec(spec)
    sys.modules["maestro_personas.models"] = models_module
    spec.loader.exec_module(models_module)

    # Load registry
    spec = importlib.util.spec_from_file_location("maestro_personas.registry", registry_path)
    registry_module = importlib.util.module_from_spec(spec)
    sys.modules["maestro_personas.registry"] = registry_module
    # Patch the relative imports
    registry_module.PersonaDefinition = models_module.PersonaDefinition
    registry_module.PersonaCategory = models_module.PersonaCategory
    spec.loader.exec_module(registry_module)

    # Load adapter with patched dependencies
    spec = importlib.util.spec_from_file_location("maestro_personas.adapter", adapter_path)
    adapter_module = importlib.util.module_from_spec(spec)
    # Inject dependencies to avoid relative import issues
    adapter_module.PersonaCategory = models_module.PersonaCategory
    adapter_module.PersonaDefinition = models_module.PersonaDefinition
    adapter_module.PersonaRegistry = registry_module.PersonaRegistry
    sys.modules["maestro_personas.adapter"] = adapter_module
    spec.loader.exec_module(adapter_module)

    MaestroPersonaAdapter = adapter_module.MaestroPersonaAdapter
    get_adapter = adapter_module.get_adapter
    MAESTRO_ENGINE_AVAILABLE = True
    logger.info("✅ Using maestro-engine personas")
except Exception as e:
    logger.warning(f"⚠️  maestro-engine not available, using fallback personas: {e}")
    from personas_fallback import SDLCPersonasFallback
    MAESTRO_ENGINE_AVAILABLE = False


class SDLCPersonas:
    """
    Comprehensive persona definitions for SDLC team.

    Now references centralized JSON definitions instead of hardcoding.
    All personas are loaded from:
    /home/ec2-user/projects/maestro-engine/src/personas/definitions/

    Benefits:
    - Single source of truth
    - Pydantic schema validation
    - Easy updates (edit JSON, not code)
    - Consistent across all services
    - No duplicate definitions
    
    Fallback: Uses personas_fallback.py if maestro-engine unavailable
    """

    _adapter: 'MaestroPersonaAdapter' = None
    _personas_cache: Dict[str, Dict[str, Any]] = None

    @classmethod
    def _get_adapter(cls):
        """Get adapter instance, loading personas if needed"""
        if not MAESTRO_ENGINE_AVAILABLE:
            # Use fallback
            return None
        
        if cls._adapter is None:
            cls._adapter = get_adapter()

        # Ensure personas are loaded
        if not cls._adapter._loaded:
            import asyncio
            try:
                # Try to get running event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If already in async context, create task
                    asyncio.create_task(cls._adapter.load_personas())
                else:
                    # Run in new loop
                    asyncio.run(cls._adapter.load_personas())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(cls._adapter.load_personas())

        return cls._adapter

    @staticmethod
    def get_all_personas() -> Dict[str, Dict[str, Any]]:
        """
        Get all SDLC persona definitions from centralized JSON.

        Returns:
            Dictionary mapping persona_id to persona definition

        Note: deployment_integration_tester is aliased to deployment_specialist
        """
        if SDLCPersonas._personas_cache is None:
            if MAESTRO_ENGINE_AVAILABLE:
                adapter = SDLCPersonas._get_adapter()
                personas = adapter.get_all_personas()

                # Add alias for backward compatibility
                # deployment_integration_tester → deployment_specialist
                if "deployment_specialist" in personas:
                    personas["deployment_integration_tester"] = personas["deployment_specialist"].copy()
                    personas["deployment_integration_tester"]["id"] = "deployment_integration_tester"

                SDLCPersonas._personas_cache = personas
            else:
                # Use fallback
                SDLCPersonas._personas_cache = SDLCPersonasFallback.get_all_personas()

        return SDLCPersonas._personas_cache

    @staticmethod
    def requirement_analyst() -> Dict[str, Any]:
        """Requirements Analyst - From JSON definition"""
        return SDLCPersonas.get_all_personas()["requirement_analyst"]

    @staticmethod
    def solution_architect() -> Dict[str, Any]:
        """Solution Architect - From JSON definition"""
        return SDLCPersonas.get_all_personas()["solution_architect"]

    @staticmethod
    def frontend_developer() -> Dict[str, Any]:
        """Frontend Developer - From JSON definition"""
        return SDLCPersonas.get_all_personas()["frontend_developer"]

    @staticmethod
    def backend_developer() -> Dict[str, Any]:
        """Backend Developer - From JSON definition"""
        return SDLCPersonas.get_all_personas()["backend_developer"]

    @staticmethod
    def devops_engineer() -> Dict[str, Any]:
        """DevOps Engineer - From JSON definition"""
        return SDLCPersonas.get_all_personas()["devops_engineer"]

    @staticmethod
    def qa_engineer() -> Dict[str, Any]:
        """QA Engineer - From JSON definition"""
        return SDLCPersonas.get_all_personas()["qa_engineer"]

    @staticmethod
    def security_specialist() -> Dict[str, Any]:
        """Security Specialist - From JSON definition"""
        return SDLCPersonas.get_all_personas()["security_specialist"]

    @staticmethod
    def ui_ux_designer() -> Dict[str, Any]:
        """UI/UX Designer - From JSON definition"""
        return SDLCPersonas.get_all_personas()["ui_ux_designer"]

    @staticmethod
    def technical_writer() -> Dict[str, Any]:
        """Technical Writer - From JSON definition"""
        return SDLCPersonas.get_all_personas()["technical_writer"]

    @staticmethod
    def deployment_specialist() -> Dict[str, Any]:
        """Deployment Specialist - From JSON definition"""
        return SDLCPersonas.get_all_personas()["deployment_specialist"]

    @staticmethod
    def deployment_integration_tester() -> Dict[str, Any]:
        """
        Deployment Integration Tester - Alias for deployment_specialist

        Note: This is an alias for backward compatibility.
        The canonical persona is 'deployment_specialist'.
        """
        return SDLCPersonas.get_all_personas()["deployment_integration_tester"]

    @staticmethod
    def database_administrator() -> Dict[str, Any]:
        """Database Administrator - From JSON definition"""
        return SDLCPersonas.get_all_personas()["database_administrator"]

    @staticmethod
    def phase_reviewer() -> Dict[str, Any]:
        """
        Phase Reviewer - Phase-level validation

        Validates deliverables at the end of each SDLC phase.
        Creates phase_reviews/ directory with validation reports.
        """
        return SDLCPersonas.get_all_personas()["phase_reviewer"]

    @staticmethod
    def test_engineer() -> Dict[str, Any]:
        """
        Test Engineer - Comprehensive test generation and execution

        Generates comprehensive runnable test cases for both frontend and backend.
        Executes tests and validates quality before deployment.
        Creates detailed test reports with coverage analysis.
        """
        return SDLCPersonas.get_all_personas()["test_engineer"]

    @staticmethod
    def deliverable_validator() -> Dict[str, Any]:
        """
        Deliverable Validator - Intelligent semantic file validation

        Uses AI to semantically match created files to expected deliverables.
        Handles variations in file naming (comprehensive, detailed, strategic).
        Provides flexible validation beyond rigid pattern matching.
        """
        return SDLCPersonas.get_all_personas()["deliverable_validator"]


# Backward compatibility: Keep module-level functions
def get_all_personas() -> Dict[str, Dict[str, Any]]:
    """Module-level function for backward compatibility"""
    return SDLCPersonas.get_all_personas()


if __name__ == "__main__":
    """Test the centralized persona system"""
    import json

    print("=" * 80)
    print("SDLC Personas - Centralized JSON Reference Test")
    print("=" * 80)
    print()

    # Load all personas
    print("Loading personas from maestro-engine JSON definitions...")
    personas = SDLCPersonas.get_all_personas()

    print(f"✅ Loaded {len(personas)} personas\n")

    # Test a few personas
    print("Sample Personas:")
    print("-" * 80)

    for persona_id in ["requirement_analyst", "backend_developer", "technical_writer"]:
        persona = personas[persona_id]
        print(f"\n🤖 {persona['name']} ({persona_id})")
        print(f"   Phase: {persona['phase']}")
        print(f"   Role: {persona['role_id']}")
        print(f"   Expertise: {len(persona['expertise'])} areas")
        print(f"   Responsibilities: {len(persona['responsibilities'])} items")
        print(f"   Collaboration: {persona['collaboration_style']}")
        print(f"   System Prompt: {len(persona['system_prompt'])} characters")

    print("\n" + "=" * 80)
    print("✅ All personas loaded successfully from JSON!")
    print("   No hardcoded attributes - everything from centralized definitions")
    print("=" * 80)

    # Show sample expertise from JSON
    print("\n📋 Sample: Technical Writer Expertise (from JSON)")
    print("-" * 80)
    tw = SDLCPersonas.technical_writer()
    for i, exp in enumerate(tw['expertise'], 1):
        print(f"   {i}. {exp}")

    print("\n📦 Sample: Technical Writer Responsibilities (from JSON)")
    print("-" * 80)
    for i, resp in enumerate(tw['responsibilities'], 1):
        print(f"   {i}. {resp}")
