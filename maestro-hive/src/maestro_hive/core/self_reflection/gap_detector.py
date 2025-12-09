#!/usr/bin/env python3
"""
Gap Detector: The Self-Reflection Engine
Scans the workspace against the 'Ideal State' registry to identify missing capabilities.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import sys

# Ensure we can import from local modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@dataclass
class Gap:
    block_id: str
    block_name: str
    gap_type: str  # 'MISSING_FILE', 'MISSING_CAPABILITY', 'MISSING_TEST'
    description: str
    severity: str
    remediation: str
    metadata: Optional[Dict[str, Any]] = None

class GapDetector:
    def __init__(self, workspace_root: str, registry_path: str):
        self.workspace_root = Path(workspace_root)
        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()
        self.gaps: List[Gap] = []

    def _load_registry(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Registry not found at {self.registry_path}")
        with open(self.registry_path, 'r') as f:
            return json.load(f)

    def scan(self, scope: Optional[str] = None) -> List[Gap]:
        """
        Run the full self-reflection scan.
        
        Args:
            scope: Optional filter string. If provided, only blocks matching
                   the scope (by ID, name, or category) will be scanned.
        """
        print(f"🔍 Starting Self-Reflection Scan on {self.workspace_root}...")
        if scope:
            print(f"   Filtering by scope: '{scope}'")
            
        self.gaps = []
        
        for block in self.registry.get('blocks', []):
            # Apply scope filter if provided
            if scope:
                s = scope.lower()
                if (s not in block['id'].lower() and 
                    s not in block['name'].lower() and 
                    s != block.get('category', '').lower()):
                    continue
            
            self._check_block_structure(block)
            self._check_block_capabilities(block)
            
        return self.gaps

    def _check_block_structure(self, block: Dict[str, Any]):
        """Check if the physical files for the block exist."""
        requirements = block.get('requirements', {})
        required_files = requirements.get('files', [])
        
        for rel_path in required_files:
            full_path = self.workspace_root / rel_path
            if not full_path.exists():
                self.gaps.append(Gap(
                    block_id=block['id'],
                    block_name=block['name'],
                    gap_type="MISSING_FILE",
                    description=f"Required file '{rel_path}' is missing.",
                    severity=block['criticality'],
                    remediation=f"Generate file '{rel_path}' using the {block['category']} template."
                ))

    def _check_block_capabilities(self, block: Dict[str, Any]):
        """
        Advanced: Check if specific keywords/capabilities exist in the files.
        This is a heuristic check for 'implementation completeness'.
        """
        requirements = block.get('requirements', {})
        capabilities = requirements.get('capabilities', [])
        required_files = requirements.get('files', [])
        
        # If files are missing, we can't check capabilities
        existing_files = [f for f in required_files if (self.workspace_root / f).exists()]
        if not existing_files:
            return

        # Naive check: Search for capability keywords in all block files
        # In a real AI platform, this would use an LLM or AST analysis
        combined_content = ""
        for rel_path in existing_files:
            try:
                with open(self.workspace_root / rel_path, 'r') as f:
                    combined_content += f.read().lower()
            except Exception:
                continue

        for cap_entry in capabilities:
            # Handle both string and dict capabilities
            if isinstance(cap_entry, dict):
                cap_name = cap_entry['name']
                cap_desc = cap_entry.get('description', '')
            else:
                cap_name = cap_entry
                cap_desc = ''

            # Normalize capability to a keyword (e.g., "rollback" -> "rollback")
            keyword = cap_name.lower().replace("_", " ")
            keyword_variant = cap_name.lower().replace("_", "")
            
            if keyword not in combined_content and keyword_variant not in combined_content:
                description = f"Capability '{cap_name}' not detected in implementation."
                if cap_desc:
                    description += f"\n\n**Definition:** {cap_desc}"

                self.gaps.append(Gap(
                    block_id=block['id'],
                    block_name=block['name'],
                    gap_type="MISSING_CAPABILITY",
                    description=description,
                    severity="MEDIUM", # Capabilities are usually less critical than the file itself
                    remediation=f"Implement '{cap_name}' logic in {existing_files[0]}.",
                    metadata={"capability": cap_name}
                ))

    def generate_report(self, output_format: str = 'text') -> str:
        if not self.gaps:
            return "✅ System Healthy. No gaps detected."

        if output_format == 'json':
            return json.dumps([asdict(g) for g in self.gaps], indent=2)
        
        # Text Report
        report = ["# 🧠 Self-Reflection Report", ""]
        
        by_severity = {'HIGH': [], 'MEDIUM': [], 'LOW': []}
        for gap in self.gaps:
            by_severity[gap.severity].append(gap)
            
        for sev in ['HIGH', 'MEDIUM', 'LOW']:
            gaps = by_severity[sev]
            if gaps:
                report.append(f"## 🚨 {sev} Priority Gaps ({len(gaps)})")
                for g in gaps:
                    report.append(f"- **[{g.block_name}]** {g.description}")
                    report.append(f"  - *Fix:* {g.remediation}")
                report.append("")
                
        return "\n".join(report)

if __name__ == "__main__":
    # Default paths assuming script is run from its location
    current_dir = Path(__file__).parent
    workspace_root = Path("/home/ec2-user/projects/maestro-platform/maestro-hive")
    registry_path = current_dir / "registry.json"
    
    detector = GapDetector(workspace_root, registry_path)
    detector.scan()
    print(detector.generate_report())
