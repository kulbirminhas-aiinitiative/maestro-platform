import os, sys, pathlib, asyncio, pytest
# Ensure project root first so execution_platform top-level (with gateway) is used
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Also include src for provider/router/spi if needed
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(1, str(SRC))

# Ensure an event loop exists for tests that call get_event_loop()
@pytest.fixture(autouse=True)
def _ensure_event_loop():
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    yield

# Default to mock provider for tests
os.environ.setdefault("EP_PROVIDER", "mock")

# Test markers
def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "quality_fabric: Quality Fabric integration tests")

# Command line options
def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run tests that require live API keys"
    )
    parser.addoption(
        "--quality-fabric",
        action="store_true",
        default=False,
        help="Submit results to Quality Fabric service"
    )

# Skip live tests unless explicitly requested
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options"""
    if not config.getoption("--run-live"):
        skip_live = pytest.mark.skip(reason="need --run-live option to run")
        for item in items:
            if "live" in item.nodeid:
                item.add_marker(skip_live)
