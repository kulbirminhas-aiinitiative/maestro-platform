"""
BDV Test Framework Detector
MD-2482 Task 1.1: Detect test framework from project structure.

Supports: pytest, jest, mocha, behave, pytest-bdd
"""

import os
import json
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    PYTEST_BDD = "pytest-bdd"
    JEST = "jest"
    MOCHA = "mocha"
    BEHAVE = "behave"
    UNKNOWN = "unknown"


@dataclass
class FrameworkConfig:
    """Configuration for detected test framework."""
    framework: TestFramework
    config_file: Optional[str] = None
    test_directory: str = "tests"
    test_pattern: str = "test_*.py"
    command: List[str] = None
    coverage_tool: Optional[str] = None
    
    def __post_init__(self):
        if self.command is None:
            self.command = self._default_command()
    
    def _default_command(self) -> List[str]:
        """Get default test command for framework."""
        commands = {
            TestFramework.PYTEST: ["pytest", "-v"],
            TestFramework.PYTEST_BDD: ["pytest", "-v", "--bdd"],
            TestFramework.JEST: ["npm", "test"],
            TestFramework.MOCHA: ["npm", "test"],
            TestFramework.BEHAVE: ["behave"],
        }
        return commands.get(self.framework, ["echo", "Unknown framework"])


class TestFrameworkDetector:
    """
    Detect test framework from project structure.
    
    AC-1: BDV executes tests against generated code using appropriate framework
    """
    
    # Framework detection patterns
    DETECTION_PATTERNS = {
        TestFramework.PYTEST: {
            "files": ["pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py"],
            "content_markers": ["[tool.pytest", "[pytest]", "pytest"],
            "test_patterns": ["test_*.py", "*_test.py"],
        },
        TestFramework.PYTEST_BDD: {
            "files": ["pytest.ini", "conftest.py"],
            "content_markers": ["pytest-bdd", "from pytest_bdd"],
            "directories": ["features"],
            "test_patterns": ["*.feature"],
        },
        TestFramework.JEST: {
            "files": ["jest.config.js", "jest.config.ts", "jest.config.json"],
            "package_markers": ["jest", "@jest/core"],
            "test_patterns": ["*.test.js", "*.test.ts", "*.spec.js", "*.spec.ts"],
        },
        TestFramework.MOCHA: {
            "files": [".mocharc.js", ".mocharc.json", ".mocharc.yaml"],
            "package_markers": ["mocha"],
            "test_patterns": ["*.test.js", "*.spec.js"],
        },
        TestFramework.BEHAVE: {
            "files": ["behave.ini", "setup.cfg"],
            "directories": ["features"],
            "content_markers": ["[behave]"],
            "test_patterns": ["*.feature"],
        },
    }
    
    def __init__(self, project_path: str):
        """
        Initialize detector with project path.
        
        Args:
            project_path: Path to project root
        """
        self.project_path = Path(project_path)
        self._package_json: Optional[Dict] = None
        self._pyproject: Optional[Dict] = None
    
    def detect(self) -> FrameworkConfig:
        """
        Detect the test framework used in the project.
        
        Returns:
            FrameworkConfig with detected framework and settings
        """
        logger.info(f"Detecting test framework in {self.project_path}")
        
        # Check each framework
        for framework, patterns in self.DETECTION_PATTERNS.items():
            if self._matches_patterns(patterns):
                config = self._build_config(framework, patterns)
                logger.info(f"Detected framework: {framework.value}")
                return config
        
        # Fallback detection
        return self._fallback_detection()
    
    def _matches_patterns(self, patterns: Dict[str, Any]) -> bool:
        """Check if project matches detection patterns."""
        # Check for config files
        if "files" in patterns:
            for file in patterns["files"]:
                if (self.project_path / file).exists():
                    return True
        
        # Check for directories
        if "directories" in patterns:
            for directory in patterns["directories"]:
                if (self.project_path / directory).is_dir():
                    return True
        
        # Check package.json for JS frameworks
        if "package_markers" in patterns:
            pkg = self._load_package_json()
            if pkg:
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                for marker in patterns["package_markers"]:
                    if marker in deps:
                        return True
        
        # Check content markers in config files
        if "content_markers" in patterns:
            for marker in patterns["content_markers"]:
                if self._find_content_marker(marker):
                    return True
        
        return False
    
    def _load_package_json(self) -> Optional[Dict]:
        """Load and cache package.json if present."""
        if self._package_json is not None:
            return self._package_json
        
        pkg_path = self.project_path / "package.json"
        if pkg_path.exists():
            try:
                with open(pkg_path) as f:
                    self._package_json = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._package_json = {}
        else:
            self._package_json = {}
        
        return self._package_json
    
    def _find_content_marker(self, marker: str) -> bool:
        """Search for content marker in common config files."""
        config_files = [
            "pyproject.toml", "setup.cfg", "pytest.ini",
            "package.json", "requirements.txt"
        ]
        
        for config_file in config_files:
            file_path = self.project_path / config_file
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    if marker in content:
                        return True
                except IOError:
                    continue
        
        return False
    
    def _build_config(self, framework: TestFramework, patterns: Dict) -> FrameworkConfig:
        """Build configuration for detected framework."""
        config = FrameworkConfig(framework=framework)
        
        # Set test directory
        if "directories" in patterns and patterns["directories"]:
            config.test_directory = patterns["directories"][0]
        elif framework in [TestFramework.PYTEST, TestFramework.PYTEST_BDD]:
            config.test_directory = "tests"
        
        # Set test pattern
        if "test_patterns" in patterns:
            config.test_pattern = patterns["test_patterns"][0]
        
        # Set coverage tool
        if framework in [TestFramework.PYTEST, TestFramework.PYTEST_BDD]:
            config.coverage_tool = "pytest-cov"
        elif framework in [TestFramework.JEST]:
            config.coverage_tool = "jest --coverage"
        
        # Find config file
        if "files" in patterns:
            for file in patterns["files"]:
                if (self.project_path / file).exists():
                    config.config_file = file
                    break
        
        return config
    
    def _fallback_detection(self) -> FrameworkConfig:
        """Fallback detection based on file structure."""
        # Check for Python test files
        if list(self.project_path.glob("**/test_*.py")):
            return FrameworkConfig(framework=TestFramework.PYTEST)
        
        # Check for JS test files
        if list(self.project_path.glob("**/*.test.js")) or \
           list(self.project_path.glob("**/*.spec.js")):
            return FrameworkConfig(framework=TestFramework.JEST)
        
        # Check for feature files
        if list(self.project_path.glob("**/*.feature")):
            return FrameworkConfig(framework=TestFramework.BEHAVE)
        
        logger.warning("Could not detect test framework")
        return FrameworkConfig(framework=TestFramework.UNKNOWN)
    
    def get_test_files(self, config: FrameworkConfig) -> List[Path]:
        """Get list of test files matching framework pattern."""
        test_dir = self.project_path / config.test_directory
        if not test_dir.exists():
            test_dir = self.project_path
        
        return list(test_dir.glob(f"**/{config.test_pattern}"))
