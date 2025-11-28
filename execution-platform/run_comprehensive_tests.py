#!/usr/bin/env python3
"""
Run comprehensive test suite - wrapper to handle imports correctly
"""
import sys
from pathlib import Path

# Ensure correct paths
root = Path(__file__).parent
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root / "tests"))
sys.path.insert(0, str(root.parent / "maestro-hive"))

# Now import and run
if __name__ == "__main__":
    import asyncio
    from test_comprehensive_suite import main
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
