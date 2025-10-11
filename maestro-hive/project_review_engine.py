#!/usr/bin/env python3.11
"""
Project Review Engine - Hybrid AI Agent + Analytical Tools

ARCHITECTURE:
    ┌─────────────────────────────────────────────┐
    │      Project Review Engine (Orchestrator)   │
    └─────────────────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
    ┌───────▼────────┐      ┌──────▼──────┐
    │ Analytical     │      │ AI Agent    │
    │ Tools (Python) │      │ (Reviewer)  │
    └───────┬────────┘      └──────┬──────┘
            │                      │
            │  Quantitative Data   │  Qualitative Analysis
            └──────────┬───────────┘
                       │
            ┌──────────▼──────────┐
            │  Comprehensive      │
            │  Review Reports     │
            └─────────────────────┘

WORKFLOW:
1. Tools gather metrics (file counts, coverage, etc.)
2. Tools analyze implementation completeness
3. AI Agent reads key files for context
4. AI Agent interprets metrics with domain knowledge
5. AI Agent identifies gaps vs requirements
6. AI Agent generates remediation plan
7. Engine saves all reports and metrics

Usage:
    python project_review_engine.py \\
        --project ./sunday_com \\
        --requirements requirements_document.md \\
        --output-dir ./reviews

Integration with SDLC:
    # Add to end of SDLC workflow
    await review_engine.review_project(
        project_path=output_dir,
        requirement_doc="requirements_document.md"
    )
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole
from review_tools import ProjectReviewTools
from project_reviewer_persona import PROJECT_REVIEWER_PERSONA, ProjectReviewConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProjectReviewEngine:
    """
    Hybrid Review Engine combining analytical tools with AI agent.

    Tools provide: Quantitative metrics
    Agent provides: Qualitative insights and recommendations
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize review engine"""
        self.api_key = api_key
        self.reviewer_agent = None

    async def initialize(self):
        """Initialize AI reviewer agent"""
        config = AgentConfig(
            name=PROJECT_REVIEWER_PERSONA["name"],
            role=AgentRole.CUSTOM,
            custom_instructions=PROJECT_REVIEWER_PERSONA["system_prompt"],
            expertise=PROJECT_REVIEWER_PERSONA["expertise"],
            api_key=self.api_key
        )

        self.reviewer_agent = TeamAgent(config)
        logger.info("✓ Project Reviewer Agent initialized")

    async def review_project(
        self,
        project_path: str | Path,
        requirement_doc: Optional[str] = None,
        output_dir: Optional[str | Path] = None,
        config: Optional[ProjectReviewConfig] = None
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive project review.

        Args:
            project_path: Path to project directory
            requirement_doc: Path to requirements document (relative to project)
            output_dir: Where to save review reports
            config: Review configuration

        Returns:
            Dictionary with review results and file paths
        """
        project_path = Path(project_path)
        output_dir = Path(output_dir) if output_dir else project_path / "reviews"
        output_dir.mkdir(exist_ok=True)

        logger.info(f"\n{'='*80}")
        logger.info(f"STARTING PROJECT REVIEW: {project_path.name}")
        logger.info(f"{'='*80}\n")

        # Step 1: Gather quantitative metrics using tools
        logger.info("Step 1/5: Gathering quantitative metrics...")
        metrics = await self._gather_metrics(project_path)

        # Step 2: Read requirements document
        logger.info("Step 2/5: Reading requirements document...")
        requirements = await self._read_requirements(project_path, requirement_doc)

        # Step 3: Sample key implementation files
        logger.info("Step 3/5: Sampling key implementation files...")
        implementation_samples = await self._sample_implementation(project_path)

        # Step 4: AI Agent performs qualitative analysis
        logger.info("Step 4/5: AI Agent performing qualitative analysis...")
        analysis = await self._ai_analysis(
            project_path=project_path,
            metrics=metrics,
            requirements=requirements,
            implementation_samples=implementation_samples
        )

        # Step 5: Generate comprehensive reports
        logger.info("Step 5/5: Generating comprehensive reports...")
        reports = await self._generate_reports(
            project_path=project_path,
            metrics=metrics,
            analysis=analysis,
            output_dir=output_dir
        )

        logger.info(f"\n{'='*80}")
        logger.info(f"REVIEW COMPLETE!")
        logger.info(f"{'='*80}\n")
        logger.info(f"Reports saved to: {output_dir}")
        logger.info(f"  - {reports['maturity_report']}")
        logger.info(f"  - {reports['gap_analysis']}")
        logger.info(f"  - {reports['remediation_plan']}")
        logger.info(f"  - {reports['metrics_json']}\n")

        return {
            "metrics": metrics,
            "analysis": analysis,
            "reports": reports,
            "completion_percentage": metrics.get("completion_percentage", 0),
            "review_timestamp": datetime.now().isoformat()
        }

    async def _gather_metrics(self, project_path: Path) -> Dict[str, Any]:
        """Gather all quantitative metrics using analytical tools"""
        metrics = ProjectReviewTools.gather_all_metrics(project_path)

        # Calculate weighted completion
        completion = ProjectReviewTools.calculate_weighted_completion(metrics)
        metrics["completion_percentage"] = completion

        # Determine maturity level
        metrics["maturity_level"] = self._determine_maturity_level(completion)

        return metrics

    async def _read_requirements(
        self,
        project_path: Path,
        requirement_doc: Optional[str]
    ) -> Optional[str]:
        """Read requirements document if it exists"""
        if not requirement_doc:
            # Try common names
            for name in ["requirements_document.md", "requirements.md", "REQUIREMENTS.md"]:
                req_path = project_path / name
                if req_path.exists():
                    requirement_doc = name
                    break

        if requirement_doc:
            req_path = project_path / requirement_doc
            if req_path.exists():
                return req_path.read_text()

        return None

    async def _sample_implementation(self, project_path: Path) -> Dict[str, str]:
        """Sample key implementation files for AI to review"""
        samples = {}

        # Sample backend routes
        backend_routes = project_path / "backend" / "src" / "routes" / "index.ts"
        if backend_routes.exists():
            samples["backend_routes_index"] = backend_routes.read_text()

        # Sample frontend App
        frontend_app = project_path / "frontend" / "src" / "App.tsx"
        if frontend_app.exists():
            samples["frontend_app"] = frontend_app.read_text()

        # Sample a stubbed page
        for page in (project_path / "frontend" / "src" / "pages").rglob("*.tsx"):
            content = page.read_text()
            if "coming soon" in content.lower():
                samples[f"stubbed_page_{page.name}"] = content
                break

        # Sample package.json for dependencies
        for pkg in ["backend/package.json", "frontend/package.json"]:
            pkg_path = project_path / pkg
            if pkg_path.exists():
                samples[pkg.replace("/", "_")] = pkg_path.read_text()

        return samples

    async def _ai_analysis(
        self,
        project_path: Path,
        metrics: Dict[str, Any],
        requirements: Optional[str],
        implementation_samples: Dict[str, str]
    ) -> Dict[str, Any]:
        """AI Agent performs qualitative analysis"""

        if not self.reviewer_agent:
            await self.initialize()

        # Build context for AI agent
        context = self._build_analysis_context(
            project_path,
            metrics,
            requirements,
            implementation_samples
        )

        # Ask AI agent to perform analysis
        prompt = f"""Conduct a comprehensive project review with the following data:

{context}

Provide your analysis in the following structure:

## MATURITY ASSESSMENT
- Overall completion: {metrics['completion_percentage']}%
- Maturity level: {metrics['maturity_level']}
- Your assessment of this percentage (is it accurate? inflated? deflated?)

## DETAILED BREAKDOWN
Analyze each dimension:
1. Documentation Quality
2. Implementation Completeness
3. Testing Coverage
4. DevOps Readiness
5. Security Implementation

For each, provide:
- Current state
- What's missing
- Quality assessment

## GAP ANALYSIS
Compare requirements vs implementation:
- Features fully implemented
- Features partially implemented
- Features not started
- Critical gaps

## ARCHITECTURE & CODE QUALITY
Based on the code samples:
- Architecture consistency
- Code quality observations
- Technical debt indicators
- Design pattern usage

## RECOMMENDATIONS
Prioritized by impact:
1. Critical fixes (blocking issues)
2. High priority (needed for MVP)
3. Medium priority (quality improvements)
4. Low priority (nice to have)

## NEXT ITERATION PLAN
What should the team focus on next?
- Top 5 priorities
- Estimated effort for each
- Dependencies between items

Be honest and specific. Reference file paths and line numbers where relevant.
"""

        response = await self.reviewer_agent.send_message(prompt)

        return {
            "ai_assessment": response,
            "analysis_timestamp": datetime.now().isoformat()
        }

    def _build_analysis_context(
        self,
        project_path: Path,
        metrics: Dict[str, Any],
        requirements: Optional[str],
        implementation_samples: Dict[str, str]
    ) -> str:
        """Build context string for AI analysis"""
        context_parts = []

        # Project info
        context_parts.append(f"PROJECT: {project_path.name}")
        context_parts.append(f"PATH: {project_path}")
        context_parts.append("")

        # Metrics summary
        context_parts.append("QUANTITATIVE METRICS:")
        context_parts.append(json.dumps(metrics, indent=2))
        context_parts.append("")

        # Requirements (first 5000 chars)
        if requirements:
            context_parts.append("REQUIREMENTS DOCUMENT (excerpt):")
            context_parts.append(requirements[:5000])
            if len(requirements) > 5000:
                context_parts.append("... (truncated)")
            context_parts.append("")

        # Implementation samples
        if implementation_samples:
            context_parts.append("IMPLEMENTATION SAMPLES:")
            for name, content in implementation_samples.items():
                context_parts.append(f"\n--- {name} ---")
                context_parts.append(content[:1000])  # First 1000 chars
                if len(content) > 1000:
                    context_parts.append("... (truncated)")

        return "\n".join(context_parts)

    async def _generate_reports(
        self,
        project_path: Path,
        metrics: Dict[str, Any],
        analysis: Dict[str, Any],
        output_dir: Path
    ) -> Dict[str, Path]:
        """Generate comprehensive review reports"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Maturity Report
        maturity_report = output_dir / f"PROJECT_MATURITY_REPORT_{timestamp}.md"
        self._write_maturity_report(maturity_report, project_path, metrics, analysis)

        # 2. Gap Analysis
        gap_analysis = output_dir / f"GAP_ANALYSIS_{timestamp}.md"
        self._write_gap_analysis(gap_analysis, analysis)

        # 3. Remediation Plan
        remediation_plan = output_dir / f"REMEDIATION_PLAN_{timestamp}.md"
        self._write_remediation_plan(remediation_plan, analysis)

        # 4. Metrics JSON
        metrics_json = output_dir / f"METRICS_{timestamp}.json"
        with open(metrics_json, 'w') as f:
            json.dump({
                "metrics": metrics,
                "analysis_summary": {
                    "timestamp": analysis["analysis_timestamp"],
                    "completion": metrics["completion_percentage"],
                    "maturity_level": metrics["maturity_level"]
                }
            }, f, indent=2)

        # 5. Create latest symlinks
        for report_type, report_path in [
            ("maturity", maturity_report),
            ("gap", gap_analysis),
            ("remediation", remediation_plan),
            ("metrics", metrics_json)
        ]:
            latest_link = output_dir / f"LATEST_{report_type.upper()}.md"
            if latest_link.suffix == '.md' and report_path.suffix == '.json':
                latest_link = output_dir / f"LATEST_{report_type.upper()}.json"

            if latest_link.exists():
                latest_link.unlink()
            try:
                latest_link.symlink_to(report_path.name)
            except OSError:
                # Windows doesn't support symlinks easily, just copy
                import shutil
                shutil.copy(report_path, latest_link)

        return {
            "maturity_report": maturity_report.name,
            "gap_analysis": gap_analysis.name,
            "remediation_plan": remediation_plan.name,
            "metrics_json": metrics_json.name
        }

    def _write_maturity_report(
        self,
        output_path: Path,
        project_path: Path,
        metrics: Dict[str, Any],
        analysis: Dict[str, Any]
    ):
        """Write maturity assessment report"""
        content = f"""# Project Maturity Report

