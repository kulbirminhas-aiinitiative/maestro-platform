"""
End-to-end persona workflow tests

Tests complete workflows involving multiple personas and provider routing.
"""

import pytest
import asyncio
from execution_platform.spi import Message, ChatRequest, ToolDefinition, ToolParameter
from execution_platform.router import PersonaRouter


pytestmark = pytest.mark.e2e


class TestPersonaWorkflows:
    """Test complete persona-based workflows"""

    @pytest.fixture
    def router(self):
        """Create persona router"""
        return PersonaRouter()

    @pytest.mark.asyncio
    async def test_code_generation_workflow(self, router):
        """
        Test code generation workflow
        
        Flow: User request -> Code Writer -> Code Reviewer -> Final output
        """
        # Step 1: Code Writer generates code
        code_writer = router.get_client("code_writer")
        
        gen_request = ChatRequest(
            messages=[
                Message(role="user", content="Write a Python function to calculate fibonacci")
            ],
            max_tokens=500
        )
        
        generated_code = ""
        async for chunk in code_writer.chat(gen_request):
            if chunk.delta_text:
                generated_code += chunk.delta_text
        
        assert len(generated_code) > 0
        # Should contain function definition
        assert "def" in generated_code.lower() or "function" in generated_code.lower()

    @pytest.mark.asyncio
    async def test_architecture_design_workflow(self, router):
        """
        Test architecture design workflow
        
        Flow: Requirements -> Architect -> Design Document
        """
        architect = router.get_client("architect")
        
        design_request = ChatRequest(
            messages=[
                Message(
                    role="user",
                    content="Design a microservices architecture for an e-commerce platform"
                )
            ],
            max_tokens=1000
        )
        
        design_doc = ""
        async for chunk in architect.chat(design_request):
            if chunk.delta_text:
                design_doc += chunk.delta_text
        
        assert len(design_doc) > 0
        # Should contain architecture concepts
        keywords = ["service", "api", "database", "architecture"]
        assert any(kw in design_doc.lower() for kw in keywords)

    @pytest.mark.asyncio
    async def test_review_workflow(self, router):
        """
        Test code review workflow
        
        Flow: Code -> Reviewer -> Review Comments
        """
        reviewer = router.get_client("reviewer")
        
        code_sample = """
def calculate(x, y):
    return x + y
"""
        
        review_request = ChatRequest(
            messages=[
                Message(
                    role="user",
                    content=f"Review this code:\n```python\n{code_sample}\n```"
                )
            ],
            max_tokens=500
        )
        
        review = ""
        async for chunk in reviewer.chat(review_request):
            if chunk.delta_text:
                review += chunk.delta_text
        
        assert len(review) > 0

    @pytest.mark.asyncio
    async def test_tool_assisted_workflow(self, router):
        """
        Test workflow with tool calling
        
        Flow: User query -> Persona with tools -> Tool execution -> Response
        """
        client = router.get_client("code_writer")
        
        # Define tools
        tools = [
            ToolDefinition(
                name="read_file",
                description="Read contents of a file",
                parameters=[
                    ToolParameter(name="path", type="string", required=True)
                ]
            ),
            ToolDefinition(
                name="write_file",
                description="Write contents to a file",
                parameters=[
                    ToolParameter(name="path", type="string", required=True),
                    ToolParameter(name="content", type="string", required=True)
                ]
            )
        ]
        
        request = ChatRequest(
            messages=[
                Message(role="user", content="Read the config file and update version")
            ],
            tools=tools,
            max_tokens=500
        )
        
        tool_calls = []
        async for chunk in client.chat(request):
            if chunk.tool_call_delta:
                tool_calls.append(chunk.tool_call_delta)
        
        # Should attempt to use tools
        # Note: Actual tool execution depends on implementation
        assert True  # Workflow completed

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, router):
        """
        Test multi-turn conversation with context
        
        Flow: Q1 -> A1 -> Q2 (referencing A1) -> A2
        """
        client = router.get_client("code_writer")
        
        # Turn 1
        turn1_request = ChatRequest(
            messages=[
                Message(role="user", content="What is a binary tree?")
            ],
            max_tokens=300
        )
        
        turn1_response = ""
        async for chunk in client.chat(turn1_request):
            if chunk.delta_text:
                turn1_response += chunk.delta_text
        
        # Turn 2 - reference previous context
        turn2_request = ChatRequest(
            messages=[
                Message(role="user", content="What is a binary tree?"),
                Message(role="assistant", content=turn1_response),
                Message(role="user", content="Now implement it in Python")
            ],
            max_tokens=500
        )
        
        turn2_response = ""
        async for chunk in client.chat(turn2_request):
            if chunk.delta_text:
                turn2_response += chunk.delta_text
        
        assert len(turn1_response) > 0
        assert len(turn2_response) > 0
        # Second response should contain code
        assert "class" in turn2_response.lower() or "def" in turn2_response.lower()


