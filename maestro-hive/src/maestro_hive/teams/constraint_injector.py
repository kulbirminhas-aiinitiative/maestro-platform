#!/usr/bin/env python3
"""
Constraint Injector - Proactive BDV/ACC Prompt Injection (MD-3096)

This module implements proactive constraint injection to prevent issues
BEFORE code is generated. Unlike reactive validation (MD-3093 shift-left),
this injects rules INTO prompts so AI knows constraints upfront.

Architecture:
    ConstraintInjector
        ├── inject_bdv_constraints() - BDV Gherkin features (AC-1)
        ├── inject_acc_constraints() - ACC architectural rules (AC-2)
        ├── inject_security_constraints() - Security rules (AC-3)
        ├── configure() - Configurable injection (AC-4)
        └── get_injection_metrics() - Track effectiveness (AC-5)

Key Benefits:
    - Prevention > Detection (AI knows rules upfront)
    - Reduced rework cycles
    - Better first-pass quality
    - Measurable improvement in validation pass rates

Related:
    - MD-3093: Shift-Left Validation (reactive validation)
    - MD-3096: Proactive Constraint Injection (this module)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class ConstraintType(str, Enum):
    """Types of constraints that can be injected."""
    BDV = "bdv"           # Behavior-Driven Validation (Gherkin features)
    ACC = "acc"           # Architectural Conformance Checking
    SECURITY = "security" # Security constraints (OWASP, input validation)


@dataclass
class InjectorConfig:
    """Configuration for constraint injection (AC-4: Configurable)."""
    enable_bdv_injection: bool = True
    enable_acc_injection: bool = True
    enable_security_injection: bool = True

    # BDV settings
    max_bdv_scenarios: int = 10  # Max scenarios to inject
    bdv_priority_threshold: str = "high"  # Only inject high+ priority scenarios

    # ACC settings
    max_acc_rules: int = 15  # Max architectural rules
    acc_rule_categories: List[str] = field(default_factory=lambda: [
        "layer_dependencies",
        "forbidden_imports",
        "naming_conventions",
        "module_boundaries"
    ])

    # Security settings
    security_categories: List[str] = field(default_factory=lambda: [
        "input_validation",
        "sql_injection",
        "xss_prevention",
        "auth_requirements"
    ])
    personas_requiring_security: List[str] = field(default_factory=lambda: [
        "backend_developer",
        "api_developer",
        "security_engineer",
        "devops_engineer"
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "enable_bdv_injection": self.enable_bdv_injection,
            "enable_acc_injection": self.enable_acc_injection,
            "enable_security_injection": self.enable_security_injection,
            "max_bdv_scenarios": self.max_bdv_scenarios,
            "bdv_priority_threshold": self.bdv_priority_threshold,
            "max_acc_rules": self.max_acc_rules,
            "acc_rule_categories": self.acc_rule_categories,
            "security_categories": self.security_categories,
            "personas_requiring_security": self.personas_requiring_security,
        }


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class BDVScenario:
    """A BDV Gherkin scenario for injection."""
    id: str
    name: str
    feature: str
    gherkin: str
    priority: str  # "critical", "high", "medium", "low"
    tags: List[str] = field(default_factory=list)


@dataclass
class ACCRule:
    """An ACC architectural rule for injection."""
    id: str
    name: str
    description: str
    rule_type: str  # "layer_dependency", "forbidden_import", "naming", etc.
    enforcement: str  # "blocking", "warning"
    examples: List[str] = field(default_factory=list)


@dataclass
class SecurityConstraint:
    """A security constraint for injection."""
    id: str
    name: str
    category: str
    description: str
    mitigation: str
    owasp_reference: Optional[str] = None


@dataclass
class InjectionResult:
    """Result of constraint injection into a prompt."""
    original_prompt_hash: str
    injected_prompt_hash: str

    bdv_scenarios_injected: int = 0
    acc_rules_injected: int = 0
    security_constraints_injected: int = 0

    total_tokens_added: int = 0  # Estimated tokens added
    injection_time_ms: float = 0.0

    constraint_sections: List[str] = field(default_factory=list)

    @property
    def total_constraints_injected(self) -> int:
        """Total number of constraints injected."""
        return (
            self.bdv_scenarios_injected +
            self.acc_rules_injected +
            self.security_constraints_injected
        )


@dataclass
class InjectionMetrics:
    """
    Metrics for tracking injection effectiveness (AC-5).

    Used to measure the 30% reduction in first-pass failures target.
    """
    total_injections: int = 0
    prompts_with_bdv: int = 0
    prompts_with_acc: int = 0
    prompts_with_security: int = 0

    # Effectiveness tracking
    first_pass_successes: int = 0
    first_pass_failures: int = 0

    # Before/after comparison
    baseline_failure_rate: float = 0.0  # Historical rate before injection
    current_failure_rate: float = 0.0   # Rate with injection

    @property
    def improvement_percentage(self) -> float:
        """Calculate improvement in first-pass success rate."""
        if self.baseline_failure_rate == 0:
            return 0.0
        reduction = self.baseline_failure_rate - self.current_failure_rate
        return (reduction / self.baseline_failure_rate) * 100

    @property
    def meets_target(self) -> bool:
        """Check if we meet the 30% reduction target (AC-5)."""
        return self.improvement_percentage >= 30.0


# =============================================================================
# CONSTRAINT INJECTOR
# =============================================================================

class ConstraintInjector:
    """
    Proactive constraint injection engine for persona prompts.

    Injects BDV, ACC, and security constraints INTO prompts BEFORE
    code generation, enabling AI to know rules upfront.

    This is the PROACTIVE counterpart to ShiftLeftValidator (reactive).

    Acceptance Criteria Coverage:
        - AC-1: inject_bdv_constraints() - BDV Gherkin features
        - AC-2: inject_acc_constraints() - ACC architectural rules
        - AC-3: inject_security_constraints() - Security constraints
        - AC-4: configure() - Configurable per constraint type
        - AC-5: get_metrics() - Measurable improvement tracking
    """

    def __init__(self, config: Optional[InjectorConfig] = None):
        """
        Initialize the constraint injector.

        Args:
            config: Optional configuration override
        """
        self.config = config or InjectorConfig()
        self._bdv_service = None
        self._acc_service = None
        self._metrics = InjectionMetrics()
        self._cache: Dict[str, Any] = {}  # Cache for expensive lookups

        logger.info("ConstraintInjector initialized (MD-3096)")
        logger.info(f"  BDV injection: {self.config.enable_bdv_injection}")
        logger.info(f"  ACC injection: {self.config.enable_acc_injection}")
        logger.info(f"  Security injection: {self.config.enable_security_injection}")

    def configure(
        self,
        enable_bdv: Optional[bool] = None,
        enable_acc: Optional[bool] = None,
        enable_security: Optional[bool] = None,
        **kwargs
    ) -> None:
        """
        AC-4: Configure constraint injection (enable/disable per type).

        Args:
            enable_bdv: Enable/disable BDV injection
            enable_acc: Enable/disable ACC injection
            enable_security: Enable/disable security injection
            **kwargs: Additional config options
        """
        if enable_bdv is not None:
            self.config.enable_bdv_injection = enable_bdv
        if enable_acc is not None:
            self.config.enable_acc_injection = enable_acc
        if enable_security is not None:
            self.config.enable_security_injection = enable_security

        # Apply additional config
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        logger.info(f"ConstraintInjector configured: BDV={self.config.enable_bdv_injection}, "
                   f"ACC={self.config.enable_acc_injection}, Security={self.config.enable_security_injection}")

    def inject_constraints(
        self,
        base_prompt: str,
        persona_id: str,
        requirement: str,
        contracts: Optional[List[Dict[str, Any]]] = None,
        project_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, InjectionResult]:
        """
        Inject all applicable constraints into a persona prompt.

        This is the main entry point for prompt enhancement.

        Args:
            base_prompt: Original persona prompt
            persona_id: ID of the persona (for context-specific injection)
            requirement: Current requirement being worked on
            contracts: Contracts for this execution (for BDV scenarios)
            project_context: Additional project context (for ACC rules)

        Returns:
            Tuple of (enhanced_prompt, injection_result)
        """
        import time
        start_time = time.time()

        result = InjectionResult(
            original_prompt_hash=self._hash_prompt(base_prompt),
            injected_prompt_hash=""
        )

        constraint_sections = []

        # AC-1: BDV Gherkin features
        if self.config.enable_bdv_injection:
            bdv_section, bdv_count = self._inject_bdv_constraints(
                requirement, contracts or []
            )
            if bdv_section:
                constraint_sections.append(bdv_section)
                result.bdv_scenarios_injected = bdv_count
                self._metrics.prompts_with_bdv += 1

        # AC-2: ACC architectural rules
        if self.config.enable_acc_injection:
            acc_section, acc_count = self._inject_acc_constraints(
                project_context or {}
            )
            if acc_section:
                constraint_sections.append(acc_section)
                result.acc_rules_injected = acc_count
                self._metrics.prompts_with_acc += 1

        # AC-3: Security constraints (for relevant personas)
        if self.config.enable_security_injection:
            if persona_id in self.config.personas_requiring_security:
                sec_section, sec_count = self._inject_security_constraints(persona_id)
                if sec_section:
                    constraint_sections.append(sec_section)
                    result.security_constraints_injected = sec_count
                    self._metrics.prompts_with_security += 1

        # Build enhanced prompt
        if constraint_sections:
            constraints_block = "\n\n".join(constraint_sections)
            enhanced_prompt = f"""{base_prompt}

