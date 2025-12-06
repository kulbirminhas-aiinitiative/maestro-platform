# Day 2 Implementation Plan
## Real Quality Analysis Implementation

**Date**: January 2025  
**Duration**: 4 hours  
**Status**: 🚀 Starting now

---

## 🎯 Objectives

Replace mock quality validation with real code analysis tools:
1. **Code Quality**: Pylint integration for Python code scoring
2. **Test Coverage**: Coverage.py for actual coverage measurement
3. **Security**: Bandit for security vulnerability scanning
4. **Documentation**: Check for README, docstrings, type hints
5. **Complexity**: Measure cyclomatic complexity

---

## 📋 Tasks (In Order)

### Task 1: Fix Quality Fabric API Syntax Error (15 min)
**File**: `~/projects/quality-fabric/services/api/routers/tests.py`  
**Issue**: Line 278 - non-default argument follows default argument

```python
# Current (broken):
async def retry_test_execution(
    execution_id: str,
    retry_failed_only: bool = Query(True, ...),
    background_tasks: BackgroundTasks,  # ❌ After default arg
    service: TestExecutionService = Depends(...)
)

# Fix:
async def retry_test_execution(
    execution_id: str,
    background_tasks: BackgroundTasks,  # ✅ Move before defaults
    retry_failed_only: bool = Query(True, ...),
    service: TestExecutionService = Depends(...)
)
```

### Task 2: Create Real Quality Analyzer (60 min)
**File**: `~/projects/quality-fabric/services/core/sdlc_quality_analyzer.py` (NEW)

Implement:
```python
class SDLCQualityAnalyzer:
    """Real quality analysis for SDLC personas"""
    
    async def analyze_code_quality(self, code_files: List[Dict]) -> Dict:
        """Run pylint on code files"""
        # Extract code, run pylint, return scores
        pass
    
    async def measure_test_coverage(
        self, 
        code_files: List[Dict], 
        test_files: List[Dict]
    ) -> float:
        """Calculate actual test coverage"""
        # Run coverage.py, return percentage
        pass
    
    async def scan_security(self, code_files: List[Dict]) -> Dict:
        """Run bandit security scan"""
        # Run bandit, return vulnerabilities
        pass
    
    async def check_documentation(self, files: List[Dict]) -> Dict:
        """Check documentation completeness"""
        # Check for README, docstrings, type hints
        pass
    
    async def analyze_complexity(self, code_files: List[Dict]) -> Dict:
        """Measure cyclomatic complexity"""
        # Calculate complexity scores
        pass
```

**Dependencies**:
```bash
pip install pylint coverage bandit radon
```

### Task 3: Update API Router to Use Real Analyzer (30 min)
**File**: `~/projects/quality-fabric/services/api/routers/sdlc_integration.py`

Replace mock logic in `validate_persona_output`:
```python
from services.core.sdlc_quality_analyzer import SDLCQualityAnalyzer

analyzer = SDLCQualityAnalyzer()

@router.post("/validate-persona")
async def validate_persona_output(request: PersonaValidationRequest):
    # Use real analyzer instead of mock
    analysis = await analyzer.analyze_persona_output(
        persona_type=request.persona_type,
        artifacts=request.artifacts
    )
    
    return PersonaValidationResponse(
        persona_id=request.persona_id,
        status=analysis["status"],
        overall_score=analysis["score"],
        quality_metrics=analysis["metrics"],
        ...
    )
```

### Task 4: Start Quality Fabric API Server (5 min)
```bash
cd ~/projects/quality-fabric
python3.11 services/api/main.py &

# Verify
curl http://localhost:8001/api/sdlc/health
```

### Task 5: Switch Client to Real APIs (10 min)
**File**: `~/projects/shared/claude_team_sdk/examples/sdlc_team/quality_fabric_client.py`

Change from mock to real:
```python
# Line ~50
USE_MOCK = False  # Switch to real API calls
```

