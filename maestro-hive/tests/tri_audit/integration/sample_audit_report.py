#!/usr/bin/env python3
"""
Sample Tri-Modal Audit Report Generator

Demonstrates the full tri-modal audit system with sample reports.
"""

import asyncio
import json
from pathlib import Path

# Import from test_full_audit
import sys
sys.path.insert(0, str(Path(__file__).parent))

from test_full_audit import (
    TriModalAuditOrchestrator,
    AuditReportGenerator,
    ReportFormat,
    AuditDashboard
)


async def generate_sample_reports():
    """Generate sample audit reports in all formats"""

    print("=" * 80)
    print("TRI-MODAL AUDIT SYSTEM - SAMPLE REPORT GENERATION")
    print("=" * 80)

    # Run audit
    orchestrator = TriModalAuditOrchestrator()
    print("\nRunning tri-modal audit...")

    report = await orchestrator.run_full_audit("sample-demo-001")

    print(f"✓ Audit completed in {report.execution_time:.3f}s")
    print(f"  - Audit ID: {report.audit_id}")
    print(f"  - Verdict: {report.verdict.value}")
    print(f"  - Overall Health Score: {report.overall_health_score:.1f}/100")
    print(f"  - Can Deploy: {'YES ✓' if report.can_deploy else 'NO ✗'}")

    # Generate reports
    generator = AuditReportGenerator()

    print("\n" + "-" * 80)
    print("REPORT GENERATION")
    print("-" * 80)

    # JSON Report
    print("\n1. JSON Report:")
    json_report = generator.generate_report(report, ReportFormat.JSON)
    print(json.dumps(json.loads(json_report), indent=2)[:500] + "...")

    # HTML Report
    print("\n2. HTML Report:")
    html_report = generator.generate_report(report, ReportFormat.HTML)
    print(f"   Generated {len(html_report)} characters of HTML")
    print(f"   Preview: {html_report[:200]}...")

    # Markdown Report
    print("\n3. Markdown Report:")
    md_report = generator.generate_report(report, ReportFormat.MARKDOWN)
    print(md_report[:600] + "...")

    # Dashboard Data
    print("\n4. Dashboard Data:")
    dashboard_data = generator.generate_dashboard_data(report)
    print(json.dumps(dashboard_data, indent=2))

    # Aggregated Metrics
    print("\n" + "-" * 80)
    print("AGGREGATED METRICS")
    print("-" * 80)
    print(f"\nDDE Score:  {report.aggregated_metrics.dde_score * 100:.1f}/100")
    print(f"BDV Score:  {report.aggregated_metrics.bdv_score * 100:.1f}/100")
    print(f"ACC Score:  {report.aggregated_metrics.acc_score * 100:.1f}/100")
    print(f"\nWeighted Overall Health: {report.aggregated_metrics.overall_health_score:.1f}/100")
    print(f"  (DDE: 30%, BDV: 40%, ACC: 30%)")

    # Violations
    print("\n" + "-" * 80)
    print("VIOLATIONS")
    print("-" * 80)
    print(f"\nTotal Violations:    {report.aggregated_metrics.total_violations}")
    print(f"Blocking Violations: {report.aggregated_metrics.blocking_violations}")
    print(f"Warning Violations:  {report.aggregated_metrics.warning_violations}")

    print("\nTop Violations:")
    for i, violation in enumerate(report.violations[:5], 1):
        print(f"{i}. [{violation.severity.value}] {violation.title}")
        print(f"   Stream: {violation.stream}, Component: {violation.component}")

    # Recommendations
    print("\n" + "-" * 80)
    print("RECOMMENDATIONS")
    print("-" * 80)
    for i, rec in enumerate(report.recommendations, 1):
        print(f"\n{i}. [{rec.priority}] {rec.title}")
        print(f"   Affected Streams: {', '.join(rec.affected_streams)}")
        print(f"   Estimated Effort: {rec.estimated_effort}")
        print(f"   Description: {rec.description}")

    # Stream Details
    print("\n" + "-" * 80)
    print("STREAM DETAILS")
    print("-" * 80)

    print("\nDDE (Dependency-Driven Execution):")
    print(f"  Status:         {'PASS ✓' if report.dde_result.passed else 'FAIL ✗'}")
    print(f"  Completeness:   {report.dde_result.completeness:.2%}")
    print(f"  Gate Pass Rate: {report.dde_result.gate_pass_rate:.2%}")
    print(f"  Execution Time: {report.dde_result.execution_time:.3f}s")

    print("\nBDV (Behavior-Driven Validation):")
    print(f"  Status:        {'PASS ✓' if report.bdv_result.passed else 'FAIL ✗'}")
    print(f"  Coverage:      {report.bdv_result.coverage:.2%}")
    print(f"  Compliance:    {report.bdv_result.compliance:.2%}")
    print(f"  Flake Rate:    {report.bdv_result.flake_rate:.2%}")
    print(f"  Scenarios:     {report.bdv_result.passed_scenarios}/{report.bdv_result.total_scenarios} passed")
    print(f"  Execution Time: {report.bdv_result.execution_time:.3f}s")

    print("\nACC (Architectural Conformance Checking):")
    print(f"  Status:         {'PASS ✓' if report.acc_result.passed else 'FAIL ✗'}")
    print(f"  Avg Complexity: {report.acc_result.complexity_avg:.2f}")
    print(f"  Avg Coupling:   {report.acc_result.coupling_avg:.2f}")
    print(f"  Cycles:         {report.acc_result.cycles}")
    print(f"  Blocking Viol.: {report.acc_result.blocking_violations}")
    print(f"  Warning Viol.:  {report.acc_result.warning_violations}")
    print(f"  Execution Time: {report.acc_result.execution_time:.3f}s")

    # Diagnosis
    print("\n" + "-" * 80)
    print("DIAGNOSIS")
    print("-" * 80)
    print(f"\n{report.diagnosis}")

    # Dashboard
    print("\n" + "-" * 80)
    print("DASHBOARD TRENDS")
    print("-" * 80)

    dashboard = AuditDashboard()
    dashboard.add_audit(report)

    # Run a few more audits for trends
    for i in range(2, 6):
        additional_report = await orchestrator.run_full_audit(f"sample-demo-{i:03d}")
        dashboard.add_audit(additional_report)

    trends = dashboard.get_trend_data(limit=5)
    print("\nHealth Score Trend:")
    print(f"  {trends['health_scores']}")

    verdict_dist = dashboard.get_verdict_distribution()
    print("\nVerdict Distribution:")
    for verdict, count in verdict_dist.items():
        print(f"  {verdict}: {count}")

    hotspots = dashboard.get_violation_hotspots()
    print("\nViolation Hotspots (Top 5):")
    for component, count in list(hotspots.items())[:5]:
        print(f"  {component}: {count} violations")

    print("\n" + "=" * 80)
    print("REPORT GENERATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(generate_sample_reports())
