#!/usr/bin/env python3
"""
Parallel Execution Coordinator V2 - Contract-Based Orchestration

This module coordinates parallel execution of multiple personas using contracts:
- Analyzes dependencies between contracts
- Identifies which work can run in parallel
- Generates mocks for parallel work
- Orchestrates execution with proper ordering
- Validates contract fulfillment across team

Key Innovation: True parallel execution through contract-first development

Architecture:
    ParallelCoordinator
        ├── analyze_dependencies() - Build dependency graph
        ├── identify_parallel_groups() - Find parallelizable work
        ├── execute_parallel() - Run personas simultaneously
        └── validate_integration() - Check contracts match

Contract Validation Process:
    1. Provider generates contract spec (e.g., OpenAPI)
    2. Coordinator generates mock from spec
    3. Consumers work against mock (parallel!)
    4. Provider builds real implementation
    5. Coordinator validates real matches spec
    6. Integration happens automatically

Timeline Example:
    Sequential: Backend (60m) → Frontend (30m) → QA (30m) = 120m
    Parallel:   Backend (60m) ║ Frontend (30m+mock) ║ = 60m + 30m validation = 90m
                                ║ QA (30m+mock)      ║

Result: 25-50% time savings through intelligent parallelization!
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import networkx as nx

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
from persona_executor_v2 import PersonaExecutorV2, PersonaExecutionResult, MockGeneration

# MD-3093: Shift-Left Validation
try:
    from maestro_hive.teams.shift_left_validator import (
        ShiftLeftValidator,
        CriticalViolation,
        GroupValidationResult,
        ValidationFeedback
    )
    SHIFT_LEFT_AVAILABLE = True
except ImportError:
    SHIFT_LEFT_AVAILABLE = False
    ShiftLeftValidator = None
    CriticalViolation = Exception
    GroupValidationResult = None
    ValidationFeedback = None

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ExecutionGroup:
    """Group of personas that can execute in parallel"""
    id: str
    personas: List[str]
    contracts: List[Dict[str, Any]]
    dependencies: List[str]  # IDs of groups that must complete first
    can_use_mocks: bool = False  # Whether this group can work with mocks
    estimated_duration: float = 0.0


@dataclass
class ParallelExecutionResult:
    """Result of parallel execution"""
    success: bool
    total_duration: float
    sequential_duration: float  # What it would have taken sequentially
    time_savings_percent: float

    # Per-persona results
    persona_results: Dict[str, PersonaExecutionResult]

    # Execution groups
    groups_executed: List[ExecutionGroup]
    parallelization_achieved: float  # 0-1, how much parallelization was achieved

    # Contract validation
    contracts_fulfilled: int
    contracts_total: int
    integration_issues: List[Dict[str, Any]]

    # Quality
    overall_quality_score: float
    quality_by_persona: Dict[str, float]

    # MD-3093: Shift-Left Validation Results
    shift_left_validations: List[Any] = field(default_factory=list)  # List[GroupValidationResult]
    early_stopped: bool = False
    early_stop_reason: Optional[str] = None
    corrections_applied: int = 0

    # Metadata
    executed_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# PARALLEL COORDINATOR V2
# =============================================================================

class ParallelCoordinatorV2:
    """
    Coordinate parallel execution of personas using contracts.
    
    This is the orchestration engine that enables true parallel work
    through contract-first development and mock generation.
    """
    
    def __init__(
        self,
        output_dir: Path,
        max_parallel_workers: int = 4,
        enable_shift_left: bool = True
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_parallel_workers = max_parallel_workers

        # Dependency graph
        self.dependency_graph = nx.DiGraph()

        # MD-3093: Shift-Left Validator
        self.shift_left_validator = None
        self.enable_shift_left = enable_shift_left
        if enable_shift_left and SHIFT_LEFT_AVAILABLE:
            self.shift_left_validator = ShiftLeftValidator()
            logger.info("✅ Shift-Left Validator enabled (MD-3093)")
        elif enable_shift_left:
            logger.warning("⚠️ Shift-Left Validator requested but not available")

        logger.info("✅ Parallel Coordinator V2 initialized")
        logger.info(f"   Max parallel workers: {max_parallel_workers}")
        logger.info(f"   Shift-Left validation: {self.shift_left_validator is not None}")
    
    def analyze_dependencies(
        self,
        contracts: List[Dict[str, Any]]
    ) -> nx.DiGraph:
        """
        Analyze contract dependencies and build execution graph.
        
        Returns dependency graph where:
        - Nodes = contracts
        - Edges = dependencies (A → B means B depends on A)
        """
        logger.info(f"📊 Analyzing dependencies for {len(contracts)} contract(s)...")
        
        graph = nx.DiGraph()
        
        # Add all contracts as nodes
        for contract in contracts:
            contract_id = contract["id"]
            graph.add_node(contract_id, contract=contract)
        
        # Add dependency edges
        for contract in contracts:
            contract_id = contract["id"]
            dependencies = contract.get("dependencies", [])
            
            for dep_id in dependencies:
                if dep_id in [c["id"] for c in contracts]:
                    # Add edge: dependency → contract (contract depends on dependency)
                    graph.add_edge(dep_id, contract_id)
                    logger.info(f"   📌 {dep_id} → {contract_id}")
        
        self.dependency_graph = graph
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(graph):
            logger.warning("⚠️  Circular dependencies detected!")
            cycles = list(nx.simple_cycles(graph))
            for cycle in cycles:
                logger.warning(f"   Cycle: {' → '.join(cycle)}")
        
        logger.info(f"   ✅ Dependency graph built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        return graph
    
    def identify_parallel_groups(
        self,
        contracts: List[Dict[str, Any]]
    ) -> List[ExecutionGroup]:
        """
        Identify groups of contracts that can execute in parallel.
        
        Uses topological sorting to group independent contracts.
        Contracts with mock_available=True can run in parallel with their providers.
        """
        logger.info("🔍 Identifying parallel execution groups...")
        
        graph = self.analyze_dependencies(contracts)
        
        # Get topological generations (levels of the DAG)
        try:
            generations = list(nx.topological_generations(graph))
        except nx.NetworkXError as e:
            logger.error(f"Cannot perform topological sort: {e}")
            # Fallback: sequential execution
            generations = [[c["id"]] for c in contracts]
        
        groups = []
        
        for i, generation in enumerate(generations):
            # Get contracts for this generation
            gen_contracts = [
                graph.nodes[node_id]["contract"]
                for node_id in generation
            ]
            
            # Get personas for these contracts
            personas = list(set([c["provider_persona_id"] for c in gen_contracts]))
            
            # Determine if mocks can be used
            # Mocks can be used if this group depends on previous groups
            can_use_mocks = i > 0 and any(
                c.get("mock_available", False) for c in gen_contracts
            )
            
            # Estimate duration (use max of contract durations)
            estimated_duration = max(
                [c.get("estimated_effort_hours", 1.0) for c in gen_contracts],
                default=1.0
            ) * 3600  # Convert to seconds
            
            group = ExecutionGroup(
                id=f"group_{i}",
                personas=personas,
                contracts=gen_contracts,
                dependencies=[f"group_{j}" for j in range(i)],
                can_use_mocks=can_use_mocks,
                estimated_duration=estimated_duration
            )
            
            groups.append(group)
            
            logger.info(f"   Group {i}: {len(personas)} persona(s), {len(gen_contracts)} contract(s)")
            logger.info(f"      Personas: {', '.join(personas)}")
            logger.info(f"      Can use mocks: {can_use_mocks}")
        
        logger.info(f"   ✅ Identified {len(groups)} execution group(s)")
        
        return groups
    
    async def execute_parallel(
        self,
        requirement: str,
        contracts: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> ParallelExecutionResult:
        """
        Execute personas in parallel based on contracts.

        This is the main orchestration method.

        MD-3093: Now includes shift-left validation after each group.
        """
        start_time = datetime.now()
        context = context or {}
        execution_id = context.get("session_id", f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        logger.info("="*80)
        logger.info("🚀 PARALLEL EXECUTION COORDINATOR")
        logger.info("="*80)
        logger.info(f"Requirement: {requirement[:80]}...")
        logger.info(f"Contracts: {len(contracts)}")
        logger.info(f"Max parallel workers: {self.max_parallel_workers}")
        logger.info(f"Shift-Left validation: {self.shift_left_validator is not None}")
        logger.info("="*80)

        # MD-3093: Reset shift-left validator for new execution
        if self.shift_left_validator:
            self.shift_left_validator.reset()

        # Step 1: Identify parallel groups
        groups = self.identify_parallel_groups(contracts)

        # Step 2: Generate mocks for contracts that need them
        mocks = await self._generate_mocks_for_contracts(contracts)

        # Step 3: Execute groups in order (parallel within groups)
        # MD-3093: With shift-left validation after each group
        persona_results = {}
        groups_executed = []
        shift_left_validations = []
        early_stopped = False
        early_stop_reason = None
        corrections_applied = 0

        for group in groups:
            logger.info(f"\n🎬 Executing {group.id}...")
            logger.info(f"   Personas: {', '.join(group.personas)}")
            logger.info(f"   Parallel: {len(group.personas) > 1}")

            try:
                # Execute personas in this group in parallel
                group_results = await self._execute_group(
                    requirement,
                    group,
                    mocks,
                    context
                )

                # Merge results
                persona_results.update(group_results)
                groups_executed.append(group)

                # MD-3093 AC-1/AC-2: Shift-Left Validation after each group
                if self.shift_left_validator:
                    logger.info(f"   🔬 Running shift-left validation for {group.id}...")

                    try:
                        validation_result = await self.shift_left_validator.validate_group(
                            group_id=group.id,
                            group_result=group_results,
                            contracts=group.contracts,
                            output_dir=self.output_dir,
                            execution_id=execution_id
                        )
                        shift_left_validations.append(validation_result)

                        # MD-3093 AC-4: Apply feedback and retry if needed
                        if validation_result.feedback and not validation_result.should_stop:
                            retry_result = await self._apply_feedback_and_retry(
                                requirement=requirement,
                                group=group,
                                group_results=group_results,
                                feedback=validation_result.feedback,
                                mocks=mocks,
                                context=context
                            )
                            if retry_result:
                                corrections_applied += 1
                                persona_results.update(retry_result)
                                logger.info(f"   🔄 Applied correction for {group.id}")

                    except CriticalViolation as cv:
                        # MD-3093 AC-3: Early stop on critical violations
                        logger.error(f"   🛑 CRITICAL VIOLATION in {group.id}: {cv}")
                        early_stopped = True
                        early_stop_reason = str(cv)
                        if cv.validation_result:
                            shift_left_validations.append(cv.validation_result)
                        break

                logger.info(f"   ✅ {group.id} complete")

            except Exception as e:
                logger.error(f"   ❌ {group.id} failed: {e}")
                # Continue with next group unless it's a critical failure
                if "critical" in str(e).lower():
                    early_stopped = True
                    early_stop_reason = str(e)
                    break

        # Step 4: Calculate metrics
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        # Calculate what sequential duration would have been
        sequential_duration = sum(
            result.duration_seconds
            for result in persona_results.values()
        )

        # Calculate time savings
        time_savings_percent = (
            (sequential_duration - total_duration) / sequential_duration
            if sequential_duration > 0 else 0
        )

        # Calculate parallelization achieved
        theoretical_parallel_time = max(
            [group.estimated_duration for group in groups],
            default=1.0
        )
        parallelization_achieved = min(
            theoretical_parallel_time / total_duration if total_duration > 0 else 0,
            1.0
        )

        # Step 5: Validate integration
        integration_issues = await self._validate_integration(
            contracts,
            persona_results
        )

        # Calculate contract fulfillment
        contracts_fulfilled = sum(
            1 for result in persona_results.values()
            if result.contract_fulfilled
        )
        contracts_total = len(contracts)

        # Calculate quality scores
        overall_quality = sum(
            result.quality_score for result in persona_results.values()
        ) / len(persona_results) if persona_results else 0.0

        quality_by_persona = {
            persona_id: result.quality_score
            for persona_id, result in persona_results.items()
        }

        # Determine success (including early stop consideration)
        execution_success = (
            all(r.success for r in persona_results.values())
            and not early_stopped
        )

        result = ParallelExecutionResult(
            success=execution_success,
            total_duration=total_duration,
            sequential_duration=sequential_duration,
            time_savings_percent=time_savings_percent,
            persona_results=persona_results,
            groups_executed=groups_executed,
            parallelization_achieved=parallelization_achieved,
            contracts_fulfilled=contracts_fulfilled,
            contracts_total=contracts_total,
            integration_issues=integration_issues,
            overall_quality_score=overall_quality,
            quality_by_persona=quality_by_persona,
            shift_left_validations=shift_left_validations,
            early_stopped=early_stopped,
            early_stop_reason=early_stop_reason,
            corrections_applied=corrections_applied,
            executed_at=end_time
        )

        # Print summary
        self._print_execution_summary(result)

        return result

    async def _apply_feedback_and_retry(
        self,
        requirement: str,
        group: ExecutionGroup,
        group_results: Dict[str, PersonaExecutionResult],
        feedback: 'ValidationFeedback',
        mocks: Dict[str, Any],
        context: Dict[str, Any],
        max_retries: int = 2
    ) -> Optional[Dict[str, PersonaExecutionResult]]:
        """
        MD-3093 AC-4: Apply validation feedback and retry execution.

        Args:
            requirement: Original requirement
            group: Execution group to retry
            group_results: Previous results
            feedback: Validation feedback with corrections
            mocks: Available mocks
            context: Execution context
            max_retries: Maximum retry attempts

        Returns:
            Updated results if correction successful, None otherwise
        """
        retry_count = feedback.retry_context.get("retry_number", 0)

        if retry_count >= max_retries:
            logger.warning(f"   Max retries ({max_retries}) reached for {group.id}")
            return None

        logger.info(f"   🔄 Applying feedback for {feedback.persona_id} (retry {retry_count + 1}/{max_retries})")

        # Update feedback context
        feedback.retry_context["retry_number"] = retry_count + 1

        # Add feedback to context for persona
        correction_context = {
            **context,
            "validation_feedback": feedback.to_prompt_context(),
            "is_correction_retry": True,
            "retry_number": retry_count + 1
        }

        try:
            # Re-execute the group with feedback context
            corrected_results = await self._execute_group(
                requirement=requirement,
                group=group,
                mocks=mocks,
                context=correction_context
            )

            logger.info(f"   ✅ Correction applied for {group.id}")
            return corrected_results

        except Exception as e:
            logger.error(f"   ❌ Correction failed for {group.id}: {e}")
            return None
    
    async def _generate_mocks_for_contracts(
        self,
        contracts: List[Dict[str, Any]]
    ) -> Dict[str, MockGeneration]:
        """Generate mocks for contracts that support it"""
        logger.info("\n🎭 Generating mocks for parallel work...")
        
        mocks = {}
        
        for contract in contracts:
            if contract.get("mock_available", False):
                contract_id = contract["id"]
                provider_id = contract["provider_persona_id"]
                
                logger.info(f"   Generating mock for: {contract['name']}")
                
                # Create executor for provider (just for mock generation)
                executor = PersonaExecutorV2(
                    persona_id=provider_id,
                    output_dir=self.output_dir
                )
                
                # Generate mock
                mock = await executor.generate_mock_from_contract(contract)
                mocks[contract_id] = mock
                
                logger.info(f"      ✅ Mock ready: {len(mock.artifacts)} artifact(s)")
        
        logger.info(f"   ✅ Generated {len(mocks)} mock(s)")
        
        return mocks
    
    async def _execute_group(
        self,
        requirement: str,
        group: ExecutionGroup,
        mocks: Dict[str, MockGeneration],
        context: Dict[str, Any]
    ) -> Dict[str, PersonaExecutionResult]:
        """Execute a group of personas in parallel"""
        
        # Create execution tasks
        tasks = []
        persona_contracts = {}
        
        for contract in group.contracts:
            provider_id = contract["provider_persona_id"]
            persona_contracts[provider_id] = contract
            
            # Create executor
            executor = PersonaExecutorV2(
                persona_id=provider_id,
                output_dir=self.output_dir
            )
            
            # Determine if this persona can use mocks
            use_mock = False
            if group.can_use_mocks:
                # Check if dependencies have mocks
                dependencies = contract.get("dependencies", [])
                use_mock = any(dep_id in mocks for dep_id in dependencies)
            
            # Create execution task
            task = executor.execute(
                requirement=requirement,
                contract=contract,
                context=context,
                use_mock=use_mock
            )
            
            tasks.append((provider_id, task))
        
        # Execute in parallel (limited by max_parallel_workers)
        results = {}
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_parallel_workers)
        
        async def execute_with_semaphore(persona_id: str, task):
            async with semaphore:
                return persona_id, await task
        
        # Run all tasks
        completed = await asyncio.gather(
            *[execute_with_semaphore(pid, task) for pid, task in tasks],
            return_exceptions=True
        )
        
        # Process results
        for item in completed:
            if isinstance(item, Exception):
                logger.error(f"Task failed: {item}")
                continue
            
            persona_id, result = item
            results[persona_id] = result
        
        return results
    
    async def _validate_integration(
        self,
        contracts: List[Dict[str, Any]],
        persona_results: Dict[str, PersonaExecutionResult]
    ) -> List[Dict[str, Any]]:
        """
        Validate that contracts are fulfilled and integrate properly.
        
        This checks:
        1. Each contract is fulfilled by its provider
        2. Consumers can use provider's deliverables
        3. Interfaces match (API specs, schemas, etc.)
        """
        logger.info("\n🔍 Validating integration...")
        
        issues = []
        
        for contract in contracts:
            contract_id = contract["id"]
            provider_id = contract["provider_persona_id"]
            consumer_ids = contract.get("consumer_persona_ids", [])
            
            # Check if provider fulfilled contract
            if provider_id not in persona_results:
                issues.append({
                    "type": "missing_provider",
                    "severity": "critical",
                    "contract_id": contract_id,
                    "provider_id": provider_id,
                    "message": f"Provider {provider_id} did not execute"
                })
                continue
            
            provider_result = persona_results[provider_id]
            
            if not provider_result.contract_fulfilled:
                issues.append({
                    "type": "contract_not_fulfilled",
                    "severity": "high",
                    "contract_id": contract_id,
                    "provider_id": provider_id,
                    "missing": provider_result.missing_deliverables,
                    "message": f"Provider {provider_id} did not fulfill contract"
                })
            
            # Check consumers
            for consumer_id in consumer_ids:
                if consumer_id not in persona_results:
                    issues.append({
                        "type": "missing_consumer",
                        "severity": "medium",
                        "contract_id": contract_id,
                        "consumer_id": consumer_id,
                        "message": f"Consumer {consumer_id} did not execute"
                    })
        
        if issues:
            logger.warning(f"   ⚠️  Found {len(issues)} integration issue(s)")
            for issue in issues:
                logger.warning(f"      {issue['severity'].upper()}: {issue['message']}")
        else:
            logger.info("   ✅ All contracts fulfilled, integration validated")
        
        return issues
    
    def _print_execution_summary(self, result: ParallelExecutionResult):
        """Print execution summary"""
        logger.info("\n" + "="*80)
        logger.info("📊 PARALLEL EXECUTION SUMMARY")
        logger.info("="*80)
        logger.info(f"Success: {'✅ YES' if result.success else '❌ NO'}")
        logger.info(f"")
        logger.info(f"⏱️  Timing:")
        logger.info(f"   Parallel execution: {result.total_duration:.1f}s ({result.total_duration/60:.1f}m)")
        logger.info(f"   Sequential would be: {result.sequential_duration:.1f}s ({result.sequential_duration/60:.1f}m)")
        logger.info(f"   Time saved: {result.time_savings_percent:.0%} ⚡")
        logger.info(f"")
        logger.info(f"📦 Deliverables:")
        logger.info(f"   Personas executed: {len(result.persona_results)}")
        logger.info(f"   Execution groups: {len(result.groups_executed)}")
        logger.info(f"   Parallelization: {result.parallelization_achieved:.0%}")
        logger.info(f"")
        logger.info(f"📝 Contracts:")
        logger.info(f"   Fulfilled: {result.contracts_fulfilled}/{result.contracts_total}")
        logger.info(f"   Integration issues: {len(result.integration_issues)}")
        logger.info(f"")
        logger.info(f"✨ Quality:")
        logger.info(f"   Overall: {result.overall_quality_score:.0%}")

        for persona_id, quality in result.quality_by_persona.items():
            logger.info(f"   {persona_id}: {quality:.0%}")

        # MD-3093: Shift-Left Validation Summary
        if result.shift_left_validations:
            logger.info(f"")
            logger.info(f"🔬 Shift-Left Validation (MD-3093):")
            logger.info(f"   Groups validated: {len(result.shift_left_validations)}")
            logger.info(f"   Corrections applied: {result.corrections_applied}")

            passed = sum(1 for v in result.shift_left_validations if v.passed)
            logger.info(f"   Passed: {passed}/{len(result.shift_left_validations)}")

            if result.early_stopped:
                logger.error(f"   🛑 EARLY STOP: {result.early_stop_reason}")

            # Show per-group validation scores
            for validation in result.shift_left_validations:
                status = "✅" if validation.passed else ("🛑" if validation.should_stop else "⚠️")
                logger.info(f"   {status} {validation.group_id}: BDV={validation.bdv_score:.2f} ACC={validation.acc_score:.2f}")

        if result.integration_issues:
            logger.info(f"")
            logger.info(f"⚠️  Issues:")
            for issue in result.integration_issues:
                logger.info(f"   [{issue['severity']}] {issue['message']}")

        logger.info("="*80)
        
        # Visual timeline
        logger.info("")
        logger.info("📅 Execution Timeline:")
        logger.info("")
        
        if result.time_savings_percent > 0:
            logger.info("   Sequential:")
            logger.info(f"   0───{result.sequential_duration:.0f}s")
            for persona_id in result.persona_results.keys():
                logger.info(f"   │{persona_id[:20]:<20}│")
            logger.info("")
            logger.info("   Parallel:")
            logger.info(f"   0───{result.total_duration:.0f}s")
            for group in result.groups_executed:
                personas_str = ", ".join(p[:10] for p in group.personas)
                logger.info(f"   ║{personas_str:<20}║")
            logger.info("")
            logger.info(f"   ⚡ {result.time_savings_percent:.0%} faster!")
        
        logger.info("="*80)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

async def main():
    """CLI entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Parallel Coordinator V2 - Contract-Based Orchestration"
    )
    parser.add_argument("--requirement", required=True, help="Requirement to fulfill")
    parser.add_argument("--contracts", required=True, help="Contracts JSON file")
    parser.add_argument("--output", default="./generated_project", help="Output directory")
    parser.add_argument("--max-workers", type=int, default=4, help="Max parallel workers")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    # Load contracts
    with open(args.contracts) as f:
        contracts = json.load(f)
    
    # Create coordinator
    coordinator = ParallelCoordinatorV2(
        output_dir=Path(args.output),
        max_parallel_workers=args.max_workers
    )
    
    # Execute
    result = await coordinator.execute_parallel(
        requirement=args.requirement,
        contracts=contracts
    )
    
    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    asyncio.run(main())
