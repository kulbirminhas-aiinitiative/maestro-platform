#!/usr/bin/env python3
"""
Comprehensive Test Scenarios for Team Execution V2

This module generates 3 medium-complex requirements with extensive test cases
to validate the entire team_execution_v2 workflow:
1. AI-driven requirement analysis
2. Blueprint selection
3. Contract design
4. Team composition
5. Parallel execution
6. Contract validation
7. Quality assessment

Each scenario tests different execution patterns and contract types.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "maestro_hive" / "teams"))
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# TEST SCENARIO DEFINITIONS
# =============================================================================

@dataclass
class TestScenario:
    """A comprehensive test scenario"""
    id: str
    name: str
    description: str
    requirement: str
    expected_blueprint_type: str  # parallel, sequential, collaborative, etc.
    expected_personas: List[str]
    expected_contracts: List[str]
    expected_parallelization: str  # fully_parallel, partially_parallel, etc.
    complexity: str  # simple, moderate, complex, very_complex
    test_cases: List[Dict[str, Any]]
    success_criteria: Dict[str, Any]


# =============================================================================
# SCENARIO 1: E-Commerce REST API with Frontend
# =============================================================================

SCENARIO_1_ECOMMERCE_API = TestScenario(
    id="s1_ecommerce_api",
    name="E-Commerce Product Catalog API + Frontend",
    description="""
    Build a complete e-commerce product catalog system:
    - RESTful API backend with product CRUD operations
    - React frontend for browsing products
    - PostgreSQL database schema
    - Comprehensive test suite
    - API documentation
    
    This tests contract-first parallel development where frontend and backend
    can work simultaneously using OpenAPI contract.
    """,
    requirement="""
Build an e-commerce product catalog system with the following features:

1. Backend API (Node.js/Express):
   - GET /api/products - List all products with pagination
   - GET /api/products/:id - Get product details
   - POST /api/products - Create new product (admin only)
   - PUT /api/products/:id - Update product (admin only)
   - DELETE /api/products/:id - Delete product (admin only)
   - GET /api/products/search?q=<query> - Search products
   - Product fields: id, name, description, price, category, imageUrl, stock, createdAt

2. Database:
   - PostgreSQL schema with products table
   - Indexes on name and category for search performance
   - Migration scripts

3. Frontend (React):
   - Product listing page with grid layout
   - Product detail page
   - Search functionality
   - Admin panel for product management
   - Shopping cart interface

4. Testing:
   - Backend: API integration tests (Jest/Supertest)
   - Frontend: Component tests (React Testing Library)
   - E2E tests (Playwright)

5. Documentation:
   - OpenAPI/Swagger spec for API
   - README with setup instructions
   - Architecture diagram

Timeline: 2 weeks
Team size: 3-4 developers
Quality: Production-ready with 80%+ test coverage
""",
    expected_blueprint_type="parallel-contract-first",
    expected_personas=[
        "backend_developer",
        "frontend_developer",
        "database_architect",
        "test_engineer",
        "tech_writer"
    ],
    expected_contracts=[
        "product_api_contract",  # OpenAPI spec
        "database_schema_contract",
        "frontend_backend_contract",
        "test_coverage_contract"
    ],
    expected_parallelization="partially_parallel",
    complexity="complex",
    test_cases=[
        {
            "name": "Contract Design Validation",
            "description": "Verify AI designs proper OpenAPI contract",
            "validations": [
                "OpenAPI 3.0+ spec generated",
                "All 6 endpoints defined",
                "Request/response schemas complete",
                "Error responses documented",
                "Authentication specified"
            ]
        },
        {
            "name": "Parallel Execution Verification",
            "description": "Confirm frontend and backend work in parallel",
            "validations": [
                "Frontend starts before backend completes",
                "Frontend uses mock API from contract",
                "Time savings >= 40% vs sequential",
                "Both deliverables complete"
            ]
        },
        {
            "name": "Contract Fulfillment Check",
            "description": "Validate all contracts are fulfilled",
            "validations": [
                "Backend implements all API endpoints",
                "API matches OpenAPI spec 100%",
                "Frontend calls all defined endpoints",
                "Database schema matches contract",
                "Tests cover contract scenarios"
            ]
        },
        {
            "name": "Quality Gates",
            "description": "Ensure quality standards met",
            "validations": [
                "Backend test coverage >= 80%",
                "Frontend test coverage >= 75%",
                "No critical security issues",
                "API response time < 200ms",
                "Documentation complete"
            ]
        },
        {
            "name": "Team Composition Check",
            "description": "Verify correct team assembled",
            "validations": [
                "Backend developer assigned",
                "Frontend developer assigned",
                "Test engineer assigned",
                "Database architect assigned (if complex)",
                "Tech writer assigned"
            ]
        }
    ],
    success_criteria={
        "all_contracts_fulfilled": True,
        "min_quality_score": 0.85,
        "min_completeness_score": 0.90,
        "time_savings_vs_sequential": 0.40,
        "test_coverage_backend": 0.80,
        "test_coverage_frontend": 0.75,
        "zero_critical_issues": True
    }
)


# =============================================================================
# SCENARIO 2: Real-time Chat Application with WebSocket
# =============================================================================

SCENARIO_2_REALTIME_CHAT = TestScenario(
    id="s2_realtime_chat",
    name="Real-time Chat Application with WebSocket",
    description="""
    Build a real-time chat system with WebSocket communication:
    - WebSocket server for real-time messaging
    - React frontend with socket.io-client
    - Redis for message queuing and presence
    - User authentication and authorization
    - Message history and persistence
    
    This tests event-driven contract design and collaborative execution patterns.
    """,
    requirement="""
