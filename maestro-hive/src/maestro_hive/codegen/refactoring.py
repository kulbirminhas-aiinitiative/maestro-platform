#!/usr/bin/env python3
"""
Code Refactoring: AI-assisted code refactoring engine.

This module provides automated code refactoring capabilities including
extract method/class, rename symbol, move to module, simplify conditionals,
and apply design patterns.
"""

import ast
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RefactoringType(Enum):
    """Type of refactoring operation."""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    RENAME_SYMBOL = "rename_symbol"
    MOVE_TO_MODULE = "move_to_module"
    INLINE_METHOD = "inline_method"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    EXTRACT_VARIABLE = "extract_variable"
    APPLY_PATTERN = "apply_pattern"


class RefactoringStatus(Enum):
    """Status of a refactoring operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class CodeLocation:
    """Location in source code."""
    file_path: str
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0


@dataclass
class RefactoringPlan:
    """Plan for a refactoring operation."""
    id: str
    type: RefactoringType
    description: str
    source_locations: List[CodeLocation]
    target_location: Optional[CodeLocation] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_impact: str = ""
    risks: List[str] = field(default_factory=list)


@dataclass
class RefactoringResult:
    """Result of a refactoring operation."""
    plan: RefactoringPlan
    status: RefactoringStatus
    changes: List[Dict[str, Any]] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class CodeAnalyzer:
    """Analyzes code structure for refactoring."""

    def __init__(self, source_code: str):
        """
        Initialize analyzer with source code.

        Args:
            source_code: Python source code to analyze
        """
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self._ast: Optional[ast.Module] = None

    @property
    def ast_tree(self) -> ast.Module:
        """Get or parse AST."""
        if self._ast is None:
            self._ast = ast.parse(self.source_code)
        return self._ast

    def find_function(self, name: str) -> Optional[ast.FunctionDef]:
        """Find a function definition by name."""
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    def find_class(self, name: str) -> Optional[ast.ClassDef]:
        """Find a class definition by name."""
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                return node
        return None

    def find_symbol_usages(self, name: str) -> List[CodeLocation]:
        """Find all usages of a symbol."""
        usages = []
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.Name) and node.id == name:
                usages.append(CodeLocation(
                    file_path="",
                    start_line=node.lineno,
                    end_line=node.lineno,
                    start_col=node.col_offset,
                    end_col=node.end_col_offset or node.col_offset + len(name)
                ))
        return usages

    def get_function_variables(self, func_node: ast.FunctionDef) -> Set[str]:
        """Get all variables used in a function."""
        variables = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Name):
                variables.add(node.id)
        return variables

    def get_imports(self) -> List[Tuple[str, Optional[str]]]:
        """Get all imports in the module."""
        imports = []
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, alias.asname))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    full_name = f"{node.module}.{alias.name}" if node.module else alias.name
                    imports.append((full_name, alias.asname))
        return imports

    def find_complex_conditionals(self, threshold: int = 3) -> List[CodeLocation]:
        """Find conditionals with high complexity."""
        complex_conds = []

        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.If):
                # Count boolean operators in condition
                complexity = sum(
                    1 for n in ast.walk(node.test)
                    if isinstance(n, ast.BoolOp)
                )
                if complexity >= threshold:
                    complex_conds.append(CodeLocation(
                        file_path="",
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        start_col=node.col_offset
                    ))

        return complex_conds


class RefactoringEngine:
    """
    AI-assisted code refactoring engine.

    Provides automated refactoring capabilities with safety checks,
    preview mode, and rollback support.
    """

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize the refactoring engine.

        Args:
            backup_dir: Directory for storing backups before refactoring
        """
        self.backup_dir = Path(backup_dir) if backup_dir else None
        self._refactoring_counter = 0

        if self.backup_dir:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a file for potential refactorings.

        Args:
            file_path: Path to source file

        Returns:
            Analysis results with suggestions
        """
        source = file_path.read_text()
        analyzer = CodeAnalyzer(source)

        suggestions = []

        # Find complex conditionals
        complex_conds = analyzer.find_complex_conditionals()
        for loc in complex_conds:
            loc.file_path = str(file_path)
            suggestions.append({
                "type": RefactoringType.SIMPLIFY_CONDITIONAL.value,
                "location": asdict(loc),
                "description": "Complex conditional could be simplified",
                "priority": "medium"
            })

        # Find long functions (>50 lines)
        for node in ast.walk(analyzer.ast_tree):
            if isinstance(node, ast.FunctionDef):
                func_length = (node.end_lineno or node.lineno) - node.lineno
                if func_length > 50:
                    suggestions.append({
                        "type": RefactoringType.EXTRACT_METHOD.value,
                        "location": {
                            "file_path": str(file_path),
                            "start_line": node.lineno,
                            "end_line": node.end_lineno or node.lineno
                        },
                        "description": f"Function '{node.name}' is {func_length} lines, consider extracting methods",
                        "priority": "high"
                    })

        return {
            "file": str(file_path),
            "suggestions": suggestions,
            "metrics": {
                "lines": len(analyzer.lines),
                "functions": sum(1 for n in ast.walk(analyzer.ast_tree) if isinstance(n, ast.FunctionDef)),
                "classes": sum(1 for n in ast.walk(analyzer.ast_tree) if isinstance(n, ast.ClassDef))
            }
        }

    def create_plan(
        self,
        refactoring_type: RefactoringType,
        source_locations: List[CodeLocation],
        **params
    ) -> RefactoringPlan:
        """
        Create a refactoring plan.

        Args:
            refactoring_type: Type of refactoring
            source_locations: Locations of code to refactor
            **params: Additional parameters for the refactoring

        Returns:
            RefactoringPlan with details
        """
        self._refactoring_counter += 1
        plan_id = f"REF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._refactoring_counter:04d}"

        descriptions = {
            RefactoringType.EXTRACT_METHOD: "Extract selected code into a new method",
            RefactoringType.EXTRACT_CLASS: "Extract related methods into a new class",
            RefactoringType.RENAME_SYMBOL: f"Rename symbol to '{params.get('new_name', 'unknown')}'",
            RefactoringType.MOVE_TO_MODULE: f"Move code to module '{params.get('target_module', 'unknown')}'",
            RefactoringType.INLINE_METHOD: "Inline method at call sites",
            RefactoringType.SIMPLIFY_CONDITIONAL: "Simplify complex conditional logic",
            RefactoringType.EXTRACT_VARIABLE: "Extract expression into named variable",
            RefactoringType.APPLY_PATTERN: f"Apply design pattern '{params.get('pattern', 'unknown')}'"
        }

        risks = self._assess_risks(refactoring_type, source_locations, params)

        return RefactoringPlan(
            id=plan_id,
            type=refactoring_type,
            description=descriptions.get(refactoring_type, "Unknown refactoring"),
            source_locations=source_locations,
            parameters=params,
            estimated_impact=self._estimate_impact(source_locations),
            risks=risks
        )

    def preview(self, plan: RefactoringPlan) -> Dict[str, Any]:
        """
        Preview refactoring changes without applying.

        Args:
            plan: RefactoringPlan to preview

        Returns:
            Preview of changes that would be made
        """
        changes = []

        for loc in plan.source_locations:
            file_path = Path(loc.file_path)
            if not file_path.exists():
                continue

            source = file_path.read_text()
            lines = source.splitlines()

            original_lines = lines[loc.start_line - 1:loc.end_line]

            # Generate refactored code based on type
            if plan.type == RefactoringType.RENAME_SYMBOL:
                new_name = plan.parameters.get('new_name', 'renamed')
                old_name = plan.parameters.get('old_name', '')
                refactored_lines = [
                    line.replace(old_name, new_name) for line in original_lines
                ]
            elif plan.type == RefactoringType.EXTRACT_METHOD:
                method_name = plan.parameters.get('method_name', 'extracted_method')
                refactored_lines = [
                    f"    # Extracted to {method_name}()",
                    f"    return self.{method_name}()"
                ]
            else:
                refactored_lines = original_lines  # Placeholder

            changes.append({
                "file": str(file_path),
                "location": asdict(loc),
                "original": original_lines,
                "refactored": refactored_lines,
                "diff_preview": self._generate_diff(original_lines, refactored_lines)
            })

        return {
            "plan_id": plan.id,
            "type": plan.type.value,
            "changes": changes,
            "files_affected": len(set(c["file"] for c in changes))
        }

    def execute(self, plan: RefactoringPlan, dry_run: bool = False) -> RefactoringResult:
        """
        Execute a refactoring plan.

        Args:
            plan: RefactoringPlan to execute
            dry_run: If True, only simulate the refactoring

        Returns:
            RefactoringResult with status and changes
        """
        result = RefactoringResult(
            plan=plan,
            status=RefactoringStatus.IN_PROGRESS
        )

        try:
            # Create backup
            if not dry_run and self.backup_dir:
                backup_path = self._create_backup(plan.source_locations)
                result.backup_path = str(backup_path)

            # Execute based on refactoring type
            if plan.type == RefactoringType.RENAME_SYMBOL:
                changes = self._execute_rename(plan, dry_run)
            elif plan.type == RefactoringType.EXTRACT_METHOD:
                changes = self._execute_extract_method(plan, dry_run)
            elif plan.type == RefactoringType.SIMPLIFY_CONDITIONAL:
                changes = self._execute_simplify_conditional(plan, dry_run)
            else:
                changes = []
                result.error_message = f"Refactoring type {plan.type.value} not yet implemented"
                result.status = RefactoringStatus.FAILED
                return result

            result.changes = changes
            result.affected_files = list(set(c.get("file", "") for c in changes))
            result.status = RefactoringStatus.COMPLETED
            result.metrics = {
                "files_modified": len(result.affected_files),
                "changes_made": len(changes)
            }

            logger.info(f"Refactoring {plan.id} completed successfully")

        except Exception as e:
            result.status = RefactoringStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Refactoring {plan.id} failed: {e}")

        return result

    def rollback(self, result: RefactoringResult) -> bool:
        """
        Rollback a refactoring operation.

        Args:
            result: RefactoringResult to rollback

        Returns:
            True if rollback successful
        """
        if not result.backup_path:
            logger.warning("No backup available for rollback")
            return False

        try:
            backup_path = Path(result.backup_path)
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False

            # Restore files from backup
            for change in result.changes:
                file_path = Path(change["file"])
                backup_file = backup_path / file_path.name

                if backup_file.exists():
                    content = backup_file.read_text()
                    file_path.write_text(content)

            result.status = RefactoringStatus.ROLLED_BACK
            logger.info(f"Refactoring {result.plan.id} rolled back successfully")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _execute_rename(self, plan: RefactoringPlan, dry_run: bool) -> List[Dict[str, Any]]:
        """Execute rename symbol refactoring."""
        changes = []
        old_name = plan.parameters.get('old_name', '')
        new_name = plan.parameters.get('new_name', '')

        if not old_name or not new_name:
            raise ValueError("Rename requires 'old_name' and 'new_name' parameters")

        for loc in plan.source_locations:
            file_path = Path(loc.file_path)
            source = file_path.read_text()

            # Simple regex-based rename (production would use AST)
            pattern = rf'\b{re.escape(old_name)}\b'
            new_source = re.sub(pattern, new_name, source)

            if not dry_run:
                file_path.write_text(new_source)

            changes.append({
                "file": str(file_path),
                "type": "rename",
                "old_name": old_name,
                "new_name": new_name,
                "occurrences": len(re.findall(pattern, source))
            })

        return changes

    def _execute_extract_method(self, plan: RefactoringPlan, dry_run: bool) -> List[Dict[str, Any]]:
        """Execute extract method refactoring."""
        changes = []
        method_name = plan.parameters.get('method_name', 'extracted_method')

        for loc in plan.source_locations:
            file_path = Path(loc.file_path)
            source = file_path.read_text()
            lines = source.splitlines()

            # Extract the selected lines
            extracted_lines = lines[loc.start_line - 1:loc.end_line]
            indent = len(extracted_lines[0]) - len(extracted_lines[0].lstrip())

            # Create new method
            new_method = [
                "",
                " " * indent + f"def {method_name}(self):",
                " " * indent + '    """Extracted method."""'
            ]
            new_method.extend([" " * 4 + line for line in extracted_lines])

            # Replace original with method call
            lines[loc.start_line - 1:loc.end_line] = [
                " " * indent + f"self.{method_name}()"
            ]

            # Insert new method at end of class
            lines.extend(new_method)

            if not dry_run:
                file_path.write_text("\n".join(lines))

            changes.append({
                "file": str(file_path),
                "type": "extract_method",
                "method_name": method_name,
                "lines_extracted": len(extracted_lines)
            })

        return changes

    def _execute_simplify_conditional(self, plan: RefactoringPlan, dry_run: bool) -> List[Dict[str, Any]]:
        """Execute simplify conditional refactoring."""
        changes = []

        for loc in plan.source_locations:
            file_path = Path(loc.file_path)
            source = file_path.read_text()
            lines = source.splitlines()

            # Get the conditional lines
            cond_lines = lines[loc.start_line - 1:loc.end_line]

            # Simple simplification: extract to explaining variable
            changes.append({
                "file": str(file_path),
                "type": "simplify_conditional",
                "suggestion": "Consider extracting complex condition to a well-named variable",
                "original_lines": loc.end_line - loc.start_line + 1
            })

        return changes

    def _assess_risks(
        self,
        refactoring_type: RefactoringType,
        locations: List[CodeLocation],
        params: Dict[str, Any]
    ) -> List[str]:
        """Assess risks of a refactoring operation."""
        risks = []

        if refactoring_type == RefactoringType.RENAME_SYMBOL:
            risks.append("May miss string references to symbol")
            risks.append("Could affect external callers if public API")

        if refactoring_type == RefactoringType.EXTRACT_METHOD:
            risks.append("May need to pass additional parameters")
            risks.append("Could change method ordering in class")

        if len(locations) > 5:
            risks.append("Large number of affected locations increases risk")

        return risks

    def _estimate_impact(self, locations: List[CodeLocation]) -> str:
        """Estimate impact of refactoring."""
        total_lines = sum(loc.end_line - loc.start_line + 1 for loc in locations)

        if total_lines < 10:
            return "low"
        elif total_lines < 50:
            return "medium"
        else:
            return "high"

    def _create_backup(self, locations: List[CodeLocation]) -> Path:
        """Create backup of files to be modified."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        for loc in locations:
            file_path = Path(loc.file_path)
            if file_path.exists():
                backup_file = backup_path / file_path.name
                backup_file.write_text(file_path.read_text())

        return backup_path

    def _generate_diff(self, original: List[str], refactored: List[str]) -> str:
        """Generate a simple diff preview."""
        diff_lines = []
        for line in original:
            diff_lines.append(f"- {line}")
        for line in refactored:
            diff_lines.append(f"+ {line}")
        return "\n".join(diff_lines)


# Convenience function
def create_refactoring_engine(**kwargs) -> RefactoringEngine:
    """Create a new RefactoringEngine instance."""
    return RefactoringEngine(**kwargs)
