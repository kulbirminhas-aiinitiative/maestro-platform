# ACC Coupling & Complexity Metrics - Quick Reference Guide

## Quick Start

### Run All Tests
```bash
pytest tests/acc/integration/test_coupling_complexity.py -v -m "acc and integration"
```

### Run Demo
```bash
python demo_coupling_complexity_metrics.py acc
```

### View Results
```bash
cat acc/metrics_report.json | jq '.summary'
open acc/metrics_dashboard.html
```

---

## Test IDs Reference

### Cyclomatic Complexity (ACC-301 to ACC-306)
- **ACC-301**: Calculate McCabe complexity
- **ACC-302**: Complexity thresholds (Low/Medium/High)
- **ACC-303**: Detect complex functions
- **ACC-304**: Module-level aggregation
- **ACC-305**: Complexity trends
- **ACC-306**: Performance (1000 functions < 2s)

### Coupling Metrics (ACC-307 to ACC-312)
- **ACC-307**: Afferent coupling (Ca)
- **ACC-308**: Efferent coupling (Ce)
- **ACC-309**: Instability (I)
- **ACC-310**: Module-level coupling
- **ACC-311**: Package-level coupling
- **ACC-312**: High coupling detection

### Cohesion Metrics (ACC-313 to ACC-318)
- **ACC-313**: LCOM calculation
- **ACC-314**: Class responsibility
- **ACC-315**: SRP violations
- **ACC-316**: God class detection
- **ACC-317**: Cohesion score
- **ACC-318**: Refactoring suggestions

### Hotspot Detection (ACC-319 to ACC-324)
- **ACC-319**: Complexity + coupling
- **ACC-320**: Hotspot formula
- **ACC-321**: Rank by risk
- **ACC-322**: Prioritize refactoring
- **ACC-323**: Hotspot trends
- **ACC-324**: Visualization data

### Integration (ACC-325 to ACC-330)
- **ACC-325**: ImportGraphBuilder integration
- **ACC-326**: RuleEngine integration
- **ACC-327**: JSON export
- **ACC-328**: HTML export
- **ACC-329**: Performance (1000 files < 5s)
- **ACC-330**: Incremental metrics

---

## Formulas

### Cyclomatic Complexity
```
complexity = decision_points + 1
where decision_points = if + for + while + and + or + except + with + comprehensions
```

### Coupling Metrics
```
Ca = len(incoming_imports)  # Afferent coupling
Ce = len(outgoing_imports)  # Efferent coupling
I = Ce / (Ca + Ce)          # Instability (0=stable, 1=unstable)
```

### Cohesion (LCOM)
```
P = pairs of methods that don't share instance variables
Q = pairs of methods that share instance variables
LCOM = (P - Q) / max(P, Q) if P > Q else 0.0
Cohesion Score = 1.0 - LCOM
```

### Hotspot Risk Score
```
risk_score = complexity * (Ce + 1) / (Ca + 1)
```

---

## Thresholds

### Complexity
- **Low**: < 10 (simple, maintainable)
- **Medium**: 10-20 (moderate, review)
- **High**: > 20 (complex, refactor)

### Instability
- **0.0**: Stable (depended upon by many)
- **0.5**: Balanced
- **1.0**: Unstable (depends on many)

### Cohesion Score
- **0.0-0.3**: Low (needs refactoring)
- **0.3-0.7**: Medium (acceptable)
- **0.7-1.0**: High (well-designed)

### God Class
- **Methods**: > 20
- **Lines of Code**: > 500

### Hotspot Risk
- **< 10**: Low priority
- **10-50**: Medium priority
- **> 50**: High priority (refactor now)

---

## Helper Classes

### ComplexityAnalyzer
```python
analyzer = ComplexityAnalyzer()
metrics = analyzer.analyze_file(path)
high_complexity = analyzer.get_high_complexity_functions(threshold=10)
```

### CouplingCalculator
```python
calculator = CouplingCalculator(import_graph)
metrics = calculator.calculate_module_coupling(module_name)
highly_coupled = calculator.get_highly_coupled_modules(threshold=10)
```

### CohesionAnalyzer
```python
analyzer = CohesionAnalyzer()
metrics = analyzer.analyze_file(path)
god_classes = analyzer.detect_god_classes()
srp_violations = analyzer.detect_srp_violations(lcom_threshold=0.8)
```

### HotspotDetector
```python
detector = HotspotDetector(complexity_analyzer, coupling_calculator)
hotspots = detector.get_top_hotspots(n=10)
trends = detector.detect_trends(historical_hotspots)
viz_data = detector.generate_visualization_data()
```

### MetricsDashboard
```python
dashboard = MetricsDashboard(
    complexity_analyzer,
    coupling_calculator,
    cohesion_analyzer,
    hotspot_detector
)
metrics = dashboard.export_json(Path("metrics.json"))
html = dashboard.export_html(Path("dashboard.html"))
```

