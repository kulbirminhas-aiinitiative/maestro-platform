# Team Execution V2 Split Mode - Test Report

**Generated**: 2025-10-09 12:26:58

## Test Summary

- **Total Tests**: 10
- **Passed**: 4 ✅
- **Failed**: 6 ❌
- **Total Duration**: 179.9s (3.0m)
- **Success Rate**: 40%

- **Wall Clock Time**: 175.9s (2.9m)

## Test Results

| Test ID | Test Name | Status | Duration | Error |
|---------|-----------|--------|----------|-------|
| TC1 | TC1: Single Phase Execution | ❌ FAIL | 22.0s | No module named 'networkx'... |
| TC2 | TC2: Sequential Phase Execution | ❌ FAIL | 30.8s | No module named 'networkx'... |
| TC3 | TC3: Full Batch Execution | ❌ FAIL | 35.9s | No module named 'networkx'... |
| TC4 | TC4: Resume from Checkpoint | ❌ FAIL | 31.8s | No module named 'networkx'... |
| TC5 | TC5: Phase Skipping (Direct Jump) | ❌ FAIL | 24.5s | No module named 'networkx'... |
| TC6 | TC6: Human Edits Between Phases | ❌ FAIL | 30.9s | No module named 'networkx'... |
| TC7 | TC7: Quality Gate Failure | ✅ PASS | 1.0s |  |
| TC8 | TC8: Contract Validation Failure | ✅ PASS | 1.0s |  |
| TC9 | TC9: Multiple Checkpoints | ✅ PASS | 1.0s |  |
| TC10 | TC10: Concurrent Execution | ✅ PASS | 1.0s |  |

## Detailed Results

### TC1: TC1: Single Phase Execution

- **Status**: ❌ FAILED
- **Duration**: 22.01s

**Error**:
```
No module named 'networkx'
```

### TC2: TC2: Sequential Phase Execution

- **Status**: ❌ FAILED
- **Duration**: 30.76s

**Error**:
```
No module named 'networkx'
```

### TC3: TC3: Full Batch Execution

- **Status**: ❌ FAILED
- **Duration**: 35.89s

**Error**:
```
No module named 'networkx'
```

### TC4: TC4: Resume from Checkpoint

- **Status**: ❌ FAILED
- **Duration**: 31.78s

**Error**:
```
No module named 'networkx'
```

### TC5: TC5: Phase Skipping (Direct Jump)

- **Status**: ❌ FAILED
- **Duration**: 24.54s

**Error**:
```
No module named 'networkx'
```

### TC6: TC6: Human Edits Between Phases

- **Status**: ❌ FAILED
- **Duration**: 30.90s

**Error**:
```
No module named 'networkx'
```

### TC7: TC7: Quality Gate Failure

- **Status**: ✅ PASSED
- **Duration**: 1.00s

### TC8: TC8: Contract Validation Failure

- **Status**: ✅ PASSED
- **Duration**: 1.00s

### TC9: TC9: Multiple Checkpoints

- **Status**: ✅ PASSED
- **Duration**: 1.00s

### TC10: TC10: Concurrent Execution

- **Status**: ✅ PASSED
- **Duration**: 1.00s

## Performance Analysis

- **Average Test Duration**: 18.0s
- **Max Test Duration**: 35.9s
- **Min Test Duration**: 1.0s

## Checkpoint Analysis

- **Total Checkpoints Created**: 0

## Context Flow Validation

## Test Requirements


================================================================================
TEST REQUIREMENTS SUMMARY
================================================================================

📋 MINIMAL_01: Single Health Check Endpoint
   Complexity: minimal
   Phases: 2 (requirements, implementation)
   Duration per phase: ~30s
   Personas per phase: 1
   Expected artifacts: 2
   Can skip: design, testing, deployment

📋 SIMPLE_01: Basic TODO API
   Complexity: simple
   Phases: 4 (requirements, design, implementation, testing)
   Duration per phase: ~45s
   Personas per phase: 2
   Expected artifacts: 6
   Can skip: deployment

📋 STANDARD_01: Full-Stack Task Management App
   Complexity: standard
   Phases: 5 (requirements, design, implementation, testing, deployment)
   Duration per phase: ~60s
   Personas per phase: 3
   Expected artifacts: 14

================================================================================

## Conclusion

❌ **6 test(s) failed.**

Please review the detailed results above for error messages.

**Report Generated**: 2025-10-09 12:26:58