# =============================================================================
# MANDATORY CONSTRAINTS (Injected by ConstraintInjector - MD-3096)
# =============================================================================
# Your code MUST satisfy these constraints. They will be validated automatically.
# Violating these constraints will cause your work to be rejected.

{constraints_block}

# =============================================================================
# END MANDATORY CONSTRAINTS
# =============================================================================
"""
        else:
            enhanced_prompt = base_prompt

        # Finalize result
        result.injected_prompt_hash = self._hash_prompt(enhanced_prompt)
        result.constraint_sections = [s[:100] + "..." for s in constraint_sections]
        result.injection_time_ms = (time.time() - start_time) * 1000
        result.total_tokens_added = self._estimate_tokens(enhanced_prompt) - self._estimate_tokens(base_prompt)

        # Update metrics
        self._metrics.total_injections += 1

        logger.info(f"Constraints injected for {persona_id}: "
                   f"BDV={result.bdv_scenarios_injected}, "
                   f"ACC={result.acc_rules_injected}, "
                   f"Security={result.security_constraints_injected} "
                   f"(+{result.total_tokens_added} tokens, {result.injection_time_ms:.1f}ms)")

        return enhanced_prompt, result

    def _inject_bdv_constraints(
        self,
        requirement: str,
        contracts: List[Dict[str, Any]]
    ) -> Tuple[str, int]:
        """
        AC-1: Inject BDV Gherkin features as must-pass tests.

        Args:
            requirement: Current requirement
            contracts: Contracts with acceptance criteria

        Returns:
            Tuple of (constraint_section, count)
        """
        scenarios = self._get_bdv_scenarios(requirement, contracts)

        if not scenarios:
            return "", 0

        # Build Gherkin section
        lines = [
            "## MUST-PASS BEHAVIORAL TESTS (BDV)",
            "",
            "Your implementation MUST satisfy these Gherkin scenarios.",
            "These will be automatically validated after code generation.",
            ""
        ]

        # Apply limit
        limited_scenarios = scenarios[:self.config.max_bdv_scenarios]

        for i, scenario in enumerate(limited_scenarios, 1):
            lines.append(f"### Test {i}: {scenario.name}")
            lines.append(f"Priority: {scenario.priority.upper()}")
            lines.append("```gherkin")
            lines.append(scenario.gherkin)
            lines.append("```")
            lines.append("")

        # Return count of INJECTED scenarios (not total available)
        return "\n".join(lines), len(limited_scenarios)

    def _inject_acc_constraints(
        self,
        project_context: Dict[str, Any]
    ) -> Tuple[str, int]:
        """
        AC-2: Inject ACC architectural rules.

        Args:
            project_context: Project architecture context

        Returns:
            Tuple of (constraint_section, count)
        """
        rules = self._get_acc_rules(project_context)

        if not rules:
            return "", 0

        # Build architecture section
        lines = [
            "## ARCHITECTURAL CONSTRAINTS (ACC)",
            "",
            "Your code MUST follow these architectural rules.",
            "Violations will be detected and your work will be rejected.",
            ""
        ]

        # Apply limit
        limited_rules = rules[:self.config.max_acc_rules]

        for i, rule in enumerate(limited_rules, 1):
            lines.append(f"### Rule {i}: {rule.name}")
            lines.append(f"Type: {rule.rule_type} | Enforcement: {rule.enforcement.upper()}")
            lines.append(f"Description: {rule.description}")
            if rule.examples:
                lines.append("Examples:")
                for ex in rule.examples[:2]:
                    lines.append(f"  - {ex}")
            lines.append("")

        # Return count of INJECTED rules (not total available)
        return "\n".join(lines), len(limited_rules)

    def _inject_security_constraints(
        self,
        persona_id: str
    ) -> Tuple[str, int]:
        """
        AC-3: Inject security constraints for relevant personas.

        Args:
            persona_id: Persona to inject security for

        Returns:
            Tuple of (constraint_section, count)
        """
        constraints = self._get_security_constraints(persona_id)

        if not constraints:
            return "", 0

        # Build security section
        lines = [
            "## SECURITY REQUIREMENTS (OWASP)",
            "",
            "Your code MUST implement these security controls.",
            "Security violations will cause immediate rejection.",
            ""
        ]

        for i, constraint in enumerate(constraints, 1):
            lines.append(f"### Security {i}: {constraint.name}")
            lines.append(f"Category: {constraint.category}")
            lines.append(f"Requirement: {constraint.description}")
            lines.append(f"Mitigation: {constraint.mitigation}")
            if constraint.owasp_reference:
                lines.append(f"Reference: {constraint.owasp_reference}")
            lines.append("")

        return "\n".join(lines), len(constraints)

    def _get_bdv_scenarios(
        self,
        requirement: str,
        contracts: List[Dict[str, Any]]
    ) -> List[BDVScenario]:
        """
        Get BDV scenarios for the requirement.

        Extracts Gherkin scenarios from:
        1. BDV service (if available)
        2. Contract acceptance criteria (fallback)
        """
        scenarios = []

        # Try BDV service first
        bdv_service = self._get_bdv_service()
        if bdv_service:
            try:
                bdv_scenarios = bdv_service.get_scenarios_for_requirement(requirement)
                for s in bdv_scenarios:
                    scenarios.append(BDVScenario(
                        id=s.get("id", f"bdv_{len(scenarios)}"),
                        name=s.get("name", "Unknown"),
                        feature=s.get("feature", ""),
                        gherkin=s.get("gherkin", ""),
                        priority=s.get("priority", "medium"),
                        tags=s.get("tags", [])
                    ))
            except Exception as e:
                logger.warning(f"BDV service error: {e}")

        # Fallback: Generate from contract acceptance criteria
        if not scenarios and contracts:
            for contract in contracts:
                for ac in contract.get("acceptance_criteria", []):
                    scenarios.append(BDVScenario(
                        id=f"contract_ac_{len(scenarios)}",
                        name=f"Contract: {contract.get('name', 'Unknown')}",
                        feature=contract.get("name", ""),
                        gherkin=self._ac_to_gherkin(ac),
                        priority="high"
                    ))

        return scenarios

    def _get_acc_rules(
        self,
        project_context: Dict[str, Any]
    ) -> List[ACCRule]:
        """
        Get ACC architectural rules for the project.

        Returns standard rules plus project-specific rules if available.
        """
        rules = []

        # Try ACC service first
        acc_service = self._get_acc_service()
        if acc_service:
            try:
                acc_rules = acc_service.get_rules()
                for r in acc_rules:
                    rules.append(ACCRule(
                        id=r.get("id", f"acc_{len(rules)}"),
                        name=r.get("name", "Unknown"),
                        description=r.get("description", ""),
                        rule_type=r.get("type", "general"),
                        enforcement=r.get("enforcement", "warning"),
                        examples=r.get("examples", [])
                    ))
            except Exception as e:
                logger.warning(f"ACC service error: {e}")

        # Always include standard architectural rules
        standard_rules = [
            ACCRule(
                id="acc_layer_deps",
                name="Layer Dependencies",
                description="Domain layer cannot import from Infrastructure or Presentation layers",
                rule_type="layer_dependency",
                enforcement="blocking",
                examples=[
                    "domain/ cannot import from infrastructure/",
                    "domain/ cannot import from api/ or routes/"
                ]
            ),
            ACCRule(
                id="acc_no_circular",
                name="No Circular Dependencies",
                description="Modules cannot have circular import dependencies",
                rule_type="circular_dependency",
                enforcement="blocking",
                examples=[
                    "A imports B, B imports A = VIOLATION",
                    "Use dependency injection to break cycles"
                ]
            ),
            ACCRule(
                id="acc_interface_boundary",
                name="Interface Boundaries",
                description="External systems must be accessed through adapter interfaces",
                rule_type="module_boundary",
                enforcement="warning",
                examples=[
                    "Database access through repository pattern",
                    "HTTP clients through adapter classes"
                ]
            ),
        ]

        # Add standard rules that aren't already present
        existing_ids = {r.id for r in rules}
        for rule in standard_rules:
            if rule.id not in existing_ids:
                rules.append(rule)

        return rules

    def _get_security_constraints(
        self,
        persona_id: str
    ) -> List[SecurityConstraint]:
        """
        Get security constraints for the persona.

        Returns OWASP-based security requirements.
        """
        # Standard security constraints (OWASP Top 10 based)
        all_constraints = [
            SecurityConstraint(
                id="sec_input_validation",
                name="Input Validation",
                category="input_validation",
                description="All user input must be validated and sanitized before processing",
                mitigation="Use allowlists, escape special characters, validate types and ranges",
                owasp_reference="A03:2021-Injection"
            ),
            SecurityConstraint(
                id="sec_sql_injection",
                name="SQL Injection Prevention",
                category="sql_injection",
                description="Never concatenate user input into SQL queries",
                mitigation="Use parameterized queries or ORM with proper escaping",
                owasp_reference="A03:2021-Injection"
            ),
            SecurityConstraint(
                id="sec_xss",
                name="XSS Prevention",
                category="xss_prevention",
                description="All output to HTML must be properly escaped",
                mitigation="Use auto-escaping templates, sanitize HTML, use CSP headers",
                owasp_reference="A03:2021-Injection"
            ),
            SecurityConstraint(
                id="sec_auth",
                name="Authentication Requirements",
                category="auth_requirements",
                description="Protected endpoints must verify authentication and authorization",
                mitigation="Use JWT/session validation, implement RBAC, check permissions",
                owasp_reference="A01:2021-Broken Access Control"
            ),
            SecurityConstraint(
                id="sec_secrets",
                name="Secret Management",
                category="secrets",
                description="Never hardcode secrets, API keys, or credentials in code",
                mitigation="Use environment variables or secret management systems",
                owasp_reference="A02:2021-Cryptographic Failures"
            ),
        ]

        # Filter by configured categories
        return [
            c for c in all_constraints
            if c.category in self.config.security_categories
        ]

    def _ac_to_gherkin(self, ac: str) -> str:
        """Convert acceptance criteria text to Gherkin format."""
        return f"""Feature: Contract Acceptance
  Scenario: {ac[:50]}...
    Given the system is set up correctly
    When the functionality is executed
    Then {ac}
