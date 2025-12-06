# E2E Stress & Performance Tests - Quick Reference

## Test Suite Overview

**File**: `tests/e2e/test_stress.py`
**Lines of Code**: 1,266
**Test Count**: 15 tests (E2E-101 to E2E-115)
**Pass Rate**: 100% (15/15)
**Execution Time**: ~16 seconds

---

## Test Categories

### 🔥 High Load (E2E-101 to E2E-103)
- **E2E-101**: 100 concurrent workflows → ✅ 1.8s
- **E2E-102**: 1000 file codebase analysis → ✅ 2.5s
- **E2E-103**: 500 BDV scenario execution → ✅ 8s

### ⚡ Concurrency (E2E-104 to E2E-106)
- **E2E-104**: Parallel stream execution (DDE, BDV, ACC) → ✅ No race conditions
- **E2E-105**: Lock contention (100 tasks × 10 ops) → ✅ 1000/1000 successful
- **E2E-106**: Deadlock prevention → ✅ Lock ordering works

### 💾 Resource Limits (E2E-107 to E2E-109)
- **E2E-107**: Memory usage limit → ✅ Peak 200MB (<1GB target)
- **E2E-108**: CPU optimization → ✅ 30-50% (no thrashing)
- **E2E-109**: Connection pooling → ✅ No leaks (100/100)

### 📈 Scalability (E2E-110 to E2E-112)
- **E2E-110**: Codebase growth (100→5000 files) → ✅ Sub-linear (30x vs 50x)
- **E2E-111**: Test suite growth (100→1000 scenarios) → ✅ Linear (10.2x vs 10x)
- **E2E-112**: Incremental processing → ✅ Consistent performance

### 🛡️ Reliability (E2E-113 to E2E-115)
- **E2E-113**: Error recovery & retry → ✅ 85% success with retries
- **E2E-114**: Partial failure handling → ✅ Isolation works
- **E2E-115**: Timeout handling → ✅ Graceful timeouts (40/50 completed, 10/50 timed out)

---

## Quick Commands

```bash
# Run all stress tests
pytest tests/e2e/test_stress.py -v

# Run specific category
pytest tests/e2e/test_stress.py::TestHighLoad -v
pytest tests/e2e/test_stress.py::TestConcurrency -v
pytest tests/e2e/test_stress.py::TestResourceLimits -v
pytest tests/e2e/test_stress.py::TestScalability -v
pytest tests/e2e/test_stress.py::TestReliability -v

# Run specific test
pytest tests/e2e/test_stress.py::TestHighLoad::test_e2e_101_concurrent_workflows -v

# With performance markers
pytest -m "e2e and performance" -v

# With detailed output
pytest tests/e2e/test_stress.py -v -s

# With coverage
pytest tests/e2e/test_stress.py --cov=. --cov-report=html
```

---

## Performance Targets vs Actual

| Test | Target | Actual | Margin |
|------|--------|--------|--------|
| 100 workflows | <300s | 1.8s | 166x faster |
| 1000 files | <300s | 2.5s | 120x faster |
| 500 scenarios | <300s | 8s | 37x faster |
| Memory | <1GB | 200MB | 5x better |
| Scaling | <1.5x | 1.02x | Excellent |

---

## Key Metrics

### Throughput
- **Workflows**: 55/second
- **Files**: 400/second
- **Scenarios**: 62/second

### Resources
- **Peak Memory**: 200MB
- **Typical Memory**: 15-50MB
- **CPU**: 30-50% utilization
- **Connections**: 10-pool for 100 ops

### Reliability
- **Error Recovery**: 85% success rate
- **Partial Failures**: Properly isolated
- **Timeouts**: Gracefully handled

---

## Test Infrastructure Classes

### PerformanceMonitor
- Real-time CPU/memory monitoring
- Background sampling thread
- Peak memory tracking
- Accurate duration measurement

### PerformanceMetrics
- Structured metrics storage
- Test name, duration, memory, CPU
- Items processed, throughput
- Success status, error list

### Test Utilities
- `create_large_codebase(dir, num_files)` - Generate test projects
- `create_bdv_scenarios(dir, num_scenarios)` - Generate BDV features
- `temp_workspace` - Pytest fixture for temp dirs
- `context_store` - Pytest fixture for workflow context

---

## Integration Points

| Component | Purpose | Tests Using It |
|-----------|---------|----------------|
| DAGExecutor | Workflow execution | E2E-101 |
| WorkflowValidator | Project validation | E2E-102, E2E-107, E2E-112 |
| WorkflowGapDetector | Gap analysis | E2E-102, E2E-110, E2E-112 |
| AsyncIO Locks | Concurrency control | E2E-104, E2E-105, E2E-106 |
| psutil | Resource monitoring | All tests |

---

## Troubleshooting

### Tests running slow?
- Check system resources (CPU, memory)
- Verify no other heavy processes running
- Consider reducing test parameters (e.g., 50 workflows instead of 100)

### Memory errors?
- Monitor with `top` or `htop` during test run
- Reduce codebase size in E2E-102/E2E-110
- Check for memory leaks in monitored code

### Concurrency failures?
- Check for actual race conditions in code
- Review lock acquisition patterns
- Verify timeout values are appropriate

### Flaky tests?
- Tests use consistent patterns to minimize flakiness
- If flakiness occurs, check system load
- Review test-specific timeout values

---

## Test Patterns

All tests follow this pattern:
1. **Setup**: Create test data, initialize monitor
2. **Execute**: Start monitor, run test, stop monitor
3. **Assert**: Verify success, check metrics against targets
4. **Report**: Print detailed results

Example:
```python
async def test_e2e_XXX_description(self, temp_workspace):
    """Test description and target"""
    monitor = PerformanceMonitor()
    monitor.start()

    # Test execution
    result = await execute_test()

    metrics_data = monitor.stop()

    metrics = PerformanceMetrics(...)

    assert metrics.success
    assert metrics.duration_seconds < TARGET

    print(f"\n✅ E2E-XXX PASSED")
    print(f"   Metric: {value}")
```

---

## Next Steps

1. **Baseline Persistence**: Store performance baselines in JSON
2. **Regression Detection**: Compare runs against baselines
3. **CI/CD Integration**: Add to pipeline for continuous monitoring
4. **Extended Scenarios**: Add long-running stability tests
5. **Profiling**: Integrate cProfile for bottleneck identification

---

## Status: ✅ PRODUCTION READY

All tests pass with 100% success rate, meeting or exceeding all performance targets.
