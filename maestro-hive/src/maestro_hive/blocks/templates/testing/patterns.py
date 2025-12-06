"""
Test Patterns - MD-2523

Common testing patterns for setup/teardown, mocking, assertions, and coverage.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class SetupTeardownPattern:
    """Pattern for test setup and teardown."""

    name: str
    description: str
    setup_code: str
    teardown_code: str
    scope: str = "function"  # function, class, module, session

    @staticmethod
    def get_patterns() -> List["SetupTeardownPattern"]:
        """Get all setup/teardown patterns."""
        return [
            SetupTeardownPattern(
                name="database_fixture",
                description="Database connection with automatic cleanup",
                scope="module",
                setup_code='''
@pytest.fixture(scope="module")
def database():
    """Database connection for tests."""
    # Setup: Create connection and tables
    db = Database(connection_string="sqlite:///:memory:")
    db.create_tables()
    db.seed_test_data()

    yield db

    # Teardown: Close connection
    db.drop_tables()
    db.close()
''',
                teardown_code="# Teardown handled in fixture via yield",
            ),
            SetupTeardownPattern(
                name="temp_directory",
                description="Temporary directory with automatic cleanup",
                scope="function",
                setup_code='''
@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for file operations."""
    # Setup: Create subdirectories
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()
    (test_dir / "data").mkdir()
    (test_dir / "output").mkdir()

    yield test_dir

    # Teardown: Automatic with tmp_path
''',
                teardown_code="# Automatic cleanup via pytest tmp_path",
            ),
            SetupTeardownPattern(
                name="http_server",
                description="Test HTTP server for integration tests",
                scope="session",
                setup_code='''
