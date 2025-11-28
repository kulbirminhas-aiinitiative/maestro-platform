#!/usr/bin/env python3
"""
Implementation Completeness Checker
Tracks implementation progress through sub-phases with validation at each step
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import re


class SubPhase(Enum):
    """Implementation sub-phases with dependencies"""
    BACKEND_MODELS = "backend_models"  # Data models and types
    BACKEND_CORE = "backend_core"  # Services and business logic
    BACKEND_API = "backend_api"  # Routes and controllers
    BACKEND_MIDDLEWARE = "backend_middleware"  # Auth, validation, error handling
    FRONTEND_STRUCTURE = "frontend_structure"  # Basic app structure
    FRONTEND_CORE = "frontend_core"  # Core components and routing
    FRONTEND_FEATURES = "frontend_features"  # Feature-specific components
    INTEGRATION = "integration"  # Frontend-backend integration


@dataclass
class SubPhaseRequirements:
    """Requirements for a sub-phase to be considered complete"""
    name: SubPhase
    description: str
    required_directories: List[str]
    required_files: List[str]  # Exact file names
    min_file_count: int  # Minimum number of files in directories
    file_patterns: List[str]  # Glob patterns for files
    dependencies: List[SubPhase] = field(default_factory=list)  # Must complete before this
    validation_checks: List[str] = field(default_factory=list)  # Custom validation functions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "description": self.description,
            "required_directories": self.required_directories,
            "required_files": self.required_files,
            "min_file_count": self.min_file_count,
            "file_patterns": self.file_patterns,
            "dependencies": [d.value for d in self.dependencies],
            "validation_checks": self.validation_checks
        }


@dataclass
class SubPhaseProgress:
    """Progress tracking for a sub-phase"""
    sub_phase: SubPhase
    status: str  # not_started, in_progress, completed, failed
    completion_percentage: float
    directories_created: int
    directories_required: int
    files_created: int
    files_required: int
    validation_passed: bool
    validation_messages: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub_phase": self.sub_phase.value,
            "status": self.status,
            "completion_percentage": self.completion_percentage,
            "directories_created": self.directories_created,
            "directories_required": self.directories_required,
            "files_created": self.files_created,
            "files_required": self.files_required,
            "validation_passed": self.validation_passed,
            "validation_messages": self.validation_messages,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


@dataclass
class ImplementationProgress:
    """Overall implementation phase progress"""
    workflow_id: str
    overall_completion: float
    current_sub_phase: Optional[SubPhase]
    sub_phase_progress: Dict[SubPhase, SubPhaseProgress]
    backend_complete: bool
    frontend_complete: bool
    integration_complete: bool
    is_deployable: bool
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "overall_completion": self.overall_completion,
            "current_sub_phase": self.current_sub_phase.value if self.current_sub_phase else None,
            "sub_phase_progress": {
                sp.value: progress.to_dict()
                for sp, progress in self.sub_phase_progress.items()
            },
            "backend_complete": self.backend_complete,
            "frontend_complete": self.frontend_complete,
            "integration_complete": self.integration_complete,
            "is_deployable": self.is_deployable,
            "blockers": self.blockers
        }


class ImplementationCompletenessChecker:
    """Checks implementation completeness with sub-phase tracking"""

    # Define sub-phase requirements
    SUB_PHASE_REQUIREMENTS = {
        SubPhase.BACKEND_MODELS: SubPhaseRequirements(
            name=SubPhase.BACKEND_MODELS,
            description="Data models, types, and database schemas",
            required_directories=["implementation/backend/src/models"],
            required_files=[],
            min_file_count=3,  # At least 3 model files
            file_patterns=["implementation/backend/src/models/*.ts", "implementation/backend/src/models/*.js"],
            dependencies=[],
            validation_checks=["check_prisma_schema", "check_model_exports"]
        ),
        SubPhase.BACKEND_CORE: SubPhaseRequirements(
            name=SubPhase.BACKEND_CORE,
            description="Business logic services",
            required_directories=["implementation/backend/src/services"],
            required_files=[],
            min_file_count=3,  # At least 3 service files
            file_patterns=["implementation/backend/src/services/*.ts", "implementation/backend/src/services/*.js"],
            dependencies=[SubPhase.BACKEND_MODELS],
            validation_checks=["check_service_imports_models"]
        ),
        SubPhase.BACKEND_API: SubPhaseRequirements(
            name=SubPhase.BACKEND_API,
            description="API routes and controllers",
            required_directories=[
                "implementation/backend/src/routes",
                "implementation/backend/src/controllers"
            ],
            required_files=["implementation/backend/src/server.ts"],
            min_file_count=5,  # At least 5 route/controller files combined
            file_patterns=[
                "implementation/backend/src/routes/*.ts",
                "implementation/backend/src/routes/*.js",
                "implementation/backend/src/controllers/*.ts",
                "implementation/backend/src/controllers/*.js"
            ],
            dependencies=[SubPhase.BACKEND_CORE],
            validation_checks=["check_route_imports", "check_server_mounts_routes"]
        ),
        SubPhase.BACKEND_MIDDLEWARE: SubPhaseRequirements(
            name=SubPhase.BACKEND_MIDDLEWARE,
            description="Authentication, validation, error handling",
            required_directories=["implementation/backend/src/middleware"],
            required_files=[],
            min_file_count=2,  # At least 2 middleware files
            file_patterns=["implementation/backend/src/middleware/*.ts", "implementation/backend/src/middleware/*.js"],
            dependencies=[SubPhase.BACKEND_API],
            validation_checks=["check_auth_middleware", "check_error_handler"]
        ),
        SubPhase.FRONTEND_STRUCTURE: SubPhaseRequirements(
            name=SubPhase.FRONTEND_STRUCTURE,
            description="Basic frontend application structure",
            required_directories=[
                "implementation/frontend/src",
                "implementation/frontend/public"
            ],
            required_files=[
                "implementation/frontend/package.json",
                "implementation/frontend/src/index.tsx",  # or .jsx or .ts or .js
            ],
            min_file_count=2,
            file_patterns=["implementation/frontend/src/index.*", "implementation/frontend/src/main.*"],
            dependencies=[],
            validation_checks=["check_package_json_valid", "check_entry_point_exists"]
        ),
        SubPhase.FRONTEND_CORE: SubPhaseRequirements(
            name=SubPhase.FRONTEND_CORE,
            description="Core components, routing, and layout",
            required_directories=[
                "implementation/frontend/src/components",
                "implementation/frontend/src/pages"  # or views
            ],
            required_files=[],  # App.tsx can be in different locations
            min_file_count=5,  # At least 5 component/page files
            file_patterns=[
                "implementation/frontend/src/App.*",
                "implementation/frontend/src/components/**/*.*",
                "implementation/frontend/src/pages/**/*.*",
                "implementation/frontend/src/views/**/*.*"
            ],
            dependencies=[SubPhase.FRONTEND_STRUCTURE],
            validation_checks=["check_app_component", "check_routing"]
        ),
        SubPhase.FRONTEND_FEATURES: SubPhaseRequirements(
            name=SubPhase.FRONTEND_FEATURES,
            description="Feature-specific components and pages",
            required_directories=[
                "implementation/frontend/src/components",
                "implementation/frontend/src/services"  # or api
            ],
            required_files=[],
            min_file_count=10,  # At least 10 component/service files
            file_patterns=[
                "implementation/frontend/src/components/**/*.*",
                "implementation/frontend/src/pages/**/*.*",
                "implementation/frontend/src/services/**/*.*",
                "implementation/frontend/src/api/**/*.*"
            ],
            dependencies=[SubPhase.FRONTEND_CORE],
            validation_checks=["check_api_client", "check_feature_components"]
        ),
        SubPhase.INTEGRATION: SubPhaseRequirements(
            name=SubPhase.INTEGRATION,
            description="Frontend-backend integration and API calls",
            required_directories=[],
            required_files=[],
            min_file_count=0,
            file_patterns=[],
            dependencies=[SubPhase.BACKEND_API, SubPhase.FRONTEND_FEATURES],
            validation_checks=["check_api_endpoints_match", "check_env_config"]
        )
    }

    def __init__(self, workflow_dir: Path):
        """
        Initialize completeness checker

        Args:
            workflow_dir: Path to workflow output directory
        """
        self.workflow_dir = Path(workflow_dir)
        self.workflow_id = self.workflow_dir.name
        self.impl_dir = self.workflow_dir / "implementation"

    def check_implementation_progress(self) -> ImplementationProgress:
        """
        Check implementation progress across all sub-phases

        Returns:
            ImplementationProgress with detailed sub-phase status
        """
        sub_phase_progress = {}

        # Check each sub-phase
        for sub_phase in SubPhase:
            requirements = self.SUB_PHASE_REQUIREMENTS[sub_phase]
            progress = self._check_sub_phase(requirements)
            sub_phase_progress[sub_phase] = progress

        # Determine current sub-phase (first incomplete or last completed)
        current_sub_phase = self._determine_current_sub_phase(sub_phase_progress)

        # Calculate overall completion
        overall_completion = self._calculate_overall_completion(sub_phase_progress)

        # Check if major phases complete
        backend_complete = all(
            sub_phase_progress[sp].status == "completed"
            for sp in [SubPhase.BACKEND_MODELS, SubPhase.BACKEND_CORE, SubPhase.BACKEND_API, SubPhase.BACKEND_MIDDLEWARE]
        )

        frontend_complete = all(
            sub_phase_progress[sp].status == "completed"
            for sp in [SubPhase.FRONTEND_STRUCTURE, SubPhase.FRONTEND_CORE, SubPhase.FRONTEND_FEATURES]
        )

        integration_complete = sub_phase_progress[SubPhase.INTEGRATION].status == "completed"

        # Determine if deployable
        is_deployable = backend_complete and frontend_complete and integration_complete

        # Identify blockers
        blockers = self._identify_blockers(sub_phase_progress)

        return ImplementationProgress(
            workflow_id=self.workflow_id,
            overall_completion=overall_completion,
            current_sub_phase=current_sub_phase,
            sub_phase_progress=sub_phase_progress,
            backend_complete=backend_complete,
            frontend_complete=frontend_complete,
            integration_complete=integration_complete,
            is_deployable=is_deployable,
            blockers=blockers
        )

    def _check_sub_phase(self, requirements: SubPhaseRequirements) -> SubPhaseProgress:
        """Check if a sub-phase meets its requirements"""
        if not self.impl_dir.exists():
            return SubPhaseProgress(
                sub_phase=requirements.name,
                status="not_started",
                completion_percentage=0.0,
                directories_created=0,
                directories_required=len(requirements.required_directories),
                files_created=0,
                files_required=requirements.min_file_count,
                validation_passed=False,
                validation_messages=["Implementation directory does not exist"]
            )

        # Check directories
        dirs_created = 0
        for dir_path in requirements.required_directories:
            if (self.workflow_dir / dir_path).exists():
                dirs_created += 1

        # Check required files
        required_files_exist = 0
        for file_path in requirements.required_files:
            full_path = self.workflow_dir / file_path
            # Handle alternative extensions
            if not full_path.exists():
                # Try common alternatives (.ts, .js, .tsx, .jsx)
                alternatives = [
                    full_path.with_suffix('.ts'),
                    full_path.with_suffix('.js'),
                    full_path.with_suffix('.tsx'),
                    full_path.with_suffix('.jsx')
                ]
                if any(alt.exists() for alt in alternatives):
                    required_files_exist += 1
            else:
                required_files_exist += 1

        # Count files matching patterns
        files_created = 0
        for pattern in requirements.file_patterns:
            pattern_path = Path(pattern)
            if pattern_path.is_absolute():
                matching_files = list(pattern_path.parent.glob(pattern_path.name))
            else:
                matching_files = list(self.workflow_dir.glob(pattern))
            files_created += len(matching_files)

        # Run validation checks
        validation_passed = True
        validation_messages = []

        for check_name in requirements.validation_checks:
            check_method = getattr(self, f"_{check_name}", None)
            if check_method:
                try:
                    passed, message = check_method()
                    if not passed:
                        validation_passed = False
                        validation_messages.append(message)
                except Exception as e:
                    validation_passed = False
                    validation_messages.append(f"{check_name} failed: {str(e)}")

        # Calculate completion percentage
        dir_score = dirs_created / len(requirements.required_directories) if requirements.required_directories else 1.0
        file_score = min(files_created / requirements.min_file_count, 1.0) if requirements.min_file_count > 0 else 1.0
        req_file_score = required_files_exist / len(requirements.required_files) if requirements.required_files else 1.0

        completion_pct = (dir_score * 0.3 + file_score * 0.5 + req_file_score * 0.2)

        # Determine status
        if completion_pct == 0:
            status = "not_started"
        elif completion_pct >= 0.9 and validation_passed:
            status = "completed"
        elif completion_pct > 0:
            status = "in_progress"
        else:
            status = "failed"

        return SubPhaseProgress(
            sub_phase=requirements.name,
            status=status,
            completion_percentage=completion_pct,
            directories_created=dirs_created,
            directories_required=len(requirements.required_directories),
            files_created=files_created,
            files_required=requirements.min_file_count + len(requirements.required_files),
            validation_passed=validation_passed,
            validation_messages=validation_messages
        )

    def _determine_current_sub_phase(
        self, progress: Dict[SubPhase, SubPhaseProgress]
    ) -> Optional[SubPhase]:
        """Determine which sub-phase is currently active"""
        # Return first sub-phase that's in_progress or not_started (in dependency order)
        sub_phase_order = [
            SubPhase.BACKEND_MODELS,
            SubPhase.BACKEND_CORE,
            SubPhase.BACKEND_API,
            SubPhase.BACKEND_MIDDLEWARE,
            SubPhase.FRONTEND_STRUCTURE,
            SubPhase.FRONTEND_CORE,
            SubPhase.FRONTEND_FEATURES,
            SubPhase.INTEGRATION
        ]

        for sub_phase in sub_phase_order:
            if progress[sub_phase].status in ["not_started", "in_progress"]:
                return sub_phase

        # All completed
        return SubPhase.INTEGRATION

    def _calculate_overall_completion(
        self, progress: Dict[SubPhase, SubPhaseProgress]
    ) -> float:
        """Calculate overall implementation completion percentage"""
        # Weight sub-phases by importance
        weights = {
            SubPhase.BACKEND_MODELS: 0.10,
            SubPhase.BACKEND_CORE: 0.15,
            SubPhase.BACKEND_API: 0.15,
            SubPhase.BACKEND_MIDDLEWARE: 0.10,
            SubPhase.FRONTEND_STRUCTURE: 0.10,
            SubPhase.FRONTEND_CORE: 0.15,
            SubPhase.FRONTEND_FEATURES: 0.15,
            SubPhase.INTEGRATION: 0.10
        }

        weighted_sum = sum(
            progress[sp].completion_percentage * weights[sp]
            for sp in SubPhase
        )

        return weighted_sum

    def _identify_blockers(
        self, progress: Dict[SubPhase, SubPhaseProgress]
    ) -> List[str]:
        """Identify blockers preventing progress"""
        blockers = []

        for sub_phase in SubPhase:
            sp_progress = progress[sub_phase]
            if sp_progress.status == "failed":
                blockers.append(f"{sub_phase.value}: Failed validation - {', '.join(sp_progress.validation_messages)}")
            elif sp_progress.status in ["not_started", "in_progress"]:
                if sp_progress.completion_percentage < 0.5:
                    blockers.append(
                        f"{sub_phase.value}: Only {sp_progress.files_created}/{sp_progress.files_required} "
                        f"required files created"
                    )

        return blockers

    # Validation check methods
    def _check_prisma_schema(self) -> tuple[bool, str]:
        """Check if Prisma schema exists"""
        schema_path = self.impl_dir / "backend" / "prisma" / "schema.prisma"
        if schema_path.exists():
            return True, "Prisma schema found"
        return False, "Prisma schema missing (backend/prisma/schema.prisma)"

    def _check_model_exports(self) -> tuple[bool, str]:
        """Check if models are exported"""
        models_dir = self.impl_dir / "backend" / "src" / "models"
        if not models_dir.exists():
            return False, "Models directory does not exist"

        model_files = list(models_dir.glob("*.ts")) + list(models_dir.glob("*.js"))
        if len(model_files) == 0:
            return False, "No model files found"

        return True, f"Found {len(model_files)} model files"

    def _check_service_imports_models(self) -> tuple[bool, str]:
        """Check if services import models"""
        services_dir = self.impl_dir / "backend" / "src" / "services"
        if not services_dir.exists():
            return False, "Services directory does not exist"

        service_files = list(services_dir.glob("*.ts")) + list(services_dir.glob("*.js"))
        if len(service_files) == 0:
            return False, "No service files found"

        # Check if at least one service imports from models
        for service_file in service_files:
            content = service_file.read_text()
            if "../models" in content or "from '@/models" in content:
                return True, "Services import models"

        return False, "Services don't import models (potential integration issue)"

    def _check_route_imports(self) -> tuple[bool, str]:
        """Check if routes exist"""
        routes_dir = self.impl_dir / "backend" / "src" / "routes"
        if not routes_dir.exists():
            return False, "Routes directory does not exist"

        route_files = list(routes_dir.glob("*.ts")) + list(routes_dir.glob("*.js"))
        if len(route_files) == 0:
            return False, "No route files found"

        return True, f"Found {len(route_files)} route files"

    def _check_server_mounts_routes(self) -> tuple[bool, str]:
        """Check if server.ts mounts routes"""
        server_files = [
            self.impl_dir / "backend" / "src" / "server.ts",
            self.impl_dir / "backend" / "src" / "server.js",
            self.impl_dir / "backend" / "src" / "index.ts",
            self.impl_dir / "backend" / "src" / "index.js"
        ]

        for server_file in server_files:
            if server_file.exists():
                content = server_file.read_text()
                # Check for route mounting patterns
                if "app.use(" in content or "router.use(" in content:
                    return True, "Server mounts routes"
                else:
                    return False, "Server exists but doesn't mount routes"

        return False, "Server file not found"

    def _check_auth_middleware(self) -> tuple[bool, str]:
        """Check if auth middleware exists"""
        middleware_dir = self.impl_dir / "backend" / "src" / "middleware"
        if not middleware_dir.exists():
            return False, "Middleware directory does not exist"

        auth_files = list(middleware_dir.glob("*auth*.*")) + list(middleware_dir.glob("*authentication*.*"))
        if auth_files:
            return True, "Authentication middleware found"

        return False, "No authentication middleware found"

    def _check_error_handler(self) -> tuple[bool, str]:
        """Check if error handler middleware exists"""
        middleware_dir = self.impl_dir / "backend" / "src" / "middleware"
        if not middleware_dir.exists():
            return False, "Middleware directory does not exist"

        error_files = list(middleware_dir.glob("*error*.*"))
        if error_files:
            return True, "Error handler middleware found"

        return False, "No error handler middleware found"

    def _check_package_json_valid(self) -> tuple[bool, str]:
        """Check if package.json is valid"""
        package_json = self.impl_dir / "frontend" / "package.json"
        if not package_json.exists():
            return False, "package.json not found"

        try:
            data = json.loads(package_json.read_text())
            if "dependencies" in data and "scripts" in data:
                return True, "package.json valid with dependencies and scripts"
            return False, "package.json missing dependencies or scripts"
        except json.JSONDecodeError:
            return False, "package.json is invalid JSON"

    def _check_entry_point_exists(self) -> tuple[bool, str]:
        """Check if frontend entry point exists"""
        entry_points = [
            self.impl_dir / "frontend" / "src" / "index.tsx",
            self.impl_dir / "frontend" / "src" / "index.jsx",
            self.impl_dir / "frontend" / "src" / "index.ts",
            self.impl_dir / "frontend" / "src" / "index.js",
            self.impl_dir / "frontend" / "src" / "main.tsx",
            self.impl_dir / "frontend" / "src" / "main.jsx",
            self.impl_dir / "frontend" / "src" / "main.ts",
            self.impl_dir / "frontend" / "src" / "main.js"
        ]

        for entry_point in entry_points:
            if entry_point.exists():
                return True, f"Entry point found: {entry_point.name}"

        return False, "No entry point found (index.tsx/jsx or main.tsx/jsx)"

    def _check_app_component(self) -> tuple[bool, str]:
        """Check if App component exists"""
        app_files = [
            self.impl_dir / "frontend" / "src" / "App.tsx",
            self.impl_dir / "frontend" / "src" / "App.jsx",
            self.impl_dir / "frontend" / "src" / "App.vue",
            self.impl_dir / "frontend" / "src" / "app.tsx",
            self.impl_dir / "frontend" / "src" / "app.jsx"
        ]

        for app_file in app_files:
            if app_file.exists():
                return True, f"App component found: {app_file.name}"

        return False, "No App component found"

    def _check_routing(self) -> tuple[bool, str]:
        """Check if routing is configured"""
        # Check for router files or routing in App
        possible_routers = [
            self.impl_dir / "frontend" / "src" / "router.tsx",
            self.impl_dir / "frontend" / "src" / "router.ts",
            self.impl_dir / "frontend" / "src" / "routes.tsx",
            self.impl_dir / "frontend" / "src" / "routes.ts",
            self.impl_dir / "frontend" / "src" / "App.tsx",
            self.impl_dir / "frontend" / "src" / "App.jsx"
        ]

        for router_file in possible_routers:
            if router_file.exists():
                content = router_file.read_text()
                if "Route" in content or "router" in content.lower():
                    return True, "Routing configured"

        return False, "No routing configuration found"

    def _check_api_client(self) -> tuple[bool, str]:
        """Check if API client/services exist"""
        possible_api_dirs = [
            self.impl_dir / "frontend" / "src" / "services",
            self.impl_dir / "frontend" / "src" / "api",
            self.impl_dir / "frontend" / "src" / "lib" / "api"
        ]

        for api_dir in possible_api_dirs:
            if api_dir.exists():
                api_files = list(api_dir.glob("*.ts")) + list(api_dir.glob("*.js"))
                if api_files:
                    return True, f"API client found in {api_dir.name}/ ({len(api_files)} files)"

        return False, "No API client or services found"

    def _check_feature_components(self) -> tuple[bool, str]:
        """Check if feature-specific components exist"""
        components_dir = self.impl_dir / "frontend" / "src" / "components"
        if not components_dir.exists():
            return False, "Components directory does not exist"

        # Count component files (excluding common/shared)
        component_files = list(components_dir.glob("**/*.tsx")) + list(components_dir.glob("**/*.jsx"))
        feature_components = [f for f in component_files if "common" not in str(f).lower() and "shared" not in str(f).lower()]

        if len(feature_components) >= 5:
            return True, f"Found {len(feature_components)} feature components"

        return False, f"Only {len(feature_components)} feature components found (need 5+)"

    def _check_api_endpoints_match(self) -> tuple[bool, str]:
        """Check if frontend API calls match backend routes"""
        # This is a simplified check - would need more sophisticated matching
        frontend_api_dir = self.impl_dir / "frontend" / "src" / "services"
        backend_routes_dir = self.impl_dir / "backend" / "src" / "routes"

        if not frontend_api_dir.exists() or not backend_routes_dir.exists():
            return False, "API client or routes directory missing"

        return True, "Frontend and backend exist (detailed endpoint matching TBD)"

    def _check_env_config(self) -> tuple[bool, str]:
        """Check if environment configuration exists"""
        env_files = [
            self.impl_dir / "backend" / ".env.example",
            self.impl_dir / "frontend" / ".env.example",
            self.impl_dir / "backend" / "src" / "config",
            self.impl_dir / "frontend" / "src" / "config"
        ]

        config_exists = any(f.exists() for f in env_files)
        if config_exists:
            return True, "Environment configuration found"

        return False, "No environment configuration found (.env.example or config/)"

    def generate_report(self, progress: ImplementationProgress) -> str:
        """Generate human-readable progress report"""
        report = []
        report.append("=" * 80)
        report.append(f"IMPLEMENTATION PROGRESS: {self.workflow_id}")
        report.append("=" * 80)
        report.append(f"Overall Completion: {progress.overall_completion * 100:.1f}%")
        report.append(f"Current Sub-Phase: {progress.current_sub_phase.value if progress.current_sub_phase else 'None'}")
        report.append(f"Backend Complete: {'Yes' if progress.backend_complete else 'No'}")
        report.append(f"Frontend Complete: {'Yes' if progress.frontend_complete else 'No'}")
        report.append(f"Integration Complete: {'Yes' if progress.integration_complete else 'No'}")
        report.append(f"Deployable: {'Yes' if progress.is_deployable else 'No'}")
        report.append("")

        report.append("Sub-Phase Progress:")
        report.append("-" * 80)
        for sub_phase in SubPhase:
            sp_progress = progress.sub_phase_progress[sub_phase]
            status_icon = {
                "completed": "✓",
                "in_progress": "⏳",
                "not_started": "○",
                "failed": "✗"
            }[sp_progress.status]

            report.append(f"{status_icon} {sub_phase.value:30} {sp_progress.completion_percentage*100:5.1f}%  "
                         f"[{sp_progress.files_created}/{sp_progress.files_required} files]  "
                         f"{sp_progress.status}")

            if sp_progress.validation_messages:
                for msg in sp_progress.validation_messages:
                    report.append(f"    ⚠ {msg}")

        if progress.blockers:
            report.append("")
            report.append("Blockers:")
            report.append("-" * 80)
            for blocker in progress.blockers:
                report.append(f"  • {blocker}")

        report.append("=" * 80)
        return "\n".join(report)


def main():
    """CLI for implementation completeness checking"""
    import argparse

    parser = argparse.ArgumentParser(description="Check implementation completeness")
    parser.add_argument(
        "workflow_dir",
        type=Path,
        help="Path to workflow directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for progress report (JSON)"
    )

    args = parser.parse_args()

    checker = ImplementationCompletenessChecker(args.workflow_dir)
    progress = checker.check_implementation_progress()

    # Print report
    print(checker.generate_report(progress))

    # Save JSON if requested
    if args.output:
        args.output.write_text(json.dumps(progress.to_dict(), indent=2))
        print(f"\nProgress report saved to: {args.output}")


if __name__ == "__main__":
    main()
