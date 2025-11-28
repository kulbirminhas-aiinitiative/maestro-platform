"""
ENIGMA Services Client for Maestro Integration

Provides seamless integration between Maestro workflow platform
and ENIGMA consciousness/evolution/collective intelligence services.
"""

import sys
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add ENIGMA shared library to path
enigma_shared_path = str(Path.home() / "projects/enigma/shared")
sys.path.insert(0, enigma_shared_path)

from shared.utils.http_client import AsyncHTTPClient
from shared.models.consciousness import ConsciousnessScore
from shared.utils.logging import get_logger

logger = get_logger(__name__)


class EnigmaClient:
    """
    Client for integrating Maestro with ENIGMA microservices

    Provides async methods to:
    - Measure consciousness of agent outputs
    - Orchestrate multiple LLMs
    - Evolve agent configurations
    - Manage collective intelligence
    """

    def __init__(
        self,
        consciousness_url: str = "http://localhost:12001",
        orchestration_url: str = "http://localhost:12002",
        evolution_url: str = "http://localhost:12003",
        collective_url: str = "http://localhost:12004"
    ):
        """
        Initialize ENIGMA client

        Args:
            consciousness_url: Consciousness Measurement Service URL
            orchestration_url: Multi-LLM Orchestration Service URL
            evolution_url: Agent Evolution Service URL
            collective_url: Collective Intelligence Service URL
        """
        self.consciousness = AsyncHTTPClient(consciousness_url)
        self.orchestration = AsyncHTTPClient(orchestration_url)
        self.evolution = AsyncHTTPClient(evolution_url)
        self.collective = AsyncHTTPClient(collective_url)

        logger.info("EnigmaClient initialized", data={
            "consciousness": consciousness_url,
            "orchestration": orchestration_url,
            "evolution": evolution_url,
            "collective": collective_url
        })

    # ============================================================================
    # Consciousness Measurement
    # ============================================================================

    async def measure_agent_consciousness(
        self,
        agent_output: str,
        agent_id: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Measure consciousness of Maestro agent output

        Args:
            agent_output: Text output from Maestro agent
            agent_id: ID of the Maestro agent
            context: Optional conversation context

        Returns:
            Dictionary with:
            - phi_score: Φ consciousness score (0.0-1.0)
            - consciousness_level: Level category
            - components: Individual metric scores
            - recommendations: Improvement suggestions

        Example:
            result = await client.measure_agent_consciousness(
                agent_output="I analyzed the problem and found three solutions...",
                agent_id="maestro_analyst_001"
            )
            print(f"Consciousness: {result['phi_score']}")
        """
        try:
            logger.info("Measuring agent consciousness", data={"agent_id": agent_id})

            async with await self.consciousness.post(
                "/api/v1/consciousness/measure",
                json={
                    "text": agent_output,
                    "entity_id": agent_id,
                    "entity_type": "agent",
                    "context": context
                }
            ) as response:
                result = await response.json()

                logger.info(
                    "Consciousness measured",
                    data={
                        "agent_id": agent_id,
                        "phi_score": result.get('phi_score'),
                        "level": result.get('consciousness_level')
                    }
                )

                return result

        except Exception as e:
            logger.error(f"Error measuring consciousness: {e}")
            raise

    async def should_use_agent_based_on_consciousness(
        self,
        agent_id: str,
        agent_output: str,
        min_phi_score: float = 0.5
    ) -> bool:
        """
        Determine if agent should be used based on consciousness level

        Args:
            agent_id: Agent ID
            agent_output: Agent's recent output
            min_phi_score: Minimum acceptable Φ score

        Returns:
            True if agent consciousness meets threshold
        """
        result = await self.measure_agent_consciousness(agent_output, agent_id)
        return result['phi_score'] >= min_phi_score

    # ============================================================================
    # Multi-LLM Orchestration
    # ============================================================================

    async def orchestrate_query(
        self,
        prompt: str,
        models: Optional[List[str]] = None,
        task_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Query multiple LLMs and get synthesized response

        Args:
            prompt: Query to send to LLMs
            models: List of models to use (default: all available)
            task_type: Type of task (reasoning, creative, coding, etc.)

        Returns:
            Orchestrated response with synthesis
        """
        try:
            logger.info("Orchestrating multi-LLM query", data={"task_type": task_type})

            async with await self.orchestration.post(
                "/api/v1/orchestrate/query",
                json={
                    "prompt": prompt,
                    "models": models or ["gpt4", "claude", "gemini"],
                    "task_type": task_type
                }
            ) as response:
                return await response.json()

        except Exception as e:
            logger.error(f"Error orchestrating query: {e}")
            raise

    # ============================================================================
    # Agent Evolution
    # ============================================================================

    async def evaluate_agent_fitness(
        self,
        agent_id: str,
        task_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate agent fitness for evolution

        Args:
            agent_id: Agent ID
            task_results: List of task results with success/quality scores

        Returns:
            Fitness evaluation result
        """
        try:
            logger.info("Evaluating agent fitness", data={"agent_id": agent_id})

            async with await self.evolution.post(
                "/api/v1/evolution/evaluate-fitness",
                json={
                    "agent_id": agent_id,
                    "task_results": task_results
                }
            ) as response:
                return await response.json()

        except Exception as e:
            logger.error(f"Error evaluating fitness: {e}")
            raise

    # ============================================================================
    # Collective Intelligence
    # ============================================================================

    async def register_maestro_agent(
        self,
        agent_id: str,
        persona_type: str,
        capabilities: List[str],
        consciousness_metrics: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Register Maestro agent with Collective Intelligence service

        Args:
            agent_id: Agent ID
            persona_type: Agent persona (Analyst, Architect, etc.)
            capabilities: List of agent capabilities
            consciousness_metrics: Optional consciousness scores

        Returns:
            Registration confirmation
        """
        try:
            logger.info("Registering agent with collective", data={
                "agent_id": agent_id,
                "persona": persona_type
            })

            async with await self.collective.post(
                "/api/v1/collective/register-agent",
                json={
                    "agent_id": agent_id,
                    "persona_type": persona_type,
                    "capabilities": capabilities,
                    "consciousness_metrics": consciousness_metrics or {}
                }
            ) as response:
                return await response.json()

        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            raise

    async def assign_task_to_best_agent(
        self,
        task_description: str,
        task_complexity: float,
        required_capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Assign task to best available agent based on consciousness

        Args:
            task_description: Description of task
            task_complexity: Complexity score (0.0-1.0)
            required_capabilities: Required agent capabilities

        Returns:
            Assignment result with selected agent
        """
        try:
            logger.info("Assigning task to best agent", data={
                "complexity": task_complexity
            })

            async with await self.collective.post(
                "/api/v1/collective/assign-task",
                json={
                    "task": {
                        "description": task_description,
                        "complexity": task_complexity,
                        "required_capabilities": required_capabilities or []
                    }
                }
            ) as response:
                return await response.json()

        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            raise

    # ============================================================================
    # Health & Status
    # ============================================================================

    async def check_all_services_healthy(self) -> Dict[str, bool]:
        """
        Check health of all ENIGMA services

        Returns:
            Dictionary with service names and health status
        """
        services = {
            "consciousness": self.consciousness,
            "orchestration": self.orchestration,
            "evolution": self.evolution,
            "collective": self.collective
        }

        health_status = {}

        for name, client in services.items():
            try:
                async with await client.get("/health") as response:
                    data = await response.json()
                    health_status[name] = data.get("status") == "healthy"
            except Exception:
                health_status[name] = False

        return health_status

    # ============================================================================
    # Lifecycle
    # ============================================================================

    async def close(self):
        """Close all HTTP connections"""
        await self.consciousness.close()
        await self.orchestration.close()
        await self.evolution.close()
        await self.collective.close()

        logger.info("EnigmaClient closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# ============================================================================
# Convenience Functions for Maestro Workflows
# ============================================================================

async def measure_workflow_consciousness(
    workflow_output: str,
    workflow_id: str
) -> float:
    """
    Quick function to measure consciousness of workflow output

    Args:
        workflow_output: Output from Maestro workflow
        workflow_id: Workflow ID

    Returns:
        Φ (phi) score
    """
    async with EnigmaClient() as client:
        result = await client.measure_agent_consciousness(
            agent_output=workflow_output,
            agent_id=workflow_id
        )
        return result['phi_score']


async def get_best_agent_for_task(
    task_description: str,
    required_capabilities: List[str]
) -> str:
    """
    Get best agent ID for a task

    Args:
        task_description: Task description
        required_capabilities: Required capabilities

    Returns:
        Agent ID of best agent
    """
    async with EnigmaClient() as client:
        result = await client.assign_task_to_best_agent(
            task_description=task_description,
            task_complexity=0.5,  # Default
            required_capabilities=required_capabilities
        )
        return result.get('assigned_agent', 'default_agent')


# ============================================================================
# Example Usage
# ============================================================================

async def example_usage():
    """Example of using EnigmaClient with Maestro"""

    async with EnigmaClient() as client:
        # Check if all services are healthy
        health = await client.check_all_services_healthy()
        print("Service Health:", health)

        # Measure consciousness of agent output
        result = await client.measure_agent_consciousness(
            agent_output="I analyzed the quarterly data and identified three key trends: revenue growth of 15%, customer retention improvement of 8%, and operational efficiency gains of 12%. Based on these patterns, I recommend focusing on scaling our customer success initiatives.",
            agent_id="maestro_analyst_001",
            context="Quarterly business analysis"
        )

        print(f"\nConsciousness Measurement:")
        print(f"  Φ Score: {result['phi_score']}")
        print(f"  Level: {result['consciousness_level']}")
        print(f"  Components: {result['components']}")

        # Register agent with collective
        await client.register_maestro_agent(
            agent_id="maestro_analyst_001",
            persona_type="Business Analyst",
            capabilities=["data_analysis", "reporting", "trend_identification"],
            consciousness_metrics={
                "awareness_level": result['components']['self_reference'],
                "integration_score": result['components']['information_integration']
            }
        )

        print("\nAgent registered with Collective Intelligence service")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