**Project:** {project_path.name}
**Review Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Overall Completion:** {metrics['completion_percentage']}%
**Maturity Level:** {metrics['maturity_level']}

---

## Executive Summary

This report provides a comprehensive assessment of project maturity based on quantitative metrics and qualitative code analysis.

### Quick Stats
- **Total Files:** {metrics['metrics']['total_files']}
- **Code Files:** {sum(metrics['metrics']['code_files'].values())}
- **Test Files:** {metrics['metrics']['test_files']}
- **Documentation Files:** {metrics['metrics']['doc_files']}
- **Lines of Code:** {metrics['metrics']['code_lines']:,}

### Component Status
| Component | Status | Notes |
|-----------|--------|-------|
| Documentation | {self._get_status_emoji(metrics['documentation'])} | {metrics['documentation']['total_md_files']} markdown files |
| Implementation | {self._get_implementation_status(metrics['implementation'])} | {metrics['implementation']['api_endpoints_implemented']} endpoints implemented |
| Testing | {self._get_testing_status(metrics['testing'])} | {metrics['testing']['total_test_files']} test files |
| DevOps | {self._get_devops_status(metrics['devops'])} | CI/CD: {metrics['devops']['has_ci_cd']} |

---

## AI Agent Assessment

{analysis['ai_assessment']}

