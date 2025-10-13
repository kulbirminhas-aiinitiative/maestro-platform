"""
ACC Import Graph Builder

Builds import dependency graphs from Python source code using AST analysis.
Used for architectural conformance checking and dependency validation.
"""

import ast
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import networkx as nx


@dataclass
class ModuleInfo:
    """Information about a Python module"""
    module_name: str
    file_path: Path
    imports: List[str] = field(default_factory=list)
    from_imports: List[str] = field(default_factory=list)
    size_lines: int = 0
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)

    def all_dependencies(self) -> List[str]:
        """Get all module dependencies"""
        return self.imports + self.from_imports


class ImportGraph:
    """
    Dependency graph of Python modules based on import statements.

    Uses NetworkX DiGraph for efficient graph operations.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.modules: Dict[str, ModuleInfo] = {}

    def add_module(self, module_info: ModuleInfo):
        """
        Add a module to the graph.

        Args:
            module_info: ModuleInfo object
        """
        self.modules[module_info.module_name] = module_info
        self.graph.add_node(module_info.module_name, info=module_info)

    def add_dependency(self, from_module: str, to_module: str):
        """
        Add a dependency edge between two modules.

        Args:
            from_module: Source module name
            to_module: Target module name
        """
        if from_module not in self.graph:
            self.graph.add_node(from_module)
        if to_module not in self.graph:
            self.graph.add_node(to_module)

        self.graph.add_edge(from_module, to_module)

    def get_dependencies(self, module_name: str) -> List[str]:
        """
        Get all dependencies (successors) of a module.

        Args:
            module_name: Module name

        Returns:
            List of module names this module depends on
        """
        if module_name not in self.graph:
            return []
        return list(self.graph.successors(module_name))

    def get_dependents(self, module_name: str) -> List[str]:
        """
        Get all dependents (predecessors) of a module.

        Args:
            module_name: Module name

        Returns:
            List of module names that depend on this module
        """
        if module_name not in self.graph:
            return []
        return list(self.graph.predecessors(module_name))

    def has_cycle(self) -> bool:
        """
        Check if the graph contains cycles.

        Returns:
            True if cycles exist, False otherwise
        """
        try:
            nx.find_cycle(self.graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def find_cycles(self) -> List[List[str]]:
        """
        Find all cycles in the graph.

        Returns:
            List of cycles, where each cycle is a list of module names
        """
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except:
            return []

    def calculate_coupling(self, module_name: str) -> Tuple[int, int, float]:
        """
        Calculate coupling metrics for a module.

        Returns:
            Tuple of (afferent_coupling, efferent_coupling, instability)
            - Afferent coupling (Ca): Number of modules that depend on this module
            - Efferent coupling (Ce): Number of modules this module depends on
            - Instability (I): Ce / (Ca + Ce), ranges from 0 (stable) to 1 (unstable)
        """
        if module_name not in self.graph:
            return (0, 0, 0.0)

        ca = len(self.get_dependents(module_name))  # Afferent coupling
        ce = len(self.get_dependencies(module_name))  # Efferent coupling

        # Calculate instability
        total = ca + ce
        instability = ce / total if total > 0 else 0.0

        return (ca, ce, instability)

    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """
        Get module information.

        Args:
            module_name: Module name

        Returns:
            ModuleInfo if found, None otherwise
        """
        return self.modules.get(module_name)

    def to_dict(self) -> Dict:
        """
        Export graph to dictionary.

        Returns:
            Dictionary representation of the graph
        """
        return {
            'nodes': list(self.graph.nodes()),
            'edges': list(self.graph.edges()),
            'modules': {
                name: {
                    'file_path': str(info.file_path),
                    'imports': info.imports,
                    'from_imports': info.from_imports,
                    'size_lines': info.size_lines,
                    'classes': info.classes,
                    'functions': info.functions
                }
                for name, info in self.modules.items()
            }
        }


class ImportGraphBuilder:
    """
    Builds import graphs from Python source code.

    Uses AST parsing to extract import statements and module dependencies.
    """

    def __init__(self, project_path: str, project_name: Optional[str] = None):
        """
        Initialize import graph builder.

        Args:
            project_path: Root path of the project
            project_name: Project name (used for module resolution)
        """
        self.project_path = Path(project_path)
        self.project_name = project_name or self.project_path.name
        self.exclusions: List[str] = [
            '__pycache__',
            '.venv',
            'venv',
            '.git',
            'node_modules',
            'tests',
            'test'
        ]

    def build_graph(self) -> ImportGraph:
        """
        Build import graph from Python files in the project.

        Returns:
            ImportGraph object
        """
        graph = ImportGraph()

        # Find all Python files
        python_files = self._find_python_files()

        # Parse each file
        for py_file in python_files:
            try:
                module_info = self._parse_file(py_file)
                if module_info:
                    graph.add_module(module_info)
            except Exception as e:
                print(f"Warning: Failed to parse {py_file}: {e}")

        # Build dependency edges
        for module_name, module_info in graph.modules.items():
            for dep in module_info.all_dependencies():
                # Resolve dependency to module name
                resolved_dep = self._resolve_import(dep)
                if resolved_dep and resolved_dep in graph.modules:
                    graph.add_dependency(module_name, resolved_dep)

        return graph

    def _find_python_files(self) -> List[Path]:
        """
        Find all Python files in the project.

        Returns:
            List of Path objects for Python files
        """
        python_files = []

        for py_file in self.project_path.rglob("*.py"):
            # Skip excluded directories
            if any(excl in str(py_file) for excl in self.exclusions):
                continue

            python_files.append(py_file)

        return sorted(python_files)

    def _parse_file(self, file_path: Path) -> Optional[ModuleInfo]:
        """
        Parse a Python file and extract module information.

        Args:
            file_path: Path to Python file

        Returns:
            ModuleInfo object or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            # Parse AST
            tree = ast.parse(source, filename=str(file_path))

            # Get module name
            module_name = self._get_module_name(file_path)

            # Extract imports
            imports, from_imports = self._extract_imports(tree)

            # Extract classes and functions
            classes = self._extract_classes(tree)
            functions = self._extract_functions(tree)

            # Count lines
            size_lines = len(source.splitlines())

            return ModuleInfo(
                module_name=module_name,
                file_path=file_path,
                imports=imports,
                from_imports=from_imports,
                size_lines=size_lines,
                classes=classes,
                functions=functions
            )

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _get_module_name(self, file_path: Path) -> str:
        """
        Convert file path to module name.

        Args:
            file_path: Path to Python file

        Returns:
            Module name (e.g., "backend.services.user_service")
        """
        # Get relative path from project root
        try:
            rel_path = file_path.relative_to(self.project_path)
        except ValueError:
            rel_path = file_path

        # Convert path to module name
        parts = list(rel_path.parts[:-1])  # Exclude filename
        if rel_path.stem != '__init__':
            parts.append(rel_path.stem)

        module_name = '.'.join(parts)
        return module_name

    def _extract_imports(self, tree: ast.AST) -> Tuple[List[str], List[str]]:
        """
        Extract import statements from AST.

        Args:
            tree: AST tree

        Returns:
            Tuple of (imports, from_imports)
        """
        imports = []
        from_imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    from_imports.append(node.module)

        return imports, from_imports

    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """
        Extract class names from AST.

        Args:
            tree: AST tree

        Returns:
            List of class names
        """
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)

        return classes

    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """
        Extract function names from AST.

        Args:
            tree: AST tree

        Returns:
            List of function names
        """
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)

        return functions

    def _resolve_import(self, import_name: str) -> Optional[str]:
        """
        Resolve import to module name.

        Args:
            import_name: Import statement module name

        Returns:
            Resolved module name or None if external
        """
        # Check if it's a relative import
        if import_name.startswith('.'):
            return import_name

        # Check if it's a project module
        parts = import_name.split('.')
        if len(parts) > 0:
            # Check if first part matches any top-level directory
            first_part = parts[0]
            candidate_path = self.project_path / first_part
            if candidate_path.exists() and candidate_path.is_dir():
                return import_name

        # External module (not in project)
        return None


# Example usage
if __name__ == "__main__":
    # Build import graph for current project
    builder = ImportGraphBuilder(project_path="/home/ec2-user/projects/maestro-platform/maestro-hive")
    graph = builder.build_graph()

    print(f"Built import graph with {len(graph.modules)} modules")
    print(f"Total dependencies: {len(graph.graph.edges())}")

    # Check for cycles
    if graph.has_cycle():
        cycles = graph.find_cycles()
        print(f"\nFound {len(cycles)} cyclic dependencies:")
        for cycle in cycles[:5]:  # Show first 5
            print(f"  {' -> '.join(cycle)}")
    else:
        print("\nNo cyclic dependencies found")

    # Calculate coupling for a few modules
    print("\nCoupling metrics for sample modules:")
    for module_name in list(graph.modules.keys())[:5]:
        ca, ce, instability = graph.calculate_coupling(module_name)
        print(f"  {module_name}: Ca={ca}, Ce={ce}, I={instability:.2f}")
