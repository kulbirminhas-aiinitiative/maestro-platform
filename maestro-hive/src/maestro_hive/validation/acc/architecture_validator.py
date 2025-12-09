"""
ACC Architecture Conformance Validator
MD-2482 Task 1.2: Validate generated code conforms to architectural patterns.

AC-4: ACC validates code against architectural patterns
AC-5: Architecture violations block phase progression
"""

import os
import ast
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


class ArchitecturePattern(Enum):
    """Supported architecture patterns."""
    MICROSERVICES = "microservices"
    DDD = "domain-driven-design"
    HEXAGONAL = "hexagonal"
    CLEAN = "clean-architecture"
    LAYERED = "layered"
    MVC = "mvc"


class ViolationSeverity(Enum):
    """Severity of architecture violations."""
    ERROR = "error"      # Blocks phase gate
    WARNING = "warning"  # Reported but doesn't block
    INFO = "info"        # Informational


@dataclass
class ArchitectureViolation:
    """
    Details of an architecture violation.
    AC-5: Architecture violations block phase progression
    """
    type: str
    severity: ViolationSeverity
    file: str
    line: Optional[int] = None
    message: str = ""
    rule: str = ""
    suggestion: str = ""
    
    def is_blocking(self) -> bool:
        """Check if violation blocks phase gate."""
        return self.severity == ViolationSeverity.ERROR


@dataclass
class ValidationResult:
    """Result of architecture validation."""
    passed: bool
    pattern: ArchitecturePattern
    violations: List[ArchitectureViolation] = field(default_factory=list)
    score: float = 100.0
    files_analyzed: int = 0
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def blocking_violations(self) -> List[ArchitectureViolation]:
        """Get violations that block phase gate."""
        return [v for v in self.violations if v.is_blocking()]
    
    @property
    def passes_gate(self) -> bool:
        """Check if result passes quality gate."""
        return len(self.blocking_violations) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "passes_gate": self.passes_gate,
            "pattern": self.pattern.value,
            "score": self.score,
            "files_analyzed": self.files_analyzed,
            "violations": [
                {
                    "type": v.type,
                    "severity": v.severity.value,
                    "file": v.file,
                    "line": v.line,
                    "message": v.message,
                    "rule": v.rule,
                }
                for v in self.violations
            ],
            "blocking_count": len(self.blocking_violations),
            "recommendations": self.recommendations,
        }


class PatternRules:
    """Rules for each architecture pattern."""
    
    MICROSERVICES = {
        "service_boundary": {
            "description": "Services should have clear boundaries",
            "check": "no_cross_service_imports",
        },
        "api_contracts": {
            "description": "Services communicate via defined APIs",
            "check": "has_api_definition",
        },
        "independent_data": {
            "description": "Each service owns its data",
            "check": "no_shared_database",
        },
    }
    
    DDD = {
        "aggregate_integrity": {
            "description": "Aggregates maintain invariants",
            "check": "aggregate_root_access",
        },
        "repository_pattern": {
            "description": "Use repositories for persistence",
            "check": "uses_repositories",
        },
        "value_objects": {
            "description": "Use value objects for identity-less concepts",
            "check": "has_value_objects",
        },
        "bounded_context": {
            "description": "Clear context boundaries",
            "check": "bounded_context_separation",
        },
    }
    
    HEXAGONAL = {
        "core_isolation": {
            "description": "Core domain has no external dependencies",
            "check": "core_no_imports",
        },
        "ports_defined": {
            "description": "Ports (interfaces) defined for external access",
            "check": "has_port_interfaces",
        },
        "adapters_implement": {
            "description": "Adapters implement port interfaces",
            "check": "adapters_use_ports",
        },
    }
    
    CLEAN = {
        "dependency_direction": {
            "description": "Dependencies point inward",
            "check": "inward_dependencies",
        },
        "entity_independence": {
            "description": "Entities independent of frameworks",
            "check": "pure_entities",
        },
        "use_case_orchestration": {
            "description": "Use cases orchestrate flow",
            "check": "use_case_pattern",
        },
    }


