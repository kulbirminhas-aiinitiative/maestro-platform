"""
ACC Import Graph Builder

Builds import dependency graphs from Python source code using AST analysis.
Used for architectural conformance checking and dependency validation.

Enhanced Features (MD-2081):
- Parallel file scanning with concurrent.futures
- Dynamic import detection (importlib.import_module)
- __all__ exports handling for star imports
- Incremental graph building with file hash caching
- Namespace package support
- Performance target: <30 seconds for 1000+ files
"""

import ast
import os
import hashlib
import json
import time
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """Information about a Python module"""
    module_name: str
    file_path: Path
    imports: List[str] = field(default_factory=list)
    from_imports: List[str] = field(default_factory=list)
    dynamic_imports: List[str] = field(default_factory=list)  # MD-2081: importlib imports
    star_imports: List[str] = field(default_factory=list)  # MD-2081: from X import *
    exports: List[str] = field(default_factory=list)  # MD-2081: __all__ exports
    size_lines: int = 0
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    file_hash: str = ""  # MD-2081: For incremental builds
    is_namespace_package: bool = False  # MD-2081: PEP 420 namespace packages

    def all_dependencies(self) -> List[str]:
        """Get all module dependencies including dynamic imports"""
        return self.imports + self.from_imports + self.dynamic_imports + self.star_imports


@dataclass
class BuildMetrics:
    """Metrics from graph building process (MD-2081)"""
    total_files: int = 0
    files_parsed: int = 0
    files_cached: int = 0
    files_failed: int = 0
    parse_time_ms: float = 0.0
    build_time_ms: float = 0.0
    total_lines: int = 0
    total_dependencies: int = 0
    dynamic_imports_found: int = 0
    star_imports_found: int = 0


