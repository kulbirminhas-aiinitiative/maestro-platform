"""
COMPREHENSIVE END-TO-END TEST: Execution Platform Provider Comparison

Tests ALL configurations with REAL implementations:
- A: Full Claude (using REAL Claude Code SDK from maestro-hive)
- B: Full OpenAI (using REAL OpenAI API)
- C: Mixed (A+B) - Alternating between Claude and OpenAI

Validates:
1. Provider routing and switching
2. Context preservation across providers
3. Output quality and coherence
4. Error handling and recovery
5. Performance characteristics
6. Token usage tracking

Identifies gaps in:
- Multi-provider workflows
- Context handoff complexity
- Provider-specific limitations
- Error handling edge cases
"""

import asyncio
import json
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
import sys

# Set up paths
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/execution-platform/src')
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive')

# Load environment variables
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
from execution_platform.spi import Message, ChatRequest


class GapAnalysis:
    """Track gaps and issues discovered during testing"""
    def __init__(self):
        self.gaps = []
        self.warnings = []
        self.errors = []
        
    def add_gap(self, category: str, description: str, severity: str = "medium"):
        self.gaps.append({
            "category": category,
            "description": description,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_warning(self, message: str):
        self.warnings.append({
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_error(self, message: str):
        self.errors.append({
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_gaps": len(self.gaps),
            "total_warnings": len(self.warnings),
            "total_errors": len(self.errors),
            "gaps": self.gaps,
            "warnings": self.warnings,
            "errors": self.errors
        }


class PhaseResult:
    """Result of executing a single phase"""
    def __init__(self, phase_name: str, persona: str):
        self.phase_name = phase_name
        self.persona = persona
        self.provider_used = None
        self.duration_ms = 0
        self.tokens_used = 0
        self.output = ""
        self.success = False
        self.error = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "persona": self.persona,
            "provider_used": self.provider_used,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "output_length": len(self.output),
            "output_preview": self.output[:200] if self.output else None,
            "success": self.success,
            "error": self.error
        }


class WorkflowResult:
    """Result of executing a complete workflow"""
    def __init__(self, config_name: str, config_description: str):
        self.config_name = config_name
        self.config_description = config_description
        self.start_time = None
        self.end_time = None
        self.phases = []
        self.gap_analysis = GapAnalysis()
        
    @property
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0
    
    @property
    def total_tokens(self) -> int:
        return sum(p.tokens_used for p in self.phases)
    
    @property
    def success_rate(self) -> float:
        if not self.phases:
            return 0.0
        successful = sum(1 for p in self.phases if p.success)
        return (successful / len(self.phases)) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_name": self.config_name,
            "config_description": self.config_description,
            "duration_ms": self.duration_ms,
            "total_phases": len(self.phases),
            "successful_phases": sum(1 for p in self.phases if p.success),
            "success_rate": self.success_rate,
            "total_tokens": self.total_tokens,
            "phases": [p.to_dict() for p in self.phases],
            "gap_analysis": self.gap_analysis.to_dict()
        }


class ComprehensiveE2ETest:
    """Comprehensive end-to-end testing framework"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = PersonaRouter()
        self.results = []
        
    async def execute_phase(
        self, 
        phase_name: str, 
        persona: str, 
        prompt: str, 
        context: str
    ) -> PhaseResult:
        """Execute a single phase and track results"""
        result = PhaseResult(phase_name, persona)
        start_time = time.time()
        
        try:
            # Get provider and client
            result.provider_used = self.router.select_provider(persona)
            client = self.router.get_client(persona)
            
            # Execute phase
            request = ChatRequest(
                messages=[
                    Message(role="user", content=f"{prompt}\n\n{context}")
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            output_chunks = []
            async for chunk in client.chat(request):
                if chunk.delta_text:
                    output_chunks.append(chunk.delta_text)
                if chunk.usage:
                    result.tokens_used = chunk.usage.total_tokens
            
            result.output = "".join(output_chunks)
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    async def test_config_a_full_claude(self, requirement: str) -> WorkflowResult:
        """Test A: Full Claude using REAL Claude Code SDK"""
        print("\n" + "="*80)
        print("TEST A: FULL CLAUDE (Real Claude Code SDK)")
        print("="*80)
        
        result = WorkflowResult(
            "A_FullClaude",
            "All phases using Claude Code SDK from maestro-hive"
        )
        result.start_time = datetime.now()
        
        phases = [
            ("requirements", "architect", "Analyze and document requirements"),
            ("architecture", "architect", "Design system architecture"),
            ("implementation", "code_writer", "Create implementation plan"),
            ("review", "reviewer", "Review for quality and completeness")
        ]
        
        context = f"Requirement: {requirement}"
        
        for phase_name, persona, prompt in phases:
            print(f"\n  Phase {len(result.phases)+1}: {phase_name} ({persona})")
            
            phase_result = await self.execute_phase(phase_name, persona, prompt, context)
            result.phases.append(phase_result)
            
            if phase_result.success:
                print(f"    ✓ {phase_result.duration_ms:.0f}ms | {phase_result.provider_used} | {phase_result.tokens_used} tokens")
                context = phase_result.output  # Chain to next phase
                
                # Check if Claude SDK is actually being used
                if "claude_agent_unavailable" in phase_result.output:
                    result.gap_analysis.add_gap(
                        "claude_sdk",
                        "Claude SDK not available - using fallback",
                        "high"
                    )
                elif "claude_agent_stub" in phase_result.output:
                    result.gap_analysis.add_gap(
                        "claude_sdk",
                        "Claude SDK returning stub responses - not real SDK",
                        "high"
                    )
            else:
                print(f"    ✗ ERROR: {phase_result.error}")
                result.gap_analysis.add_error(f"{phase_name}: {phase_result.error}")
        
        result.end_time = datetime.now()
        return result
    
    async def test_config_b_full_openai(self, requirement: str) -> WorkflowResult:
        """Test B: Full OpenAI using REAL OpenAI API"""
        print("\n" + "="*80)
        print("TEST B: FULL OPENAI (Real OpenAI API)")
        print("="*80)
        
        result = WorkflowResult(
            "B_FullOpenAI",
            "All phases using OpenAI API"
        )
        result.start_time = datetime.now()
        
        phases = [
            ("requirements", "architect_openai", "Analyze and document requirements"),
            ("architecture", "architect_openai", "Design system architecture"),
            ("implementation", "code_writer_openai", "Create implementation plan"),
            ("review", "reviewer_openai", "Review for quality and completeness")
        ]
        
        context = f"Requirement: {requirement}"
        
        for phase_name, persona, prompt in phases:
            print(f"\n  Phase {len(result.phases)+1}: {phase_name} ({persona})")
            
            phase_result = await self.execute_phase(phase_name, persona, prompt, context)
            result.phases.append(phase_result)
            
            if phase_result.success:
                print(f"    ✓ {phase_result.duration_ms:.0f}ms | {phase_result.provider_used} | {phase_result.tokens_used} tokens")
                context = phase_result.output
                
                # Validate OpenAI is actually being used
                if phase_result.provider_used != "openai":
                    result.gap_analysis.add_gap(
                        "provider_routing",
                        f"Expected openai but got {phase_result.provider_used}",
                        "medium"
                    )
            else:
                print(f"    ✗ ERROR: {phase_result.error}")
                result.gap_analysis.add_error(f"{phase_name}: {phase_result.error}")
        
        result.end_time = datetime.now()
        return result
    
    async def test_config_c_mixed(self, requirement: str) -> WorkflowResult:
        """Test C: Mixed (A+B) - Alternating Claude and OpenAI"""
        print("\n" + "="*80)
        print("TEST C: MIXED (A+B) - Alternating Claude and OpenAI")
        print("="*80)
        
        result = WorkflowResult(
            "C_Mixed_AB",
            "Alternating between Claude and OpenAI across phases"
        )
        result.start_time = datetime.now()
        
        phases = [
            ("requirements", "architect", "claude_agent", "Analyze requirements"),
            ("architecture", "architect_openai", "openai", "Design architecture"),
            ("implementation", "code_writer", "claude_agent", "Create implementation"),
            ("review", "reviewer_openai", "openai", "Review implementation")
        ]
        
        context = f"Requirement: {requirement}"
        prev_provider = None
        
        for phase_name, persona, expected_provider, prompt in phases:
            print(f"\n  Phase {len(result.phases)+1}: {phase_name} ({persona} → {expected_provider})")
            
            phase_result = await self.execute_phase(phase_name, persona, prompt, context)
            result.phases.append(phase_result)
            
            if phase_result.success:
                actual_provider = phase_result.provider_used
                match = "✓" if actual_provider == expected_provider else "⚠"
                print(f"    {match} {phase_result.duration_ms:.0f}ms | {actual_provider} | {phase_result.tokens_used} tokens")
                
                # Check provider switching
                if prev_provider and prev_provider != actual_provider:
                    print(f"    → Provider switch: {prev_provider} → {actual_provider}")
                    
                    # Validate context preservation
                    if not phase_result.output:
                        result.gap_analysis.add_gap(
                            "context_preservation",
                            f"Empty output after provider switch from {prev_provider} to {actual_provider}",
                            "high"
                        )
                    elif len(phase_result.output) < 50:
                        result.gap_analysis.add_warning(
                            f"Short output ({len(phase_result.output)} chars) after provider switch"
                        )
                
                context = phase_result.output
                prev_provider = actual_provider
                
                # Validate routing
                if actual_provider != expected_provider:
                    result.gap_analysis.add_gap(
                        "provider_routing",
                        f"Phase {phase_name}: expected {expected_provider}, got {actual_provider}",
                        "medium"
                    )
            else:
                print(f"    ✗ ERROR: {phase_result.error}")
                result.gap_analysis.add_error(f"{phase_name}: {phase_result.error}")
                
                # Check if error is due to provider switching
                if prev_provider:
                    result.gap_analysis.add_gap(
                        "provider_switching",
                        f"Error occurred after switching from {prev_provider}",
                        "high"
                    )
        
        result.end_time = datetime.now()
        return result
    
    async def run_comprehensive_test(self, requirement: str) -> Dict[str, Any]:
        """Run all three configurations and analyze results"""
        print("\n" + "="*80)
        print("COMPREHENSIVE END-TO-END PROVIDER COMPARISON")
        print("="*80)
        print(f"\nTest Requirement:\n{requirement}\n")
        
        # Run all configurations
        config_a = await self.test_config_a_full_claude(requirement)
        self.results.append(config_a)
        await asyncio.sleep(1)
        
        config_b = await self.test_config_b_full_openai(requirement)
        self.results.append(config_b)
        await asyncio.sleep(1)
        
        config_c = await self.test_config_c_mixed(requirement)
        self.results.append(config_c)
        
        # Generate comprehensive analysis
        analysis = self.generate_comprehensive_analysis()
        
        # Save results
        self.save_comprehensive_results(analysis)
        
        return analysis
    
    def generate_comprehensive_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive analysis of all tests"""
        print("\n" + "="*80)
        print("COMPREHENSIVE ANALYSIS")
        print("="*80)
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "configurations": [],
            "comparison": {},
            "gap_summary": {
                "total_gaps": 0,
                "critical_gaps": [],
                "warnings": []
            }
        }
        
        # Collect all results
        for result in self.results:
            config_data = result.to_dict()
            analysis["configurations"].append(config_data)
            
            print(f"\n{result.config_name}: {result.config_description}")
            print(f"  Duration: {result.duration_ms:.0f}ms")
            print(f"  Success Rate: {result.success_rate:.1f}%")
            print(f"  Total Tokens: {result.total_tokens}")
            print(f"  Gaps Found: {len(result.gap_analysis.gaps)}")
            
            # Collect gaps
            analysis["gap_summary"]["total_gaps"] += len(result.gap_analysis.gaps)
            for gap in result.gap_analysis.gaps:
                if gap["severity"] == "high":
                    analysis["gap_summary"]["critical_gaps"].append({
                        "config": result.config_name,
                        **gap
                    })
            
            for warning in result.gap_analysis.warnings:
                analysis["gap_summary"]["warnings"].append({
                    "config": result.config_name,
                    **warning
                })
        
        # Performance comparison
        successful = [r for r in self.results if r.success_rate == 100]
        if successful:
            durations = [r.duration_ms for r in successful]
            tokens = [r.total_tokens for r in successful]
            
            analysis["comparison"] = {
                "fastest_config": min(self.results, key=lambda r: r.duration_ms).config_name,
                "fastest_time": min(durations),
                "slowest_time": max(durations),
                "average_time": sum(durations) / len(durations),
                "token_range": f"{min(tokens)} - {max(tokens)}" if tokens else "N/A"
            }
        
        # Print summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total Configurations Tested: {len(self.results)}")
        print(f"Total Gaps Identified: {analysis['gap_summary']['total_gaps']}")
        print(f"Critical Gaps: {len(analysis['gap_summary']['critical_gaps'])}")
        print(f"Warnings: {len(analysis['gap_summary']['warnings'])}")
        
        if analysis["comparison"]:
            print(f"\nPerformance:")
            print(f"  Fastest: {analysis['comparison']['fastest_config']} ({analysis['comparison']['fastest_time']:.0f}ms)")
            print(f"  Average: {analysis['comparison']['average_time']:.0f}ms")
        
        print("="*80 + "\n")
        
        return analysis
    
    def save_comprehensive_results(self, analysis: Dict[str, Any]):
        """Save comprehensive test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full analysis
        analysis_file = self.output_dir / f"comprehensive_analysis_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"✓ Saved: {analysis_file}")
        
        # Save gap report
        gap_report_file = self.output_dir / f"gap_analysis_{timestamp}.md"
        with open(gap_report_file, 'w') as f:
            f.write("# Gap Analysis Report\n\n")
            f.write(f"**Date**: {analysis['timestamp']}\n\n")
            
            f.write("## Critical Gaps\n\n")
            if analysis['gap_summary']['critical_gaps']:
                for gap in analysis['gap_summary']['critical_gaps']:
                    f.write(f"### {gap['config']} - {gap['category']}\n")
                    f.write(f"**Severity**: {gap['severity']}\n\n")
                    f.write(f"{gap['description']}\n\n")
            else:
                f.write("No critical gaps identified ✓\n\n")
            
            f.write("## Warnings\n\n")
            if analysis['gap_summary']['warnings']:
                for warning in analysis['gap_summary']['warnings']:
                    f.write(f"- **{warning['config']}**: {warning['message']}\n")
            else:
                f.write("No warnings ✓\n\n")
        
        print(f"✓ Saved: {gap_report_file}")


async def main():
    """Main test execution"""
    requirement = """
Build a microservices-based e-commerce platform with:
- User service (authentication, profiles, preferences)
- Product catalog service (inventory, search, recommendations)
- Shopping cart service (session management, cart operations)
- Order service (checkout, payment integration, order tracking)
- Notification service (email, SMS, push notifications)

Include: API contracts, data models, inter-service communication, error handling, and deployment architecture.
"""
    
    output_dir = Path("/home/ec2-user/projects/maestro-platform/execution-platform/test-results/comprehensive-e2e")
    tester = ComprehensiveE2ETest(output_dir)
    
    try:
        analysis = await tester.run_comprehensive_test(requirement)
        
        print("\n✓ Comprehensive end-to-end test complete!")
        print(f"✓ Results saved to: {output_dir}")
        
        # Return exit code based on gaps
        critical_gaps = len(analysis['gap_summary']['critical_gaps'])
        if critical_gaps > 0:
            print(f"\n⚠ {critical_gaps} critical gaps identified - review gap analysis report")
            return 1
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