@pytest.fixture(scope="session")
def test_server():
    """Start test server for integration tests."""
    import subprocess
    import time

    # Setup: Start server
    process = subprocess.Popen(
        ["python", "-m", "uvicorn", "app:app", "--port", "8888"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)  # Wait for startup

    yield "http://localhost:8888"

    # Teardown: Stop server
    process.terminate()
    process.wait()
''',
                teardown_code="# Server terminated in fixture",
            ),
            SetupTeardownPattern(
                name="context_manager",
                description="Class-based setup with context manager",
                scope="class",
                setup_code='''
class TestWithSetup:
    """Tests with setup/teardown methods."""

    @classmethod
    def setup_class(cls):
        """Run once before all tests in class."""
        cls.shared_resource = create_expensive_resource()
        cls.config = load_test_config()

    @classmethod
    def teardown_class(cls):
        """Run once after all tests in class."""
        cls.shared_resource.cleanup()

    def setup_method(self, method):
        """Run before each test method."""
        self.fresh_data = create_test_data()

    def teardown_method(self, method):
        """Run after each test method."""
        cleanup_test_data(self.fresh_data)
''',
                teardown_code="# Handled by teardown_class and teardown_method",
            ),
        ]


@dataclass
class MockingPattern:
    """Pattern for mocking in tests."""

    name: str
    description: str
    pattern_code: str
    framework: str = "pytest"

    @staticmethod
    def get_patterns() -> List["MockingPattern"]:
        """Get all mocking patterns."""
        return [
            MockingPattern(
                name="patch_decorator",
                description="Use @patch decorator for function mocking",
                pattern_code='''
from unittest.mock import patch, Mock

@patch("module.external_function")
def test_with_mock(mock_func):
    """Test using patch decorator."""
    mock_func.return_value = {"status": "success"}

    result = function_under_test()

    mock_func.assert_called_once()
    assert result["status"] == "success"
''',
            ),
            MockingPattern(
                name="patch_context_manager",
                description="Use patch as context manager for scoped mocking",
                pattern_code='''
def test_with_context_manager():
    """Test using patch context manager."""
    with patch("module.database") as mock_db:
        mock_db.query.return_value = [{"id": 1, "name": "test"}]

        result = get_all_records()

        assert len(result) == 1
        mock_db.query.assert_called_with("SELECT * FROM records")
''',
            ),
            MockingPattern(
                name="mock_object",
                description="Create Mock objects with spec",
                pattern_code='''
def test_with_mock_object():
    """Test with Mock object having spec."""
    mock_service = Mock(spec=ExternalService)
    mock_service.fetch_data.return_value = {"data": [1, 2, 3]}
    mock_service.process.side_effect = [True, False, True]

    # Use mock in test
    processor = DataProcessor(service=mock_service)
    result = processor.run()

    assert mock_service.fetch_data.called
    assert mock_service.process.call_count == 3
''',
            ),
            MockingPattern(
                name="magic_mock",
                description="Use MagicMock for complex objects",
                pattern_code='''
from unittest.mock import MagicMock

def test_with_magic_mock():
    """Test with MagicMock for complex behavior."""
    mock_client = MagicMock()

    # Chain method calls
    mock_client.session.get.return_value.json.return_value = {"result": "ok"}

    # Context manager support
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    with mock_client as client:
        response = client.session.get("/api").json()
        assert response["result"] == "ok"
''',
            ),
            MockingPattern(
                name="async_mock",
                description="Mock async functions",
                pattern_code='''
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_async_mock():
    """Test mocking async functions."""
    with patch("module.async_fetch", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"data": "async result"}

        result = await async_function_under_test()

        mock_fetch.assert_awaited_once()
        assert result["data"] == "async result"
''',
            ),
            MockingPattern(
                name="pytest_mock",
                description="Use pytest-mock for cleaner syntax",
                pattern_code='''
def test_with_pytest_mock(mocker):
    """Test using pytest-mock fixture."""
    # Patch with mocker
    mock_func = mocker.patch("module.function")
    mock_func.return_value = "mocked"

    # Spy on real implementation
    spy = mocker.spy(real_module, "real_function")

    result = function_under_test()

    spy.assert_called()
    assert result == "mocked"
''',
            ),
        ]


@dataclass
class AssertionPattern:
    """Pattern for test assertions."""

    name: str
    description: str
    pattern_code: str
    assertion_type: str

    @staticmethod
    def get_patterns() -> List["AssertionPattern"]:
        """Get all assertion patterns."""
        return [
            AssertionPattern(
                name="equality_assertions",
                description="Basic equality and comparison assertions",
                assertion_type="equality",
                pattern_code='''
def test_equality_assertions():
    """Demonstrate equality assertions."""
    # Exact equality
    assert result == expected
    assert result != unexpected

    # Approximate equality (for floats)
    assert result == pytest.approx(3.14159, rel=1e-5)

    # Identity
    assert result is expected_object
    assert result is not other_object

    # Type checking
    assert isinstance(result, ExpectedType)
    assert type(result) is ExactType
''',
            ),
            AssertionPattern(
                name="collection_assertions",
                description="Assertions for lists, dicts, and sets",
                assertion_type="collection",
                pattern_code='''
def test_collection_assertions():
    """Demonstrate collection assertions."""
    items = [1, 2, 3, 4, 5]

    # Contains
    assert 3 in items
    assert 6 not in items

    # Length
    assert len(items) == 5
    assert len(items) > 0

    # Subset/Superset
    assert {1, 2}.issubset(set(items))
    assert set(items).issuperset({1, 2})

    # Dict assertions
    data = {"name": "test", "value": 42}
    assert "name" in data
    assert data.get("missing") is None
    assert data["value"] == 42
''',
            ),
            AssertionPattern(
                name="exception_assertions",
                description="Assertions for exception handling",
                assertion_type="exception",
                pattern_code='''
def test_exception_assertions():
    """Demonstrate exception assertions."""
    # Basic exception check
    with pytest.raises(ValueError):
        raise_value_error()

    # Check exception message
    with pytest.raises(ValueError, match="invalid input"):
        validate_input("invalid")

    # Capture and inspect exception
    with pytest.raises(CustomError) as exc_info:
        do_something_wrong()

    assert exc_info.value.error_code == 123
    assert "specific detail" in str(exc_info.value)
''',
            ),
            AssertionPattern(
                name="string_assertions",
                description="Assertions for string content",
                assertion_type="string",
                pattern_code='''
def test_string_assertions():
    """Demonstrate string assertions."""
    text = "Hello, World!"

    # Contains
    assert "World" in text
    assert "goodbye" not in text.lower()

    # Starts/Ends with
    assert text.startswith("Hello")
    assert text.endswith("!")

    # Regex matching
    import re
    assert re.match(r"Hello, \\w+!", text)
    assert re.search(r"\\bWorld\\b", text)
''',
            ),
            AssertionPattern(
                name="async_assertions",
                description="Assertions for async code",
                assertion_type="async",
                pattern_code='''
@pytest.mark.asyncio
async def test_async_assertions():
    """Demonstrate async assertions."""
    import asyncio

    # Await result and assert
    result = await async_function()
    assert result == expected

    # Assert timeout
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_function(), timeout=0.1)

    # Assert completion
    task = asyncio.create_task(async_operation())
    await asyncio.sleep(0.1)
    assert task.done()