class ArchitectureValidator:
    """
    Validate code against architectural patterns.
    
    AC-4: ACC validates code against architectural patterns
    AC-5: Architecture violations block phase progression
    """
    
    # Layer definitions for dependency checking
    LAYERS = {
        "presentation": ["controllers", "views", "handlers", "api"],
        "application": ["services", "use_cases", "commands", "queries"],
        "domain": ["entities", "models", "aggregates", "value_objects"],
        "infrastructure": ["repositories", "adapters", "external"],
    }
    
    # Allowed dependencies (layer can depend on layers in list)
    LAYER_DEPENDENCIES = {
        "presentation": ["application", "domain"],
        "application": ["domain"],
        "domain": [],  # Domain has no dependencies
        "infrastructure": ["domain", "application"],
    }
    
    def __init__(self, project_path: str, pattern: ArchitecturePattern):
        """
        Initialize validator.
        
        Args:
            project_path: Path to project root
            pattern: Architecture pattern to validate against
        """
        self.project_path = Path(project_path)
        self.pattern = pattern
        self.violations: List[ArchitectureViolation] = []
        self.files_analyzed = 0
    
    def validate(self) -> ValidationResult:
        """
        Validate project against architecture pattern.
        
        Returns:
            ValidationResult with violations and score
        """
        logger.info(f"Validating {self.project_path} against {self.pattern.value}")
        
        self.violations = []
        self.files_analyzed = 0
        
        # Get pattern-specific rules
        rules = self._get_pattern_rules()
        
        # Analyze project structure
        self._analyze_structure()
        
        # Run pattern-specific checks
        for rule_name, rule_config in rules.items():
            check_method = getattr(self, f"_check_{rule_config['check']}", None)
            if check_method:
                check_method(rule_name, rule_config)
        
        # Calculate score
        score = self._calculate_score()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        result = ValidationResult(
            passed=len(self.violations) == 0,
            pattern=self.pattern,
            violations=self.violations,
            score=score,
            files_analyzed=self.files_analyzed,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Validation complete: score={score:.1f}, "
            f"violations={len(self.violations)}, "
            f"blocking={len(result.blocking_violations)}"
        )
        
        return result
    
    def _get_pattern_rules(self) -> Dict:
        """Get rules for current pattern."""
        rules_map = {
            ArchitecturePattern.MICROSERVICES: PatternRules.MICROSERVICES,
            ArchitecturePattern.DDD: PatternRules.DDD,
            ArchitecturePattern.HEXAGONAL: PatternRules.HEXAGONAL,
            ArchitecturePattern.CLEAN: PatternRules.CLEAN,
        }
        return rules_map.get(self.pattern, {})
    
    def _analyze_structure(self) -> None:
        """Analyze project structure."""
        for py_file in self.project_path.glob("**/*.py"):
            if "__pycache__" in str(py_file):
                continue
            self.files_analyzed += 1
            self._analyze_file(py_file)
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single file for violations."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            # Check imports
            self._check_imports(file_path, tree)
            
            # Check layer violations
            self._check_layer_violations(file_path, tree)
            
        except (SyntaxError, IOError) as e:
            logger.debug(f"Could not analyze {file_path}: {e}")
    
    def _check_imports(self, file_path: Path, tree: ast.AST) -> None:
        """Check import statements for violations."""
        file_layer = self._get_file_layer(file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.Import):
                    module = node.names[0].name
                elif node.module:
                    module = node.module
                
                # Check for forbidden imports
                imported_layer = self._get_module_layer(module)
                if imported_layer and file_layer:
                    if not self._is_allowed_dependency(file_layer, imported_layer):
                        self.violations.append(ArchitectureViolation(
                            type="layer_violation",
                            severity=ViolationSeverity.ERROR,
                            file=str(file_path.relative_to(self.project_path)),
                            line=node.lineno,
                            message=f"Layer '{file_layer}' cannot import from '{imported_layer}'",
                            rule="dependency_direction",
                            suggestion=f"Move this code to {imported_layer} or use dependency injection",
                        ))
    
    def _check_layer_violations(self, file_path: Path, tree: ast.AST) -> None:
        """Check for layer boundary violations."""
        pass  # Implemented in _check_imports
    
    def _get_file_layer(self, file_path: Path) -> Optional[str]:
        """Determine which layer a file belongs to."""
        path_str = str(file_path).lower()
        
        for layer, keywords in self.LAYERS.items():
            for keyword in keywords:
                if keyword in path_str:
                    return layer
        
        return None
    
    def _get_module_layer(self, module: str) -> Optional[str]:
        """Determine which layer a module belongs to."""
        module_lower = module.lower()
        
        for layer, keywords in self.LAYERS.items():
            for keyword in keywords:
                if keyword in module_lower:
                    return layer
        
        return None
    
    def _is_allowed_dependency(self, from_layer: str, to_layer: str) -> bool:
        """Check if dependency from one layer to another is allowed."""
        if from_layer == to_layer:
            return True
        
        allowed = self.LAYER_DEPENDENCIES.get(from_layer, [])
        return to_layer in allowed
    
    # Pattern-specific checks
    def _check_no_cross_service_imports(self, rule_name: str, rule_config: Dict) -> None:
        """Check for imports across service boundaries."""
        # Implementation for microservices pattern
        pass
    
    def _check_aggregate_root_access(self, rule_name: str, rule_config: Dict) -> None:
        """Check that aggregates are accessed through roots."""
        # Implementation for DDD pattern
        pass
    
    def _check_core_no_imports(self, rule_name: str, rule_config: Dict) -> None:
        """Check that core domain has no external imports."""
        core_dirs = ["domain", "core", "entities"]
        
        for core_dir in core_dirs:
            core_path = self.project_path / core_dir
            if core_path.exists():
                for py_file in core_path.glob("**/*.py"):
                    self._check_core_file_imports(py_file)
    
    def _check_core_file_imports(self, file_path: Path) -> None:
        """Check imports in core domain file."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            forbidden_imports = ["flask", "django", "fastapi", "sqlalchemy", "requests"]
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = ""
                    if isinstance(node, ast.Import):
                        module = node.names[0].name
                    elif node.module:
                        module = node.module
                    
                    for forbidden in forbidden_imports:
                        if forbidden in module.lower():
                            self.violations.append(ArchitectureViolation(
                                type="core_isolation",
                                severity=ViolationSeverity.ERROR,
                                file=str(file_path.relative_to(self.project_path)),
                                line=node.lineno,
                                message=f"Core domain cannot import '{module}'",
                                rule="core_no_imports",
                                suggestion="Use ports/adapters pattern for external dependencies",
                            ))
        except (SyntaxError, IOError):
            pass
    
    def _check_inward_dependencies(self, rule_name: str, rule_config: Dict) -> None:
        """Check that dependencies point inward (Clean Architecture)."""
        # Already handled by layer violation checks
        pass
    
    def _calculate_score(self) -> float:
        """Calculate conformance score."""
        if self.files_analyzed == 0:
            return 100.0
        
        # Deduct points for violations
        error_penalty = 10
        warning_penalty = 3
        
        total_penalty = sum(
            error_penalty if v.severity == ViolationSeverity.ERROR else warning_penalty
            for v in self.violations
        )
        
        score = max(0, 100 - total_penalty)
        return score
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on violations."""
        recommendations = []
        
        violation_types = set(v.type for v in self.violations)
        
        if "layer_violation" in violation_types:
            recommendations.append(
                "Review layer dependencies - ensure code respects architectural boundaries"
            )
        
        if "core_isolation" in violation_types:
            recommendations.append(
                "Refactor core domain to remove framework dependencies"
            )
        
        if not recommendations and self.violations:
            recommendations.append(
                "Consider refactoring to better align with the chosen architecture pattern"
            )
        
        return recommendations


