#!/usr/bin/env python3.11
"""
Enhanced SDLC Engine V4.1 - Persona-Level Granular Reuse

Evolution beyond V4 project-level cloning to persona-level intelligent reuse.

V4 Limitation:
    Overall similarity 50% → runs full SDLC
    Misses that specific personas may have 90-100% matches

V4.1 Innovation:
    Analyzes EACH persona independently
    Example:
        Overall: 52% similar (V4 would run full SDLC)

        BUT persona-level:
        - system_architect: 100% match → REUSE architecture
        - frontend_engineer: 90% match → REUSE UI components
        - backend_engineer: 35% match → BUILD fresh
        - database_engineer: 28% match → BUILD fresh
        - security_engineer: 95% match → REUSE security

        Result: Fast-track 3 personas, execute 7 = 30% savings
        (V4 would have 0% savings!)

Generic Framework:
    NOT hardcoded - configurable per persona domain
    Each persona has:
    - Domain definition (what they care about)
    - Spec extractors (architecture, frontend, backend, etc.)
    - Similarity matchers (weighted comparison)
    - Reuse thresholds (when to reuse vs build)

Usage:
    python3.11 enhanced_sdlc_engine_v4_1.py \\
        --requirement "Create task system with custom workflows" \\
        --output ./task_system \\
        --maestro-ml-url http://localhost:8000 \\
        --enable-persona-reuse
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from dataclasses import dataclass
import httpx

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig

# Import persona loader
from personas import SDLCPersonas

# Import V4 components (reuse!)
from enhanced_sdlc_engine_v4 import (
    EnhancedSDLCEngineV4,
    RequirementAnalyzerV4,
    MaestroMLClient,
    SDLCPersonaAgentV3,
    SimilarityResult,
    ReuseStrategy
)

logger = logging.getLogger(__name__)


# ============================================================================
# V4.1 DATA STRUCTURES
# ============================================================================

@dataclass
class PersonaReuseDecision:
    """Reuse decision for a single persona"""
    persona_id: str
    similarity_score: float
    should_reuse: bool
    source_project_id: Optional[str]
    source_artifacts: List[str]
    rationale: str
    match_details: Dict[str, Any]


@dataclass
class PersonaReuseMap:
    """Complete persona-level reuse map"""
    overall_similarity: float
    persona_decisions: Dict[str, PersonaReuseDecision]
    personas_to_reuse: List[str]
    personas_to_execute: List[str]
    time_savings_percent: float
    cost_savings_dollars: float


# ============================================================================
# SELECTIVE PERSONA REUSE EXECUTOR
# ============================================================================

class SelectivePersonaReuseExecutor:
    """
    Executes selective persona reuse workflow.

    Instead of cloning entire projects (V4):
    - Analyzes each persona independently
    - Reuses specific persona artifacts when 85%+ match
    - Executes fresh personas when <85% match
    - Mix and match: reuse architect + frontend, build fresh backend + DB
    """

    def __init__(
        self,
        coordinator: Any,
        ml_client: MaestroMLClient,
        output_dir: Path,
        ml_project_id: str
    ):
        self.coordinator = coordinator
        self.ml_client = ml_client
        self.output_dir = output_dir
        self.ml_project_id = ml_project_id

    async def build_persona_reuse_map(
        self,
        requirement: str,
        requirements_md_content: str,
        persona_ids: List[str],
        similar_project_id: Optional[str] = None
    ) -> PersonaReuseMap:
        """
        Build persona-level reuse map by analyzing each persona independently.

        Generic approach - uses ML Phase 3.1 API for persona matching.

        Returns:
            PersonaReuseMap with per-persona reuse decisions
        """

        if not similar_project_id:
            # No similar project found, execute all personas
            return PersonaReuseMap(
                overall_similarity=0.0,
                persona_decisions={},
                personas_to_reuse=[],
                personas_to_execute=persona_ids,
                time_savings_percent=0.0,
                cost_savings_dollars=0.0
            )

        logger.info(f"Building persona-level reuse map against project {similar_project_id}")

        # Fetch existing project's requirements
        existing_requirements = await self._fetch_project_requirements(similar_project_id)

        # Call ML Phase 3.1 API to build reuse map
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ml_client.base_url}/api/v1/ml/persona/build-reuse-map",
                    json={
                        "new_project_requirements": requirements_md_content,
                        "existing_project_requirements": existing_requirements,
                        "persona_ids": persona_ids
                    }
                )

                if response.status_code != 200:
                    logger.warning(f"Persona reuse map failed: {response.text}")
                    # Fallback: execute all personas
                    return PersonaReuseMap(
                        overall_similarity=0.0,
                        persona_decisions={},
                        personas_to_reuse=[],
                        personas_to_execute=persona_ids,
                        time_savings_percent=0.0,
                        cost_savings_dollars=0.0
                    )

                data = response.json()

                # Build PersonaReuseDecision objects
                persona_decisions = {}
                for persona_id, match_data in data["persona_matches"].items():
                    decision = PersonaReuseDecision(
                        persona_id=persona_id,
                        similarity_score=match_data["similarity_score"],
                        should_reuse=match_data["should_reuse"],
                        source_project_id=match_data.get("source_project_id"),
                        source_artifacts=[],  # Will be populated during execution
                        rationale=match_data["rationale"],
                        match_details=match_data["match_details"]
                    )
                    persona_decisions[persona_id] = decision

                # Calculate cost savings
                cost_per_persona = 22  # $22 per persona (from V4 analysis)
                reused_count = len(data["personas_to_reuse"])
                cost_savings = reused_count * cost_per_persona

                return PersonaReuseMap(
                    overall_similarity=data["overall_similarity"],
                    persona_decisions=persona_decisions,
                    personas_to_reuse=data["personas_to_reuse"],
                    personas_to_execute=data["personas_to_execute"],
                    time_savings_percent=data["estimated_time_savings_percent"],
                    cost_savings_dollars=cost_savings
                )

        except Exception as e:
            logger.error(f"Error building persona reuse map: {e}")
            # Fallback: execute all personas
            return PersonaReuseMap(
                overall_similarity=0.0,
                persona_decisions={},
                personas_to_reuse=[],
                personas_to_execute=persona_ids,
                time_savings_percent=0.0,
                cost_savings_dollars=0.0
            )

    async def _fetch_project_requirements(self, project_id: str) -> str:
        """Fetch requirements from existing project"""
        try:
            # In real implementation, this would fetch from artifact storage
            # For now, return placeholder
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.ml_client.base_url}/api/v1/projects/{project_id}/artifacts/REQUIREMENTS.md"
                )

                if response.status_code == 200:
                    return response.text

        except Exception as e:
            logger.warning(f"Could not fetch requirements for {project_id}: {e}")

        # Fallback
        return "# Requirements\n(Not available)"

    async def execute_selective_reuse_workflow(
        self,
        requirement: str,
        reuse_map: PersonaReuseMap,
        specs: Dict
    ) -> Dict[str, Any]:
        """
        Execute selective persona reuse workflow.

        Steps:
        1. For personas_to_reuse: Fetch and integrate artifacts
        2. For personas_to_execute: Run fresh
        3. Validate integration

        Returns:
            Execution results with artifacts
        """

        results = {
            "reused_personas": [],
            "executed_personas": [],
            "artifacts": {},
            "integration_status": "pending"
        }

        # Step 1: Reuse personas
        for persona_id in reuse_map.personas_to_reuse:
            logger.info(f"⚡ REUSING {persona_id} artifacts (no execution needed)")

            decision = reuse_map.persona_decisions[persona_id]

            # Fetch artifacts from source project
            artifacts = await self._fetch_persona_artifacts(
                decision.source_project_id,
                persona_id
            )

            results["reused_personas"].append({
                "persona_id": persona_id,
                "source_project_id": decision.source_project_id,
                "similarity_score": decision.similarity_score,
                "artifacts": artifacts,
                "rationale": decision.rationale
            })

            results["artifacts"][persona_id] = artifacts

        # Step 2: Execute fresh personas
        for persona_id in reuse_map.personas_to_execute:
            logger.info(f"🔨 EXECUTING {persona_id} (building fresh)")

            # Execute persona with enhanced context
            context = self._build_persona_context(
                persona_id,
                requirement,
                specs,
                reuse_map
            )

            persona_result = await self._execute_persona(
                persona_id,
                requirement,
                context
            )

            results["executed_personas"].append({
                "persona_id": persona_id,
                "status": persona_result.get("status"),
                "artifacts": persona_result.get("artifacts", []),
                "execution_time": persona_result.get("execution_time")
            })

            results["artifacts"][persona_id] = persona_result.get("artifacts", [])

        # Step 3: Validate integration
        validation_result = await self._validate_selective_integration(
            results,
            reuse_map
        )

        results["integration_status"] = validation_result["status"]
        results["validation_details"] = validation_result

        return results

    async def _fetch_persona_artifacts(
        self,
        source_project_id: str,
        persona_id: str
    ) -> List[str]:
        """Fetch artifacts for a specific persona from source project"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.ml_client.base_url}/api/v1/projects/{source_project_id}/artifacts",
                    params={"persona": persona_id}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("artifacts", [])

        except Exception as e:
            logger.warning(f"Could not fetch artifacts for {persona_id}: {e}")

        return []

    def _build_persona_context(
        self,
        persona_id: str,
        requirement: str,
        specs: Dict,
        reuse_map: PersonaReuseMap
    ) -> str:
        """
        Build enhanced context for persona execution.

        Includes information about which personas are being reused
        to help guide integration.
        """

        reused_info = "\n".join([
            f"- {pid}: {reuse_map.persona_decisions[pid].rationale}"
            for pid in reuse_map.personas_to_reuse
        ])

        context = f"""
# Execution Context for {persona_id}

## Requirement
{requirement}

## Reused Personas (Already Available)
The following personas are being reused from a similar project:

{reused_info or "(None)"}

## Your Task
You are executing fresh because your domain has significant differences from the existing project.
However, you should integrate with the reused components above.

## Specifications
{json.dumps(specs, indent=2)}

Please proceed with your implementation, ensuring compatibility with reused components.
"""

        return context

    async def _execute_persona(
        self,
        persona_id: str,
        requirement: str,
        context: str
    ) -> Dict[str, Any]:
        """Execute a single persona"""
        try:
            # Load persona definition
            persona_def = SDLCPersonas.get_persona(persona_id)

            # Create agent
            agent = SDLCPersonaAgentV3(
                name=persona_id,
                role=AgentRole.SPECIALIST,
                coordinator=self.coordinator,
                persona_id=persona_id,
                ml_client=self.ml_client,
                ml_project_id=self.ml_project_id,
                enable_artifact_reuse=True
            )

            # Execute with context
            start_time = datetime.now()
            result = await agent.execute(
                task=f"{context}\n\n{persona_def.get('task_template', '')}"
            )
            end_time = datetime.now()

            return {
                "status": "success",
                "artifacts": result.get("artifacts", []),
                "execution_time": (end_time - start_time).total_seconds()
            }

        except Exception as e:
            logger.error(f"Error executing {persona_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "artifacts": []
            }

    async def _validate_selective_integration(
        self,
        results: Dict,
        reuse_map: PersonaReuseMap
    ) -> Dict[str, Any]:
        """Validate integration of reused and executed personas"""

        validation = {
            "status": "success",
            "issues": [],
            "warnings": []
        }

        # Check if all required personas are covered
        all_personas = set(reuse_map.personas_to_reuse + reuse_map.personas_to_execute)
        covered_personas = set(
            [p["persona_id"] for p in results["reused_personas"]] +
            [p["persona_id"] for p in results["executed_personas"]]
        )

        missing = all_personas - covered_personas
        if missing:
            validation["issues"].append(f"Missing personas: {missing}")
            validation["status"] = "failed"

        # Check for integration concerns
        if reuse_map.personas_to_reuse and reuse_map.personas_to_execute:
            validation["warnings"].append(
                "Mixed reuse and fresh execution - ensure compatibility"
            )

        return validation


