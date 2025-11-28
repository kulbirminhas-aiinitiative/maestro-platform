#!/usr/bin/env python3
"""
Comprehensive Test Suite for Workflow Validation System

Tests all validation components:
- workflow_validation.py
- workflow_gap_detector.py
- implementation_completeness_checker.py
- deployment_readiness_validator.py
- dag_validation_nodes.py
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_validation import WorkflowValidator, ValidationSeverity
from workflow_gap_detector import WorkflowGapDetector
from implementation_completeness_checker import ImplementationCompletenessChecker, SubPhase
from deployment_readiness_validator import DeploymentReadinessValidator
from dag_validation_nodes import (
    PhaseValidationNodeExecutor,
    GapDetectionNodeExecutor,
    CompletenessCheckNodeExecutor,
    DeploymentReadinessNodeExecutor,
    ValidationConfig,
    ValidationNodeType
)


class TestWorkflowValidator:
    """Test workflow_validation.py"""

    def setup_method(self):
        """Create temporary workflow directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workflow_dir = self.temp_dir / "test_workflow"
        self.workflow_dir.mkdir()

    def teardown_method(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_complete_requirements(self):
        """Create complete requirements phase"""
        req_dir = self.workflow_dir / "requirements"
        req_dir.mkdir()

        # Create required docs with correct names
        (req_dir / "01_Product_Requirements_Document.md").write_text("# Product Requirements\n\nComplete PRD content here.")
        (req_dir / "02_Functional_Requirements_Specification.md").write_text("# Functional Specs\n\nComplete functional specs here.")
        (req_dir / "03_Non_Functional_Requirements.md").write_text("# Non-Functional Requirements\n\nComplete NFRs here.")
        (req_dir / "04_User_Stories_and_Use_Cases.md").write_text("# User Stories\n\nComplete user stories here.")
        (req_dir / "Technical_Specs.md").write_text("# Technical Specs")

    def _create_incomplete_implementation(self):
        """Create incomplete implementation phase"""
        impl_dir = self.workflow_dir / "implementation"
        impl_dir.mkdir()

        # Create backend with only models
        backend_dir = impl_dir / "backend" / "src" / "models"
        backend_dir.mkdir(parents=True)
        (backend_dir / "User.ts").write_text("export class User {}")
        (backend_dir / "Product.ts").write_text("export class Product {}")

    def test_validate_requirements_pass(self):
        """Test requirements validation passes with complete docs"""
        self._create_complete_requirements()

        validator = WorkflowValidator(self.workflow_dir)
        report = validator.validate_phase("requirements")

        assert report.overall_status == "passed"
        assert len([r for r in report.results if not r.passed]) == 0

    def test_validate_requirements_fail(self):
        """Test requirements validation detects missing docs"""
        req_dir = self.workflow_dir / "requirements"
        req_dir.mkdir()
        (req_dir / "README.md").write_text("Just a readme")

        validator = WorkflowValidator(self.workflow_dir)
        report = validator.validate_phase("requirements")

        # Should be warning (non-critical failures) not passed
        assert report.overall_status == "warning"
        failures = [r for r in report.results if not r.passed]
        assert len(failures) > 0

    def test_validate_implementation_incomplete(self):
        """Test implementation validation detects incomplete backend"""
        self._create_incomplete_implementation()

        validator = WorkflowValidator(self.workflow_dir)
        report = validator.validate_phase("implementation")

        assert report.overall_status == "failed"
        critical_failures = [
            r for r in report.results
            if not r.passed and r.severity == ValidationSeverity.CRITICAL
        ]
        assert len(critical_failures) > 0

    def test_validate_all_phases(self):
        """Test validating all phases"""
        self._create_complete_requirements()

        validator = WorkflowValidator(self.workflow_dir)
        reports = validator.validate_all()

        assert "requirements" in reports
        assert len(reports) == 5  # All 5 SDLC phases


class TestGapDetector:
    """Test workflow_gap_detector.py"""

    def setup_method(self):
        """Create temporary workflow directory"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workflow_dir = self.temp_dir / "test_workflow"
        self.workflow_dir.mkdir()

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_incomplete_backend(self):
        """Create incomplete backend with server.ts that imports missing routes"""
        backend_dir = self.workflow_dir / "implementation" / "backend" / "src"
        backend_dir.mkdir(parents=True)

        # Create server.ts with route imports
        server_ts = backend_dir / "server.ts"
        server_ts.write_text("""
import express from 'express';
import authRoutes from './routes/auth.routes';
import userRoutes from './routes/user.routes';

const app = express();
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);
        """)

        # Create some models
        models_dir = backend_dir / "models"
        models_dir.mkdir()
        (models_dir / "User.ts").write_text("export class User {}")

    def test_detect_backend_gaps(self):
        """Test gap detection identifies missing routes"""
        self._create_incomplete_backend()

        detector = WorkflowGapDetector(self.workflow_dir)
        report = detector.detect_gaps()

        assert report.total_gaps > 0
        assert report.critical_gaps > 0
        assert not report.is_deployable

    def test_generate_recovery_context(self):
        """Test recovery context generation"""
        self._create_incomplete_backend()

        detector = WorkflowGapDetector(self.workflow_dir)
        report = detector.detect_gaps()
        recovery_ctx = detector.generate_recovery_context(report)

        assert "recovery_instructions" in recovery_ctx
        assert len(recovery_ctx["recovery_instructions"]) > 0
        assert recovery_ctx["workflow_id"] == self.workflow_dir.name

    def test_empty_workflow(self):
        """Test gap detection on empty workflow"""
        detector = WorkflowGapDetector(self.workflow_dir)
        report = detector.detect_gaps()

        # Should have many gaps for empty workflow
        assert report.total_gaps > 0
        assert report.estimated_completion_percentage <= 0.25  # Default for empty workflow


class TestCompletenessChecker:
    """Test implementation_completeness_checker.py"""

    def setup_method(self):
        """Create temporary workflow directory"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workflow_dir = self.temp_dir / "test_workflow"
        self.workflow_dir.mkdir()

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_backend_models(self):
        """Create backend models sub-phase"""
        models_dir = self.workflow_dir / "implementation" / "backend" / "src" / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "User.ts").write_text("export class User {}")
        (models_dir / "Product.ts").write_text("export class Product {}")
        (models_dir / "Order.ts").write_text("export class Order {}")

    def _create_backend_services(self):
        """Create backend services sub-phase"""
        services_dir = self.workflow_dir / "implementation" / "backend" / "src" / "services"
        services_dir.mkdir(parents=True)
        (services_dir / "UserService.ts").write_text("export class UserService {}")
        (services_dir / "ProductService.ts").write_text("export class ProductService {}")
        (services_dir / "OrderService.ts").write_text("export class OrderService {}")

    def test_backend_models_complete(self):
        """Test backend_models sub-phase completeness"""
        self._create_backend_models()

        checker = ImplementationCompletenessChecker(self.workflow_dir)
        progress = checker.check_implementation_progress()

        # Backend models should be detected as present
        backend_models_progress = progress.sub_phase_progress.get(SubPhase.BACKEND_MODELS)
        assert backend_models_progress is not None
        assert backend_models_progress.completion_percentage > 0.5

    def test_overall_completion(self):
        """Test overall completion calculation"""
        self._create_backend_models()
        self._create_backend_services()

        checker = ImplementationCompletenessChecker(self.workflow_dir)
        progress = checker.check_implementation_progress()

        # Should have some completion
        assert progress.overall_completion > 0.1
        assert progress.overall_completion < 1.0  # Not fully complete
        assert not progress.is_deployable  # Missing frontend

    def test_empty_implementation(self):
        """Test completeness checker on empty implementation"""
        checker = ImplementationCompletenessChecker(self.workflow_dir)
        progress = checker.check_implementation_progress()

        assert progress.overall_completion < 0.1
        assert not progress.backend_complete
        assert not progress.frontend_complete
        assert not progress.is_deployable


