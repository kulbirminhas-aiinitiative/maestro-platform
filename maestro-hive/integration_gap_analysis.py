#!/usr/bin/env python3
"""
Integration and Gap Analysis
Checks for missing integrations, edge cases, and architectural gaps
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class Gap:
    category: str
    severity: str
    title: str
    description: str
    impact: str
    recommendation: str

class GapAnalyzer:
    def __init__(self):
        self.gaps: List[Gap] = []
    
    def add_gap(self, category: str, severity: str, title: str, description: str, impact: str, recommendation: str):
        self.gaps.append(Gap(category, severity, title, description, impact, recommendation))
    
    def analyze_phase_orchestrator(self):
        """Analyze phase_workflow_orchestrator.py for gaps"""
        
        filepath = Path('phase_workflow_orchestrator.py')
        if not filepath.exists():
            return
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Check 1: Error recovery strategy
        if 'rollback' not in content.lower():
            self.add_gap(
                "Error Handling",
                "HIGH",
                "No Rollback Mechanism",
                "When a phase fails, there's no mechanism to rollback partial changes",
                "Failed phases may leave the system in an inconsistent state",
                "Add rollback capability to revert partial phase execution"
            )
        
        # Check 2: Timeout handling
        if 'timeout' not in content.lower():
            self.add_gap(
                "Robustness",
                "MEDIUM",
                "No Timeout Protection",
                "Long-running phases could hang indefinitely",
                "System could become unresponsive during phase execution",
                "Add configurable timeouts per phase with graceful handling"
            )
        
        # Check 3: Concurrent execution
        if 'concurrent' not in content.lower() and 'parallel' not in content.lower():
            self.add_gap(
                "Performance",
                "MEDIUM",
                "No Parallel Execution",
                "Personas within a phase execute sequentially",
                "Longer execution times when personas could work in parallel",
                "Consider parallel persona execution within phases where dependencies allow"
            )
        
        # Check 4: State persistence
        if 'save_state' not in content or 'checkpoint' not in content.lower():
            self.add_gap(
                "Reliability",
                "HIGH",
                "Limited State Checkpointing",
                "If orchestrator crashes, progress may be lost",
                "Need to restart entire workflow after failures",
                "Add frequent checkpointing of phase state"
            )
        
        # Check 5: Observability
        if 'metrics' not in content.lower() and 'telemetry' not in content.lower():
            self.add_gap(
                "Observability",
                "MEDIUM",
                "Limited Metrics/Telemetry",
                "No structured metrics for monitoring phase execution",
                "Difficult to monitor and optimize workflow performance",
                "Add metrics collection (duration, success rate, quality scores)"
            )
    
    def analyze_integration_points(self):
        """Check integration with existing systems"""
        
        # Check team_execution integration
        orchestrator_path = Path('phase_workflow_orchestrator.py')
        team_exec_path = Path('team_execution.py')
        
        if orchestrator_path.exists() and team_exec_path.exists():
            with open(orchestrator_path, 'r') as f:
                orch_content = f.read()
            with open(team_exec_path, 'r') as f:
                team_content = f.read()
            
            # Check if orchestrator properly imports team_execution
            if 'from team_execution import' in orch_content:
                # Good! Check if it handles import errors
                if 'TEAM_EXECUTION_AVAILABLE' not in orch_content:
                    self.add_gap(
                        "Integration",
                        "LOW",
                        "Import Error Handling",
                        "team_execution import doesn't check availability",
                        "Runtime errors if team_execution is missing",
                        "Wrap import in try/except and set availability flag"
                    )
        
        # Check session_manager integration
        if orchestrator_path.exists():
            with open(orchestrator_path, 'r') as f:
                content = f.read()
            
            if 'SessionManager' not in content:
                self.add_gap(
                    "Integration",
                    "MEDIUM",
                    "No Session Persistence",
                    "Not integrated with session_manager for state persistence",
                    "Cannot resume workflows after interruption",
                    "Integrate with SessionManager for persistent state"
                )
    
    def analyze_edge_cases(self):
        """Check for edge case handling"""
        
        # Empty requirements
        self.add_gap(
            "Edge Cases",
            "LOW",
            "Empty Requirement Handling",
            "What happens if requirement is empty or malformed?",
            "May cause confusing errors or unexpected behavior",
            "Add validation for requirement format and content"
        )
        
        # Phase cycle detection
        self.add_gap(
            "Edge Cases",
            "MEDIUM",
            "Infinite Loop Protection",
            "If a phase keeps failing and retrying, could loop forever",
            "System hangs on problematic phases",
            "Add max retry limit per phase and escalation policy"
        )
        
        # Disk space
        self.add_gap(
            "Edge Cases",
            "LOW",
            "Disk Space Checks",
            "No validation of available disk space before generating artifacts",
            "Could fail mid-execution due to disk space",
            "Check disk space before starting phases that generate large artifacts"
        )
        
        # Concurrent workflow sessions
        self.add_gap(
            "Edge Cases",
            "MEDIUM",
            "Concurrent Session Handling",
            "What if multiple workflows run with same session_id?",
            "Data corruption or race conditions",
            "Add session locking or validation to prevent conflicts"
        )
    
    def analyze_testing_coverage(self):
        """Check testing coverage"""
        
        test_files = ['test_phase_orchestrator.py', 'test_integration_full.py']
        
        for test_file in test_files:
            if not Path(test_file).exists():
                self.add_gap(
                    "Testing",
                    "HIGH",
                    f"Missing Test File: {test_file}",
                    f"Test file {test_file} not found",
                    "Cannot verify functionality",
                    f"Create {test_file} with comprehensive tests"
                )
        
        # Check test coverage depth
        if Path('test_phase_orchestrator.py').exists():
            with open('test_phase_orchestrator.py', 'r') as f:
                test_content = f.read()
            
            critical_tests = [
                ('test_phase_failure', "Phase failure handling not tested"),
                ('test_gate_validation', "Gate validation not tested"),
                ('test_quality_progression', "Progressive quality not tested"),
                ('test_resume', "Resume capability not tested"),
            ]
            
            for test_name, description in critical_tests:
                if test_name not in test_content:
                    self.add_gap(
                        "Testing",
                        "MEDIUM",
                        f"Missing Test: {test_name}",
                        description,
                        "Critical functionality not validated",
                        f"Add {test_name} to test suite"
                    )
    
    def analyze_documentation(self):
        """Check documentation completeness"""
        
        doc_files = [
            'PHASE_WORKFLOW_STATUS.md',
            'WEEK_2_COMPLETE.md',
        ]
        
        for doc_file in doc_files:
            if not Path(doc_file).exists():
                self.add_gap(
                    "Documentation",
                    "LOW",
                    f"Missing Documentation: {doc_file}",
                    f"Documentation file {doc_file} not found",
                    "Harder for team to understand implementation",
                    f"Create {doc_file} with clear explanations"
                )
    
    def analyze_configuration(self):
        """Check configuration management"""
        
        self.add_gap(
            "Configuration",
            "MEDIUM",
            "No Configuration File",
            "Phase thresholds and policies hardcoded in code",
            "Difficult to tune without code changes",
            "Create config.yaml or similar for phase configuration"
        )
        
        self.add_gap(
            "Configuration",
            "LOW",
            "No Environment-Specific Config",
            "No separate configs for dev/staging/prod",
            "Same thresholds used in all environments",
            "Support environment-specific configuration"
        )
    
    def analyze_security(self):
        """Check security considerations"""
        
        self.add_gap(
            "Security",
            "MEDIUM",
            "No Input Sanitization",
            "User requirements not sanitized before execution",
            "Potential for injection attacks or malformed input",
            "Add input validation and sanitization"
        )
        
        self.add_gap(
            "Security",
            "LOW",
            "No Access Control",
            "No validation of who can start/stop workflows",
            "Anyone with access can manipulate workflows",
            "Add authentication and authorization"
        )
    
    def print_report(self):
        """Print gap analysis report"""
        print("=" * 80)
        print("GAP ANALYSIS REPORT")
        print("=" * 80)
        print()
        
        if not self.gaps:
            print("✅ No gaps identified!")
            return
        
        # Group by category
        by_category = {}
        for gap in self.gaps:
            if gap.category not in by_category:
                by_category[gap.category] = []
            by_category[gap.category].append(gap)
        
        # Print by category
        for category in sorted(by_category.keys()):
            gaps = by_category[category]
            
            # Group by severity within category
            critical = [g for g in gaps if g.severity == 'CRITICAL']
            high = [g for g in gaps if g.severity == 'HIGH']
            medium = [g for g in gaps if g.severity == 'MEDIUM']
            low = [g for g in gaps if g.severity == 'LOW']
            
            print(f"\n{'=' * 80}")
            print(f"CATEGORY: {category}")
            print(f"{'=' * 80}")
            print(f"Total Gaps: {len(gaps)} (🔴 {len(critical)} Critical, 🟠 {len(high)} High, 🟡 {len(medium)} Medium, 🔵 {len(low)} Low)")
            
            for severity_name, severity_gaps in [('CRITICAL', critical), ('HIGH', high), ('MEDIUM', medium), ('LOW', low)]:
                if not severity_gaps:
                    continue
                
                icon = '🔴' if severity_name == 'CRITICAL' else '🟠' if severity_name == 'HIGH' else '🟡' if severity_name == 'MEDIUM' else '🔵'
                
                for gap in severity_gaps:
                    print(f"\n{icon} {severity_name}: {gap.title}")
                    print(f"  Description: {gap.description}")
                    print(f"  Impact: {gap.impact}")
                    print(f"  Recommendation: {gap.recommendation}")
        
        # Executive Summary
        print("\n" + "=" * 80)
        print("EXECUTIVE SUMMARY")
        print("=" * 80)
        
        total = len(self.gaps)
        critical = len([g for g in self.gaps if g.severity == 'CRITICAL'])
        high = len([g for g in self.gaps if g.severity == 'HIGH'])
        medium = len([g for g in self.gaps if g.severity == 'MEDIUM'])
        low = len([g for g in self.gaps if g.severity == 'LOW'])
        
        print(f"\nTotal Gaps Identified: {total}")
        print(f"  🔴 CRITICAL: {critical}")
        print(f"  🟠 HIGH: {high}")
        print(f"  🟡 MEDIUM: {medium}")
        print(f"  🔵 LOW: {low}")
        print()
        
        # Prioritization
        print("RECOMMENDED PRIORITIES:")
        print()
        
        if critical > 0:
            print("⚠️  Phase 1 (IMMEDIATE): Address all CRITICAL gaps before production")
            print("   These gaps could cause system failures or data corruption")
            print()
        
        if high > 0:
            print("⚠️  Phase 2 (SHORT-TERM): Address HIGH priority gaps")
            print("   These gaps affect reliability and user experience")
            print()
        
        if medium > 0:
            print("✓ Phase 3 (MEDIUM-TERM): Address MEDIUM priority gaps")
            print("   These gaps improve robustness and maintainability")
            print()
        
        if low > 0:
            print("✓ Phase 4 (LONG-TERM): Address LOW priority gaps as time permits")
            print("   These gaps are nice-to-haves for production quality")
        
        # Overall assessment
        print("\n" + "=" * 80)
        print("OVERALL ASSESSMENT")
        print("=" * 80)
        print()
        
        if critical > 0:
            print("🔴 NOT READY: Critical gaps must be addressed")
        elif high > 3:
            print("🟠 NEEDS WORK: Multiple high-priority gaps to address")
        elif high > 0 or medium > 5:
            print("🟡 APPROACHING READY: Good progress, some gaps to address")
        else:
            print("🟢 PRODUCTION READY: Minimal gaps, ready for deployment")

def main():
    """Run gap analysis"""
    analyzer = GapAnalyzer()
    
    print("Starting integration and gap analysis...")
    print()
    
    analyzer.analyze_phase_orchestrator()
    analyzer.analyze_integration_points()
    analyzer.analyze_edge_cases()
    analyzer.analyze_testing_coverage()
    analyzer.analyze_documentation()
    analyzer.analyze_configuration()
    analyzer.analyze_security()
    
    analyzer.print_report()

if __name__ == '__main__':
    main()
