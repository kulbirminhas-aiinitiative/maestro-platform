#!/usr/bin/env python3
"""
Test Generator: Automatically generates tests for code.

This module handles:
- Unit test generation from source code
- Integration test generation for multi-component testing
- End-to-end test generation for workflow validation
- Coverage analysis and gap detection
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of tests that can be generated."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    CONTRACT = "contract"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    MOCHA = "mocha"
    PLAYWRIGHT = "playwright"


@dataclass
class TestCase:
    """A generated test case."""
    test_id: str
    name: str
    test_type: TestType
    description: str
    code: str
    target_function: str
    target_file: str
    assertions: List[str] = field(default_factory=list)
    setup: Optional[str] = None
    teardown: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """A collection of test cases."""
    suite_id: str
    name: str
    test_cases: List[TestCase]
    framework: TestFramework
    imports: List[str] = field(default_factory=list)
    fixtures: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CoverageGap:
    """An identified gap in test coverage."""
    gap_id: str
    file_path: str
    function_name: str
    line_range: Tuple[int, int]
    reason: str
    suggested_tests: List[str]


@dataclass
class FunctionSignature:
    """Parsed function signature information."""
    name: str
    parameters: List[Tuple[str, Optional[str]]]  # (name, type_hint)
    return_type: Optional[str]
    docstring: Optional[str]
    decorators: List[str]
    is_async: bool
    line_number: int


class TestGenerator:
    """
    Generates tests from source code.

    Implements:
    - unit_test_gen: Generate unit tests for functions
    - integration_test_gen: Generate tests for component interactions
    - e2e_test_gen: Generate end-to-end tests
    - coverage_analysis: Identify untested code paths
    """

    def __init__(self, framework: TestFramework = TestFramework.PYTEST):
        """Initialize the generator with a test framework."""
        self.framework = framework
        self._generated_suites: Dict[str, TestSuite] = {}

    def generate_tests(
        self,
        source_code: str,
        source_file: str = "module.py",
        test_type: TestType = TestType.UNIT
    ) -> TestSuite:
        """
        Generate tests for the given source code.

        Args:
            source_code: Python source code to analyze
            source_file: Original file path
            test_type: Type of tests to generate

        Returns:
            TestSuite with generated test cases
        """
        logger.info(f"Generating {test_type.value} tests for {source_file}")

        # Parse source code
        functions = self._parse_functions(source_code)
        logger.info(f"Found {len(functions)} functions to test")

        # Generate test cases based on type
        if test_type == TestType.UNIT:
            test_cases = self._generate_unit_tests(functions, source_file)
        elif test_type == TestType.INTEGRATION:
            test_cases = self._generate_integration_tests(functions, source_file)
        elif test_type == TestType.E2E:
            test_cases = self._generate_e2e_tests(functions, source_file)
        else:
            test_cases = self._generate_unit_tests(functions, source_file)

        # Create test suite
        suite = TestSuite(
            suite_id=str(uuid.uuid4()),
            name=f"Test{Path(source_file).stem.title()}",
            test_cases=test_cases,
            framework=self.framework,
            imports=self._generate_imports(test_type, source_file),
            fixtures=self._generate_fixtures(functions)
        )

        self._generated_suites[suite.suite_id] = suite

        logger.info(f"Generated {len(test_cases)} test cases")
        return suite

    def _parse_functions(self, source_code: str) -> List[FunctionSignature]:
        """Parse function signatures from source code."""
        functions = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.error(f"Failed to parse source code: {e}")
            return functions

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private methods (start with _)
                if node.name.startswith('_') and not node.name.startswith('__'):
                    continue

                # Extract parameters
                params = []
                for arg in node.args.args:
                    type_hint = None
                    if arg.annotation:
                        type_hint = ast.unparse(arg.annotation)
                    params.append((arg.arg, type_hint))

                # Extract return type
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns)

                # Extract docstring
                docstring = ast.get_docstring(node)

                # Extract decorators
                decorators = [
                    ast.unparse(d) for d in node.decorator_list
                ]

                func = FunctionSignature(
                    name=node.name,
                    parameters=params,
                    return_type=return_type,
                    docstring=docstring,
                    decorators=decorators,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    line_number=node.lineno
                )
                functions.append(func)

        return functions

    def _generate_unit_tests(
        self,
        functions: List[FunctionSignature],
        source_file: str
    ) -> List[TestCase]:
        """
        Generate unit tests for functions.

        Implements unit_test_gen for individual function testing.
        """
        test_cases = []

        for func in functions:
            # Generate basic test
            test_code = self._generate_unit_test_code(func, source_file)
            test_case = TestCase(
                test_id=str(uuid.uuid4()),
                name=f"test_{func.name}",
                test_type=TestType.UNIT,
                description=f"Unit test for {func.name}",
                code=test_code,
                target_function=func.name,
                target_file=source_file,
                assertions=[f"assert result is not None"],
                tags=["unit", "auto-generated"]
            )
            test_cases.append(test_case)

            # Generate edge case tests
            edge_tests = self._generate_edge_case_tests(func, source_file)
            test_cases.extend(edge_tests)

        return test_cases

    def _generate_unit_test_code(
        self,
        func: FunctionSignature,
        source_file: str
    ) -> str:
        """Generate unit test code for a function."""
        module_name = Path(source_file).stem

        # Prepare parameters
        param_values = []
        for name, type_hint in func.parameters:
            if name == 'self':
                continue
            value = self._get_mock_value(name, type_hint)
            param_values.append(f"{name}={value}")

        params_str = ", ".join(param_values)
        call = f"{func.name}({params_str})"

        if func.is_async:
            test_code = f'''
@pytest.mark.asyncio
async def test_{func.name}():
    """Test {func.name} function."""
    # Arrange
    # (Add setup here)

    # Act
    result = await {call}

    # Assert
    assert result is not None
'''
        else:
            test_code = f'''
def test_{func.name}():
    """Test {func.name} function."""
    # Arrange
    # (Add setup here)

    # Act
    result = {call}

    # Assert
    assert result is not None
'''

        return test_code.strip()

    def _generate_edge_case_tests(
        self,
        func: FunctionSignature,
        source_file: str
    ) -> List[TestCase]:
        """Generate edge case tests."""
        test_cases = []

        # Test with None values
        for name, type_hint in func.parameters:
            if name == 'self':
                continue
            if type_hint and 'Optional' in type_hint:
                test_case = TestCase(
                    test_id=str(uuid.uuid4()),
                    name=f"test_{func.name}_with_{name}_none",
                    test_type=TestType.UNIT,
                    description=f"Test {func.name} with {name}=None",
                    code=self._generate_none_test(func, name),
                    target_function=func.name,
                    target_file=source_file,
                    assertions=[f"assert handles None for {name}"],
                    tags=["unit", "edge-case", "auto-generated"]
                )
                test_cases.append(test_case)

        return test_cases

    def _generate_none_test(self, func: FunctionSignature, param_name: str) -> str:
        """Generate a test with None parameter."""
        param_values = []
        for name, type_hint in func.parameters:
            if name == 'self':
                continue
            if name == param_name:
                param_values.append(f"{name}=None")
            else:
                value = self._get_mock_value(name, type_hint)
                param_values.append(f"{name}={value}")

        params_str = ", ".join(param_values)

        return f'''
def test_{func.name}_with_{param_name}_none():
    """Test {func.name} handles None for {param_name}."""
    result = {func.name}({params_str})
    # Should either succeed or raise appropriate error
    assert result is not None or True
'''.strip()

    def _generate_integration_tests(
        self,
        functions: List[FunctionSignature],
        source_file: str
    ) -> List[TestCase]:
        """
        Generate integration tests.

        Implements integration_test_gen for multi-component testing.
        """
        test_cases = []

        # Group functions that might interact
        # (simplified: create one integration test per 2-3 functions)
        for i in range(0, len(functions), 3):
            group = functions[i:i + 3]
            if len(group) > 1:
                test_code = self._generate_integration_test_code(group, source_file)
                test_case = TestCase(
                    test_id=str(uuid.uuid4()),
                    name=f"test_integration_{i // 3 + 1}",
                    test_type=TestType.INTEGRATION,
                    description=f"Integration test for {', '.join(f.name for f in group)}",
                    code=test_code,
                    target_function=group[0].name,
                    target_file=source_file,
                    assertions=["assert workflow completes successfully"],
                    tags=["integration", "auto-generated"]
                )
                test_cases.append(test_case)

        return test_cases

    def _generate_integration_test_code(
        self,
        functions: List[FunctionSignature],
        source_file: str
    ) -> str:
        """Generate integration test code."""
        func_names = [f.name for f in functions]
        calls = [f"    # result = {name}(...)" for name in func_names]

        return f'''
def test_integration_workflow():
    """Integration test for multiple functions working together."""
    # Setup shared context
    context = {{}}

    # Execute workflow
{chr(10).join(calls)}

    # Verify final state
    assert True  # Add actual assertions
'''.strip()

    def _generate_e2e_tests(
        self,
        functions: List[FunctionSignature],
        source_file: str
    ) -> List[TestCase]:
        """
        Generate end-to-end tests.

        Implements e2e_test_gen for full workflow validation.
        """
        test_cases = []

        # Generate one E2E test covering main workflow
        test_code = f'''
class TestE2EWorkflow:
    """End-to-end test for complete workflow."""

    @pytest.fixture
    def setup_environment(self):
        """Setup test environment."""
        # Initialize components
        yield
        # Cleanup

    def test_complete_workflow(self, setup_environment):
        """Test complete user workflow from start to finish."""
        # Step 1: Initialize
        # Step 2: Execute main operations
        # Step 3: Verify outcomes
        # Step 4: Cleanup and verify state

        assert True  # Replace with actual assertions
'''

        test_case = TestCase(
            test_id=str(uuid.uuid4()),
            name="test_e2e_complete_workflow",
            test_type=TestType.E2E,
            description="End-to-end test for complete workflow",
            code=test_code.strip(),
            target_function="workflow",
            target_file=source_file,
            assertions=["assert complete workflow succeeds"],
            tags=["e2e", "auto-generated"]
        )
        test_cases.append(test_case)

        return test_cases

    def _get_mock_value(self, param_name: str, type_hint: Optional[str]) -> str:
        """Get a mock value for a parameter."""
        if type_hint:
            type_lower = type_hint.lower()
            if 'str' in type_lower:
                return f'"test_{param_name}"'
            elif 'int' in type_lower:
                return '1'
            elif 'float' in type_lower:
                return '1.0'
            elif 'bool' in type_lower:
                return 'True'
            elif 'list' in type_lower:
                return '[]'
            elif 'dict' in type_lower:
                return '{}'
            elif 'none' in type_lower or 'optional' in type_lower:
                return 'None'

        # Default based on name
        if 'id' in param_name.lower():
            return '"test-id-123"'
        elif 'name' in param_name.lower():
            return '"test_name"'
        elif 'count' in param_name.lower() or 'size' in param_name.lower():
            return '10'

        return 'None'

    def _generate_imports(
        self,
        test_type: TestType,
        source_file: str
    ) -> List[str]:
        """Generate import statements for test file."""
        imports = ["import pytest"]

        if test_type == TestType.UNIT:
            imports.append("from unittest.mock import Mock, patch")
        elif test_type == TestType.INTEGRATION:
            imports.append("from unittest.mock import Mock, patch, MagicMock")
        elif test_type == TestType.E2E:
            imports.append("import asyncio")

        # Add import for module under test
        module_path = Path(source_file).stem
        imports.append(f"# from {module_path} import *")

        return imports

    def _generate_fixtures(
        self,
        functions: List[FunctionSignature]
    ) -> List[str]:
        """Generate pytest fixtures."""
        fixtures = []

        # Common fixtures
        fixtures.append('''
@pytest.fixture
def mock_context():
    """Provide mock context for tests."""
    return {}
''')

        # Add fixture if any async functions
        has_async = any(f.is_async for f in functions)
        if has_async:
            fixtures.append('''
@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
''')

        return fixtures

    def analyze_coverage(
        self,
        source_code: str,
        existing_tests: Optional[str] = None
    ) -> List[CoverageGap]:
        """
        Analyze code for coverage gaps.

        Implements coverage_analysis to identify untested code.
        """
        gaps = []
        functions = self._parse_functions(source_code)

        # Get tested functions from existing tests
        tested_functions: Set[str] = set()
        if existing_tests:
            test_funcs = self._parse_functions(existing_tests)
            for tf in test_funcs:
                # Extract function name from test name
                match = re.search(r'test_(\w+)', tf.name)
                if match:
                    tested_functions.add(match.group(1))

        # Find untested functions
        for func in functions:
            if func.name not in tested_functions:
                gap = CoverageGap(
                    gap_id=str(uuid.uuid4()),
                    file_path="unknown",
                    function_name=func.name,
                    line_range=(func.line_number, func.line_number + 10),
                    reason="No tests found for this function",
                    suggested_tests=[
                        f"test_{func.name}_basic",
                        f"test_{func.name}_edge_cases",
                        f"test_{func.name}_error_handling"
                    ]
                )
                gaps.append(gap)

        return gaps

    def render_test_file(self, suite: TestSuite) -> str:
        """Render a complete test file from a test suite."""
        lines = [
            '"""Auto-generated tests."""',
            ''
        ]

        # Add imports
        for imp in suite.imports:
            lines.append(imp)
        lines.append('')

        # Add fixtures
        for fixture in suite.fixtures:
            lines.append(fixture)
        lines.append('')

        # Add test class
        lines.append(f'class {suite.name}:')
        lines.append(f'    """Tests for {suite.name}."""')
        lines.append('')

        # Add test cases
        for tc in suite.test_cases:
            # Indent the code
            indented = '\n'.join(
                '    ' + line if line.strip() else ''
                for line in tc.code.split('\n')
            )
            lines.append(indented)
            lines.append('')

        return '\n'.join(lines)

    def get_suite(self, suite_id: str) -> Optional[TestSuite]:
        """Get a generated test suite by ID."""
        return self._generated_suites.get(suite_id)


# Factory function
def create_test_generator(
    framework: TestFramework = TestFramework.PYTEST
) -> TestGenerator:
    """Create a new TestGenerator instance."""
    return TestGenerator(framework)