---

## Detailed Metrics

### File Distribution
```
{json.dumps(metrics['metrics']['code_files'], indent=2)}
```

### Implementation Details
- **API Endpoints:** {metrics['implementation']['api_endpoints_implemented']} implemented, {metrics['implementation']['api_endpoints_stubbed']} stubbed
- **UI Components:** {metrics['implementation']['ui_components']}
- **UI Pages:** {metrics['implementation']['ui_pages_complete']} complete, {metrics['implementation']['ui_pages_stubbed']} stubbed
- **Database Migrations:** {metrics['implementation']['database_migrations']}

### Testing Breakdown
- **Unit Tests:** {metrics['testing']['unit_tests']}
- **Integration Tests:** {metrics['testing']['integration_tests']}
- **E2E Tests:** {metrics['testing']['e2e_tests']}
- **Coverage Available:** {metrics['testing']['coverage_available']}

### DevOps Setup
- **Docker:** {'✓' if metrics['devops']['has_docker'] else '✗'}
- **Docker Compose:** {'✓' if metrics['devops']['has_docker_compose'] else '✗'}
- **Kubernetes:** {'✓' if metrics['devops']['has_kubernetes'] else '✗'}
- **Terraform:** {'✓' if metrics['devops']['has_terraform'] else '✗'}
- **CI/CD Pipelines:** {len(metrics['devops']['ci_cd_pipelines'])}

