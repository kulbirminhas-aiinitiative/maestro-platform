"""
Maestro Block Assembler
The "Builder" for Templates as a Service.

Responsibilities:
1. Load Jinja2 blocks from the Registry.
2. Load Project Context from Memory (ContextManager).
3. Render blocks using Jinja2.
4. Assemble the final artifact.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Import Context Manager
try:
    from ..context_manager import ContextManager, ProjectContext
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from context_manager import ContextManager, ProjectContext

logger = logging.getLogger("BlockAssembler")

class BlockAssembler:
    """
    Assembles artifacts from Jinja2 blocks using persistent context.
    """

    def __init__(self, workspace_root: str, registry_path: str):
        self.workspace_root = Path(workspace_root)
        self.registry_path = Path(registry_path)
        self.context_manager = ContextManager(workspace_root)
        
        # Initialize Jinja2 Environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.registry_path)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        logger.info(f"BlockAssembler initialized with registry: {self.registry_path}")

    def assemble(self, block_names: List[str]) -> str:
        """
        Assemble a document from a list of block names.
        """
        # 1. Load Context (The Memory)
        context = self.context_manager.load_context()
        if not context:
            raise ValueError("Project Context not initialized. Run ContextManager.initialize_project() first.")
        
        logger.info(f"Assembling artifact for project: {context.project_name}")
        
        artifact_parts = []
        
        # 2. Render Blocks
        for block_name in block_names:
            try:
                template = self.env.get_template(block_name)
                # Pass 'context' to the template so it can access context.decisions
                rendered = template.render(context=context)
                artifact_parts.append(rendered)
                logger.info(f"  [+] Rendered block: {block_name}")
            except Exception as e:
                logger.error(f"Failed to render block {block_name}: {e}")
                artifact_parts.append(f"<!-- ERROR RENDERING BLOCK {block_name}: {e} -->")

        # 3. Concatenate
        return "\n\n".join(artifact_parts)

# ============================================================================
# Demo
# ============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Paths
    # Assuming this script is run from src/maestro_hive/blocks/templates/
    # and registry is at src/maestro_hive/blocks/registry/
    
    # Adjust paths for where the script is actually located vs where we run it
    # We are creating it at src/maestro_hive/blocks/templates/engine.py
    # Registry is at src/maestro_hive/blocks/registry
    
    base_path = Path(__file__).parent.parent # src/maestro_hive/blocks
    registry_path = base_path / "registry"
    workspace_root = Path(".").resolve() # Current CWD
    
    assembler = BlockAssembler(str(workspace_root), str(registry_path))
    
    # Ensure context exists (from previous step)
    # If not, initialize it
    if not assembler.context_manager.load_context():
        assembler.context_manager.initialize_project(
            name="MediTrack",
            description="Patient Vitals Tracker",
            industry="Healthcare",
            compliance=["HIPAA"]
        )
        assembler.context_manager.update_decision("encryption", "AES-256")
        assembler.context_manager.update_decision("auth_provider", "Auth0")
        assembler.context_manager.update_decision("database", "PostgreSQL")

    # Assemble SRS
    # We only have one block 'compliance/hipaa.md.j2' for now
    blocks = ["compliance/hipaa.md.j2"]
    
    print("\n=== Assembled Artifact ===")
    print(assembler.assemble(blocks))
