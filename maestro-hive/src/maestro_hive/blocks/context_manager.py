"""
Maestro Context Manager
The "Memory" of the Template Service.

Responsibilities:
1. Load/Save Project Context from .maestro/context.json
2. Manage the "Ledger" of decisions (e.g., "database": "postgres")
3. Ensure consistency across different template generations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("ContextManager")

@dataclass
class ProjectContext:
    """
    The Persistent State Ledger.
    """
    project_name: str
    description: str
    industry: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    compliance: List[str] = field(default_factory=list)
    
    # The Decision Ledger: Tracks choices made by AI or User
    # e.g., {"database": "postgres", "auth": "auth0", "encryption": "AES-256"}
    decisions: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata for tracking updates
    metadata: Dict[str, Any] = field(default_factory=dict)

class ContextManager:
    """
    Manages the persistence and retrieval of ProjectContext.
    """
    
    CONTEXT_FILE = ".maestro/context.json"

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.context_path = self.workspace_root / self.CONTEXT_FILE

    def load_context(self) -> Optional[ProjectContext]:
        """Load context from disk."""
        if not self.context_path.exists():
            logger.warning(f"Context file not found at {self.context_path}")
            return None

        try:
            with open(self.context_path, 'r') as f:
                data = json.load(f)
                return ProjectContext(**data)
        except Exception as e:
            logger.error(f"Failed to load context: {e}")
            return None

    def save_context(self, context: ProjectContext):
        """Save context to disk."""
        # Ensure directory exists
        self.context_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.context_path, 'w') as f:
                json.dump(asdict(context), f, indent=2)
            logger.info(f"Context saved to {self.context_path}")
        except Exception as e:
            logger.error(f"Failed to save context: {e}")

    def update_decision(self, key: str, value: Any):
        """
        Update a specific decision in the ledger.
        This is the primary way the AI Hydrator persists its choices.
        """
        context = self.load_context()
        if not context:
            raise ValueError("Cannot update decision: Context not initialized")
        
        context.decisions[key] = value
        self.save_context(context)
        logger.info(f"Decision recorded: {key} = {value}")

    def initialize_project(self, name: str, description: str, **kwargs) -> ProjectContext:
        """Initialize a new project context."""
        context = ProjectContext(
            project_name=name,
            description=description,
            **kwargs
        )
        self.save_context(context)
        return context

# ============================================================================
# Demo
# ============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Simulate DDE initializing a project
    mgr = ContextManager(".")
    
    print("--- Initializing Project ---")
    ctx = mgr.initialize_project(
        name="MediTrack",
        description="Patient Vitals Tracker",
        industry="Healthcare",
        compliance=["HIPAA"]
    )
    print(f"Created: {ctx.project_name} (Industry: {ctx.industry})")
    
    # Simulate AI Hydrator making a decision later
    print("\n--- AI Making Decision ---")
    mgr.update_decision("database", "PostgreSQL")
    mgr.update_decision("encryption", "AES-256")
    
    # Verify Persistence
    print("\n--- Verifying Memory ---")
    loaded_ctx = mgr.load_context()
    print(f"Decisions Ledger: {loaded_ctx.decisions}")
