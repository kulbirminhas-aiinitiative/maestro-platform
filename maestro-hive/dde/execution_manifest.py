"""
DDE Execution Manifest Production Module (MD-885)

Defines the execution plan for a workflow iteration.
Tracks nodes, dependencies, policies, and execution state.

ML Integration Points:
- Effort estimation model
- Dependency optimization
- Parallel execution prediction
"""

import json
import yaml
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Node types in execution manifest"""
    ACTION = "action"
    PHASE = "phase"
    CHECKPOINT = "checkpoint"
    NOTIFICATION = "notification"
    INTERFACE = "interface"
    IMPLEMENTATION = "impl"


class NodeStatus(Enum):
    """Execution status of a node"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class PolicySeverity(Enum):
    """Policy severity levels"""
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ManifestPolicy:
    """Policy/gate in execution manifest"""
    policy_id: str
    name: str
    severity: str
    description: Optional[str] = None
    condition: Optional[str] = None  # Expression to evaluate
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None and v != {}}


@dataclass
class ManifestNode:
    """Node in execution manifest"""
    node_id: str
    name: str
    node_type: str
    capability: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    gates: List[str] = field(default_factory=list)  # Policy IDs
    estimated_effort_hours: Optional[float] = None
    contract_id: Optional[str] = None
    assigned_agent: Optional[str] = None
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'node_id': self.node_id,
            'name': self.name,
            'node_type': self.node_type,
            'status': self.status
        }
        if self.capability:
            result['capability'] = self.capability
        if self.depends_on:
            result['depends_on'] = self.depends_on
        if self.outputs:
            result['outputs'] = self.outputs
        if self.gates:
            result['gates'] = self.gates
        if self.estimated_effort_hours:
            result['estimated_effort_hours'] = self.estimated_effort_hours
        if self.contract_id:
            result['contract_id'] = self.contract_id
        if self.assigned_agent:
            result['assigned_agent'] = self.assigned_agent
        if self.started_at:
            result['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        if self.error_message:
            result['error_message'] = self.error_message
        if self.metadata:
            result['metadata'] = self.metadata
        return result


class ExecutionManifest:
    """
    Execution Manifest

    Defines the complete execution plan for a workflow iteration.
    """

    def __init__(
        self,
        manifest_id: str,
        workflow_id: str,
        iteration: int = 1,
        description: str = ""
    ):
        """
        Initialize execution manifest.

        Args:
            manifest_id: Unique manifest identifier
            workflow_id: Parent workflow ID
            iteration: Iteration number
            description: Manifest description
        """
        self.manifest_id = manifest_id
        self.workflow_id = workflow_id
        self.iteration = iteration
        self.description = description

        self.nodes: Dict[str, ManifestNode] = {}
        self.policies: Dict[str, ManifestPolicy] = {}
        self.metadata: Dict[str, Any] = {}

        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.status = "pending"  # pending, running, completed, failed

    def add_node(self, node: ManifestNode) -> 'ExecutionManifest':
        """Add a node to the manifest"""
        self.nodes[node.node_id] = node
        self.updated_at = datetime.now()
        return self

    def add_policy(self, policy: ManifestPolicy) -> 'ExecutionManifest':
        """Add a policy to the manifest"""
        self.policies[policy.policy_id] = policy
        self.updated_at = datetime.now()
        return self

    def get_node(self, node_id: str) -> Optional[ManifestNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)

    def update_node_status(
        self,
        node_id: str,
        status: str,
        error_message: str = None
    ):
        """Update node execution status"""
        if node_id not in self.nodes:
            raise ValueError(f"Node not found: {node_id}")

        node = self.nodes[node_id]
        node.status = status

        if status == "running" and not node.started_at:
            node.started_at = datetime.now()
        elif status in ["completed", "failed"]:
            node.completed_at = datetime.now()

        if error_message:
            node.error_message = error_message

        self.updated_at = datetime.now()

    def get_ready_nodes(self) -> List[ManifestNode]:
        """Get nodes that are ready to execute (dependencies met)"""
        ready = []

        for node in self.nodes.values():
            if node.status != "pending":
                continue

            # Check if all dependencies are completed
            deps_met = True
            for dep_id in node.depends_on:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status != "completed":
                    deps_met = False
                    break

            if deps_met:
                ready.append(node)

        return ready

    def get_execution_order(self) -> List[List[str]]:
        """
        Get execution order as groups that can run in parallel.

        Returns:
            List of lists, where each inner list contains
            node IDs that can execute concurrently.
        """
        order = []
        executed = set()
        remaining = set(self.nodes.keys())

        while remaining:
            # Find nodes with all dependencies satisfied
            group = []
            for node_id in remaining:
                node = self.nodes[node_id]
                deps_met = all(dep in executed for dep in node.depends_on)
                if deps_met:
                    group.append(node_id)

            if not group:
                # Circular dependency detected
                raise ValueError(f"Circular dependency detected in nodes: {remaining}")

            order.append(group)
            executed.update(group)
            remaining -= set(group)

        return order

    def validate(self) -> List[str]:
        """
        Validate manifest structure.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for required fields
        if not self.manifest_id:
            errors.append("manifest_id is required")
        if not self.workflow_id:
            errors.append("workflow_id is required")

        # Validate nodes
        for node_id, node in self.nodes.items():
            # Check dependencies exist
            for dep_id in node.depends_on:
                if dep_id not in self.nodes:
                    errors.append(f"Node {node_id} depends on non-existent node {dep_id}")

            # Check gates reference valid policies
            for gate_id in node.gates:
                if gate_id not in self.policies:
                    errors.append(f"Node {node_id} references non-existent policy {gate_id}")

        # Check for cycles
        try:
            self.get_execution_order()
        except ValueError as e:
            errors.append(str(e))

        return errors

    def get_progress(self) -> Dict[str, Any]:
        """Get execution progress summary"""
        total = len(self.nodes)
        completed = sum(1 for n in self.nodes.values() if n.status == "completed")
        failed = sum(1 for n in self.nodes.values() if n.status == "failed")
        running = sum(1 for n in self.nodes.values() if n.status == "running")
        pending = sum(1 for n in self.nodes.values() if n.status == "pending")

        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'running': running,
            'pending': pending,
            'progress_percent': (completed / total * 100) if total > 0 else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'manifest_id': self.manifest_id,
            'workflow_id': self.workflow_id,
            'iteration': self.iteration,
            'description': self.description,
            'status': self.status,
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'policies': {k: v.to_dict() for k, v in self.policies.items()},
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'progress': self.get_progress()
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)

    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False)

    def save(self, path: str):
        """Save manifest to file"""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if path.endswith('.yaml') or path.endswith('.yml'):
            with open(path, 'w') as f:
                f.write(self.to_yaml())
        else:
            with open(path, 'w') as f:
                f.write(self.to_json())

        logger.info(f"💾 Saved manifest to {path}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionManifest':
        """Create manifest from dictionary"""
        manifest = cls(
            manifest_id=data['manifest_id'],
            workflow_id=data['workflow_id'],
            iteration=data.get('iteration', 1),
            description=data.get('description', '')
        )

        manifest.status = data.get('status', 'pending')
        manifest.metadata = data.get('metadata', {})

        if 'created_at' in data:
            manifest.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            manifest.updated_at = datetime.fromisoformat(data['updated_at'])

        # Load nodes
        for node_id, node_data in data.get('nodes', {}).items():
            node = ManifestNode(
                node_id=node_data['node_id'],
                name=node_data['name'],
                node_type=node_data['node_type'],
                capability=node_data.get('capability'),
                depends_on=node_data.get('depends_on', []),
                outputs=node_data.get('outputs', []),
                gates=node_data.get('gates', []),
                estimated_effort_hours=node_data.get('estimated_effort_hours'),
                contract_id=node_data.get('contract_id'),
                assigned_agent=node_data.get('assigned_agent'),
                status=node_data.get('status', 'pending'),
                metadata=node_data.get('metadata', {})
            )
            if node_data.get('started_at'):
                node.started_at = datetime.fromisoformat(node_data['started_at'])
            if node_data.get('completed_at'):
                node.completed_at = datetime.fromisoformat(node_data['completed_at'])
            manifest.add_node(node)

        # Load policies
        for policy_id, policy_data in data.get('policies', {}).items():
            policy = ManifestPolicy(
                policy_id=policy_data['policy_id'],
                name=policy_data['name'],
                severity=policy_data['severity'],
                description=policy_data.get('description'),
                condition=policy_data.get('condition'),
                metadata=policy_data.get('metadata', {})
            )
            manifest.add_policy(policy)

        return manifest

    @classmethod
    def load(cls, path: str) -> 'ExecutionManifest':
        """Load manifest from file"""
        with open(path) as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        return cls.from_dict(data)


class ManifestBuilder:
    """Builder for creating execution manifests from contracts"""

    @staticmethod
    def from_contracts(
        workflow_id: str,
        contracts: List[Dict[str, Any]],
        iteration: int = 1
    ) -> ExecutionManifest:
        """
        Build manifest from contract definitions.

        Args:
            workflow_id: Workflow ID
            contracts: List of contract dictionaries
            iteration: Iteration number

        Returns:
            ExecutionManifest
        """
        # Generate manifest ID
        manifest_id = f"manifest_{workflow_id}_{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        manifest = ExecutionManifest(
            manifest_id=manifest_id,
            workflow_id=workflow_id,
            iteration=iteration,
            description=f"Iteration {iteration} of {workflow_id}"
        )

        # Create nodes from contracts
        contract_to_node = {}

        for contract in contracts:
            contract_id = contract.get('id', contract.get('contract_id'))
            provider = contract.get('provider', '')
            name = contract.get('name', f"Contract {contract_id}")

            node_id = f"node_{contract_id}"
            contract_to_node[contract_id] = node_id

            # Determine node type
            node_type = "action"
            if "test" in name.lower() or "qa" in provider.lower():
                node_type = "checkpoint"

            node = ManifestNode(
                node_id=node_id,
                name=name,
                node_type=node_type,
                capability=provider,
                contract_id=contract_id,
                estimated_effort_hours=contract.get('estimated_effort', 1.0),
                metadata={'contract': contract}
            )

            manifest.add_node(node)

        # Set up dependencies based on contract dependencies
        for contract in contracts:
            contract_id = contract.get('id', contract.get('contract_id'))
            node_id = contract_to_node.get(contract_id)

            if not node_id:
                continue

            dependencies = contract.get('dependencies', [])
            node = manifest.get_node(node_id)

            for dep_contract_id in dependencies:
                dep_node_id = contract_to_node.get(dep_contract_id)
                if dep_node_id:
                    node.depends_on.append(dep_node_id)

        # Add default quality policies
        manifest.add_policy(ManifestPolicy(
            policy_id="quality_gate",
            name="Quality Gate",
            severity="BLOCKING",
            description="Contract must be fulfilled with quality score >= 0.8"
        ))

        manifest.add_policy(ManifestPolicy(
            policy_id="timeout_warning",
            name="Timeout Warning",
            severity="WARNING",
            description="Execution exceeds estimated effort by 50%"
        ))

        # Validate
        errors = manifest.validate()
        if errors:
            logger.warning(f"Manifest validation errors: {errors}")

        return manifest


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create manifest manually
    manifest = ExecutionManifest(
        manifest_id="manifest_001",
        workflow_id="workflow_test",
        iteration=1,
        description="Test workflow manifest"
    )

    # Add nodes
    manifest.add_node(ManifestNode(
        node_id="node_1",
        name="Requirements Analysis",
        node_type="action",
        capability="requirement_analyst",
        estimated_effort_hours=0.5,
        outputs=["requirements.md"]
    ))

    manifest.add_node(ManifestNode(
        node_id="node_2",
        name="Backend Development",
        node_type="action",
        capability="backend_developer",
        depends_on=["node_1"],
        estimated_effort_hours=2.0,
        outputs=["api.py", "models.py"]
    ))

    manifest.add_node(ManifestNode(
        node_id="node_3",
        name="Testing",
        node_type="checkpoint",
        capability="qa_engineer",
        depends_on=["node_2"],
        estimated_effort_hours=1.0,
        outputs=["tests.py", "coverage_report.html"]
    ))

    # Add policy
    manifest.add_policy(ManifestPolicy(
        policy_id="quality_gate",
        name="Quality Gate",
        severity="BLOCKING"
    ))

    # Validate
    errors = manifest.validate()
    if errors:
        print(f"Errors: {errors}")
    else:
        print("✅ Manifest is valid")

    # Get execution order
    order = manifest.get_execution_order()
    print(f"\nExecution order: {order}")

    # Print manifest
    print("\n=== Manifest ===")
    print(manifest.to_json())

    # Test building from contracts
    print("\n=== Build from Contracts ===")
    contracts = [
        {'id': 'c1', 'name': 'Requirements', 'provider': 'requirement_analyst', 'dependencies': []},
        {'id': 'c2', 'name': 'Backend', 'provider': 'backend_developer', 'dependencies': ['c1']},
        {'id': 'c3', 'name': 'Testing', 'provider': 'qa_engineer', 'dependencies': ['c2']},
    ]

    manifest2 = ManifestBuilder.from_contracts("test_workflow", contracts)
    print(f"Built manifest with {len(manifest2.nodes)} nodes")
    print(f"Execution order: {manifest2.get_execution_order()}")