class TestDeploymentReadinessValidator:
    """Test deployment_readiness_validator.py"""

    def setup_method(self):
        """Create temporary workflow directory"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workflow_dir = self.temp_dir / "test_workflow"
        self.workflow_dir.mkdir()

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_basic_deployment(self):
        """Create basic deployment directory"""
        deploy_dir = self.workflow_dir / "deployment"
        deploy_dir.mkdir()

        # Create docker-compose.yml
        compose_file = deploy_dir / "docker-compose.yml"
        compose_file.write_text("""
version: '3.8'
services:
  backend:
    build:
      context: ../implementation/backend
      dockerfile: ../../deployment/docker/Dockerfile.backend
    ports:
      - "3000:3000"
""")

        # Create Dockerfile
        docker_dir = deploy_dir / "docker"
        docker_dir.mkdir()
        dockerfile = docker_dir / "Dockerfile.backend"
        dockerfile.write_text("""
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "start"]
""")

    @pytest.mark.asyncio
    async def test_no_deployment_directory(self):
        """Test validation fails when deployment directory missing"""
        validator = DeploymentReadinessValidator(self.workflow_dir)
        report = await validator.validate()

        assert not report.is_deployable
        assert report.critical_failures > 0

    @pytest.mark.asyncio
    async def test_basic_deployment_present(self):
        """Test validation with basic deployment files"""
        self._create_basic_deployment()

        validator = DeploymentReadinessValidator(self.workflow_dir)
        report = await validator.validate()

        # Should have some checks pass
        assert report.checks_passed > 0

    @pytest.mark.asyncio
    async def test_docker_compose_validation(self):
        """Test Docker Compose file validation"""
        self._create_basic_deployment()

        validator = DeploymentReadinessValidator(self.workflow_dir)
        report = await validator.validate()

        # Check that docker-compose validation ran
        compose_checks = [
            c for c in report.checks
            if 'docker_compose' in c.check_name
        ]
        assert len(compose_checks) > 0


class TestDAGValidationNodes:
    """Test dag_validation_nodes.py integration"""

    def setup_method(self):
        """Setup for DAG node tests"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workflow_dir = self.temp_dir / "test_workflow"
        self.workflow_dir.mkdir()

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_phase_validation_node(self):
        """Test PhaseValidationNodeExecutor"""
        # Create some requirements
        req_dir = self.workflow_dir / "requirements"
        req_dir.mkdir()
        for i in range(5):
            (req_dir / f"doc{i}.md").write_text(f"# Document {i}")

        config = ValidationConfig(
            validation_type=ValidationNodeType.PHASE_VALIDATOR,
            phase_to_validate="requirements",
            fail_on_validation_error=False
        )

        executor = PhaseValidationNodeExecutor(config)
        node_input = {
            'global_context': {'workflow_dir': str(self.workflow_dir)},
            'dependency_outputs': {},
            'all_outputs': {}
        }

        result = await executor.execute(node_input)

        assert 'status' in result
        assert 'validation_passed' in result

    @pytest.mark.asyncio
    async def test_gap_detection_node(self):
        """Test GapDetectionNodeExecutor"""
        config = ValidationConfig(
            validation_type=ValidationNodeType.GAP_DETECTOR,
            generate_recovery_context=True
        )

        executor = GapDetectionNodeExecutor(config)
        node_input = {
            'global_context': {'workflow_dir': str(self.workflow_dir)},
            'dependency_outputs': {}
        }

        result = await executor.execute(node_input)

        assert 'status' in result
        assert 'gaps_detected' in result

    @pytest.mark.asyncio
    async def test_completeness_check_node(self):
        """Test CompletenessCheckNodeExecutor"""
        config = ValidationConfig(
            validation_type=ValidationNodeType.COMPLETENESS_CHECKER
        )

        executor = CompletenessCheckNodeExecutor(config)
        node_input = {
            'global_context': {'workflow_dir': str(self.workflow_dir)},
            'dependency_outputs': {}
        }

        result = await executor.execute(node_input)

        assert 'status' in result
        assert 'overall_completion' in result

    @pytest.mark.asyncio
    async def test_deployment_readiness_node(self):
        """Test DeploymentReadinessNodeExecutor"""
        config = ValidationConfig(
            validation_type=ValidationNodeType.DEPLOYMENT_READINESS
        )

        executor = DeploymentReadinessNodeExecutor(config)
        node_input = {
            'global_context': {'workflow_dir': str(self.workflow_dir)},
            'dependency_outputs': {}
        }

        result = await executor.execute(node_input)

        assert 'status' in result
        assert 'is_deployable' in result