---

*Generated by Project Review Engine - Hybrid AI Agent + Analytical Tools*
"""
        output_path.write_text(content)

    def _write_gap_analysis(self, output_path: Path, analysis: Dict[str, Any]):
        """Write gap analysis report"""
        content = f"""# Gap Analysis Report

**Review Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Purpose
This report identifies gaps between project requirements and current implementation, extracted from AI agent analysis.

## Analysis

{analysis['ai_assessment']}

---

*Note: This is an AI-generated analysis. Review with technical leads for validation.*
"""
        output_path.write_text(content)

    def _write_remediation_plan(self, output_path: Path, analysis: Dict[str, Any]):
        """Write remediation plan"""
        content = f"""# Remediation Plan - Next Iteration Priorities

**Review Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Purpose
Actionable plan for addressing gaps and moving to next maturity level.

## Recommendations & Action Items

{analysis['ai_assessment']}

---

## Implementation Notes

1. **Prioritize by Impact:** Focus on critical and high-priority items first
2. **Track Progress:** Use these items as basis for next sprint planning
3. **Re-review:** Run project review again after completing each major section
4. **Iterate:** This is a living document - update as priorities change

---

*Generated by Project Review Engine*
"""
        output_path.write_text(content)

    def _get_status_emoji(self, component_metrics: Dict[str, Any]) -> str:
        """Get status emoji based on component metrics"""
        # Simple heuristic
        if isinstance(component_metrics, dict):
            true_count = sum(1 for v in component_metrics.values() if v is True or (isinstance(v, int) and v > 0))
            total = len(component_metrics)
            ratio = true_count / total if total > 0 else 0
            if ratio >= 0.8:
                return "🟢 Excellent"
            elif ratio >= 0.5:
                return "🟡 Good"
            else:
                return "🔴 Needs Work"
        return "⚪ Unknown"

    def _get_implementation_status(self, impl: Dict[str, Any]) -> str:
        """Get implementation status"""
        impl_count = impl['api_endpoints_implemented']
        stub_count = impl['api_endpoints_stubbed']
        total = impl_count + stub_count
        if total == 0:
            return "🔴 Not Started"
        ratio = impl_count / total
        if ratio >= 0.8:
            return "🟢 Mostly Complete"
        elif ratio >= 0.5:
            return "🟡 In Progress"
        else:
            return "🟠 Early Stage"

    def _get_testing_status(self, testing: Dict[str, Any]) -> str:
        """Get testing status"""
        if testing['total_test_files'] == 0:
            return "🔴 No Tests"
        elif testing['total_test_files'] < 5:
            return "🟠 Minimal"
        elif testing['total_test_files'] < 20:
            return "🟡 Basic"
        else:
            return "🟢 Good"

    def _get_devops_status(self, devops: Dict[str, Any]) -> str:
        """Get DevOps status"""
        score = sum([
            devops['has_docker'],
            devops['has_docker_compose'],
            devops['has_kubernetes'],
            devops['has_terraform'],
            devops['has_ci_cd']
        ])
        if score >= 4:
            return "🟢 Excellent"
        elif score >= 2:
            return "🟡 Good"
        else:
            return "🔴 Basic"

    def _determine_maturity_level(self, completion: float) -> str:
        """Determine maturity level from completion percentage"""
        if completion >= 96:
            return "Production Ready"
        elif completion >= 81:
            return "Pre-Production"
        elif completion >= 61:
            return "Late Development"
        elif completion >= 41:
            return "Mid Development"
        elif completion >= 21:
            return "Early Development"
        else:
            return "Concept/Planning"


# CLI Interface
async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Project Review Engine - Hybrid AI Agent + Analytical Tools"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Path to project directory"
    )
    parser.add_argument(
        "--requirements",
        help="Path to requirements document (relative to project)"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for reports (default: project/reviews)"
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )

    args = parser.parse_args()

    # Create engine
    engine = ProjectReviewEngine(api_key=args.api_key)

    # Run review
    try:
        results = await engine.review_project(
            project_path=args.project,
            requirement_doc=args.requirements,
            output_dir=args.output_dir
        )

        print(f"\n✓ Review complete!")
        print(f"  Completion: {results['completion_percentage']}%")
        print(f"  Reports: {results['reports']}")

    except Exception as e:
        logger.error(f"Review failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