"""

    def _get_bdv_service(self):
        """Lazy-load BDV service."""
        if self._bdv_service is None:
            try:
                from bdv.integration_service import get_bdv_integration_service
                self._bdv_service = get_bdv_integration_service()
            except ImportError:
                pass
        return self._bdv_service

    def _get_acc_service(self):
        """Lazy-load ACC service."""
        if self._acc_service is None:
            try:
                from acc.integration_service import get_acc_integration_service
                self._acc_service = get_acc_integration_service()
            except ImportError:
                pass
        return self._acc_service

    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash of prompt for tracking."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:12]

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Rough estimate: ~4 chars per token
        return len(text) // 4

    # =========================================================================
    # METRICS (AC-5)
    # =========================================================================

    def get_metrics(self) -> InjectionMetrics:
        """
        AC-5: Get injection metrics for effectiveness tracking.

        Returns:
            InjectionMetrics with success/failure rates
        """
        return self._metrics

    def record_execution_result(self, success: bool) -> None:
        """
        Record execution result for metrics tracking.

        Called after persona execution to track first-pass success rate.

        Args:
            success: Whether the execution passed validation on first try
        """
        if success:
            self._metrics.first_pass_successes += 1
        else:
            self._metrics.first_pass_failures += 1

        # Update current failure rate
        total = self._metrics.first_pass_successes + self._metrics.first_pass_failures
        if total > 0:
            self._metrics.current_failure_rate = (
                self._metrics.first_pass_failures / total
            )

    def set_baseline_failure_rate(self, rate: float) -> None:
        """
        Set baseline failure rate for comparison.

        Args:
            rate: Historical failure rate (0.0 to 1.0)
        """
        self._metrics.baseline_failure_rate = rate
        logger.info(f"Baseline failure rate set: {rate:.1%}")

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics = InjectionMetrics()
        logger.info("ConstraintInjector metrics reset")


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_injector_instance: Optional[ConstraintInjector] = None


def get_constraint_injector(config: Optional[InjectorConfig] = None) -> ConstraintInjector:
    """
    Get the singleton ConstraintInjector instance.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        ConstraintInjector instance
    """
    global _injector_instance
    if _injector_instance is None:
        _injector_instance = ConstraintInjector(config)
    return _injector_instance


def inject_constraints_into_prompt(
    prompt: str,
    persona_id: str,
    requirement: str,
    **kwargs
) -> str:
    """
    Convenience function to inject constraints into a prompt.

    Args:
        prompt: Base prompt
        persona_id: Persona identifier
        requirement: Current requirement
        **kwargs: Additional context

    Returns:
        Enhanced prompt with constraints
    """
    injector = get_constraint_injector()
    enhanced, _ = injector.inject_constraints(
        prompt, persona_id, requirement, **kwargs
    )
    return enhanced
