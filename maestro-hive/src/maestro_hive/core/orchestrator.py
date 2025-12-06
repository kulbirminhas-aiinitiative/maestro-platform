import asyncio
from typing import Dict, Any
from .block_interface import BlockInterface, BlockResult, BlockStatus

# Import the legacy executor
# Note: We use a try-import to allow the block to exist even if dependencies are missing during setup
try:
    import sys
    import os
    # Add project root to path to find epic_executor
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from epic_executor.executor import EpicExecutor, JiraConfig, ConfluenceConfig
except ImportError:
    EpicExecutor = None

class UnifiedOrchestrator(BlockInterface):
    """
    The Unified Orchestrator Block.
    Currently wraps the legacy EpicExecutor (v1) but exposes the v2 Block Interface.
    """

    @property
    def block_id(self) -> str:
        return "core.orchestrator"

    @property
    def version(self) -> str:
        return "2.0.0-adapter"

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        required = ["epic_key", "jira_url", "jira_token", "jira_email"]
        return all(k in inputs for k in required)

    def execute(self, inputs: Dict[str, Any]) -> BlockResult:
        """
        Executes the legacy EpicExecutor in a synchronous wrapper.
        """
        if not EpicExecutor:
            return BlockResult(
                status=BlockStatus.FAILED,
                output={},
                error="Legacy EpicExecutor module not found or dependencies missing."
            )

        try:
            # Map inputs to legacy config
            jira_config = JiraConfig(
                url=inputs["jira_url"],
                email=inputs["jira_email"],
                token=inputs["jira_token"]
            )
            # Mock confluence config for now if not provided
            conf_config = ConfluenceConfig(url="", username="", token="")

            executor = EpicExecutor(jira_config, conf_config)
            
            # Run the async execution in a sync wrapper
            epic_key = inputs["epic_key"]
            result = asyncio.run(executor.execute(epic_key))

            return BlockResult(
                status=BlockStatus.COMPLETED if result.success else BlockStatus.FAILED,
                output={
                    "compliance_score": result.compliance_score.total_score,
                    "artifacts": [a.path for a in result.artifacts]
                },
                metrics={
                    "duration_seconds": result.duration_seconds,
                    "score": result.compliance_score.total_score
                }
            )

        except Exception as e:
            return BlockResult(
                status=BlockStatus.FAILED,
                output={},
                error=str(e)
            )
