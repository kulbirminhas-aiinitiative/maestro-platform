"""
Type Hint Generator.

EPIC: MD-2496
AC-3: Type hints included where appropriate
"""

import ast
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TypeHintGenerator:
    """
    Generate type hints for Python code.

    AC-3: Ensures type hints are included where appropriate.
    """

    # Common type mappings
    TYPE_MAPPINGS = {
        "str": "str",
        "string": "str",
        "int": "int",
        "integer": "int",
        "float": "float",
        "double": "float",
        "bool": "bool",
        "boolean": "bool",
        "list": "List[Any]",
        "dict": "Dict[str, Any]",
        "dictionary": "Dict[str, Any]",
        "none": "None",
        "null": "None",
        "any": "Any",
    }

    # Default return types for common patterns
    RETURN_PATTERNS = {
        r"^is_": "bool",
        r"^has_": "bool",
        r"^can_": "bool",
        r"^should_": "bool",
        r"^get_count": "int",
        r"^count_": "int",
        r"^len_": "int",
        r"^find_": "Optional[Any]",
        r"^get_": "Any",
        r"^list_": "List[Any]",
        r"^create_": "Any",
        r"^delete_": "bool",
        r"^update_": "Any",
        r"^validate": "bool",
        r"^to_dict": "Dict[str, Any]",
        r"^to_json": "str",
        r"^from_dict": "Any",  # Usually cls type
        r"^from_json": "Any",  # Usually cls type
    }

    def __init__(self):
        self._imports_needed: Set[str] = set()

    def add_type_hints(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add type hints to Python code.

        Args:
            code: Source code without type hints
            context: Optional context for type inference

        Returns:
            Code with type annotations added
        """
        context = context or {}
        self._imports_needed = set()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            logger.warning("Could not parse code for type hint addition")
            return code

        # Analyze and add hints
        modified_code = self._process_code(code, tree, context)

        # Add imports if needed
        if self._imports_needed:
            modified_code = self._add_imports(modified_code)

        return modified_code

    def _process_code(
        self,
        code: str,
        tree: ast.AST,
        context: Dict[str, Any],
    ) -> str:
        """Process code and add type hints."""
        lines = code.split("\n")
        modifications: List[Tuple[int, str, str]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mods = self._hint_function(node, lines, context)
                modifications.extend(mods)

        # Apply modifications in reverse order to preserve line numbers
        for line_num, old_text, new_text in sorted(modifications, reverse=True):
            if 0 <= line_num < len(lines):
                lines[line_num] = lines[line_num].replace(old_text, new_text)

        return "\n".join(lines)

    def _hint_function(
        self,
        node: ast.AST,
        lines: List[str],
        context: Dict[str, Any],
    ) -> List[Tuple[int, str, str]]:
        """Add type hints to a function definition."""
        modifications = []

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return modifications

        # Skip if already has return annotation
        if node.returns is not None:
            return modifications

        # Get the function line
        line_idx = node.lineno - 1
        if line_idx >= len(lines):
            return modifications

        line = lines[line_idx]

        # Infer return type
        return_type = self._infer_return_type(node, context)
        if return_type:
            self._imports_needed.update(self._get_required_imports(return_type))

            # Find the closing parenthesis and colon
            match = re.search(r"\)\s*:", line)
            if match:
                old_text = match.group(0)
                new_text = f") -> {return_type}:"
                modifications.append((line_idx, old_text, new_text))

        # Add parameter type hints
        param_mods = self._hint_parameters(node, line_idx, lines, context)
        modifications.extend(param_mods)

        return modifications

    def _hint_parameters(
        self,
        node: ast.AST,
        line_idx: int,
        lines: List[str],
        context: Dict[str, Any],
    ) -> List[Tuple[int, str, str]]:
        """Add type hints to function parameters."""
        modifications = []

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return modifications

        for arg in node.args.args:
            # Skip self and cls
            if arg.arg in ("self", "cls"):
                continue

            # Skip if already has annotation
            if arg.annotation is not None:
                continue

            # Infer type from name or context
            param_type = self._infer_param_type(arg.arg, context)
            if param_type:
                self._imports_needed.update(self._get_required_imports(param_type))

                # Find parameter in function signature
                line = lines[line_idx]
                # Simple pattern: param_name without type
                pattern = rf"\b{arg.arg}\b(?!\s*:)"
                match = re.search(pattern, line)
                if match:
                    old_text = arg.arg
                    new_text = f"{arg.arg}: {param_type}"
                    modifications.append((line_idx, old_text, new_text))

        return modifications

    def _infer_return_type(
        self,
        node: ast.AST,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Infer return type from function name and body."""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        func_name = node.name

        # Check context first
        if func_name in context.get("return_types", {}):
            return context["return_types"][func_name]

        # Check patterns
        for pattern, return_type in self.RETURN_PATTERNS.items():
            if re.match(pattern, func_name):
                return return_type

        # Analyze body for return statements
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if child.value is None:
                    return "None"
                return self._infer_type_from_expr(child.value)

        return None

    def _infer_param_type(
        self,
        param_name: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Infer parameter type from name."""
        # Check context
        if param_name in context.get("param_types", {}):
            return context["param_types"][param_name]

        # Common name patterns
        name_lower = param_name.lower()

        if name_lower in ("id", "user_id", "item_id", "entity_id"):
            return "str"
        elif name_lower in ("name", "title", "description", "path", "url"):
            return "str"
        elif name_lower in ("count", "limit", "offset", "page", "size"):
            return "int"
        elif name_lower in ("enabled", "active", "is_valid", "force"):
            return "bool"
        elif name_lower in ("data", "payload", "body", "params"):
            return "Dict[str, Any]"
        elif name_lower in ("items", "results", "records"):
            return "List[Any]"
        elif name_lower.endswith("_at") or name_lower.endswith("_time"):
            return "Optional[datetime]"
        elif name_lower.endswith("_config") or name_lower.endswith("_options"):
            return "Optional[Dict[str, Any]]"

        return None

    def _infer_type_from_expr(self, expr: ast.AST) -> Optional[str]:
        """Infer type from an expression."""
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, str):
                return "str"
            elif isinstance(expr.value, int):
                return "int"
            elif isinstance(expr.value, float):
                return "float"
            elif isinstance(expr.value, bool):
                return "bool"
            elif expr.value is None:
                return "None"
        elif isinstance(expr, ast.List):
            return "List[Any]"
        elif isinstance(expr, ast.Dict):
            return "Dict[str, Any]"
        elif isinstance(expr, ast.Set):
            return "Set[Any]"
        elif isinstance(expr, ast.Tuple):
            return "Tuple[Any, ...]"

        return "Any"

    def _get_required_imports(self, type_hint: str) -> Set[str]:
        """Get required imports for a type hint."""
        imports = set()

        if "List" in type_hint or "Dict" in type_hint or "Set" in type_hint:
            imports.add("from typing import List, Dict, Set, Any")
        if "Optional" in type_hint:
            imports.add("from typing import Optional")
        if "Tuple" in type_hint:
            imports.add("from typing import Tuple")
        if "Any" in type_hint:
            imports.add("from typing import Any")
        if "datetime" in type_hint:
            imports.add("from datetime import datetime")

        return imports

    def _add_imports(self, code: str) -> str:
        """Add required imports to code."""
        lines = code.split("\n")

        # Find insertion point (after docstring, before other code)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Skip docstring
                if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                    insert_idx = i + 1
                else:
                    # Multi-line docstring
                    for j in range(i + 1, len(lines)):
                        if '"""' in lines[j] or "'''" in lines[j]:
                            insert_idx = j + 1
                            break
                break
            elif not stripped or stripped.startswith("#"):
                continue
            elif stripped.startswith("import ") or stripped.startswith("from "):
                insert_idx = i + 1
            else:
                break

        # Consolidate imports
        typing_imports = set()
        other_imports = set()

        for imp in self._imports_needed:
            if "typing" in imp:
                # Extract types from typing import
                match = re.search(r"from typing import (.+)", imp)
                if match:
                    types = [t.strip() for t in match.group(1).split(",")]
                    typing_imports.update(types)
            else:
                other_imports.add(imp)

        # Build import lines
        import_lines = []
        if typing_imports:
            import_lines.append(f"from typing import {', '.join(sorted(typing_imports))}")
        import_lines.extend(sorted(other_imports))

        if import_lines:
            lines.insert(insert_idx, "\n".join(import_lines) + "\n")

        return "\n".join(lines)

    def calculate_type_coverage(self, code: str) -> float:
        """
        Calculate percentage of typed functions.

        Args:
            code: Source code to analyze

        Returns:
            Percentage of functions with type hints (0.0-1.0)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 0.0

        total_functions = 0
        typed_functions = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1

                # Check if has return type and all params typed
                has_return = node.returns is not None
                params_typed = all(
                    arg.annotation is not None
                    for arg in node.args.args
                    if arg.arg not in ("self", "cls")
                )

                if has_return and params_typed:
                    typed_functions += 1

        if total_functions == 0:
            return 1.0  # No functions = 100% coverage

        return typed_functions / total_functions
