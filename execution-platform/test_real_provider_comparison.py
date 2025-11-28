"""
REAL Comparative Test: Execution Platform with ACTUAL Provider Combinations

This script tests three REAL scenarios with ACTUAL API calls:
A) Full Claude (using Claude Agent SDK)
B) Mixed (alternating Claude + OpenAI) - Real provider switching
C) Full OpenAI (using OpenAI API with real key)

Requirements:
- OPENAI_API_KEY must be set
- Personas configured in persona_policy.yaml
"""

import asyncio
import json
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import sys
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/execution-platform/src')

# Set up environment variables from .env file
env_file = Path("/home/ec2-user/projects/maestro-platform/execution-platform/.env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.startswith('EP_'):
                    # Map EP_OPENAI_API_KEY to OPENAI_API_KEY
                    actual_key = key.replace('EP_', '')
                    os.environ[actual_key] = value
                    if 'KEY' in key:
                        print(f"✓ Set {actual_key}=***{value[-4:]}")

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
            "success": len(self.errors) == 0,
            "outputs_preview": {k: v[:100] + "..." if len(v) > 100 else v 
                               for k, v in self.outputs.items()}
        }


class RealWorkflowComparator:
    """Compares REAL provider executions"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = PersonaRouter()
        
    async def execute_phase(self, persona: str, phase_name: str, prompt: str, 
                          context: str, max_tokens: int = 500) -> tuple:
        """Execute a single phase with a persona"""
        phase_start = time.time()
        
        try:
            # Get provider and client
            provider = self.router.select_provider(persona)
            client = self.router.get_client(persona)
            
            # Execute phase
            request = ChatRequest(
                messages=[
                    Message(role="user", content=f"{prompt}\n\nContext:\n{context}")
                ],
                max_tokens=max_tokens
            )
            
            phase_output = ""
            tokens_used = 0
            
            async for chunk in client.chat(request):
                if chunk.delta_text:
                    phase_output += chunk.delta_text
                if chunk.usage:
                    tokens_used = chunk.usage.total_tokens
            
            phase_duration = (time.time() - phase_start) * 1000
            
            return {
                'success': True,
                'output': phase_output,
                'duration': phase_duration,
                'provider': provider,
                'tokens': tokens_used
            }
            
        except Exception as e:
            phase_duration = (time.time() - phase_start) * 1000
            return {
                'success': False,
                'error': str(e),
                'duration': phase_duration,
                'provider': 'unknown',
                'tokens': 0
            }
    
    async def test_full_claude(self, requirement: str) -> TestResult:
        """Test A: Full Claude using Claude Agent SDK"""
        print("\n" + "="*80)
        print("TEST A: FULL CLAUDE (Claude Agent SDK)")
        print("="*80)
        result = TestResult("A_FullClaude_REAL")
        result.start_time = datetime.now()
        
        phases = [
            ("requirements", "architect", "Analyze this requirement and create a detailed requirements document"),
            ("architecture", "architect", "Design the system architecture"),
            ("implementation", "code_writer", "Create an implementation plan"),
            ("review", "reviewer", "Review the implementation plan for quality")
        ]
        
        context = requirement
        
        for phase_name, persona, prompt in phases:
            print(f"\n  Phase: {phase_name} (persona={persona})")
            
            phase_result = await self.execute_phase(persona, phase_name, prompt, context)
            
            if phase_result['success']:
                result.phase_durations[phase_name] = phase_result['duration']
                result.phases_completed.append(phase_name)
                result.providers_used[phase_name] = phase_result['provider']
                result.total_tokens += phase_result['tokens']
                result.outputs[phase_name] = phase_result['output']
                context = phase_result['output']  # Chain to next phase
                
                print(f"    ✓ {phase_result['duration']:.0f}ms | {phase_result['provider']} | {phase_result['tokens']} tokens")
            else:
                result.errors.append(f"{phase_name}: {phase_result['error']}")
                print(f"    ✗ ERROR: {phase_result['error']}")
                break
        
        result.end_time = datetime.now()
        result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
        return result
    
    async def test_mixed_providers(self, requirement: str) -> TestResult:
        """Test B: Mixed Claude + OpenAI - alternating providers"""
        print("\n" + "="*80)
        print("TEST B: MIXED (Alternating Claude + OpenAI)")
        print("="*80)
        result = TestResult("B_Mixed_REAL")
        result.start_time = datetime.now()
        
        # Alternate between Claude and OpenAI
        phases = [
            ("requirements", "architect", "claude_agent", "Analyze requirement"),
            ("architecture", "architect_openai", "openai", "Design architecture"),
            ("implementation", "code_writer", "claude_agent", "Implementation plan"),
            ("review", "reviewer_openai", "openai", "Review plan")
        ]
        
        context = requirement
        
        for phase_name, persona, expected_provider, prompt in phases:
            print(f"\n  Phase: {phase_name} (persona={persona}, target={expected_provider})")
            
            phase_result = await self.execute_phase(persona, phase_name, prompt, context)
            
            if phase_result['success']:
                result.phase_durations[phase_name] = phase_result['duration']
                result.phases_completed.append(phase_name)
                result.providers_used[phase_name] = phase_result['provider']
                result.total_tokens += phase_result['tokens']
                result.outputs[phase_name] = phase_result['output']
                context = phase_result['output']
                
                actual = phase_result['provider']
                match = "✓" if actual == expected_provider else "⚠"
                print(f"    {match} {phase_result['duration']:.0f}ms | {actual} | {phase_result['tokens']} tokens")
            else:
                result.errors.append(f"{phase_name}: {phase_result['error']}")
                print(f"    ✗ ERROR: {phase_result['error']}")
                break
        
        result.end_time = datetime.now()
        result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
        return result
    
    async def test_full_openai(self, requirement: str) -> TestResult:
        """Test C: Full OpenAI using real OpenAI API"""
        print("\n" + "="*80)
        print("TEST C: FULL OPENAI (Real OpenAI API)")
        print("="*80)
        result = TestResult("C_FullOpenAI_REAL")
        result.start_time = datetime.now()
        
        # Use _openai personas which prefer OpenAI
        phases = [
            ("requirements", "architect_openai", "Analyze requirement"),
            ("architecture", "architect_openai", "Design architecture"),
            ("implementation", "code_writer_openai", "Implementation plan"),
            ("review", "reviewer_openai", "Review plan")
        ]
        
        context = requirement
        
        for phase_name, persona, prompt in phases:
            print(f"\n  Phase: {phase_name} (persona={persona})")
            
            phase_result = await self.execute_phase(persona, phase_name, prompt, context)
            
            if phase_result['success']:
                result.phase_durations[phase_name] = phase_result['duration']
                result.phases_completed.append(phase_name)
                result.providers_used[phase_name] = phase_result['provider']
                result.total_tokens += phase_result['tokens']
                result.outputs[phase_name] = phase_result['output']
                context = phase_result['output']
                
                print(f"    ✓ {phase_result['duration']:.0f}ms | {phase_result['provider']} | {phase_result['tokens']} tokens")
            else:
                result.errors.append(f"{phase_name}: {phase_result['error']}")
                print(f"    ✗ ERROR: {phase_result['error']}")
                break
        
        result.end_time = datetime.now()
        result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
        return result
    
    async def run_comparison(self, requirement: str) -> Dict[str, Any]:
        """Run all three REAL test configurations and compare"""
        print("\n" + "="*80)
        print("REAL PROVIDER COMPARISON TEST")
        print("="*80)
        print(f"\nRequirement:\n{requirement}\n")
        
        results = []
        
        # Test A: Full Claude
        result_a = await self.test_full_claude(requirement)
        results.append(result_a)
        
        # Small delay between tests
        await asyncio.sleep(1)
        
        # Test B: Mixed
        result_b = await self.test_mixed_providers(requirement)
        results.append(result_b)
        
        await asyncio.sleep(1)
        
        # Test C: Full OpenAI
        result_c = await self.test_full_openai(requirement)
        results.append(result_c)
        
        # Generate comparison report
        report = self.generate_comparison_report(results)
        
        # Save results
        self.save_results(results, report)
        
        return report
    
    def generate_comparison_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate comprehensive comparison report"""
        print("\n" + "="*80)
        print("COMPARISON RESULTS")
        print("="*80)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "configurations": [],
            "comparison": {},
            "provider_usage": {}
        }
        
        all_providers = set()
        
        for result in results:
            config_data = result.to_dict()
            report["configurations"].append(config_data)
            
            print(f"\n{result.config_name}:")
            print(f"  Total Duration: {result.duration_ms:.0f}ms")
            print(f"  Phases Completed: {len(result.phases_completed)}/4")
            print(f"  Total Tokens: {result.total_tokens}")
            print(f"  Success: {'✓ YES' if not result.errors else '✗ NO'}")
            
            if result.providers_used:
                print(f"  Providers Used:")
                for phase, provider in result.providers_used.items():
                    duration = result.phase_durations.get(phase, 0)
                    print(f"    - {phase}: {provider} ({duration:.0f}ms)")
                    all_providers.add(provider)
            
            if result.errors:
                print(f"  Errors:")
                for error in result.errors:
                    print(f"    - {error}")
        
        # Calculate comparison metrics
        successful = [r for r in results if not r.errors]
        if successful:
            durations = [r.duration_ms for r in successful]
            tokens = [r.total_tokens for r in successful]
            
            report["comparison"] = {
                "fastest": min(durations),
                "slowest": max(durations),
                "average": sum(durations) / len(durations),
                "min_tokens": min(tokens),
                "max_tokens": max(tokens),
                "avg_tokens": sum(tokens) / len(tokens)
            }
        
        report["provider_usage"]["unique_providers"] = list(all_providers)
        
        print("\n" + "="*80)
        print("SUMMARY:")
        if report["comparison"]:
            print(f"  Fastest Configuration: {report['comparison']['fastest']:.0f}ms")
            print(f"  Slowest Configuration: {report['comparison']['slowest']:.0f}ms")
            print(f"  Token Usage Range: {report['comparison']['min_tokens']} - {report['comparison']['max_tokens']}")
        print(f"  Providers Tested: {', '.join(all_providers)}")
        print("="*80 + "\n")
        
        return report
    
    def save_results(self, results: List[TestResult], report: Dict[str, Any]):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save individual results
        for result in results:
            filename = f"{result.config_name}_{timestamp}.json"
            filepath = self.output_dir / filename
            with open(filepath, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"✓ Saved: {filepath}")
        
        # Save comparison report
        report_file = self.output_dir / f"REAL_comparison_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✓ Saved: {report_file}")
        
        # Save detailed markdown summary
        summary_file = self.output_dir / f"REAL_comparison_summary_{timestamp}.md"
        with open(summary_file, 'w') as f:
            f.write("# Real Provider Comparison Test Results\n\n")
            f.write(f"**Date**: {report['timestamp']}\n\n")
            f.write("## Test Configurations\n\n")
            
            for config in report['configurations']:
                f.write(f"### {config['config_name']}\n\n")
                f.write(f"- **Duration**: {config['duration_ms']:.0f}ms\n")
                f.write(f"- **Phases**: {len(config['phases_completed'])}/4\n")
                f.write(f"- **Tokens**: {config['total_tokens']}\n")
                f.write(f"- **Success**: {'✓' if config['success'] else '✗'}\n\n")
                
                if config['providers_used']:
                    f.write("**Provider Usage:**\n\n")
                    f.write("| Phase | Provider | Duration |\n")
                    f.write("|-------|----------|----------|\n")
                    for phase, provider in config['providers_used'].items():
                        duration = config['phase_durations'].get(phase, 0)
                        f.write(f"| {phase} | {provider} | {duration:.0f}ms |\n")
                    f.write("\n")
                
                if config.get('outputs_preview'):
                    f.write("**Output Samples:**\n\n")
                    for phase, preview in config['outputs_preview'].items():
                        f.write(f"*{phase}*: {preview}\n\n")
                
                if config['errors']:
                    f.write("**Errors:**\n\n")
                    for error in config['errors']:
                        f.write(f"- {error}\n")
                    f.write("\n")
            
            if report.get('comparison'):
                f.write("## Performance Comparison\n\n")
                comp = report['comparison']
                f.write(f"- **Fastest**: {comp['fastest']:.0f}ms\n")
                f.write(f"- **Slowest**: {comp['slowest']:.0f}ms\n")
                f.write(f"- **Average**: {comp['average']:.0f}ms\n")
                f.write(f"- **Token Range**: {comp['min_tokens']} - {comp['max_tokens']}\n")
        
        print(f"✓ Saved: {summary_file}")


async def main():
    """Main test execution"""
    requirement = """
Create a RESTful API for a todo/task management system with these features:
1. User authentication (JWT-based)
2. CRUD operations for tasks
3. Task priorities (low, medium, high)
4. Due dates and reminders
5. Categories/tags for tasks
6. User can share tasks with other users
7. Basic statistics endpoint

Include: API endpoints design, data models, authentication flow, and error handling strategy.
"""
    
    output_dir = Path("/home/ec2-user/projects/maestro-platform/execution-platform/test-results/real-comparison")
    comparator = RealWorkflowComparator(output_dir)
    
    try:
        report = await comparator.run_comparison(requirement)
        print("\n✓ Real provider comparison test complete!")
        print(f"✓ Results saved to: {output_dir}")
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
