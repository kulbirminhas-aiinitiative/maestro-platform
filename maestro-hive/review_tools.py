"""
Review Tools - Analytical Scripts for Project Reviewer Persona

These tools provide quantitative metrics that the AI agent interprets.

DESIGN PRINCIPLE:
    Tools = Fast, deterministic data collection
    Agent = Intelligent interpretation and recommendations

Each tool returns structured data that the AI agent can analyze.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import re


@dataclass
class ProjectMetrics:
    """Quantitative project metrics"""
    total_files: int
    code_files: Dict[str, int]  # {extension: count}
    test_files: int
    doc_files: int
    config_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    directories: int


@dataclass
class ImplementationStatus:
    """Implementation completeness metrics"""
    backend_routes: Dict[str, Any]
    frontend_pages: Dict[str, Any]
    database_migrations: int
    api_endpoints_implemented: int
    api_endpoints_stubbed: int
    ui_components: int
    ui_pages_complete: int
    ui_pages_stubbed: int


@dataclass
class TestingMetrics:
    """Testing coverage metrics"""
    total_test_files: int
    unit_tests: int
    integration_tests: int
    e2e_tests: int
    coverage_percent: Optional[float]
    coverage_available: bool


@dataclass
class DevOpsMetrics:
    """DevOps configuration metrics"""
    has_docker: bool
    has_docker_compose: bool
    has_kubernetes: bool
    has_terraform: bool
    has_ci_cd: bool
    ci_cd_pipelines: List[str]
    deployment_configs: int


@dataclass
class DocumentationMetrics:
    """Documentation quality metrics"""
    readme_exists: bool
    readme_size: int
    total_md_files: int
    total_md_lines: int
    has_api_docs: bool
    has_architecture_docs: bool
    has_deployment_docs: bool


class ProjectMetricsAnalyzer:
    """Tool 1: Analyze project structure and file metrics"""

    @staticmethod
    def analyze(project_path: Path) -> ProjectMetrics:
        """Analyze project structure and count files"""
        code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go',
            '.rs', '.cpp', '.c', '.h', '.cs', '.rb', '.php'
        }
        test_patterns = {'test', 'spec', '__tests__'}
        doc_extensions = {'.md', '.txt', '.rst', '.adoc'}
        config_extensions = {
            '.json', '.yaml', '.yml', '.toml', '.ini',
            '.env', '.config', '.conf'
        }

        total_files = 0
        code_files = defaultdict(int)
        test_files = 0
        doc_files = 0
        config_files = 0
        directories = 0

        total_lines = 0
        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        for root, dirs, files in os.walk(project_path):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in {
                'node_modules', '.git', '__pycache__', 'venv',
                '.venv', 'dist', 'build', '.next', 'coverage'
            }]
            directories += len(dirs)

            for file in files:
                total_files += 1
                file_path = Path(root) / file
                ext = file_path.suffix.lower()

                # Categorize files
                if ext in code_extensions:
                    code_files[ext] += 1
                    if any(pattern in file.lower() for pattern in test_patterns):
                        test_files += 1

                if ext in doc_extensions:
                    doc_files += 1

                if ext in config_extensions or file.startswith('.'):
                    config_files += 1

                # Count lines (for text files only)
                if ext in code_extensions or ext in doc_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                total_lines += 1
                                stripped = line.strip()
                                if not stripped:
                                    blank_lines += 1
                                elif stripped.startswith(('#', '//', '/*', '*', '"""', "'''")):
                                    comment_lines += 1
                                else:
                                    code_lines += 1
                    except (UnicodeDecodeError, PermissionError):
                        pass

        return ProjectMetrics(
            total_files=total_files,
            code_files=dict(code_files),
            test_files=test_files,
            doc_files=doc_files,
            config_files=config_files,
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            directories=directories
        )


