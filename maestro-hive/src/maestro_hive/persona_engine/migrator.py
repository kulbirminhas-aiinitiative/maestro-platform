"""
Persona Migrator - Migrates existing personas to v4.0 schema.

AC-5: Existing 11+ personas in personas.py migrate to new schema

EPIC: MD-2554
"""

from typing import Any, Dict, List, Optional
import json
import logging
from pathlib import Path

from .schema import (
    PersonaSchema,
    PersonaIdentity,
    PersonaCapabilities,
    PersonaConstraints,
    PersonalityTraits,
    PersonaPrompts,
    ExecutionConfig,
    SDLCPersonaExtension,
    PersonaCategory,
    CommunicationStyle,
)


logger = logging.getLogger(__name__)


class MigrationResult:
    """Result of persona migration."""
    
    def __init__(self, persona_id: str):
        self.persona_id = persona_id
        self.success: bool = False
        self.source_version: str = "unknown"
        self.target_version: str = "4.0"
        self.changes: List[str] = []
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona_id": self.persona_id,
            "success": self.success,
            "source_version": self.source_version,
            "target_version": self.target_version,
            "changes": self.changes,
            "errors": self.errors,
        }


class PersonaMigrator:
    """
    Migrates existing personas from v3.0 to v4.0 schema.
    
    AC-5: Existing 11+ personas in personas.py migrate to new schema
    
    Key migrations:
    - Add personality traits (with sensible defaults based on role)
    - Add constraints (with safe defaults)
    - Convert metadata to identity structure
    - Preserve all existing fields
    """
    
    # Default personality traits by role type
    ROLE_PERSONALITY_DEFAULTS = {
        "analyst": {
            "communication_style": CommunicationStyle.FORMAL,
            "verbosity": 0.7,
            "creativity": 0.4,
            "assertiveness": 0.5,
            "formality": 0.7,
            "empathy": 0.6,
            "risk_tolerance": 0.2,
        },
        "developer": {
            "communication_style": CommunicationStyle.TECHNICAL,
            "verbosity": 0.5,
            "creativity": 0.6,
            "assertiveness": 0.5,
            "formality": 0.4,
            "empathy": 0.4,
            "risk_tolerance": 0.4,
        },
        "architect": {
            "communication_style": CommunicationStyle.FORMAL,
            "verbosity": 0.6,
            "creativity": 0.7,
            "assertiveness": 0.7,
            "formality": 0.6,
            "empathy": 0.5,
            "risk_tolerance": 0.3,
        },
        "qa": {
            "communication_style": CommunicationStyle.TECHNICAL,
            "verbosity": 0.6,
            "creativity": 0.3,
            "assertiveness": 0.6,
            "formality": 0.5,
            "empathy": 0.4,
            "risk_tolerance": 0.1,
        },
        "devops": {
            "communication_style": CommunicationStyle.TECHNICAL,
            "verbosity": 0.4,
            "creativity": 0.5,
            "assertiveness": 0.6,
            "formality": 0.4,
            "empathy": 0.3,
            "risk_tolerance": 0.2,
        },
        "writer": {
            "communication_style": CommunicationStyle.FRIENDLY,
            "verbosity": 0.8,
            "creativity": 0.6,
            "assertiveness": 0.3,
            "formality": 0.5,
            "empathy": 0.7,
            "risk_tolerance": 0.3,
        },
        "default": {
            "communication_style": CommunicationStyle.TECHNICAL,
            "verbosity": 0.5,
            "creativity": 0.5,
            "assertiveness": 0.5,
            "formality": 0.5,
            "empathy": 0.5,
            "risk_tolerance": 0.3,
        },
    }
    
    # Default constraints for all personas
    DEFAULT_CONSTRAINTS = {
        "forbidden_actions": [
            "delete_production_data",
            "expose_secrets",
            "bypass_authentication",
        ],
        "safety_rules": [
            "Always validate inputs",
            "Never hardcode credentials",
            "Follow secure coding practices",
        ],
        "ethical_boundaries": [
            "Respect user privacy",
            "Be transparent about AI nature",
        ],
    }
    
    @classmethod
    def migrate_v3_to_v4(cls, v3_data: Dict[str, Any]) -> MigrationResult:
        """
        Migrate a v3.0 persona to v4.0 schema.
        
        Args:
            v3_data: Persona data in v3.0 format
            
        Returns:
            MigrationResult with migrated persona or errors
        """
        persona_id = v3_data.get("persona_id", "unknown")
        result = MigrationResult(persona_id)
        result.source_version = v3_data.get("schema_version", "3.0")
        
        try:
            # Build v4.0 structure
            v4_data = cls._build_v4_structure(v3_data, result)
            
            # Validate the migrated persona
            persona = PersonaSchema.model_validate(v4_data)
            
            result.success = True
            result.migrated_persona = persona
            
        except Exception as e:
            result.errors.append(str(e))
            result.success = False
        
        return result
    
    @classmethod
    def _build_v4_structure(cls, v3_data: Dict[str, Any], result: MigrationResult) -> Dict[str, Any]:
        """Build v4.0 structure from v3.0 data."""
        
        # Start with basic fields
        v4_data = {
            "persona_id": v3_data["persona_id"],
            "schema_version": "4.0",
        }
        
        # Migrate identity from metadata
        metadata = v3_data.get("metadata", {})
        role = v3_data.get("role", {})
        
        v4_data["identity"] = {
            "display_name": v3_data.get("display_name", 
                v3_data["persona_id"].replace("_", " ").title()),
            "version": v3_data.get("version", "1.0.0"),
            "description": metadata.get("description", 
                f"Migrated persona: {v3_data['persona_id']}"),
            "author": metadata.get("author", "MAESTRO Team"),
            "created_at": metadata.get("created_at", "2025-01-01"),
            "updated_at": metadata.get("updated_at", "2025-12-06"),
            "category": metadata.get("category", "development"),
            "status": metadata.get("status", "active"),
            "human_alias": metadata.get("human_alias"),
        }
        result.changes.append("Created identity from metadata")
        
        # Migrate capabilities
        capabilities = v3_data.get("capabilities", {})
        v4_data["capabilities"] = {
            "core": capabilities.get("core", []),
            "tools": capabilities.get("tools", []),
            "expertise_areas": role.get("specializations", []),
            "experience_level": role.get("experience_level", 7),
            "autonomy_level": role.get("autonomy_level", 7),
        }
        result.changes.append("Migrated capabilities")
        
        # Add NEW: constraints (v4.0 feature)
        v4_data["constraints"] = cls.DEFAULT_CONSTRAINTS.copy()
        v4_data["constraints"]["resource_limits"] = {
            "max_tokens": v3_data.get("execution", {}).get("timeout_seconds", 300) * 25,
            "timeout_seconds": v3_data.get("execution", {}).get("timeout_seconds", 300),
        }
        result.changes.append("Added default constraints (NEW in v4.0)")
        
        # Add NEW: personality traits (v4.0 feature)
        role_type = cls._infer_role_type(v3_data["persona_id"])
        personality_defaults = cls.ROLE_PERSONALITY_DEFAULTS.get(
            role_type, 
            cls.ROLE_PERSONALITY_DEFAULTS["default"]
        )
        v4_data["personality"] = personality_defaults
        result.changes.append(f"Added personality traits based on role '{role_type}' (NEW in v4.0)")
        
        # Migrate prompts
        prompts = v3_data.get("prompts", {})
        v4_data["prompts"] = {
            "system_prompt": prompts.get("system_prompt", 
                f"You are a {v3_data['persona_id'].replace('_', ' ')}."),
            "task_prompt_template": prompts.get("task_prompt_template",
                "Complete the following task: {task}"),
        }
        result.changes.append("Migrated prompts")
        
        # Migrate execution config
        execution = v3_data.get("execution", {})
        v4_data["execution"] = {
            "timeout_seconds": execution.get("timeout_seconds", 300),
            "max_retries": execution.get("max_retries", 3),
            "priority": execution.get("priority", 5),
            "parallel_capable": execution.get("parallel_capable", False),
        }
        result.changes.append("Migrated execution config")
        
        # Add domain extension if SDLC persona
        dependencies = v3_data.get("dependencies", {})
        contracts = v3_data.get("contracts", {})
        if dependencies or contracts:
            v4_data["domain_extension"] = {
                "domain_type": "sdlc",
                "phase": cls._infer_phase(v3_data["persona_id"]),
                "deliverables": contracts.get("output", {}).get("required", []),
                "input_contracts": contracts.get("input", {}).get("required", []),
                "output_contracts": contracts.get("output", {}).get("required", []),
                "depends_on": dependencies.get("depends_on", []),
                "required_by": dependencies.get("required_by", []),
            }
            result.changes.append("Added SDLC domain extension")
        
        return v4_data
    
    @classmethod
    def _infer_role_type(cls, persona_id: str) -> str:
        """Infer role type from persona ID."""
        id_lower = persona_id.lower()
        
        if "analyst" in id_lower or "requirement" in id_lower:
            return "analyst"
        elif "architect" in id_lower:
            return "architect"
        elif "developer" in id_lower or "dev" in id_lower:
            return "developer"
        elif "qa" in id_lower or "test" in id_lower or "quality" in id_lower:
            return "qa"
        elif "devops" in id_lower or "deployment" in id_lower:
            return "devops"
        elif "writer" in id_lower or "document" in id_lower:
            return "writer"
        else:
            return "default"
    
    @classmethod
    def _infer_phase(cls, persona_id: str) -> str:
        """Infer SDLC phase from persona ID."""
        id_lower = persona_id.lower()
        
        if "requirement" in id_lower or "analyst" in id_lower:
            return "requirements"
        elif "architect" in id_lower or "design" in id_lower:
            return "design"
        elif "developer" in id_lower or "backend" in id_lower or "frontend" in id_lower:
            return "development"
        elif "qa" in id_lower or "test" in id_lower:
            return "testing"
        elif "devops" in id_lower or "deploy" in id_lower:
            return "deployment"
        else:
            return "development"
    
    @classmethod
    def migrate_directory(cls, source_dir: str, output_dir: str) -> Dict[str, Any]:
        """
        Migrate all personas in a directory.
        
        Args:
            source_dir: Directory with v3.0 persona JSON files
            output_dir: Directory to write v4.0 personas
            
        Returns:
            Summary of migration results
        """
        source_path = Path(source_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "migrations": [],
        }
        
        for json_file in source_path.glob("*.json"):
            results["total"] += 1
            
            try:
                with open(json_file, "r") as f:
                    v3_data = json.load(f)
                
                migration = cls.migrate_v3_to_v4(v3_data)
                results["migrations"].append(migration.to_dict())
                
                if migration.success:
                    results["success"] += 1
                    
                    # Write migrated persona
                    output_file = output_path / json_file.name
                    with open(output_file, "w") as f:
                        json.dump(migration.migrated_persona.to_dict(), f, indent=2)
                    
                    logger.info(f"Migrated: {migration.persona_id}")
                else:
                    results["failed"] += 1
                    logger.error(f"Failed: {migration.persona_id} - {migration.errors}")
                    
            except Exception as e:
                results["failed"] += 1
                logger.error(f"Error migrating {json_file}: {e}")
        
        return results
