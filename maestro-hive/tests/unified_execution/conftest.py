"""
Pytest configuration for unified_execution tests.

Sets up the Python path to find maestro_hive module.
"""

import sys
from pathlib import Path

# Add src directory to path for maestro_hive imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