Develop a real-time chat application with these requirements:

1. Backend (Node.js/Socket.io):
   - WebSocket server for real-time bi-directional communication
   - Events: user_joined, user_left, message_sent, typing_indicator
   - JWT-based authentication
   - Room/channel support
   - Message history (last 100 messages per room)
   - Online user presence tracking

2. Redis Integration:
   - Pub/sub for horizontal scaling
   - User presence cache
   - Message queue for persistence
   - Session storage

3. Message Persistence (MongoDB):
   - Store all messages permanently
   - User profiles and room memberships
   - Support for message search
   - Attachment metadata storage

4. Frontend (React + Socket.io-client):
   - Real-time message display
   - Typing indicators
   - User presence indicators
   - Room switching
   - Message composer with emoji support
   - Notification system

5. Security:
   - XSS prevention
   - CSRF protection
   - Rate limiting (10 messages/second per user)
   - Input sanitization

6. Testing:
   - WebSocket connection tests
   - Message flow integration tests
   - Load testing (1000 concurrent users)
   - Frontend component tests

7. Monitoring:
   - Active connections dashboard
   - Message throughput metrics
   - Error rate tracking

Timeline: 3 weeks
Team size: 4-5 developers
Quality: Handle 10,000 concurrent connections
""",
    expected_blueprint_type="collaborative-consensus",
    expected_personas=[
        "backend_developer",
        "frontend_developer",
        "devops_engineer",
        "security_specialist",
        "test_engineer",
        "performance_engineer"
    ],
    expected_contracts=[
        "websocket_protocol_contract",  # Event schemas
        "authentication_contract",
        "redis_integration_contract",
        "frontend_backend_contract",
        "performance_contract"
    ],
    expected_parallelization="partially_parallel",
    complexity="very_complex",
    test_cases=[
        {
            "name": "Event Protocol Contract",
            "description": "Validate WebSocket event schema design",
            "validations": [
                "All events documented with schemas",
                "Bidirectional flow specified",
                "Error handling defined",
                "Reconnection strategy specified",
                "Message ordering guaranteed"
            ]
        },
        {
            "name": "Authentication Flow",
            "description": "Verify secure auth implementation",
            "validations": [
                "JWT token validation on connect",
                "Token refresh mechanism",
                "Unauthorized access blocked",
                "Session hijacking prevented"
            ]
        },
        {
            "name": "Real-time Performance",
            "description": "Confirm performance requirements met",
            "validations": [
                "Message latency < 100ms p95",
                "Support 1000+ concurrent connections",
                "Memory usage stable under load",
                "CPU usage < 70% at peak"
            ]
        },
        {
            "name": "Parallel Development Coordination",
            "description": "Check team coordination effectiveness",
            "validations": [
                "Frontend mocks WebSocket events from contract",
                "Backend implements event contract",
                "Redis integration independent",
                "UI developed before backend complete"
            ]
        },
        {
            "name": "Collaborative Consensus",
            "description": "Validate team collaboration patterns",
            "validations": [
                "Backend and DevOps agree on deployment",
                "Security specialist reviews architecture",
                "Performance engineer validates approach",
                "All concerns addressed before implementation"
            ]
        }
    ],
    success_criteria={
        "all_contracts_fulfilled": True,
        "min_quality_score": 0.88,
        "min_completeness_score": 0.92,
        "message_latency_p95_ms": 100,
        "concurrent_connections": 1000,
        "test_coverage_backend": 0.85,
        "security_audit_passed": True,
        "performance_benchmarks_met": True
    }
)


# =============================================================================
# SCENARIO 3: Data Pipeline with ML Model Deployment
# =============================================================================

SCENARIO_3_ML_PIPELINE = TestScenario(
    id="s3_ml_pipeline",
    name="Data Pipeline with ML Model Deployment",
    description="""
    Build an end-to-end ML pipeline:
    - Data ingestion from multiple sources
    - ETL pipeline with data validation
    - ML model training and evaluation
    - Model serving API
    - Monitoring and alerting
    
    This tests hybrid execution with sequential dependencies but parallel
    sub-tasks within each phase.
    """,
    requirement="""
