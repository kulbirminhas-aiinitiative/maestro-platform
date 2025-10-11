# Action Plan: Get to Production Ready in 2-3 Days

**Goal:** Enable fully automated "review and fix to production quality" workflow  
**Timeline:** 2-3 days (16-24 hours focused work)  
**Status:** Ready to Start

---

## Day 1: Quality-Fabric Integration (8 hours)

### Morning Session (4 hours)

#### Task 1.1: Create Quality-Fabric API Client (2 hours)

**File:** `quality_fabric_api_client.py` (NEW)

**Requirements:**
- Async HTTP client using httpx
- Connection pooling and retries
- Authentication support
- Core endpoints integration

**Implementation:**
```python
"""
Quality-Fabric API Client for SDLC Workflow Integration
"""
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class QualityFabricClient:
    """Client for Quality-Fabric Testing as a Service API"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv('QUALITY_FABRIC_API_KEY')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Create async client with retries
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=self._get_headers(),
            follow_redirects=True
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    async def validate_project(
        self,
        project_path: str,
        validation_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Validate project using quality-fabric
        
        Args:
            project_path: Path to project directory
            validation_type: Type of validation (comprehensive, quick, security)
        
        Returns:
            {
                "score": 0.75,
                "issues": [...],
                "recommendations": [...],
                "metrics": {...}
            }
        """
        try:
            response = await self._post_with_retry(
                "/api/sdlc/validate-project",
                {
                    "project_path": str(project_path),
                    "validation_type": validation_type
                }
            )
            return response
        except Exception as e:
            logger.error(f"Failed to validate project: {e}")
            # Fallback to local validation
            return await self._fallback_validation(project_path)
    
    async def get_ai_suggestions(
        self,
        issues: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get AI-powered fix suggestions
        
        Args:
            issues: List of issues to get suggestions for
            context: Additional context (project type, tech stack, etc.)
        
        Returns:
            {
                "suggestions": [
                    {
                        "issue_id": "...",
                        "fix_type": "code_change",
                        "description": "...",
                        "confidence": 0.85,
                        "code_snippet": "..."
                    }
                ]
            }
        """
        try:
            response = await self._post_with_retry(
                "/api/ai/suggest-improvements",
                {
                    "issues": issues,
                    "context": context or {}
                }
            )
            return response
        except Exception as e:
            logger.error(f"Failed to get AI suggestions: {e}")
            return {"suggestions": []}
    
    async def run_comprehensive_tests(
        self,
        project_path: str,
        test_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive tests
        
        Args:
            project_path: Path to project
            test_types: Types of tests to run (unit, integration, e2e, security)
        
        Returns:
            Test results with coverage and metrics
        """
        test_types = test_types or ["unit", "integration", "security"]
        
        try:
            response = await self._post_with_retry(
                "/api/tests/run-comprehensive",
                {
                    "project_path": str(project_path),
                    "test_types": test_types
                }
            )
            return response
        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _post_with_retry(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(url, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Retry {attempt + 1}/{self.max_retries} for {endpoint}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
    
    async def _fallback_validation(self, project_path: str) -> Dict[str, Any]:
        """Fallback to local validation if API unavailable"""
        logger.warning("Using fallback validation (quality-fabric API unavailable)")
        
        # Import local validation
        from phase_gate_validator import PhaseGateValidator
        validator = PhaseGateValidator()
        
        # Run basic validation
        # (Simplified version - real implementation would be more comprehensive)
        return {
            "score": 0.0,
            "issues": ["Quality-fabric API unavailable"],
            "recommendations": ["Check quality-fabric service status"],
            "fallback": True
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Test the client
async def test_client():
    """Test quality-fabric client"""
    async with QualityFabricClient() as client:
        # Test health check
        try:
            response = await client.client.get(f"{client.base_url}/health")
            print(f"✅ Quality-Fabric API health: {response.json()}")
        except Exception as e:
            print(f"❌ Quality-Fabric API not available: {e}")


if __name__ == "__main__":
    asyncio.run(test_client())
```

**Validation:**
```bash
python quality_fabric_api_client.py
# Should connect to quality-fabric and show health status
```

---

#### Task 1.2: Integrate into Validator (2 hours)

**File:** `phase_gate_validator.py` (MODIFY)

**Changes:**
Add quality-fabric enrichment to validation:

```python
# Add import at top
from quality_fabric_api_client import QualityFabricClient

class PhaseGateValidator:
    def __init__(self, use_quality_fabric: bool = True):
        self.use_quality_fabric = use_quality_fabric
        self.qf_client = None
    
    async def validate_exit_criteria(
        self,
        phase: SDLCPhase,
        phase_exec: PhaseExecution,
        quality_thresholds: QualityThresholds,
        output_dir: Path
    ) -> PhaseGateResult:
        """Enhanced validation with quality-fabric"""
        
        # Run standard validation
        result = await self._run_standard_validation(...)
        
        # Enrich with quality-fabric if enabled
        if self.use_quality_fabric:
            try:
                qf_result = await self._run_quality_fabric_validation(output_dir)
                result = self._merge_validation_results(result, qf_result)
            except Exception as e:
                logger.warning(f"Quality-fabric enrichment failed: {e}")
        
        return result
    
    async def _run_quality_fabric_validation(
        self,
        output_dir: Path
    ) -> Dict[str, Any]:
        """Run quality-fabric validation"""
        if not self.qf_client:
            self.qf_client = QualityFabricClient()
        
        return await self.qf_client.validate_project(
            project_path=str(output_dir),
            validation_type="comprehensive"
        )
    
    def _merge_validation_results(
        self,
        standard: PhaseGateResult,
        qf_result: Dict[str, Any]
    ) -> PhaseGateResult:
        """Merge standard and quality-fabric results"""
        # Add quality-fabric issues
        qf_issues = qf_result.get("issues", [])
        standard.issues.extend(qf_issues)
        
        # Adjust score based on quality-fabric findings
        qf_score = qf_result.get("score", standard.quality_score)
        standard.quality_score = (standard.quality_score + qf_score) / 2
        
        # Add recommendations
        standard.recommendations.extend(qf_result.get("recommendations", []))
        
        return standard
```

**Validation:**
```bash
pytest tests/test_quality_fabric_integration.py -v
```

---

### Afternoon Session (4 hours)

#### Task 1.3: Create Orchestration Layer (4 hours)

**File:** `autonomous_quality_improver.py` (NEW)

**Requirements:**
- Main orchestration loop
- Iteration management
- Quality tracking
- Reporting

