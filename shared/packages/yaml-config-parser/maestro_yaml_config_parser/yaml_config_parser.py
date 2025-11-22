#!/usr/bin/env python3
"""
YAML Configuration Parser for Quality Fabric
Transforms simple YAML configurations into TestExecutionPlan objects
"""

import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from services.core.test_orchestrator import (
    TestExecutionPlan,
    TestCategory
)

logger = logging.getLogger(__name__)


@dataclass
class ProjectConfig:
    """Project configuration from YAML"""
    name: str
    repo: Optional[str] = None
    branch: Optional[str] = "main"
    language: Optional[str] = None
    framework: Optional[str] = None


@dataclass
class QualityGateConfig:
    """Quality gate configuration"""
    coverage: Optional[float] = None
    success_rate: Optional[float] = None
    pylint_score: Optional[float] = None
    max_duration: Optional[int] = None
    security_score: Optional[float] = None


@dataclass
class MockServiceConfig:
    """Mock service configuration"""
    name: str
    type: str  # wiremock, mountebank, custom
    port: Optional[int] = None
    stubs: Optional[str] = None
    record_from: Optional[str] = None
    replay_delay: Optional[str] = None


@dataclass
class TestSuiteConfig:
    """Test suite configuration from YAML"""
    name: str
    categories: List[str]
    config: Dict[str, Any]
    quality_gates: Optional[QualityGateConfig] = None
    parallel: bool = True
    timeout: str = "30min"
    fail_fast: bool = False
    retry_count: int = 1