class TestIntegration:
    """Integration tests for complete workflow validation"""

    def setup_method(self):
        """Setup integration test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workflow_dir = self.temp_dir / "complete_workflow"
        self.workflow_dir.mkdir()

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_complete_workflow(self):
        """Create a complete workflow structure"""
        # Requirements - with correct numbered names
        req_dir = self.workflow_dir / "requirements"
        req_dir.mkdir()
        req_docs = [
            "01_Product_Requirements_Document.md",
            "02_Functional_Requirements_Specification.md",
            "03_Non_Functional_Requirements.md",
            "04_User_Stories_and_Use_Cases.md",
            "Technical_Specs.md"
        ]
        for doc in req_docs:
            (req_dir / doc).write_text(f"# {doc}\n\nComplete content for {doc}")

        # Design - with correct numbered names
        design_dir = self.workflow_dir / "design"
        design_dir.mkdir()
        design_docs = [
            "01_SYSTEM_ARCHITECTURE.md",
            "02_DATABASE_SCHEMA_DESIGN.md",
            "03_API_DESIGN_SPECIFICATION.md",
            "04_UI_UX_DESIGN.md"
        ]
        for doc in design_docs:
            # Add endpoints for API spec
            content = f"# {doc}\n\nComplete content for {doc}\n"
            if "API" in doc:
                content += "\n## Endpoints\n- GET /api/users\n- POST /api/users\n"
            (design_dir / doc).write_text(content)

        # Implementation - Backend
        backend_dir = self.workflow_dir / "implementation" / "backend" / "src"
        backend_dir.mkdir(parents=True)

        # Models
        models_dir = backend_dir / "models"
        models_dir.mkdir()
        for i in range(5):
            (models_dir / f"Model{i}.ts").write_text(f"export class Model{i} {{}}")

        # Services
        services_dir = backend_dir / "services"
        services_dir.mkdir()
        for i in range(5):
            (services_dir / f"Service{i}.ts").write_text(f"export class Service{i} {{}}")

        # Routes
        routes_dir = backend_dir / "routes"
        routes_dir.mkdir()
        for i in range(5):
            (routes_dir / f"route{i}.routes.ts").write_text(f"export const router{i} = {{}}")

        # Controllers
        controllers_dir = backend_dir / "controllers"
        controllers_dir.mkdir()
        for i in range(5):
            (controllers_dir / f"Controller{i}.ts").write_text(f"export class Controller{i} {{}}")

        # Server with route imports
        server_content = """