**Implementation:**
```python
"""
Autonomous Quality Improver
Automatically improve project quality to production level
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from phase_models import SDLCPhase
from phased_autonomous_executor import PhasedAutonomousExecutor
from quality_fabric_api_client import QualityFabricClient
from maestro_ml_client import MaestroMLClient

logger = logging.getLogger(__name__)


class AutonomousQualityImprover:
    """Autonomous quality improvement orchestrator"""
    
    def __init__(
        self,
        use_quality_fabric: bool = True,
        use_rag_templates: bool = True,
        use_ml_predictions: bool = True
    ):
        self.use_quality_fabric = use_quality_fabric
        self.use_rag_templates = use_rag_templates
        self.use_ml_predictions = use_ml_predictions
        
        # Initialize clients
        self.qf_client = QualityFabricClient() if use_quality_fabric else None
        self.ml_client = MaestroMLClient() if use_rag_templates else None
        
        # Tracking
        self.improvement_history: List[Dict[str, Any]] = []
    
    async def improve_to_production_quality(
        self,
        project_path: str,
        target_quality: float = 0.90,
        max_iterations: int = 5,
        min_improvement: float = 0.05,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automatically improve project to production quality
        
        Args:
            project_path: Path to project to improve
            target_quality: Target quality score (0-1)
            max_iterations: Maximum improvement iterations
            min_improvement: Minimum improvement per iteration
            session_id: Optional session ID for tracking
        
        Returns:
            Improvement report with before/after metrics
        """
        project_path = Path(project_path)
        session_id = session_id or f"quality_improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 Starting Autonomous Quality Improvement")
        logger.info(f"{'='*80}")
        logger.info(f"   Project: {project_path}")
        logger.info(f"   Target Quality: {target_quality:.0%}")
        logger.info(f"   Max Iterations: {max_iterations}")
        logger.info(f"   Session: {session_id}")
        logger.info(f"{'='*80}\n")
        
        # Initialize executor
        executor = PhasedAutonomousExecutor(
            requirement=f"Improve {project_path.name} to production quality",
            output_dir=project_path,
            session_id=session_id
        )
        
        # Step 1: Initial Validation
        logger.info("📊 Step 1: Initial Validation...")
        initial_validation = await executor._run_comprehensive_validation(project_path)
        initial_score = initial_validation['overall_score']
        
        logger.info(f"   Initial Quality Score: {initial_score:.2%}")
        logger.info(f"   Issues Found: {len(initial_validation.get('all_issues', []))}")
        
        if initial_score >= target_quality:
            logger.info(f"✅ Project already meets quality target ({initial_score:.2%} >= {target_quality:.2%})")
            return self._generate_report(
                project_path=project_path,
                initial_validation=initial_validation,
                final_validation=initial_validation,
                iterations_run=0,
                target_achieved=True
            )
        
        # Step 2: Iterative Improvement
        current_score = initial_score
        iteration = 0
        
        while iteration < max_iterations and current_score < target_quality:
            iteration += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"🔄 Iteration {iteration}/{max_iterations}")
            logger.info(f"{'='*80}")
            logger.info(f"   Current Score: {current_score:.2%}")
            logger.info(f"   Target Score: {target_quality:.2%}")
            logger.info(f"   Gap: {(target_quality - current_score):.2%}")
            
            # 2.1: Analyze with Quality-Fabric (if enabled)
            ai_suggestions = []
            if self.use_quality_fabric and self.qf_client:
                logger.info("\n🤖 Getting AI-powered suggestions from quality-fabric...")
                try:
                    qf_analysis = await self.qf_client.get_ai_suggestions(
                        issues=initial_validation.get('all_issues', []),
                        context={
                            "project_type": "web_application",
                            "current_score": current_score,
                            "target_score": target_quality,
                            "iteration": iteration
                        }
                    )
                    ai_suggestions = qf_analysis.get('suggestions', [])
                    logger.info(f"   Got {len(ai_suggestions)} AI suggestions")
                except Exception as e:
                    logger.warning(f"   Quality-fabric suggestions failed: {e}")
            
            # 2.2: Check RAG templates (if enabled)
            template_matches = []
            if self.use_rag_templates and self.ml_client:
                logger.info("\n📚 Checking RAG templates for similar solutions...")
                try:
                    # Get issues by persona
                    issues_by_persona = self._group_issues_by_persona(
                        initial_validation.get('all_issues', [])
                    )
                    
                    for persona, issues in issues_by_persona.items():
                        matches = await self.ml_client.find_similar_templates(
                            requirement=" ".join(issues[:3]),  # Use top 3 issues
                            persona=persona,
                            threshold=0.70
                        )
                        template_matches.extend(matches)
                    
                    logger.info(f"   Found {len(template_matches)} template matches")
                except Exception as e:
                    logger.warning(f"   Template matching failed: {e}")
            
            # 2.3: Plan Remediation
            logger.info("\n📋 Planning remediation...")
            remediation_plan = await executor._plan_remediation(
                initial_validation.get('all_issues', [])
            )
            
            total_personas = sum(len(p) for p in remediation_plan.values())
            logger.info(f"   Phases to remediate: {len(remediation_plan)}")
            logger.info(f"   Total personas: {total_personas}")
            
            for phase, personas in remediation_plan.items():
                logger.info(f"      {phase}: {', '.join(personas)}")
            
            # 2.4: Execute Remediation
            logger.info("\n🔧 Executing remediation...")
            remediation_result = await executor._execute_remediation(
                project_dir=project_path,
                remediation_plan=remediation_plan,
                validation_results=initial_validation
            )
            
            # 2.5: Validate Improvements
            new_score = remediation_result['final_score']
            improvement = new_score - current_score
            
            logger.info(f"\n📈 Iteration {iteration} Results:")
            logger.info(f"   Before: {current_score:.2%}")
            logger.info(f"   After: {new_score:.2%}")
            logger.info(f"   Improvement: {improvement:+.2%}")
            
            # Track iteration
            self.improvement_history.append({
                "iteration": iteration,
                "score_before": current_score,
                "score_after": new_score,
                "improvement": improvement,
                "personas_executed": total_personas,
                "ai_suggestions_used": len(ai_suggestions),
                "templates_matched": len(template_matches)
            })
            
            # Check if improvement is too small
            if improvement < min_improvement:
                logger.warning(f"\n⚠️  Improvement too small ({improvement:.2%} < {min_improvement:.2%})")
                logger.warning("   Stopping iterations - may have reached maximum achievable quality")
                break
            
            current_score = new_score
        
        # Step 3: Final Report
        final_validation = remediation_result.get('final_validation', initial_validation)
        target_achieved = current_score >= target_quality
        
        logger.info(f"\n{'='*80}")
        logger.info(f"{'✅' if target_achieved else '⚠️ '} Quality Improvement Complete")
        logger.info(f"{'='*80}")
        logger.info(f"   Initial Score: {initial_score:.2%}")
        logger.info(f"   Final Score: {current_score:.2%}")
        logger.info(f"   Total Improvement: {(current_score - initial_score):+.2%}")
        logger.info(f"   Target: {target_quality:.2%} {'✅ ACHIEVED' if target_achieved else '❌ NOT ACHIEVED'}")
        logger.info(f"   Iterations: {iteration}")
        logger.info(f"{'='*80}\n")
        
        report = self._generate_report(
            project_path=project_path,
            initial_validation=initial_validation,
            final_validation=final_validation,
            iterations_run=iteration,
            target_achieved=target_achieved
        )
        
        return report
    
    def _group_issues_by_persona(self, issues: List[str]) -> Dict[str, List[str]]:
        """Group issues by relevant persona"""
        # Simple keyword-based grouping
        persona_keywords = {
            "backend_developer": ["api", "database", "backend", "server"],
            "frontend_developer": ["ui", "frontend", "react", "component"],
            "qa_engineer": ["test", "quality", "coverage"],
            "devops_engineer": ["deploy", "docker", "ci/cd"],
            "security_engineer": ["security", "auth", "vulnerability"]
        }
        
        grouped = {}
        for issue in issues:
            issue_lower = issue.lower()
            assigned = False
            
            for persona, keywords in persona_keywords.items():
                if any(kw in issue_lower for kw in keywords):
                    if persona not in grouped:
                        grouped[persona] = []
                    grouped[persona].append(issue)
                    assigned = True
                    break
            
            if not assigned:
                if "general" not in grouped:
                    grouped["general"] = []
                grouped["general"].append(issue)
        
        return grouped
    
    def _generate_report(
        self,
        project_path: Path,
        initial_validation: Dict[str, Any],
        final_validation: Dict[str, Any],
        iterations_run: int,
        target_achieved: bool
    ) -> Dict[str, Any]:
        """Generate comprehensive improvement report"""
        report = {
            "project": str(project_path),
            "session_id": getattr(self, 'session_id', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "initial_score": initial_validation['overall_score'],
            "final_score": final_validation['overall_score'],
            "improvement": final_validation['overall_score'] - initial_validation['overall_score'],
            "iterations_run": iterations_run,
            "target_achieved": target_achieved,
            "improvement_history": self.improvement_history,
            "initial_issues_count": len(initial_validation.get('all_issues', [])),
            "final_issues_count": len(final_validation.get('all_issues', [])),
            "issues_resolved": len(initial_validation.get('all_issues', [])) - len(final_validation.get('all_issues', [])),
            "configuration": {
                "use_quality_fabric": self.use_quality_fabric,
                "use_rag_templates": self.use_rag_templates,
                "use_ml_predictions": self.use_ml_predictions
            }
        }
        
        # Save report
        report_file = project_path / f"quality_improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Report saved to: {report_file}")
        
        return report
    
    async def close(self):
        """Cleanup resources"""
        if self.qf_client:
            await self.qf_client.close()


# CLI Interface
async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous Quality Improver")
    parser.add_argument("--project", required=True, help="Project path to improve")
    parser.add_argument("--target-quality", type=float, default=0.90, help="Target quality score (0-1)")
    parser.add_argument("--max-iterations", type=int, default=5, help="Maximum iterations")
    parser.add_argument("--no-quality-fabric", action="store_true", help="Disable quality-fabric integration")
    parser.add_argument("--no-rag", action="store_true", help="Disable RAG templates")
    parser.add_argument("--session", help="Session ID for tracking")
    
    args = parser.parse_args()
    
    improver = AutonomousQualityImprover(
        use_quality_fabric=not args.no_quality_fabric,
        use_rag_templates=not args.no_rag
    )
    
    try:
        report = await improver.improve_to_production_quality(
            project_path=args.project,
            target_quality=args.target_quality,
            max_iterations=args.max_iterations,
            session_id=args.session
        )
        
        print(f"\n✅ Quality improvement complete!")
        print(f"   Initial: {report['initial_score']:.2%}")
        print(f"   Final: {report['final_score']:.2%}")
        print(f"   Improvement: {report['improvement']:+.2%}")
        print(f"   Target Achieved: {'✅ Yes' if report['target_achieved'] else '❌ No'}")
        
    finally:
        await improver.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

**Validation:**
```bash
# Test with sunday_com
python autonomous_quality_improver.py \
    --project sunday_com \
    --target-quality 0.85 \
    --max-iterations 2 \
    --session sunday_test_run