class YAMLConfigParser:
    """Parse YAML test configuration files"""

    SCHEMA_VERSION = "1.0"

    # Valid test categories
    VALID_CATEGORIES = {
        "unit": TestCategory.UNIT,
        "integration": TestCategory.INTEGRATION,
        "functional": TestCategory.FUNCTIONAL,
        "api": TestCategory.API,
        "frontend": TestCategory.FRONTEND,
        "performance": TestCategory.PERFORMANCE,
        "security": TestCategory.SECURITY,
        "visual": TestCategory.VISUAL,
        "database": TestCategory.DATABASE,
        "deployment": TestCategory.DEPLOYMENT,
        "mobile": TestCategory.MOBILE,
        "workflows": TestCategory.WORKFLOWS,
        "chaos": TestCategory.CHAOS,
        "compliance": TestCategory.COMPLIANCE
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_file(self, yaml_path: str) -> Dict[str, Any]:
        """Parse YAML file into configuration dict"""
        try:
            path = Path(yaml_path)
            if not path.exists():
                raise FileNotFoundError(f"YAML config not found: {yaml_path}")

            with open(path, 'r') as f:
                config = yaml.safe_load(f)

            if not config:
                raise ValueError("Empty YAML configuration")

            # Validate schema version
            version = config.get('version', '1.0')
            if version != self.SCHEMA_VERSION:
                self.logger.warning(f"Schema version mismatch: {version} != {self.SCHEMA_VERSION}")

            return config

        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error: {e}")
            raise ValueError(f"Invalid YAML syntax: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing YAML: {e}")
            raise

    def parse_string(self, yaml_content: str) -> Dict[str, Any]:
        """Parse YAML string into configuration dict"""
        try:
            config = yaml.safe_load(yaml_content)
            if not config:
                raise ValueError("Empty YAML configuration")
            return config
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error: {e}")
            raise ValueError(f"Invalid YAML syntax: {e}")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure"""
        errors = []

        # Check required top-level keys
        if 'project' not in config:
            errors.append("Missing required 'project' section")

        if 'test_suites' not in config:
            errors.append("Missing required 'test_suites' section")

        # Validate project section
        if 'project' in config:
            project = config['project']
            if not isinstance(project, dict):
                errors.append("'project' must be a dictionary")
            elif 'name' not in project:
                errors.append("'project.name' is required")

        # Validate test_suites section
        if 'test_suites' in config:
            test_suites = config['test_suites']
            if not isinstance(test_suites, list):
                errors.append("'test_suites' must be a list")
            elif len(test_suites) == 0:
                errors.append("'test_suites' cannot be empty")
            else:
                for idx, suite in enumerate(test_suites):
                    if not isinstance(suite, dict):
                        errors.append(f"test_suites[{idx}] must be a dictionary")
                        continue

                    if 'name' not in suite:
                        errors.append(f"test_suites[{idx}].name is required")

                    if 'categories' not in suite:
                        errors.append(f"test_suites[{idx}].categories is required")
                    elif not isinstance(suite['categories'], list):
                        errors.append(f"test_suites[{idx}].categories must be a list")
                    else:
                        # Validate category names
                        for cat in suite['categories']:
                            if cat not in self.VALID_CATEGORIES:
                                errors.append(
                                    f"Invalid category '{cat}' in test_suites[{idx}]. "
                                    f"Valid categories: {list(self.VALID_CATEGORIES.keys())}"
                                )

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        return True

    def parse_project_config(self, config: Dict[str, Any]) -> ProjectConfig:
        """Parse project configuration section"""
        project = config.get('project', {})

        return ProjectConfig(
            name=project.get('name', 'unknown'),
            repo=project.get('repo'),
            branch=project.get('branch', 'main'),
            language=project.get('language'),
            framework=project.get('framework')
        )

    def parse_quality_gates(self, gates_config: Dict[str, Any]) -> QualityGateConfig:
        """Parse quality gates configuration"""
        return QualityGateConfig(
            coverage=gates_config.get('coverage'),
            success_rate=gates_config.get('success_rate'),
            pylint_score=gates_config.get('pylint_score'),
            max_duration=gates_config.get('max_duration'),
            security_score=gates_config.get('security_score')
        )

    def parse_timeout(self, timeout_str: str) -> int:
        """Parse timeout string (e.g., '30min', '2h') into minutes"""
        timeout_str = timeout_str.lower().strip()

        if timeout_str.endswith('min'):
            return int(timeout_str[:-3])
        elif timeout_str.endswith('m'):
            return int(timeout_str[:-1])
        elif timeout_str.endswith('hour') or timeout_str.endswith('hours'):
            return int(timeout_str.split('hour')[0]) * 60
        elif timeout_str.endswith('h'):
            return int(timeout_str[:-1]) * 60
        else:
            # Assume minutes if no unit
            return int(timeout_str)

    def parse_test_suite(self, suite_config: Dict[str, Any]) -> TestSuiteConfig:
        """Parse individual test suite configuration"""
        # Parse categories
        category_names = suite_config.get('categories', [])

        # Parse quality gates if present
        quality_gates = None
        if 'quality_gates' in suite_config:
            quality_gates = self.parse_quality_gates(suite_config['quality_gates'])

        # Parse timeout
        timeout_str = suite_config.get('timeout', '30min')
        timeout_minutes = self.parse_timeout(timeout_str)

        return TestSuiteConfig(
            name=suite_config.get('name', 'unnamed'),
            categories=category_names,
            config=suite_config.get('config', {}),
            quality_gates=quality_gates,
            parallel=suite_config.get('parallel', True),
            timeout=timeout_str,
            fail_fast=suite_config.get('fail_fast', False),
            retry_count=suite_config.get('retry_count', 1)
        )

    def convert_to_execution_plan(
        self,
        suite_config: TestSuiteConfig,
        project_config: ProjectConfig
    ) -> TestExecutionPlan:
        """Convert TestSuiteConfig to TestExecutionPlan"""

        # Map category names to TestCategory enums
        categories = []
        for cat_name in suite_config.categories:
            if cat_name in self.VALID_CATEGORIES:
                categories.append(self.VALID_CATEGORIES[cat_name])
            else:
                self.logger.warning(f"Unknown category: {cat_name}, skipping")

        if not categories:
            raise ValueError(f"No valid categories found for test suite '{suite_config.name}'")

        # Parse timeout
        timeout_minutes = self.parse_timeout(suite_config.timeout)

        # Create execution plan
        return TestExecutionPlan(
            plan_id=f"{project_config.name}_{suite_config.name}",
            name=suite_config.name,
            description=f"Test suite '{suite_config.name}' for project '{project_config.name}'",
            categories=categories,
            parallel_execution=suite_config.parallel,
            fail_fast=suite_config.fail_fast,
            timeout_minutes=timeout_minutes,
            retry_count=suite_config.retry_count,
            custom_config=suite_config.config
        )

    def parse_mock_services(self, config: Dict[str, Any]) -> List[MockServiceConfig]:
        """Parse mock services configuration"""
        mocking_config = config.get('mocking', {})

        if not mocking_config.get('enabled', False):
            return []

        services = mocking_config.get('services', [])
        mock_configs = []

        for service in services:
            mock_configs.append(MockServiceConfig(
                name=service.get('name', 'unknown'),
                type=service.get('type', 'wiremock'),
                port=service.get('port'),
                stubs=service.get('stubs'),
                record_from=service.get('record_from'),
                replay_delay=service.get('replay_delay')
            ))

        return mock_configs

    def parse_config_to_plans(self, yaml_path: str) -> List[TestExecutionPlan]:
        """
        Parse YAML file and convert all test suites to execution plans

        Returns:
            List of TestExecutionPlan objects, one for each test suite
        """
        # Parse YAML file
        config = self.parse_file(yaml_path)

        # Validate configuration
        self.validate_config(config)

        # Parse project configuration
        project_config = self.parse_project_config(config)

        # Parse test suites
        test_suites = config.get('test_suites', [])
        execution_plans = []

        for suite_data in test_suites:
            try:
                suite_config = self.parse_test_suite(suite_data)
                execution_plan = self.convert_to_execution_plan(suite_config, project_config)
                execution_plans.append(execution_plan)
                self.logger.info(f"Created execution plan: {execution_plan.plan_id}")
            except Exception as e:
                self.logger.error(f"Failed to parse test suite '{suite_data.get('name', 'unknown')}': {e}")
                raise

        return execution_plans

    def get_suite_by_name(self, yaml_path: str, suite_name: str) -> Optional[TestExecutionPlan]:
        """Get a specific test suite by name"""
        plans = self.parse_config_to_plans(yaml_path)

        for plan in plans:
            if plan.name == suite_name:
                return plan

        return None


# Convenience function for quick parsing
def parse_quality_fabric_yaml(yaml_path: str) -> List[TestExecutionPlan]:
    """
    Quick parse function for .quality-fabric.yaml files

    Args:
        yaml_path: Path to .quality-fabric.yaml file

    Returns:
        List of TestExecutionPlan objects
    """
    parser = YAMLConfigParser()
    return parser.parse_config_to_plans(yaml_path)