# ============================================================================
# ENHANCED SDLC ENGINE V4.1 (Persona-Level Reuse)
# ============================================================================

class EnhancedSDLCEngineV4_1(EnhancedSDLCEngineV4):
    """
    V4.1 with persona-level granular reuse.

    Extends V4 to support selective persona reuse instead of just
    project-level cloning.
    """

    async def execute_sdlc_v4_1(
        self,
        requirement: str,
        persona_ids: Optional[List[str]] = None,
        enable_persona_reuse: bool = True,
        force_full_sdlc: bool = False
    ) -> Dict[str, Any]:
        """
        Execute SDLC with persona-level intelligent reuse.

        Args:
            requirement: User requirement
            persona_ids: Personas to use (default: all 10)
            enable_persona_reuse: Enable granular persona-level reuse
            force_full_sdlc: Force full SDLC bypass reuse

        Returns:
            Execution results with persona-level reuse details
        """

        if persona_ids is None:
            persona_ids = [
                "requirement_analyst",
                "system_architect",
                "backend_engineer",
                "frontend_engineer",
                "database_engineer",
                "api_engineer",
                "security_engineer",
                "testing_engineer",
                "devops_engineer",
                "deployment_engineer"
            ]

        start_time = datetime.now()

        # Step 1: Run requirement analyst (always runs first)
        logger.info("=== V4.1 SDLC Execution: Persona-Level Reuse ===")
        logger.info("Step 1: Analyzing requirements...")

        analyzer = RequirementAnalyzerV4(
            coordinator=self.coordinator,
            ml_client=self.ml_client,
            output_dir=self.output_dir,
            ml_project_id=self.ml_project_id
        )

        specs, similarity_result, reuse_strategy = await analyzer.analyze_with_similarity(requirement)

        requirements_md_path = self.output_dir / "REQUIREMENTS.md"
        requirements_md_content = requirements_md_path.read_text() if requirements_md_path.exists() else ""

        # Step 2: Decide execution path
        if force_full_sdlc or not similarity_result.similar_project_found:
            logger.info("No similar project found or forced full SDLC. Executing all personas.")
            # Fallback to V4
            return await super().execute_sdlc_v4(requirement, force_full_sdlc=True)

        # Step 3: V4.1 Persona-Level Analysis
        if enable_persona_reuse:
            logger.info("Step 2: Building persona-level reuse map...")

            selective_executor = SelectivePersonaReuseExecutor(
                coordinator=self.coordinator,
                ml_client=self.ml_client,
                output_dir=self.output_dir,
                ml_project_id=self.ml_project_id
            )

            reuse_map = await selective_executor.build_persona_reuse_map(
                requirement=requirement,
                requirements_md_content=requirements_md_content,
                persona_ids=persona_ids,
                similar_project_id=similarity_result.project_id
            )

            # Log persona-level decisions
            logger.info(f"Overall similarity: {reuse_map.overall_similarity:.1%}")
            logger.info(f"Personas to REUSE ({len(reuse_map.personas_to_reuse)}): {reuse_map.personas_to_reuse}")
            logger.info(f"Personas to EXECUTE ({len(reuse_map.personas_to_execute)}): {reuse_map.personas_to_execute}")
            logger.info(f"Time savings: {reuse_map.time_savings_percent:.1f}%")
            logger.info(f"Cost savings: ${reuse_map.cost_savings_dollars:.2f}")

            # Step 4: Execute selective reuse workflow
            logger.info("Step 3: Executing selective reuse workflow...")

            execution_results = await selective_executor.execute_selective_reuse_workflow(
                requirement=requirement,
                reuse_map=reuse_map,
                specs=specs
            )

            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds() / 60.0

            return {
                "status": "success",
                "execution_mode": "persona_level_selective_reuse",
                "total_time_minutes": total_time,
                "similarity_result": {
                    "overall_similarity": reuse_map.overall_similarity,
                    "similar_project_id": similarity_result.project_id
                },
                "persona_reuse_map": {
                    "personas_reused": reuse_map.personas_to_reuse,
                    "personas_executed": reuse_map.personas_to_execute,
                    "time_savings_percent": reuse_map.time_savings_percent,
                    "cost_savings_dollars": reuse_map.cost_savings_dollars,
                    "persona_decisions": {
                        pid: {
                            "similarity_score": decision.similarity_score,
                            "should_reuse": decision.should_reuse,
                            "rationale": decision.rationale
                        }
                        for pid, decision in reuse_map.persona_decisions.items()
                    }
                },
                "execution_results": execution_results,
                "ml_project_id": self.ml_project_id
            }

        else:
            # Fallback to V4 project-level clone
            logger.info("Persona-level reuse disabled. Using V4 project-level clone.")
            return await super().execute_sdlc_v4(requirement, force_full_sdlc=False)


