#!/usr/bin/env python3
"""
Detect hardcoded URLs in codebase.

This script scans Python files for hardcoded localhost URLs and other
service URLs that should be in configuration instead.

Usage:
    python scripts/detect_hardcoded_urls.py
    python scripts/detect_hardcoded_urls.py --strict  # Exit 1 if any found
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns to detect
URL_PATTERNS = [
    r'localhost:\d+',
    r'127\.0\.0\.1:\d+',
    r'http://localhost',
    r'https://localhost',
    r'postgresql://[^"\']*@localhost',
    r'redis://localhost',
    r'mongodb://[^"\']*@localhost',
]

EXCLUDE_PATTERNS = [
    r'.*\.pyc$',
    r'.*__pycache__.*',
    r'.*\.egg-info.*',
    r'.*\.venv.*',
    r'.*venv.*',
    r'.*/\.git/.*',
    r'.*/generated_.*',
    r'.*/node_modules/.*',
]


def should_exclude(file_path: str) -> bool:
    """Check if file should be excluded from scanning."""
    return any(re.match(pattern, file_path) for pattern in EXCLUDE_PATTERNS)


def find_hardcoded_urls(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Find hardcoded URLs in a file.

    Returns:
        List of (line_number, line_content, matched_url) tuples
    """
    findings = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue

                # Check each pattern
                for pattern in URL_PATTERNS:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        findings.append((line_num, line.strip(), match.group()))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return findings


def scan_directory(root_dir: str = ".") -> dict:
    """
    Scan directory for hardcoded URLs.

    Returns:
        Dictionary mapping file paths to findings
    """
    results = {}

    for file_path in Path(root_dir).rglob("*.py"):
        str_path = str(file_path)

        if should_exclude(str_path):
            continue

        findings = find_hardcoded_urls(file_path)
        if findings:
            results[str_path] = findings

    return results


def print_results(results: dict, strict: bool = False):
    """Print scan results."""
    if not results:
        print("✅ No hardcoded URLs found!")
        return

    print(f"❌ Found hardcoded URLs in {len(results)} file(s):\n")

    total_issues = 0
    for file_path, findings in results.items():
        print(f"📄 {file_path}")
        for line_num, line_content, url in findings:
            print(f"   Line {line_num}: {url}")
            print(f"   → {line_content[:80]}...")
            total_issues += 1
        print()

    print(f"Total issues: {total_issues}")
    print("\n💡 Recommendation:")
    print("   1. Move URLs to config/default.yaml")
    print("   2. Use environment variables: ${VAR_NAME:default_value}")
    print("   3. Load with dynaconf or similar configuration library")

    if strict:
        sys.exit(1)


def main():
    """Main entry point."""
    strict = "--strict" in sys.argv

    print("🔍 Scanning for hardcoded URLs...\n")

    results = scan_directory(".")
    print_results(results, strict=strict)


if __name__ == "__main__":
    main()
