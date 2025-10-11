"""
Demo: Integrate Quality Fabric with SDLC Team Personas
Shows real persona integration with quality validation
"""

import asyncio
import logging
from pathlib import Path

# Import persona quality decorator
from persona_quality_decorator import (
    backend_developer_quality,
    frontend_developer_quality,
    qa_engineer_quality,
    quality_enforcer
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Mock Persona Execution Functions (simulating real personas)
# ============================================================================

@backend_developer_quality
async def execute_backend_developer(persona_id: str, context: dict):
    """
    Backend Developer Persona
    Generates backend code, API endpoints, business logic
    """
    logger.info(f"[{persona_id}] 🔨 Generating backend implementation...")
    
    # Simulate work
    await asyncio.sleep(0.2)
    
    # Check for quality feedback from previous iteration
    feedback = context.get("quality_feedback", {})
    iteration = feedback.get("iteration", 0)
    
    # Simulate progressive improvement
    has_tests = iteration >= 1  # Add tests in iteration 2+
    has_docs = iteration >= 2    # Add docs in iteration 3+
    
    output = {
        "code_files": [
            {
                "name": "api/main.py",
                "path": "backend/api/main.py",
                "lines": 250,
                "functions": 12
            },
            {
                "name": "api/models.py",
                "path": "backend/api/models.py",
                "lines": 180,
                "classes": 6
            },
            {
                "name": "api/services.py",
                "path": "backend/api/services.py",
                "lines": 320,
                "functions": 18
            }
        ],
        "test_files": [
            {
                "name": "test_api.py",
                "path": "backend/tests/test_api.py",
                "lines": 200,
                "test_cases": 24
            },
            {
                "name": "test_models.py",
                "path": "backend/tests/test_models.py",
                "lines": 150,
                "test_cases": 18
            }
        ] if has_tests else [],
        "documentation": [
            {
                "name": "API.md",
                "path": "docs/API.md",
                "lines": 120
            }
        ] if has_docs else [],
        "config_files": [
            {
                "name": "requirements.txt",
                "path": "backend/requirements.txt",
                "dependencies": 15
            }
        ],
        "metadata": {
            "framework": "FastAPI",
            "python_version": "3.11",
            "iteration": iteration + 1
        }
    }
    
    logger.info(f"[{persona_id}] Generated {len(output['code_files'])} code files, "
                f"{len(output['test_files'])} test files")
    
    return output


@frontend_developer_quality
async def execute_frontend_developer(persona_id: str, context: dict):
    """
    Frontend Developer Persona
    Generates UI components, pages, styling
    """
    logger.info(f"[{persona_id}] 🎨 Generating frontend implementation...")
    
    await asyncio.sleep(0.2)
    
    feedback = context.get("quality_feedback", {})
    iteration = feedback.get("iteration", 0)
    
    has_tests = iteration >= 1
    
    output = {
        "code_files": [
            {
                "name": "App.tsx",
                "path": "frontend/src/App.tsx",
                "lines": 150,
                "components": 5
            },
            {
                "name": "Dashboard.tsx",
                "path": "frontend/src/pages/Dashboard.tsx",
                "lines": 280,
                "components": 8
            },
            {
                "name": "api.ts",
                "path": "frontend/src/services/api.ts",
                "lines": 200,
                "functions": 12
            }
        ],
        "test_files": [
            {
                "name": "App.test.tsx",
                "path": "frontend/src/__tests__/App.test.tsx",
                "lines": 120,
                "test_cases": 15
            }
        ] if has_tests else [],
        "documentation": [
            {
                "name": "COMPONENTS.md",
                "path": "docs/COMPONENTS.md",
                "lines": 80
            }
        ],
        "config_files": [
            {
                "name": "package.json",
                "path": "frontend/package.json",
                "dependencies": 20
            }
        ],
        "metadata": {
            "framework": "React + TypeScript",
            "node_version": "18",
            "iteration": iteration + 1
        }
    }
    
    logger.info(f"[{persona_id}] Generated {len(output['code_files'])} components")
    
    return output


@qa_engineer_quality
async def execute_qa_engineer(persona_id: str, context: dict):
    """
    QA Engineer Persona
    Generates comprehensive test suites
    """
    logger.info(f"[{persona_id}] 🧪 Generating test suite...")
    
    await asyncio.sleep(0.15)
    
    output = {
        "code_files": [],
        "test_files": [
            {
                "name": "test_integration.py",
                "path": "tests/integration/test_integration.py",
                "lines": 350,
                "test_cases": 42
            },
            {
                "name": "test_e2e.py",
                "path": "tests/e2e/test_e2e.py",
                "lines": 280,
                "test_cases": 25
            },
            {
                "name": "test_performance.py",
                "path": "tests/performance/test_performance.py",
                "lines": 180,
                "test_cases": 12
            }
        ],
        "documentation": [
            {
                "name": "TEST_PLAN.md",
                "path": "docs/TEST_PLAN.md",
                "lines": 150
            },
            {
                "name": "TEST_RESULTS.md",
                "path": "docs/TEST_RESULTS.md",
                "lines": 80
            }
        ],
        "config_files": [
            {
                "name": "pytest.ini",
                "path": "tests/pytest.ini"
            }
        ],
        "metadata": {
            "test_framework": "pytest",
            "coverage_target": 85
        }
    }
    
    logger.info(f"[{persona_id}] Generated {len(output['test_files'])} test suites")
    
    return output


# ============================================================================
# Demo Workflow
# ============================================================================

async def demo_workflow():
    """
    Demonstrate full SDLC workflow with quality validation
    """
    print("\n" + "="*80)
    print("🚀 SDLC Team with Quality Fabric Integration Demo")
    print("="*80 + "\n")
    
    # Execution context
    context = {
        "project_name": "demo_ecommerce_platform",
        "requirements": "Build a scalable e-commerce platform",
        "tech_stack": {
            "backend": "Python FastAPI",
            "frontend": "React TypeScript",
            "database": "PostgreSQL"
        }
    }
    
    persona_results = []
    
    # ========================================================================
    # Phase 1: Implementation
    # ========================================================================
    print("\n" + "-"*80)
    print("📋 PHASE 1: IMPLEMENTATION")
    print("-"*80 + "\n")
    
    # Backend Developer
    print("\n👨‍💻 Executing Backend Developer...")
    backend_result = await execute_backend_developer(
        "backend_dev_001",
        context.copy()
    )
    persona_results.append({
        "persona_id": "backend_dev_001",
        "persona_type": "backend_developer",
        "overall_score": backend_result["validation"].overall_score,
        "status": backend_result["validation"].status,
        "iterations": backend_result["iterations"]
    })
    
    print(f"   Status: {backend_result['validation'].status}")
    print(f"   Score: {backend_result['validation'].overall_score:.1f}%")
    print(f"   Iterations: {backend_result['iterations']}")
    print(f"   Gates passed: {', '.join(backend_result['validation'].gates_passed)}")
    
    # Frontend Developer
    print("\n👩‍💻 Executing Frontend Developer...")
    frontend_result = await execute_frontend_developer(
        "frontend_dev_001",
        context.copy()
    )
    persona_results.append({
        "persona_id": "frontend_dev_001",
        "persona_type": "frontend_developer",
        "overall_score": frontend_result["validation"].overall_score,
        "status": frontend_result["validation"].status,
        "iterations": frontend_result["iterations"]
    })
    
    print(f"   Status: {frontend_result['validation'].status}")
    print(f"   Score: {frontend_result['validation'].overall_score:.1f}%")
    print(f"   Iterations: {frontend_result['iterations']}")
    
    # ========================================================================
    # Phase Gate: Implementation → Testing
    # ========================================================================
    print("\n" + "-"*80)
    print("🚪 PHASE GATE: Implementation → Testing")
    print("-"*80 + "\n")
    
    phase_gate_result = await quality_enforcer.validate_phase_gate(
        current_phase="implementation",
        next_phase="testing",
        persona_results=persona_results
    )
    
    print(f"   Gate Status: {phase_gate_result['status']}")
    print(f"   Overall Quality: {phase_gate_result['overall_quality_score']:.1f}%")
    
    if phase_gate_result['blockers']:
        print(f"   ❌ Blockers: {', '.join(phase_gate_result['blockers'])}")
    if phase_gate_result['warnings']:
        print(f"   ⚠️  Warnings: {', '.join(phase_gate_result['warnings'])}")
    
    if phase_gate_result['status'] in ['pass', 'warning']:
        print(f"   ✅ Transition allowed!")
        
        # ====================================================================
        # Phase 2: Testing
        # ====================================================================
        print("\n" + "-"*80)
        print("📋 PHASE 2: TESTING")
        print("-"*80 + "\n")
        
        # QA Engineer
        print("\n🧪 Executing QA Engineer...")
        qa_result = await execute_qa_engineer(
            "qa_eng_001",
            context.copy()
        )
        
        print(f"   Status: {qa_result['validation'].status}")
        print(f"   Score: {qa_result['validation'].overall_score:.1f}%")
        print(f"   Iterations: {qa_result['iterations']}")
    else:
        print(f"   ❌ Transition blocked!")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*80)
    print("📊 WORKFLOW SUMMARY")
    print("="*80 + "\n")
    
    print(f"✅ Personas Executed: {len(persona_results) + 1}")
    print(f"✅ Average Quality Score: {sum(r['overall_score'] for r in persona_results) / len(persona_results):.1f}%")
    print(f"✅ Total Iterations: {sum(r['iterations'] for r in persona_results) + qa_result['iterations']}")
    print(f"✅ Phase Gate Status: {phase_gate_result['status']}")
    
    print("\n🎉 Demo Complete!\n")


# ============================================================================
# Run Demo
# ============================================================================

if __name__ == "__main__":
    asyncio.run(demo_workflow())