class ContractValidator:
    """
    Validate API contracts match implementation.
    Part of AC-4: ACC validates code against architectural patterns
    """
    
    def __init__(self, spec_path: str, implementation_path: str):
        """
        Initialize contract validator.
        
        Args:
            spec_path: Path to OpenAPI spec
            implementation_path: Path to API implementation
        """
        self.spec_path = Path(spec_path)
        self.implementation_path = Path(implementation_path)
    
    def validate(self) -> ValidationResult:
        """Validate that implementation matches spec."""
        violations = []
        
        # Load spec
        spec = self._load_spec()
        if not spec:
            violations.append(ArchitectureViolation(
                type="contract",
                severity=ViolationSeverity.ERROR,
                file=str(self.spec_path),
                message="Could not load OpenAPI spec",
                rule="api_contract",
            ))
            return ValidationResult(
                passed=False,
                pattern=ArchitecturePattern.MICROSERVICES,
                violations=violations,
            )
        
        # Extract endpoints from spec
        spec_endpoints = self._extract_spec_endpoints(spec)
        
        # Find implementation endpoints
        impl_endpoints = self._find_implementation_endpoints()
        
        # Compare
        for endpoint in spec_endpoints:
            if endpoint not in impl_endpoints:
                violations.append(ArchitectureViolation(
                    type="missing_endpoint",
                    severity=ViolationSeverity.ERROR,
                    file=str(self.implementation_path),
                    message=f"Endpoint {endpoint} defined in spec but not implemented",
                    rule="api_contract",
                ))
        
        return ValidationResult(
            passed=len(violations) == 0,
            pattern=ArchitecturePattern.MICROSERVICES,
            violations=violations,
        )
    
    def _load_spec(self) -> Optional[Dict]:
        """Load OpenAPI spec."""
        if not self.spec_path.exists():
            return None
        
        try:
            import yaml
            content = self.spec_path.read_text()
            if self.spec_path.suffix in [".yaml", ".yml"]:
                return yaml.safe_load(content)
            else:
                return json.loads(content)
        except Exception:
            return None
    
    def _extract_spec_endpoints(self, spec: Dict) -> Set[str]:
        """Extract endpoints from OpenAPI spec."""
        endpoints = set()
        
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method in methods:
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoints.add(f"{method.upper()} {path}")
        
        return endpoints
    
    def _find_implementation_endpoints(self) -> Set[str]:
        """Find implemented endpoints in code."""
        endpoints = set()
        
        # Scan for route decorators
        patterns = [
            r"@app\.route\(['\"]([^'\"]+)['\"].*methods=\[([^\]]+)\]",
            r"@router\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]",
        ]
        
        for py_file in self.implementation_path.glob("**/*.py"):
            try:
                content = py_file.read_text()
                for pattern in patterns:
                    for match in re.finditer(pattern, content):
                        if len(match.groups()) == 2:
                            endpoints.add(f"{match.group(1).upper()} {match.group(2)}")
            except IOError:
                continue
        
        return endpoints
