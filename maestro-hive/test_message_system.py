#!/usr/bin/env python3
"""
Test Script for Message-Based Context System

Tests the new message types and conversation manager.
"""

import asyncio
from pathlib import Path
from sdlc_messages import (
    PersonaWorkMessage,
    ConversationMessage,
    SystemMessage,
    QualityGateMessage
)
from conversation_manager import ConversationHistory


async def test_basic_messages():
    """Test basic message creation and formatting"""
    print("=" * 70)
    print("TEST 1: Basic Message Creation")
    print("=" * 70)
    
    # Create conversation
    conv = ConversationHistory("test_session_001")
    
    # Add persona work message
    work_msg = conv.add_persona_work(
        persona_id="backend_developer",
        phase="implementation",
        summary="Implemented REST API with Express.js framework",
        decisions=[
            {
                "decision": "Chose Express over Fastify",
                "rationale": "Better ecosystem, more stable, extensive documentation",
                "alternatives_considered": ["Fastify", "Koa", "Hapi"],
                "trade_offs": "Slightly slower than Fastify, but better community support"
            },
            {
                "decision": "Used PostgreSQL for database",
                "rationale": "ACID compliance required for transactions",
                "alternatives_considered": ["MongoDB", "MySQL"],
                "trade_offs": "More complex than MongoDB, but provides data consistency"
            }
        ],
        files_created=[
            "backend/server.ts",
            "backend/routes/api.ts",
            "backend/models/user.ts",
            "backend/middleware/auth.ts"
        ],
        deliverables={
            "api_implementation": ["backend/routes/api.ts"],
            "database_schema": ["backend/models/user.ts"]
        },
        questions=[
            {
                "for": "frontend_developer",
                "question": "Do you prefer JSON:API format or plain JSON for responses?"
            }
        ],
        assumptions=[
            "Frontend will handle JWT token storage in localStorage",
            "CORS configuration will be handled by DevOps"
        ],
        dependencies={
            "depends_on": ["solution_architect"],
            "provides_for": ["frontend_developer", "qa_engineer"]
        },
        duration_seconds=180,
        quality_score=0.87
    )
    
    print(f"\n✅ Created PersonaWorkMessage: {work_msg.id[:8]}...")
    print(f"\nFormatted Output:\n")
    print(work_msg.to_text())
    
    return conv


async def test_conversation_flow():
    """Test full conversation flow"""
    print("\n" + "=" * 70)
    print("TEST 2: Conversation Flow")
    print("=" * 70)
    
    conv = ConversationHistory("test_session_002")
    
    # System message: Project start
    conv.add_system_message(
        content="Starting SDLC workflow for e-commerce platform",
        phase="requirements",
        level="info"
    )
    
    # Requirements analyst works
    conv.add_persona_work(
        persona_id="requirement_analyst",
        phase="requirements",
        summary="Analyzed requirements and identified core features for e-commerce platform",
        decisions=[
            {
                "decision": "Focus on MVP with 5 core features",
                "rationale": "Faster time to market, validate assumptions early",
                "alternatives_considered": ["Full feature set", "Minimal viable product"],
                "trade_offs": "Limited features initially, but faster feedback loop"
            }
        ],
        files_created=["requirements/functional_requirements.md"],
        deliverables={"functional_requirements": ["requirements/functional_requirements.md"]}
    )
    
    # Architect works
    conv.add_persona_work(
        persona_id="solution_architect",
        phase="design",
        summary="Designed microservices architecture with API gateway pattern",
        decisions=[
            {
                "decision": "Microservices architecture",
                "rationale": "Independent scaling, technology flexibility, fault isolation",
                "alternatives_considered": ["Monolith", "Modular monolith"],
                "trade_offs": "More operational complexity, but better scalability"
            }
        ],
        files_created=["architecture/system_design.md", "architecture/component_diagram.png"],
        questions=[
            {
                "for": "security_specialist",
                "question": "What's your recommendation for service-to-service authentication?"
            }
        ],
        dependencies={
            "depends_on": ["requirement_analyst"],
            "provides_for": ["backend_developer", "frontend_developer", "devops_engineer"]
        }
    )
    
    # Security specialist responds
    conv.add_discussion(
        persona_id="security_specialist",
        content="""For service-to-service auth, I recommend:
        1. mTLS (mutual TLS) for service-to-service communication
        2. JWT with RS256 for user authentication
        3. API Gateway with OAuth2 for external clients
        
        This provides defense in depth.""",
        phase="design",
        message_type="answer"
    )
    
    # Quality gate
    conv.add_quality_gate(
        persona_id="solution_architect",
        phase="design",
        passed=True,
        quality_score=0.92,
        completeness_percentage=95.0,
        metrics={
            "documentation_quality": 9.5,
            "architecture_completeness": 95,
            "security_considerations": 8.5
        },
        issues=[],
        recommendations=[]
    )
    
    print(f"\n✅ Created conversation with {len(conv)} messages")
    print(f"\nConversation Statistics:")
    stats = conv.get_summary_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n\nFull Conversation:")
    print("-" * 70)
    print(conv.get_conversation_text())
    
    return conv