Create a production ML pipeline for customer churn prediction:

1. Data Ingestion (Python/Airflow):
   - Ingest data from 3 sources: PostgreSQL, S3 CSV files, REST API
   - Schedule: Daily at 2 AM UTC
   - Data validation and quality checks
   - Store raw data in data lake (S3)

2. ETL Pipeline (Python/Pandas/PySpark):
   - Clean and transform data
   - Feature engineering:
     * Customer lifetime value
     * Engagement scores
     * Usage patterns
     * Transaction frequency
   - Store features in feature store
   - Data versioning with DVC

3. ML Model Training (Python/Scikit-learn/MLflow):
   - Train binary classification model (churn yes/no)
   - Models to evaluate: Random Forest, XGBoost, LightGBM
   - Hyperparameter tuning with Optuna
   - Track experiments in MLflow
   - Model validation (AUC > 0.85)
   - Model versioning and registry

4. Model Serving (FastAPI):
   - REST API for predictions
   - Endpoints:
     * POST /predict - Single prediction
     * POST /batch-predict - Batch predictions
     * GET /model/info - Model metadata
   - Input validation with Pydantic
   - Response time < 50ms p95

5. Monitoring (Prometheus/Grafana):
   - Model performance metrics
   - Prediction latency
   - Data drift detection
   - Alerting on degradation

6. Infrastructure (Terraform/Kubernetes):
   - Deploy to Kubernetes
   - Auto-scaling (2-10 pods)
   - CI/CD pipeline with GitHub Actions
   - Blue-green deployment

7. Testing:
   - Unit tests for data processing
   - Model accuracy tests
   - API integration tests
   - Load testing (1000 requests/sec)

8. Documentation:
   - Architecture diagram
   - Data dictionary
   - Model card (fairness, bias, limitations)
   - API documentation
   - Runbook for operations

