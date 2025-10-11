#!/usr/bin/env python3
"""
Quick test runner for Autonomous SDLC Engine V2
Generates a website similar to fifth9.com
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from autonomous_sdlc_engine_v2 import AutonomousSDLCEngineV2


async def main():
    """Run SDLC engine with fifth9.com-like website requirement"""

    # Create engine with custom output directory
    engine = AutonomousSDLCEngineV2(output_dir="./generated_fifth9_website")

    # Your requirement
    requirement = """
    Generate a website like fifth9.com:
    - Professional consulting/services website
    - Modern, clean design
    - Service offerings showcase
    - Contact form
    - About page
    - Responsive design
    - SEO optimized
    """

    print("="*80)
    print("🚀 Testing Autonomous SDLC Engine V2")
    print("="*80)
    print(f"\n📝 Requirement: {requirement.strip()}\n")
    print("⏳ This will take several minutes as AI agents autonomously work...")
    print("="*80)

    # Execute
    result = await engine.execute(requirement)

    if result["success"]:
        print("\n" + "="*80)
        print("✅ SUCCESS!")
        print("="*80)
        print(f"\n📁 Project generated at: {result['project_dir']}")
        print(f"📦 Files created: {len(result['files'])}")
        print(f"🔄 Workflow iterations: {result['iterations']}")

        print("\n📋 Files generated:")
        for file_path in result['files'][:10]:  # Show first 10
            print(f"  - {file_path}")
        if len(result['files']) > 10:
            print(f"  ... and {len(result['files']) - 10} more files")

        print(f"\n🎉 Complete! Check the generated project at:")
        print(f"   {result['project_dir']}")


if __name__ == "__main__":
    asyncio.run(main())