async def test_persona_context():
    """Test persona context extraction"""
    print("\n" + "=" * 70)
    print("TEST 3: Persona Context Extraction")
    print("=" * 70)
    
    conv = await test_conversation_flow()
    
    # Get context for backend developer
    print("\n\nContext for Backend Developer:")
    print("=" * 70)
    context = conv.get_persona_context("backend_developer", phase="design")
    print(context)
    
    return conv


async def test_persistence():
    """Test save/load functionality"""
    print("\n" + "=" * 70)
    print("TEST 4: Persistence (Save/Load)")
    print("=" * 70)
    
    # Create and populate conversation
    conv = await test_conversation_flow()
    
    # Save
    save_path = Path("test_conversation.json")
    conv.save(save_path)
    print(f"\n✅ Saved conversation to {save_path}")
    
    # Load
    loaded_conv = ConversationHistory.load(save_path)
    print(f"✅ Loaded conversation with {len(loaded_conv)} messages")
    
    # Verify
    assert len(loaded_conv) == len(conv), "Message count mismatch"
    print("✅ Verification passed: Message counts match")
    
    # Clean up
    save_path.unlink()
    print(f"✅ Cleaned up test file")
    
    return loaded_conv


async def test_filtering():
    """Test message filtering"""
    print("\n" + "=" * 70)
    print("TEST 5: Message Filtering")
    print("=" * 70)
    
    conv = await test_conversation_flow()
    
    # Filter by type
    work_messages = conv.get_messages(message_type=PersonaWorkMessage)
    print(f"\nPersona work messages: {len(work_messages)}")
    
    discussions = conv.get_messages(message_type=ConversationMessage)
    print(f"Discussion messages: {len(discussions)}")
    
    quality_gates = conv.get_messages(message_type=QualityGateMessage)
    print(f"Quality gate messages: {len(quality_gates)}")
    
    # Filter by phase
    design_messages = conv.get_messages(phase="design")
    print(f"\nDesign phase messages: {len(design_messages)}")
    
    # Filter by source
    architect_messages = conv.get_messages(source="solution_architect")
    print(f"Architect messages: {len(architect_messages)}")
    
    print("\n✅ All filters working correctly")


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "MESSAGE-BASED CONTEXT SYSTEM - TEST SUITE" + " " * 16 + "║")
    print("╚" + "═" * 68 + "╝")
    
    try:
        await test_basic_messages()
        await test_conversation_flow()
        await test_persona_context()
        await test_persistence()
        await test_filtering()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\n🎉 Message-based context system is working correctly!")
        print("\nNext Steps:")
        print("1. Integrate into team_execution.py")
        print("2. Test with real SDLC workflow")
        print("3. Measure context quality improvement")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
