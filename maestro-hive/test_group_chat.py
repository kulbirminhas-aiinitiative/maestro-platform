#!/usr/bin/env python3
"""
Test Group Chat Implementation
"""

import asyncio
from pathlib import Path

from sdlc_group_chat import SDLCGroupChat
from conversation_manager import ConversationHistory


async def test_group_chat():
    """Test group chat functionality"""
    
    print("="*80)
    print("GROUP CHAT TEST")
    print("="*80)
    print()
    
    # Load personas first
    from src.personas import get_adapter
    adapter = get_adapter()
    await adapter.ensure_loaded()
    
    # Create conversation
    conv = ConversationHistory("test_group_chat")
    output_dir = Path("./test_group_chat_output")
    output_dir.mkdir(exist_ok=True)
    
    # Create group chat
    group_chat = SDLCGroupChat(
        session_id="test_group_chat",
        conversation=conv,
        output_dir=output_dir
    )
    
    # Run architecture discussion
    result = await group_chat.run_design_discussion(
        topic="System Architecture",
        participants=[
            "solution_architect",
            "security_specialist",
            "backend_developer",
            "frontend_developer"
        ],
        requirement="Build a task management REST API",
        phase="design",
        max_rounds=2
    )
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Consensus Reached: {result['consensus_reached']}")
    print(f"Rounds: {result['rounds']}")
    print(f"Messages: {len(result['messages'])}")
    print()
    
    print("Consensus Summary:")
    print("-"*80)
    print(result['consensus']['summary'])
    print()
    
    # Save conversation
    conv_path = output_dir / "group_chat_test.json"
    conv.save(conv_path)
    print(f"✅ Conversation saved to {conv_path}")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_group_chat())
    print("\n✅ Group chat test completed!")