Timeline: 4 weeks
Team size: 5-6 specialists
Quality: Production-grade with monitoring
""",
    expected_blueprint_type="hybrid-phased",
    expected_personas=[
        "data_engineer",
        "ml_engineer",
        "backend_developer",
        "devops_engineer",
        "test_engineer",
        "ml_ops_specialist",
        "tech_writer"
    ],
    expected_contracts=[
        "data_schema_contract",
        "feature_contract",
        "model_interface_contract",
        "api_contract",
        "deployment_contract",
        "monitoring_contract"
    ],
    expected_parallelization="partially_parallel",
    complexity="very_complex",
    test_cases=[
        {
            "name": "Phase Dependency Validation",
            "description": "Ensure correct execution order",
            "validations": [
                "Data ingestion completes before ETL",
                "ETL completes before model training",
                "Model trained before serving deployed",
                "Monitoring configured after deployment",
                "Parallel work within each phase"
            ]
        },
        {
            "name": "Data Contract Fulfillment",
            "description": "Verify data pipeline contracts",
            "validations": [
                "Data schema matches contract",
                "All features generated as specified",
                "Data quality checks passed",
                "Feature store populated correctly"
            ]
        },
        {
            "name": "Model Performance Contract",
            "description": "Validate ML model quality",
            "validations": [
                "Model AUC >= 0.85",
                "Prediction latency < 50ms p95",
                "Model versioned in registry",
                "Experiments tracked in MLflow",
                "Model card created"
            ]
        },
        {
            "name": "API Contract Compliance",
            "description": "Check serving API implementation",
            "validations": [
                "All endpoints implemented",
                "Input validation works",
                "Response format matches contract",
                "Error handling correct",
                "OpenAPI spec generated"
            ]
        },
        {
            "name": "Infrastructure Contract",
            "description": "Validate deployment and scaling",
            "validations": [
                "Kubernetes deployment successful",
                "Auto-scaling configured",
                "CI/CD pipeline works",
                "Blue-green deployment functional",
                "Monitoring dashboards deployed"
            ]
        },
        {
            "name": "Hybrid Execution Pattern",
            "description": "Confirm hybrid execution efficiency",
            "validations": [
                "Sequential phases respected",
                "Parallel tasks within phases",
                "Data eng + DevOps work in parallel on infra",
                "API dev + ML training in parallel",
                "Time savings >= 30% vs fully sequential"
            ]
        },
        {
            "name": "End-to-End Integration",
            "description": "Test full pipeline",
            "validations": [
                "Data flows end-to-end",
                "Predictions generated correctly",
                "Monitoring alerts work",
                "Model retraining possible",
                "Documentation complete"
            ]
        }
    ],
    success_criteria={
        "all_contracts_fulfilled": True,
        "min_quality_score": 0.90,
        "min_completeness_score": 0.95,
        "model_auc": 0.85,
        "api_latency_p95_ms": 50,
        "test_coverage": 0.85,
        "deployment_success": True,
        "monitoring_operational": True,
        "time_savings_vs_sequential": 0.30,
        "documentation_complete": True
    }
)


# =============================================================================
# TEST EXECUTION ENGINE
# =============================================================================

class ComprehensiveTestRunner:
    """
    Runs comprehensive test scenarios and tracks results.
    """
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("./test_comprehensive_output")
        self.output_dir.mkdir(exist_ok=True)
        self.results = []
    
    async def run_scenario(self, scenario: TestScenario) -> Dict[str, Any]:
        """
        Execute a test scenario and collect results.
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🧪 RUNNING SCENARIO: {scenario.name}")
        logger.info(f"{'='*80}\n")
        
        start_time = datetime.now()
        scenario_result = {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "started_at": start_time.isoformat(),
            "test_cases": [],
            "success": False,
            "errors": []
        }
        
        try:
            # Import team execution v2
            try:
                from team_execution_v2 import TeamExecutionEngineV2
            except ImportError:
                from maestro_hive.teams.team_execution_v2 import TeamExecutionEngineV2
            
            # Create engine
            engine = TeamExecutionEngineV2()
            
            logger.info(f"📋 Requirement:\n{scenario.requirement}\n")
            
            # Execute the requirement
            logger.info("🚀 Starting team execution...")
            execution_result = await engine.execute(
                requirement=scenario.requirement,
                constraints={
                    "test_scenario_id": scenario.id,
                    "expected_complexity": scenario.complexity,
                    "expected_parallelization": scenario.expected_parallelization
                }
            )
            
            # Save execution result
            result_file = self.output_dir / f"{scenario.id}_execution_result.json"
            with open(result_file, 'w') as f:
                json.dump(execution_result, f, indent=2, default=str)
            
            logger.info(f"💾 Execution result saved to: {result_file}")
            
            # Run test cases
            logger.info(f"\n{'─'*80}")
            logger.info("🔍 RUNNING TEST CASES")
            logger.info(f"{'─'*80}\n")
            
            for i, test_case in enumerate(scenario.test_cases, 1):
                logger.info(f"\n📝 Test Case {i}/{len(scenario.test_cases)}: {test_case['name']}")
                logger.info(f"   Description: {test_case['description']}")
                
                test_result = await self._run_test_case(
                    test_case,
                    execution_result,
                    scenario
                )
                scenario_result["test_cases"].append(test_result)
                
                # Log test result
                status = "✅ PASS" if test_result["passed"] else "❌ FAIL"
                logger.info(f"   Result: {status}")
                if not test_result["passed"]:
                    logger.warning(f"   Failures: {test_result['failures']}")
            
            # Validate success criteria
            logger.info(f"\n{'─'*80}")
            logger.info("🎯 VALIDATING SUCCESS CRITERIA")
            logger.info(f"{'─'*80}\n")
            
            criteria_result = self._validate_success_criteria(
                scenario.success_criteria,
                execution_result
            )
            scenario_result["success_criteria"] = criteria_result
            
            # Determine overall success
            all_tests_passed = all(tc["passed"] for tc in scenario_result["test_cases"])
            criteria_met = criteria_result["all_met"]
            scenario_result["success"] = all_tests_passed and criteria_met
            
            end_time = datetime.now()
            scenario_result["completed_at"] = end_time.isoformat()
            scenario_result["duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Summary
            logger.info(f"\n{'='*80}")
            if scenario_result["success"]:
                logger.info(f"✅ SCENARIO PASSED: {scenario.name}")
            else:
                logger.info(f"❌ SCENARIO FAILED: {scenario.name}")
            logger.info(f"{'='*80}\n")
            
            logger.info(f"Test Cases: {sum(1 for tc in scenario_result['test_cases'] if tc['passed'])}/{len(scenario_result['test_cases'])} passed")
            logger.info(f"Success Criteria: {criteria_result['met_count']}/{criteria_result['total_count']} met")
            logger.info(f"Duration: {scenario_result['duration_seconds']:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Scenario execution failed: {e}", exc_info=True)
            scenario_result["errors"].append(str(e))
            scenario_result["completed_at"] = datetime.now().isoformat()
        
        return scenario_result
    
    async def _run_test_case(
        self,
        test_case: Dict[str, Any],
        execution_result: Dict[str, Any],
        scenario: TestScenario
    ) -> Dict[str, Any]:
        """Run a single test case."""
        test_result = {
            "name": test_case["name"],
            "description": test_case["description"],
            "validations": [],
            "passed": False,
            "failures": []
        }
        
        # Run each validation
        for validation in test_case["validations"]:
            validation_result = await self._run_validation(
                validation,
                execution_result,
                scenario
            )
            test_result["validations"].append(validation_result)
            
            if not validation_result["passed"]:
                test_result["failures"].append(validation)
        
        # Test passes if all validations pass
        test_result["passed"] = len(test_result["failures"]) == 0
        
        return test_result
    
    async def _run_validation(
        self,
        validation: str,
        execution_result: Dict[str, Any],
        scenario: TestScenario
    ) -> Dict[str, Any]:
        """Run a single validation check."""
        # This is simplified - in production, each validation would have
        # specific logic to check the execution result
        
        validation_result = {
            "validation": validation,
            "passed": False,
            "details": ""
        }
        
        # Simulate validation logic
        # In reality, this would inspect execution_result deeply
        
        # For demo, we'll check if certain keys exist
        if "OpenAPI" in validation or "spec" in validation:
            # Check for contract in results
            if "contracts" in execution_result:
                validation_result["passed"] = True
                validation_result["details"] = "Contract found in results"
            else:
                validation_result["details"] = "No contracts in results"
        
        elif "parallel" in validation.lower():
            # Check for parallel execution evidence
            if execution_result.get("parallel_execution", False):
                validation_result["passed"] = True
                validation_result["details"] = "Parallel execution confirmed"
            else:
                validation_result["details"] = "No parallel execution detected"
        
        elif "coverage" in validation.lower():
            # Check test coverage
            quality = execution_result.get("quality_score", 0)
            if quality >= 0.75:
                validation_result["passed"] = True
                validation_result["details"] = f"Quality score: {quality}"
            else:
                validation_result["details"] = f"Quality score too low: {quality}"
        
        else:
            # Generic check - look for success indicators
            if execution_result.get("success", False):
                validation_result["passed"] = True
                validation_result["details"] = "Execution succeeded"
            else:
                validation_result["details"] = "Execution did not complete successfully"
        
        return validation_result
    
    def _validate_success_criteria(
        self,
        criteria: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate success criteria against execution result."""
        result = {
            "all_met": False,
            "total_count": len(criteria),
            "met_count": 0,
            "criteria": []
        }
        
        for criterion, expected_value in criteria.items():
            criterion_result = {
                "criterion": criterion,
                "expected": expected_value,
                "actual": None,
                "met": False
            }
            
            # Extract actual value from execution result
            # This is simplified - real implementation would be more sophisticated
            if criterion in execution_result:
                criterion_result["actual"] = execution_result[criterion]
            elif criterion == "all_contracts_fulfilled":
                criterion_result["actual"] = execution_result.get("success", False)
            elif criterion.startswith("min_"):
                metric = criterion.replace("min_", "")
                criterion_result["actual"] = execution_result.get(metric, 0)
            else:
                criterion_result["actual"] = "Not measured"
            
            # Check if met
            if isinstance(expected_value, (int, float)):
                actual = criterion_result["actual"]
                if isinstance(actual, (int, float)):
                    if criterion.startswith("min_"):
                        criterion_result["met"] = actual >= expected_value
                    else:
                        criterion_result["met"] = actual <= expected_value
            elif isinstance(expected_value, bool):
                criterion_result["met"] = criterion_result["actual"] == expected_value
            else:
                criterion_result["met"] = str(criterion_result["actual"]) == str(expected_value)
            
            if criterion_result["met"]:
                result["met_count"] += 1
            
            result["criteria"].append(criterion_result)
            
            # Log criterion
            status = "✅" if criterion_result["met"] else "❌"
            logger.info(f"   {status} {criterion}: {criterion_result['actual']} (expected: {expected_value})")
        
        result["all_met"] = result["met_count"] == result["total_count"]
        return result
    
    async def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all test scenarios."""
        logger.info("\n" + "="*80)
        logger.info("🚀 COMPREHENSIVE TEST SUITE - TEAM EXECUTION V2")
        logger.info("="*80 + "\n")
        
        scenarios = [
            SCENARIO_1_ECOMMERCE_API,
            SCENARIO_2_REALTIME_CHAT,
            SCENARIO_3_ML_PIPELINE
        ]
        
        suite_start = datetime.now()
        
        for i, scenario in enumerate(scenarios, 1):
            logger.info(f"\n{'#'*80}")
            logger.info(f"# SCENARIO {i}/{len(scenarios)}")
            logger.info(f"{'#'*80}\n")
            
            result = await self.run_scenario(scenario)
            self.results.append(result)
        
        suite_end = datetime.now()
        
        # Generate summary report
        summary = {
            "test_suite": "Team Execution V2 Comprehensive Tests",
            "started_at": suite_start.isoformat(),
            "completed_at": suite_end.isoformat(),
            "duration_seconds": (suite_end - suite_start).total_seconds(),
            "total_scenarios": len(scenarios),
            "passed_scenarios": sum(1 for r in self.results if r["success"]),
            "failed_scenarios": sum(1 for r in self.results if not r["success"]),
            "scenarios": self.results
        }
        
        # Save summary
        summary_file = self.output_dir / "test_suite_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"\n{'='*80}")
        logger.info("📊 TEST SUITE SUMMARY")
        logger.info(f"{'='*80}\n")
        logger.info(f"Total Scenarios: {summary['total_scenarios']}")
        logger.info(f"Passed: {summary['passed_scenarios']}")
        logger.info(f"Failed: {summary['failed_scenarios']}")
        logger.info(f"Duration: {summary['duration_seconds']:.2f}s")
        logger.info(f"\n💾 Summary saved to: {summary_file}\n")
        
        return summary


# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Main entry point."""
    runner = ComprehensiveTestRunner()
    summary = await runner.run_all_scenarios()
    
    # Exit with appropriate code
    if summary["failed_scenarios"] > 0:
        logger.error(f"\n❌ {summary['failed_scenarios']} scenario(s) failed")
        return 1
    else:
        logger.info(f"\n✅ All {summary['passed_scenarios']} scenario(s) passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