class ImplementationChecker:
    """Tool 2: Check implementation completeness"""

    @staticmethod
    def check(project_path: Path) -> ImplementationStatus:
        """Check how much is actually implemented vs stubbed"""
        backend_path = project_path / "backend" / "src"
        frontend_path = project_path / "frontend" / "src"

        # Check backend routes
        backend_routes = ImplementationChecker._check_backend_routes(backend_path)

        # Check frontend pages
        frontend_pages = ImplementationChecker._check_frontend_pages(frontend_path)

        # Count database migrations
        db_migrations = ImplementationChecker._count_migrations(project_path)

        # Count UI components
        ui_components = ImplementationChecker._count_ui_components(frontend_path)

        return ImplementationStatus(
            backend_routes=backend_routes,
            frontend_pages=frontend_pages,
            database_migrations=db_migrations,
            api_endpoints_implemented=backend_routes.get('implemented', 0),
            api_endpoints_stubbed=backend_routes.get('stubbed', 0),
            ui_components=ui_components,
            ui_pages_complete=frontend_pages.get('complete', 0),
            ui_pages_stubbed=frontend_pages.get('stubbed', 0)
        )

    @staticmethod
    def _check_backend_routes(backend_path: Path) -> Dict[str, Any]:
        """Check which routes are implemented vs commented out"""
        if not backend_path.exists():
            return {'implemented': 0, 'stubbed': 0, 'files': []}

        routes_path = backend_path / "routes"
        if not routes_path.exists():
            return {'implemented': 0, 'stubbed': 0, 'files': []}

        implemented = 0
        stubbed = 0
        route_files = []

        for route_file in routes_path.glob("*.ts"):
            content = route_file.read_text()
            route_files.append(str(route_file.name))

            # Count actual route definitions
            implemented += len(re.findall(r'router\.(get|post|put|delete|patch)', content))

            # Count commented routes (stubbed)
            stubbed += len(re.findall(r'//.*router\.use', content))

        return {
            'implemented': implemented,
            'stubbed': stubbed,
            'files': route_files
        }

    @staticmethod
    def _check_frontend_pages(frontend_path: Path) -> Dict[str, Any]:
        """Check which pages are complete vs stubbed"""
        if not frontend_path.exists():
            return {'complete': 0, 'stubbed': 0, 'files': []}

        pages_path = frontend_path / "pages"
        if not pages_path.exists():
            return {'complete': 0, 'stubbed': 0, 'files': []}

        complete = 0
        stubbed = 0
        page_files = []

        stub_indicators = [
            'coming soon',
            'under development',
            'placeholder',
            'todo',
            'not implemented'
        ]

        for page_file in pages_path.rglob("*.tsx"):
            content = page_file.read_text().lower()
            page_files.append(str(page_file.relative_to(frontend_path)))

            # Check if page is a stub
            if any(indicator in content for indicator in stub_indicators):
                stubbed += 1
            else:
                complete += 1

        return {
            'complete': complete,
            'stubbed': stubbed,
            'files': page_files
        }

    @staticmethod
    def _count_migrations(project_path: Path) -> int:
        """Count database migration files"""
        migration_paths = [
            project_path / "database" / "migrations",
            project_path / "backend" / "prisma" / "migrations",
            project_path / "migrations"
        ]

        total = 0
        for path in migration_paths:
            if path.exists():
                total += len(list(path.glob("*.sql"))) + len(list(path.glob("*.ts")))

        return total

    @staticmethod
    def _count_ui_components(frontend_path: Path) -> int:
        """Count UI components"""
        if not frontend_path.exists():
            return 0

        components_path = frontend_path / "components"
        if not components_path.exists():
            return 0

        return len(list(components_path.rglob("*.tsx")))


class TestCoverageAnalyzer:
    """Tool 3: Analyze test coverage"""

    @staticmethod
    def analyze(project_path: Path) -> TestingMetrics:
        """Analyze testing setup and coverage"""
        test_files = list(project_path.rglob("*.test.ts")) + \
                     list(project_path.rglob("*.test.tsx")) + \
                     list(project_path.rglob("*.spec.ts"))

        unit_tests = 0
        integration_tests = 0
        e2e_tests = 0

        for test_file in test_files:
            if 'integration' in str(test_file).lower():
                integration_tests += 1
            elif 'e2e' in str(test_file).lower() or 'playwright' in str(test_file).lower():
                e2e_tests += 1
            else:
                unit_tests += 1

        # Try to get coverage from coverage reports
        coverage_percent = None
        coverage_available = False

        coverage_paths = [
            project_path / "coverage" / "coverage-summary.json",
            project_path / "backend" / "coverage" / "coverage-summary.json",
            project_path / "frontend" / "coverage" / "coverage-summary.json"
        ]

        for coverage_path in coverage_paths:
            if coverage_path.exists():
                try:
                    with open(coverage_path) as f:
                        data = json.load(f)
                        coverage_percent = data.get('total', {}).get('lines', {}).get('pct')
                        coverage_available = True
                        break
                except Exception:
                    pass

        return TestingMetrics(
            total_test_files=len(test_files),
            unit_tests=unit_tests,
            integration_tests=integration_tests,
            e2e_tests=e2e_tests,
            coverage_percent=coverage_percent,
            coverage_available=coverage_available
        )


