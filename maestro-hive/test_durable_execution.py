import asyncio
import os
import json
import shutil
from src.maestro_hive.unified_execution.persona_executor import PersonaExecutor
from src.maestro_hive.unified_execution.exceptions import RecoverableError

async def failing_task():
    raise RecoverableError("Simulated Failure", "TEST_ERROR")

async def success_task():
    return "Success!"

async def test_durable_execution():
    workflow_id = "test_workflow_durable_001"
    state_dir = "/var/maestro/state"
    
    # Clean up previous test
    state_file = f"{state_dir}/{workflow_id}.json"
    if os.path.exists(state_file):
        os.remove(state_file)
        
    print(f"--- Starting Durable Execution Test for {workflow_id} ---")
    
    # 1. Run Failing Task
    executor = PersonaExecutor(persona_id="tester", workflow_id=workflow_id)
    print("Executing failing task...")
    try:
        await executor.execute(failing_task, task_name="fail_test")
    except Exception:
        pass # Expected to fail eventually
        
    # 2. Verify State File Exists
    # Checkpoint manager creates files in checkpoints dir with timestamp
    checkpoint_dir = "/var/maestro/checkpoints"
    
    # Find the latest checkpoint file for this workflow
    checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.startswith(workflow_id)]
    checkpoint_files.sort() # Sort by name (timestamp is in name)
    
    if checkpoint_files:
        latest_checkpoint = os.path.join(checkpoint_dir, checkpoint_files[-1])
        print(f"✅ Checkpoint file found: {latest_checkpoint}")
        with open(latest_checkpoint, 'r') as f:
            state = json.load(f)
            # Checkpoint structure might be wrapped
            if 'data' in state:
                state = state['data']
                
            persona_state = state['persona_states']['tester']
            print(f"State Content: {json.dumps(persona_state, indent=2)}")
    else:
        print(f"❌ No checkpoint files found in {checkpoint_dir}!")
        return

    # 3. Run Success Task (Simulating Resume/Next Step)
    print("\nExecuting success task...")
    await executor.execute(success_task, task_name="success_test")
    
    # 4. Verify State Update
    checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.startswith(workflow_id)]
    checkpoint_files.sort()
    latest_checkpoint = os.path.join(checkpoint_dir, checkpoint_files[-1])
    
    with open(latest_checkpoint, 'r') as f:
        state = json.load(f)
        if 'data' in state:
            state = state['data']
            
        persona_state = state['persona_states']['tester']
        print(f"Updated State Content: {json.dumps(persona_state, indent=2)}")
        
        if persona_state['status'] == 'success':
            print("✅ State updated to SUCCESS.")
        else:
            print(f"❌ State status mismatch: {persona_state['status']}")

if __name__ == "__main__":
    # Ensure directory exists (mocking what StatePersistence does)
    os.makedirs("/var/maestro/state", exist_ok=True)
    os.makedirs("/var/maestro/checkpoints", exist_ok=True)
    asyncio.run(test_durable_execution())
