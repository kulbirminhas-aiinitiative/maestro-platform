#!/usr/bin/env python3
"""
Contract Manager - API Contract Versioning for Parallel Work

Contracts are the decoupling layer that enables frontend and backend
(and other teams) to work in parallel using mocks. The contract acts as
the agreement between teams.

Key Features:
- Version-controlled API contracts
- Contract evolution tracking
- Breaking change detection
- Consumer dependency tracking
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from persistence.state_manager import StateManager
from persistence.models import Contract, ContractStatus
from sqlalchemy import select, and_, or_


class ContractManager:
    """
    Manages API contract versioning for parallel execution

    The Contract-First approach is critical for parallel work.
    Frontend and Backend can work simultaneously using mocked implementations
    of the contract.
    """

    def __init__(self, state_manager: StateManager):
        self.state = state_manager

    # =========================================================================
    # Contract Creation and Evolution
    # =========================================================================

    async def create_contract(
        self,
        team_id: str,
        contract_name: str,
        version: str,
        contract_type: str,
        specification: Dict[str, Any],
        owner_role: str,
        owner_agent: str,
        consumers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new API contract

        Args:
            team_id: Team identifier
            contract_name: Contract name (e.g., "FraudAlertsAPI")
            version: Version string (e.g., "v0.1")
            contract_type: Type (REST_API, GraphQL, gRPC, EventStream)
            specification: Full contract spec (OpenAPI, GraphQL schema, etc.)
            owner_role: Role responsible (usually "Tech Lead")
            owner_agent: Agent owner
            consumers: List of agents/roles depending on this contract

        Returns:
            Contract info
        """
        contract = Contract(
            id=f"contract_{uuid.uuid4().hex[:12]}",
            team_id=team_id,
            contract_name=contract_name,
            version=version,
            contract_type=contract_type,
            specification=specification,
            owner_role=owner_role,
            owner_agent=owner_agent,
            status=ContractStatus.DRAFT,
            consumers=consumers or []
        )

        async with self.state.db.session() as session:
            session.add(contract)
            await session.commit()
            await session.refresh(contract)

        # Publish event
        await self.state.redis.publish_event(
            f"team:{team_id}:events:contract.created",
            "contract.created",
            {
                "contract_id": contract.id,
                "contract_name": contract_name,
                "version": version,
                "owner": owner_agent
            }
        )

        print(f"  📜 Contract created: {contract_name} {version}")
        print(f"     Type: {contract_type}")
        print(f"     Owner: {owner_role} ({owner_agent})")

        return contract.to_dict()

    async def evolve_contract(
        self,
        team_id: str,
        contract_name: str,
        new_version: str,
        new_specification: Dict[str, Any],
        changes_from_previous: Dict[str, Any],
        breaking_changes: bool,
        owner_agent: str
    ) -> Dict[str, Any]:
        """
        Evolve contract to new version

        Args:
            team_id: Team identifier
            contract_name: Contract name
            new_version: New version (e.g., "v0.2")
            new_specification: Updated specification
            changes_from_previous: What changed
            breaking_changes: Whether this contains breaking changes
            owner_agent: Who created this version

        Returns:
            New contract version
        """
        # Get current active version
        current = await self.get_active_contract(team_id, contract_name)

        if not current:
            raise ValueError(f"No active contract found for {contract_name}")

        # Create new version
        new_contract = Contract(
            id=f"contract_{uuid.uuid4().hex[:12]}",
            team_id=team_id,
            contract_name=contract_name,
            version=new_version,
            contract_type=current['contract_type'],
            specification=new_specification,
            owner_role=current['owner_role'],
            owner_agent=owner_agent,
            status=ContractStatus.DRAFT,
            consumers=current['consumers'],
            supersedes_contract_id=current['id'],
            changes_from_previous=changes_from_previous,
            breaking_changes=breaking_changes
        )

        async with self.state.db.session() as session:
            session.add(new_contract)
            await session.commit()
            await session.refresh(new_contract)

        # Publish event (breaking changes are critical!)
        event_type = "contract.breaking_change" if breaking_changes else "contract.evolved"
        await self.state.redis.publish_event(
            f"team:{team_id}:events:{event_type}",
            event_type,
            {
                "contract_id": new_contract.id,
                "contract_name": contract_name,
                "old_version": current['version'],
                "new_version": new_version,
                "breaking_changes": breaking_changes,
                "changes": changes_from_previous,
                "consumers": current['consumers']
            }
        )

        if breaking_changes:
            print(f"  ⚠️  Contract BREAKING CHANGE: {contract_name} {current['version']} → {new_version}")
            print(f"     All consumers must update!")
        else:
            print(f"  🔄 Contract evolved: {contract_name} {current['version']} → {new_version}")

        return new_contract.to_dict()

    async def activate_contract(
        self,
        contract_id: str,
        activated_by: str
    ) -> Dict[str, Any]:
        """
        Activate a contract (move from DRAFT to ACTIVE)

        Args:
            contract_id: Contract to activate
            activated_by: Who activated it

        Returns:
            Updated contract
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Contract).where(Contract.id == contract_id)
            )
            contract = result.scalar_one_or_none()

            if not contract:
                raise ValueError(f"Contract {contract_id} not found")

            # Deprecate old version if exists
            if contract.supersedes_contract_id:
                old_result = await session.execute(
                    select(Contract).where(Contract.id == contract.supersedes_contract_id)
                )
                old_contract = old_result.scalar_one_or_none()
                if old_contract and old_contract.status == ContractStatus.ACTIVE:
                    old_contract.status = ContractStatus.DEPRECATED

            contract.status = ContractStatus.ACTIVE
            contract.activated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(contract)

        print(f"  ✅ Contract activated: {contract.contract_name} {contract.version}")

        return contract.to_dict()

    # =========================================================================
    # Contract Queries
    # =========================================================================

    async def get_active_contract(
        self,
        team_id: str,
        contract_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get currently active version of a contract"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Contract).where(
                    and_(
                        Contract.team_id == team_id,
                        Contract.contract_name == contract_name,
                        Contract.status == ContractStatus.ACTIVE
                    )
                )
            )
            contract = result.scalar_one_or_none()
            return contract.to_dict() if contract else None

    async def get_contract_history(
        self,
        team_id: str,
        contract_name: str
    ) -> List[Dict[str, Any]]:
        """Get all versions of a contract"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Contract).where(
                    and_(
                        Contract.team_id == team_id,
                        Contract.contract_name == contract_name
                    )
                ).order_by(Contract.created_at)
            )
            contracts = result.scalars().all()
            return [c.to_dict() for c in contracts]

    async def get_contracts_for_consumer(
        self,
        team_id: str,
        consumer_id: str
    ) -> List[Dict[str, Any]]:
        """Get all contracts consumed by an agent"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Contract).where(
                    and_(
                        Contract.team_id == team_id,
                        Contract.status == ContractStatus.ACTIVE
                    )
                )
            )
            all_contracts = result.scalars().all()

            # Filter by consumer (JSON array contains consumer_id)
            relevant = [
                c.to_dict() for c in all_contracts
                if consumer_id in (c.consumers or [])
            ]

            return relevant

    # =========================================================================
    # Dependency Management
    # =========================================================================

    async def register_consumer(
        self,
        contract_id: str,
        consumer_id: str
    ) -> Dict[str, Any]:
        """Register a new consumer for a contract"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Contract).where(Contract.id == contract_id)
            )
            contract = result.scalar_one_or_none()

            if not contract:
                raise ValueError(f"Contract {contract_id} not found")

            if not isinstance(contract.consumers, list):
                contract.consumers = []

            if consumer_id not in contract.consumers:
                contract.consumers.append(consumer_id)

            await session.commit()
            await session.refresh(contract)

        print(f"  ✓ Registered consumer {consumer_id} for contract {contract.contract_name}")

        return contract.to_dict()

    # =========================================================================
    # Reporting
    # =========================================================================

    async def get_contract_summary(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """Get summary of contracts for a team"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Contract).where(Contract.team_id == team_id)
            )
            all_contracts = result.scalars().all()

        by_status = {}
        by_type = {}
        active_contracts = []

        for contract in all_contracts:
            status = contract.status.value if isinstance(contract.status, ContractStatus) else contract.status
            by_status[status] = by_status.get(status, 0) + 1

            ctype = contract.contract_type
            by_type[ctype] = by_type.get(ctype, 0) + 1

            if status == "active":
                active_contracts.append({
                    "name": contract.contract_name,
                    "version": contract.version,
                    "consumers": len(contract.consumers or [])
                })

        return {
            "team_id": team_id,
            "total_contracts": len(all_contracts),
            "by_status": by_status,
            "by_type": by_type,
            "active_contracts": active_contracts
        }

    async def print_contract_summary(self, team_id: str):
        """Print formatted contract summary"""
        summary = await self.get_contract_summary(team_id)

        print(f"\n{'=' * 80}")
        print(f"CONTRACT SUMMARY: {team_id}")
        print(f"{'=' * 80}\n")

        print(f"  Total contracts: {summary['total_contracts']}")
        print(f"\n  By Status:")
        for status, count in summary['by_status'].items():
            print(f"    {status}: {count}")

        print(f"\n  Active Contracts:")
        for contract in summary['active_contracts']:
            print(f"    {contract['name']} {contract['version']} ({contract['consumers']} consumers)")

        print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    print("Contract Manager - API Contract Versioning")
    print("=" * 80)
    print("\nEnables parallel work through Contract-First Design:")
    print("- Teams agree on interfaces before implementation")
    print("- Frontend/Backend work simultaneously using mocks")
    print("- Version control prevents breaking changes")
    print("- Consumer tracking enables impact analysis")
