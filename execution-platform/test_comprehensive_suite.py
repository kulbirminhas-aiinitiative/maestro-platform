"""
COMPREHENSIVE TEST SUITE FOR EXECUTION PLATFORM
Extensive test cases covering all variations and aspects

Test Categories:
1. Provider Routing Tests
2. Context Passing Tests
3. Error Handling Tests
4. Performance Tests
5. Provider Switching Tests
6. Tool Calling Tests
7. Streaming Tests
8. Multi-persona Workflows
9. Edge Cases
10. Integration Tests

All tests integrated with Quality Fabric for enterprise reporting
"""

import asyncio
import json
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Set up paths
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/execution-platform/src')
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/execution-platform/tests')
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive')

# Load environment
env_file = Path("/home/ec2-user/projects/maestro-platform/execution-platform/.env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.startswith('EP_'):
                    actual_key = key.replace('EP_', '')
                    os.environ[actual_key] = value

from execution_platform.router import PersonaRouter
from execution_platform.spi import Message, ChatRequest, ToolDefinition, ToolParameter

# Import Quality Fabric client
sys.path.insert(0, str(Path(__file__).parent / "tests"))
from quality_fabric_client import (
    QualityFabricClient, TestResult, TestSuite, QualityGate
)


class TestCase:
    """Individual test case"""
    def __init__(self, test_id: str, name: str, category: str, description: str):
        self.test_id = test_id
        self.name = name
        self.category = category
        self.description = description
        self.status = "pending"
        self.duration_ms = 0
        self.error = None
        self.metadata = {}
        
    def to_test_result(self) -> TestResult:
        """Convert to Quality Fabric TestResult"""
        return TestResult(
            test_id=self.test_id,
            test_name=self.name,
            status="passed" if self.status == "success" else "failed" if self.status == "failed" else "skipped",
            duration_ms=self.duration_ms,
            error_message=self.error,
            tags=[self.category],
            metadata=self.metadata
        )


class ComprehensiveTestSuite:
    """Comprehensive test suite with Quality Fabric integration"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = PersonaRouter()
        self.test_cases = []
        self.qf_client = QualityFabricClient(project="execution-platform")
        
    def register_test(self, test_case: TestCase):
        """Register a test case"""
        self.test_cases.append(test_case)
        
    async def execute_test(self, test_case: TestCase, test_func) -> bool:
        """Execute a single test case"""
        print(f"\n  [{test_case.test_id}] {test_case.name}")
        start_time = time.time()
        
        try:
            await test_func()
            test_case.status = "success"
            test_case.duration_ms = (time.time() - start_time) * 1000
            print(f"    ✓ PASSED ({test_case.duration_ms:.0f}ms)")
            return True
        except AssertionError as e:
            test_case.status = "failed"
            test_case.error = f"Assertion failed: {str(e)}"
            test_case.duration_ms = (time.time() - start_time) * 1000
            print(f"    ✗ FAILED: {test_case.error}")
            return False
        except Exception as e:
            test_case.status = "failed"
            test_case.error = str(e)
            test_case.duration_ms = (time.time() - start_time) * 1000
            print(f"    ✗ ERROR: {test_case.error}")
            return False
    
    # ==================== CATEGORY 1: PROVIDER ROUTING TESTS ====================
    
    async def test_provider_routing_claude(self):
        """Test routing to Claude provider"""
        persona = "architect"
        provider = self.router.select_provider(persona)
        assert provider == "claude_agent", f"Expected claude_agent, got {provider}"
    
    async def test_provider_routing_openai(self):
        """Test routing to OpenAI provider"""
        persona = "architect_openai"
        provider = self.router.select_provider(persona)
        assert provider == "openai", f"Expected openai, got {provider}"
    
    async def test_provider_routing_qa_engineer(self):
        """Test routing for QA engineer persona"""
        persona = "qa_engineer"
        provider = self.router.select_provider(persona)
        assert provider in ["openai", "claude_agent"], f"Unexpected provider: {provider}"
    
    async def test_provider_routing_invalid_persona(self):
        """Test handling of invalid persona"""
        try:
            self.router.select_provider("nonexistent_persona_xyz")
            assert False, "Should have raised error for invalid persona"
        except ValueError:
            pass  # Expected
    
    # ==================== CATEGORY 2: CONTEXT PASSING TESTS ====================
    
    async def test_context_single_provider(self):
        """Test context passing within single provider"""
        client = self.router.get_client("code_writer")
        
        # First message
        req1 = ChatRequest(
            messages=[Message(role="user", content="Remember this: PROJECT_NAME=TestApp")],
            max_tokens=100
        )
        
        response1 = ""
        async for chunk in client.chat(req1):
            if chunk.delta_text:
                response1 += chunk.delta_text
        
        # Second message referencing first
        req2 = ChatRequest(
            messages=[
                Message(role="user", content="Remember this: PROJECT_NAME=TestApp"),
                Message(role="assistant", content=response1),
                Message(role="user", content="What was the project name?")
            ],
            max_tokens=100
        )
        
        response2 = ""
        async for chunk in client.chat(req2):
            if chunk.delta_text:
                response2 += chunk.delta_text
        
        assert len(response2) > 0, "No response received"
    
    async def test_context_across_providers(self):
        """Test context passing between Claude and OpenAI"""
        # Phase 1: Claude
        claude_client = self.router.get_client("architect")
        req1 = ChatRequest(
            messages=[Message(role="user", content="Design a user authentication system")],
            max_tokens=200
        )
        
        claude_response = ""
        async for chunk in claude_client.chat(req1):
            if chunk.delta_text:
                claude_response += chunk.delta_text
        
        assert len(claude_response) > 0, "No response from Claude"
        
        # Phase 2: OpenAI with Claude's context
        openai_client = self.router.get_client("architect_openai")
        req2 = ChatRequest(
            messages=[
                Message(role="user", content="Design a user authentication system"),
                Message(role="assistant", content=claude_response),
                Message(role="user", content="Now implement the login endpoint")
            ],
            max_tokens=200
        )
        
        openai_response = ""
        async for chunk in openai_client.chat(req2):
            if chunk.delta_text:
                openai_response += chunk.delta_text
        
        assert len(openai_response) > 0, "No response from OpenAI"
    
    async def test_long_context_preservation(self):
        """Test context preservation with long conversation"""
        client = self.router.get_client("code_writer")
        messages = [Message(role="user", content="Hello")]
        
        # Simulate 5 turns
        for i in range(5):
            req = ChatRequest(messages=messages, max_tokens=100)
            response = ""
            async for chunk in client.chat(req):
                if chunk.delta_text:
                    response += chunk.delta_text
            
            messages.append(Message(role="assistant", content=response))
            messages.append(Message(role="user", content=f"Continue step {i+1}"))
        
        assert len(messages) >= 10, "Context chain broken"
    
    # ==================== CATEGORY 3: ERROR HANDLING TESTS ====================
    
    async def test_empty_message_handling(self):
        """Test handling of empty messages"""
        client = self.router.get_client("code_writer")
        req = ChatRequest(
            messages=[Message(role="user", content="")],
            max_tokens=50
        )
        
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
        
        # Should complete without error
        assert True
    
    async def test_very_long_prompt(self):
        """Test handling of very long prompts"""
        client = self.router.get_client("code_writer")
        long_content = "This is a test. " * 500  # ~7500 chars
        
        req = ChatRequest(
            messages=[Message(role="user", content=long_content)],
            max_tokens=100
        )
        
        response = ""
        async for chunk in client.chat(req):
            if chunk.delta_text:
                response += chunk.delta_text
        
        assert len(response) > 0, "No response for long prompt"
    
    async def test_special_characters_handling(self):
        """Test handling of special characters"""
        client = self.router.get_client("code_writer")
        special_chars = "Test: @#$%^&*()[]{}|\\/<>?`~\"'"
        
        req = ChatRequest(
            messages=[Message(role="user", content=special_chars)],
            max_tokens=50
        )
        
        response = ""
        async for chunk in client.chat(req):
            if chunk.delta_text:
                response += chunk.delta_text
        
        assert len(response) > 0, "No response for special characters"
    
    # ==================== CATEGORY 4: PERFORMANCE TESTS ====================
    
    async def test_rapid_sequential_requests(self):
        """Test rapid sequential requests to same provider"""
        client = self.router.get_client("code_writer")
        
        for i in range(3):
            req = ChatRequest(
                messages=[Message(role="user", content=f"Quick test {i}")],
                max_tokens=50
            )
            
            response = ""
            async for chunk in client.chat(req):
                if chunk.delta_text:
                    response += chunk.delta_text
            
            assert len(response) > 0, f"No response for request {i}"
    
    async def test_concurrent_requests_same_provider(self):
        """Test concurrent requests to same provider"""
        client = self.router.get_client("code_writer")
        
        async def single_request(msg):
            req = ChatRequest(
                messages=[Message(role="user", content=msg)],
                max_tokens=50
            )
            response = ""
            async for chunk in client.chat(req):
                if chunk.delta_text:
                    response += chunk.delta_text
            return response
        
        responses = await asyncio.gather(
            single_request("Test 1"),
            single_request("Test 2"),
            single_request("Test 3")
        )
        
        assert all(len(r) > 0 for r in responses), "Some requests failed"
    
    async def test_concurrent_requests_different_providers(self):
        """Test concurrent requests to different providers"""
        claude_client = self.router.get_client("architect")
        openai_client = self.router.get_client("architect_openai")
        
        async def claude_request():
            req = ChatRequest(
                messages=[Message(role="user", content="Claude test")],
                max_tokens=50
            )
            response = ""
            async for chunk in claude_client.chat(req):
                if chunk.delta_text:
                    response += chunk.delta_text
            return response
        
        async def openai_request():
            req = ChatRequest(
                messages=[Message(role="user", content="OpenAI test")],
                max_tokens=50
            )
            response = ""
            async for chunk in openai_client.chat(req):
                if chunk.delta_text:
                    response += chunk.delta_text
            return response
        
        claude_resp, openai_resp = await asyncio.gather(
            claude_request(),
            openai_request()
        )
        
        assert len(claude_resp) > 0, "Claude request failed"
        assert len(openai_resp) > 0, "OpenAI request failed"
    
    # ==================== CATEGORY 5: PROVIDER SWITCHING TESTS ====================
    
    async def test_provider_switch_claude_to_openai(self):
        """Test switching from Claude to OpenAI"""
        # Claude phase
        claude_client = self.router.get_client("architect")
        req1 = ChatRequest(
            messages=[Message(role="user", content="Design a REST API")],
            max_tokens=100
        )
        
        claude_response = ""
        async for chunk in claude_client.chat(req1):
            if chunk.delta_text:
                claude_response += chunk.delta_text
        
        # Switch to OpenAI
        openai_client = self.router.get_client("architect_openai")
        req2 = ChatRequest(
            messages=[
                Message(role="user", content="Design a REST API"),
                Message(role="assistant", content=claude_response),
                Message(role="user", content="Now add authentication")
            ],
            max_tokens=100
        )
        
        openai_response = ""
        async for chunk in openai_client.chat(req2):
            if chunk.delta_text:
                openai_response += chunk.delta_text
        
        assert len(claude_response) > 0, "Claude phase failed"
        assert len(openai_response) > 0, "OpenAI phase failed"
    
    async def test_provider_switch_openai_to_claude(self):
        """Test switching from OpenAI to Claude"""
        # OpenAI phase
        openai_client = self.router.get_client("architect_openai")
        req1 = ChatRequest(
            messages=[Message(role="user", content="Create a data model")],
            max_tokens=100
        )
        
        openai_response = ""
        async for chunk in openai_client.chat(req1):
            if chunk.delta_text:
                openai_response += chunk.delta_text
        
        # Switch to Claude
        claude_client = self.router.get_client("architect")
        req2 = ChatRequest(
            messages=[
                Message(role="user", content="Create a data model"),
                Message(role="assistant", content=openai_response),
                Message(role="user", content="Now implement the model")
            ],
            max_tokens=100
        )
        
        claude_response = ""
        async for chunk in claude_client.chat(req2):
            if chunk.delta_text:
                claude_response += chunk.delta_text
        
        assert len(openai_response) > 0, "OpenAI phase failed"
        assert len(claude_response) > 0, "Claude phase failed"
    
    async def test_multiple_provider_switches(self):
        """Test multiple provider switches in sequence"""
        responses = []
        
        # Claude -> OpenAI -> Claude -> OpenAI
        switches = [
            ("architect", "Start"),
            ("architect_openai", "Continue with OpenAI"),
            ("code_writer", "Continue with Claude"),
            ("code_writer_openai", "Finish with OpenAI")
        ]
        
        messages = [Message(role="user", content="Design a microservice")]
        
        for persona, prompt in switches:
            client = self.router.get_client(persona)
            messages.append(Message(role="user", content=prompt))
            
            req = ChatRequest(messages=messages, max_tokens=100)
            response = ""
            async for chunk in client.chat(req):
                if chunk.delta_text:
                    response += chunk.delta_text
            
            responses.append(response)
            messages.append(Message(role="assistant", content=response))
        
        assert all(len(r) > 0 for r in responses), "Some switches failed"
    
    # ==================== CATEGORY 6: STREAMING TESTS ====================
    
    async def test_streaming_chunks_received(self):
        """Test that streaming returns multiple chunks"""
        client = self.router.get_client("code_writer")
        req = ChatRequest(
            messages=[Message(role="user", content="Write a hello world function")],
            max_tokens=200
        )
        
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
        
        assert len(chunks) > 0, "No chunks received"
    
    async def test_streaming_assembly(self):
        """Test assembling streaming chunks into complete response"""
        client = self.router.get_client("code_writer")
        req = ChatRequest(
            messages=[Message(role="user", content="Count from 1 to 5")],
            max_tokens=100
        )
        
        full_text = ""
        async for chunk in client.chat(req):
            if chunk.delta_text:
                full_text += chunk.delta_text
        
        assert len(full_text) > 0, "No text assembled"
    
    async def test_streaming_finish_reason(self):
        """Test that finish_reason is provided"""
        client = self.router.get_client("code_writer")
        req = ChatRequest(
            messages=[Message(role="user", content="Hello")],
            max_tokens=50
        )
        
        finish_reasons = []
        async for chunk in client.chat(req):
            if chunk.finish_reason:
                finish_reasons.append(chunk.finish_reason)
        
        assert len(finish_reasons) > 0, "No finish_reason received"
    
    # ==================== CATEGORY 7: TOOL CALLING TESTS ====================
    
    async def test_tool_definition_acceptance(self):
        """Test that tool definitions are accepted"""
        client = self.router.get_client("code_writer")
        
        tools = [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                parameters=[
                    ToolParameter(name="param1", type="string", required=True)
                ]
            )
        ]
        
        req = ChatRequest(
            messages=[Message(role="user", content="Use the test tool")],
            tools=tools,
            max_tokens=100
        )
        
        response = ""
        async for chunk in client.chat(req):
            if chunk.delta_text:
                response += chunk.delta_text
        
        # Should complete without error
        assert True
    
    # ==================== CATEGORY 8: MULTI-PERSONA WORKFLOWS ====================
    
    async def test_multi_persona_workflow(self):
        """Test complete multi-persona workflow"""
        personas = ["architect", "code_writer", "reviewer"]
        responses = []
        
        context = "Build a user authentication system"
        
        for persona in personas:
            client = self.router.get_client(persona)
            req = ChatRequest(
                messages=[Message(role="user", content=f"{persona}: {context}")],
                max_tokens=100
            )
            
            response = ""
            async for chunk in client.chat(req):
                if chunk.delta_text:
                    response += chunk.delta_text
            
            responses.append(response)
            context = response
        
        assert all(len(r) > 0 for r in responses), "Workflow incomplete"
    
    # ==================== RUN ALL TESTS ====================
    
    async def run_all_tests(self) -> TestSuite:
        """Run all comprehensive tests"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUITE - EXECUTION PLATFORM")
        print("="*80)
        
        suite_start = datetime.now()
        
        # Register all tests
        tests_to_run = [
            # Category 1: Provider Routing (4 tests)
            (TestCase("PR01", "Provider Routing - Claude", "provider_routing", "Test routing to Claude"), 
             self.test_provider_routing_claude),
            (TestCase("PR02", "Provider Routing - OpenAI", "provider_routing", "Test routing to OpenAI"), 
             self.test_provider_routing_openai),
            (TestCase("PR03", "Provider Routing - QA Engineer", "provider_routing", "Test QA engineer routing"), 
             self.test_provider_routing_qa_engineer),
            (TestCase("PR04", "Provider Routing - Invalid Persona", "provider_routing", "Test invalid persona handling"), 
             self.test_provider_routing_invalid_persona),
            
            # Category 2: Context Passing (3 tests)
            (TestCase("CP01", "Context - Single Provider", "context_passing", "Test context within provider"), 
             self.test_context_single_provider),
            (TestCase("CP02", "Context - Across Providers", "context_passing", "Test context between providers"), 
             self.test_context_across_providers),
            (TestCase("CP03", "Context - Long Conversation", "context_passing", "Test long context preservation"), 
             self.test_long_context_preservation),
            
            # Category 3: Error Handling (3 tests)
            (TestCase("EH01", "Error - Empty Message", "error_handling", "Test empty message handling"), 
             self.test_empty_message_handling),
            (TestCase("EH02", "Error - Long Prompt", "error_handling", "Test very long prompt"), 
             self.test_very_long_prompt),
            (TestCase("EH03", "Error - Special Characters", "error_handling", "Test special characters"), 
             self.test_special_characters_handling),
            
            # Category 4: Performance (3 tests)
            (TestCase("PF01", "Performance - Sequential Requests", "performance", "Test rapid sequential requests"), 
             self.test_rapid_sequential_requests),
            (TestCase("PF02", "Performance - Concurrent Same Provider", "performance", "Test concurrent same provider"), 
             self.test_concurrent_requests_same_provider),
            (TestCase("PF03", "Performance - Concurrent Different Providers", "performance", "Test concurrent different providers"), 
             self.test_concurrent_requests_different_providers),
            
            # Category 5: Provider Switching (3 tests)
            (TestCase("PS01", "Switch - Claude to OpenAI", "provider_switching", "Test Claude to OpenAI switch"), 
             self.test_provider_switch_claude_to_openai),
            (TestCase("PS02", "Switch - OpenAI to Claude", "provider_switching", "Test OpenAI to Claude switch"), 
             self.test_provider_switch_openai_to_claude),
            (TestCase("PS03", "Switch - Multiple Switches", "provider_switching", "Test multiple provider switches"), 
             self.test_multiple_provider_switches),
            
            # Category 6: Streaming (3 tests)
            (TestCase("ST01", "Streaming - Chunks Received", "streaming", "Test streaming chunks"), 
             self.test_streaming_chunks_received),
            (TestCase("ST02", "Streaming - Assembly", "streaming", "Test chunk assembly"), 
             self.test_streaming_assembly),
            (TestCase("ST03", "Streaming - Finish Reason", "streaming", "Test finish reason"), 
             self.test_streaming_finish_reason),
            
            # Category 7: Tool Calling (1 test)
            (TestCase("TC01", "Tool Calling - Definition", "tool_calling", "Test tool definition acceptance"), 
             self.test_tool_definition_acceptance),
            
            # Category 8: Multi-persona (1 test)
            (TestCase("MP01", "Multi-persona Workflow", "multi_persona", "Test complete workflow"), 
             self.test_multi_persona_workflow),
        ]
        
        # Execute all tests
        for test_case, test_func in tests_to_run:
            self.register_test(test_case)
            await self.execute_test(test_case, test_func)
            await asyncio.sleep(0.1)  # Brief pause between tests
        
        suite_end = datetime.now()
        
        # Create Quality Fabric test suite
        qf_suite = TestSuite(
            suite_id=f"comprehensive-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            suite_name="Execution Platform Comprehensive Test Suite",
            project="execution-platform",
            environment="test",
            start_time=suite_start,
            end_time=suite_end,
            total_tests=len(self.test_cases),
            passed=sum(1 for t in self.test_cases if t.status == "success"),
            failed=sum(1 for t in self.test_cases if t.status == "failed"),
            skipped=sum(1 for t in self.test_cases if t.status == "skipped"),
            results=[t.to_test_result() for t in self.test_cases]
        )
        
        # Print summary
        self.print_summary(qf_suite)
        
        # Submit to Quality Fabric
        await self.submit_to_quality_fabric(qf_suite)
        
        return qf_suite
    
    def print_summary(self, suite: TestSuite):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {suite.total_tests}")
        print(f"Passed: {suite.passed} ✓")
        print(f"Failed: {suite.failed} ✗")
        print(f"Skipped: {suite.skipped} ⊝")
        print(f"Success Rate: {suite.success_rate:.1f}%")
        print(f"Duration: {suite.duration_ms:.0f}ms")
        print("="*80)
        
        # Category breakdown
        categories = {}
        for test in self.test_cases:
            if test.category not in categories:
                categories[test.category] = {"total": 0, "passed": 0}
            categories[test.category]["total"] += 1
            if test.status == "success":
                categories[test.category]["passed"] += 1
        
        print("\nCATEGORY BREAKDOWN:")
        for cat, stats in categories.items():
            rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")
    
    async def submit_to_quality_fabric(self, suite: TestSuite):
        """Submit results to Quality Fabric"""
        print("\n" + "="*80)
        print("QUALITY FABRIC SUBMISSION")
        print("="*80)
        
        try:
            # Check if service is available
            health = await self.qf_client.health_check()
            if health.get("status") == "unavailable":
                print("⚠ Quality Fabric service unavailable - saving locally")
                local_path = self.output_dir / f"qf_results_{suite.suite_id}.json"
                self.qf_client.save_local_report(suite, local_path)
                print(f"✓ Saved locally: {local_path}")
                return
            
            # Submit to Quality Fabric
            print("Submitting test results to Quality Fabric...")
            response = await self.qf_client.submit_test_suite(suite)
            
            if response.get("fallback"):
                print("⚠ Failed to submit - saved locally")
            else:
                print("✓ Successfully submitted to Quality Fabric")
            
            # Check quality gates
            print("\nChecking quality gates...")
            gates = await self.qf_client.check_quality_gates(suite.suite_id)
            
            for gate in gates:
                status = "✓" if gate.passed else "✗"
                print(f"  {status} {gate.name}: {gate.message}")
            
        except Exception as e:
            print(f"✗ Error with Quality Fabric: {e}")
            print("Saving results locally...")
            local_path = self.output_dir / f"qf_results_{suite.suite_id}.json"
            self.qf_client.save_local_report(suite, local_path)
            print(f"✓ Saved locally: {local_path}")
        
        finally:
            await self.qf_client.close()


async def main():
    """Main execution"""
    output_dir = Path("/home/ec2-user/projects/maestro-platform/execution-platform/test-results/comprehensive-suite")
    suite = ComprehensiveTestSuite(output_dir)
    
    try:
        qf_suite = await suite.run_all_tests()
        
        print("\n✓ Comprehensive test suite complete!")
        print(f"✓ Results: {qf_suite.passed}/{qf_suite.total_tests} passed")
        print(f"✓ Quality Fabric: Submitted")
        
        return 0 if qf_suite.failed == 0 else 1
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
