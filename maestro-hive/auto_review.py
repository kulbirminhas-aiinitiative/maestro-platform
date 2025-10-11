#!/usr/bin/env python3
"""
Automated Gap Analysis for Phase Workflow Implementation
Reviews code quality, integration points, edge cases, and potential issues
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Any, Set
from dataclasses import dataclass

@dataclass
class ReviewFinding:
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    file: str
    line: int
    message: str
    recommendation: str

class CodeReviewer:
    def __init__(self):
        self.findings: List[ReviewFinding] = []
        
    def add_finding(self, category: str, severity: str, file: str, line: int, message: str, recommendation: str):
        self.findings.append(ReviewFinding(category, severity, file, line, message, recommendation))
    
    def review_file(self, filepath: Path):
        """Review a single Python file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
            
            # Review patterns
            self._check_error_handling(filepath, tree, content)
            self._check_logging(filepath, tree, content)
            self._check_type_hints(filepath, tree)
            self._check_async_patterns(filepath, tree)
            self._check_todo_fixme(filepath, content)
            self._check_hardcoded_values(filepath, content)
            
        except Exception as e:
            self.add_finding(
                "Syntax", "CRITICAL", str(filepath), 0,
                f"Failed to parse file: {e}",
                "Fix syntax errors before proceeding"
            )
    
    def _check_error_handling(self, filepath: Path, tree: ast.AST, content: str):
        """Check for proper error handling"""
        filename = filepath.name
        
        # Find all try/except blocks
        try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
        
        # Find bare excepts
        for try_node in try_blocks:
            for handler in try_node.handlers:
                if handler.type is None:  # bare except
                    self.add_finding(
                        "Error Handling", "MEDIUM", filename, handler.lineno,
                        "Bare except clause catches all exceptions",
                        "Use specific exception types or at least 'except Exception'"
                    )
        
        # Check if critical functions have error handling
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        for func in functions:
            if func.name in ['execute_workflow', 'execute_phase', 'validate_entry_gate', 'validate_exit_gate']:
                has_try = any(isinstance(node, ast.Try) for node in ast.walk(func))
                if not has_try:
                    self.add_finding(
                        "Error Handling", "HIGH", filename, func.lineno,
                        f"Critical function '{func.name}' lacks error handling",
                        "Add try/except blocks for robustness"
                    )
    
    def _check_logging(self, filepath: Path, tree: ast.AST, content: str):
        """Check for adequate logging"""
        filename = filepath.name
        
        # Count logging statements
        logging_calls = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['debug', 'info', 'warning', 'error', 'critical']:
                        logging_calls += 1
        
        # Check if logger is defined
        has_logger = 'logger = logging.getLogger' in content
        
        if not has_logger and logging_calls > 0:
            self.add_finding(
                "Logging", "MEDIUM", filename, 0,
                "Logging calls without logger definition",
                "Define logger: logger = logging.getLogger(__name__)"
            )
        
        # Check for print statements (should use logging)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    self.add_finding(
                        "Logging", "LOW", filename, node.lineno,
                        "Using print() instead of logging",
                        "Replace print() with logger.info() or logger.debug()"
                    )
    
    def _check_type_hints(self, filepath: Path, tree: ast.AST):
        """Check for type hints on functions"""
        filename = filepath.name
        
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        functions_without_return = []
        
        for func in functions:
            if func.name.startswith('_'):  # Skip private
                continue
            if func.returns is None and func.name != '__init__':
                functions_without_return.append((func.name, func.lineno))
        
        if functions_without_return:
            for name, lineno in functions_without_return[:3]:  # First 3
                self.add_finding(
                    "Type Hints", "LOW", filename, lineno,
                    f"Function '{name}' missing return type hint",
                    "Add return type hint for better IDE support and documentation"
                )
    
    def _check_async_patterns(self, filepath: Path, tree: ast.AST):
        """Check async/await usage"""
        filename = filepath.name
        
        # Find async functions
        async_funcs = [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
        
        for func in async_funcs:
            # Check if they use await
            has_await = any(isinstance(node, ast.Await) for node in ast.walk(func))
            if not has_await:
                self.add_finding(
                    "Async Patterns", "MEDIUM", filename, func.lineno,
                    f"Async function '{func.name}' doesn't use await",
                    "Consider making it synchronous or ensure async operations exist"
                )
    
    def _check_todo_fixme(self, filepath: Path, content: str):
        """Check for TODO/FIXME comments"""
        filename = filepath.name
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            if 'TODO' in line or 'FIXME' in line:
                self.add_finding(
                    "Code Quality", "INFO", filename, i,
                    f"TODO/FIXME found: {line.strip()}",
                    "Address before production release"
                )
    
    def _check_hardcoded_values(self, filepath: Path, content: str):
        """Check for hardcoded values that should be configurable"""
        filename = filepath.name
        lines = content.split('\n')
        
        # Common patterns
        patterns = [
            ('max_retries = 3', 'Consider making max_retries configurable'),
            ('timeout = 60', 'Consider making timeout configurable'),
            ('threshold = 0.', 'Consider making threshold configurable'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, recommendation in patterns:
                if pattern in line and 'def ' not in line:
                    self.add_finding(
                        "Configuration", "LOW", filename, i,
                        f"Hardcoded value: {line.strip()}",
                        recommendation
                    )
    
    def print_report(self):
        """Print comprehensive review report"""
        print("=" * 80)
        print("AUTOMATED CODE REVIEW REPORT")
        print("=" * 80)
        print()
        
        if not self.findings:
            print("✅ No issues found! Code looks good.")
            return
        
        # Group by severity
        by_severity = {}
        for finding in self.findings:
            if finding.severity not in by_severity:
                by_severity[finding.severity] = []
            by_severity[finding.severity].append(finding)
        
        # Print by severity
        severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
        
        for severity in severity_order:
            if severity not in by_severity:
                continue
            
            findings = by_severity[severity]
            print(f"\n{'🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡' if severity == 'MEDIUM' else '��' if severity == 'LOW' else '⚪'} {severity} ({len(findings)} issues)")
            print("-" * 80)
            
            for finding in findings:
                print(f"\n  File: {finding.file}:{finding.line}")
                print(f"  Category: {finding.category}")
                print(f"  Issue: {finding.message}")
                print(f"  Fix: {finding.recommendation}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        total = len(self.findings)
        critical = len(by_severity.get('CRITICAL', []))
        high = len(by_severity.get('HIGH', []))
        medium = len(by_severity.get('MEDIUM', []))
        low = len(by_severity.get('LOW', []))
        info = len(by_severity.get('INFO', []))
        
        print(f"Total Issues: {total}")
        print(f"  CRITICAL: {critical}")
        print(f"  HIGH: {high}")
        print(f"  MEDIUM: {medium}")
        print(f"  LOW: {low}")
        print(f"  INFO: {info}")
        print()
        
        if critical > 0:
            print("⚠️  CRITICAL issues must be fixed before production!")
        elif high > 0:
            print("⚠️  HIGH priority issues should be addressed soon.")
        elif medium > 0:
            print("✓ No critical issues, but consider addressing MEDIUM priority items.")
        else:
            print("✅ Code quality looks good!")

def main():
    """Run automated review"""
    reviewer = CodeReviewer()
    
    # Files to review
    files_to_review = [
        'phase_workflow_orchestrator.py',
        'phase_gate_validator.py',
        'progressive_quality_manager.py',
        'phase_models.py',
    ]
    
    print("Starting automated code review...")
    print()
    
    for filename in files_to_review:
        filepath = Path(filename)
        if filepath.exists():
            print(f"Reviewing {filename}...")
            reviewer.review_file(filepath)
        else:
            print(f"⚠️  {filename} not found")
    
    print()
    reviewer.print_report()

if __name__ == '__main__':
    main()
