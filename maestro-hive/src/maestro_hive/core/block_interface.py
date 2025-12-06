from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class BlockStatus(Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class BlockResult:
    status: BlockStatus
    output: Dict[str, Any]
    error: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None

class BlockInterface(ABC):
    """
    The Universal Contract for all Maestro Blocks.
    Wraps legacy code or new implementations in a standard interface.
    """
    
    @property
    @abstractmethod
    def block_id(self) -> str:
        """Unique identifier for the block (e.g., 'core.orchestrator')"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version of the block"""
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Check if inputs meet the block's contract before execution"""
        pass

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> BlockResult:
        """
        Execute the block's core logic.
        Must return a BlockResult, never raise an exception.
        """
        pass

    def health_check(self) -> bool:
        """Optional: Check if the block is healthy and ready to run"""
        return True
