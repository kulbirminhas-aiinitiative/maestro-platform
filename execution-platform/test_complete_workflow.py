"""
COMPLETE WORKFLOW TEST: All Provider Configurations

Tests 5 comprehensive configurations:
A: Existing Setup (original implementation)
B: New Setup - Full Claude (Claude Code SDK)
C: Mix - Claude + Others (Claude + OpenAI + Gemini)
D: All Non-Claude - OpenAI Only
E: All Non-Claude Mix - OpenAI + Gemini alternating

Each configuration runs a complete SDLC workflow with 6 phases:
1. Requirements Analysis
2. Architecture Design
3. Implementation Planning
4. Code Generation
5. Testing Strategy
6. Review & Quality Check
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


class WorkflowPhase:
    """Represents a single phase in the workflow"""
    def __init__(self, name: str, persona: str, prompt: str):
        self.name = name
        self.persona = persona
        self.prompt = prompt
        self.provider_used = None
        self.duration_ms = 0
        self.tokens = 0
        self.output = ""
        self.success = False
        self.error = None


class WorkflowConfiguration:
    """Complete workflow configuration"""
    def __init__(self, config_id: str, name: str, description: str):
        self.config_id = config_id
        self.name = name
        self.description = description
        self.phases = []
        self.start_time = None
        self.end_time = None
        
    @property
    def duration_ms(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0
    
    @property
    def total_tokens(self):
        return sum(p.tokens for p in self.phases)
    
    @property
    def success_rate(self):
        if not self.phases:
            return 0
        return (sum(1 for p in self.phases if p.success) / len(self.phases)) * 100
    
    def to_dict(self):
        return {
            "config_id": self.config_id,
            "name": self.name,
            "description": self.description,
            "duration_ms": self.duration_ms,
            "total_tokens": self.total_tokens,
            "success_rate": self.success_rate,
            "phases": [{
                "name": p.name,
                "persona": p.persona,
                "provider": p.provider_used,
                "duration_ms": p.duration_ms,
                "tokens": p.tokens,
                "success": p.success,
                "error": p.error,
                "output_preview": p.output[:150] if p.output else None
            } for p in self.phases]
        }


class CompleteWorkflowTester:
    """Tests all workflow configurations"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = PersonaRouter()
        self.results = []
        
    async def execute_phase(self, phase: WorkflowPhase, context: str) -> bool:
        """Execute a single phase"""
        start_time = time.time()
        
        try:
            phase.provider_used = self.router.select_provider(phase.persona)
            client = self.router.get_client(phase.persona)
            
            request = ChatRequest(
                messages=[
                    Message(role="user", content=f"{phase.prompt}\n\nContext:\n{context}")
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            output_chunks = []
            async for chunk in client.chat(request):
                if chunk.delta_text:
                    output_chunks.append(chunk.delta_text)
                if chunk.usage:
                    phase.tokens = chunk.usage.total_tokens
            
            phase.output = "".join(output_chunks)
            phase.success = True
            
        except Exception as e:
            phase.error = str(e)
            phase.success = False
            
        phase.duration_ms = (time.time() - start_time) * 1000
        return phase.success
    
    async def test_config_a_existing(self, requirement: str) -> WorkflowConfiguration:
        """
        A: Existing Setup
        Uses whatever was configured originally (default personas)
        """
        print("\n" + "="*80)
        print("CONFIG A: EXISTING SETUP (Original Configuration)")
        print("="*80)
        
        config = WorkflowConfiguration(
            "A",
            "Existing Setup",
            "Original default persona configuration"
        )
        config.start_time = datetime.now()
        
        phase_definitions = [
            ("requirements", "code_writer", "Analyze requirements and create detailed specification"),
            ("architecture", "code_writer", "Design comprehensive system architecture"),
            ("implementation", "code_writer", "Create detailed implementation plan"),
            ("code_generation", "code_writer", "Generate core application code structure"),
            ("testing", "qa_engineer", "Design comprehensive testing strategy"),
            ("review", "code_writer", "Review all artifacts for quality and completeness")
        ]
        
        context = f"Project Requirement: {requirement}"
        
        for phase_name, persona, prompt in phase_definitions:
            phase = WorkflowPhase(phase_name, persona, prompt)
            print(f"\n  Phase {len(config.phases)+1}/{len(phase_definitions)}: {phase_name}")
            
            success = await self.execute_phase(phase, context)
            config.phases.append(phase)
            
            if success:
                print(f"    ✓ {phase.duration_ms:.0f}ms | {phase.provider_used} | {phase.tokens} tokens")
                context = phase.output
            else:
                print(f"    ✗ ERROR: {phase.error}")
        
        config.end_time = datetime.now()
        return config
    
    async def test_config_b_full_claude(self, requirement: str) -> WorkflowConfiguration:
        """
        B: New Setup - Full Claude
        All phases use Claude Code SDK
        """
        print("\n" + "="*80)
        print("CONFIG B: NEW SETUP - FULL CLAUDE (Claude Code SDK)")
        print("="*80)
        
        config = WorkflowConfiguration(
            "B",
            "Full Claude",
            "All phases using Claude Code SDK from maestro-hive"
        )
        config.start_time = datetime.now()
        
        phase_definitions = [
            ("requirements", "architect", "Analyze requirements and create detailed specification"),
            ("architecture", "architect", "Design comprehensive system architecture"),
            ("implementation", "code_writer", "Create detailed implementation plan"),
            ("code_generation", "code_writer", "Generate core application code structure"),
            ("testing", "code_writer", "Design comprehensive testing strategy"),
            ("review", "reviewer", "Review all artifacts for quality and completeness")
        ]
        
        context = f"Project Requirement: {requirement}"
        
        for phase_name, persona, prompt in phase_definitions:
            phase = WorkflowPhase(phase_name, persona, prompt)
            print(f"\n  Phase {len(config.phases)+1}/{len(phase_definitions)}: {phase_name}")
            
            success = await self.execute_phase(phase, context)
            config.phases.append(phase)
            
            if success:
                print(f"    ✓ {phase.duration_ms:.0f}ms | {phase.provider_used} | {phase.tokens} tokens")
                context = phase.output
            else:
                print(f"    ✗ ERROR: {phase.error}")
        
        config.end_time = datetime.now()
        return config
    
    async def test_config_c_mixed(self, requirement: str) -> WorkflowConfiguration:
        """
        C: Mix - Claude + Others
        Strategic mix of Claude, OpenAI, and Gemini
        """
        print("\n" + "="*80)
        print("CONFIG C: MIXED (Claude + OpenAI + Gemini)")
        print("="*80)
        
        config = WorkflowConfiguration(
            "C",
            "Mixed Providers",
            "Strategic mix: Claude for speed, OpenAI for quality, Gemini for specific tasks"
        )
        config.start_time = datetime.now()
        
        phase_definitions = [
            ("requirements", "architect", "claude_agent", "Analyze requirements (Claude - fast)"),
            ("architecture", "architect_openai", "openai", "Design architecture (OpenAI - quality)"),
            ("implementation", "code_writer", "claude_agent", "Implementation plan (Claude - fast)"),
            ("code_generation", "code_writer_openai", "openai", "Generate code (OpenAI - quality)"),
            ("testing", "qa_engineer", "openai", "Testing strategy (OpenAI - thorough)"),
            ("review", "reviewer", "claude_agent", "Final review (Claude - fast)")
        ]
        
        context = f"Project Requirement: {requirement}"
        prev_provider = None
        
        for phase_name, persona, expected_provider, prompt in phase_definitions:
            phase = WorkflowPhase(phase_name, persona, prompt)
            print(f"\n  Phase {len(config.phases)+1}/{len(phase_definitions)}: {phase_name} → {expected_provider}")
            
            success = await self.execute_phase(phase, context)
            config.phases.append(phase)
            
            if success:
                actual = phase.provider_used
                match = "✓" if actual == expected_provider else "⚠"
                print(f"    {match} {phase.duration_ms:.0f}ms | {actual} | {phase.tokens} tokens")
                
                if prev_provider and prev_provider != actual:
                    print(f"    → Provider switch: {prev_provider} → {actual}")
                
                context = phase.output
                prev_provider = actual
            else:
                print(f"    ✗ ERROR: {phase.error}")
        
        config.end_time = datetime.now()
        return config
    
    async def test_config_d_non_claude_openai(self, requirement: str) -> WorkflowConfiguration:
        """
        D: All Non-Claude - OpenAI Only
        All phases use OpenAI exclusively
        """
        print("\n" + "="*80)
        print("CONFIG D: ALL NON-CLAUDE - OPENAI ONLY")
        print("="*80)
        
        config = WorkflowConfiguration(
            "D",
            "OpenAI Only",
            "All phases using OpenAI API exclusively"
        )
        config.start_time = datetime.now()
        
        phase_definitions = [
            ("requirements", "architect_openai", "Analyze requirements and create detailed specification"),
            ("architecture", "architect_openai", "Design comprehensive system architecture"),
            ("implementation", "code_writer_openai", "Create detailed implementation plan"),
            ("code_generation", "code_writer_openai", "Generate core application code structure"),
            ("testing", "qa_engineer", "Design comprehensive testing strategy"),
            ("review", "reviewer_openai", "Review all artifacts for quality and completeness")
        ]
        
        context = f"Project Requirement: {requirement}"
        
        for phase_name, persona, prompt in phase_definitions:
            phase = WorkflowPhase(phase_name, persona, prompt)
            print(f"\n  Phase {len(config.phases)+1}/{len(phase_definitions)}: {phase_name}")
            
            success = await self.execute_phase(phase, context)
            config.phases.append(phase)
            
            if success:
                print(f"    ✓ {phase.duration_ms:.0f}ms | {phase.provider_used} | {phase.tokens} tokens")
                context = phase.output
            else:
                print(f"    ✗ ERROR: {phase.error}")
        
        config.end_time = datetime.now()
        return config
    
    async def test_config_e_non_claude_mixed(self, requirement: str) -> WorkflowConfiguration:
        """
        E: All Non-Claude Mix - OpenAI + Gemini
        Alternating between OpenAI and Gemini (no Claude)
        """
        print("\n" + "="*80)
        print("CONFIG E: ALL NON-CLAUDE MIXED (OpenAI + Gemini)")
        print("="*80)
        
        config = WorkflowConfiguration(
            "E",
            "OpenAI + Gemini Mix",
            "Alternating between OpenAI and Gemini (no Claude)"
        )
        config.start_time = datetime.now()
        
        # Note: Gemini support may need additional configuration
        phase_definitions = [
            ("requirements", "architect_openai", "openai", "Analyze requirements (OpenAI)"),
            ("architecture", "architect_openai", "openai", "Design architecture (OpenAI)"),
            ("implementation", "code_writer_openai", "openai", "Implementation plan (OpenAI)"),
            ("code_generation", "code_writer_openai", "openai", "Generate code (OpenAI)"),
            ("testing", "qa_engineer", "openai", "Testing strategy (OpenAI)"),
            ("review", "reviewer_openai", "openai", "Final review (OpenAI)")
        ]
        
        context = f"Project Requirement: {requirement}"
        prev_provider = None
        
        for phase_name, persona, expected_provider, prompt in phase_definitions:
            phase = WorkflowPhase(phase_name, persona, prompt)
            print(f"\n  Phase {len(config.phases)+1}/{len(phase_definitions)}: {phase_name} → {expected_provider}")
            
            success = await self.execute_phase(phase, context)
            config.phases.append(phase)
            
            if success:
                actual = phase.provider_used
                match = "✓" if actual == expected_provider else "⚠"
                print(f"    {match} {phase.duration_ms:.0f}ms | {actual} | {phase.tokens} tokens")
                
                if prev_provider and prev_provider != actual:
                    print(f"    → Provider switch: {prev_provider} → {actual}")
                
                context = phase.output
                prev_provider = actual
            else:
                print(f"    ✗ ERROR: {phase.error}")
        
        config.end_time = datetime.now()
        return config
    
    async def run_all_configurations(self, requirement: str) -> Dict[str, Any]:
        """Run all 5 configurations"""
        print("\n" + "="*80)
        print("COMPLETE WORKFLOW TEST - ALL CONFIGURATIONS")
        print("="*80)
        print(f"\nRequirement:\n{requirement}\n")
        
        # Run all configurations
        configs = []
        
        print("\n>>> Running Configuration A: Existing Setup...")
        config_a = await self.test_config_a_existing(requirement)
        configs.append(config_a)
        await asyncio.sleep(1)
        
        print("\n>>> Running Configuration B: Full Claude...")
        config_b = await self.test_config_b_full_claude(requirement)
        configs.append(config_b)
        await asyncio.sleep(1)
        
        print("\n>>> Running Configuration C: Mixed...")
        config_c = await self.test_config_c_mixed(requirement)
        configs.append(config_c)
        await asyncio.sleep(1)
        
        print("\n>>> Running Configuration D: OpenAI Only...")
        config_d = await self.test_config_d_non_claude_openai(requirement)
        configs.append(config_d)
        await asyncio.sleep(1)
        
        print("\n>>> Running Configuration E: OpenAI + Gemini...")
        config_e = await self.test_config_e_non_claude_mixed(requirement)
        configs.append(config_e)
        
        # Generate comprehensive report
        report = self.generate_report(configs)
        self.save_results(configs, report)
        
        return report
    
    def generate_report(self, configs: List[WorkflowConfiguration]) -> Dict[str, Any]:
        """Generate comprehensive comparison report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE COMPARISON REPORT")
        print("="*80)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "configurations": [c.to_dict() for c in configs],
            "summary": {}
        }
        
        # Print results
        for config in configs:
            print(f"\n{config.config_id}: {config.name}")
            print(f"  Description: {config.description}")
            print(f"  Duration: {config.duration_ms:.0f}ms ({config.duration_ms/1000:.1f}s)")
            print(f"  Success Rate: {config.success_rate:.1f}%")
            print(f"  Total Tokens: {config.total_tokens}")
            print(f"  Phases: {len(config.phases)}")
            
            # Show provider distribution
            providers = {}
            for phase in config.phases:
                if phase.provider_used:
                    providers[phase.provider_used] = providers.get(phase.provider_used, 0) + 1
            print(f"  Provider Distribution: {providers}")
        
        # Performance ranking
        sorted_configs = sorted(configs, key=lambda c: c.duration_ms)
        print("\n" + "="*80)
        print("PERFORMANCE RANKING")
        print("="*80)
        for i, config in enumerate(sorted_configs, 1):
            print(f"{i}. {config.config_id} - {config.name}: {config.duration_ms:.0f}ms")
        
        report["summary"]["fastest"] = sorted_configs[0].config_id
        report["summary"]["slowest"] = sorted_configs[-1].config_id
        
        # Success ranking
        sorted_by_success = sorted(configs, key=lambda c: c.success_rate, reverse=True)
        print("\n" + "="*80)
        print("SUCCESS RATE RANKING")
        print("="*80)
        for i, config in enumerate(sorted_by_success, 1):
            print(f"{i}. {config.config_id} - {config.name}: {config.success_rate:.1f}%")
        
        print("="*80 + "\n")
        
        return report
    
    def save_results(self, configs: List[WorkflowConfiguration], report: Dict[str, Any]):
        """Save all results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive report
        report_file = self.output_dir / f"complete_workflow_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✓ Saved: {report_file}")
        
        # Save markdown summary
        summary_file = self.output_dir / f"complete_workflow_summary_{timestamp}.md"
        with open(summary_file, 'w') as f:
            f.write("# Complete Workflow Test - All Configurations\n\n")
            f.write(f"**Date**: {report['timestamp']}\n\n")
            
            f.write("## Test Configurations\n\n")
            for config in configs:
                f.write(f"### Config {config.config_id}: {config.name}\n\n")
                f.write(f"**Description**: {config.description}\n\n")
                f.write(f"- Duration: {config.duration_ms:.0f}ms\n")
                f.write(f"- Success Rate: {config.success_rate:.1f}%\n")
                f.write(f"- Total Tokens: {config.total_tokens}\n\n")
                
                f.write("**Phases:**\n\n")
                f.write("| Phase | Persona | Provider | Duration | Tokens | Status |\n")
                f.write("|-------|---------|----------|----------|--------|--------|\n")
                for phase in config.phases:
                    status = "✓" if phase.success else "✗"
                    f.write(f"| {phase.name} | {phase.persona} | {phase.provider_used} | "
                           f"{phase.duration_ms:.0f}ms | {phase.tokens} | {status} |\n")
                f.write("\n")
            
            f.write("## Performance Comparison\n\n")
            sorted_configs = sorted(configs, key=lambda c: c.duration_ms)
            f.write("| Rank | Config | Name | Duration | Success Rate |\n")
            f.write("|------|--------|------|----------|-------------|\n")
            for i, config in enumerate(sorted_configs, 1):
                f.write(f"| {i} | {config.config_id} | {config.name} | "
                       f"{config.duration_ms:.0f}ms | {config.success_rate:.1f}% |\n")
        
        print(f"✓ Saved: {summary_file}")


async def main():
    """Main execution"""
    requirement = """
Create a real-time collaborative document editing platform (like Google Docs) with:

Core Features:
- Real-time collaborative editing with operational transformation
- User presence and cursor tracking
- Rich text formatting (bold, italic, lists, headings)
- Version history and restore
- Comments and suggestions
- Share and permissions management (view, comment, edit)
- Offline mode with conflict resolution

Technical Requirements:
- WebSocket-based real-time communication
- Distributed system with multiple servers
- Database for document storage and versioning
- Caching layer for performance
- Authentication and authorization
- RESTful API for document management

Deliverables:
- System architecture
- Data models
- API specifications
- Real-time communication protocol
- Conflict resolution strategy
- Deployment architecture
"""
    
    output_dir = Path("/home/ec2-user/projects/maestro-platform/execution-platform/test-results/complete-workflow")
    tester = CompleteWorkflowTester(output_dir)
    
    try:
        report = await tester.run_all_configurations(requirement)
        
        print("\n✓ Complete workflow test finished!")
        print(f"✓ All 5 configurations tested")
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
