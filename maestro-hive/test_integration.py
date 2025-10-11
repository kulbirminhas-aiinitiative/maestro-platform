#!/usr/bin/env python3
"""
Test Integration of Message-Based Context System

Tests the updated team_execution.py with conversation history.
"""

import asyncio
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from team_execution import AutonomousSDLCEngineV3_1_Resumable


async def test_integration():
    """Test message-based context integration"""
    print("="*70)
    print("INTEGRATION TEST: Message-Based Context in team_execution.py")
    print("="*70)
    print()
    
    # Create engine with minimal personas
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=["requirement_analyst"],  # Just one for quick test
        output_dir="./test_integration_output",
        enable_persona_reuse=False  # Disable for test
    )
    
    # Execute
    print("Starting execution...")
    try:
        result = await engine.execute(
            requirement="Build a simple calculator API with Python FastAPI",
            session_id="integration_test_001"
        )
        
        print("\n✅ Execution completed!")
        print(f"Session ID: {result['session_id']}")
        print(f"Personas executed: {len(result['executions'])}")
        
        # Check conversation history
        conv_path = Path("./test_integration_output/conversation_history.json")
        if conv_path.exists():
            print(f"\n✅ Conversation history saved: {conv_path}")
            
            # Load and display stats
            from conversation_manager import ConversationHistory
            conv = ConversationHistory.load(conv_path)
            
            print(f"\nConversation Statistics:")
            stats = conv.get_summary_statistics()
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print(f"\n📝 Messages in conversation:")
            for msg in conv.messages:
                print(f"  - {msg.source}: {msg.__class__.__name__}")
            
            return True
        else:
            print(f"\n❌ Conversation history not found")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