# ============================================================================
# CLI (for testing)
# ============================================================================

async def main():
    """Demo V4.1 with persona-level reuse"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced SDLC Engine V4.1")
    parser.add_argument("--requirement", required=True, help="Project requirement")
    parser.add_argument("--output", default="./output_v4_1", help="Output directory")
    parser.add_argument("--maestro-ml-url", default="http://localhost:8001", help="Maestro ML URL")
    parser.add_argument("--enable-persona-reuse", action="store_true", default=True, help="Enable persona-level reuse")
    parser.add_argument("--disable-persona-reuse", action="store_true", help="Disable persona-level reuse")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize coordinator (placeholder)
    from src.claude_team_sdk.coordination.team_coordinator import TeamCoordinator
    team_config = TeamConfig(
        name="SDLC Team V4.1",
        max_iterations=50
    )
    coordinator = TeamCoordinator(team_config)

    # Initialize ML client
    ml_client = MaestroMLClient(base_url=args.maestro_ml_url)

    # Create V4.1 engine
    engine = EnhancedSDLCEngineV4_1(
        coordinator=coordinator,
        base_url="http://localhost:8000",  # Placeholder
        maestro_ml_url=args.maestro_ml_url,
        output_dir=output_dir
    )

    # Execute
    enable_persona_reuse = not args.disable_persona_reuse if args.disable_persona_reuse else args.enable_persona_reuse

    result = await engine.execute_sdlc_v4_1(
        requirement=args.requirement,
        enable_persona_reuse=enable_persona_reuse
    )

    # Print summary
    print("\n" + "="*80)
    print("V4.1 EXECUTION SUMMARY")
    print("="*80)
    print(f"Status: {result['status']}")
    print(f"Execution Mode: {result['execution_mode']}")
    print(f"Total Time: {result['total_time_minutes']:.1f} minutes")

    if "persona_reuse_map" in result:
        print(f"\nPersona-Level Reuse:")
        print(f"  Reused: {len(result['persona_reuse_map']['personas_reused'])} personas")
        print(f"  Executed: {len(result['persona_reuse_map']['personas_executed'])} personas")
        print(f"  Time Savings: {result['persona_reuse_map']['time_savings_percent']:.1f}%")
        print(f"  Cost Savings: ${result['persona_reuse_map']['cost_savings_dollars']:.2f}")

    print(f"\nOutput: {output_dir}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
