#!/usr/bin/env python3
"""
Traceability Integration - Week 7-8 Requirements Traceability

Complete traceability system that integrates with contract validation.
Provides simple API for checking PRD coverage and generating reports.

Key Features:
- Full traceability analysis (PRD extraction, code analysis, mapping)
- Markdown and JSON report generation
- Integration with contract PRD_TRACEABILITY requirement
- Simple API for validation system

FUTURE ENHANCEMENT: Personas should generate feature metadata during PRD creation
as structured data (JSON/YAML) alongside the markdown document. This would be
more reliable than parsing markdown after the fact.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from code_feature_analyzer import analyze_code_features, CodeFeature
from prd_feature_extractor import extract_prd_features, PRDFeature
from feature_mapper import map_prd_to_code, TraceabilityMatrix, MappingStatus

logger = logging.getLogger(__name__)


class TraceabilityAnalyzer:
    """Complete traceability analysis system"""

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = workflow_dir
        self.impl_dir = workflow_dir / "implementation"
        self.requirements_dir = workflow_dir / "requirements"

    async def analyze(self) -> Tuple[TraceabilityMatrix, Dict[str, Any]]:
        """Run complete traceability analysis"""
        logger.info(f"📊 Running traceability analysis for {self.workflow_dir.name}")

        # Step 1: Extract PRD features
        prd_features = await extract_prd_features(self.requirements_dir)

        # Step 2: Analyze code features
        code_features = await analyze_code_features(self.impl_dir)

        # Step 3: Map features
        matrix = await map_prd_to_code(prd_features, code_features)

        # Step 4: Calculate metrics
        metrics = self._calculate_metrics(matrix)

        logger.info(f"✅ Traceability analysis complete")
        logger.info(f"  Coverage: {metrics['prd_coverage']:.0%}")
        logger.info(f"  Code Features: {metrics['code_feature_count']}")

        return matrix, metrics

    def _calculate_metrics(self, matrix: TraceabilityMatrix) -> Dict[str, Any]:
        """Calculate traceability metrics"""
        return {
            "prd_coverage": matrix.coverage_percentage,
            "prd_feature_count": matrix.total_prd_features,
            "code_feature_count": matrix.total_code_features,
            "fully_implemented": sum(1 for m in matrix.mappings if m.status == MappingStatus.FULLY_IMPLEMENTED),
            "partially_implemented": sum(1 for m in matrix.mappings if m.status == MappingStatus.PARTIALLY_IMPLEMENTED),
            "not_implemented": len(matrix.unmapped_prd),
            "not_in_prd": len(matrix.unmapped_code),
            "average_completeness": sum(m.coverage for m in matrix.mappings) / len(matrix.mappings) if matrix.mappings else 0.0
        }


class TraceabilityReporter:
    """Generate traceability reports"""

    def generate_markdown_report(
        self,
        matrix: TraceabilityMatrix,
        metrics: Dict[str, Any],
        workflow_name: str
    ) -> str:
        """Generate markdown traceability report"""
        lines = []

        lines.append("# Requirements Traceability Report")
        lines.append("")
        lines.append(f"**Workflow**: {workflow_name}")
        lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        if matrix.total_prd_features > 0:
            lines.append(f"- **PRD Features**: {matrix.total_prd_features}")
            lines.append(f"- **Implemented Features**: {matrix.total_code_features}")
            lines.append(f"- **Coverage**: {metrics['prd_coverage']:.0%}")
            lines.append(f"- **Fully Implemented**: {metrics['fully_implemented']}")
            lines.append(f"- **Partially Implemented**: {metrics['partially_implemented']}")
            lines.append(f"- **Not Implemented**: {metrics['not_implemented']}")
            lines.append(f"- **Extra Features** (not in PRD): {metrics['not_in_prd']}")
        else:
            lines.append("⚠️  **No PRD documents found** - analyzing code only")
            lines.append("")
            lines.append(f"- **Code Features Identified**: {matrix.total_code_features}")
            lines.append(f"- **Average Completeness**: {metrics['average_completeness']:.0%}")
        lines.append("")

        # Feature Mappings
        if matrix.total_prd_features > 0:
            lines.append("## Feature Mapping")
            lines.append("")

            # Fully implemented
            fully_impl = [m for m in matrix.mappings if m.status == MappingStatus.FULLY_IMPLEMENTED]
            if fully_impl:
                lines.append("### ✅ Fully Implemented Features")
                lines.append("")
                for mapping in fully_impl:
                    lines.append(f"#### {mapping.prd_feature.title}")
                    lines.append(f"- **PRD**: {mapping.prd_feature.id}")
                    lines.append(f"- **Code**: {mapping.code_feature.name} ({mapping.code_feature.id})")
                    lines.append(f"- **Confidence**: {mapping.match_confidence:.0%}")
                    lines.append(f"- **Coverage**: {mapping.coverage:.0%}")
                    if mapping.code_feature.endpoints:
                        lines.append(f"- **Endpoints**: {len(mapping.code_feature.endpoints)}")
                    if mapping.code_feature.models:
                        model_names = [m.name for m in mapping.code_feature.models]
                        lines.append(f"- **Models**: {', '.join(model_names)}")
                    lines.append("")

            # Partially implemented
            partial_impl = [m for m in matrix.mappings if m.status == MappingStatus.PARTIALLY_IMPLEMENTED]
            if partial_impl:
                lines.append("### ⚠️  Partially Implemented Features")
                lines.append("")
                for mapping in partial_impl:
                    lines.append(f"#### {mapping.prd_feature.title}")
                    lines.append(f"- **Coverage**: {mapping.coverage:.0%}")
                    lines.append(f"- **Gaps**:")
                    for gap in mapping.gaps:
                        lines.append(f"  - {gap}")
                    lines.append("")

            # Not implemented
            if matrix.unmapped_prd:
                lines.append("### ❌ Not Implemented Features")
                lines.append("")
                for feature in matrix.unmapped_prd:
                    lines.append(f"- **{feature.title}** ({feature.id})")
                    if feature.priority:
                        lines.append(f"  - Priority: {feature.priority.value}")
                lines.append("")

            # Extra features
            if matrix.unmapped_code:
                lines.append("### ℹ️  Extra Features (Not in PRD)")
                lines.append("")
                for feature in matrix.unmapped_code:
                    lines.append(f"- **{feature.name}** ({feature.id})")
                    lines.append(f"  - Completeness: {feature.completeness:.0%}")
                    lines.append(f"  - Endpoints: {len(feature.endpoints)}")
                lines.append("")
        else:
            # No PRD - just list code features
            lines.append("## Identified Code Features")
            lines.append("")
            lines.append("_Note: No PRD available for comparison_")
            lines.append("")

            for mapping in matrix.mappings:
                if mapping.code_feature:
                    lines.append(f"### {mapping.code_feature.name}")
                    lines.append(f"- **ID**: {mapping.code_feature.id}")
                    lines.append(f"- **Category**: {mapping.code_feature.category.value}")
                    lines.append(f"- **Completeness**: {mapping.code_feature.completeness:.0%}")
                    lines.append(f"- **Confidence**: {mapping.code_feature.confidence:.0%}")
                    lines.append(f"- **Endpoints**: {len(mapping.code_feature.endpoints)}")
                    lines.append(f"- **Models**: {len(mapping.code_feature.models)}")
                    lines.append(f"- **Components**: {len(mapping.code_feature.components)}")
                    lines.append(f"- **Has Tests**: {'✅' if mapping.code_feature.has_tests else '❌'}")
                    lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        if matrix.total_prd_features > 0:
            if metrics['not_implemented'] > 0:
                lines.append(f"1. **Implement missing features** ({metrics['not_implemented']} features)")
            if metrics['partially_implemented'] > 0:
                lines.append(f"2. **Complete partial implementations** ({metrics['partially_implemented']} features)")
            if metrics['not_in_prd'] > 0:
                lines.append(f"3. **Review extra features** ({metrics['not_in_prd']} features not in PRD)")
        else:
            lines.append("1. **Create PRD with feature specifications** for better traceability")
            untested = sum(1 for m in matrix.mappings if m.code_feature and not m.code_feature.has_tests)
            if untested > 0:
                lines.append(f"2. **Add tests** for {untested} features")
        lines.append("")

        # Future Enhancement Note
        lines.append("---")
        lines.append("")
        lines.append("_Note: Future enhancement - Generate structured feature metadata (JSON/YAML)_")
        lines.append("_alongside PRD documents during creation for more reliable traceability._")
        lines.append("")

        return "\n".join(lines)


async def validate_prd_traceability(
    workflow_dir: Path,
    min_coverage: float = 0.80
) -> Tuple[bool, float, List[str]]:
    """
    Validate PRD traceability for contract system.

    Args:
        workflow_dir: Workflow directory path
        min_coverage: Minimum required coverage (0.0-1.0)

    Returns:
        Tuple of (passed, coverage, violations)
    """
    analyzer = TraceabilityAnalyzer(workflow_dir)
    matrix, metrics = await analyzer.analyze()

    coverage = metrics['prd_coverage']
    passed = coverage >= min_coverage
    violations = []

    if not passed:
        if matrix.total_prd_features > 0:
            violations.append(f"PRD coverage below threshold: {coverage:.0%} < {min_coverage:.0%}")
            if metrics['not_implemented'] > 0:
                violations.append(f"{metrics['not_implemented']} PRD features not implemented")
            if metrics['partially_implemented'] > 0:
                violations.append(f"{metrics['partially_implemented']} features only partially implemented")
        # If no PRD, pass by default (100% coverage)

    return passed, coverage, violations


async def generate_full_report(workflow_dir: Path) -> Tuple[str, str]:
    """
    Generate complete traceability report (markdown + JSON).

    Returns:
        Tuple of (markdown_report, json_report_path)
    """
    analyzer = TraceabilityAnalyzer(workflow_dir)
    matrix, metrics = await analyzer.analyze()

    reporter = TraceabilityReporter()

    # Generate markdown report
    markdown = reporter.generate_markdown_report(matrix, metrics, workflow_dir.name)

    # Save reports
    md_file = workflow_dir / "TRACEABILITY_REPORT.md"
    json_file = workflow_dir / "TRACEABILITY_REPORT.json"

    md_file.write_text(markdown)

    json_data = {
        "workflow": workflow_dir.name,
        "generated_at": datetime.now().isoformat(),
        "metrics": metrics,
        "matrix": matrix.to_dict()
    }
    json_file.write_text(json.dumps(json_data, indent=2))

    logger.info(f"📄 Saved traceability reports:")
    logger.info(f"  Markdown: {md_file}")
    logger.info(f"  JSON: {json_file}")

    return markdown, str(json_file)


if __name__ == "__main__":
    # Test traceability integration
    import asyncio

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

    async def main():
        workflow_dir = Path("/tmp/maestro_workflow/wf-1760076571-6b932a66")

        print("=" * 80)
        print("TRACEABILITY INTEGRATION - TEST RUN")
        print("=" * 80)
        print(f"Workflow: {workflow_dir.name}\n")

        # Test 1: Full report generation
        print("Test 1: Generating complete traceability report...")
        markdown, json_path = await generate_full_report(workflow_dir)

        print(f"\n✅ Reports generated")
        print(f"  Markdown: {len(markdown)} characters")
        print(f"  JSON: {json_path}")

        # Test 2: Contract validation
        print("\nTest 2: Validating PRD traceability (contract requirement)...")
        passed, coverage, violations = await validate_prd_traceability(workflow_dir, min_coverage=0.80)

        print(f"\n📊 Validation Result:")
        print(f"  Coverage: {coverage:.0%}")
        print(f"  Required: 80%")
        print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")

        if violations:
            print(f"\n⚠️  Violations:")
            for violation in violations:
                print(f"  - {violation}")
        else:
            print(f"\n✅ No violations (no PRD to validate against)")

        # Show excerpt of markdown report
        print("\n" + "=" * 80)
        print("MARKDOWN REPORT EXCERPT")
        print("=" * 80)
        lines = markdown.split('\n')
        for line in lines[:30]:
            print(line)
        if len(lines) > 30:
            print(f"\n... ({len(lines) - 30} more lines)")

    asyncio.run(main())
