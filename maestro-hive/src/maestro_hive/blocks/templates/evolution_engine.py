"""
Maestro Template Evolution Engine
The "Brain" that evolves templates based on user interactions.

Responsibilities:
1. Capture "Template Usage" events (Original vs. Final).
2. Analyze diffs to understand user preferences.
3. Propose updates to the Template Registry (Evolution).
4. Feed data into the ML model for continuous improvement.
"""

import logging
import json
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("EvolutionEngine")

@dataclass
class EvolutionEvent:
    template_id: str
    project_id: str
    timestamp: str
    original_content: str
    final_content: str
    diff_score: float

class EvolutionEngine:
    """
    Manages the evolutionary lifecycle of templates.
    """

    def __init__(self, workspace_root: str, learning_db_path: str = ".maestro/learning_db.json"):
        self.workspace_root = Path(workspace_root)
        self.learning_db_path = self.workspace_root / learning_db_path
        self._ensure_db()

    def _ensure_db(self):
        if not self.learning_db_path.parent.exists():
            self.learning_db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.learning_db_path.exists():
            with open(self.learning_db_path, 'w') as f:
                json.dump({"events": [], "insights": []}, f)

    def record_interaction(self, template_id: str, project_id: str, original: str, final: str):
        """
        Record a user interaction with a template.
        """
        # Calculate similarity/diff
        matcher = difflib.SequenceMatcher(None, original, final)
        similarity = matcher.ratio()
        
        event = EvolutionEvent(
            template_id=template_id,
            project_id=project_id,
            timestamp=datetime.now().isoformat(),
            original_content=original,
            final_content=final,
            diff_score=similarity
        )
        
        self._save_event(event)
        logger.info(f"Recorded interaction for {template_id}. Similarity: {similarity:.2f}")
        
        # Trigger immediate analysis
        self._analyze_event(event)

    def _save_event(self, event: EvolutionEvent):
        with open(self.learning_db_path, 'r+') as f:
            data = json.load(f)
            data["events"].append(event.__dict__)
            f.seek(0)
            json.dump(data, f, indent=2)

    def _analyze_event(self, event: EvolutionEvent):
        """
        Analyze the event to generate insights.
        This is where the ML model would be invoked.
        """
        if event.diff_score < 0.8:
            logger.warning(f"High deviation detected for {event.template_id}. User rewrote >20% of the template.")
            self._propose_evolution(event)

    def _propose_evolution(self, event: EvolutionEvent):
        """
        Propose an update to the template based on the user's changes.
        """
        # In a real implementation, this would use an LLM to summarize the changes
        # and propose a PR to the registry.
        insight = {
            "template_id": event.template_id,
            "type": "EVOLUTION_PROPOSAL",
            "reason": "High user deviation",
            "suggestion": "Analyze 'final_content' to incorporate user patterns."
        }
        
        with open(self.learning_db_path, 'r+') as f:
            data = json.load(f)
            data["insights"].append(insight)
            f.seek(0)
            json.dump(data, f, indent=2)
            
        logger.info(f"Evolution proposal generated for {event.template_id}")

# ============================================================================
# Demo
# ============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = EvolutionEngine(".")
    
    # Simulate a scenario where a user heavily modifies the HIPAA template
    original = """
    ## HIPAA Compliance
    The system must encrypt PHI using AES-256.
    """
    
    final = """
    ## HIPAA Compliance
    The system must encrypt PHI using AES-256-GCM.
    Keys must be rotated every 90 days.
    Access logs must be retained for 7 years.
    """
    
    engine.record_interaction("compliance/hipaa.md.j2", "MediTrack", original, final)
