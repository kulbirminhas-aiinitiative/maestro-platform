"""
Maestro Blocks - Certified Block Implementations

This module provides certified block wrappers for existing maestro-hive modules,
enabling composition-first SDLC workflows with contract testing and versioning.

Blocks Available:
- DAGExecutorBlock: Wraps DAGWorkflow/DAGExecutor (dag-executor@2.0.0)
- PhaseOrchestratorBlock: Wraps PhasedAutonomousExecutor (phase-orchestrator@1.5.0)
- ContractRegistryBlock: Wraps ContractRegistry (contract-registry@1.0.0)
- JiraAdapterBlock: Wraps JiraAdapter (jira-adapter@3.1.0)
- QualityFabricBlock: Wraps QualityFabricClient (quality-fabric@2.0.0)

Reference: MD-2507 Block Formalization EPIC
"""

from .interfaces import (
    IDAGExecutor,
    IPhaseOrchestrator,
    IContractRegistry,
    IJiraAdapter,
    IQualityFabric,
)
from .dag_executor_block import DAGExecutorBlock
from .phase_orchestrator_block import PhaseOrchestratorBlock
from .contract_registry_block import ContractRegistryBlock
from .jira_adapter_block import JiraAdapterBlock
from .quality_fabric_block import QualityFabricBlock
from .registry import BlockRegistry, get_block_registry

__all__ = [
    # Interfaces
    "IDAGExecutor",
    "IPhaseOrchestrator",
    "IContractRegistry",
    "IJiraAdapter",
    "IQualityFabric",
    # Blocks
    "DAGExecutorBlock",
    "PhaseOrchestratorBlock",
    "ContractRegistryBlock",
    "JiraAdapterBlock",
    "QualityFabricBlock",
    # Registry
    "BlockRegistry",
    "get_block_registry",
]
