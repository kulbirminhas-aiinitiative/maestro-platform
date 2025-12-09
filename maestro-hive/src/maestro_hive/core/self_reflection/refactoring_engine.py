#!/usr/bin/env python3
"""
RefactoringEngine: Auto-Fix Generation via RAG + LLM

Part of MD-2533: Self-Healing Mechanism - Auto-Refactoring

This module generates and applies fixes for detected failures using:
1. RAG (Retrieval-Augmented Generation) to find similar past fixes
2. LLM to generate new fixes based on context

Architecture:
- Input: Failure from FailureDetector
- Process: RAG lookup -> Context building -> LLM generation -> Fix validation
- Output: Fix object with patch content
"""

import json
import re
import difflib
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

from .failure_detector import Failure, FailureType, Severity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FixStatus(Enum):
    """Status of a generated fix."""
    GENERATED = "GENERATED"
    VALIDATED = "VALIDATED"
    APPLIED = "APPLIED"
    TESTED = "TESTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass
class Fix:
    """
    Represents a generated fix for a failure.

    Contains the patch content, target file, and validation state.
    """
    fix_id: str
    failure_id: str
    target_file: str
    original_content: str
    fixed_content: str
    patch_content: str
    confidence_score: float  # 0.0 to 1.0
    fix_type: str  # 'import', 'typo', 'type_hint', 'logic', etc.
    status: FixStatus = FixStatus.GENERATED
    explanation: str = ""
    rag_matches: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applied_at: Optional[str] = None
    test_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d['status'] = self.status.value
        return d

    def get_unified_diff(self) -> str:
        """Generate unified diff between original and fixed content."""
        original_lines = self.original_content.splitlines(keepends=True)
        fixed_lines = self.fixed_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{self.target_file}",
            tofile=f"b/{self.target_file}",
            lineterm=''
        )
        return ''.join(diff)


