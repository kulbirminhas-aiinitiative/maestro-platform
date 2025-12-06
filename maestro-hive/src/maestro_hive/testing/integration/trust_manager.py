"""
Block Trust Manager

EPIC: MD-2509
AC-1: Skip unit tests for TRUSTED blocks

Manages trust status of blocks to determine test scope.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import (
    TrustStatus,
    BlockTestScope,
    TestRequirements,
    TrustEvidence,
)

logger = logging.getLogger(__name__)


class BlockTrustManager:
    """
    Manages trust status for blocks (AC-1).

    Determines which blocks are trusted and can skip unit tests.

    Example:
        manager = BlockTrustManager()

        # Check trust status
        status = manager.get_trust_status("auth_service")

        # Register a trusted block
        evidence = TrustEvidence(
            block_name="auth_service",
            verified_by="security_team",
            evidence_type="manual_review"
        )
        manager.register_trusted_block("auth_service", evidence)

        # Get test scope
        scope = manager.get_test_scope("auth_service")
        if not scope.run_unit_tests:
            print("Skipping unit tests for trusted block")
    """

    def __init__(
        self,
        registry_path: Optional[str] = None,
        auto_load: bool = True,
    ):
        """
        Initialize trust manager.

        Args:
            registry_path: Path to trust registry file
            auto_load: Whether to auto-load registry from file
        """
        self.registry_path = registry_path or os.environ.get(
            "TRUST_REGISTRY_PATH",
            "./trust_registry.json"
        )

        self._trusted_blocks: Dict[str, TrustEvidence] = {}
        self._catalogued_blocks: Set[str] = set()
        self._stats = {
            "lookups": 0,
            "trusted_hits": 0,
            "catalogued_hits": 0,
            "new_hits": 0,
        }

        if auto_load and Path(self.registry_path).exists():
            self.load_registry()

    def get_trust_status(self, block_name: str) -> TrustStatus:
        """
        Get trust status for a block (AC-1).

        Args:
            block_name: Name of the block

        Returns:
            TrustStatus indicating trust level
        """
        self._stats["lookups"] += 1

        if block_name in self._trusted_blocks:
            self._stats["trusted_hits"] += 1
            return TrustStatus.TRUSTED
        elif block_name in self._catalogued_blocks:
            self._stats["catalogued_hits"] += 1
            return TrustStatus.CATALOGUED
        else:
            self._stats["new_hits"] += 1
            return TrustStatus.NEW

    def register_trusted_block(
        self,
        block_name: str,
        evidence: TrustEvidence,
        save: bool = True,
    ) -> None:
        """
        Register a block as TRUSTED (AC-1).

        Args:
            block_name: Name of the block
            evidence: Evidence supporting trust status
            save: Whether to persist to registry file
        """
        evidence.block_name = block_name
        self._trusted_blocks[block_name] = evidence

        # Remove from catalogued if present
        self._catalogued_blocks.discard(block_name)

        logger.info(f"Registered trusted block: {block_name}")

        if save:
            self.save_registry()

    def register_catalogued_block(
        self,
        block_name: str,
        save: bool = True,
    ) -> None:
        """
        Register a block as CATALOGUED.

        Args:
            block_name: Name of the block
            save: Whether to persist to registry file
        """
        # Don't downgrade trusted blocks
        if block_name in self._trusted_blocks:
            logger.warning(f"Block {block_name} is already TRUSTED, not downgrading")
            return

        self._catalogued_blocks.add(block_name)
        logger.info(f"Registered catalogued block: {block_name}")

        if save:
            self.save_registry()

    def demote_block(self, block_name: str, save: bool = True) -> TrustStatus:
        """
        Demote a block's trust status.

        TRUSTED -> CATALOGUED -> NEW

        Returns the new status.
        """
        if block_name in self._trusted_blocks:
            del self._trusted_blocks[block_name]
            self._catalogued_blocks.add(block_name)
            new_status = TrustStatus.CATALOGUED
        elif block_name in self._catalogued_blocks:
            self._catalogued_blocks.discard(block_name)
            new_status = TrustStatus.NEW
        else:
            new_status = TrustStatus.NEW

        logger.info(f"Demoted block {block_name} to {new_status.value}")

        if save:
            self.save_registry()

        return new_status

    def get_test_scope(self, block_name: str, version: str = "") -> BlockTestScope:
        """
        Get the test scope for a block (AC-1).

        Args:
            block_name: Name of the block
            version: Optional version string

        Returns:
            BlockTestScope with test requirements
        """
        status = self.get_trust_status(block_name)
        requirements = TestRequirements.for_status(status)

        return BlockTestScope(
            block_name=block_name,
            block_version=version,
            trust_status=status,
            requirements=requirements,
        )

    def get_trusted_blocks(self) -> List[str]:
        """Get all trusted block names."""
        return list(self._trusted_blocks.keys())

    def get_catalogued_blocks(self) -> List[str]:
        """Get all catalogued block names."""
        return list(self._catalogued_blocks)

    def get_trust_evidence(self, block_name: str) -> Optional[TrustEvidence]:
        """Get trust evidence for a block."""
        return self._trusted_blocks.get(block_name)

    def load_registry(self, path: Optional[str] = None) -> None:
        """Load trust registry from file."""
        path = path or self.registry_path

        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Load trusted blocks
            for item in data.get("trusted_blocks", []):
                evidence = TrustEvidence(
                    block_name=item["name"],
                    block_version=item.get("version", ""),
                    verified_by=item.get("verified_by", ""),
                    verified_at=datetime.fromisoformat(item["verified_at"])
                    if "verified_at" in item else datetime.utcnow(),
                    evidence_type=item.get("evidence_type", ""),
                )
                self._trusted_blocks[item["name"]] = evidence

            # Load catalogued blocks
            for item in data.get("catalogued_blocks", []):
                name = item["name"] if isinstance(item, dict) else item
                self._catalogued_blocks.add(name)

            logger.info(
                f"Loaded trust registry: {len(self._trusted_blocks)} trusted, "
                f"{len(self._catalogued_blocks)} catalogued"
            )

        except FileNotFoundError:
            logger.debug(f"Trust registry not found at {path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid trust registry JSON: {e}")

    def save_registry(self, path: Optional[str] = None) -> None:
        """Save trust registry to file."""
        path = path or self.registry_path

        data = {
            "trusted_blocks": [
                {
                    "name": name,
                    "version": evidence.block_version,
                    "verified_by": evidence.verified_by,
                    "verified_at": evidence.verified_at.isoformat(),
                    "evidence_type": evidence.evidence_type,
                }
                for name, evidence in self._trusted_blocks.items()
            ],
            "catalogued_blocks": [
                {"name": name} for name in self._catalogued_blocks
            ],
        }

        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved trust registry to {path}")

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "trusted_count": len(self._trusted_blocks),
            "catalogued_count": len(self._catalogued_blocks),
            "lookups": self._stats["lookups"],
            "trusted_hits": self._stats["trusted_hits"],
            "catalogued_hits": self._stats["catalogued_hits"],
            "new_hits": self._stats["new_hits"],
            "trust_rate": (
                self._stats["trusted_hits"] / self._stats["lookups"]
                if self._stats["lookups"] > 0 else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = {
            "lookups": 0,
            "trusted_hits": 0,
            "catalogued_hits": 0,
            "new_hits": 0,
        }


# Global instance
_global_trust_manager: Optional[BlockTrustManager] = None


def get_trust_manager() -> BlockTrustManager:
    """Get the global trust manager instance."""
    global _global_trust_manager
    if _global_trust_manager is None:
        _global_trust_manager = BlockTrustManager()
    return _global_trust_manager
