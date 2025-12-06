"""
ACC Auto-Fix Engine (MD-2089)

Generates fix suggestions for architectural violations.

Features:
- Layer violation fixes (move imports, DI)
- Cycle breaking suggestions
- Coupling reduction patterns
- Code change templates with confidence scores
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SuggestionType(str, Enum):
    """Type of auto-fix suggestion."""
    MOVE_IMPORT = "move_import"
    EXTRACT_INTERFACE = "extract_interface"
    DEPENDENCY_INJECTION = "dependency_injection"
    FACADE_PATTERN = "facade_pattern"
    EVENT_BUS = "event_bus"
    SPLIT_MODULE = "split_module"
    MERGE_MODULES = "merge_modules"


class EffortEstimate(str, Enum):
    """Effort estimate for implementing fix."""
    TRIVIAL = "trivial"  # < 1 hour
    SMALL = "small"  # 1-4 hours
    MEDIUM = "medium"  # 1-2 days
    LARGE = "large"  # > 2 days


@dataclass
class CodeChange:
    """Proposed code change."""
    file_path: str
    change_type: str  # ADD, REMOVE, MODIFY
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    explanation: str = ""


@dataclass
class AutoFixSuggestion:
    """Auto-fix suggestion for a violation."""
    violation_id: str
    violation_type: str
    suggestion_type: SuggestionType
    confidence: float  # 0.0 to 1.0
    title: str
    description: str
    code_changes: List[CodeChange] = field(default_factory=list)
    estimated_effort: EffortEstimate = EffortEstimate.SMALL
    prerequisites: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'violation_id': self.violation_id,
            'violation_type': self.violation_type,
            'suggestion_type': self.suggestion_type.value,
            'confidence': self.confidence,
            'title': self.title,
            'description': self.description,
            'code_changes': [
                {
                    'file_path': cc.file_path,
                    'change_type': cc.change_type,
                    'line_start': cc.line_start,
                    'line_end': cc.line_end,
                    'old_code': cc.old_code,
                    'new_code': cc.new_code,
                    'explanation': cc.explanation
                }
                for cc in self.code_changes
            ],
            'estimated_effort': self.estimated_effort.value,
            'prerequisites': self.prerequisites,
            'risks': self.risks
        }


class AutoFixEngine:
    """
    Generates auto-fix suggestions for architectural violations.

    Supports:
    - Layer violations (move imports, dependency injection)
    - Cyclic dependencies (extract interface, event bus)
    - High coupling (facade pattern, split module)
    """

    def __init__(
        self,
        components: Optional[Dict[str, List[str]]] = None,
        layers: Optional[List[str]] = None
    ):
        """
        Initialize auto-fix engine.

        Args:
            components: Component name to path patterns mapping
            layers: Layer order from top to bottom
        """
        self.components = components or {
            'Presentation': ['routes/', 'api/', 'controllers/', 'views/'],
            'BusinessLogic': ['services/', 'domain/', 'core/'],
            'DataAccess': ['repositories/', 'models/', 'database/', 'dal/'],
            'Infrastructure': ['utils/', 'helpers/', 'config/', 'common/']
        }

        self.layers = layers or [
            'Presentation',
            'BusinessLogic',
            'DataAccess',
            'Infrastructure'
        ]

    def suggest_fixes(
        self,
        violation: Dict[str, Any],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> List[AutoFixSuggestion]:
        """
        Generate fix suggestions for a violation.

        Args:
            violation: Violation dictionary with type, source, target, etc.
            graph_context: Optional import graph context

        Returns:
            List of AutoFixSuggestion sorted by confidence
        """
        violation_type = violation.get('rule_type', violation.get('type', 'unknown'))
        suggestions = []

        if violation_type in ['layer', 'must_not_call', 'dependency']:
            suggestions.extend(self._suggest_layer_fixes(violation))

        if violation_type in ['cycle', 'no_cycles']:
            suggestions.extend(self._suggest_cycle_fixes(violation, graph_context))

        if violation_type in ['coupling', 'high_coupling']:
            suggestions.extend(self._suggest_coupling_fixes(violation, graph_context))

        # Sort by confidence (highest first)
        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)

    def _suggest_layer_fixes(
        self,
        violation: Dict[str, Any]
    ) -> List[AutoFixSuggestion]:
        """Generate suggestions for layer violations."""
        suggestions = []

        source = violation.get('source_file', violation.get('source', ''))
        target = violation.get('target_file', violation.get('target', ''))
        source_component = self._get_component(source)
        target_component = self._get_component(target)

        # Suggestion 1: Move import to allowed layer
        suggestions.append(AutoFixSuggestion(
            violation_id=violation.get('rule_id', 'unknown'),
            violation_type='layer',
            suggestion_type=SuggestionType.MOVE_IMPORT,
            confidence=0.7,
            title=f"Move {target} import to BusinessLogic layer",
            description=(
                f"The import from {source_component or 'Unknown'} to "
                f"{target_component or 'Unknown'} violates layering rules. "
                f"Consider moving the dependency through the BusinessLogic layer."
            ),
            code_changes=[
                CodeChange(
                    file_path=source,
                    change_type="MODIFY",
                    explanation=f"Remove direct import of {target}",
                    old_code=f"from {target} import ...",
                    new_code=f"# Moved to service layer\n# from {target} import ..."
                )
            ],
            estimated_effort=EffortEstimate.SMALL,
            risks=["May require changes to multiple files"]
        ))

        # Suggestion 2: Use dependency injection
        suggestions.append(AutoFixSuggestion(
            violation_id=violation.get('rule_id', 'unknown'),
            violation_type='layer',
            suggestion_type=SuggestionType.DEPENDENCY_INJECTION,
            confidence=0.8,
            title="Use dependency injection",
            description=(
                f"Instead of importing {target} directly, inject it as a "
                f"dependency through constructor or factory pattern."
            ),
            code_changes=[
                CodeChange(
                    file_path=source,
                    change_type="MODIFY",
                    explanation="Add constructor parameter for injected dependency",
                    new_code=(
                        "class MyClass:\n"
                        "    def __init__(self, dependency: ProtocolType):\n"
                        "        self._dependency = dependency"
                    )
                )
            ],
            estimated_effort=EffortEstimate.MEDIUM,
            prerequisites=["Define protocol/interface for dependency"],
            risks=["Requires updating all instantiation sites"]
        ))

        return suggestions

    def _suggest_cycle_fixes(
        self,
        violation: Dict[str, Any],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> List[AutoFixSuggestion]:
        """Generate suggestions for cyclic dependencies."""
        suggestions = []

        cycle_nodes = violation.get('cycle_nodes', violation.get('details', {}).get('cycle', []))

        # Suggestion 1: Extract interface
        suggestions.append(AutoFixSuggestion(
            violation_id=violation.get('rule_id', 'unknown'),
            violation_type='cycle',
            suggestion_type=SuggestionType.EXTRACT_INTERFACE,
            confidence=0.75,
            title="Extract interface to break cycle",
            description=(
                "Create an abstract interface/protocol that both modules can depend on, "
                "breaking the direct circular dependency."
            ),
            code_changes=[
                CodeChange(
                    file_path="interfaces/__init__.py",
                    change_type="ADD",
                    explanation="Create new interface module",
                    new_code=(
                        "from abc import ABC, abstractmethod\n\n"
                        "class IService(ABC):\n"
                        "    @abstractmethod\n"
                        "    def process(self, data):\n"
                        "        pass"
                    )
                )
            ],
            estimated_effort=EffortEstimate.MEDIUM,
            prerequisites=["Identify shared contract between modules"],
            risks=["May increase code complexity"]
        ))

        # Suggestion 2: Event bus
        suggestions.append(AutoFixSuggestion(
            violation_id=violation.get('rule_id', 'unknown'),
            violation_type='cycle',
            suggestion_type=SuggestionType.EVENT_BUS,
            confidence=0.6,
            title="Use event bus for communication",
            description=(
                "Replace direct calls with event-driven communication. "
                "One module publishes events, another subscribes."
            ),
            code_changes=[
                CodeChange(
                    file_path="events/bus.py",
                    change_type="ADD",
                    explanation="Create event bus",
                    new_code=(
                        "class EventBus:\n"
                        "    _subscribers = {}\n\n"
                        "    @classmethod\n"
                        "    def subscribe(cls, event_type, handler):\n"
                        "        cls._subscribers.setdefault(event_type, []).append(handler)\n\n"
                        "    @classmethod\n"
                        "    def publish(cls, event_type, data):\n"
                        "        for handler in cls._subscribers.get(event_type, []):\n"
                        "            handler(data)"
                    )
                )
            ],
            estimated_effort=EffortEstimate.LARGE,
            prerequisites=["Define event types and handlers"],
            risks=["Harder to trace data flow", "Potential performance overhead"]
        ))

        return suggestions

    def _suggest_coupling_fixes(
        self,
        violation: Dict[str, Any],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> List[AutoFixSuggestion]:
        """Generate suggestions for high coupling violations."""
        suggestions = []

        source = violation.get('source_file', violation.get('source', ''))
        coupling_value = violation.get('coupling_value', 0)

        # Suggestion 1: Facade pattern
        suggestions.append(AutoFixSuggestion(
            violation_id=violation.get('rule_id', 'unknown'),
            violation_type='coupling',
            suggestion_type=SuggestionType.FACADE_PATTERN,
            confidence=0.7,
            title="Apply Facade pattern",
            description=(
                f"Create a facade that encapsulates the {coupling_value} dependencies. "
                f"Other modules interact with the facade instead of individual dependencies."
            ),
            code_changes=[
                CodeChange(
                    file_path=f"{source.rsplit('.', 1)[0]}_facade.py",
                    change_type="ADD",
                    explanation="Create facade module",
                    new_code=(
                        "class ServiceFacade:\n"
                        "    '''Facade to reduce coupling to internal services.'''\n\n"
                        "    def __init__(self):\n"
                        "        # Initialize dependencies here\n"
                        "        pass\n\n"
                        "    def do_operation(self, data):\n"
                        "        '''Orchestrate internal services.'''\n"
                        "        pass"
                    )
                )
            ],
            estimated_effort=EffortEstimate.MEDIUM,
            risks=["Facade can become a 'god object' if not designed carefully"]
        ))

        # Suggestion 2: Split module
        suggestions.append(AutoFixSuggestion(
            violation_id=violation.get('rule_id', 'unknown'),
            violation_type='coupling',
            suggestion_type=SuggestionType.SPLIT_MODULE,
            confidence=0.6,
            title="Split into smaller modules",
            description=(
                f"The module has {coupling_value} dependencies. "
                f"Consider splitting it by responsibility into smaller, focused modules."
            ),
            estimated_effort=EffortEstimate.LARGE,
            prerequisites=["Identify cohesive groups of functionality"],
            risks=["May require significant refactoring"]
        ))

        return suggestions

    def _get_component(self, module: str) -> Optional[str]:
        """Determine which component a module belongs to."""
        for component, patterns in self.components.items():
            for pattern in patterns:
                if pattern in module:
                    return component
        return None

    def generate_fix_report(
        self,
        violations: List[Dict[str, Any]],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive fix report for all violations.

        Args:
            violations: List of violation dictionaries
            graph_context: Optional import graph context

        Returns:
            Report dictionary
        """
        all_suggestions = []
        by_type = {}
        by_effort = {}

        for violation in violations:
            suggestions = self.suggest_fixes(violation, graph_context)

            for suggestion in suggestions:
                all_suggestions.append(suggestion)

                # Group by type
                stype = suggestion.suggestion_type.value
                by_type.setdefault(stype, []).append(suggestion)

                # Group by effort
                effort = suggestion.estimated_effort.value
                by_effort.setdefault(effort, []).append(suggestion)

        return {
            'total_violations': len(violations),
            'total_suggestions': len(all_suggestions),
            'suggestions': [s.to_dict() for s in all_suggestions],
            'by_type': {k: len(v) for k, v in by_type.items()},
            'by_effort': {k: len(v) for k, v in by_effort.items()},
            'quick_wins': [
                s.to_dict() for s in all_suggestions
                if s.confidence > 0.7 and s.estimated_effort in [EffortEstimate.TRIVIAL, EffortEstimate.SMALL]
            ]
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Sample violations
    violations = [
        {
            'rule_id': 'layer_001',
            'type': 'layer',
            'source': 'dal/repository.py',
            'target': 'controllers/api.py',
            'message': 'Data access should not import presentation layer'
        },
        {
            'rule_id': 'coupling_001',
            'type': 'coupling',
            'source': 'services/mega_service.py',
            'coupling_value': 15,
            'message': 'High coupling detected'
        }
    ]

    engine = AutoFixEngine()
    report = engine.generate_fix_report(violations)

    print("=== Auto-Fix Report ===\n")
    print(f"Violations: {report['total_violations']}")
    print(f"Suggestions: {report['total_suggestions']}")
    print(f"\nBy type: {report['by_type']}")
    print(f"By effort: {report['by_effort']}")
    print(f"\nQuick wins: {len(report['quick_wins'])}")

    for qw in report['quick_wins']:
        print(f"  - {qw['title']} (confidence: {qw['confidence']:.0%})")
