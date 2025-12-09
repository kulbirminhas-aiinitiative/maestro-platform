#!/usr/bin/env python3
"""
Pattern Recognition: Identifies patterns in code and execution history.

This module handles:
- Pattern detection in code structures
- Error pattern learning from failures
- Success pattern extraction
- Knowledge graph building
"""

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns that can be recognized."""
    CODE_STRUCTURE = "code_structure"
    ERROR = "error"
    SUCCESS = "success"
    WORKFLOW = "workflow"
    ANTI_PATTERN = "anti_pattern"
    BEST_PRACTICE = "best_practice"


class PatternConfidence(Enum):
    """Confidence levels for pattern matches."""
    HIGH = "high"       # > 80% match
    MEDIUM = "medium"   # 50-80% match
    LOW = "low"         # < 50% match


@dataclass
class Pattern:
    """A recognized pattern."""
    pattern_id: str
    pattern_type: PatternType
    name: str
    description: str
    signature: str  # Pattern signature for matching
    examples: List[str] = field(default_factory=list)
    occurrence_count: int = 0
    confidence: PatternConfidence = PatternConfidence.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PatternMatch:
    """A match of a pattern in content."""
    match_id: str
    pattern_id: str
    pattern_name: str
    location: str
    confidence: float  # 0.0 to 1.0
    context: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ErrorPattern:
    """A learned error pattern."""
    error_id: str
    error_type: str
    message_pattern: str
    stack_trace_pattern: Optional[str]
    root_cause: str
    fix_suggestions: List[str]
    occurrence_count: int = 0


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    node_id: str
    node_type: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""
    edge_id: str
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0


class PatternRecognizer:
    """
    Recognizes patterns in code and execution data.

    Implements:
    - pattern_recognition: Identify patterns in content
    - error_learning: Learn from error occurrences
    - feedback_loop: Improve patterns from feedback
    - knowledge_graph: Build relationships between concepts
    """

    # Common code patterns
    CODE_PATTERNS = {
        'singleton': r'class\s+\w+.*:\s*_instance\s*=\s*None',
        'factory': r'def\s+create_\w+\s*\(',
        'decorator': r'@\w+\s*(?:\(.*?\))?\s*\ndef\s+',
        'async_handler': r'async\s+def\s+\w+.*:',
        'error_handling': r'try:\s*\n.*except\s+',
        'context_manager': r'with\s+\w+.*:\s*\n',
        'list_comprehension': r'\[.*for\s+\w+\s+in\s+.*\]',
        'generator': r'yield\s+',
    }

    # Common error patterns
    ERROR_PATTERNS = {
        'null_pointer': r'AttributeError.*None',
        'key_error': r'KeyError:\s*[\'"]\w+[\'"]',
        'type_error': r'TypeError.*expected\s+\w+.*got\s+\w+',
        'import_error': r'ImportError.*No module named',
        'index_error': r'IndexError.*out of range',
        'connection_error': r'ConnectionError|ConnectionRefused',
        'timeout': r'TimeoutError|timed?\s*out',
    }

    def __init__(self):
        """Initialize the pattern recognizer."""
        self._patterns: Dict[str, Pattern] = {}
        self._error_patterns: Dict[str, ErrorPattern] = {}
        self._knowledge_nodes: Dict[str, KnowledgeNode] = {}
        self._knowledge_edges: List[KnowledgeEdge] = []
        self._feedback_history: List[Dict[str, Any]] = []

        # Initialize with built-in patterns
        self._initialize_patterns()

    def _initialize_patterns(self) -> None:
        """Initialize built-in patterns."""
        for name, signature in self.CODE_PATTERNS.items():
            pattern = Pattern(
                pattern_id=f"builtin-{name}",
                pattern_type=PatternType.CODE_STRUCTURE,
                name=name.replace('_', ' ').title(),
                description=f"Common {name} pattern",
                signature=signature
            )
            self._patterns[pattern.pattern_id] = pattern

    def recognize_patterns(
        self,
        content: str,
        pattern_types: Optional[List[PatternType]] = None
    ) -> List[PatternMatch]:
        """
        Recognize patterns in content.

        Implements pattern_recognition to find known patterns.

        Args:
            content: Text content to analyze
            pattern_types: Optional filter for pattern types

        Returns:
            List of PatternMatch objects
        """
        matches = []

        for pattern in self._patterns.values():
            # Filter by type if specified
            if pattern_types and pattern.pattern_type not in pattern_types:
                continue

            # Try to match pattern
            regex_matches = re.finditer(pattern.signature, content, re.MULTILINE | re.DOTALL)

            for regex_match in regex_matches:
                # Calculate confidence based on match quality
                match_text = regex_match.group(0)
                confidence = self._calculate_match_confidence(pattern, match_text)

                match = PatternMatch(
                    match_id=str(uuid.uuid4()),
                    pattern_id=pattern.pattern_id,
                    pattern_name=pattern.name,
                    location=f"Line {content[:regex_match.start()].count(chr(10)) + 1}",
                    confidence=confidence,
                    context=match_text[:100] + ('...' if len(match_text) > 100 else ''),
                    suggestions=self._get_suggestions(pattern)
                )
                matches.append(match)

                # Update occurrence count
                pattern.occurrence_count += 1

        logger.info(f"Recognized {len(matches)} patterns in content")
        return matches

    def _calculate_match_confidence(self, pattern: Pattern, match_text: str) -> float:
        """Calculate confidence score for a pattern match."""
        # Base confidence
        confidence = 0.7

        # Increase for longer matches (more context)
        if len(match_text) > 50:
            confidence += 0.1

        # Increase for patterns seen many times
        if pattern.occurrence_count > 10:
            confidence += 0.1

        # Decrease for very short matches
        if len(match_text) < 20:
            confidence -= 0.1

        return min(1.0, max(0.0, confidence))

    def _get_suggestions(self, pattern: Pattern) -> List[str]:
        """Get suggestions based on pattern type."""
        suggestions = []

        if pattern.pattern_type == PatternType.ANTI_PATTERN:
            suggestions.append(f"Consider refactoring: {pattern.description}")
        elif pattern.pattern_type == PatternType.BEST_PRACTICE:
            suggestions.append(f"Good usage of {pattern.name}")
        elif pattern.pattern_type == PatternType.CODE_STRUCTURE:
            suggestions.append(f"Ensure proper implementation of {pattern.name}")

        return suggestions

    def learn_error_pattern(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        root_cause: Optional[str] = None,
        fix: Optional[str] = None
    ) -> ErrorPattern:
        """
        Learn from an error occurrence.

        Implements error_learning to build error knowledge base.
        """
        # Generate pattern from error message
        message_pattern = self._generalize_error_message(error_message)

        # Check if we already have this pattern
        for existing in self._error_patterns.values():
            if existing.message_pattern == message_pattern:
                existing.occurrence_count += 1
                if fix and fix not in existing.fix_suggestions:
                    existing.fix_suggestions.append(fix)
                logger.info(f"Updated existing error pattern: {existing.error_id}")
                return existing

        # Create new pattern
        error_pattern = ErrorPattern(
            error_id=str(uuid.uuid4()),
            error_type=error_type,
            message_pattern=message_pattern,
            stack_trace_pattern=self._generalize_stack_trace(stack_trace) if stack_trace else None,
            root_cause=root_cause or "Unknown",
            fix_suggestions=[fix] if fix else [],
            occurrence_count=1
        )

        self._error_patterns[error_pattern.error_id] = error_pattern

        logger.info(f"Learned new error pattern: {error_type}")
        return error_pattern

    def _generalize_error_message(self, message: str) -> str:
        """Generalize error message to pattern."""
        # Replace specific values with placeholders
        pattern = message
        pattern = re.sub(r"'[^']*'", r"'\\w+'", pattern)
        pattern = re.sub(r'"[^"]*"', r'"\\w+"', pattern)
        pattern = re.sub(r'\d+', r'\\d+', pattern)
        pattern = re.sub(r'0x[0-9a-fA-F]+', r'0x[0-9a-fA-F]+', pattern)
        return pattern

    def _generalize_stack_trace(self, stack_trace: str) -> str:
        """Generalize stack trace to pattern."""
        # Extract key components
        pattern = stack_trace
        pattern = re.sub(r'line \d+', r'line \\d+', pattern)
        pattern = re.sub(r'/[^\s]+\.py', r'/\\S+\\.py', pattern)
        return pattern

    def match_error(self, error_message: str) -> Optional[ErrorPattern]:
        """Match an error against known patterns."""
        for pattern in self._error_patterns.values():
            if re.search(pattern.message_pattern, error_message):
                return pattern

        # Check built-in patterns
        for name, regex in self.ERROR_PATTERNS.items():
            if re.search(regex, error_message):
                # Create a temporary pattern for built-in match
                return ErrorPattern(
                    error_id=f"builtin-{name}",
                    error_type=name,
                    message_pattern=regex,
                    stack_trace_pattern=None,
                    root_cause=f"Common {name.replace('_', ' ')} error",
                    fix_suggestions=self._get_error_fix_suggestions(name)
                )

        return None

    def _get_error_fix_suggestions(self, error_name: str) -> List[str]:
        """Get fix suggestions for known error types."""
        suggestions = {
            'null_pointer': [
                "Check for None values before accessing attributes",
                "Use optional chaining or null checks"
            ],
            'key_error': [
                "Use .get() method with default value",
                "Check if key exists before accessing"
            ],
            'type_error': [
                "Verify input types match expected types",
                "Add type validation or conversion"
            ],
            'import_error': [
                "Install missing package",
                "Check import path and module name"
            ],
            'connection_error': [
                "Verify service is running",
                "Check network connectivity",
                "Implement retry logic"
            ],
            'timeout': [
                "Increase timeout value",
                "Optimize slow operations",
                "Add async processing"
            ]
        }
        return suggestions.get(error_name, ["Review error message for specific fix"])

    def record_feedback(
        self,
        pattern_id: str,
        feedback_type: str,  # 'helpful', 'not_helpful', 'incorrect'
        context: Optional[str] = None
    ) -> None:
        """
        Record feedback on pattern matches.

        Implements feedback_loop for continuous improvement.
        """
        feedback = {
            'pattern_id': pattern_id,
            'feedback_type': feedback_type,
            'context': context,
            'timestamp': datetime.utcnow().isoformat()
        }
        self._feedback_history.append(feedback)

        # Update pattern confidence based on feedback
        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            if feedback_type == 'helpful':
                if pattern.confidence != PatternConfidence.HIGH:
                    pattern.confidence = PatternConfidence.HIGH
            elif feedback_type == 'not_helpful':
                if pattern.confidence != PatternConfidence.LOW:
                    pattern.confidence = PatternConfidence.MEDIUM
            elif feedback_type == 'incorrect':
                pattern.confidence = PatternConfidence.LOW

        logger.info(f"Recorded feedback for pattern {pattern_id}: {feedback_type}")

    def add_knowledge_node(
        self,
        node_type: str,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> KnowledgeNode:
        """
        Add a node to the knowledge graph.

        Implements knowledge_graph building.
        """
        node = KnowledgeNode(
            node_id=str(uuid.uuid4()),
            node_type=node_type,
            name=name,
            attributes=attributes or {}
        )
        self._knowledge_nodes[node.node_id] = node
        return node

    def add_knowledge_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0
    ) -> Optional[KnowledgeEdge]:
        """Add an edge to the knowledge graph."""
        if source_id not in self._knowledge_nodes or target_id not in self._knowledge_nodes:
            logger.warning("Cannot create edge: source or target node not found")
            return None

        edge = KnowledgeEdge(
            edge_id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight
        )
        self._knowledge_edges.append(edge)
        return edge

    def query_knowledge_graph(
        self,
        start_node_id: str,
        relation_type: Optional[str] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Query the knowledge graph from a starting node."""
        results = []
        visited: Set[str] = set()

        def traverse(node_id: str, depth: int):
            if depth > max_depth or node_id in visited:
                return
            visited.add(node_id)

            node = self._knowledge_nodes.get(node_id)
            if not node:
                return

            # Find related edges
            for edge in self._knowledge_edges:
                if edge.source_id == node_id:
                    if relation_type is None or edge.relation_type == relation_type:
                        target = self._knowledge_nodes.get(edge.target_id)
                        if target:
                            results.append({
                                'source': node.name,
                                'relation': edge.relation_type,
                                'target': target.name,
                                'depth': depth,
                                'weight': edge.weight
                            })
                            traverse(edge.target_id, depth + 1)

        traverse(start_node_id, 0)
        return results

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about recognized patterns."""
        type_counts = Counter(p.pattern_type.value for p in self._patterns.values())
        confidence_counts = Counter(p.confidence.value for p in self._patterns.values())

        return {
            'total_patterns': len(self._patterns),
            'total_error_patterns': len(self._error_patterns),
            'by_type': dict(type_counts),
            'by_confidence': dict(confidence_counts),
            'knowledge_nodes': len(self._knowledge_nodes),
            'knowledge_edges': len(self._knowledge_edges),
            'feedback_count': len(self._feedback_history)
        }

    def register_custom_pattern(
        self,
        name: str,
        signature: str,
        pattern_type: PatternType,
        description: str
    ) -> Pattern:
        """Register a custom pattern for recognition."""
        pattern = Pattern(
            pattern_id=f"custom-{uuid.uuid4().hex[:8]}",
            pattern_type=pattern_type,
            name=name,
            description=description,
            signature=signature
        )
        self._patterns[pattern.pattern_id] = pattern
        logger.info(f"Registered custom pattern: {name}")
        return pattern


# Factory function
def create_pattern_recognizer() -> PatternRecognizer:
    """Create a new PatternRecognizer instance."""
    return PatternRecognizer()
