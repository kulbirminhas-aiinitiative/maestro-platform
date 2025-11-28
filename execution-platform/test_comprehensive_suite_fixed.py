import sys
from pathlib import Path
import importlib.util

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tests"))
sys.path.insert(0, str(Path(__file__).parent.parent / "maestro-hive"))

# Now import after paths are set - using importlib instead of exec() for security
spec = importlib.util.spec_from_file_location(
    "test_comprehensive_suite",
    Path(__file__).parent / "test_comprehensive_suite.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
