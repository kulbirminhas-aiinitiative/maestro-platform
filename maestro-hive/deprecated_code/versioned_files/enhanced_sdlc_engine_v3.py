#!/usr/bin/env python3.11
"""
Enhanced SDLC Engine V3 - Maestro ML Integration

Builds on V2 with intelligent meta-learning capabilities for team optimization,
artifact reuse, and cost/speed optimization.

Key Enhancements over V2:
- ✅ Maestro ML artifact reuse (Music Library integration)
- ✅ Real-time metrics tracking (Git, CI/CD, velocity)
- ✅ Project success tracking and learning
- ✅ Team composition optimization (when Phase 3 ready)
- ✅ Cost/speed prediction (when Phase 3 ready)
- ✅ Artifact-aware persona execution
- ✅ Development velocity monitoring

Architecture:
    - MaestroMLClient: HTTP client for maestro_ml API
    - SDLCPersonaAgentV3: Artifact-aware persona execution
    - EnhancedSDLCEngineV3: Main orchestrator with ML integration
    - All V2 features: JSON integration, auto-ordering, validation

Usage:
    # Full SDLC with ML optimization
    python3.11 enhanced_sdlc_engine_v3.py \\
        --requirement "Build a blog platform with markdown editor" \\
        --output ./blog_project \\
        --maestro-ml-url http://localhost:8000

    # Specific personas with artifact reuse
    python3.11 enhanced_sdlc_engine_v3.py \\
        --requirement "Build REST API" \\
        --personas requirement_analyst backend_developer \\
        --output ./api_project \\
        --use-artifacts

    # Resume with analytics
    python3.11 enhanced_sdlc_engine_v3.py \\
        --resume blog_v1 \\
        --auto-complete \\
        --show-analytics
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum
import logging
from dataclasses import dataclass
import httpx

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig

# Import JSON persona loader
from personas import SDLCPersonas

# Import V2 components (reuse!)
from enhanced_sdlc_engine_v2 import (
    DependencyResolver,
    ContractValidator,
    ValidationError,
    SDLCPersonaAgent
)

logger = logging.getLogger(__name__)


# ============================================================================
# MAESTRO ML CLIENT
# ============================================================================

class MaestroMLClient:
    """
    HTTP client for Maestro ML Platform API.

    Provides methods for:
    - Artifact search and registration
    - Metrics tracking
    - Project creation and success tracking
    - Team analytics (Git, CI/CD)
    - Recommendations (Phase 3)
    """

    def __init__(self, base_url: str = "http://localhost:8000", enabled: bool = True):
        self.base_url = base_url.rstrip('/')
        self.enabled = enabled
        self.client = httpx.AsyncClient(timeout=30.0)

    async def check_health(self) -> bool:
        """Check if Maestro ML API is available"""
        if not self.enabled:
            return False

        try:
            response = await self.client.get(f"{self.base_url}/")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Maestro ML not available: {e}")
            return False

    # ========================================================================
    # PROJECT MANAGEMENT
    # ========================================================================

    async def create_project(
        self,
        name: str,
        problem_class: str,
        complexity_score: int,
        team_size: int,
        metadata: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create a new project in Maestro ML.

        Returns:
            Project data with ID, or None if disabled/failed
        """
        if not self.enabled:
            return None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/projects",
                json={
                    "name": name,
                    "problem_class": problem_class,
                    "complexity_score": complexity_score,
                    "team_size": team_size,
                    "metadata": metadata or {}
                }
            )
            response.raise_for_status()
            project = response.json()
            logger.info(f"📊 Created Maestro ML project: {project['id']}")
            return project
        except Exception as e:
            logger.warning(f"Failed to create Maestro ML project: {e}")
            return None

    async def update_project_success(
        self,
        project_id: str,
        model_accuracy: Optional[float] = None,
        business_impact_usd: Optional[float] = None,
        deployment_days: Optional[int] = None,
        compute_cost: Optional[float] = None
    ) -> Optional[Dict]:
        """Update project with success metrics"""
        if not self.enabled or not project_id:
            return None

        try:
            response = await self.client.patch(
                f"{self.base_url}/api/v1/projects/{project_id}/success",
                json={
                    "model_accuracy": model_accuracy,
                    "business_impact_usd": business_impact_usd,
                    "deployment_days": deployment_days,
                    "compute_cost": compute_cost
                }
            )
            response.raise_for_status()
            logger.info(f"✅ Updated Maestro ML project success: {project_id}")
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to update project success: {e}")
            return None

    # ========================================================================
    # ARTIFACT REGISTRY (Music Library)
    # ========================================================================

    async def search_artifacts(
        self,
        query: Optional[str] = None,
        artifact_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_impact_score: float = 70.0
    ) -> List[Dict]:
        """
        Search for high-impact reusable artifacts.

        Args:
            query: Search query (persona_id, component name, etc.)
            artifact_type: Filter by type (code_template, schema, etc.)
            tags: Filter by tags
            min_impact_score: Only return artifacts with impact score >= this

        Returns:
            List of artifact dicts with metadata
        """
        if not self.enabled:
            return []

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/artifacts/search",
                json={
                    "query": query,
                    "type": artifact_type,
                    "tags": tags,
                    "min_impact_score": min_impact_score
                }
            )
            response.raise_for_status()
            artifacts = response.json()

            if artifacts:
                logger.info(f"🎵 Found {len(artifacts)} reusable artifacts (impact score >= {min_impact_score})")

            return artifacts
        except Exception as e:
            logger.warning(f"Failed to search artifacts: {e}")
            return []

    async def register_artifact(
        self,
        name: str,
        artifact_type: str,
        version: str,
        storage_path: str,
        created_by: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Register a new artifact in the Music Library"""
        if not self.enabled:
            return None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/artifacts",
                json={
                    "name": name,
                    "type": artifact_type,
                    "version": version,
                    "storage_path": storage_path,
                    "created_by": created_by,
                    "tags": tags or [],
                    "metadata": metadata or {}
                }
            )
            response.raise_for_status()
            artifact = response.json()
            logger.debug(f"📦 Registered artifact: {name}")
            return artifact
        except Exception as e:
            logger.warning(f"Failed to register artifact: {e}")
            return None

    async def log_artifact_usage(
        self,
        artifact_id: str,
        project_id: str,
        impact_score: Optional[float] = None,
        context: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Log that an artifact was used in a project"""
        if not self.enabled or not artifact_id or not project_id:
            return None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/artifacts/{artifact_id}/use",
                json={
                    "project_id": project_id,
                    "impact_score": impact_score,
                    "context": context or {}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to log artifact usage: {e}")
            return None

    # ========================================================================
    # METRICS TRACKING
    # ========================================================================

    async def log_metric(
        self,
        project_id: str,
        metric_type: str,
        metric_value: float,
        metadata: Optional[Dict] = None
    ):
        """Log a process metric"""
        if not self.enabled or not project_id:
            return

        try:
            await self.client.post(
                f"{self.base_url}/api/v1/metrics",
                json={
                    "project_id": project_id,
                    "metric_type": metric_type,
                    "metric_value": metric_value,
                    "metadata": metadata or {}
                }
            )
            logger.debug(f"📈 Logged metric: {metric_type} = {metric_value}")
        except Exception as e:
            logger.debug(f"Failed to log metric: {e}")

    async def get_development_velocity(self, project_id: str) -> Optional[float]:
        """Get development velocity score (0-100)"""
        if not self.enabled or not project_id:
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/metrics/{project_id}/velocity"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("velocity_score")
        except Exception as e:
            logger.warning(f"Failed to get velocity: {e}")
            return None

    # ========================================================================
    # TEAM ANALYTICS
    # ========================================================================

    async def get_git_metrics(self, project_id: str, since_days: int = 7) -> Optional[Dict]:
        """Get Git collaboration metrics"""
        if not self.enabled or not project_id:
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/teams/{project_id}/git-metrics",
                params={"since_days": since_days}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get Git metrics: {e}")
            return None

    async def get_cicd_metrics(
        self,
        project_id: str,
        since_days: int = 7,
        ci_provider: str = "github_actions"
    ) -> Optional[Dict]:
        """Get CI/CD pipeline metrics"""
        if not self.enabled or not project_id:
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/teams/{project_id}/cicd-metrics",
                params={"since_days": since_days, "ci_provider": ci_provider}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get CI/CD metrics: {e}")
            return None

    # ========================================================================
    # RECOMMENDATIONS (Phase 3)
    # ========================================================================

    async def get_recommendations(
        self,
        problem_class: str,
        complexity_score: int,
        team_size: int
    ) -> Optional[Dict]:
        """
        Get ML-powered recommendations for team composition and artifacts.

        Returns:
            {
                "predicted_success_score": float,
                "predicted_duration_days": int,
                "predicted_cost": float,
                "team_composition": {...},
                "suggested_artifacts": [...]
            }
        """
        if not self.enabled:
            return None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/recommendations",
                params={
                    "problem_class": problem_class,
                    "complexity_score": complexity_score,
                    "team_size": team_size
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get recommendations: {e}")
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ============================================================================
# ARTIFACT-AWARE PERSONA AGENT (V3)
# ============================================================================

class SDLCPersonaAgentV3(SDLCPersonaAgent):
    """
    Enhanced persona agent with Maestro ML artifact awareness.

    Before execution:
    - Searches for high-impact reusable artifacts
    - Injects artifact suggestions into prompt

    After execution:
    - Registers created artifacts
    - Logs artifact usage
    """

    def __init__(self, persona_id: str, coordination_server, ml_client: Optional[MaestroMLClient] = None):
        super().__init__(persona_id, coordination_server)
        self.ml_client = ml_client
        self.project_id = None  # Set by engine
        self.used_artifacts = []

    async def execute_work_with_ml(
        self,
        requirement: str,
        output_dir: Path,
        coordinator: TeamCoordinator,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute work with ML-powered artifact awareness.

        1. Search for reusable artifacts
        2. Enhance prompt with artifact suggestions
        3. Execute persona work
        4. Register new artifacts
        5. Log metrics
        """
        self.project_id = project_id
        start_time = datetime.now()

        # Search for reusable artifacts
        artifacts = await self._search_artifacts()

        # Enhance context with artifacts
        enhanced_requirement = self._enhance_with_artifacts(requirement, artifacts)

        # Execute base work
        result = await self.execute_work(enhanced_requirement, output_dir, coordinator)

        # Register created artifacts
        if result.get("success") and self.ml_client:
            await self._register_created_artifacts(result, output_dir)

        # Log execution metrics
        if self.ml_client and project_id:
            await self._log_execution_metrics(result, start_time)

        result["artifacts_found"] = len(artifacts)
        result["artifacts_used"] = len(self.used_artifacts)

        return result

    async def _search_artifacts(self) -> List[Dict]:
        """Search for relevant artifacts for this persona"""
        if not self.ml_client:
            return []

        logger.info(f"[{self.persona_id}] 🔍 Searching for reusable artifacts...")

        # Search by persona role and type
        artifacts = await self.ml_client.search_artifacts(
            query=self.persona_id,
            tags=[self.persona_def["role"]["primary_role"]],
            min_impact_score=70.0  # Only high-impact artifacts
        )

        return artifacts

    def _enhance_with_artifacts(self, requirement: str, artifacts: List[Dict]) -> str:
        """Enhance requirement with artifact suggestions"""
        if not artifacts:
            return requirement

        artifact_text = "\n\n🎵 HIGH-IMPACT REUSABLE ARTIFACTS (Music Library):\n\n"
        artifact_text += "The following proven components are available for reuse:\n\n"

        for i, artifact in enumerate(artifacts[:5], 1):  # Top 5
            artifact_text += f"{i}. {artifact['name']}\n"
            artifact_text += f"   Type: {artifact['type']}\n"
            artifact_text += f"   Impact Score: {artifact['avg_impact_score']:.1f}/100\n"
            artifact_text += f"   Used {artifact['usage_count']} times successfully\n"
            artifact_text += f"   Location: {artifact['storage_path']}\n"
            if artifact.get('tags'):
                artifact_text += f"   Tags: {', '.join(artifact['tags'])}\n"
            artifact_text += "\n"

        artifact_text += """
💡 ARTIFACT REUSE INSTRUCTIONS:
- Review these artifacts and adapt them to your needs
- Reuse proven patterns, templates, and schemas where applicable
- Customize for this specific requirement
- This accelerates development and improves quality!

IMPORTANT: After using an artifact, mention which ones you used in your work.
"""

        return f"{requirement}\n{artifact_text}"

    async def _register_created_artifacts(self, result: Dict, output_dir: Path):
        """Register newly created artifacts in Maestro ML"""
        files_created = result.get("files_created", [])

        for file_path in files_created:
            path = Path(file_path)

            # Determine artifact type from file extension
            artifact_type = self._classify_artifact_type(path)

            # Register artifact
            await self.ml_client.register_artifact(
                name=path.name,
                artifact_type=artifact_type,
                version="1.0",
                storage_path=str(file_path),
                created_by=self.persona_id,
                tags=[
                    self.persona_def["role"]["primary_role"],
                    self.persona_id
                ],
                metadata={
                    "created_in_project": self.project_id,
                    "persona": self.persona_id
                }
            )

    def _classify_artifact_type(self, path: Path) -> str:
        """Classify artifact type from file"""
        ext = path.suffix.lower()

        type_map = {
            '.py': 'code_template',
            '.js': 'code_template',
            '.ts': 'code_template',
            '.java': 'code_template',
            '.sql': 'schema',
            '.json': 'schema',
            '.yaml': 'config',
            '.yml': 'config',
            '.md': 'documentation',
            '.ipynb': 'notebook'
        }

        return type_map.get(ext, 'other')

    async def _log_execution_metrics(self, result: Dict, start_time: datetime):
        """Log execution metrics to Maestro ML"""
        duration = result.get("duration_seconds", 0)

        # Log execution time
        await self.ml_client.log_metric(
            project_id=self.project_id,
            metric_type="persona_execution_time",
            metric_value=duration,
            metadata={"persona_id": self.persona_id}
        )

        # Log file creation count
        await self.ml_client.log_metric(
            project_id=self.project_id,
            metric_type="files_created",
            metric_value=len(result.get("files_created", [])),
            metadata={"persona_id": self.persona_id}
        )

        # Log success/failure
        success_value = 1.0 if result.get("success") else 0.0
        await self.ml_client.log_metric(
            project_id=self.project_id,
            metric_type="persona_success_rate",
            metric_value=success_value,
            metadata={"persona_id": self.persona_id}
        )


# ============================================================================
# ENHANCED SDLC ENGINE V3 (Maestro ML Integration)
# ============================================================================

class EnhancedSDLCEngineV3:
    """
    SDK-powered SDLC engine with Maestro ML integration.

    V3 Features:
    - All V2 features (JSON integration, auto-ordering, validation)
    - Artifact-aware execution (searches Music Library)
    - Real-time metrics tracking
    - Project success tracking
    - Team analytics (Git, CI/CD)
    - ML recommendations (when Phase 3 ready)
    """

    def __init__(
        self,
        output_dir: Path,
        session_id: Optional[str] = None,
        maestro_ml_url: str = "http://localhost:8000",
        use_ml: bool = True
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id or f"sdlc_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create TeamCoordinator (from V2)
        team_config = TeamConfig(
            team_id=self.session_id,
            workspace_path=self.output_dir,
            max_agents=20
        )
        self.coordinator = TeamCoordinator(team_config)
        self.coord_server = self.coordinator.create_coordination_server()

        # Maestro ML Client
        self.ml_client = MaestroMLClient(base_url=maestro_ml_url, enabled=use_ml)
        self.ml_project_id = None

        # Track state
        self.completed_personas = set()
        self.requirement = None
        self.start_time = None

    async def initialize(self):
        """Initialize and check Maestro ML connection"""
        ml_available = await self.ml_client.check_health()

        if self.ml_client.enabled:
            if ml_available:
                logger.info("✅ Maestro ML connected - artifact reuse and analytics enabled")
            else:
                logger.warning("⚠️  Maestro ML not available - running without ML features")
                self.ml_client.enabled = False
        else:
            logger.info("ℹ️  Maestro ML disabled - running in standard mode")

    async def execute_sdlc(
        self,
        requirement: str,
        persona_ids: Optional[List[str]] = None,
        problem_class: str = "general",
        complexity_score: int = 50
    ) -> Dict[str, Any]:
        """
        Execute SDLC workflow with ML optimization.

        Args:
            requirement: Project requirement
            persona_ids: Specific personas to execute (None = all)
            problem_class: Type of problem (web_app, ml_pipeline, api, etc.)
            complexity_score: 1-100 complexity estimate

        Returns:
            Execution result dict with ML analytics
        """
        self.requirement = requirement
        self.start_time = datetime.now()

        # Initialize ML
        await self.initialize()

        # Create project in Maestro ML
        if self.ml_client.enabled:
            project = await self.ml_client.create_project(
                name=self.session_id,
                problem_class=problem_class,
                complexity_score=complexity_score,
                team_size=len(persona_ids) if persona_ids else 10,
                metadata={"requirement": requirement}
            )
            if project:
                self.ml_project_id = project["id"]

        # Determine which personas to execute
        if persona_ids is None:
            all_personas = SDLCPersonas.get_all_personas()
            persona_ids = list(all_personas.keys())

        # Filter out already completed
        pending = [p for p in persona_ids if p not in self.completed_personas]

        if not pending:
            logger.info("✅ All personas already completed!")
            return self._build_result([], 0)

        logger.info("=" * 80)
        logger.info("🚀 ENHANCED SDLC ENGINE V3 - Maestro ML Integration")
        logger.info("=" * 80)
        logger.info(f"📝 Requirement: {requirement[:100]}...")
        logger.info(f"🆔 Session: {self.session_id}")
        logger.info(f"👥 Personas to execute: {len(pending)}")
        logger.info(f"📁 Output: {self.output_dir}")
        if self.ml_project_id:
            logger.info(f"📊 Maestro ML Project: {self.ml_project_id}")
        logger.info("=" * 80)

        # Auto-determine execution order (from V2)
        try:
            ordered_personas = DependencyResolver.resolve_order(pending)
            logger.info(f"\n📋 Auto-resolved execution order (from JSON dependencies):")
            for i, pid in enumerate(ordered_personas, 1):
                pdef = SDLCPersonas.get_all_personas()[pid]
                deps = pdef["dependencies"]["depends_on"]
                logger.info(f"   {i}. {pid} (depends on: {deps or 'none'})")
        except ValueError as e:
            logger.error(f"❌ Dependency resolution failed: {e}")
            return {"success": False, "error": str(e)}

        # Group for parallel execution (from V2)
        parallel_groups = DependencyResolver.group_parallel_personas(ordered_personas)
        logger.info(f"\n🔄 Parallel execution groups: {len(parallel_groups)}")
        for i, group in enumerate(parallel_groups, 1):
            if len(group) > 1:
                logger.info(f"   Group {i}: {group} (parallel)")
            else:
                logger.info(f"   Group {i}: {group}")

        # Execute groups
        all_results = []
        for group_idx, group in enumerate(parallel_groups, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"🎯 GROUP {group_idx}/{len(parallel_groups)}: {len(group)} persona(s)")
            logger.info(f"{'=' * 80}")

            if len(group) == 1:
                # Sequential execution
                result = await self._execute_persona(group[0], requirement)
                all_results.append(result)
            else:
                # Parallel execution
                logger.info(f"⚡ Executing {len(group)} personas in PARALLEL...")
                results = await asyncio.gather(*[
                    self._execute_persona(pid, requirement)
                    for pid in group
                ])
                all_results.extend(results)

            # Save session after each group
            await self._save_session()

            # Log group metrics
            if self.ml_client.enabled and self.ml_project_id:
                group_duration = sum(r.get("duration_seconds", 0) for r in all_results[-len(group):])
                await self.ml_client.log_metric(
                    project_id=self.ml_project_id,
                    metric_type="group_execution_time",
                    metric_value=group_duration,
                    metadata={"group_index": group_idx, "group_size": len(group)}
                )

        # Final results
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        # Update project success
        if self.ml_client.enabled and self.ml_project_id:
            successful = sum(1 for r in all_results if r.get("success"))
            success_rate = (successful / len(all_results)) * 100 if all_results else 0

            await self.ml_client.update_project_success(
                project_id=self.ml_project_id,
                model_accuracy=success_rate,
                deployment_days=int(duration / 86400),  # Convert to days
                compute_cost=len(all_results) * 10.0  # Rough estimate: $10 per persona
            )

        return self._build_result(all_results, duration)

    async def _execute_persona(
        self,
        persona_id: str,
        requirement: str
    ) -> Dict[str, Any]:
        """Execute single persona with ML awareness"""

        # Create V3 agent (artifact-aware)
        agent = SDLCPersonaAgentV3(persona_id, self.coord_server, self.ml_client)

        # Initialize
        await agent.initialize()

        # Execute with ML features
        result = await agent.execute_work_with_ml(
            requirement,
            self.output_dir,
            self.coordinator,
            self.ml_project_id
        )

        # Shutdown
        await agent.shutdown()

        # Track completion
        if result.get("success"):
            self.completed_personas.add(persona_id)

        return result

    def _build_result(self, results: List[Dict], duration: float) -> Dict[str, Any]:
        """Build final result dict with ML analytics"""

        workspace_state = asyncio.run(self.coordinator.get_workspace_state())

        all_files = []
        total_artifacts_found = 0
        total_artifacts_used = 0

        for r in results:
            all_files.extend(r.get("files_created", []))
            total_artifacts_found += r.get("artifacts_found", 0)
            total_artifacts_used += r.get("artifacts_used", 0)

        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful

        result = {
            "success": failed == 0,
            "session_id": self.session_id,
            "requirement": self.requirement,
            "personas_executed": len(results),
            "personas_successful": successful,
            "personas_failed": failed,
            "completed_personas": list(self.completed_personas),
            "files_created": all_files,
            "file_count": len(all_files),
            "knowledge_items": workspace_state["knowledge_items"],
            "artifacts": workspace_state["artifacts"],
            "messages": workspace_state["messages"],
            "duration_seconds": duration,
            "output_dir": str(self.output_dir),
            "persona_results": results,
            # V3 ML features
            "ml_project_id": self.ml_project_id,
            "artifacts_found": total_artifacts_found,
            "artifacts_used": total_artifacts_used,
            "ml_enabled": self.ml_client.enabled
        }

        # Save to file
        with open(self.output_dir / "sdlc_v3_results.json", 'w') as f:
            json.dump(result, f, indent=2, default=str)

        self._print_summary(result)

        return result

    def _print_summary(self, result: Dict):
        """Print execution summary with ML stats"""

        logger.info("\n" + "=" * 80)
        logger.info("📊 SDLC EXECUTION COMPLETE (V3 - Maestro ML)")
        logger.info("=" * 80)
        logger.info(f"✅ Success: {result['success']}")
        logger.info(f"🆔 Session: {result['session_id']}")
        logger.info(f"👥 Personas executed: {result['personas_executed']}")
        logger.info(f"   ✅ Successful: {result['personas_successful']}")
        logger.info(f"   ❌ Failed: {result['personas_failed']}")
        logger.info(f"📁 Files created: {result['file_count']}")
        logger.info(f"📚 Knowledge items: {result['knowledge_items']}")
        logger.info(f"📦 Artifacts: {result['artifacts']}")
        logger.info(f"💬 Messages: {result['messages']}")
        logger.info(f"⏱️  Duration: {result['duration_seconds']:.2f}s")

        # ML stats
        if result.get("ml_enabled"):
            logger.info(f"\n🎵 MAESTRO ML STATS:")
            logger.info(f"   📊 ML Project ID: {result.get('ml_project_id', 'N/A')}")
            logger.info(f"   🔍 Artifacts found: {result.get('artifacts_found', 0)}")
            logger.info(f"   ✅ Artifacts used: {result.get('artifacts_used', 0)}")

            if result.get('artifacts_found', 0) > 0:
                reuse_rate = (result.get('artifacts_used', 0) / result['artifacts_found']) * 100
                logger.info(f"   📈 Artifact reuse rate: {reuse_rate:.1f}%")

        logger.info(f"\n📂 Output: {result['output_dir']}")
        logger.info("=" * 80)

    async def _save_session(self):
        """Save session state"""
        session_data = {
            "version": "3.0",
            "session_id": self.session_id,
            "requirement": self.requirement,
            "completed_personas": list(self.completed_personas),
            "ml_project_id": self.ml_project_id,
            "timestamp": datetime.now().isoformat()
        }

        self.coordinator.shared_workspace["session_metadata_v3"] = session_data

        session_file = self.output_dir / ".session_v3.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        logger.debug(f"💾 Session saved: {self.session_id}")

    async def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Resume existing V3 session"""
        session_file = self.output_dir / ".session_v3.json"

        if not session_file.exists():
            raise ValueError(f"Session not found: {session_id}")

        with open(session_file, 'r') as f:
            session_data = json.load(f)

        self.session_id = session_data["session_id"]
        self.requirement = session_data["requirement"]
        self.completed_personas = set(session_data["completed_personas"])
        self.ml_project_id = session_data.get("ml_project_id")

        logger.info(f"📂 Resumed V3 session: {self.session_id}")
        logger.info(f"✅ Completed personas: {', '.join(self.completed_personas)}")
        if self.ml_project_id:
            logger.info(f"📊 ML Project: {self.ml_project_id}")

        return session_data

    async def get_analytics(self) -> Optional[Dict]:
        """Get comprehensive analytics from Maestro ML"""
        if not self.ml_client.enabled or not self.ml_project_id:
            return None

        logger.info("\n" + "=" * 80)
        logger.info("📊 MAESTRO ML ANALYTICS")
        logger.info("=" * 80)

        analytics = {}

        # Get development velocity
        velocity = await self.ml_client.get_development_velocity(self.ml_project_id)
        if velocity:
            analytics["velocity_score"] = velocity
            logger.info(f"⚡ Development Velocity: {velocity:.1f}/100")

        # Get Git metrics
        git_metrics = await self.ml_client.get_git_metrics(self.ml_project_id)
        if git_metrics:
            analytics["git_metrics"] = git_metrics
            metrics = git_metrics.get("metrics", {})
            logger.info(f"\n📊 GIT METRICS:")
            logger.info(f"   Commits/week: {metrics.get('commits_per_week', 0)}")
            logger.info(f"   Contributors: {metrics.get('unique_contributors', 0)}")
            logger.info(f"   Code churn: {metrics.get('code_churn_rate', 0):.1f}%")
            logger.info(f"   Collaboration score: {metrics.get('collaboration_score', 0):.1f}")

        # Get CI/CD metrics
        cicd_metrics = await self.ml_client.get_cicd_metrics(self.ml_project_id)
        if cicd_metrics:
            analytics["cicd_metrics"] = cicd_metrics
            metrics = cicd_metrics.get("metrics", {})
            logger.info(f"\n📊 CI/CD METRICS:")
            logger.info(f"   Success rate: {metrics.get('pipeline_success_rate', 0):.1f}%")
            logger.info(f"   Avg duration: {metrics.get('avg_pipeline_duration_minutes', 0):.1f} min")
            logger.info(f"   Deployments/week: {metrics.get('deployment_frequency_per_week', 0):.1f}")

        logger.info("=" * 80)

        return analytics

    async def cleanup(self):
        """Cleanup resources"""
        await self.ml_client.close()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced SDLC Engine V3 - Maestro ML Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full SDLC with ML optimization
  python3.11 enhanced_sdlc_engine_v3.py \\
      --requirement "Build a blog platform" \\
      --output ./blog_project \\
      --maestro-ml-url http://localhost:8000

  # Specific personas with artifact reuse
  python3.11 enhanced_sdlc_engine_v3.py \\
      --requirement "Build REST API" \\
      --personas requirement_analyst backend_developer \\
      --output ./api_project \\
      --use-artifacts

  # Resume with analytics
  python3.11 enhanced_sdlc_engine_v3.py \\
      --resume blog_v1 \\
      --auto-complete \\
      --show-analytics

V3 Features:
  - Artifact reuse from Music Library (high-impact components)
  - Real-time metrics tracking (Git, CI/CD, velocity)
  - Project success tracking and learning
  - Team composition optimization (Phase 3)
  - Cost/speed prediction (Phase 3)
        """
    )

    parser.add_argument('--requirement', help='Project requirement (for new sessions)')
    parser.add_argument('--output', type=Path, default=Path("./sdlc_v3_output"),
                       help='Output directory')
    parser.add_argument('--session-id', help='Session ID for new session')
    parser.add_argument('--personas', nargs='+',
                       help='Specific personas to execute (default: all)')
    parser.add_argument('--resume', help='Resume existing session by ID')
    parser.add_argument('--auto-complete', action='store_true',
                       help='Auto-complete all remaining personas')
    parser.add_argument('--list-personas', action='store_true',
                       help='List all available personas from JSON')

    # ML options
    parser.add_argument('--maestro-ml-url', default='http://localhost:8000',
                       help='Maestro ML API URL (default: http://localhost:8000)')
    parser.add_argument('--no-ml', action='store_true',
                       help='Disable Maestro ML integration')
    parser.add_argument('--use-artifacts', action='store_true', default=True,
                       help='Enable artifact reuse (default: True)')
    parser.add_argument('--show-analytics', action='store_true',
                       help='Show analytics after execution')

    # Problem classification (for ML)
    parser.add_argument('--problem-class', default='general',
                       help='Problem class: web_app, ml_pipeline, api, etc.')
    parser.add_argument('--complexity', type=int, default=50,
                       help='Complexity score 1-100 (default: 50)')

    args = parser.parse_args()

    # List personas (reuse from V2)
    if args.list_personas:
        print("\n" + "=" * 80)
        print("📋 AVAILABLE PERSONAS (from JSON)")
        print("=" * 80)

        all_personas = SDLCPersonas.get_all_personas()

        for i, (pid, pdef) in enumerate(all_personas.items(), 1):
            deps = pdef["dependencies"]["depends_on"]
            parallel = "✅" if pdef["execution"]["parallel_capable"] else "❌"

            print(f"\n{i}. {pid}")
            print(f"   Name: {pdef['display_name']}")
            print(f"   Role: {pdef['role']['primary_role']}")
            print(f"   Depends on: {deps or 'none'}")
            print(f"   Parallel capable: {parallel}")
            print(f"   Timeout: {pdef['execution']['timeout_seconds']}s")

        print("\n" + "=" * 80)
        return

    # Create engine
    engine = EnhancedSDLCEngineV3(
        output_dir=args.output,
        session_id=args.session_id if not args.resume else args.resume,
        maestro_ml_url=args.maestro_ml_url,
        use_ml=not args.no_ml
    )

    try:
        # Resume session
        if args.resume:
            session_data = await engine.resume_session(args.resume)

            if args.auto_complete:
                # Execute all remaining personas
                all_available = list(SDLCPersonas.get_all_personas().keys())
                remaining = [p for p in all_available if p not in engine.completed_personas]

                if remaining:
                    print(f"🔄 Auto-completing {len(remaining)} remaining personas...")
                    result = await engine.execute_sdlc(
                        requirement=engine.requirement,
                        persona_ids=remaining
                    )
                else:
                    print("✅ All personas already completed!")
                    return
            elif args.personas:
                # Execute specific personas
                result = await engine.execute_sdlc(
                    requirement=engine.requirement,
                    persona_ids=args.personas
                )
            else:
                print("ℹ️  Session resumed. Use --auto-complete or --personas to continue.")
                return

        # New session
        else:
            if not args.requirement:
                print("❌ Error: --requirement is required for new sessions")
                parser.print_help()
                return

            result = await engine.execute_sdlc(
                requirement=args.requirement,
                persona_ids=args.personas,
                problem_class=args.problem_class,
                complexity_score=args.complexity
            )

        # Show analytics
        if args.show_analytics:
            await engine.get_analytics()

        # Print final status
        if result["success"]:
            print(f"\n✅ Execution completed!")
            print(f"🆔 Session: {result['session_id']}")
            print(f"📁 {result['file_count']} files created")
            print(f"📚 {result['knowledge_items']} knowledge items")

            if result.get("ml_enabled"):
                print(f"\n🎵 Maestro ML Stats:")
                print(f"   📊 Project ID: {result.get('ml_project_id', 'N/A')}")
                print(f"   🔍 Artifacts found: {result.get('artifacts_found', 0)}")
                print(f"   ✅ Artifacts used: {result.get('artifacts_used', 0)}")

            print(f"\n📂 Output: {result['output_dir']}")
        else:
            print(f"\n❌ Execution failed!")
            print(f"Check logs for details")
            sys.exit(1)

    finally:
        await engine.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