```

---

## Day 2: Testing and Refinement (8 hours)

### Morning Session (4 hours)

#### Task 2.1: Integration Testing (2 hours)

**File:** `tests/test_quality_improvement_integration.py` (NEW)

**Tests:**
1. Test validation → remediation flow
2. Test quality-fabric integration
3. Test RAG template matching
4. Test iteration logic
5. Test stopping criteria

#### Task 2.2: Bug Fixes (2 hours)

Fix issues found during testing:
- Error handling edge cases
- API timeout handling
- Path resolution issues
- Scoring calculation bugs

---

### Afternoon Session (4 hours)

#### Task 2.3: End-to-End Sunday.com Test (3 hours)

Run full workflow on sunday_com:

```bash
# Full production run
python autonomous_quality_improver.py \
    --project sunday_com \
    --target-quality 0.90 \
    --max-iterations 3 \
    --session sunday_production_run
```

Monitor and document:
- Initial score
- Issues identified
- Remediation actions taken
- Template reuse
- Final score
- Time taken
- Cost (estimated)

#### Task 2.4: Documentation (1 hour)

Create user guide:
- Installation instructions
- Configuration options
- Usage examples
- Troubleshooting guide

---

## Day 3: Polish and Deploy (4-6 hours)

### Morning Session (2-3 hours)

#### Task 3.1: Performance Optimization

- Add caching for validation results
- Parallel persona execution where possible
- Optimize RAG template matching
- Add progress indicators

#### Task 3.2: Error Handling Enhancement

- Graceful degradation when quality-fabric unavailable
- Rollback on quality regression
- Partial failure recovery
- Better error messages

---

### Afternoon Session (2-3 hours)

#### Task 3.3: Final Validation

Run on multiple projects:
1. sunday_com (primary test case)
2. kids_learning_platform (secondary test)
3. Any other available projects

#### Task 3.4: Production Deployment

1. Set environment variables
2. Configure quality-fabric connection
3. Set up maestro-templates storage
4. Create production configuration
5. Deploy and test

---

## Success Criteria

After completing this plan, you should be able to:

```bash
# Single command to improve any project to production quality
python autonomous_quality_improver.py \
    --project <any_project> \
    --target-quality 0.90 \
    --max-iterations 5