Also update to actually make HTTP requests instead of mock responses.

### Task 6: Test with Real Analysis (20 min)
```bash
cd ~/projects/shared/claude_team_sdk/examples/sdlc_team

# Run demo with real analysis
python3.11 demo_quality_integration.py

# Should now see:
# - Real pylint scores (0-10)
# - Actual coverage % (0-100)
# - Security issues count
# - Slower (5-30s per validation)
```

### Task 7: Add Caching Layer (30 min)
**File**: `~/projects/quality-fabric/services/core/sdlc_quality_cache.py` (NEW)

Cache analysis results to speed up iterations:
```python
class QualityAnalysisCache:
    """Cache quality analysis results"""
    
    def __init__(self):
        self.cache = {}  # or Redis
    
    def get_cached_analysis(
        self, 
        code_hash: str,
        analysis_type: str
    ) -> Optional[Dict]:
        """Get cached analysis if available"""
        pass
    
    def cache_analysis(
        self,
        code_hash: str,
        analysis_type: str,
        result: Dict
    ):
        """Cache analysis result"""
        pass
```

### Task 8: Update Documentation (20 min)
Update guides to reflect real analysis:
- API_INTEGRATION_GUIDE.md
- DAY1_QUICK_START.md
- Add DAY2_COMPLETE.md

### Task 9: Performance Testing (15 min)
Benchmark real analysis vs mock:
```python
import time

# Mock: <100ms
# Real: 5-30 seconds expected

# Measure actual performance
```

### Task 10: Error Handling (20 min)
Add robust error handling for:
- Pylint crashes
- Coverage measurement failures
- Security scan errors
- Timeout handling

---

## 📊 Expected Results

### Mock (Day 1)
```
Backend Developer validation: <100ms
- Status: Based on presence checks
- Score: Estimated
- Coverage: Calculated from file counts
```

### Real (Day 2)
```
Backend Developer validation: 8-15 seconds
- Status: Based on actual analysis
- Score: Pylint score 0-10
- Coverage: Real % from coverage.py
- Security: Bandit vulnerability count
- Complexity: Radon cyclomatic complexity
```

---

## 🔧 Tools to Install

```bash
# In Quality Fabric environment
cd ~/projects/quality-fabric
python3.11 -m pip install --upgrade pip
python3.11 -m pip install pylint coverage bandit radon mccabe
```

---

## ⚡ Parallel Execution Plan

Can work in parallel on:
1. **Track A**: Fix syntax error + install dependencies (15 min)
2. **Track B**: Create analyzer implementation (60 min)
3. **Track C**: Update API router (30 min)
4. **Track D**: Add caching layer (30 min)
5. **Track E**: Documentation updates (20 min)

Total: ~60 min with parallelization

---

## 🎯 Success Criteria

- [ ] Quality Fabric API starts without errors
- [ ] Real pylint analysis working
- [ ] Real coverage measurement working
- [ ] Security scanning working
- [ ] API returns actual quality metrics
- [ ] Demo runs with real analysis
- [ ] Response time < 30 seconds
- [ ] Caching improves iteration speed
- [ ] Error handling robust
- [ ] Documentation updated

---

## 📈 Performance Targets

| Metric | Day 1 (Mock) | Day 2 (Real) | Target |
|--------|--------------|--------------|--------|
| Validation time | <100ms | 5-30s | <15s |
| Accuracy | Low | High | 95%+ |
| Pylint score | Estimated | Real | 0-10 |
| Coverage % | Estimated | Real | 0-100 |
| Security issues | Mock | Real | Actual |
| Cache hit rate | N/A | N/A | 80%+ |

---

## 🚀 Let's Start!

**Current Time**: Now  
**Target**: Complete in 4 hours  

**First step**: Fix syntax error and install dependencies in parallel.

---

**Created**: January 2025  
**Status**: 🚀 Ready to implement  
**Next**: Fix syntax error