class ImportGraph:
    """
    Dependency graph of Python modules based on import statements.

    Uses NetworkX DiGraph for efficient graph operations.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.modules: Dict[str, ModuleInfo] = {}
        self.build_metrics: BuildMetrics = BuildMetrics()  # MD-2081: Build metrics

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

    def to_dependencies_dict(self) -> Dict[str, List[str]]:
        """
        MD-2022: Convert ImportGraph to Dict[str, List[str]] for rule evaluation.

        This method extracts the module -> dependencies mapping that RuleEngine expects.
        Use this instead of iterating directly over ImportGraph to avoid
        "'ImportGraph' object is not iterable" errors.

        Returns:
            Dictionary mapping module names to their list of dependencies
        """
        return {
            module_name: self.get_dependencies(module_name)
            for module_name in self.modules.keys()
        }

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
                    'dynamic_imports': info.dynamic_imports,
                    'star_imports': info.star_imports,
                    'exports': info.exports,
                    'size_lines': info.size_lines,
                    'classes': info.classes,
                    'functions': info.functions,
                    'file_hash': info.file_hash,
                    'is_namespace_package': info.is_namespace_package
                }
                for name, info in self.modules.items()
            },
            'build_metrics': {
                'total_files': self.build_metrics.total_files,
                'files_parsed': self.build_metrics.files_parsed,
                'files_cached': self.build_metrics.files_cached,
                'files_failed': self.build_metrics.files_failed,
                'parse_time_ms': self.build_metrics.parse_time_ms,
                'build_time_ms': self.build_metrics.build_time_ms,
                'total_lines': self.build_metrics.total_lines,
                'total_dependencies': self.build_metrics.total_dependencies,
                'dynamic_imports_found': self.build_metrics.dynamic_imports_found,
                'star_imports_found': self.build_metrics.star_imports_found
            }
        }


class ImportGraphBuilder:
    """
    Builds import graphs from Python source code.

    Uses AST parsing to extract import statements and module dependencies.

    Enhanced (MD-2081):
    - Parallel file scanning with configurable workers
    - Dynamic import detection (importlib.import_module)
    - __all__ exports handling for star imports
    - Incremental graph building with file hash caching
    - Namespace package support (PEP 420)
    """

    def __init__(
        self,
        project_path: str,
        project_name: Optional[str] = None,
        max_workers: int = 4,  # MD-2081: Parallel workers
        cache_path: Optional[str] = None  # MD-2081: Cache for incremental builds
    ):
        """
        Initialize import graph builder.

        Args:
            project_path: Root path of the project
            project_name: Project name (used for module resolution)
            max_workers: Number of parallel workers for file scanning
            cache_path: Path to cache file for incremental builds
        """
        self.project_path = Path(project_path)
        self.project_name = project_name or self.project_path.name
        self.max_workers = max_workers
        self.cache_path = Path(cache_path) if cache_path else self.project_path / ".acc_cache.json"
        self._module_cache: Dict[str, ModuleInfo] = {}
        self._file_hashes: Dict[str, str] = {}

        self.exclusions: List[str] = [
            '__pycache__',
            '.venv',
            'venv',
            '.git',
            'node_modules',
            '.tox',
            '.eggs',
            '*.egg-info',
            'build',
            'dist'
        ]

        # Load existing cache
        self._load_cache()

    def build_graph(self, use_cache: bool = True, parallel: bool = True) -> ImportGraph:
        """
        Build import graph from Python files in the project.

        Args:
            use_cache: Whether to use incremental caching (default: True)
            parallel: Whether to use parallel scanning (default: True)

        Returns:
            ImportGraph object with build metrics
        """
        start_time = time.time()
        graph = ImportGraph()

        # Find all Python files
        python_files = self._find_python_files()
        graph.build_metrics.total_files = len(python_files)

        # Parse files (parallel or sequential)
        parse_start = time.time()
        if parallel and len(python_files) > 10:
            parsed_modules = self._parse_files_parallel(python_files, use_cache)
        else:
            parsed_modules = self._parse_files_sequential(python_files, use_cache)

        graph.build_metrics.parse_time_ms = (time.time() - parse_start) * 1000

        # Add modules to graph
        for module_info in parsed_modules:
            if module_info:
                graph.add_module(module_info)
                graph.build_metrics.files_parsed += 1
                graph.build_metrics.total_lines += module_info.size_lines
                graph.build_metrics.dynamic_imports_found += len(module_info.dynamic_imports)
                graph.build_metrics.star_imports_found += len(module_info.star_imports)

        # Build dependency edges
        for module_name, module_info in graph.modules.items():
            for dep in module_info.all_dependencies():
                # Resolve dependency to module name
                resolved_dep = self._resolve_import(dep)
                if resolved_dep and resolved_dep in graph.modules:
                    graph.add_dependency(module_name, resolved_dep)
                    graph.build_metrics.total_dependencies += 1

        # Save cache for incremental builds
        if use_cache:
            self._save_cache()

        graph.build_metrics.build_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Built import graph: {graph.build_metrics.files_parsed} files, "
            f"{graph.build_metrics.total_dependencies} deps, "
            f"{graph.build_metrics.build_time_ms:.0f}ms"
        )

        return graph

    def _parse_files_parallel(
        self,
        python_files: List[Path],
        use_cache: bool
    ) -> List[Optional[ModuleInfo]]:
        """Parse files in parallel using ThreadPoolExecutor (MD-2081)."""
        results: List[Optional[ModuleInfo]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._parse_file_cached, f, use_cache): f
                for f in python_files
            }

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    module_info = future.result()
                    results.append(module_info)
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")
                    results.append(None)

        return results

    def _parse_files_sequential(
        self,
        python_files: List[Path],
        use_cache: bool
    ) -> List[Optional[ModuleInfo]]:
        """Parse files sequentially (fallback for small projects)."""
        results: List[Optional[ModuleInfo]] = []

        for py_file in python_files:
            try:
                module_info = self._parse_file_cached(py_file, use_cache)
                results.append(module_info)
            except Exception as e:
                logger.warning(f"Failed to parse {py_file}: {e}")
                results.append(None)

        return results

    def _parse_file_cached(
        self,
        file_path: Path,
        use_cache: bool
    ) -> Optional[ModuleInfo]:
        """Parse file with caching support (MD-2081)."""
        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)
        cache_key = str(file_path)

        # Check cache
        if use_cache and cache_key in self._module_cache:
            cached = self._module_cache[cache_key]
            if cached.file_hash == file_hash:
                return cached

        # Parse file
        module_info = self._parse_file(file_path)
        if module_info:
            module_info.file_hash = file_hash
            self._module_cache[cache_key] = module_info

        return module_info

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content (MD-2081)."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def _load_cache(self):
        """Load module cache from disk (MD-2081)."""
        if not self.cache_path.exists():
            return

        try:
            with open(self.cache_path, 'r') as f:
                cache_data = json.load(f)

            for file_path, module_data in cache_data.get('modules', {}).items():
                self._module_cache[file_path] = ModuleInfo(
                    module_name=module_data['module_name'],
                    file_path=Path(module_data['file_path']),
                    imports=module_data.get('imports', []),
                    from_imports=module_data.get('from_imports', []),
                    dynamic_imports=module_data.get('dynamic_imports', []),
                    star_imports=module_data.get('star_imports', []),
                    exports=module_data.get('exports', []),
                    size_lines=module_data.get('size_lines', 0),
                    classes=module_data.get('classes', []),
                    functions=module_data.get('functions', []),
                    file_hash=module_data.get('file_hash', ''),
                    is_namespace_package=module_data.get('is_namespace_package', False)
                )

            logger.debug(f"Loaded {len(self._module_cache)} cached modules")

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

    def _save_cache(self):
        """Save module cache to disk (MD-2081)."""
        try:
            cache_data = {
                'version': '1.0',
                'project_path': str(self.project_path),
                'modules': {
                    path: {
                        'module_name': info.module_name,
                        'file_path': str(info.file_path),
                        'imports': info.imports,
                        'from_imports': info.from_imports,
                        'dynamic_imports': info.dynamic_imports,
                        'star_imports': info.star_imports,
                        'exports': info.exports,
                        'size_lines': info.size_lines,
                        'classes': info.classes,
                        'functions': info.functions,
                        'file_hash': info.file_hash,
                        'is_namespace_package': info.is_namespace_package
                    }
                    for path, info in self._module_cache.items()
                }
            }

            with open(self.cache_path, 'w') as f:
                json.dump(cache_data, f)

            logger.debug(f"Saved {len(self._module_cache)} modules to cache")

        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

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

        Enhanced (MD-2081):
        - Dynamic import detection (importlib.import_module)
        - Star import extraction (from X import *)
        - __all__ exports parsing
        - Namespace package detection

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

            # Extract imports (enhanced)
            imports, from_imports, dynamic_imports, star_imports = self._extract_imports_enhanced(tree)

            # Extract __all__ exports
            exports = self._extract_exports(tree)

            # Extract classes and functions
            classes = self._extract_classes(tree)
            functions = self._extract_functions(tree)

            # Count lines
            size_lines = len(source.splitlines())

            # Check if namespace package (PEP 420)
            is_namespace = self._is_namespace_package(file_path)

            return ModuleInfo(
                module_name=module_name,
                file_path=file_path,
                imports=imports,
                from_imports=from_imports,
                dynamic_imports=dynamic_imports,
                star_imports=star_imports,
                exports=exports,
                size_lines=size_lines,
                classes=classes,
                functions=functions,
                is_namespace_package=is_namespace
            )

        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")
            return None

    def _is_namespace_package(self, file_path: Path) -> bool:
        """Check if this is a PEP 420 namespace package (MD-2081)."""
        # A namespace package is a directory without __init__.py
        # but containing Python files or subdirectories with Python files
        if file_path.name != '__init__.py':
            return False

        parent_dir = file_path.parent
        # Check if __init__.py is empty or only has docstrings/comments
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()

            # Empty or docstring-only __init__.py in directory with subpackages
            if not content:
                return True

            # Parse and check if only has docstring
            tree = ast.parse(content)
            if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
                if isinstance(tree.body[0].value, (ast.Str, ast.Constant)):
                    return True

        except Exception:
            pass

        return False

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
        Extract import statements from AST (legacy method for compatibility).

        Args:
            tree: AST tree

        Returns:
            Tuple of (imports, from_imports)
        """
        imports, from_imports, _, _ = self._extract_imports_enhanced(tree)
        return imports, from_imports

    def _extract_imports_enhanced(
        self,
        tree: ast.AST
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        """
        Extract import statements with enhanced detection (MD-2081).

        Detects:
        - Regular imports (import X)
        - From imports (from X import Y)
        - Dynamic imports (importlib.import_module('X'))
        - Star imports (from X import *)

        Args:
            tree: AST tree

        Returns:
            Tuple of (imports, from_imports, dynamic_imports, star_imports)
        """
        imports = []
        from_imports = []
        dynamic_imports = []
        star_imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Check for star import
                    if any(alias.name == '*' for alias in node.names):
                        star_imports.append(node.module)
                    else:
                        from_imports.append(node.module)

            elif isinstance(node, ast.Call):
                # Detect importlib.import_module('module_name')
                dynamic_import = self._extract_dynamic_import(node)
                if dynamic_import:
                    dynamic_imports.append(dynamic_import)

        return imports, from_imports, dynamic_imports, star_imports

    def _extract_dynamic_import(self, node: ast.Call) -> Optional[str]:
        """
        Extract module name from dynamic import call (MD-2081).

        Detects patterns like:
        - importlib.import_module('module_name')
        - __import__('module_name')

        Args:
            node: AST Call node

        Returns:
            Module name if detected, None otherwise
        """
        try:
            # Check for importlib.import_module(...)
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'import_module':
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == 'importlib':
                            if node.args and isinstance(node.args[0], (ast.Str, ast.Constant)):
                                if isinstance(node.args[0], ast.Str):
                                    return node.args[0].s
                                elif isinstance(node.args[0], ast.Constant):
                                    return str(node.args[0].value)

            # Check for __import__('module_name')
            elif isinstance(node.func, ast.Name):
                if node.func.id == '__import__':
                    if node.args and isinstance(node.args[0], (ast.Str, ast.Constant)):
                        if isinstance(node.args[0], ast.Str):
                            return node.args[0].s
                        elif isinstance(node.args[0], ast.Constant):
                            return str(node.args[0].value)

        except Exception:
            pass

        return None

    def _extract_exports(self, tree: ast.AST) -> List[str]:
        """
        Extract __all__ exports from module (MD-2081).

        Detects patterns like:
        - __all__ = ['func1', 'func2', 'Class1']
        - __all__ = ('func1', 'func2')

        Args:
            tree: AST tree

        Returns:
            List of exported names
        """
        exports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        # Extract list/tuple elements
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Str):
                                    exports.append(elt.s)
                                elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)

        return exports

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
    import sys

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Build import graph for current project with enhanced features (MD-2081)
    project_path = sys.argv[1] if len(sys.argv) > 1 else "/home/ec2-user/projects/maestro-platform/maestro-hive"

    print(f"Building import graph for: {project_path}")
    print("=" * 60)

    builder = ImportGraphBuilder(
        project_path=project_path,
        max_workers=4  # Parallel scanning
    )

    # Build graph with parallel scanning and caching
    graph = builder.build_graph(use_cache=True, parallel=True)

    # Show build metrics (MD-2081)
    metrics = graph.build_metrics
    print(f"\n=== Build Metrics (MD-2081) ===")
    print(f"  Total files found:     {metrics.total_files}")
    print(f"  Files parsed:          {metrics.files_parsed}")
    print(f"  Files from cache:      {metrics.files_cached}")
    print(f"  Files failed:          {metrics.files_failed}")
    print(f"  Total lines:           {metrics.total_lines}")
    print(f"  Total dependencies:    {metrics.total_dependencies}")
    print(f"  Dynamic imports found: {metrics.dynamic_imports_found}")
    print(f"  Star imports found:    {metrics.star_imports_found}")
    print(f"  Parse time:            {metrics.parse_time_ms:.0f}ms")
    print(f"  Total build time:      {metrics.build_time_ms:.0f}ms")

    # Performance check (target: <30s for 1000+ files)
    if metrics.total_files >= 1000:
        if metrics.build_time_ms < 30000:
            print(f"\n  PASS: Built {metrics.total_files} files in {metrics.build_time_ms/1000:.1f}s (<30s target)")
        else:
            print(f"\n  FAIL: Built {metrics.total_files} files in {metrics.build_time_ms/1000:.1f}s (>30s target)")

    # Check for cycles
    print(f"\n=== Cycle Detection ===")
    if graph.has_cycle():
        cycles = graph.find_cycles()
        print(f"  Found {len(cycles)} cyclic dependencies:")
        for cycle in cycles[:5]:  # Show first 5
            print(f"    {' -> '.join(cycle)}")
    else:
        print("  No cyclic dependencies found")

    # Calculate coupling for a few modules
    print(f"\n=== Coupling Metrics (Sample) ===")
    for module_name in list(graph.modules.keys())[:5]:
        ca, ce, instability = graph.calculate_coupling(module_name)
        print(f"  {module_name}: Ca={ca}, Ce={ce}, I={instability:.2f}")

    # Show modules with dynamic imports (MD-2081)
    print(f"\n=== Dynamic Imports Found ===")
    for name, info in graph.modules.items():
        if info.dynamic_imports:
            print(f"  {name}: {info.dynamic_imports}")

    # Show modules with __all__ exports (MD-2081)
    print(f"\n=== Modules with __all__ exports ===")
    count = 0
    for name, info in graph.modules.items():
        if info.exports:
            print(f"  {name}: {len(info.exports)} exports")
            count += 1
            if count >= 5:
                break