''',
            ),
            AssertionPattern(
                name="custom_assertions",
                description="Custom assertion helpers",
                assertion_type="custom",
                pattern_code='''
def assert_valid_response(response, expected_status=200):
    """Custom assertion for API responses."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: "
        f"{response.text}"
    )
    data = response.json()
    assert "error" not in data
    return data


def assert_items_equal(actual, expected, key="id"):
    """Assert two lists contain same items (order-independent)."""
    actual_keys = sorted(item[key] for item in actual)
    expected_keys = sorted(item[key] for item in expected)
    assert actual_keys == expected_keys, (
        f"Item mismatch: {actual_keys} != {expected_keys}"
    )
''',
            ),
        ]


@dataclass
class CoveragePattern:
    """Pattern for coverage configuration."""

    name: str
    description: str
    config: Dict[str, Any]

    @staticmethod
    def get_patterns() -> List["CoveragePattern"]:
        """Get all coverage patterns."""
        return [
            CoveragePattern(
                name="pytest_cov_basic",
                description="Basic pytest-cov configuration",
                config={
                    "tool.pytest.ini_options": {
                        "addopts": "--cov=src --cov-report=term-missing --cov-report=html",
                    },
                    "tool.coverage.run": {
                        "source": ["src"],
                        "branch": True,
                        "omit": ["*/tests/*", "*/__pycache__/*"],
                    },
                    "tool.coverage.report": {
                        "fail_under": 80,
                        "exclude_lines": [
                            "pragma: no cover",
                            "if TYPE_CHECKING:",
                            "raise NotImplementedError",
                        ],
                    },
                },
            ),
            CoveragePattern(
                name="pytest_cov_strict",
                description="Strict coverage with 90% minimum",
                config={
                    "tool.coverage.run": {
                        "source": ["src"],
                        "branch": True,
                        "relative_files": True,
                    },
                    "tool.coverage.report": {
                        "fail_under": 90,
                        "show_missing": True,
                        "skip_empty": True,
                    },
                    "tool.coverage.html": {
                        "directory": "htmlcov",
                    },
                },
            ),
            CoveragePattern(
                name="jest_coverage",
                description="Jest coverage configuration",
                config={
                    "jest": {
                        "collectCoverage": True,
                        "coverageDirectory": "coverage",
                        "coverageReporters": ["text", "lcov", "html"],
                        "coverageThreshold": {
                            "global": {
                                "branches": 80,
                                "functions": 80,
                                "lines": 80,
                                "statements": 80,
                            },
                        },
                        "collectCoverageFrom": [
                            "src/**/*.{js,jsx,ts,tsx}",
                            "!src/**/*.d.ts",
                            "!src/**/index.{js,ts}",
                        ],
                    },
                },
            ),
        ]


def get_all_patterns() -> Dict[str, List]:
    """Get all pattern categories."""
    return {
        "setup_teardown": SetupTeardownPattern.get_patterns(),
        "mocking": MockingPattern.get_patterns(),
        "assertions": AssertionPattern.get_patterns(),
        "coverage": CoveragePattern.get_patterns(),
    }
