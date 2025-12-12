import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "maestro_hive" / "teams"))
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from team_execution_v2 import TeamExecutionEngineV2
except ImportError:
    from maestro_hive.teams.team_execution_v2 import TeamExecutionEngineV2

async def main():
    print("🚀 Starting simple test...")
    engine = TeamExecutionEngineV2()
    
    requirement = "Create a simple Python script that prints 'Hello World'"
    
    try:
        result = await engine.execute(
            requirement=requirement,
            constraints={"prefer_parallel": False}
        )
        print("✅ Execution successful")
        print(result)
    except Exception as e:
        print(f"❌ Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
