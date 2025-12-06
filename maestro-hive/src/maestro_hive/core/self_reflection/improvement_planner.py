#!/usr/bin/env python3
"""
Improvement Planner: The Roadmap Generator
Takes identified gaps and prioritizes them into an actionable execution plan.
"""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from gap_detector import GapDetector, Gap

class ImprovementPlanner:
    def __init__(self, detector: GapDetector):
        self.detector = detector

    def create_plan(self, output_path: str):
        """Generates a prioritized roadmap based on detected gaps."""
        gaps = self.detector.scan()
        
        if not gaps:
            print("No gaps to plan for!")
            return

        # Sort by severity: HIGH > MEDIUM > LOW
        severity_map = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        sorted_gaps = sorted(gaps, key=lambda g: severity_map.get(g.severity, 3))

        plan_content = [
            f"# 🚀 Auto-Generated Improvement Plan",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Objective:** Close {len(gaps)} identified gaps to reach Platform Maturity.",
            "",
            "## 📋 Executive Summary",
            "The Self-Reflection Engine has identified critical structural and functional gaps.",
            "Immediate attention is required for **Core** and **Quality** blocks.",
            "",
            "## 🛠️ Action Plan",
            ""
        ]

        for i, gap in enumerate(sorted_gaps, 1):
            icon = "🔴" if gap.severity == "HIGH" else "🟡" if gap.severity == "MEDIUM" else "🟢"
            plan_content.append(f"### {i}. {icon} Fix {gap.block_name} ({gap.gap_type})")
            plan_content.append(f"- **Problem:** {gap.description}")
            plan_content.append(f"- **Impact:** {gap.severity} severity impact on platform stability.")
            plan_content.append(f"- **Action:** `{gap.remediation}`")
            plan_content.append("")

        # Write to file
        with open(output_path, 'w') as f:
            f.write("\n".join(plan_content))
        
        print(f"✅ Improvement Plan generated at: {output_path}")

if __name__ == "__main__":
    current_dir = Path(__file__).parent
    workspace_root = Path("/home/ec2-user/projects/maestro-platform/maestro-hive")
    registry_path = current_dir / "registry.json"
    
    detector = GapDetector(workspace_root, registry_path)
    planner = ImprovementPlanner(detector)
    
    output_file = workspace_root / "SELF_IMPROVEMENT_PLAN.md"
    planner.create_plan(output_file)