class DevOpsAnalyzer:
    """Tool 4: Analyze DevOps setup"""

    @staticmethod
    def analyze(project_path: Path) -> DevOpsMetrics:
        """Analyze DevOps configurations"""
        has_docker = (project_path / "Dockerfile").exists()
        has_docker_compose = (project_path / "docker-compose.yml").exists()
        has_kubernetes = (project_path / "k8s").exists()
        has_terraform = (project_path / "terraform").exists()

        # Check CI/CD
        ci_cd_pipelines = []
        github_actions = project_path / ".github" / "workflows"
        if github_actions.exists():
            ci_cd_pipelines = [f.name for f in github_actions.glob("*.yml")]
            has_ci_cd = len(ci_cd_pipelines) > 0
        else:
            has_ci_cd = False

        # Count deployment configs
        deployment_configs = 0
        if has_kubernetes:
            deployment_configs += len(list((project_path / "k8s").rglob("*.yaml")))
        if has_terraform:
            deployment_configs += len(list((project_path / "terraform").rglob("*.tf")))

        return DevOpsMetrics(
            has_docker=has_docker,
            has_docker_compose=has_docker_compose,
            has_kubernetes=has_kubernetes,
            has_terraform=has_terraform,
            has_ci_cd=has_ci_cd,
            ci_cd_pipelines=ci_cd_pipelines,
            deployment_configs=deployment_configs
        )


class DocumentationAnalyzer:
    """Tool 5: Analyze documentation"""

    @staticmethod
    def analyze(project_path: Path) -> DocumentationMetrics:
        """Analyze documentation quality"""
        readme = project_path / "README.md"
        readme_exists = readme.exists()
        readme_size = readme.stat().st_size if readme_exists else 0

        # Count all markdown files
        md_files = list(project_path.rglob("*.md"))
        total_md_files = len(md_files)

        # Count markdown lines
        total_md_lines = 0
        for md_file in md_files:
            try:
                total_md_lines += len(md_file.read_text().splitlines())
            except Exception:
                pass

        # Check for specific documentation
        has_api_docs = any(
            'api' in f.name.lower() for f in md_files
        )
        has_architecture_docs = any(
            'architecture' in f.name.lower() or 'design' in f.name.lower()
            for f in md_files
        )
        has_deployment_docs = any(
            'deploy' in f.name.lower() for f in md_files
        )

        return DocumentationMetrics(
            readme_exists=readme_exists,
            readme_size=readme_size,
            total_md_files=total_md_files,
            total_md_lines=total_md_lines,
            has_api_docs=has_api_docs,
            has_architecture_docs=has_architecture_docs,
            has_deployment_docs=has_deployment_docs
        )