class RAGClient:
    """
    Client for Retrieval-Augmented Generation.

    Queries a vector store for similar past fixes to provide context
    for fix generation.
    """

    def __init__(self, endpoint: Optional[str] = None):
        """
        Initialize RAG client.

        Args:
            endpoint: Vector store API endpoint (optional)
        """
        self.endpoint = endpoint
        self._cache: Dict[str, List[Dict]] = {}
        self._fix_history: List[Dict] = []

    def find_similar_fixes(
        self,
        failure: Failure,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find similar past fixes for a failure.

        Args:
            failure: The failure to find fixes for
            top_k: Number of similar fixes to return

        Returns:
            List of similar fix records
        """
        # Build query from failure
        query = f"{failure.failure_type.value} {failure.error_message}"

        # Check cache first
        cache_key = f"{failure.failure_type.value}:{failure.file_path}"
        if cache_key in self._cache:
            logger.debug(f"RAG cache hit for {cache_key}")
            return self._cache[cache_key][:top_k]

        # If no endpoint, use local fix history
        if not self.endpoint:
            return self._search_local_history(failure, top_k)

        # Query vector store
        try:
            import requests
            response = requests.post(
                f"{self.endpoint}/search",
                json={
                    "query": query,
                    "filter": {"failure_type": failure.failure_type.value},
                    "top_k": top_k
                },
                timeout=10
            )
            if response.status_code == 200:
                results = response.json().get('matches', [])
                self._cache[cache_key] = results
                return results
        except Exception as e:
            logger.warning(f"RAG query failed: {e}. Falling back to local history.")

        return self._search_local_history(failure, top_k)

    def _search_local_history(
        self,
        failure: Failure,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Search local fix history for similar fixes."""
        matches = []

        for fix_record in self._fix_history:
            if fix_record.get('failure_type') == failure.failure_type.value:
                # Simple string similarity
                error_sim = self._string_similarity(
                    failure.error_message,
                    fix_record.get('error_message', '')
                )
                if error_sim > 0.3:
                    matches.append({
                        **fix_record,
                        'similarity_score': error_sim
                    })

        # Sort by similarity
        matches.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        return matches[:top_k]

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity ratio."""
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def add_fix_to_history(self, failure: Failure, fix: Fix):
        """Add a successful fix to the local history."""
        self._fix_history.append({
            'failure_type': failure.failure_type.value,
            'error_message': failure.error_message,
            'file_path': failure.file_path,
            'fix_type': fix.fix_type,
            'patch_content': fix.patch_content,
            'confidence_score': fix.confidence_score,
            'timestamp': datetime.now().isoformat()
        })


class LLMClient:
    """
    Client for LLM-based fix generation.

    Uses language models to generate fixes based on failure context.
    """

    # Common fix templates for different failure types
    FIX_TEMPLATES = {
        FailureType.IMPORT_ERROR: """
Fix this import error:
Error: {error_message}
File: {file_path}

Common solutions:
1. Check if the module is installed
2. Check import path spelling
3. Check for circular imports

Provide the corrected import statement.
""",
        FailureType.NAME_ERROR: """
Fix this NameError:
Error: {error_message}
File: {file_path}
Line: {line_number}

The variable or function name is undefined. Check for:
1. Typos in variable names
2. Missing imports
3. Variable defined in wrong scope

Provide the fix.
""",
        FailureType.TYPE_ERROR: """
Fix this TypeError:
Error: {error_message}
File: {file_path}
Line: {line_number}

Check for:
1. Wrong argument types
2. Missing type conversions
3. Incorrect number of arguments

Provide the corrected code.
""",
        FailureType.ATTRIBUTE_ERROR: """
Fix this AttributeError:
Error: {error_message}
File: {file_path}
Line: {line_number}

The attribute does not exist on the object. Check for:
1. Typos in attribute names
2. Wrong object type
3. Missing method/property definition

Provide the fix.
"""
    }

    def __init__(self, model: str = "claude-3-sonnet-20240229"):
        """
        Initialize LLM client.

        Args:
            model: Model identifier for fix generation
        """
        self.model = model
        self._api_key = None

    def generate_fix(
        self,
        failure: Failure,
        source_content: str,
        rag_context: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Generate a fix for a failure using LLM.

        Args:
            failure: The failure to fix
            source_content: Content of the file with the failure
            rag_context: Similar past fixes from RAG

        Returns:
            Fixed content string or None if generation fails
        """
        # Build prompt
        prompt = self._build_prompt(failure, source_content, rag_context)

        # Try rule-based fix first for common patterns
        rule_fix = self._try_rule_based_fix(failure, source_content)
        if rule_fix:
            logger.info("Applied rule-based fix")
            return rule_fix

        # If no API key available, return None
        if not self._api_key:
            logger.warning("No LLM API key configured. Skipping LLM generation.")
            return None

        # Call LLM API
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key)

            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            fixed_content = self._extract_code_from_response(response.content[0].text)
            return fixed_content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None

    def _build_prompt(
        self,
        failure: Failure,
        source_content: str,
        rag_context: List[Dict[str, Any]]
    ) -> str:
        """Build the prompt for fix generation."""
        template = self.FIX_TEMPLATES.get(
            failure.failure_type,
            "Fix the following error:\n{error_message}\n\nFile content:\n{source_content}"
        )

        # Add RAG context if available
        rag_section = ""
        if rag_context:
            rag_section = "\n\nSimilar past fixes:\n"
            for i, ctx in enumerate(rag_context[:3], 1):
                rag_section += f"\n{i}. {ctx.get('patch_content', 'N/A')[:200]}"

        prompt = template.format(
            error_message=failure.error_message,
            file_path=failure.file_path,
            line_number=failure.line_number,
            source_content=source_content[:2000]  # Truncate for context window
        )

        return prompt + rag_section

    def _try_rule_based_fix(
        self,
        failure: Failure,
        source_content: str
    ) -> Optional[str]:
        """
        Try to apply a rule-based fix for common patterns.

        Returns fixed content if successful, None otherwise.
        """
        if failure.failure_type == FailureType.IMPORT_ERROR:
            return self._fix_import_error(failure, source_content)

        if failure.failure_type == FailureType.NAME_ERROR:
            return self._fix_name_error(failure, source_content)

        return None

    def _fix_import_error(self, failure: Failure, source: str) -> Optional[str]:
        """Fix common import errors."""
        error_msg = failure.error_message.lower()

        # Missing module patterns
        patterns = {
            "no module named 'typing_extensions'": "from typing import *",
            "cannot import name": None,  # Too complex for rule-based
        }

        for pattern, fix in patterns.items():
            if pattern in error_msg and fix:
                # Add the import at the top
                lines = source.split('\n')
                import_section_end = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        import_section_end = i + 1

                lines.insert(import_section_end, fix)
                return '\n'.join(lines)

        return None

    def _fix_name_error(self, failure: Failure, source: str) -> Optional[str]:
        """Fix common NameError issues."""
        # Extract undefined name from error message
        match = re.search(r"name '(\w+)' is not defined", failure.error_message)
        if not match:
            return None

        undefined_name = match.group(1)

        # Check if it's a common typo
        common_fixes = {
            'true': 'True',
            'false': 'False',
            'none': 'None',
            'self': 'self',
        }

        if undefined_name.lower() in common_fixes:
            correct_name = common_fixes[undefined_name.lower()]
            return source.replace(undefined_name, correct_name)

        return None

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code block from LLM response."""
        # Look for code blocks
        code_match = re.search(r'```(?:python)?\n(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # If no code block, return the whole response
        return response.strip()


class RefactoringEngine:
    """
    Main engine for generating and applying fixes.

    Orchestrates RAG lookup, LLM generation, and fix application.
    """

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        rag_endpoint: Optional[str] = None,
        llm_model: str = "claude-3-sonnet-20240229"
    ):
        """
        Initialize RefactoringEngine.

        Args:
            workspace_root: Root directory for file operations
            rag_endpoint: Vector store API endpoint
            llm_model: LLM model for fix generation
        """
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.rag = RAGClient(endpoint=rag_endpoint)
        self.llm = LLMClient(model=llm_model)
        self.fixes: List[Fix] = []
        self.confidence_threshold = 0.7

    def generate_fix(self, failure: Failure) -> Optional[Fix]:
        """
        Generate a fix for a failure.

        Args:
            failure: The failure to fix

        Returns:
            Fix object if successful, None otherwise
        """
        logger.info(f"Generating fix for {failure.failure_type.value}: {failure.error_message[:50]}")

        # Read source file
        if not failure.file_path:
            logger.warning("No file path in failure, cannot generate fix")
            return None

        source_path = self.workspace_root / failure.file_path
        if not source_path.exists():
            # Try relative to workspace
            source_path = Path(failure.file_path)
            if not source_path.exists():
                logger.warning(f"Source file not found: {failure.file_path}")
                return None

        try:
            original_content = source_path.read_text()
        except Exception as e:
            logger.error(f"Failed to read source file: {e}")
            return None

        # Query RAG for similar fixes
        rag_matches = self.rag.find_similar_fixes(failure)
        logger.info(f"Found {len(rag_matches)} similar fixes from RAG")

        # Calculate confidence based on RAG matches
        confidence = self._calculate_confidence(failure, rag_matches)

        # Generate fix
        fixed_content = self.llm.generate_fix(failure, original_content, rag_matches)

        if not fixed_content:
            logger.warning("Failed to generate fix content")
            return None

        # Create Fix object
        fix = Fix(
            fix_id=f"fix_{failure.failure_id}",
            failure_id=failure.failure_id,
            target_file=str(source_path),
            original_content=original_content,
            fixed_content=fixed_content,
            patch_content=self._generate_patch(original_content, fixed_content, failure.file_path),
            confidence_score=confidence,
            fix_type=self._determine_fix_type(failure),
            explanation=f"Auto-generated fix for {failure.failure_type.value}",
            rag_matches=rag_matches
        )

        # Validate fix
        if self._validate_fix(fix):
            fix.status = FixStatus.VALIDATED
            self.fixes.append(fix)
            return fix

        logger.warning("Fix validation failed")
        fix.status = FixStatus.FAILED
        return None

    def apply_fix(self, fix: Fix, backup: bool = True) -> bool:
        """
        Apply a fix to the target file.

        Args:
            fix: The fix to apply
            backup: Whether to create a backup of the original file

        Returns:
            True if fix was applied successfully
        """
        if fix.status not in (FixStatus.VALIDATED, FixStatus.GENERATED):
            logger.warning(f"Cannot apply fix with status {fix.status}")
            return False

        target_path = Path(fix.target_file)

        try:
            # Create backup if requested
            if backup:
                backup_path = target_path.with_suffix(target_path.suffix + '.bak')
                backup_path.write_text(fix.original_content)
                logger.info(f"Created backup: {backup_path}")

            # Apply fix
            target_path.write_text(fix.fixed_content)
            fix.status = FixStatus.APPLIED
            fix.applied_at = datetime.now().isoformat()

            logger.info(f"Applied fix to {fix.target_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")
            fix.status = FixStatus.FAILED
            return False

    def test_fix(self, fix: Fix, test_command: Optional[str] = None) -> bool:
        """
        Test a fix by running relevant tests.

        Args:
            fix: The fix to test
            test_command: Optional specific test command

        Returns:
            True if tests pass
        """
        if fix.status != FixStatus.APPLIED:
            logger.warning("Fix must be applied before testing")
            return False

        # Determine test command
        if not test_command:
            # Try to find relevant test
            test_file = self._find_related_test(fix.target_file)
            if test_file:
                test_command = f"python -m pytest {test_file} -v"
            else:
                # Run syntax check at minimum
                test_command = f"python -m py_compile {fix.target_file}"

        logger.info(f"Testing fix with: {test_command}")

        try:
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.workspace_root
            )

            fix.test_result = {
                'command': test_command,
                'return_code': result.returncode,
                'stdout': result.stdout[:1000],
                'stderr': result.stderr[:1000]
            }

            if result.returncode == 0:
                fix.status = FixStatus.TESTED
                logger.info("Fix passed tests")
                return True
            else:
                logger.warning(f"Fix failed tests: {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Test command timed out")
            fix.test_result = {'error': 'timeout'}
            return False
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            fix.test_result = {'error': str(e)}
            return False

    def rollback_fix(self, fix: Fix) -> bool:
        """
        Rollback an applied fix.

        Args:
            fix: The fix to rollback

        Returns:
            True if rollback was successful
        """
        if fix.status not in (FixStatus.APPLIED, FixStatus.TESTED, FixStatus.FAILED):
            logger.warning("Cannot rollback fix that was not applied")
            return False

        target_path = Path(fix.target_file)
        backup_path = target_path.with_suffix(target_path.suffix + '.bak')

        try:
            if backup_path.exists():
                # Restore from backup
                target_path.write_text(backup_path.read_text())
                backup_path.unlink()
                logger.info(f"Rolled back fix for {fix.target_file}")
            else:
                # Use original content from fix
                target_path.write_text(fix.original_content)
                logger.info(f"Restored original content for {fix.target_file}")

            fix.status = FixStatus.REJECTED
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _calculate_confidence(
        self,
        failure: Failure,
        rag_matches: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for fix generation."""
        base_confidence = 0.5

        # Boost for RAG matches
        if rag_matches:
            best_match = max(m.get('similarity_score', 0) for m in rag_matches)
            base_confidence += best_match * 0.3

        # Boost for well-defined error types
        high_confidence_types = {
            FailureType.IMPORT_ERROR,
            FailureType.NAME_ERROR,
            FailureType.SYNTAX_ERROR
        }
        if failure.failure_type in high_confidence_types:
            base_confidence += 0.15

        # Reduce for complex errors
        if failure.failure_type in (FailureType.RUNTIME_ERROR, FailureType.UNKNOWN):
            base_confidence -= 0.2

        return min(max(base_confidence, 0.0), 1.0)

    def _determine_fix_type(self, failure: Failure) -> str:
        """Determine the type of fix based on failure."""
        type_map = {
            FailureType.IMPORT_ERROR: 'import',
            FailureType.NAME_ERROR: 'typo',
            FailureType.TYPE_ERROR: 'type_fix',
            FailureType.ATTRIBUTE_ERROR: 'attribute',
            FailureType.SYNTAX_ERROR: 'syntax',
            FailureType.ASSERTION_ERROR: 'logic',
        }
        return type_map.get(failure.failure_type, 'unknown')

    def _generate_patch(
        self,
        original: str,
        fixed: str,
        filename: str
    ) -> str:
        """Generate unified diff patch."""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}"
        )
        return ''.join(diff)

    def _validate_fix(self, fix: Fix) -> bool:
        """Validate a generated fix before application."""
        # Check that fix actually changes something
        if fix.original_content == fix.fixed_content:
            logger.warning("Fix makes no changes")
            return False

        # Check for Python syntax validity
        try:
            compile(fix.fixed_content, fix.target_file, 'exec')
        except SyntaxError as e:
            logger.warning(f"Fix has syntax error: {e}")
            return False

        # Check confidence threshold
        if fix.confidence_score < self.confidence_threshold:
            logger.warning(f"Fix confidence {fix.confidence_score} below threshold {self.confidence_threshold}")
            return False

        return True

    def _find_related_test(self, source_file: str) -> Optional[str]:
        """Find test file related to a source file."""
        source_path = Path(source_file)

        # Common test file patterns
        test_patterns = [
            source_path.parent / f"test_{source_path.name}",
            source_path.parent / "tests" / f"test_{source_path.name}",
            source_path.parent.parent / "tests" / f"test_{source_path.name}",
        ]

        for pattern in test_patterns:
            if pattern.exists():
                return str(pattern)

        return None


if __name__ == "__main__":
    print("RefactoringEngine: Auto-Fix Generation")
    print("Usage: Import and use with FailureDetector")
    print("")
    print("Example:")
    print("  from failure_detector import FailureDetector, Failure")
    print("  from refactoring_engine import RefactoringEngine")
    print("")
    print("  detector = FailureDetector()")
    print("  failures = detector.scan_pytest('output.txt')")
    print("")
    print("  engine = RefactoringEngine()")
    print("  for failure in failures:")
    print("      fix = engine.generate_fix(failure)")
    print("      if fix:")
    print("          engine.apply_fix(fix)")
    print("          engine.test_fix(fix)")