import express from 'express';
import router0 from './routes/route0.routes';
import router1 from './routes/route1.routes';

const app = express();
app.use('/api', router0);
app.use('/api', router1);
"""
        (backend_dir / "server.ts").write_text(server_content)

        # Implementation - Frontend
        frontend_dir = self.workflow_dir / "implementation" / "frontend" / "src"
        frontend_dir.mkdir(parents=True)

        # Components
        components_dir = frontend_dir / "components"
        components_dir.mkdir()
        for i in range(10):
            (components_dir / f"Component{i}.tsx").write_text(f"export const Component{i} = () => {{}}")

        # Pages
        pages_dir = frontend_dir / "pages"
        pages_dir.mkdir()
        for i in range(5):
            (pages_dir / f"Page{i}.tsx").write_text(f"export const Page{i} = () => {{}}")

        # App
        (frontend_dir / "App.tsx").write_text("export const App = () => {}")
        (frontend_dir / "index.tsx").write_text("import App from './App';")

        # Package files with complete metadata
        backend_package = {
            "name": "backend",
            "version": "1.0.0",
            "description": "Backend API",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "test": "jest",
                "dev": "nodemon server.js"
            },
            "dependencies": {
                "express": "^4.18.0"
            }
        }
        frontend_package = {
            "name": "frontend",
            "version": "1.0.0",
            "description": "Frontend Application",
            "scripts": {
                "build": "react-scripts build",
                "start": "react-scripts start",
                "test": "react-scripts test"
            },
            "dependencies": {
                "react": "^18.0.0"
            }
        }
        import json
        (self.workflow_dir / "implementation" / "backend" / "package.json").write_text(json.dumps(backend_package, indent=2))
        (self.workflow_dir / "implementation" / "frontend" / "package.json").write_text(json.dumps(frontend_package, indent=2))

        # Testing
        testing_dir = self.workflow_dir / "testing"
        testing_dir.mkdir()
        (testing_dir / "unit_tests.test.ts").write_text("describe('Unit Tests', () => { it('works', () => {}) })")
        (testing_dir / "integration_tests.test.ts").write_text("describe('Integration Tests', () => { it('works', () => {}) })")

        # Deployment
        deployment_dir = self.workflow_dir / "deployment"
        deployment_dir.mkdir()
        docker_dir = deployment_dir / "docker"
        docker_dir.mkdir()

        # Docker Compose
        compose_content = """version: '3.8'
services:
  backend:
    build: ../implementation/backend
    ports:
      - "3000:3000"
  frontend:
    build: ../implementation/frontend
    ports:
      - "3001:3001"
"""
        (deployment_dir / "docker-compose.yml").write_text(compose_content)

        # Dockerfiles
        (docker_dir / "Dockerfile.backend").write_text("FROM node:18\nWORKDIR /app\nCOPY . .\nCMD ['npm', 'start']")
        (docker_dir / "Dockerfile.frontend").write_text("FROM node:18\nWORKDIR /app\nCOPY . .\nCMD ['npm', 'start']")

    def test_complete_workflow_validation(self):
        """Test validation of complete workflow"""
        self._create_complete_workflow()

        # Run all validators
        validator = WorkflowValidator(self.workflow_dir)
        reports = validator.validate_all()

        # Requirements and design should pass
        assert reports["requirements"].overall_status == "passed"
        assert reports["design"].overall_status == "passed"

        # Implementation should have high completion
        gap_detector = WorkflowGapDetector(self.workflow_dir)
        gap_report = gap_detector.detect_gaps()

        # Should have reasonable completion (not complete due to missing middleware etc)
        assert gap_report.estimated_completion_percentage > 0.7  # At least 70%
        assert gap_report.total_gaps < 20  # Not too many gaps

        # Completeness checker
        checker = ImplementationCompletenessChecker(self.workflow_dir)
        progress = checker.check_implementation_progress()

        # Should have high overall completion even if not all sub-phases are complete
        assert progress.overall_completion > 0.7  # At least 70% complete
        # Some sub-phases should be completed
        completed_phases = [sp for sp, prog in progress.sub_phase_progress.items() if prog.status == 'completed']
        assert len(completed_phases) > 0


# Test Runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
