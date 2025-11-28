"""
Policy Loader Module
Loads and manages YAML-based quality policies and phase SLOs for contract-as-code enforcement.

Version: 1.0.0
Last Updated: 2025-10-12
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityGate:
    """Represents a quality gate with threshold and severity."""
    name: str
    threshold: float
    severity: str  # BLOCKING or WARNING
    description: str
    rules: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class PersonaPolicy:
    """Represents quality policies for a specific persona."""
    persona_type: str
    description: str
    quality_gates: Dict[str, QualityGate]
    required_artifacts: List[str]
    optional_artifacts: List[str]


@dataclass
class PhaseSLO:
    """Represents SLOs and exit criteria for an SDLC phase."""
    phase_id: str
    phase_name: str
    description: str
    success_criteria: Dict[str, Dict[str, Any]]
    required_artifacts: List[str]
    optional_artifacts: List[str]
    exit_gates: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]


@dataclass
class ContractPolicy:
    """Master contract policy configuration."""
    version: str
    global_policies: Dict[str, Any]
    persona_policies: Dict[str, PersonaPolicy]
    build_policies: Dict[str, Any]
    security_policies: Dict[str, Any]
    traceability_policies: Dict[str, Any]
    deployment_policies: Dict[str, Any]
    quality_slo_policies: Dict[str, Any]
    override_policies: Dict[str, Any]
    monitoring_policies: Dict[str, Any]


@dataclass
class PhaseConfiguration:
    """Phase SLO configuration."""
    version: str
    global_settings: Dict[str, Any]
    phases: Dict[str, PhaseSLO]
    cross_phase_policies: Dict[str, Any]
    bypass_rules: Dict[str, Any]


class PolicyLoader:
    """
    Loads and manages YAML-based policies for quality gates and phase SLOs.
    Provides methods to retrieve policies by persona type and phase.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the policy loader.

        Args:
            config_dir: Directory containing YAML config files. Defaults to ./config
        """
        if config_dir is None:
            # Default to config/ directory relative to this file
            self.config_dir = Path(__file__).parent / "config"
        else:
            self.config_dir = Path(config_dir)

        self.master_contract_path = self.config_dir / "master_contract.yaml"
        self.phase_slos_path = self.config_dir / "phase_slos.yaml"

        # Cached policies
        self._contract_policy: Optional[ContractPolicy] = None
        self._phase_config: Optional[PhaseConfiguration] = None
        self._last_loaded: Optional[datetime] = None

        logger.info(f"PolicyLoader initialized with config_dir: {self.config_dir}")

    def load_policies(self, force_reload: bool = False) -> None:
        """
        Load or reload all policy configurations from YAML files.

        Args:
            force_reload: Force reload even if already loaded
        """
        if not force_reload and self._contract_policy and self._phase_config:
            logger.debug("Policies already loaded, skipping reload")
            return

        try:
            self._contract_policy = self._load_contract_policy()
            self._phase_config = self._load_phase_configuration()
            self._last_loaded = datetime.now()
            logger.info("Successfully loaded all policy configurations")
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
            raise

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse a YAML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Policy file not found: {file_path}")

        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty or invalid YAML file: {file_path}")

        return data

    def _load_contract_policy(self) -> ContractPolicy:
        """Load master contract policy from YAML."""
        data = self._load_yaml_file(self.master_contract_path)

        # Parse persona policies
        persona_policies = {}
        for persona_type, persona_data in data.get('persona_policies', {}).items():
            quality_gates = {}
            for gate_name, gate_data in persona_data.get('quality_gates', {}).items():
                quality_gates[gate_name] = QualityGate(
                    name=gate_name,
                    threshold=gate_data.get('threshold', 0.0),
                    severity=gate_data.get('severity', 'WARNING'),
                    description=gate_data.get('description', ''),
                    rules=gate_data.get('rules', []),
                    enabled=gate_data.get('enabled', True)
                )

            persona_policies[persona_type] = PersonaPolicy(
                persona_type=persona_type,
                description=persona_data.get('description', ''),
                quality_gates=quality_gates,
                required_artifacts=persona_data.get('artifacts', {}).get('required', []),
                optional_artifacts=persona_data.get('artifacts', {}).get('optional', [])
            )

        return ContractPolicy(
            version=data.get('version', '1.0.0'),
            global_policies=data.get('global_policies', {}),
            persona_policies=persona_policies,
            build_policies=data.get('build_policies', {}),
            security_policies=data.get('security_policies', {}),
            traceability_policies=data.get('traceability_policies', {}),
            deployment_policies=data.get('deployment_policies', {}),
            quality_slo_policies=data.get('quality_slo_policies', {}),
            override_policies=data.get('override_policies', {}),
            monitoring_policies=data.get('monitoring_policies', {})
        )

    def _load_phase_configuration(self) -> PhaseConfiguration:
        """Load phase SLO configuration from YAML."""
        data = self._load_yaml_file(self.phase_slos_path)

        # Parse phase configurations
        phases = {}
        for phase_id, phase_data in data.items():
            # Skip non-phase keys
            if phase_id in ['version', 'schema_version', 'global_settings',
                           'cross_phase_policies', 'bypass_rules', 'reporting']:
                continue

            phases[phase_id] = PhaseSLO(
                phase_id=phase_id,
                phase_name=phase_data.get('phase_name', phase_id),
                description=phase_data.get('description', ''),
                success_criteria=phase_data.get('success_criteria', {}),
                required_artifacts=phase_data.get('required_artifacts', []),
                optional_artifacts=phase_data.get('optional_artifacts', []),
                exit_gates=phase_data.get('exit_gates', []),
                metrics=phase_data.get('metrics', [])
            )

        return PhaseConfiguration(
            version=data.get('version', '1.0.0'),
            global_settings=data.get('global_settings', {}),
            phases=phases,
            cross_phase_policies=data.get('cross_phase_policies', {}),
            bypass_rules=data.get('bypass_rules', {})
        )

    def get_persona_policy(self, persona_type: str) -> Optional[PersonaPolicy]:
        """
        Get quality policy for a specific persona type.

        Args:
            persona_type: Type of persona (e.g., 'backend_developer')

        Returns:
            PersonaPolicy or None if not found
        """
        if not self._contract_policy:
            self.load_policies()

        return self._contract_policy.persona_policies.get(persona_type)

    def get_phase_slo(self, phase_id: str) -> Optional[PhaseSLO]:
        """
        Get SLO configuration for a specific phase with intelligent fallback.

        Fallback logic:
        1. Try exact match (e.g., 'implementation')
        2. If service_* → use 'service_template'
        3. If integration_* → use 'custom_component'
        4. Otherwise → use 'custom_component' as generic fallback

        Args:
            phase_id: Phase identifier (e.g., 'implementation', 'backend', 'service_1')

        Returns:
            PhaseSLO or None if not found
        """
        if not self._phase_config:
            self.load_policies()

        # Try exact match first
        slo = self._phase_config.phases.get(phase_id)
        if slo:
            return slo

        # Pattern matching for common custom types
        if phase_id.startswith('service_'):
            # service_1, service_2, etc. → use service_template
            logger.debug(f"Mapping {phase_id} to service_template")
            slo = self._phase_config.phases.get('service_template')
            if slo:
                return slo

        # Fallback to custom_component for undefined phase types
        logger.debug(f"Using custom_component fallback for {phase_id}")
        return self._phase_config.phases.get('custom_component')

    def get_quality_gates(self, persona_type: str) -> Dict[str, QualityGate]:
        """
        Get all quality gates for a persona type.

        Args:
            persona_type: Type of persona

        Returns:
            Dictionary of quality gates
        """
        persona_policy = self.get_persona_policy(persona_type)
        if not persona_policy:
            logger.warning(f"No policy found for persona type: {persona_type}")
            return {}

        return persona_policy.quality_gates

    def get_gate_threshold(self, persona_type: str, gate_name: str) -> Optional[float]:
        """
        Get threshold for a specific quality gate.

        Args:
            persona_type: Type of persona
            gate_name: Name of the quality gate

        Returns:
            Threshold value or None if not found
        """
        gates = self.get_quality_gates(persona_type)
        gate = gates.get(gate_name)
        return gate.threshold if gate else None

    def is_gate_blocking(self, persona_type: str, gate_name: str) -> bool:
        """
        Check if a quality gate is blocking for a persona.

        Args:
            persona_type: Type of persona
            gate_name: Name of the quality gate

        Returns:
            True if gate is blocking, False otherwise
        """
        gates = self.get_quality_gates(persona_type)
        gate = gates.get(gate_name)
        return gate.severity == "BLOCKING" if gate else False

    def get_phase_exit_gates(self, phase_id: str) -> List[Dict[str, Any]]:
        """
        Get exit gates for a specific phase.

        Args:
            phase_id: Phase identifier

        Returns:
            List of exit gate definitions
        """
        phase_slo = self.get_phase_slo(phase_id)
        if not phase_slo:
            logger.warning(f"No SLO found for phase: {phase_id}")
            return []

        return phase_slo.exit_gates

    def get_required_artifacts(self, persona_type: Optional[str] = None,
                              phase_id: Optional[str] = None) -> List[str]:
        """
        Get required artifacts for a persona or phase.

        Args:
            persona_type: Type of persona (optional)
            phase_id: Phase identifier (optional)

        Returns:
            List of required artifact names
        """
        artifacts = []

        if persona_type:
            persona_policy = self.get_persona_policy(persona_type)
            if persona_policy:
                artifacts.extend(persona_policy.required_artifacts)

        if phase_id:
            phase_slo = self.get_phase_slo(phase_id)
            if phase_slo:
                artifacts.extend(phase_slo.required_artifacts)

        return list(set(artifacts))  # Remove duplicates

    def can_bypass_gate(self, gate_name: str, phase_id: str) -> bool:
        """
        Check if a gate can be bypassed for a specific phase.

        Args:
            gate_name: Name of the quality gate
            phase_id: Phase identifier

        Returns:
            True if gate can be bypassed (with ADR), False otherwise
        """
        if not self._phase_config:
            self.load_policies()

        bypass_rules = self._phase_config.bypass_rules
        non_bypassable = bypass_rules.get('non_bypassable_gates', [])

        if gate_name in non_bypassable:
            return False

        bypassable = bypass_rules.get('bypassable_gates', [])
        for rule in bypassable:
            if rule.get('gate') == gate_name:
                phases = rule.get('phases', [])
                if not phases or phase_id in phases:
                    return True

        return False

    def get_global_policies(self) -> Dict[str, Any]:
        """Get global quality policies."""
        if not self._contract_policy:
            self.load_policies()

        return self._contract_policy.global_policies

    def get_security_policies(self) -> Dict[str, Any]:
        """Get security-specific policies."""
        if not self._contract_policy:
            self.load_policies()

        return self._contract_policy.security_policies

    def get_override_policies(self) -> Dict[str, Any]:
        """Get policy override rules."""
        if not self._contract_policy:
            self.load_policies()

        return self._contract_policy.override_policies

    def validate_persona_output(self, persona_type: str,
                               quality_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate persona output against quality gates.

        Args:
            persona_type: Type of persona
            quality_metrics: Dictionary of metric name to value

        Returns:
            Validation result with passed/failed gates
        """
        gates = self.get_quality_gates(persona_type)
        if not gates:
            return {
                "status": "error",
                "message": f"No gates found for persona: {persona_type}",
                "gates_passed": [],
                "gates_failed": []
            }

        gates_passed = []
        gates_failed = []

        for gate_name, gate in gates.items():
            if not gate.enabled:
                continue

            metric_value = quality_metrics.get(gate_name, 0.0)

            if metric_value >= gate.threshold:
                gates_passed.append(gate_name)
            else:
                gates_failed.append({
                    "gate": gate_name,
                    "threshold": gate.threshold,
                    "actual": metric_value,
                    "severity": gate.severity,
                    "description": gate.description
                })

        # Check if any blocking gates failed
        blocking_failures = [g for g in gates_failed if g["severity"] == "BLOCKING"]
        status = "fail" if blocking_failures else ("warning" if gates_failed else "pass")

        return {
            "status": status,
            "gates_passed": gates_passed,
            "gates_failed": gates_failed,
            "blocking_failures": len(blocking_failures),
            "total_gates": len(gates)
        }

    def validate_phase_transition(self, phase_id: str,
                                  phase_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate if phase transition criteria are met.

        Args:
            phase_id: Phase identifier
            phase_metrics: Dictionary of metric name to value

        Returns:
            Validation result with passed/failed exit gates
        """
        phase_slo = self.get_phase_slo(phase_id)
        if not phase_slo:
            return {
                "status": "error",
                "message": f"No SLO found for phase: {phase_id}",
                "gates_passed": [],
                "gates_failed": []
            }

        gates_passed = []
        gates_failed = []

        for exit_gate in phase_slo.exit_gates:
            gate_name = exit_gate.get('gate')
            condition = exit_gate.get('condition')
            severity = exit_gate.get('severity', 'WARNING')

            # Evaluate condition using success_criteria from phase SLO
            try:
                # Create evaluation namespace with all phase metrics
                eval_namespace = phase_metrics.copy()

                # Normalize condition (replace AND/OR with and/or for Python)
                normalized_condition = condition.replace(' AND ', ' and ').replace(' OR ', ' or ')

                # Evaluate the condition in the namespace
                result = eval(normalized_condition, {"__builtins__": {}}, eval_namespace)

                if result:
                    gates_passed.append(gate_name)
                else:
                    gates_failed.append({
                        "gate_name": gate_name,
                        "condition": condition,
                        "severity": severity,
                        "message": f"Gate condition not met: {condition}"
                    })
            except Exception as e:
                logger.error(f"Error evaluating condition for gate {gate_name}: {e}")
                # Treat evaluation errors as WARNING failures (not blocking)
                gates_failed.append({
                    "gate_name": gate_name,
                    "condition": condition,
                    "severity": "WARNING",  # Force to WARNING to not block
                    "message": f"Could not evaluate gate condition: {str(e)}",
                    "error": str(e)
                })

        # Check if any blocking gates failed
        blocking_failures = [g for g in gates_failed if g.get("severity") == "BLOCKING"]
        status = "fail" if blocking_failures else ("warning" if gates_failed else "pass")

        return {
            "status": status,
            "phase": phase_id,
            "gates_passed": gates_passed,
            "gates_failed": gates_failed,
            "blocking_failures": len(blocking_failures),
            "total_gates": len(phase_slo.exit_gates)
        }


# Singleton instance
_policy_loader_instance: Optional[PolicyLoader] = None


def get_policy_loader(config_dir: Optional[str] = None) -> PolicyLoader:
    """
    Get or create the singleton PolicyLoader instance.

    Args:
        config_dir: Optional config directory path

    Returns:
        PolicyLoader instance
    """
    global _policy_loader_instance

    if _policy_loader_instance is None:
        _policy_loader_instance = PolicyLoader(config_dir)
        _policy_loader_instance.load_policies()

    return _policy_loader_instance


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)

    loader = get_policy_loader()

    # Test persona policy loading
    print("\n=== Backend Developer Policy ===")
    backend_policy = loader.get_persona_policy("backend_developer")
    if backend_policy:
        print(f"Description: {backend_policy.description}")
        print(f"Quality Gates: {list(backend_policy.quality_gates.keys())}")
        print(f"Required Artifacts: {backend_policy.required_artifacts}")

    # Test phase SLO loading
    print("\n=== Implementation Phase SLO ===")
    impl_slo = loader.get_phase_slo("implementation")
    if impl_slo:
        print(f"Phase: {impl_slo.phase_name}")
        print(f"Success Criteria: {list(impl_slo.success_criteria.keys())}")
        print(f"Exit Gates: {len(impl_slo.exit_gates)}")

    # Test validation
    print("\n=== Validation Test ===")
    test_metrics = {
        "code_quality": 8.5,
        "test_coverage": 0.85,
        "security": 0,
        "complexity": 8,
        "documentation": 0.75
    }
    result = loader.validate_persona_output("backend_developer", test_metrics)
    print(f"Validation Status: {result['status']}")
    print(f"Gates Passed: {result['gates_passed']}")
    print(f"Gates Failed: {result['gates_failed']}")
