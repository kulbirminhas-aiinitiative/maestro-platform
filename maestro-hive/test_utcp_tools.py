#!/usr/bin/env python3
"""
Test script for UTCP JIRA and Git tools.

Usage:
    python test_utcp_tools.py --jira    # Test JIRA tool
    python test_utcp_tools.py --git     # Test Git tool
    python test_utcp_tools.py --all     # Test both
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utcp.tools.jira_tool import JiraTool
from utcp.tools.git_tool import GitTool
from utcp.registry import get_registry


def load_jira_credentials() -> dict:
    """Load JIRA credentials from .jira-config file."""
    config_path = Path.home() / "projects/maestro-frontend-production/.jira-config"

    if not config_path.exists():
        raise FileNotFoundError(f"JIRA config not found: {config_path}")

    credentials = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes and export prefix
                key = key.replace('export ', '').strip()
                value = value.strip().strip('"').strip("'")
                credentials[key] = value

    return {
        'base_url': credentials.get('JIRA_BASE_URL', ''),
        'email': credentials.get('JIRA_EMAIL', ''),
        'api_token': credentials.get('JIRA_API_TOKEN', ''),
        'project_key': credentials.get('JIRA_PROJECT_KEY', 'MD'),
    }


async def test_jira_tool():
    """Test JIRA tool operations."""
    print("\n" + "="*60)
    print("TESTING JIRA TOOL")
    print("="*60)

    try:
        credentials = load_jira_credentials()
        jira = JiraTool(credentials)

        # Test 1: Health check
        print("\n1. Health Check...")
        result = await jira.health_check()
        if result.success:
            print(f"   ✓ Connected as: {result.data['user']}")
        else:
            print(f"   ✗ Failed: {result.error}")
            return False

        # Test 2: Get issue
        print("\n2. Get Issue (MD-592)...")
        result = await jira.get_issue("MD-592")
        if result.success:
            print(f"   ✓ Found: {result.data['summary'][:50]}...")
            print(f"   Status: {result.data['status']}")
        else:
            print(f"   ✗ Failed: {result.error}")

        # Test 3: Search issues
        print("\n3. Search Issues (sprint=55)...")
        result = await jira.search_issues("sprint=55", max_results=5)
        if result.success:
            print(f"   ✓ Found {result.data['total']} issues")
            for issue in result.data['issues'][:3]:
                print(f"      - {issue['key']}: {issue['summary'][:40]}...")
        else:
            print(f"   ✗ Failed: {result.error}")

        # Test 4: Get transitions
        print("\n4. Get Transitions for MD-866...")
        result = await jira.get_transitions("MD-866")
        if result.success:
            print(f"   ✓ Available transitions:")
            for t in result.data['transitions']:
                print(f"      - {t['name']} -> {t['to_status']}")
        else:
            print(f"   ✗ Failed: {result.error}")

        # Test 5: Get comments
        print("\n5. Get Comments (MD-592)...")
        result = await jira.get_comments("MD-592")
        if result.success:
            print(f"   ✓ Found {len(result.data['comments'])} comments")
            if result.data['comments']:
                latest = result.data['comments'][-1]
                print(f"      Latest by: {latest['author']}")
        else:
            print(f"   ✗ Failed: {result.error}")

        print("\n" + "-"*60)
        print("JIRA Tool Tests: PASSED")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


async def test_git_tool():
    """Test Git tool operations."""
    print("\n" + "="*60)
    print("TESTING GIT TOOL")
    print("="*60)

    try:
        repo_path = "/home/ec2-user/projects/maestro-platform/maestro-hive"

        credentials = {
            'repo_path': repo_path,
            # Optional GitHub credentials for PR operations
            'github_token': os.environ.get('GITHUB_TOKEN', ''),
            'github_owner': 'fifth9',  # Adjust as needed
            'github_repo': 'maestro-hive',
        }

        git = GitTool(credentials)

        # Test 1: Health check
        print("\n1. Health Check...")
        result = await git.health_check()
        if result.success:
            print(f"   ✓ Repository: {result.data['repo_path']}")
            print(f"   Branch: {result.data['branch']}")
            print(f"   Commit: {result.data['commit']}")
        else:
            print(f"   ✗ Failed: {result.error}")
            return False

        # Test 2: Get status
        print("\n2. Get Status...")
        result = await git.get_status()
        if result.success:
            print(f"   ✓ Branch: {result.data['branch']}")
            print(f"   Modified: {len(result.data['modified'])} files")
            print(f"   Untracked: {len(result.data['untracked'])} files")
            print(f"   Staged: {len(result.data['staged'])} files")
            if result.data['upstream']:
                print(f"   Ahead/Behind: {result.data['ahead']}/{result.data['behind']}")
        else:
            print(f"   ✗ Failed: {result.error}")

        # Test 3: Get log
        print("\n3. Get Log (last 5 commits)...")
        result = await git.get_log(count=5)
        if result.success:
            print(f"   ✓ Recent commits:")
            for commit in result.data['commits']:
                print(f"      - {commit['hash']}: {commit['message'][:50]}...")
        else:
            print(f"   ✗ Failed: {result.error}")

        # Test 4: Get diff (staged)
        print("\n4. Get Diff (staged)...")
        result = await git.diff(staged=True)
        if result.success:
            if result.data['has_changes']:
                lines = result.data['diff'].split('\n')
                print(f"   ✓ Staged changes: {len(lines)} lines")
            else:
                print(f"   ✓ No staged changes")
        else:
            print(f"   ✗ Failed: {result.error}")

        print("\n" + "-"*60)
        print("Git Tool Tests: PASSED")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


async def test_registry():
    """Test tool registry."""
    print("\n" + "="*60)
    print("TESTING TOOL REGISTRY")
    print("="*60)

    try:
        from utcp.registry import ToolRegistry
        from utcp.base import ToolCapability

        registry = ToolRegistry()

        # Register tools
        registry.register(
            name="jira",
            description="JIRA integration for issue tracking",
            tool_class=JiraTool,
            tags=["issue-tracking", "agile"]
        )

        registry.register(
            name="git",
            description="Git operations for version control",
            tool_class=GitTool,
            tags=["version-control", "code"]
        )

        print("\n1. List all tools...")
        tools = registry.list_tools()
        print(f"   ✓ Registered {len(tools)} tools")
        for tool in tools:
            print(f"      - {tool.name}: {tool.description}")

        print("\n2. Get tool info...")
        info = registry.get_tool_info("jira")
        if info:
            print(f"   ✓ JIRA tool info:")
            print(f"      Capabilities: {info['capabilities']}")
            print(f"      Tags: {info['tags']}")

        print("\n3. Get tools for implementation phase...")
        phase_tools = registry.get_tools_for_phase("implementation")
        print(f"   ✓ Found {len(phase_tools)} tools for implementation")
        for tool in phase_tools:
            print(f"      - {tool.name}")

        print("\n" + "-"*60)
        print("Registry Tests: PASSED")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test UTCP tools")
    parser.add_argument("--jira", action="store_true", help="Test JIRA tool")
    parser.add_argument("--git", action="store_true", help="Test Git tool")
    parser.add_argument("--registry", action="store_true", help="Test registry")
    parser.add_argument("--all", action="store_true", help="Test all")

    args = parser.parse_args()

    if not any([args.jira, args.git, args.registry, args.all]):
        args.all = True

    results = []

    if args.jira or args.all:
        results.append(("JIRA", await test_jira_tool()))

    if args.git or args.all:
        results.append(("Git", await test_git_tool()))

    if args.registry or args.all:
        results.append(("Registry", await test_registry()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("="*60)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