---

## Common Commands

### Test Specific Category
```bash
# Complexity tests only
pytest tests/acc/integration/test_coupling_complexity.py -v -k "complexity"

# Coupling tests only
pytest tests/acc/integration/test_coupling_complexity.py -v -k "coupling"

# Hotspot tests only
pytest tests/acc/integration/test_coupling_complexity.py -v -k "hotspot"
```

### Performance Testing
```bash
# Show execution times
pytest tests/acc/integration/test_coupling_complexity.py -v --durations=10

# Run performance tests only
pytest tests/acc/integration/test_coupling_complexity.py -v -k "performance"
```

### Analyze Different Projects
```bash
# Analyze current project
python demo_coupling_complexity_metrics.py .

# Analyze specific module
python demo_coupling_complexity_metrics.py acc

# Analyze any directory
python demo_coupling_complexity_metrics.py /path/to/project
```

---

## Output Files

### metrics_report.json
- Summary statistics
- Complexity breakdown
- Coupling metrics
- Cohesion analysis
- Top hotspots

### metrics_dashboard.html
- Visual dashboard
- Top 10 hotspots table
- Color-coded severity
- Summary statistics

---

## Interpretation

### Health Score
```
score = 100 - (high_complexity_ratio * 100)

90-100: Excellent ✅
70-89:  Good ⚠️
0-69:   Needs work 🚨
```

### Refactoring Priority
1. **Hotspots with risk > 50**: Immediate action
2. **God classes**: Split responsibilities
3. **High complexity (> 20)**: Simplify logic
4. **High coupling (Ce > 10)**: Reduce dependencies
5. **Low cohesion (< 0.3)**: Improve class design

---

## Troubleshooting

### Tests Fail
```bash
# Run with verbose output
pytest tests/acc/integration/test_coupling_complexity.py -vv --tb=long

# Run single test
pytest tests/acc/integration/test_coupling_complexity.py::test_acc_301_calculate_mccabe_complexity -v
```

### Demo Script Issues
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Install dependencies
pip install pytest networkx

# Run with debug output
python -u demo_coupling_complexity_metrics.py acc 2>&1 | tee debug.log
```

### Empty Results
- Check that directory contains Python files
- Verify exclusions list (should not filter your files)
- Ensure files have valid Python syntax

---

## Integration Examples

### CI/CD Pipeline (GitHub Actions)
```yaml
- name: Run Coupling & Complexity Analysis
  run: |
    python demo_coupling_complexity_metrics.py .
    cat metrics_report.json | jq '.summary.high_complexity_functions' > complexity_count.txt
    if [ $(cat complexity_count.txt) -gt 10 ]; then
      echo "Too many high complexity functions"
      exit 1
    fi
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

python demo_coupling_complexity_metrics.py . > /dev/null 2>&1
HEALTH_SCORE=$(cat metrics_report.json | jq '.summary.health_score // 100')

if [ "$HEALTH_SCORE" -lt 70 ]; then
  echo "Code health score too low: $HEALTH_SCORE"
  exit 1
fi
```

### Python Script Integration
```python
import subprocess
import json

# Run analysis
result = subprocess.run(
    ["python", "demo_coupling_complexity_metrics.py", "src"],
    capture_output=True
)

# Load results
with open("src/metrics_report.json") as f:
    metrics = json.load(f)

# Check thresholds
if metrics["summary"]["high_complexity_functions"] > 10:
    raise ValueError("Too many complex functions")

if metrics["summary"]["god_classes"] > 0:
    raise ValueError("God classes detected")
```

---

## Files Reference

### Test Files
- `tests/acc/integration/test_coupling_complexity.py` (1,800+ lines)

### Documentation
- `ACC_COUPLING_COMPLEXITY_SUMMARY.md` (comprehensive guide)
- `ACC_COUPLING_COMPLEXITY_TEST_RESULTS.md` (test results)
- `ACC_COUPLING_COMPLEXITY_QUICK_REFERENCE.md` (this file)

### Scripts
- `demo_coupling_complexity_metrics.py` (demo script)

### Output
- `acc/metrics_report.json` (JSON metrics)
- `acc/metrics_dashboard.html` (HTML dashboard)

---

## Performance Targets

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| 1000 functions | < 2s | 0.08s | ✅ 25x faster |
| 1000 files | < 5s | 0.38s | ✅ 13x faster |
| Full suite | < 3s | 1.27s | ✅ 2.4x faster |

---

## Support

### Running Tests
```bash
pytest tests/acc/integration/test_coupling_complexity.py -v -m "acc and integration"
```

### Getting Help
```bash
pytest tests/acc/integration/test_coupling_complexity.py --help
python demo_coupling_complexity_metrics.py --help
```

---

**Last Updated**: 2025-10-13
**Version**: 1.0.0
**Status**: Production Ready ✅
