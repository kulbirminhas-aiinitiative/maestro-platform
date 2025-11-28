#!/usr/bin/env python3
"""
Demo script for ACC Coupling & Complexity Metrics

Demonstrates usage of ComplexityAnalyzer, CouplingCalculator,
CohesionAnalyzer, HotspotDetector, and MetricsDashboard.

Usage:
    python demo_coupling_complexity_metrics.py [path_to_analyze]
"""

import sys
import json
from pathlib import Path

# Import helper classes from test suite
# Note: In production, these would be moved to acc/ module
sys.path.insert(0, str(Path(__file__).parent / "tests" / "acc" / "integration"))

from test_coupling_complexity import (
    ComplexityAnalyzer,
    CouplingCalculator,
    CohesionAnalyzer,
    HotspotDetector,
    MetricsDashboard,
    create_test_builder
)


def analyze_project(project_path: Path):
    """
    Analyze a Python project for complexity, coupling, cohesion, and hotspots.

    Args:
        project_path: Path to project directory
    """
    print(f"🔍 Analyzing project: {project_path}")
    print("=" * 80)

    # 1. Build import graph
    print("\n1️⃣  Building import dependency graph...")
    builder = create_test_builder(project_path)
    graph = builder.build_graph()
    print(f"   ✓ Found {len(graph.modules)} modules")
    print(f"   ✓ Found {len(graph.graph.edges())} dependencies")

    # 2. Analyze complexity
    print("\n2️⃣  Analyzing cyclomatic complexity...")
    complexity_analyzer = ComplexityAnalyzer()
    complexity_analyzer.analyze_directory(project_path)
    print(f"   ✓ Analyzed {len(complexity_analyzer.results)} functions")

    # Show complexity distribution
    low = len([m for m in complexity_analyzer.results if m.cyclomatic_complexity < 10])
    medium = len([m for m in complexity_analyzer.results if 10 <= m.cyclomatic_complexity <= 20])
    high = len([m for m in complexity_analyzer.results if m.cyclomatic_complexity > 20])
    print(f"   ✓ Low complexity: {low}, Medium: {medium}, High: {high}")

    # Show top 5 most complex functions
    top_complex = sorted(
        complexity_analyzer.results,
        key=lambda x: x.cyclomatic_complexity,
        reverse=True
    )[:5]

    if top_complex:
        print("\n   📊 Top 5 most complex functions:")
        for i, func in enumerate(top_complex, 1):
            print(f"      {i}. {func.name}: complexity={func.cyclomatic_complexity}, "
                  f"loc={func.lines_of_code}")

    # 3. Calculate coupling
    print("\n3️⃣  Calculating coupling metrics...")
    coupling_calculator = CouplingCalculator(graph)
    all_coupling = coupling_calculator.calculate_all_coupling()
    print(f"   ✓ Calculated coupling for {len(all_coupling)} modules")

    # Show top 5 most coupled modules
    top_coupled = sorted(all_coupling, key=lambda x: x.efferent_coupling, reverse=True)[:5]

    if top_coupled:
        print("\n   📊 Top 5 most coupled modules:")
        for i, module in enumerate(top_coupled, 1):
            print(f"      {i}. {module.module_name}: "
                  f"Ca={module.afferent_coupling}, Ce={module.efferent_coupling}, "
                  f"I={module.instability:.2f}")

    # 4. Analyze cohesion
    print("\n4️⃣  Analyzing class cohesion...")
    cohesion_analyzer = CohesionAnalyzer()
    cohesion_analyzer.analyze_directory(project_path)
    print(f"   ✓ Analyzed {len(cohesion_analyzer.results)} classes")

    # Detect God classes
    god_classes = cohesion_analyzer.detect_god_classes()
    if god_classes:
        print(f"\n   ⚠️  Found {len(god_classes)} God classes:")
        for gc in god_classes:
            print(f"      - {gc.class_name}: {gc.method_count} methods, "
                  f"{gc.lines_of_code} lines")
    else:
        print("   ✓ No God classes detected")

    # Show low cohesion classes
    low_cohesion = [m for m in cohesion_analyzer.results if m.lcom > 0.7]
    if low_cohesion:
        print(f"\n   ⚠️  Found {len(low_cohesion)} classes with low cohesion:")
        for lc in low_cohesion[:5]:
            print(f"      - {lc.class_name}: LCOM={lc.lcom:.2f}, "
                  f"cohesion_score={lc.cohesion_score:.2f}")

    # 5. Detect hotspots
    print("\n5️⃣  Detecting code hotspots...")
    hotspot_detector = HotspotDetector(complexity_analyzer, coupling_calculator)
    top_hotspots = hotspot_detector.get_top_hotspots(n=10)
    print(f"   ✓ Identified top 10 hotspots")

    if top_hotspots:
        print("\n   🔥 Top 10 refactoring priorities (by risk score):")
        for i, hotspot in enumerate(top_hotspots, 1):
            print(f"      {i}. {hotspot.module_name}")
            print(f"         Risk Score: {hotspot.risk_score:.2f}")
            print(f"         Complexity: {hotspot.complexity}, "
                  f"Coupling: Ce={hotspot.efferent_coupling}, Ca={hotspot.afferent_coupling}")

    # 6. Generate dashboard
    print("\n6️⃣  Generating metrics dashboard...")
    dashboard = MetricsDashboard(
        complexity_analyzer,
        coupling_calculator,
        cohesion_analyzer,
        hotspot_detector
    )

    # Export to JSON
    json_output = project_path / "metrics_report.json"
    metrics = dashboard.export_json(json_output)
    print(f"   ✓ JSON report: {json_output}")

    # Export to HTML
    html_output = project_path / "metrics_dashboard.html"
    dashboard.export_html(html_output)
    print(f"   ✓ HTML dashboard: {html_output}")

    # 7. Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    print(f"Total Functions: {metrics['summary']['total_functions']}")
    print(f"Total Classes: {metrics['summary']['total_classes']}")
    print(f"Total Modules: {metrics['summary']['total_modules']}")
    print(f"High Complexity Functions: {metrics['summary']['high_complexity_functions']}")
    print(f"God Classes: {metrics['summary']['god_classes']}")
    print(f"Top Hotspots: {metrics['summary']['top_hotspots']}")

    # Calculate overall health score
    total_functions = metrics['summary']['total_functions']
    high_complexity = metrics['summary']['high_complexity_functions']

    if total_functions > 0:
        complexity_ratio = high_complexity / total_functions
        health_score = max(0, 100 - (complexity_ratio * 100))

        print(f"\n🏥 Code Health Score: {health_score:.1f}/100")

        if health_score >= 80:
            print("   ✅ Excellent! Code is maintainable and well-structured.")
        elif health_score >= 60:
            print("   ⚠️  Good, but some refactoring opportunities exist.")
        else:
            print("   🚨 Needs attention. Prioritize refactoring hotspots.")

    print("\n✨ Analysis complete!")
    print(f"📂 Reports saved to: {project_path.absolute()}")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        # Default to acc module
        project_path = Path(__file__).parent / "acc"

    if not project_path.exists():
        print(f"❌ Error: Path does not exist: {project_path}")
        sys.exit(1)

    if not project_path.is_dir():
        print(f"❌ Error: Path is not a directory: {project_path}")
        sys.exit(1)

    try:
        analyze_project(project_path)
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