class ProjectReviewTools:
    """Main tool orchestrator for Project Reviewer Persona"""

    @staticmethod
    def gather_all_metrics(project_path: str | Path) -> Dict[str, Any]:
        """
        Gather all quantitative metrics for a project.

        This is the main entry point the AI agent uses.
        Returns structured data for intelligent interpretation.
        """
        project_path = Path(project_path)

        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        metrics = {
            "project_path": str(project_path),
            "project_name": project_path.name,
            "metrics": asdict(ProjectMetricsAnalyzer.analyze(project_path)),
            "implementation": asdict(ImplementationChecker.check(project_path)),
            "testing": asdict(TestCoverageAnalyzer.analyze(project_path)),
            "devops": asdict(DevOpsAnalyzer.analyze(project_path)),
            "documentation": asdict(DocumentationAnalyzer.analyze(project_path))
        }

        return metrics

    @staticmethod
    def save_metrics(metrics: Dict[str, Any], output_path: Path):
        """Save metrics to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)

    @staticmethod
    def calculate_weighted_completion(metrics: Dict[str, Any]) -> float:
        """
        Calculate weighted completion percentage.

        Weights:
        - Documentation: 15%
        - Implementation: 40%
        - Testing: 20%
        - DevOps: 15%
        - Security: 10%
        """
        weights = {
            'documentation': 0.15,
            'implementation': 0.40,
            'testing': 0.20,
            'devops': 0.15,
            'security': 0.10
        }

        scores = {}

        # Documentation score
        doc = metrics['documentation']
        doc_score = 0
        if doc['readme_exists']:
            doc_score += 0.3
        if doc['has_api_docs']:
            doc_score += 0.3
        if doc['has_architecture_docs']:
            doc_score += 0.2
        if doc['has_deployment_docs']:
            doc_score += 0.2
        scores['documentation'] = min(doc_score, 1.0)

        # Implementation score
        impl = metrics['implementation']
        impl_endpoints = impl['api_endpoints_implemented']
        impl_stubbed = impl['api_endpoints_stubbed']
        total_endpoints = impl_endpoints + impl_stubbed
        endpoint_score = impl_endpoints / total_endpoints if total_endpoints > 0 else 0

        pages_complete = impl['ui_pages_complete']
        pages_stubbed = impl['ui_pages_stubbed']
        total_pages = pages_complete + pages_stubbed
        pages_score = pages_complete / total_pages if total_pages > 0 else 0

        scores['implementation'] = (endpoint_score + pages_score) / 2

        # Testing score
        test = metrics['testing']
        if test['coverage_available'] and test['coverage_percent']:
            scores['testing'] = min(test['coverage_percent'] / 100, 1.0)
        else:
            # Estimate based on test file count
            test_ratio = test['total_test_files'] / max(metrics['metrics']['code_files'].get('.ts', 1), 1)
            scores['testing'] = min(test_ratio, 1.0)

        # DevOps score
        devops = metrics['devops']
        devops_score = 0
        if devops['has_docker']:
            devops_score += 0.2
        if devops['has_docker_compose']:
            devops_score += 0.2
        if devops['has_kubernetes']:
            devops_score += 0.2
        if devops['has_terraform']:
            devops_score += 0.2
        if devops['has_ci_cd']:
            devops_score += 0.2
        scores['devops'] = devops_score

        # Security score (placeholder - would need security scanning)
        scores['security'] = 0.5  # Assume 50% without actual scanning

        # Calculate weighted total
        total_score = sum(scores[key] * weights[key] for key in weights.keys())
        return round(total_score * 100, 2)


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python review_tools.py <project_path>")
        sys.exit(1)

    project_path = Path(sys.argv[1])
    metrics = ProjectReviewTools.gather_all_metrics(project_path)

    print("\n" + "=" * 80)
    print("PROJECT METRICS SUMMARY")
    print("=" * 80 + "\n")

    print(f"Project: {metrics['project_name']}")
    print(f"Path: {metrics['project_path']}\n")

    print("Files:")
    print(f"  Total: {metrics['metrics']['total_files']}")
    print(f"  Code: {sum(metrics['metrics']['code_files'].values())}")
    print(f"  Tests: {metrics['metrics']['test_files']}")
    print(f"  Docs: {metrics['metrics']['doc_files']}\n")

    print("Implementation:")
    print(f"  API Endpoints: {metrics['implementation']['api_endpoints_implemented']} implemented, "
          f"{metrics['implementation']['api_endpoints_stubbed']} stubbed")
    print(f"  UI Pages: {metrics['implementation']['ui_pages_complete']} complete, "
          f"{metrics['implementation']['ui_pages_stubbed']} stubbed")
    print(f"  DB Migrations: {metrics['implementation']['database_migrations']}\n")

    print("Testing:")
    print(f"  Test Files: {metrics['testing']['total_test_files']}")
    print(f"  Unit: {metrics['testing']['unit_tests']}")
    print(f"  Integration: {metrics['testing']['integration_tests']}")
    print(f"  E2E: {metrics['testing']['e2e_tests']}\n")

    print("DevOps:")
    print(f"  Docker: {'✓' if metrics['devops']['has_docker'] else '✗'}")
    print(f"  Kubernetes: {'✓' if metrics['devops']['has_kubernetes'] else '✗'}")
    print(f"  Terraform: {'✓' if metrics['devops']['has_terraform'] else '✗'}")
    print(f"  CI/CD: {'✓' if metrics['devops']['has_ci_cd'] else '✗'}\n")

    completion = ProjectReviewTools.calculate_weighted_completion(metrics)
    print(f"Estimated Completion: {completion}%\n")

    # Save metrics
    output_file = project_path / "PROJECT_METRICS.json"
    ProjectReviewTools.save_metrics(metrics, output_file)
    print(f"Detailed metrics saved to: {output_file}")
