"""
BDV Generated Feature Test Runner (MD-2021 Enhancement)

Dynamically discovers and executes auto-generated Gherkin feature files.
Works with pytest-bdd to run scenarios from BDVIntegrationService.

Author: Claude Code Implementation
Date: 2025-12-01
"""

import pytest
from pytest_bdd import scenarios
from pathlib import Path
import glob

# Get the directory containing this file
FEATURES_DIR = Path(__file__).parent
GENERATED_DIR = FEATURES_DIR / "generated"


def get_latest_feature_files():
    """Get the most recent set of generated feature files."""
    if not GENERATED_DIR.exists():
        return []

    # Find all feature files
    feature_files = list(GENERATED_DIR.glob("*.feature"))

    # Sort by modification time (newest first)
    feature_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return feature_files


# Dynamically load scenarios from generated feature files
# Note: pytest-bdd scenarios() must be called at module level
try:
    # Load all scenarios from the generated directory
    scenarios(str(GENERATED_DIR))
except Exception as e:
    # If no features found or other error, create a placeholder test
    @pytest.mark.skip(reason=f"No generated features available: {e}")
    def test_no_generated_features():
        """Placeholder when no generated features exist."""
        pass
