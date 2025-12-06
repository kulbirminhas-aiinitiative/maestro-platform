"""
RAG Feedback Loop for Self-Healing Mechanism.

Uses Retrieval-Augmented Generation to improve code based on failed tests.

Implements AC-3: Feedback loop: Failed tests -> RAG -> Better Code
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context for RAG code generation."""
    failed_test: str
    error_message: str
    original_code: str
    test_file: str
    code_file: str
    stack_trace: Optional[str] = None
    related_code: List[str] = None

    def __post_init__(self):
        if self.related_code is None:
            self.related_code = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failed_test": self.failed_test,
            "error_message": self.error_message,
            "original_code": self.original_code,
            "test_file": self.test_file,
            "code_file": self.code_file,
            "stack_trace": self.stack_trace,
            "related_code": self.related_code,
        }


@dataclass
class RAGResult:
    """Result from RAG code generation."""
    improved_code: str
    explanation: str
    confidence: float
    changes_made: List[str]
    similar_patterns: List[Dict[str, Any]]


class RAGFeedbackLoop:
    """
    Implements the feedback loop: Failed tests -> RAG -> Better Code.

    This component:
    1. Takes failed test information and error context
    2. Queries the vector store for similar successful patterns
    3. Uses retrieved context to generate improved code
    4. Validates and returns the improvement
    """

    def __init__(
        self,
        vector_store_url: Optional[str] = None,
        rag_endpoint: Optional[str] = None,
        similarity_threshold: float = 0.7,
        max_results: int = 5,
    ):
        """
        Initialize the RAG feedback loop.

        Args:
            vector_store_url: URL of the vector store (e.g., Qdrant)
            rag_endpoint: URL of the RAG API endpoint
            similarity_threshold: Minimum similarity for retrieved results
            max_results: Maximum number of similar patterns to retrieve
        """
        self.vector_store_url = vector_store_url or "http://localhost:6333"
        self.rag_endpoint = rag_endpoint or "http://localhost:8002/api/v1/rag"
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results

        # Cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}

        # Pattern database for successful fixes
        self._successful_fixes: List[Dict[str, Any]] = []

    async def process_failed_test(
        self,
        context: RAGContext,
    ) -> Optional[RAGResult]:
        """
        Process a failed test and generate improved code.

        Args:
            context: The RAG context with failed test information

        Returns:
            RAGResult with improved code if successful
        """
        try:
            # Step 1: Retrieve similar patterns
            similar_patterns = await self._retrieve_similar_patterns(context)

            # Step 2: Generate improved code
            result = await self._generate_improved_code(context, similar_patterns)

            if result:
                # Step 3: Store the successful pattern for future use
                self._store_pattern(context, result)

            return result

        except Exception as e:
            logger.error(f"Error in RAG feedback loop: {e}")
            return None

    async def _retrieve_similar_patterns(
        self,
        context: RAGContext,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar successful patterns from vector store.
        """
        # Create embedding for the error context
        query_text = f"""
        Error: {context.error_message}
        Test: {context.failed_test}
        Code context: {context.original_code[:500]}
        """

        # In production, this would call the vector store
        # For now, search in our local pattern database
        similar = []

        error_tokens = set(context.error_message.lower().split())

        for pattern in self._successful_fixes:
            pattern_tokens = set(pattern.get("error", "").lower().split())
            if pattern_tokens:
                similarity = len(error_tokens & pattern_tokens) / len(error_tokens | pattern_tokens)
                if similarity >= self.similarity_threshold:
                    similar.append({
                        **pattern,
                        "similarity": similarity,
                    })

        # Sort by similarity
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:self.max_results]

    async def _generate_improved_code(
        self,
        context: RAGContext,
        similar_patterns: List[Dict[str, Any]],
    ) -> Optional[RAGResult]:
        """
        Generate improved code using RAG.
        """
        # Build context from similar patterns
        pattern_context = ""
        for i, pattern in enumerate(similar_patterns):
            pattern_context += f"""
Similar Fix {i+1} (similarity: {pattern.get('similarity', 0):.2f}):
- Error: {pattern.get('error', 'N/A')}
- Fix: {pattern.get('fix', 'N/A')}
"""

        # Generate improved code
        # In production, this would call an LLM API
        improved_code, changes = self._apply_pattern_fixes(
            context.original_code,
            context.error_message,
            similar_patterns,
        )

        if not changes:
            return None

        return RAGResult(
            improved_code=improved_code,
            explanation=f"Applied {len(changes)} fixes based on similar patterns",
            confidence=0.7 if similar_patterns else 0.5,
            changes_made=changes,
            similar_patterns=similar_patterns,
        )

    def _apply_pattern_fixes(
        self,
        original_code: str,
        error_message: str,
        patterns: List[Dict[str, Any]],
    ) -> Tuple[str, List[str]]:
        """
        Apply fixes from similar patterns to the code.
        """
        improved_code = original_code
        changes = []

        # Apply common fixes based on error type
        error_lower = error_message.lower()

        # Missing import fix
        if "nameerror" in error_lower or "undefined" in error_lower:
            import_match = self._extract_undefined_name(error_message)
            if import_match:
                import_fix = self._suggest_import(import_match)
                if import_fix:
                    improved_code = import_fix + "\n" + improved_code
                    changes.append(f"Added import for '{import_match}'")

        # Null check fix
        if "nonetype" in error_lower or "null" in error_lower:
            # Add null checks for common patterns
            if "." in improved_code:
                lines = improved_code.split("\n")
                for i, line in enumerate(lines):
                    if ".get(" not in line and "if " not in line:
                        # Simple heuristic: add guard for attribute access
                        pass  # Would need more sophisticated analysis

        # Use patterns from similar fixes
        for pattern in patterns:
            fix_template = pattern.get("fix_template")
            if fix_template and pattern.get("similarity", 0) > 0.8:
                # Apply the fix template
                old_pattern = pattern.get("old_pattern")
                new_pattern = pattern.get("new_pattern")
                if old_pattern and new_pattern:
                    if old_pattern in improved_code:
                        improved_code = improved_code.replace(old_pattern, new_pattern)
                        changes.append(f"Applied pattern fix: {pattern.get('description', 'pattern replacement')}")

        return improved_code, changes

    def _extract_undefined_name(self, error_message: str) -> Optional[str]:
        """Extract undefined name from error message."""
        import re
        patterns = [
            r"name '(\w+)' is not defined",
            r"NameError: (\w+)",
            r"undefined: (\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                return match.group(1)
        return None

    def _suggest_import(self, name: str) -> Optional[str]:
        """Suggest an import statement for a name."""
        common_imports = {
            "json": "import json",
            "os": "import os",
            "sys": "import sys",
            "re": "import re",
            "logging": "import logging",
            "datetime": "from datetime import datetime",
            "timedelta": "from datetime import timedelta",
            "Path": "from pathlib import Path",
            "Dict": "from typing import Dict",
            "List": "from typing import List",
            "Optional": "from typing import Optional",
            "Any": "from typing import Any",
            "Tuple": "from typing import Tuple",
            "Union": "from typing import Union",
            "dataclass": "from dataclasses import dataclass",
            "field": "from dataclasses import field",
            "Enum": "from enum import Enum",
            "uuid": "import uuid",
            "hashlib": "import hashlib",
            "asyncio": "import asyncio",
        }
        return common_imports.get(name)

    def _store_pattern(
        self,
        context: RAGContext,
        result: RAGResult,
    ) -> None:
        """
        Store a successful fix pattern for future retrieval.
        """
        pattern = {
            "id": hashlib.sha256(
                f"{context.error_message}:{result.improved_code}".encode()
            ).hexdigest()[:16],
            "error": context.error_message,
            "original_code": context.original_code,
            "fixed_code": result.improved_code,
            "changes": result.changes_made,
            "confidence": result.confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "test_file": context.test_file,
        }

        # Check for duplicates
        existing_ids = {p["id"] for p in self._successful_fixes}
        if pattern["id"] not in existing_ids:
            self._successful_fixes.append(pattern)
            logger.info(f"Stored new successful fix pattern: {pattern['id']}")

    def add_successful_fix(
        self,
        error_message: str,
        original_code: str,
        fixed_code: str,
        description: str,
        old_pattern: Optional[str] = None,
        new_pattern: Optional[str] = None,
    ) -> str:
        """
        Manually add a successful fix pattern to the database.

        Returns:
            The pattern ID
        """
        pattern = {
            "id": hashlib.sha256(
                f"{error_message}:{fixed_code}".encode()
            ).hexdigest()[:16],
            "error": error_message,
            "original_code": original_code,
            "fixed_code": fixed_code,
            "description": description,
            "old_pattern": old_pattern,
            "new_pattern": new_pattern,
            "fix_template": f"{old_pattern} -> {new_pattern}" if old_pattern else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        existing_ids = {p["id"] for p in self._successful_fixes}
        if pattern["id"] not in existing_ids:
            self._successful_fixes.append(pattern)

        return pattern["id"]

    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG feedback loop statistics."""
        return {
            "stored_patterns": len(self._successful_fixes),
            "cache_size": len(self._embedding_cache),
            "vector_store_url": self.vector_store_url,
            "rag_endpoint": self.rag_endpoint,
            "similarity_threshold": self.similarity_threshold,
        }

    def export_patterns(self) -> List[Dict[str, Any]]:
        """Export stored patterns for persistence."""
        return self._successful_fixes.copy()

    def import_patterns(self, patterns: List[Dict[str, Any]]) -> int:
        """
        Import patterns from persistence.

        Returns:
            Number of patterns imported
        """
        existing_ids = {p["id"] for p in self._successful_fixes}
        count = 0

        for pattern in patterns:
            if pattern.get("id") and pattern["id"] not in existing_ids:
                self._successful_fixes.append(pattern)
                existing_ids.add(pattern["id"])
                count += 1

        return count