```

And it will:
- ✅ Automatically validate the project
- ✅ Identify all quality issues
- ✅ Get AI-powered fix suggestions from quality-fabric
- ✅ Check RAG templates for similar solutions
- ✅ Execute targeted remediations
- ✅ Iterate until target quality achieved
- ✅ Generate comprehensive report
- ✅ Track costs and savings

---

## Contingency Plans

### If Quality-Fabric API Not Available
**Fallback:** Use local validation only
**Impact:** -20% quality analysis depth
**Mitigation:** Implement quality-fabric integration later

### If RAG Templates Empty
**Fallback:** Execute all personas normally
**Impact:** -30% cost savings
**Mitigation:** Bootstrap templates from successful executions

### If Sunday.com Test Fails
**Fallback:** Use simpler test project
**Impact:** Need more debugging time
**Mitigation:** Add more logging and debug mode

---

## Expected Outcomes

### After Day 1
- ✅ Quality-fabric integration working
- ✅ Orchestration layer created
- ✅ Basic end-to-end flow functional
- ⚠️ May have bugs

### After Day 2
- ✅ Bugs fixed
- ✅ Integration tested
- ✅ Sunday.com test complete
- ✅ Documentation ready

### After Day 3
- ✅ Production ready
- ✅ Optimized performance
- ✅ Comprehensive testing
- ✅ Deployment complete

---

## Next Steps

**Ready to start Day 1?**

Just say:
- **"Proceed with Day 1"** - I'll create all Day 1 files
- **"Show me Task 1.1 first"** - I'll create quality_fabric_api_client.py
- **"I need more details on X"** - I'll explain any section in detail

**Your choice!**
