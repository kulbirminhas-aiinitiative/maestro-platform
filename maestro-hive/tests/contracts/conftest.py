"""
Pytest configuration for contract protocol tests
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path so we can import contracts
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
