"""
Comparative Test: Execution Platform with Provider Combinations

This script tests three scenarios:
A) Full Claude (using Claude Agent SDK)
B) Mixed (Claude + OpenAI simulated) - Different phases use different personas
C) Full OpenAI (simulated with different persona)

The test runs the same requirement through all three configurations and compares:
- Execution time
- Output quality
- Provider routing behavior
- Token usage
- Error handling
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import sys
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/execution-platform/src')

# Import execution platform
from execution_platform.router import PersonaRouter
from execution_platform.spi import Message, ChatRequest


class TestResult:
    """Container for test results"""
    def __init__(self, config_name: str):
        self.config_name = config_name
        self.start_time = None
        self.end_time = None
        self.duration_ms = 0
        self.phases_completed = []
        self.phase_durations = {}
        self.providers_used = {}
        self.total_tokens = 0
        self.errors = []
        self.outputs = {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_name": self.config_name,
            "duration_ms": self.duration_ms,
            "phases_completed": self.phases_completed,
            "phase_durations": self.phase_durations,
            "providers_used": self.providers_used,
            "total_tokens": self.total_tokens,
            "errors": self.errors,
            "success": len(self.errors) == 0
        }


class WorkflowComparator:
    """Compares DAG workflow and Execution Platform implementations"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = PersonaRouter()
        
    async def test_execution_platform_full_claude(self, requirement: str) -> TestResult:
        """Test A: Full Claude using Execution Platform"""
        print("\n=== Test A: Execution Platform - Full Claude ===")
        result = TestResult("A_ExecPlatform_FullClaude")
        result.start_time = datetime.now()
        
        try:
            # Define phases to execute
            phases = [
                ("requirements", "Analyze the following requirement and create detailed requirements document"),
                ("architecture", "Design system architecture based on the requirements"),
                ("implementation", "Create implementation plan with technology stack"),
                ("review", "Review the implementation plan for quality and completeness")
            ]
            
            context = requirement
            
            for phase_name, prompt in phases:
                phase_start = time.time()
                print(f"\n  Phase: {phase_name}")
                
                # Use persona based on phase
                persona_map = {
                    "requirements": "architect",
                    "architecture": "architect",
                    "implementation": "code_writer",
                    "review": "reviewer"
                }
                
                persona = persona_map.get(phase_name, "code_writer")
                
                try:
                    # Get provider for this persona (should be claude_agent)
                    provider = self.router.select_provider(persona)
                    client = self.router.get_client(persona)
                    
                    # Execute phase
                    request = ChatRequest(
                        messages=[
                            Message(role="user", content=f"{prompt}\n\nContext:\n{context}")
                        ],
                        max_tokens=1000
                    )
                    
                    phase_output = ""
                    async for chunk in client.chat(request):
                        if chunk.delta_text:
                            phase_output += chunk.delta_text
                        if chunk.usage:
                            result.total_tokens += chunk.usage.total_tokens
                    
                    # Store results
                    phase_duration = (time.time() - phase_start) * 1000
                    result.phase_durations[phase_name] = phase_duration
                    result.phases_completed.append(phase_name)
                    result.providers_used[phase_name] = provider
                    result.outputs[phase_name] = phase_output[:200]  # First 200 chars
                    
                    # Pass output to next phase
                    context = phase_output
                    
                    print(f"    ✓ Completed in {phase_duration:.0f}ms using {provider}")
                    
                except Exception as e:
                    result.errors.append(f"{phase_name}: {str(e)}")
                    print(f"    ✗ Error: {e}")
                    break
                    
        except Exception as e:
            result.errors.append(f"Overall: {str(e)}")
            
        result.end_time = datetime.now()
        result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    async def test_execution_platform_mixed(self, requirement: str) -> TestResult:
        """Test B: Mixed Claude + OpenAI using Execution Platform"""
        print("\n=== Test B: Execution Platform - Mixed (Claude + OpenAI) ===")
        result = TestResult("B_ExecPlatform_Mixed")
        result.start_time = datetime.now()
        
        try:
            # Define phases with explicit provider override
            phases = [
                ("requirements", "architect", "claude_agent", "Analyze requirements"),
                ("architecture", "architect", "openai", "Design architecture"),
                ("implementation", "code_writer", "claude_agent", "Create implementation"),
                ("review", "reviewer", "openai", "Review implementation")
            ]
            
            context = requirement
            
            for phase_name, persona, preferred_provider, prompt in phases:
                phase_start = time.time()
                print(f"\n  Phase: {phase_name} (targeting {preferred_provider})")
                
                try:
                    # For mixed mode, we'd need to modify router to accept provider hints
                    # For now, we'll use the persona's default provider
                    provider = self.router.select_provider(persona)
                    client = self.router.get_client(persona)
                    
                    request = ChatRequest(
                        messages=[
                            Message(role="user", content=f"{prompt}\n\nContext:\n{context}")
                        ],
                        max_tokens=1000
                    )
                    
                    phase_output = ""
                    async for chunk in client.chat(request):
                        if chunk.delta_text:
                            phase_output += chunk.delta_text
                        if chunk.usage:
                            result.total_tokens += chunk.usage.total_tokens
                    
                    phase_duration = (time.time() - phase_start) * 1000
                    result.phase_durations[phase_name] = phase_duration
                    result.phases_completed.append(phase_name)
                    result.providers_used[phase_name] = provider
                    result.outputs[phase_name] = phase_output[:200]
                    
                    context = phase_output
                    
                    print(f"    ✓ Completed in {phase_duration:.0f}ms using {provider}")
                    
                except Exception as e:
                    result.errors.append(f"{phase_name}: {str(e)}")
                    print(f"    ✗ Error: {e}")
                    break
                    
        except Exception as e:
            result.errors.append(f"Overall: {str(e)}")
            
        result.end_time = datetime.now()
        result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    async def test_execution_platform_full_openai(self, requirement: str) -> TestResult:
        """Test C: Full OpenAI using Execution Platform"""
        print("\n=== Test C: Execution Platform - Full OpenAI ===")
        result = TestResult("C_ExecPlatform_FullOpenAI")
        result.start_time = datetime.now()
        
        try:
            # Note: This requires modifying persona policies to use OpenAI
            # For now, we'll attempt but may fall back to default providers
            phases = [
                ("requirements", "Analyze requirements"),
                ("architecture", "Design architecture"),
                ("implementation", "Create implementation"),
                ("review", "Review implementation")
            ]
            
            context = requirement
            
            for phase_name, prompt in phases:
                phase_start = time.time()
                print(f"\n  Phase: {phase_name}")
                
                try:
                    # Try to use OpenAI-preferring persona
                    # This would require configuration changes
                    persona = "code_writer"
                    provider = self.router.select_provider(persona)
                    client = self.router.get_client(persona)
                    
                    request = ChatRequest(
                        messages=[
                            Message(role="user", content=f"{prompt}\n\nContext:\n{context}")
                        ],
                        max_tokens=1000
                    )
                    
                    phase_output = ""
                    async for chunk in client.chat(request):
                        if chunk.delta_text:
                            phase_output += chunk.delta_text
                        if chunk.usage:
                            result.total_tokens += chunk.usage.total_tokens
                    
                    phase_duration = (time.time() - phase_start) * 1000
                    result.phase_durations[phase_name] = phase_duration
                    result.phases_completed.append(phase_name)
                    result.providers_used[phase_name] = provider
                    result.outputs[phase_name] = phase_output[:200]
                    
                    context = phase_output
                    
                    print(f"    ✓ Completed in {phase_duration:.0f}ms using {provider}")
                    
                except Exception as e:
                    result.errors.append(f"{phase_name}: {str(e)}")
                    print(f"    ✗ Error: {e}")
                    break
                    
        except Exception as e:
            result.errors.append(f"Overall: {str(e)}")
            
        result.end_time = datetime.now()
        result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    async def run_comparison(self, requirement: str) -> Dict[str, Any]:
        """Run all three test configurations and compare"""
        print("\n" + "="*80)
        print("WORKFLOW COMPARISON TEST")
        print("="*80)
        print(f"\nRequirement: {requirement}\n")
        
        results = []
        
        # Test A: Full Claude
        result_a = await self.test_execution_platform_full_claude(requirement)
        results.append(result_a)
        
        # Test B: Mixed
        result_b = await self.test_execution_platform_mixed(requirement)
        results.append(result_b)
        
        # Test C: Full OpenAI (may use defaults due to config)
        result_c = await self.test_execution_platform_full_openai(requirement)
        results.append(result_c)
        
        # Generate comparison report
        report = self.generate_comparison_report(results)
        
        # Save results
        self.save_results(results, report)
        
        return report
    
    def generate_comparison_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate comprehensive comparison report"""
        print("\n" + "="*80)
        print("COMPARISON REPORT")
        print("="*80)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "configurations": [],
            "comparison": {}
        }
        
        for result in results:
            config_data = result.to_dict()
            report["configurations"].append(config_data)
            
            print(f"\n{result.config_name}:")
            print(f"  Duration: {result.duration_ms:.0f}ms")
            print(f"  Phases: {len(result.phases_completed)}/{4}")
            print(f"  Tokens: {result.total_tokens}")
            print(f"  Providers: {result.providers_used}")
            print(f"  Success: {'✓' if not result.errors else '✗'}")
            if result.errors:
                print(f"  Errors: {result.errors}")
        
        # Calculate comparison metrics
        durations = [r.duration_ms for r in results if r.duration_ms > 0]
        if durations:
            report["comparison"]["fastest"] = min(durations)
            report["comparison"]["slowest"] = max(durations)
            report["comparison"]["average"] = sum(durations) / len(durations)
            
        tokens = [r.total_tokens for r in results]
        if tokens:
            report["comparison"]["min_tokens"] = min(tokens)
            report["comparison"]["max_tokens"] = max(tokens)
            report["comparison"]["avg_tokens"] = sum(tokens) / len(tokens)
        
        print("\n" + "="*80)
        print(f"Fastest: {report['comparison'].get('fastest', 0):.0f}ms")
        print(f"Slowest: {report['comparison'].get('slowest', 0):.0f}ms")
        print(f"Token Range: {report['comparison'].get('min_tokens', 0)} - {report['comparison'].get('max_tokens', 0)}")
        print("="*80 + "\n")
        
        return report
    
    def save_results(self, results: List[TestResult], report: Dict[str, Any]):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        for result in results:
            filename = f"{result.config_name}_{timestamp}.json"
            filepath = self.output_dir / filename
            with open(filepath, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"Saved: {filepath}")
        
        # Save comparison report
        report_file = self.output_dir / f"comparison_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Saved: {report_file}")
        
        # Save summary markdown
        summary_file = self.output_dir / f"comparison_summary_{timestamp}.md"
        with open(summary_file, 'w') as f:
            f.write("# Workflow Comparison Test Results\n\n")
            f.write(f"**Date**: {report['timestamp']}\n\n")
            f.write("## Configurations Tested\n\n")
            
            for config in report['configurations']:
                f.write(f"### {config['config_name']}\n\n")
                f.write(f"- **Duration**: {config['duration_ms']:.0f}ms\n")
                f.write(f"- **Phases Completed**: {len(config['phases_completed'])}\n")
                f.write(f"- **Total Tokens**: {config['total_tokens']}\n")
                f.write(f"- **Success**: {'✓' if config['success'] else '✗'}\n")
                f.write(f"- **Providers Used**: {config['providers_used']}\n\n")
                
                if config['errors']:
                    f.write("**Errors:**\n")
                    for error in config['errors']:
                        f.write(f"- {error}\n")
                    f.write("\n")
            
            f.write("## Summary\n\n")
            comp = report.get('comparison', {})
            if comp:
                f.write(f"- **Fastest Configuration**: {comp.get('fastest', 0):.0f}ms\n")
                f.write(f"- **Slowest Configuration**: {comp.get('slowest', 0):.0f}ms\n")
                f.write(f"- **Average Duration**: {comp.get('average', 0):.0f}ms\n")
                f.write(f"- **Token Range**: {comp.get('min_tokens', 0)} - {comp.get('max_tokens', 0)}\n")
        
        print(f"Saved: {summary_file}")


async def main():
    """Main test execution"""
    # Sample requirement
    requirement = """
    Create a simple REST API for a task management system with the following features:
    - User authentication (login/logout)
    - CRUD operations for tasks (create, read, update, delete)
    - Task categories and priorities
    - Due date tracking
    - RESTful endpoints with proper HTTP methods
    - Basic error handling and validation
    """
    
    output_dir = Path("/home/ec2-user/projects/maestro-platform/execution-platform/test-results/comparison")
    comparator = WorkflowComparator(output_dir)
    
    try:
        report = await comparator.run_comparison(requirement)
        print("\n✓ Comparison test complete!")
        print(f"Results saved to: {output_dir}")
        return 0
    except Exception as e:
        print(f"\n✗ Comparison test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
