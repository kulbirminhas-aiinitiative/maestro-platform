#!/usr/bin/env python3
"""
Run Autonomous Discussion from Config File

Usage:
    python run_autonomous_discussion.py autonomous_config.yaml
    python run_autonomous_discussion.py custom_config.yaml
"""

import asyncio
import yaml
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from autonomous_discussion import run_autonomous_discussion


async def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python run_autonomous_discussion.py <config_file.yaml>")
        print("\nExample:")
        print("  python run_autonomous_discussion.py autonomous_config.yaml")
        sys.exit(1)

    config_file = sys.argv[1]

    if not Path(config_file).exists():
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)

    # Load configuration
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    discussion = config['discussion']

    # Extract parameters
    agenda = discussion['agenda']
    rounds = discussion.get('rounds', 3)
    target = discussion.get('target_outcome')
    team = discussion['team']

    print(f"\n📋 Loading discussion from: {config_file}\n")

    # Run autonomous discussion
    await run_autonomous_discussion(
        agenda=agenda,
        discussion_rounds=rounds,
        target_outcome=target,
        team_composition=team
    )


if __name__ == "__main__":
    asyncio.run(main())