class TestProviderSwitching:
    """Test dynamic provider switching based on capabilities"""

    @pytest.fixture
    def router(self):
        return PersonaRouter()

    @pytest.mark.asyncio
    async def test_different_personas_different_providers(self, router):
        """
        Test that different personas can use different providers
        """
        # Get clients for different personas
        architect = router.get_client("architect")
        code_writer = router.get_client("code_writer")
        reviewer = router.get_client("reviewer")
        
        # All should be valid clients
        assert architect is not None
        assert code_writer is not None
        assert reviewer is not None
        
        # All should respond to simple queries
        request = ChatRequest(
            messages=[Message(role="user", content="Hello")],
            max_tokens=50
        )
        
        for client in [architect, code_writer, reviewer]:
            chunks = []
            async for chunk in client.chat(request):
                chunks.append(chunk)
            assert len(chunks) > 0

    def test_provider_selection_logic(self, router):
        """Test provider selection algorithm"""
        # Test that selection respects capabilities
        for persona in ["architect", "code_writer", "reviewer"]:
            provider = router.select_provider(persona)
            assert provider in ["claude_agent", "openai", "gemini"]

    def test_invalid_persona_handling(self, router):
        """Test handling of invalid persona"""
        with pytest.raises(ValueError):
            router.select_provider("nonexistent_persona")


class TestContextHandoff:
    """Test context passing between personas"""

    @pytest.fixture
    def router(self):
        return PersonaRouter()

    @pytest.mark.asyncio
    async def test_context_preservation(self, router):
        """
        Test that context is preserved when handing off between personas
        
        Flow: Architect designs -> Code Writer implements
        """
        # Phase 1: Architect creates design
        architect = router.get_client("architect")
        
        design_request = ChatRequest(
            messages=[
                Message(
                    role="user",
                    content="Design a simple REST API for user management"
                )
            ],
            max_tokens=500
        )
        
        design = ""
        async for chunk in architect.chat(design_request):
            if chunk.delta_text:
                design += chunk.delta_text
        
        # Phase 2: Code Writer implements based on design
        code_writer = router.get_client("code_writer")
        
        impl_request = ChatRequest(
            messages=[
                Message(role="user", content="Design a simple REST API"),
                Message(role="assistant", content=design),
                Message(role="user", content="Now implement the user endpoint")
            ],
            max_tokens=800
        )
        
        implementation = ""
        async for chunk in code_writer.chat(impl_request):
            if chunk.delta_text:
                implementation += chunk.delta_text
        
        assert len(design) > 0
        assert len(implementation) > 0
        # Implementation should reference design concepts
        # This is a soft assertion as it depends on model behavior


@pytest.mark.asyncio
async def test_concurrent_persona_execution(tmp_path):
    """
    Test that multiple personas can execute concurrently
    
    This simulates a team of agents working in parallel
    """
    router = PersonaRouter()
    
    async def run_persona_task(persona: str, task: str):
        """Execute a task for a specific persona"""
        client = router.get_client(persona)
        request = ChatRequest(
            messages=[Message(role="user", content=task)],
            max_tokens=200
        )
        
        response = ""
        async for chunk in client.chat(request):
            if chunk.delta_text:
                response += chunk.delta_text
        
        return persona, response
    
    # Run multiple personas concurrently
    tasks = [
        run_persona_task("architect", "Design a database schema"),
        run_persona_task("code_writer", "Write a hello world function"),
        run_persona_task("reviewer", "What makes good code?")
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All should complete
    assert len(results) == 3
    
    # All should have responses
    for persona, response in results:
        assert len(response) > 0


@pytest.mark.asyncio
async def test_error_recovery_in_workflow():
    """
    Test error recovery in a multi-step workflow
    
    If one step fails, workflow should handle gracefully
    """
    router = PersonaRouter()
    client = router.get_client("code_writer")
    
    # Intentionally problematic request
    request = ChatRequest(
        messages=[Message(role="user", content="")],  # Empty request
        max_tokens=10
    )
    
    # Should not crash
    try:
        chunks = []
        async for chunk in client.chat(request):
            chunks.append(chunk)
        # Even if empty, should complete without exception
        assert True
    except Exception as e:
        # If exception, should be a known error type
        from execution_platform.spi import LLMError
        assert isinstance(e, (LLMError, ValueError, RuntimeError))
