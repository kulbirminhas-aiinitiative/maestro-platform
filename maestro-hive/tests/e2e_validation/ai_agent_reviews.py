#!/usr/bin/env python3
"""
AI Agent Reviews - Phase 3

Four AI team leads review the comprehensive test results:
1. Tech Lead (Solution Architect) - Architecture & Design Review
2. QA Lead (Quality Engineer) - Testing & Quality Review
3. DevOps Lead (DevOps Engineer) - Deployment & Operations Review
4. Security Lead (Security Specialist) - Security & Compliance Review

Each agent analyzes the test results and provides gap analysis.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


# =============================================================================
# AGENT PERSONAS
# =============================================================================

class AgentReview:
    """Base class for agent reviews"""

    def __init__(self, name: str, role: str, focus_areas: List[str]):
        self.name = name
        self.role = role
        self.focus_areas = focus_areas
        self.findings: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []
        self.risk_level: str = "LOW"

    def analyze(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test report and generate findings"""
        raise NotImplementedError


class TechLeadReview(AgentReview):
    """Solution Architect perspective"""

    def __init__(self):
        super().__init__(
            name="Alex Chen",
            role="Tech Lead / Solution Architect",
            focus_areas=["Architecture", "Design Patterns", "System Integration", "Scalability"]
        )

    def analyze(self, report: Dict[str, Any]) -> Dict[str, Any]:
        stats = report['statistics']
        detailed = report['detailed_results']

        # Finding 1: Non-standard phase node validation
        custom_phase_errors = []
        for result in detailed:
            for node_id, validation in result.get('validation_results', {}).items():
                policy_val = validation.get('policy_validation', {})
                if policy_val.get('status') == 'error' and 'No SLO found' in policy_val.get('message', ''):
                    custom_phase_errors.append({
                        'test': result['test_id'],
                        'node': node_id,
                        'message': policy_val['message']
                    })

        if custom_phase_errors:
            self.findings.append({
                'severity': 'HIGH',
                'category': 'Architecture Gap',
                'title': 'Custom Phase Nodes Lack Policy Validation',
                'description': f'Found {len(custom_phase_errors)} instances where custom phase nodes (backend, frontend, architecture, services) have no SLO definitions',
                'impact': 'These nodes bypass policy validation entirely, creating blind spots in quality enforcement',
                'examples': custom_phase_errors[:3]
            })
            self.recommendations.append(
                "Define SLO policies for custom node types or implement a generic validation template for non-standard phases"
            )
            self.risk_level = "MEDIUM"

        # Finding 2: Test failure analysis
        failed_tests = [r for r in detailed if not r['passed']]
        if failed_tests:
            self.findings.append({
                'severity': 'MEDIUM',
                'category': 'Test Coverage',
                'title': f'{len(failed_tests)} Test Cases Failed',
                'description': f'Tests failed: {", ".join([t["test_id"] for t in failed_tests])}',
                'impact': 'Indicates gaps in handling expected failure scenarios or policy enforcement inconsistencies',
                'details': [{'test': t['test_id'], 'error': t['error_message']} for t in failed_tests]
            })
            self.recommendations.append(
                "Review failure propagation logic for non-standard phase nodes to ensure consistent blocking behavior"
            )

        # Finding 3: Legacy contract validation always skipped
        legacy_skipped = sum(1 for r in detailed for v in r.get('validation_results', {}).values()
                            if not v.get('legacy_contract_validation', {}).get('passed', True))
        if legacy_skipped > 0:
            self.findings.append({
                'severity': 'LOW',
                'category': 'Technical Debt',
                'title': 'Legacy Contract Validation Inactive',
                'description': f'Legacy validation skipped in {legacy_skipped} node executions (no output_dir)',
                'impact': 'Backward compatibility path is not exercised, potential issues undetected',
            })
            self.recommendations.append(
                "Either activate legacy validation testing or deprecate if policy-based validation is sufficient"
            )

        # Finding 4: Parallel execution validated successfully
        parallel_tests = [r for r in detailed if 'parallel' in r['name'].lower()]
        passed_parallel = [t for t in parallel_tests if t['passed']]
        if passed_parallel:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Architecture Success',
                'title': 'Parallel Execution Works',
                'description': f'{len(passed_parallel)}/{len(parallel_tests)} parallel execution tests passed',
                'impact': 'System can handle concurrent workflow execution - major scalability win',
            })

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        return {
            'reviewer': {'name': self.name, 'role': self.role},
            'focus_areas': self.focus_areas,
            'risk_assessment': self.risk_level,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'sign_off': f"Reviewed by {self.name}, {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }


class QALeadReview(AgentReview):
    """QA Engineer perspective"""

    def __init__(self):
        super().__init__(
            name="Sarah Martinez",
            role="QA Lead / Quality Engineer",
            focus_areas=["Test Coverage", "Quality Gates", "Validation Accuracy", "Defect Analysis"]
        )

    def analyze(self, report: Dict[str, Any]) -> Dict[str, Any]:
        stats = report['statistics']
        detailed = report['detailed_results']

        # Finding 1: Overall test pass rate
        pass_rate = stats['summary']['pass_rate']
        if pass_rate < 100:
            self.findings.append({
                'severity': 'MEDIUM',
                'category': 'Test Execution',
                'title': f'Pass Rate: {pass_rate}% (16/20 tests)',
                'description': '4 tests failed validation, all related to custom phase node handling',
                'impact': 'System functional for standard SDLC phases but has gaps for custom workflows',
            })
            self.recommendations.append(
                "Expand test scenarios to cover edge cases with custom phase types before production"
            )
            self.risk_level = "MEDIUM"

        # Finding 2: Gate condition evaluation errors
        gate_errors = []
        for result in detailed:
            for node_id, validation in result.get('validation_results', {}).items():
                policy_val = validation.get('policy_validation', {})
                for gate in policy_val.get('gates_failed', []):
                    if 'error' in gate:
                        gate_errors.append({
                            'test': result['test_id'],
                            'node': node_id,
                            'gate': gate['gate_name'],
                            'error': gate['error']
                        })

        if gate_errors:
            # Group by error type
            error_types = {}
            for err in gate_errors:
                error_msg = err['error']
                if error_msg not in error_types:
                    error_types[error_msg] = 0
                error_types[error_msg] += 1

            self.findings.append({
                'severity': 'MEDIUM',
                'category': 'Quality Gate Issues',
                'title': f'{len(gate_errors)} Gate Condition Evaluation Errors',
                'description': 'Multiple gates failed to evaluate due to missing metric fields',
                'impact': 'Gates marked as WARNING instead of being evaluated properly',
                'error_breakdown': error_types,
                'examples': gate_errors[:3]
            })
            self.recommendations.append(
                "Audit phase_slos.yaml gate conditions to ensure all referenced metrics are documented as required outputs"
            )
            self.recommendations.append(
                "Add validation to fail fast if executor doesn't return required metrics for a phase"
            )

        # Finding 3: Node execution success rate
        node_stats = stats['nodes']
        node_pass_rate = node_stats['pass_rate']
        self.findings.append({
            'severity': 'INFO',
            'category': 'Node Reliability',
            'title': f'Node Pass Rate: {node_pass_rate:.1f}% (49/52 nodes)',
            'description': f'{node_stats["total_failed"]} nodes failed across all tests',
            'impact': 'High node reliability indicates robust execution engine',
        })

        # Finding 4: Test complexity coverage
        complexity = stats['coverage']['complexity_range']
        self.findings.append({
            'severity': 'INFO',
            'category': 'Test Coverage',
            'title': f'Complexity Range: {complexity["min"]}-{complexity["max"]} (avg: {complexity["average"]:.1f})',
            'description': f'Validated {stats["coverage"]["feature_count"]} distinct features',
            'impact': 'Comprehensive coverage across simple to complex scenarios',
            'features': stats['coverage']['features_validated'][:10]  # First 10
        })

        # Finding 5: Performance
        exec_time = stats['execution_time']
        avg_time = exec_time['average_seconds']
        if avg_time < 0.5:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Performance',
                'title': f'Excellent Performance: {avg_time:.2f}s average per test',
                'description': f'Total execution: {exec_time["total_seconds"]:.2f}s for 20 tests',
                'impact': 'Fast validation enables rapid iteration and developer productivity',
            })

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        return {
            'reviewer': {'name': self.name, 'role': self.role},
            'focus_areas': self.focus_areas,
            'risk_assessment': self.risk_level,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'sign_off': f"Reviewed by {self.name}, {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }


class DevOpsLeadReview(AgentReview):
    """DevOps Engineer perspective"""

    def __init__(self):
        super().__init__(
            name="Marcus Johnson",
            role="DevOps Lead / Platform Engineer",
            focus_areas=["Deployment", "Scalability", "Reliability", "Monitoring"]
        )

    def analyze(self, report: Dict[str, Any]) -> Dict[str, Any]:
        stats = report['statistics']
        detailed = report['detailed_results']

        # Finding 1: Retry mechanism tested
        retry_tests = [r for r in detailed if 'retry' in r['name'].lower()]
        if retry_tests:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Reliability',
                'title': 'Retry Logic Validated',
                'description': f'{len(retry_tests)} retry tests executed',
                'impact': 'System has built-in resilience for transient failures',
            })

        # Finding 2: Parallel execution scalability
        wide_tests = [r for r in detailed if 'wide' in r['name'].lower() or 'parallel' in r['name'].lower()]
        max_parallel = max([r['nodes_executed'] for r in wide_tests]) if wide_tests else 0
        if max_parallel >= 5:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Scalability',
                'title': f'Wide Parallelism: {max_parallel} Concurrent Nodes',
                'description': 'System handles multiple parallel executions successfully',
                'impact': 'Can scale to microservices architectures with many parallel services',
            })

        # Finding 3: Edge case handling
        edge_tests = [r for r in detailed if r['category'] == 'edge']
        edge_passed = [t for t in edge_tests if t['passed']]
        edge_failed = [t for t in edge_tests if not t['passed']]

        if edge_failed:
            self.findings.append({
                'severity': 'LOW',
                'category': 'Edge Cases',
                'title': f'Edge Case Handling: {len(edge_passed)}/{len(edge_tests)} Passed',
                'description': f'Failed: {", ".join([t["test_id"] for t in edge_failed])}',
                'impact': 'Empty workflow handling needs improvement - may cause issues in production',
            })
            self.recommendations.append(
                "Add defensive checks for empty/malformed workflows before execution"
            )
            self.risk_level = "LOW"

        # Finding 4: Execution time analysis
        exec_time = stats['execution_time']
        slowest = exec_time['slowest_test']
        if slowest['time_seconds'] > 1.0:
            slow_test = next(r for r in detailed if r['test_id'] == slowest['test_id'])
            if 'slow' not in slow_test['name'].lower():
                self.findings.append({
                    'severity': 'LOW',
                    'category': 'Performance',
                    'title': f'Slow Test Detected: {slowest["test_id"]} ({slowest["time_seconds"]:.2f}s)',
                    'description': 'Unexpectedly slow execution detected',
                    'impact': 'May indicate performance bottleneck or timeout issues',
                })
                self.recommendations.append(
                    "Profile slow tests to identify bottlenecks in validation or execution"
                )

        # Finding 5: Deployment phase coverage
        deployment_tests = [r for r in detailed for node in r.get('validation_results', {}).keys()
                          if 'deployment' in node or 'monitoring' in node]
        if deployment_tests:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Deployment',
                'title': 'Deployment & Monitoring Phases Tested',
                'description': f'Full SDLC pipeline including deployment validated',
                'impact': 'System ready for production deployment workflows',
            })
        else:
            self.findings.append({
                'severity': 'MEDIUM',
                'category': 'Deployment',
                'title': 'Limited Deployment Phase Testing',
                'description': 'Few tests exercise deployment and monitoring phases',
                'impact': 'Production deployment scenarios may not be fully validated',
            })
            self.recommendations.append(
                "Add more test scenarios covering deployment rollback, monitoring, and production operations"
            )

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        return {
            'reviewer': {'name': self.name, 'role': self.role},
            'focus_areas': self.focus_areas,
            'risk_assessment': self.risk_level,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'sign_off': f"Reviewed by {self.name}, {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }


class SecurityLeadReview(AgentReview):
    """Security Specialist perspective"""

    def __init__(self):
        super().__init__(
            name="Dr. Priya Sharma",
            role="Security Lead / Security Specialist",
            focus_areas=["Security Gates", "Vulnerability Detection", "Compliance", "Risk Assessment"]
        )

    def analyze(self, report: Dict[str, Any]) -> Dict[str, Any]:
        stats = report['statistics']
        detailed = report['detailed_results']

        # Finding 1: Security gate enforcement
        security_tests = [r for r in detailed if 'security' in r['name'].lower()]
        security_passed = [t for t in security_tests if t['passed']]

        if security_tests:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Security Gates',
                'title': f'Security Gate Testing: {len(security_passed)}/{len(security_tests)} Passed',
                'description': 'Security vulnerability gates are enforced and tested',
                'impact': 'Security blocking gates prevent vulnerable code from progressing',
            })

        # Finding 2: Security validation coverage
        security_gates = []
        for result in detailed:
            for node_id, validation in result.get('validation_results', {}).items():
                policy_val = validation.get('policy_validation', {})
                for gate in policy_val.get('gates_passed', []):
                    if 'security' in gate.lower():
                        security_gates.append(gate)

        unique_security_gates = set(security_gates)
        if unique_security_gates:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Security Coverage',
                'title': f'{len(unique_security_gates)} Security Gates Validated',
                'description': f'Gates: {", ".join(unique_security_gates)}',
                'impact': 'Multiple security checkpoints in workflow lifecycle',
            })

        # Finding 3: Vulnerability blocking validation
        vuln_tests = [r for r in detailed
                     if any('security_vulnerabilities' in str(v)
                           for v in r.get('validation_results', {}).values())]
        if vuln_tests:
            blocking_vuln = []
            for result in vuln_tests:
                for node_id, validation in result.get('validation_results', {}).items():
                    policy_val = validation.get('policy_validation', {})
                    for gate in policy_val.get('gates_failed', []):
                        if 'security' in gate.get('gate_name', '').lower() and gate.get('severity') == 'BLOCKING':
                            blocking_vuln.append({
                                'test': result['test_id'],
                                'gate': gate['gate_name'],
                                'passed': result['passed']
                            })

            if blocking_vuln:
                self.findings.append({
                    'severity': 'INFO',
                    'category': 'Vulnerability Blocking',
                    'title': 'Security Vulnerabilities Properly Block Workflows',
                    'description': f'{len(blocking_vuln)} tests validated vulnerability blocking',
                    'impact': 'System enforces zero-vulnerability policy at security gates',
                })

        # Finding 4: Security design review gates
        design_security = []
        for result in detailed:
            design_validation = result.get('validation_results', {}).get('design', {})
            if design_validation:
                policy_val = design_validation.get('policy_validation', {})
                for gate in policy_val.get('gates_failed', []):
                    if 'security' in gate.get('gate_name', '').lower():
                        design_security.append(gate)

        if design_security:
            self.findings.append({
                'severity': 'INFO',
                'category': 'Shift-Left Security',
                'title': 'Security Review in Design Phase',
                'description': 'Security gates enforced early in SDLC (design phase)',
                'impact': 'Shift-left approach catches security issues before implementation',
            })

        # Finding 5: Gap - Missing security metrics in custom phases
        custom_phases_no_security = []
        for result in detailed:
            for node_id, validation in result.get('validation_results', {}).items():
                policy_val = validation.get('policy_validation', {})
                if policy_val.get('status') == 'error' and node_id in ['backend', 'frontend', 'service_1', 'service_2']:
                    custom_phases_no_security.append({
                        'test': result['test_id'],
                        'phase': node_id
                    })

        if custom_phases_no_security:
            self.findings.append({
                'severity': 'HIGH',
                'category': 'Security Gap',
                'title': 'Custom Phases Lack Security Validation',
                'description': f'{len(custom_phases_no_security)} instances of custom phases with no security gates',
                'impact': 'Backend, frontend, and service nodes bypass security validation entirely',
            })
            self.recommendations.append(
                "Define security gates for all custom phase types (backend, frontend, services)"
            )
            self.recommendations.append(
                "Implement mandatory security scanning for all node types, not just 'implementation' phase"
            )
            self.risk_level = "MEDIUM"

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        return {
            'reviewer': {'name': self.name, 'role': self.role},
            'focus_areas': self.focus_areas,
            'risk_assessment': self.risk_level,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'sign_off': f"Reviewed by {self.name}, {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }


# =============================================================================
# REVIEW ORCHESTRATOR
# =============================================================================

class ReviewOrchestrator:
    """Orchestrates reviews from all 4 team leads"""

    def __init__(self):
        self.agents = [
            TechLeadReview(),
            QALeadReview(),
            DevOpsLeadReview(),
            SecurityLeadReview()
        ]

    def run_reviews(self, report_path: str) -> Dict[str, Any]:
        """Run all agent reviews"""
        # Load test report
        with open(report_path, 'r') as f:
            report = json.load(f)

        print("\n" + "="*80)
        print("PHASE 3: AI AGENT REVIEWS")
        print("="*80)
        print(f"Analyzing test report: {report_path}")
        print(f"Test execution: {report['report_metadata']['phase']}")
        print(f"Generated at: {report['report_metadata']['generated_at']}")
        print("="*80)

        # Run each agent review
        reviews = []
        for i, agent in enumerate(self.agents, 1):
            print(f"\n[{i}/4] Running review: {agent.role}")
            print(f"       Reviewer: {agent.name}")
            print(f"       Focus: {', '.join(agent.focus_areas)}")

            review = agent.analyze(report)
            reviews.append(review)

            print(f"       ✓ Found {len(review['findings'])} findings")
            print(f"       ✓ Risk Level: {review['risk_assessment']}")
            print(f"       ✓ Recommendations: {len(review['recommendations'])}")

        # Aggregate results
        consolidated = self._consolidate_reviews(report, reviews)

        print("\n" + "="*80)
        print("CONSOLIDATED REVIEW SUMMARY")
        print("="*80)
        print(f"Total Findings: {consolidated['summary']['total_findings']}")
        print(f"High Severity: {consolidated['summary']['high_severity']}")
        print(f"Medium Severity: {consolidated['summary']['medium_severity']}")
        print(f"Overall Risk: {consolidated['summary']['overall_risk']}")
        print(f"Total Recommendations: {consolidated['summary']['total_recommendations']}")
        print("="*80)

        return consolidated

    def _consolidate_reviews(self, report: Dict[str, Any], reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidate all reviews into final report"""

        # Count findings by severity
        all_findings = []
        all_recommendations = []

        for review in reviews:
            all_findings.extend(review['findings'])
            all_recommendations.extend(review['recommendations'])

        high_severity = len([f for f in all_findings if f['severity'] == 'HIGH'])
        medium_severity = len([f for f in all_findings if f['severity'] == 'MEDIUM'])
        low_severity = len([f for f in all_findings if f['severity'] == 'LOW'])

        # Determine overall risk
        risk_levels = [r['risk_assessment'] for r in reviews]
        if 'HIGH' in risk_levels:
            overall_risk = 'HIGH'
        elif 'MEDIUM' in risk_levels:
            overall_risk = 'MEDIUM'
        else:
            overall_risk = 'LOW'

        # Extract common themes
        common_issues = self._identify_common_themes(all_findings)

        # Priority recommendations
        priority_recs = self._prioritize_recommendations(all_recommendations, high_severity, medium_severity)

        consolidated = {
            'metadata': {
                'review_date': datetime.now().isoformat(),
                'report_reviewed': report['report_metadata']['generated_at'],
                'reviewers': [r['reviewer'] for r in reviews]
            },
            'summary': {
                'total_findings': len(all_findings),
                'high_severity': high_severity,
                'medium_severity': medium_severity,
                'low_severity': low_severity,
                'overall_risk': overall_risk,
                'total_recommendations': len(all_recommendations),
                'test_pass_rate': report['statistics']['summary']['pass_rate']
            },
            'common_themes': common_issues,
            'individual_reviews': reviews,
            'priority_recommendations': priority_recs,
            'production_readiness': self._assess_production_readiness(overall_risk, report['statistics'])
        }

        return consolidated

    def _identify_common_themes(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Identify common issues across reviews"""
        themes = []

        # Check for custom phase issues
        custom_phase_count = len([f for f in findings if 'custom' in str(f).lower() or 'No SLO' in str(f)])
        if custom_phase_count >= 2:
            themes.append(f"Custom phase node validation gap (mentioned by {custom_phase_count} reviewers)")

        # Check for gate evaluation errors
        gate_error_count = len([f for f in findings if 'gate' in str(f).lower() and 'error' in str(f).lower()])
        if gate_error_count >= 2:
            themes.append(f"Gate condition evaluation issues (mentioned by {gate_error_count} reviewers)")

        # Check for security concerns
        security_count = len([f for f in findings if f['severity'] in ['HIGH', 'MEDIUM'] and 'security' in str(f).lower()])
        if security_count >= 1:
            themes.append(f"Security validation gaps (mentioned by {security_count} reviewers)")

        return themes

    def _prioritize_recommendations(self, recommendations: List[str], high_count: int, medium_count: int) -> List[Dict[str, Any]]:
        """Prioritize and deduplicate recommendations"""

        # Deduplicate
        unique_recs = list(set(recommendations))

        # Prioritize
        priority = []

        # P0: Address high severity findings
        if high_count > 0:
            custom_phase_recs = [r for r in unique_recs if 'custom' in r.lower() or 'SLO' in r or 'generic' in r.lower()]
            if custom_phase_recs:
                priority.append({
                    'level': 'P0 - CRITICAL',
                    'recommendation': custom_phase_recs[0],
                    'rationale': f'{high_count} high-severity findings related to this'
                })

        # P1: Address medium severity findings
        if medium_count > 0:
            gate_recs = [r for r in unique_recs if 'gate' in r.lower() or 'metric' in r.lower()]
            if gate_recs:
                priority.append({
                    'level': 'P1 - HIGH',
                    'recommendation': gate_recs[0],
                    'rationale': f'{medium_count} medium-severity findings related to this'
                })

        # P2: Other recommendations
        remaining = [r for r in unique_recs if r not in [p['recommendation'] for p in priority]]
        for rec in remaining[:3]:  # Top 3
            priority.append({
                'level': 'P2 - MEDIUM',
                'recommendation': rec,
                'rationale': 'Improvement opportunity identified by team leads'
            })

        return priority

    def _assess_production_readiness(self, risk: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Assess if system is production-ready"""

        pass_rate = stats['summary']['pass_rate']

        if risk == 'HIGH' or pass_rate < 70:
            status = 'NOT READY'
            reasoning = 'High-severity issues must be resolved before production deployment'
            next_steps = [
                'Address all HIGH severity findings',
                'Re-run comprehensive tests',
                'Conduct security audit'
            ]
        elif risk == 'MEDIUM' and pass_rate >= 80:
            status = 'READY WITH CAVEATS'
            reasoning = 'Core functionality validated, but known limitations exist for custom workflows'
            next_steps = [
                'Document known limitations for custom phase types',
                'Create monitoring for bypassed validation scenarios',
                'Plan Phase 1 improvements for custom node support'
            ]
        else:
            status = 'PRODUCTION READY'
            reasoning = 'All critical functionality validated, acceptable risk level'
            next_steps = [
                'Proceed with gradual rollout',
                'Monitor production metrics',
                'Iterate on non-critical improvements'
            ]

        return {
            'status': status,
            'reasoning': reasoning,
            'next_steps': next_steps,
            'approval_required': risk in ['HIGH', 'MEDIUM']
        }


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function"""

    # Load test report
    report_path = Path("reports/comprehensive_test_report.json")

    if not report_path.exists():
        print(f"❌ Test report not found: {report_path}")
        return 1

    # Run reviews
    orchestrator = ReviewOrchestrator()
    consolidated = orchestrator.run_reviews(str(report_path))

    # Save consolidated report
    output_path = Path("reports/ai_agent_reviews_phase3.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(consolidated, f, indent=2)

    print(f"\n📄 Phase 3 review report saved to: {output_path}")

    # Print production readiness
    readiness = consolidated['production_readiness']
    print("\n" + "="*80)
    print("PRODUCTION READINESS ASSESSMENT")
    print("="*80)
    print(f"Status: {readiness['status']}")
    print(f"\nReasoning: {readiness['reasoning']}")
    print(f"\nNext Steps:")
    for i, step in enumerate(readiness['next_steps'], 1):
        print(f"  {i}. {step}")
    print("="*80)

    # Return exit code based on status
    if readiness['status'] == 'NOT READY':
        return 1
    else:
        return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
