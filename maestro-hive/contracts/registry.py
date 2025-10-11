"""
Contract Registry - Central Contract Management

The ContractRegistry manages all contracts in the system, including:
- Contract storage and retrieval
- Lifecycle state transitions
- Dependency graph management
- Execution plan generation
- Contract verification

Version: 1.0.0
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
import uuid
from collections import defaultdict

from contracts.models import (
    UniversalContract,
    ContractLifecycle,
    ContractEvent,
    ContractProposedEvent,
    ContractAcceptedEvent,
    ContractFulfilledEvent,
    ContractVerifiedEvent,
    ContractBreachedEvent,
    VerificationResult,
    ContractBreach,
    ExecutionPlan,
)


class ContractRegistryError(Exception):
    """Base exception for ContractRegistry errors"""
    pass


class ContractNotFoundError(ContractRegistryError):
    """Raised when a contract is not found"""
    pass


class ContractTransitionError(ContractRegistryError):
    """Raised when an invalid state transition is attempted"""
    pass


class DependencyCycleError(ContractRegistryError):
    """Raised when a dependency cycle is detected"""
    pass


class ContractRegistry:
    """
    Central registry for managing all contracts in the system.

    The ContractRegistry provides 15 core methods:
    1. register_contract() - Register a new contract
    2. get_contract() - Retrieve a contract by ID
    3. list_contracts() - List all contracts (with optional filters)
    4. update_contract() - Update an existing contract
    5. delete_contract() - Delete a contract (soft delete)
    6. propose_contract() - Transition to PROPOSED state
    7. accept_contract() - Transition to ACCEPTED state
    8. fulfill_contract() - Transition to FULFILLED state
    9. verify_contract() - Transition to VERIFIED state
    10. breach_contract() - Mark contract as BREACHED
    11. get_dependencies() - Get all contracts this depends on
    12. get_dependents() - Get all contracts that depend on this
    13. create_execution_plan() - Generate execution plan with topological sort
    14. get_contract_history() - Get event history for a contract
    15. search_contracts() - Search contracts by various criteria
    """

    def __init__(self):
        """Initialize the contract registry"""
        self._contracts: Dict[str, UniversalContract] = {}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)  # contract_id -> dependencies
        self._dependents_graph: Dict[str, Set[str]] = defaultdict(set)  # contract_id -> dependents

    # ========================================================================
    # 1. Register Contract
    # ========================================================================

    def register_contract(self, contract: UniversalContract) -> UniversalContract:
        """
        Register a new contract in the registry.

        Args:
            contract: The contract to register

        Returns:
            The registered contract

        Raises:
            ContractRegistryError: If contract_id already exists
            DependencyCycleError: If dependencies create a cycle
        """
        if contract.contract_id in self._contracts:
            raise ContractRegistryError(f"Contract {contract.contract_id} already exists")

        # Check for dependency cycles
        self._check_dependency_cycle(contract.contract_id, contract.depends_on)

        # Register the contract
        self._contracts[contract.contract_id] = contract

        # Update dependency graphs
        for dep_id in contract.depends_on:
            self._dependency_graph[contract.contract_id].add(dep_id)
            self._dependents_graph[dep_id].add(contract.contract_id)

        return contract

    # ========================================================================
    # 2. Get Contract
    # ========================================================================

    def get_contract(self, contract_id: str) -> UniversalContract:
        """
        Retrieve a contract by ID.

        Args:
            contract_id: The contract ID to retrieve

        Returns:
            The contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
        """
        if contract_id not in self._contracts:
            raise ContractNotFoundError(f"Contract {contract_id} not found")
        return self._contracts[contract_id]

    # ========================================================================
    # 3. List Contracts
    # ========================================================================

    def list_contracts(
        self,
        contract_type: Optional[str] = None,
        lifecycle_state: Optional[ContractLifecycle] = None,
        provider_agent: Optional[str] = None,
        consumer_agent: Optional[str] = None,
        priority: Optional[str] = None,
        is_blocking: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> List[UniversalContract]:
        """
        List all contracts with optional filters.

        Args:
            contract_type: Filter by contract type
            lifecycle_state: Filter by lifecycle state
            provider_agent: Filter by provider agent
            consumer_agent: Filter by consumer agent
            priority: Filter by priority
            is_blocking: Filter by blocking status
            tags: Filter by tags (contract must have all specified tags)

        Returns:
            List of contracts matching the filters
        """
        contracts = list(self._contracts.values())

        # Apply filters
        if contract_type:
            contracts = [c for c in contracts if c.contract_type == contract_type]

        if lifecycle_state:
            contracts = [c for c in contracts if c.lifecycle_state == lifecycle_state]

        if provider_agent:
            contracts = [c for c in contracts if c.provider_agent == provider_agent]

        if consumer_agent:
            contracts = [c for c in contracts if consumer_agent in c.consumer_agents]

        if priority:
            contracts = [c for c in contracts if c.priority == priority]

        if is_blocking is not None:
            contracts = [c for c in contracts if c.is_blocking == is_blocking]

        if tags:
            contracts = [c for c in contracts if all(tag in c.tags for tag in tags)]

        return contracts

    # ========================================================================
    # 4. Update Contract
    # ========================================================================

    def update_contract(self, contract: UniversalContract) -> UniversalContract:
        """
        Update an existing contract.

        Args:
            contract: The updated contract

        Returns:
            The updated contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
            DependencyCycleError: If updated dependencies create a cycle
        """
        if contract.contract_id not in self._contracts:
            raise ContractNotFoundError(f"Contract {contract.contract_id} not found")

        # Check for dependency cycles with updated dependencies
        old_contract = self._contracts[contract.contract_id]
        if contract.depends_on != old_contract.depends_on:
            self._check_dependency_cycle(contract.contract_id, contract.depends_on)

            # Update dependency graphs
            # Remove old dependencies
            for dep_id in old_contract.depends_on:
                self._dependency_graph[contract.contract_id].discard(dep_id)
                self._dependents_graph[dep_id].discard(contract.contract_id)

            # Add new dependencies
            for dep_id in contract.depends_on:
                self._dependency_graph[contract.contract_id].add(dep_id)
                self._dependents_graph[dep_id].add(contract.contract_id)

        # Update timestamp
        contract.updated_at = datetime.utcnow()

        # Store updated contract
        self._contracts[contract.contract_id] = contract

        return contract

    # ========================================================================
    # 5. Delete Contract
    # ========================================================================

    def delete_contract(self, contract_id: str) -> None:
        """
        Delete a contract (soft delete - marks as REJECTED).

        Args:
            contract_id: The contract ID to delete

        Raises:
            ContractNotFoundError: If contract doesn't exist
            ContractRegistryError: If contract has dependents
        """
        if contract_id not in self._contracts:
            raise ContractNotFoundError(f"Contract {contract_id} not found")

        # Check if contract has dependents
        dependents = self._dependents_graph[contract_id]
        if dependents:
            raise ContractRegistryError(
                f"Cannot delete contract {contract_id} - has {len(dependents)} dependents"
            )

        # Soft delete: transition to REJECTED
        contract = self._contracts[contract_id]
        contract.lifecycle_state = ContractLifecycle.REJECTED
        contract.updated_at = datetime.utcnow()

        # Clean up dependency graphs
        for dep_id in contract.depends_on:
            self._dependents_graph[dep_id].discard(contract_id)
        self._dependency_graph[contract_id].clear()

    # ========================================================================
    # 6. Propose Contract
    # ========================================================================

    def propose_contract(
        self,
        contract_id: str,
        proposer: str,
    ) -> UniversalContract:
        """
        Propose a contract (transition to PROPOSED state).

        Args:
            contract_id: The contract ID to propose
            proposer: The agent proposing the contract

        Returns:
            The updated contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
            ContractTransitionError: If invalid state transition
        """
        contract = self.get_contract(contract_id)

        if not contract.transition_to(ContractLifecycle.PROPOSED):
            raise ContractTransitionError(
                f"Cannot transition contract {contract_id} from {contract.lifecycle_state.value} to PROPOSED"
            )

        # Add event
        event = ContractProposedEvent(
            event_id=str(uuid.uuid4()),
            event_type="proposed",
            contract_id=contract_id,
            proposer=proposer,
            contract=contract,
        )
        contract.add_event(event)

        return contract

    # ========================================================================
    # 7. Accept Contract
    # ========================================================================

    def accept_contract(
        self,
        contract_id: str,
        acceptor: str,
    ) -> UniversalContract:
        """
        Accept a contract (transition to ACCEPTED state).

        Args:
            contract_id: The contract ID to accept
            acceptor: The agent accepting the contract

        Returns:
            The updated contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
            ContractTransitionError: If invalid state transition
        """
        contract = self.get_contract(contract_id)

        if not contract.transition_to(ContractLifecycle.ACCEPTED):
            raise ContractTransitionError(
                f"Cannot transition contract {contract_id} from {contract.lifecycle_state.value} to ACCEPTED"
            )

        # Add event
        event = ContractAcceptedEvent(
            event_id=str(uuid.uuid4()),
            event_type="accepted",
            contract_id=contract_id,
            acceptor=acceptor,
        )
        contract.add_event(event)

        # Transition to IN_PROGRESS
        contract.transition_to(ContractLifecycle.IN_PROGRESS)

        return contract

    # ========================================================================
    # 8. Fulfill Contract
    # ========================================================================

    def fulfill_contract(
        self,
        contract_id: str,
        fulfiller: str,
        deliverables: List[str],
    ) -> UniversalContract:
        """
        Mark contract as fulfilled (transition to FULFILLED state).

        Args:
            contract_id: The contract ID to fulfill
            fulfiller: The agent fulfilling the contract
            deliverables: List of artifact IDs delivered

        Returns:
            The updated contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
            ContractTransitionError: If invalid state transition
        """
        contract = self.get_contract(contract_id)

        if not contract.transition_to(ContractLifecycle.FULFILLED):
            raise ContractTransitionError(
                f"Cannot transition contract {contract_id} from {contract.lifecycle_state.value} to FULFILLED"
            )

        # Add event
        event = ContractFulfilledEvent(
            event_id=str(uuid.uuid4()),
            event_type="fulfilled",
            contract_id=contract_id,
            fulfiller=fulfiller,
            deliverables=deliverables,
        )
        contract.add_event(event)

        return contract

    # ========================================================================
    # 9. Verify Contract
    # ========================================================================

    def verify_contract(
        self,
        contract_id: str,
        verifier: str,
        verification_result: VerificationResult,
    ) -> UniversalContract:
        """
        Verify a contract (transition to VERIFIED or VERIFIED_WITH_WARNINGS).

        Args:
            contract_id: The contract ID to verify
            verifier: The validator or agent verifying the contract
            verification_result: The verification result

        Returns:
            The updated contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
            ContractTransitionError: If invalid state transition
        """
        contract = self.get_contract(contract_id)

        # Determine target state based on verification result
        if verification_result.passed:
            # Check if there were any warnings
            has_warnings = any(
                not cr.passed and not getattr(cr, 'blocking', True)
                for cr in verification_result.criteria_results
            )
            target_state = (
                ContractLifecycle.VERIFIED_WITH_WARNINGS if has_warnings
                else ContractLifecycle.VERIFIED
            )
        else:
            # Verification failed - breach
            return self.breach_contract(
                contract_id=contract_id,
                breach=ContractBreach(
                    breach_id=str(uuid.uuid4()),
                    contract_id=contract_id,
                    severity="major",
                    description="Contract verification failed",
                    failed_criteria=[cr.criterion_id for cr in verification_result.criteria_results if not cr.passed],
                ),
            )

        if not contract.transition_to(target_state):
            raise ContractTransitionError(
                f"Cannot transition contract {contract_id} from {contract.lifecycle_state.value} to {target_state.value}"
            )

        # Store verification result
        contract.verification_result = verification_result

        # Add event
        event = ContractVerifiedEvent(
            event_id=str(uuid.uuid4()),
            event_type="verified",
            contract_id=contract_id,
            verifier=verifier,
            verification_result=verification_result,
        )
        contract.add_event(event)

        return contract

    # ========================================================================
    # 10. Breach Contract
    # ========================================================================

    def breach_contract(
        self,
        contract_id: str,
        breach: ContractBreach,
    ) -> UniversalContract:
        """
        Mark contract as breached (transition to BREACHED state).

        Args:
            contract_id: The contract ID to breach
            breach: Details of the breach

        Returns:
            The updated contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
        """
        contract = self.get_contract(contract_id)

        # Force transition to BREACHED (can happen from multiple states)
        contract.lifecycle_state = ContractLifecycle.BREACHED
        contract.updated_at = datetime.utcnow()

        # Add event
        event = ContractBreachedEvent(
            event_id=str(uuid.uuid4()),
            event_type="breached",
            contract_id=contract_id,
            breach=breach,
            severity=breach.severity,
        )
        contract.add_event(event)

        return contract

    # ========================================================================
    # 11. Get Dependencies
    # ========================================================================

    def get_dependencies(self, contract_id: str) -> List[UniversalContract]:
        """
        Get all contracts that this contract depends on.

        Args:
            contract_id: The contract ID

        Returns:
            List of dependency contracts

        Raises:
            ContractNotFoundError: If contract doesn't exist
        """
        if contract_id not in self._contracts:
            raise ContractNotFoundError(f"Contract {contract_id} not found")

        dependencies = []
        for dep_id in self._dependency_graph[contract_id]:
            if dep_id in self._contracts:
                dependencies.append(self._contracts[dep_id])

        return dependencies

    # ========================================================================
    # 12. Get Dependents
    # ========================================================================

    def get_dependents(self, contract_id: str) -> List[UniversalContract]:
        """
        Get all contracts that depend on this contract.

        Args:
            contract_id: The contract ID

        Returns:
            List of dependent contracts

        Raises:
            ContractNotFoundError: If contract doesn't exist
        """
        if contract_id not in self._contracts:
            raise ContractNotFoundError(f"Contract {contract_id} not found")

        dependents = []
        for dep_id in self._dependents_graph[contract_id]:
            if dep_id in self._contracts:
                dependents.append(self._contracts[dep_id])

        return dependents

    # ========================================================================
    # 13. Create Execution Plan
    # ========================================================================

    def create_execution_plan(
        self,
        contract_ids: Optional[List[str]] = None,
    ) -> ExecutionPlan:
        """
        Create an execution plan with topological sort.

        Args:
            contract_ids: List of contract IDs to include (None = all contracts)

        Returns:
            Execution plan with topological order and parallel groups

        Raises:
            DependencyCycleError: If there's a cycle in the dependency graph
        """
        # Get contracts to include
        if contract_ids is None:
            contracts = list(self._contracts.values())
        else:
            contracts = [self.get_contract(cid) for cid in contract_ids]

        contract_id_set = {c.contract_id for c in contracts}

        # Build dependency graph for these contracts
        graph = {c.contract_id: [] for c in contracts}
        for contract in contracts:
            for dep_id in contract.depends_on:
                if dep_id in contract_id_set:
                    graph[contract.contract_id].append(dep_id)

        # Topological sort using Kahn's algorithm
        execution_order = self._topological_sort(graph)

        # Generate parallel groups
        parallel_groups = self._generate_parallel_groups(graph, execution_order)

        # Create execution plan
        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            contracts=contracts,
            execution_order=execution_order,
            dependency_graph=graph,
            parallel_groups=parallel_groups,
        )

        return plan

    # ========================================================================
    # 14. Get Contract History
    # ========================================================================

    def get_contract_history(
        self,
        contract_id: str,
    ) -> List[ContractEvent]:
        """
        Get the event history for a contract.

        Args:
            contract_id: The contract ID

        Returns:
            List of events in chronological order

        Raises:
            ContractNotFoundError: If contract doesn't exist
        """
        contract = self.get_contract(contract_id)
        return sorted(contract.events, key=lambda e: e.timestamp)

    # ========================================================================
    # 15. Search Contracts
    # ========================================================================

    def search_contracts(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
    ) -> List[UniversalContract]:
        """
        Search contracts by various criteria.

        Args:
            query: Search query string
            search_fields: Fields to search (default: name, description, tags)

        Returns:
            List of matching contracts
        """
        if search_fields is None:
            search_fields = ["name", "description", "tags"]

        query_lower = query.lower()
        matches = []

        for contract in self._contracts.values():
            # Search in specified fields
            if "name" in search_fields and query_lower in contract.name.lower():
                matches.append(contract)
                continue

            if "description" in search_fields and query_lower in contract.description.lower():
                matches.append(contract)
                continue

            if "tags" in search_fields and any(query_lower in tag.lower() for tag in contract.tags):
                matches.append(contract)
                continue

            if "contract_id" in search_fields and query_lower in contract.contract_id.lower():
                matches.append(contract)
                continue

            if "contract_type" in search_fields and query_lower in contract.contract_type.lower():
                matches.append(contract)
                continue

        return matches

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _check_dependency_cycle(self, contract_id: str, dependencies: List[str]) -> None:
        """
        Check if adding these dependencies would create a cycle.

        Args:
            contract_id: The contract ID
            dependencies: List of dependency IDs

        Raises:
            DependencyCycleError: If a cycle is detected
        """
        # Build temporary graph with new dependencies
        temp_graph = dict(self._dependency_graph)
        temp_graph[contract_id] = set(dependencies)

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in temp_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        if has_cycle(contract_id):
            raise DependencyCycleError(
                f"Adding dependencies {dependencies} to contract {contract_id} would create a cycle"
            )

    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        Topological sort using Kahn's algorithm.

        Args:
            graph: Dependency graph (node -> list of dependencies)

        Returns:
            List of node IDs in topological order

        Raises:
            DependencyCycleError: If there's a cycle
        """
        # Calculate in-degrees (number of dependencies for each node)
        in_degree = {node: len(graph[node]) for node in graph}

        # Find nodes with no dependencies (in-degree = 0)
        queue = [node for node in graph if in_degree[node] == 0]
        result = []

        while queue:
            # Process node with no dependencies
            node = queue.pop(0)
            result.append(node)

            # Find all nodes that depend on this node and reduce their in-degree
            for dependent in graph:
                if node in graph[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check if all nodes were processed
        if len(result) != len(graph):
            raise DependencyCycleError("Dependency cycle detected in graph")

        return result

    def _generate_parallel_groups(
        self,
        graph: Dict[str, List[str]],
        execution_order: List[str],
    ) -> List[List[str]]:
        """
        Generate parallel execution groups.

        Args:
            graph: Dependency graph
            execution_order: Topological order

        Returns:
            List of parallel groups (contracts that can run in parallel)
        """
        # Track when each contract can start (based on dependencies)
        level = {}
        for node in execution_order:
            # Calculate level as max(dependency levels) + 1
            dep_levels = [level.get(dep, 0) for dep in graph[node]]
            level[node] = max(dep_levels) + 1 if dep_levels else 0

        # Group by level
        parallel_groups = []
        max_level = max(level.values()) if level else 0

        for i in range(max_level + 1):
            group = [node for node in execution_order if level[node] == i]
            if group:
                parallel_groups.append(group)

        return parallel_groups


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "ContractRegistry",
    "ContractRegistryError",
    "ContractNotFoundError",
    "ContractTransitionError",
    "DependencyCycleError",
]
