#!/usr/bin/env python3
"""
Test Gap Analyzer for Team Execution V2

Analyzes test execution results, identifies gaps, and proposes improvements.

This script:
1. Tracks test execution in detail
2. Identifies failures and their root causes
3. Analyzes workflow gaps
4. Proposes specific improvements
5. Generates actionable reports
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Gap:
    """Identified gap in the workflow"""
    id: str
    category: str  # contract_design, execution, validation, team_composition, etc.
    severity: str  # critical, high, medium, low
    title: str
    description: str
    evidence: List[str]
    impact: str
    root_cause: str
    proposed_fix: str
    affected_components: List[str]
    estimated_effort: str  # hours or days


@dataclass
class ImprovementProposal:
    """Proposed improvement to the workflow"""
    id: str
    title: str
    description: str
    rationale: str
    implementation_steps: List[str]
    affected_files: List[str]
    estimated_effort: str
    priority: str  # critical, high, medium, low
    dependencies: List[str]


class TestGapAnalyzer:
    """Analyzes test results and identifies gaps."""
    
    def __init__(self, results_dir: Path):
        self.results_dir = Path(results_dir)
        self.gaps: List[Gap] = []
        self.improvements: List[ImprovementProposal] = []
        self.metrics = {}
    
    def analyze(self) -> Dict[str, Any]:
        """Run complete gap analysis."""
        logger.info("🔍 Starting gap analysis...")
        
        # Load test results
        summary_file = self.results_dir / "test_suite_summary.json"
        if not summary_file.exists():
            logger.error(f"No test summary found at {summary_file}")
            return {}
        
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        # Analyze each scenario
        for scenario_result in summary.get("scenarios", []):
            self._analyze_scenario(scenario_result)
        
        # Calculate metrics
        self._calculate_metrics(summary)
        
        # Generate report
        report = self._generate_report(summary)
        
        # Save report
        report_file = self.results_dir / "gap_analysis_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📊 Gap analysis complete. Report saved to: {report_file}")
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _analyze_scenario(self, scenario_result: Dict[str, Any]):
        """Analyze a single scenario result."""
        scenario_id = scenario_result["scenario_id"]
        scenario_name = scenario_result["scenario_name"]
        
        logger.info(f"\nAnalyzing scenario: {scenario_name}")
        
        # Check if scenario failed
        if not scenario_result.get("success", False):
            logger.warning(f"  ⚠️  Scenario failed")
            
            # Analyze test case failures
            for test_case in scenario_result.get("test_cases", []):
                if not test_case.get("passed", False):
                    self._analyze_test_case_failure(
                        test_case,
                        scenario_id,
                        scenario_name
                    )
            
            # Analyze success criteria failures
            criteria = scenario_result.get("success_criteria", {})
            for criterion in criteria.get("criteria", []):
                if not criterion.get("met", False):
                    self._analyze_criterion_failure(
                        criterion,
                        scenario_id,
                        scenario_name
                    )
        else:
            logger.info(f"  ✅ Scenario passed")
    
    def _analyze_test_case_failure(
        self,
        test_case: Dict[str, Any],
        scenario_id: str,
        scenario_name: str
    ):
        """Analyze a failed test case."""
        test_name = test_case["name"]
        failures = test_case.get("failures", [])
        
        logger.info(f"    ❌ Test case failed: {test_name}")
        logger.info(f"       Failures: {failures}")
        
        # Categorize the gap
        category = self._categorize_failure(test_name, failures)
        
        # Create gap record
        gap = Gap(
            id=f"gap_{scenario_id}_{test_name.lower().replace(' ', '_')}",
            category=category,
            severity=self._assess_severity(test_name, failures),
            title=f"{test_name} failed in {scenario_name}",
            description=test_case.get("description", ""),
            evidence=failures,
            impact=self._assess_impact(test_name, failures),
            root_cause=self._infer_root_cause(test_name, failures),
            proposed_fix=self._propose_fix(test_name, failures, category),
            affected_components=self._identify_affected_components(
                test_name,
                failures,
                category
            ),
            estimated_effort=self._estimate_effort(category, failures)
        )
        
        self.gaps.append(gap)
        
        # Generate improvement proposal if needed
        if gap.severity in ["critical", "high"]:
            improvement = self._create_improvement_proposal(gap)
            if improvement:
                self.improvements.append(improvement)
    
    def _analyze_criterion_failure(
        self,
        criterion: Dict[str, Any],
        scenario_id: str,
        scenario_name: str
    ):
        """Analyze a failed success criterion."""
        criterion_name = criterion["criterion"]
        expected = criterion["expected"]
        actual = criterion["actual"]
        
        logger.info(f"    ❌ Criterion not met: {criterion_name}")
        logger.info(f"       Expected: {expected}, Actual: {actual}")
        
        # Create gap
        gap = Gap(
            id=f"gap_{scenario_id}_{criterion_name}",
            category="quality_metrics",
            severity="high" if criterion_name.startswith("min_") else "medium",
            title=f"Quality criterion '{criterion_name}' not met",
            description=f"Expected {expected}, got {actual}",
            evidence=[f"{criterion_name}: {actual} (expected {expected})"],
            impact=f"Quality standards not achieved in {scenario_name}",
            root_cause=self._infer_criterion_root_cause(criterion_name, expected, actual),
            proposed_fix=self._propose_criterion_fix(criterion_name, expected, actual),
            affected_components=["quality_validation", "execution_engine"],
            estimated_effort="4-8 hours"
        )
        
        self.gaps.append(gap)
    
    def _categorize_failure(self, test_name: str, failures: List[str]) -> str:
        """Categorize the type of failure."""
        test_lower = test_name.lower()
        failures_str = " ".join(failures).lower()
        
        if "contract" in test_lower or "contract" in failures_str:
            return "contract_design"
        elif "parallel" in test_lower or "parallel" in failures_str:
            return "parallel_execution"
        elif "team" in test_lower or "persona" in failures_str:
            return "team_composition"
        elif "quality" in test_lower or "coverage" in failures_str:
            return "quality_validation"
        elif "api" in test_lower or "endpoint" in failures_str:
            return "api_implementation"
        elif "validation" in test_lower or "fulfillment" in failures_str:
            return "contract_validation"
        else:
            return "execution_general"
    
    def _assess_severity(self, test_name: str, failures: List[str]) -> str:
        """Assess severity of the failure."""
        critical_keywords = ["security", "authentication", "data loss", "corruption"]
        high_keywords = ["contract", "parallel", "validation", "quality"]
        
        test_lower = test_name.lower()
        failures_str = " ".join(failures).lower()
        
        if any(kw in test_lower or kw in failures_str for kw in critical_keywords):
            return "critical"
        elif any(kw in test_lower or kw in failures_str for kw in high_keywords):
            return "high"
        elif len(failures) > 3:
            return "high"
        elif len(failures) > 1:
            return "medium"
        else:
            return "low"
    
    def _assess_impact(self, test_name: str, failures: List[str]) -> str:
        """Assess impact of the failure."""
        if "parallel" in test_name.lower():
            return "Parallel execution not working - significant time savings lost"
        elif "contract" in test_name.lower():
            return "Contract-based coordination failing - cannot enable parallel work"
        elif "quality" in test_name.lower():
            return "Quality standards not met - deliverables may be subpar"
        elif "team" in test_name.lower():
            return "Team composition incorrect - wrong expertise assigned"
        else:
            return "Execution workflow impaired - feature may not work correctly"
    
    def _infer_root_cause(self, test_name: str, failures: List[str]) -> str:
        """Infer root cause of the failure."""
        if "openapi" in " ".join(failures).lower():
            return "Contract designer agent not generating proper OpenAPI specs"
        elif "mock" in " ".join(failures).lower():
            return "Mock generation from contracts not working"
        elif "parallel" in test_name.lower():
            return "Parallel execution coordination logic has issues"
        elif "blueprint" in test_name.lower():
            return "Blueprint selection or application not working correctly"
        else:
            return "Execution engine workflow has gaps"
    
    def _propose_fix(
        self,
        test_name: str,
        failures: List[str],
        category: str
    ) -> str:
        """Propose a fix for the failure."""
        fixes = {
            "contract_design": "Enhance ContractDesignerAgent with better prompts and validation",
            "parallel_execution": "Fix parallel coordination logic in execution engine",
            "team_composition": "Improve TeamComposerAgent's persona selection logic",
            "quality_validation": "Strengthen quality validation checks and scoring",
            "contract_validation": "Implement comprehensive contract fulfillment checking",
            "api_implementation": "Add API implementation validation against contracts"
        }
        
        return fixes.get(category, "Review and fix execution workflow")
    
    def _identify_affected_components(
        self,
        test_name: str,
        failures: List[str],
        category: str
    ) -> List[str]:
        """Identify which components are affected."""
        component_map = {
            "contract_design": ["ContractDesignerAgent", "contract_manager"],
            "parallel_execution": ["ParallelExecutor", "CoordinationEngine"],
            "team_composition": ["TeamComposerAgent", "BlueprintSelector"],
            "quality_validation": ["QualityValidator", "TestEngine"],
            "contract_validation": ["ContractValidator", "FulfillmentChecker"],
            "api_implementation": ["PersonaExecutor", "CodeGenerator"]
        }
        
        return component_map.get(category, ["TeamExecutionEngineV2"])
    
    def _estimate_effort(self, category: str, failures: List[str]) -> str:
        """Estimate effort to fix."""
        if len(failures) > 5:
            return "2-3 days"
        elif category in ["contract_design", "parallel_execution"]:
            return "1-2 days"
        elif category in ["quality_validation", "contract_validation"]:
            return "8-16 hours"
        else:
            return "4-8 hours"
    
    def _infer_criterion_root_cause(
        self,
        criterion_name: str,
        expected: Any,
        actual: Any
    ) -> str:
        """Infer root cause for criterion failure."""
        if "coverage" in criterion_name:
            return "Test generation not comprehensive enough"
        elif "quality_score" in criterion_name:
            return "Quality scoring algorithm too lenient or validation incomplete"
        elif "time_savings" in criterion_name:
            return "Parallel execution not optimized or not working"
        elif "latency" in criterion_name:
            return "Performance optimization needed"
        else:
            return "Implementation not meeting specification"
    
    def _propose_criterion_fix(
        self,
        criterion_name: str,
        expected: Any,
        actual: Any
    ) -> str:
        """Propose fix for criterion failure."""
        if "coverage" in criterion_name:
            return "Enhance test generation with more comprehensive test cases"
        elif "quality_score" in criterion_name:
            return "Tighten quality validation and scoring thresholds"
        elif "time_savings" in criterion_name:
            return "Optimize parallel execution paths and reduce coordination overhead"
        else:
            return "Review implementation and ensure spec compliance"
    
    def _create_improvement_proposal(self, gap: Gap) -> Optional[ImprovementProposal]:
        """Create an improvement proposal from a gap."""
        
        improvement_templates = {
            "contract_design": {
                "title": "Enhance Contract Design Agent",
                "description": "Improve ContractDesignerAgent to generate complete, validated contracts",
                "steps": [
                    "Add contract schema validation",
                    "Enhance prompts with examples",
                    "Add contract completeness checks",
                    "Implement contract versioning"
                ],
                "files": [
                    "team_execution_v2.py (ContractDesignerAgent)",
                    "contract_manager.py"
                ]
            },
            "parallel_execution": {
                "title": "Fix Parallel Execution Coordination",
                "description": "Ensure parallel execution works correctly with proper coordination",
                "steps": [
                    "Fix dependency resolution logic",
                    "Add parallel execution tracking",
                    "Implement proper mock generation",
                    "Add time savings measurement"
                ],
                "files": [
                    "team_execution_v2.py (ParallelExecutor)",
                    "parallel_coordinator_v2.py"
                ]
            },
            "team_composition": {
                "title": "Improve Team Composition Logic",
                "description": "Enhance TeamComposerAgent's persona selection",
                "steps": [
                    "Add expertise matching algorithm",
                    "Implement blueprint search and ranking",
                    "Add team size optimization",
                    "Include role validation"
                ],
                "files": [
                    "team_execution_v2.py (TeamComposerAgent)",
                    "blueprints/team_factory.py"
                ]
            },
            "quality_validation": {
                "title": "Strengthen Quality Validation",
                "description": "Implement comprehensive quality checks and scoring",
                "steps": [
                    "Add test coverage measurement",
                    "Implement code quality scoring",
                    "Add security vulnerability scanning",
                    "Create quality gate enforcement"
                ],
                "files": [
                    "team_execution_v2.py (QualityValidator)",
                    "quality_fabric_integration.py"
                ]
            },
            "contract_validation": {
                "title": "Implement Contract Fulfillment Validation",
                "description": "Add comprehensive contract fulfillment checking",
                "steps": [
                    "Create contract spec parser",
                    "Implement deliverable verification",
                    "Add interface compliance checking",
                    "Generate fulfillment reports"
                ],
                "files": [
                    "team_execution_v2.py (ContractValidator)",
                    "contract_manager.py"
                ]
            }
        }
        
        template = improvement_templates.get(gap.category)
        if not template:
            return None
        
        return ImprovementProposal(
            id=f"improvement_{gap.id}",
            title=template["title"],
            description=template["description"],
            rationale=f"Addresses gap: {gap.title}. {gap.impact}",
            implementation_steps=template["steps"],
            affected_files=template["files"],
            estimated_effort=gap.estimated_effort,
            priority=gap.severity,
            dependencies=[]
        )
    
    def _calculate_metrics(self, summary: Dict[str, Any]):
        """Calculate analysis metrics."""
        self.metrics = {
            "total_gaps": len(self.gaps),
            "gaps_by_severity": defaultdict(int),
            "gaps_by_category": defaultdict(int),
            "total_improvements": len(self.improvements),
            "improvements_by_priority": defaultdict(int),
            "estimated_total_effort_hours": 0
        }
        
        for gap in self.gaps:
            self.metrics["gaps_by_severity"][gap.severity] += 1
            self.metrics["gaps_by_category"][gap.category] += 1
            
            # Parse effort (rough estimate)
            effort_str = gap.estimated_effort
            if "day" in effort_str:
                hours = float(effort_str.split("-")[0]) * 8
            else:
                hours = float(effort_str.split("-")[0])
            self.metrics["estimated_total_effort_hours"] += hours
        
        for improvement in self.improvements:
            self.metrics["improvements_by_priority"][improvement.priority] += 1
    
    def _generate_report(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "test_suite_summary": {
                "total_scenarios": summary.get("total_scenarios", 0),
                "passed_scenarios": summary.get("passed_scenarios", 0),
                "failed_scenarios": summary.get("failed_scenarios", 0)
            },
            "metrics": dict(self.metrics),
            "gaps": [asdict(gap) for gap in self.gaps],
            "improvement_proposals": [asdict(imp) for imp in self.improvements],
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate high-level recommendations."""
        recommendations = []
        
        if self.metrics["gaps_by_severity"]["critical"] > 0:
            recommendations.append({
                "priority": "CRITICAL",
                "recommendation": "Address critical gaps immediately before proceeding",
                "details": f"{self.metrics['gaps_by_severity']['critical']} critical issues found"
            })
        
        if self.metrics["gaps_by_category"]["contract_design"] > 2:
            recommendations.append({
                "priority": "HIGH",
                "recommendation": "Contract design system needs significant improvement",
                "details": "Multiple contract-related failures detected"
            })
        
        if self.metrics["gaps_by_category"]["parallel_execution"] > 1:
            recommendations.append({
                "priority": "HIGH",
                "recommendation": "Parallel execution coordination needs fixes",
                "details": "Parallel workflow not functioning correctly"
            })
        
        if self.metrics["gaps_by_category"]["quality_validation"] > 1:
            recommendations.append({
                "priority": "MEDIUM",
                "recommendation": "Strengthen quality validation mechanisms",
                "details": "Quality standards not consistently met"
            })
        
        total_effort_days = self.metrics["estimated_total_effort_hours"] / 8
        recommendations.append({
            "priority": "INFO",
            "recommendation": f"Estimated {total_effort_days:.1f} days to address all gaps",
            "details": f"{len(self.gaps)} gaps identified, {len(self.improvements)} improvements proposed"
        })
        
        return recommendations
    
    def _print_summary(self, report: Dict[str, Any]):
        """Print analysis summary to console."""
        logger.info("\n" + "="*80)
        logger.info("📊 GAP ANALYSIS SUMMARY")
        logger.info("="*80 + "\n")
        
        # Test results
        ts = report["test_suite_summary"]
        logger.info(f"Test Scenarios: {ts['total_scenarios']}")
        logger.info(f"  ✅ Passed: {ts['passed_scenarios']}")
        logger.info(f"  ❌ Failed: {ts['failed_scenarios']}\n")
        
        # Gaps
        metrics = report["metrics"]
        logger.info(f"Gaps Identified: {metrics['total_gaps']}")
        if metrics['total_gaps'] > 0:
            logger.info(f"  By Severity:")
            for severity in ["critical", "high", "medium", "low"]:
                count = metrics['gaps_by_severity'].get(severity, 0)
                if count > 0:
                    logger.info(f"    {severity.upper()}: {count}")
            
            logger.info(f"  By Category:")
            for category, count in metrics['gaps_by_category'].items():
                logger.info(f"    {category}: {count}")
        
        logger.info(f"\nImprovement Proposals: {metrics['total_improvements']}")
        if metrics['total_improvements'] > 0:
            for priority in ["critical", "high", "medium", "low"]:
                count = metrics['improvements_by_priority'].get(priority, 0)
                if count > 0:
                    logger.info(f"  {priority.upper()}: {count}")
        
        logger.info(f"\nEstimated Effort: {metrics['estimated_total_effort_hours'] / 8:.1f} days")
        
        # Recommendations
        logger.info("\n" + "-"*80)
        logger.info("🎯 RECOMMENDATIONS")
        logger.info("-"*80 + "\n")
        
        for rec in report["recommendations"]:
            priority_icon = {
                "CRITICAL": "🚨",
                "HIGH": "⚠️",
                "MEDIUM": "📌",
                "INFO": "ℹ️"
            }.get(rec["priority"], "•")
            
            logger.info(f"{priority_icon} [{rec['priority']}] {rec['recommendation']}")
            logger.info(f"   {rec['details']}\n")


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        results_dir = Path("./test_comprehensive_output")
    else:
        results_dir = Path(sys.argv[1])
    
    if not results_dir.exists():
        logger.error(f"Results directory not found: {results_dir}")
        return 1
    
    analyzer = TestGapAnalyzer(results_dir)
    report = analyzer.analyze()
    
    # Return exit code based on severity
    if report["metrics"]["gaps_by_severity"].get("critical", 0) > 0:
        return 2  # Critical issues
    elif report["metrics"]["gaps_by_severity"].get("high", 0) > 0:
        return 1  # High priority issues
    else:
        return 0  # Success or only low priority issues


if __name__ == "__main__":
    exit(main())
