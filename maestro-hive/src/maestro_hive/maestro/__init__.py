"""
Unified Maestro CLI - SDLC Execution with Learning Loop

EPIC: MD-2493 - [PLATFORM] Unified Maestro CLI - SDLC Execution with Learning Loop

This module unifies epic-execute and team_execution_v2 into a single /maestro command
with the following capabilities:

1. Process both EPICs and ad-hoc requirements
2. Produce functional code (not stubs)
3. Run actual tests
4. Learn from past executions via RAG
5. Recursively traverse JIRA hierarchies
6. Use semantic matching for evidence

Sub-EPICs:
- MD-2494: Unified Orchestrator Core
- MD-2495: JIRA Sub-EPIC Recursion
- MD-2496: Real Code Generation
- MD-2497: Actual Test Execution
- MD-2498: Semantic Evidence Matching
- MD-2499: RAG Retrieval Service
- MD-2500: Execution History Store
- MD-2501: Gap-Driven Iteration
- MD-2502: CLI Slash Command Interface
"""

from .orchestrator import UnifiedMaestroOrchestrator

__version__ = "1.0.0"
__all__ = ["UnifiedMaestroOrchestrator"]
