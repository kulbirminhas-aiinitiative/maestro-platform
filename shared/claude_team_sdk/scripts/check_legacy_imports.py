#!/usr/bin/env python3
"""
Check for imports from _legacy or _experiments directories.

This prevents production code from accidentally importing experimental
or deprecated code.

Usage:
    python scripts/check_legacy_imports.py
    python scripts/check_legacy_imports.py src/**/*.py  # Check specific files
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def check_file(filepath: str) -> List[Tuple[int, str]]:
    """
    Check if file imports from _legacy or _experiments.

    Returns:
        List of (line_number, import_statement) tuples
    """
    violations = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Check for legacy imports
                if re.search(r'from _legacy|import _legacy', line):
                    violations.append((line_num, line.strip(), "_legacy"))

                # Check for experiments imports
                if re.search(r'from _experiments|import _experiments', line):
                    violations.append((line_num, line.strip(), "_experiments"))

    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)

    return violations


def scan_files(files: List[str]) -> dict:
    """
    Scan files for legacy/experimental imports.

    Returns:
        Dictionary mapping file paths to violations
    """
    results = {}

    for filepath in files:
        violations = check_file(filepath)
        if violations:
            results[filepath] = violations

    return results


def print_results(results: dict):
    """Print scan results."""
    if not results:
        print("✅ No legacy/experimental imports found!")
        return

    print(f"❌ Found forbidden imports in {len(results)} file(s):\n")

    for filepath, violations in results.items():
        print(f"📄 {filepath}")
        for line_num, import_stmt, source in violations:
            print(f"   Line {line_num}: Cannot import from {source}/")
            print(f"   → {import_stmt}")
        print()

    print("⚠️  Production code cannot import from _legacy or _experiments directories")
    print("   - These directories are excluded from production builds")
    print("   - Code must be migrated to src/ to be used in production")

    sys.exit(1)


def main():
    """Main entry point."""
    # Get files to check
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        # Scan all Python files in src/ directory
        src_dir = Path("src")
        if src_dir.exists():
            files = [str(p) for p in src_dir.rglob("*.py")]
        else:
            # Fallback to root Python files
            files = [str(p) for p in Path(".").rglob("*.py")
                    if not str(p).startswith(('.venv', 'venv', '__pycache__'))]

    if not files:
        print("No Python files found to check")
        return

    print(f"🔍 Checking {len(files)} file(s) for forbidden imports...\n")

    results = scan_files(files)
    print_results(results)


if __name__ == "__main__":
    main()
