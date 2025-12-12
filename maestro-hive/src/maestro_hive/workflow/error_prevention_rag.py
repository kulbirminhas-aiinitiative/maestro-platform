"""
Error Prevention RAG Module - AC-4 Implementation

RAG-based error detection and prevention system that analyzes workflow
patterns to identify potential issues before they occur.

Part of EPIC MD-2961: Workflow Optimization & Standardization
"""

import asyncio
import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for detected errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of preventable errors."""
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATA_VALIDATION = "data_validation"
    CONCURRENCY = "concurrency"
    INTEGRATION = "integration"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class ErrorPattern:
    """Represents a known error pattern in the knowledge base."""

    id: str
    name: str
    description: str
    category: ErrorCategory
    severity: ErrorSeverity
    indicators: List[str]
    prevention_strategies: List[str]
    resolution_steps: List[str]
    related_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "indicators": self.indicators,
            "prevention_strategies": self.prevention_strategies,
            "resolution_steps": self.resolution_steps,
            "related_patterns": self.related_patterns,
            "metadata": self.metadata
        }


@dataclass
class DetectionResult:
    """Result of error pattern detection."""

    pattern: ErrorPattern
    confidence: float  # 0.0 to 1.0
    matched_indicators: List[str]
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_high_confidence(self) -> bool:
        """Check if detection has high confidence."""
        return self.confidence >= 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern": self.pattern.to_dict(),
            "confidence": self.confidence,
            "matched_indicators": self.matched_indicators,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PreventionRecommendation:
    """Recommendation for preventing detected errors."""

    detection: DetectionResult
    recommended_actions: List[str]
    code_suggestions: List[str]
    estimated_impact: str
    priority: int  # 1-10, higher is more urgent

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "detection": self.detection.to_dict(),
            "recommended_actions": self.recommended_actions,
            "code_suggestions": self.code_suggestions,
            "estimated_impact": self.estimated_impact,
            "priority": self.priority
        }


class VectorStore:
    """Simple in-memory vector store for pattern matching."""

    def __init__(self):
        self._vectors: Dict[str, Tuple[List[float], Any]] = {}
        self._dimension: int = 128

    def _text_to_vector(self, text: str) -> List[float]:
        """Convert text to a simple hash-based vector."""
        # Simple hash-based vectorization for demonstration
        # In production, use proper embeddings (OpenAI, sentence-transformers, etc.)
        hash_bytes = hashlib.sha512(text.encode()).digest()
        vector = []
        for i in range(0, min(len(hash_bytes), self._dimension), 1):
            vector.append(float(hash_bytes[i]) / 255.0)
        while len(vector) < self._dimension:
            vector.append(0.0)
        return vector[:self._dimension]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def add(self, key: str, text: str, data: Any) -> None:
        """Add item to vector store."""
        vector = self._text_to_vector(text)
        self._vectors[key] = (vector, data)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Any]]:
        """Search for similar items."""
        query_vector = self._text_to_vector(query)
        results = []

        for key, (vector, data) in self._vectors.items():
            similarity = self._cosine_similarity(query_vector, vector)
            results.append((key, similarity, data))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def remove(self, key: str) -> bool:
        """Remove item from store."""
        if key in self._vectors:
            del self._vectors[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all items."""
        self._vectors.clear()

    def __len__(self) -> int:
        return len(self._vectors)


class ErrorKnowledgeBase:
    """Knowledge base of error patterns and their solutions."""

    def __init__(self):
        self._patterns: Dict[str, ErrorPattern] = {}
        self._vector_store = VectorStore()
        self._initialize_default_patterns()

    def _initialize_default_patterns(self) -> None:
        """Initialize with default error patterns."""
        default_patterns = [
            ErrorPattern(
                id="timeout_cascade",
                name="Timeout Cascade Failure",
                description="Cascading timeouts across dependent services",
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.HIGH,
                indicators=[
                    "multiple timeout errors in sequence",
                    "increasing latency across services",
                    "circuit breaker trips",
                    "retry storms"
                ],
                prevention_strategies=[
                    "Implement circuit breakers",
                    "Set appropriate timeout budgets",
                    "Use bulkhead isolation",
                    "Add retry limits with backoff"
                ],
                resolution_steps=[
                    "Identify the root cause service",
                    "Reset circuit breakers",
                    "Scale affected services",
                    "Review timeout configurations"
                ]
            ),
            ErrorPattern(
                id="memory_leak",
                name="Memory Leak Detection",
                description="Gradual memory consumption leading to OOM",
                category=ErrorCategory.RESOURCE_EXHAUSTION,
                severity=ErrorSeverity.CRITICAL,
                indicators=[
                    "steadily increasing memory usage",
                    "garbage collection frequency increasing",
                    "response times degrading over time",
                    "OOM killer events"
                ],
                prevention_strategies=[
                    "Implement resource limits",
                    "Use connection pooling",
                    "Clear caches periodically",
                    "Profile memory usage in tests"
                ],
                resolution_steps=[
                    "Capture heap dump",
                    "Analyze memory allocations",
                    "Identify leaking objects",
                    "Restart affected services"
                ]
            ),
            ErrorPattern(
                id="deadlock",
                name="Deadlock Condition",
                description="Circular wait causing system freeze",
                category=ErrorCategory.CONCURRENCY,
                severity=ErrorSeverity.CRITICAL,
                indicators=[
                    "thread wait chains",
                    "lock acquisition timeouts",
                    "zero progress on operations",
                    "high CPU with no work done"
                ],
                prevention_strategies=[
                    "Use lock ordering",
                    "Implement lock timeouts",
                    "Prefer lock-free data structures",
                    "Use async/await patterns"
                ],
                resolution_steps=[
                    "Generate thread dump",
                    "Identify lock cycle",
                    "Force release locks",
                    "Restart deadlocked threads"
                ]
            ),
            ErrorPattern(
                id="data_corruption",
                name="Data Corruption Risk",
                description="Race conditions leading to data inconsistency",
                category=ErrorCategory.DATA_VALIDATION,
                severity=ErrorSeverity.HIGH,
                indicators=[
                    "concurrent writes to same resource",
                    "missing optimistic locking",
                    "no transaction boundaries",
                    "inconsistent read results"
                ],
                prevention_strategies=[
                    "Implement optimistic locking",
                    "Use database transactions",
                    "Add validation constraints",
                    "Implement idempotency"
                ],
                resolution_steps=[
                    "Identify corrupted records",
                    "Restore from backup",
                    "Validate data integrity",
                    "Add missing constraints"
                ]
            ),
            ErrorPattern(
                id="connection_exhaustion",
                name="Connection Pool Exhaustion",
                description="All connections in pool consumed",
                category=ErrorCategory.RESOURCE_EXHAUSTION,
                severity=ErrorSeverity.HIGH,
                indicators=[
                    "connection wait timeouts",
                    "pool size at maximum",
                    "slow connection returns",
                    "increasing connection creation"
                ],
                prevention_strategies=[
                    "Size pool appropriately",
                    "Implement connection timeouts",
                    "Use connection health checks",
                    "Monitor pool utilization"
                ],
                resolution_steps=[
                    "Identify connection leaks",
                    "Force close stale connections",
                    "Increase pool size temporarily",
                    "Fix connection return bugs"
                ]
            ),
            ErrorPattern(
                id="api_rate_limit",
                name="API Rate Limit Exceeded",
                description="Too many API requests causing throttling",
                category=ErrorCategory.INTEGRATION,
                severity=ErrorSeverity.MEDIUM,
                indicators=[
                    "429 HTTP responses",
                    "retry-after headers",
                    "request queue buildup",
                    "exponential backoff triggers"
                ],
                prevention_strategies=[
                    "Implement rate limiting",
                    "Use request batching",
                    "Add caching layer",
                    "Queue non-urgent requests"
                ],
                resolution_steps=[
                    "Back off requests",
                    "Check rate limit headers",
                    "Optimize request patterns",
                    "Request quota increase"
                ]
            ),
            ErrorPattern(
                id="config_drift",
                name="Configuration Drift",
                description="Environment configuration mismatch",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.MEDIUM,
                indicators=[
                    "works in dev fails in prod",
                    "missing environment variables",
                    "version mismatches",
                    "feature flag inconsistencies"
                ],
                prevention_strategies=[
                    "Use infrastructure as code",
                    "Validate configs on startup",
                    "Implement config versioning",
                    "Use config management tools"
                ],
                resolution_steps=[
                    "Compare configurations",
                    "Sync config sources",
                    "Roll back to known good config",
                    "Document differences"
                ]
            ),
            ErrorPattern(
                id="injection_vulnerability",
                name="Injection Vulnerability",
                description="Unsanitized input leading to injection",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                indicators=[
                    "string concatenation in queries",
                    "unsanitized user input",
                    "missing input validation",
                    "dynamic code execution"
                ],
                prevention_strategies=[
                    "Use parameterized queries",
                    "Implement input validation",
                    "Use ORM frameworks",
                    "Apply content security policy"
                ],
                resolution_steps=[
                    "Identify injection points",
                    "Add input sanitization",
                    "Review access logs",
                    "Patch vulnerable code"
                ]
            ),
            ErrorPattern(
                id="n_plus_one",
                name="N+1 Query Problem",
                description="Excessive database queries in loops",
                category=ErrorCategory.PERFORMANCE,
                severity=ErrorSeverity.MEDIUM,
                indicators=[
                    "linear query growth with data",
                    "slow list page loads",
                    "high database connection usage",
                    "ORM lazy loading everywhere"
                ],
                prevention_strategies=[
                    "Use eager loading",
                    "Implement batch fetching",
                    "Add query analysis to tests",
                    "Use DataLoader pattern"
                ],
                resolution_steps=[
                    "Profile database queries",
                    "Add eager loading hints",
                    "Implement caching",
                    "Optimize query structure"
                ]
            ),
            ErrorPattern(
                id="retry_storm",
                name="Retry Storm",
                description="Coordinated retries overwhelming service",
                category=ErrorCategory.INTEGRATION,
                severity=ErrorSeverity.HIGH,
                indicators=[
                    "synchronized retry attempts",
                    "traffic spikes after failures",
                    "no jitter in retry timing",
                    "cascading service failures"
                ],
                prevention_strategies=[
                    "Add retry jitter",
                    "Implement exponential backoff",
                    "Use circuit breakers",
                    "Limit total retry attempts"
                ],
                resolution_steps=[
                    "Disable retries temporarily",
                    "Add random jitter",
                    "Implement backoff",
                    "Add circuit breaker"
                ]
            )
        ]

        for pattern in default_patterns:
            self.add_pattern(pattern)

    def add_pattern(self, pattern: ErrorPattern) -> None:
        """Add a pattern to the knowledge base."""
        self._patterns[pattern.id] = pattern

        # Create searchable text from pattern
        search_text = f"{pattern.name} {pattern.description} {' '.join(pattern.indicators)}"
        self._vector_store.add(pattern.id, search_text, pattern)

    def get_pattern(self, pattern_id: str) -> Optional[ErrorPattern]:
        """Get pattern by ID."""
        return self._patterns.get(pattern_id)

    def search_patterns(self, query: str, top_k: int = 5) -> List[Tuple[ErrorPattern, float]]:
        """Search for relevant patterns."""
        results = self._vector_store.search(query, top_k)
        return [(result[2], result[1]) for result in results]

    def get_patterns_by_category(self, category: ErrorCategory) -> List[ErrorPattern]:
        """Get all patterns in a category."""
        return [p for p in self._patterns.values() if p.category == category]

    def get_patterns_by_severity(self, severity: ErrorSeverity) -> List[ErrorPattern]:
        """Get all patterns with given severity."""
        return [p for p in self._patterns.values() if p.severity == severity]

    @property
    def pattern_count(self) -> int:
        """Get total number of patterns."""
        return len(self._patterns)


class ErrorDetector:
    """Detects potential errors in workflow configurations and code."""

    def __init__(self, knowledge_base: ErrorKnowledgeBase):
        self._knowledge_base = knowledge_base
        self._detection_rules: List[Callable] = []
        self._initialize_rules()

    def _initialize_rules(self) -> None:
        """Initialize detection rules."""
        self._detection_rules = [
            self._detect_missing_timeout,
            self._detect_missing_retry_config,
            self._detect_unbounded_concurrency,
            self._detect_missing_error_handling,
            self._detect_hardcoded_credentials,
            self._detect_unbounded_loops,
            self._detect_missing_validation
        ]

    def _detect_missing_timeout(self, context: Dict[str, Any]) -> Optional[DetectionResult]:
        """Detect missing timeout configuration."""
        code = context.get("code", "")
        config = context.get("config", {})

        indicators = []

        # Check for HTTP calls without timeout
        if re.search(r'requests\.(get|post|put|delete)\([^)]*\)', code):
            if 'timeout=' not in code:
                indicators.append("HTTP request without timeout")

        # Check for async operations without timeout
        if 'asyncio' in code and 'timeout' not in code.lower():
            indicators.append("Async operations without timeout")

        # Check config for missing timeouts
        if 'timeout' not in config and 'timeouts' not in config:
            indicators.append("No timeout configuration found")

        if indicators:
            pattern = self._knowledge_base.get_pattern("timeout_cascade")
            if pattern:
                return DetectionResult(
                    pattern=pattern,
                    confidence=min(0.9, 0.3 * len(indicators)),
                    matched_indicators=indicators,
                    context={"source": "timeout_detection"}
                )
        return None

    def _detect_missing_retry_config(self, context: Dict[str, Any]) -> Optional[DetectionResult]:
        """Detect missing retry configuration."""
        code = context.get("code", "")
        config = context.get("config", {})

        indicators = []

        # Check for external calls without retry
        if any(call in code for call in ['requests.', 'httpx.', 'aiohttp.']):
            if 'retry' not in code.lower() and 'tenacity' not in code:
                indicators.append("External calls without retry logic")

        # Check for database operations without retry
        if any(db in code for db in ['cursor.execute', 'session.query', 'connection.']):
            if 'retry' not in code.lower():
                indicators.append("Database operations without retry")

        if indicators:
            pattern = self._knowledge_base.get_pattern("retry_storm")
            if pattern:
                return DetectionResult(
                    pattern=pattern,
                    confidence=0.6,
                    matched_indicators=indicators,
                    context={"source": "retry_detection"}
                )
        return None

    def _detect_unbounded_concurrency(self, context: Dict[str, Any]) -> Optional[DetectionResult]:
        """Detect unbounded concurrency issues."""
        code = context.get("code", "")

        indicators = []

        # Check for unbounded thread/task creation
        if 'ThreadPoolExecutor()' in code or 'ProcessPoolExecutor()' in code:
            if 'max_workers' not in code:
                indicators.append("Unbounded executor pool")

        # Check for gather without limits
        if 'asyncio.gather' in code:
            if 'semaphore' not in code.lower() and 'limit' not in code.lower():
                indicators.append("Unbounded async gather")

        # Check for unbounded queues
        if 'Queue()' in code and 'maxsize' not in code:
            indicators.append("Unbounded queue")

        if indicators:
            pattern = self._knowledge_base.get_pattern("connection_exhaustion")
            if pattern:
                return DetectionResult(
                    pattern=pattern,
                    confidence=0.7,
                    matched_indicators=indicators,
                    context={"source": "concurrency_detection"}
                )
        return None

    def _detect_missing_error_handling(self, context: Dict[str, Any]) -> Optional[DetectionResult]:
        """Detect missing error handling."""
        code = context.get("code", "")

        indicators = []

        # Check for bare except
        if re.search(r'except\s*:', code):
            indicators.append("Bare except clause catches all exceptions")

        # Check for swallowed exceptions
        if re.search(r'except.*:\s*pass', code):
            indicators.append("Exception swallowed with pass")

        # Check for missing try/except around risky operations
        risky_patterns = ['open(', 'requests.', 'json.loads', 'cursor.execute']
        for pattern in risky_patterns:
            if pattern in code:
                # Simple heuristic: check if there's a try nearby
                lines = code.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        context_start = max(0, i - 5)
                        context_end = min(len(lines), i + 5)
                        context_block = '\n'.join(lines[context_start:context_end])
                        if 'try:' not in context_block:
                            indicators.append(f"{pattern} without error handling")
                            break

        if indicators:
            pattern = self._knowledge_base.get_pattern("data_corruption")
            if pattern:
                return DetectionResult(
                    pattern=pattern,
                    confidence=0.65,
                    matched_indicators=indicators,
                    context={"source": "error_handling_detection"}
                )
        return None

    def _detect_hardcoded_credentials(self, context: Dict[str, Any]) -> Optional[DetectionResult]:
        """Detect hardcoded credentials."""
        code = context.get("code", "")

        indicators = []

        # Check for hardcoded passwords
        if re.search(r'password\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            indicators.append("Hardcoded password detected")

        # Check for hardcoded API keys
        if re.search(r'api[_-]?key\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            indicators.append("Hardcoded API key detected")

        # Check for hardcoded secrets
        if re.search(r'secret\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            indicators.append("Hardcoded secret detected")

        if indicators:
            pattern = self._knowledge_base.get_pattern("injection_vulnerability")
            if pattern:
                return DetectionResult(
                    pattern=pattern,
                    confidence=0.85,
                    matched_indicators=indicators,
                    context={"source": "credential_detection"}
                )
        return None

    def _detect_unbounded_loops(self, context: Dict[str, Any]) -> Optional[DetectionResult]:
        """Detect potentially unbounded loops."""
        code = context.get("code", "")

        indicators = []

        # Check for while True without break
        while_true_matches = list(re.finditer(r'while\s+True\s*:', code))
        for match in while_true_matches:
            # Check if there's a break in the loop body
            start = match.end()
            # Simple heuristic: check next 500 chars for break
            loop_body = code[start:start + 500]
            if 'break' not in loop_body and 'return' not in loop_body:
                indicators.append("while True loop without visible exit")

        # Check for recursion without base case visible
        func_matches = list(re.finditer(r'def\s+(\w+)\s*\(', code))
        for match in func_matches:
            func_name = match.group(1)
            start = match.end()
            # Check next 1000 chars for recursive call
            func_body = code[start:start + 1000]
            if func_name + '(' in func_body:
                if 'if ' not in func_body and 'return' not in func_body[:200]:
                    indicators.append(f"Potential unbounded recursion in {func_name}")

        if indicators:
            pattern = self._knowledge_base.get_pattern("memory_leak")
            if pattern:
                return DetectionResult(
                    pattern=pattern,
                    confidence=0.5,
                    matched_indicators=indicators,
                    context={"source": "loop_detection"}
                )
        return None

    def _detect_missing_validation(self, context: Dict[str, Any]) -> Optional[DetectionResult]:
        """Detect missing input validation."""
        code = context.get("code", "")

        indicators = []

        # Check for SQL queries with string formatting
        if re.search(r'execute\s*\(\s*f["\']|execute\s*\(\s*["\'].*%\s*', code):
            indicators.append("SQL query with string formatting (injection risk)")

        # Check for eval/exec usage
        if re.search(r'\beval\s*\(|\bexec\s*\(', code):
            indicators.append("eval/exec usage detected")

        # Check for unsanitized path operations
        if 'os.path.join' in code and 'sanitize' not in code.lower():
            # Check if user input might flow into path
            if 'request.' in code or 'input(' in code:
                indicators.append("Path operations with potential unsanitized input")

        if indicators:
            pattern = self._knowledge_base.get_pattern("injection_vulnerability")
            if pattern:
                return DetectionResult(
                    pattern=pattern,
                    confidence=0.8,
                    matched_indicators=indicators,
                    context={"source": "validation_detection"}
                )
        return None

    def detect(self, context: Dict[str, Any]) -> List[DetectionResult]:
        """Run all detection rules and return results."""
        results = []

        for rule in self._detection_rules:
            try:
                result = rule(context)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Detection rule {rule.__name__} failed: {e}")

        # Also do semantic search for any other patterns
        if "description" in context:
            semantic_results = self._knowledge_base.search_patterns(
                context["description"],
                top_k=3
            )
            for pattern, similarity in semantic_results:
                if similarity > 0.5:  # Threshold for relevance
                    # Check if we already detected this pattern
                    if not any(r.pattern.id == pattern.id for r in results):
                        results.append(DetectionResult(
                            pattern=pattern,
                            confidence=similarity * 0.5,  # Lower confidence for semantic matches
                            matched_indicators=["semantic similarity match"],
                            context={"source": "semantic_search"}
                        ))

        # Sort by confidence
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results


class PreventionEngine:
    """Generates prevention recommendations based on detected errors."""

    def __init__(self, knowledge_base: ErrorKnowledgeBase):
        self._knowledge_base = knowledge_base

    def generate_recommendations(
        self,
        detections: List[DetectionResult]
    ) -> List[PreventionRecommendation]:
        """Generate prevention recommendations for detected issues."""
        recommendations = []

        for detection in detections:
            recommendation = self._create_recommendation(detection)
            recommendations.append(recommendation)

        # Sort by priority
        recommendations.sort(key=lambda r: r.priority, reverse=True)
        return recommendations

    def _create_recommendation(
        self,
        detection: DetectionResult
    ) -> PreventionRecommendation:
        """Create a recommendation for a single detection."""
        pattern = detection.pattern

        # Calculate priority based on severity and confidence
        severity_scores = {
            ErrorSeverity.CRITICAL: 10,
            ErrorSeverity.HIGH: 7,
            ErrorSeverity.MEDIUM: 4,
            ErrorSeverity.LOW: 2
        }
        base_priority = severity_scores.get(pattern.severity, 5)
        priority = int(base_priority * detection.confidence)

        # Generate code suggestions based on pattern
        code_suggestions = self._generate_code_suggestions(pattern)

        # Estimate impact
        impact = self._estimate_impact(pattern, detection)

        return PreventionRecommendation(
            detection=detection,
            recommended_actions=pattern.prevention_strategies,
            code_suggestions=code_suggestions,
            estimated_impact=impact,
            priority=priority
        )

    def _generate_code_suggestions(self, pattern: ErrorPattern) -> List[str]:
        """Generate code suggestions for preventing the error."""
        suggestions = []

        if pattern.category == ErrorCategory.TIMEOUT:
            suggestions.append(
                "# Add timeout to HTTP requests\n"
                "response = requests.get(url, timeout=30)"
            )
            suggestions.append(
                "# Add timeout to async operations\n"
                "result = await asyncio.wait_for(coro, timeout=30.0)"
            )

        elif pattern.category == ErrorCategory.CONCURRENCY:
            suggestions.append(
                "# Use bounded executor\n"
                "executor = ThreadPoolExecutor(max_workers=10)"
            )
            suggestions.append(
                "# Use semaphore for limiting concurrency\n"
                "sem = asyncio.Semaphore(10)\n"
                "async with sem:\n"
                "    await process_item(item)"
            )

        elif pattern.category == ErrorCategory.RESOURCE_EXHAUSTION:
            suggestions.append(
                "# Use connection pooling\n"
                "from sqlalchemy.pool import QueuePool\n"
                "engine = create_engine(url, poolclass=QueuePool, pool_size=5)"
            )
            suggestions.append(
                "# Implement cache with TTL\n"
                "@lru_cache(maxsize=1000)\n"
                "def expensive_operation(key): ..."
            )

        elif pattern.category == ErrorCategory.SECURITY:
            suggestions.append(
                "# Use parameterized queries\n"
                "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
            )
            suggestions.append(
                "# Use environment variables for secrets\n"
                "api_key = os.environ.get('API_KEY')"
            )

        elif pattern.category == ErrorCategory.DATA_VALIDATION:
            suggestions.append(
                "# Add input validation\n"
                "from pydantic import BaseModel, validator\n"
                "class UserInput(BaseModel):\n"
                "    name: str\n"
                "    @validator('name')\n"
                "    def validate_name(cls, v): ..."
            )

        elif pattern.category == ErrorCategory.INTEGRATION:
            suggestions.append(
                "# Implement retry with exponential backoff\n"
                "from tenacity import retry, stop_after_attempt, wait_exponential\n"
                "@retry(stop=stop_after_attempt(3), wait=wait_exponential())\n"
                "def call_external_api(): ..."
            )

        return suggestions

    def _estimate_impact(
        self,
        pattern: ErrorPattern,
        detection: DetectionResult
    ) -> str:
        """Estimate the impact of not addressing the issue."""
        severity = pattern.severity
        confidence = detection.confidence

        if severity == ErrorSeverity.CRITICAL and confidence > 0.7:
            return "SEVERE: High likelihood of system failure or data loss"
        elif severity == ErrorSeverity.HIGH and confidence > 0.5:
            return "SIGNIFICANT: May cause service degradation or partial outages"
        elif severity == ErrorSeverity.MEDIUM:
            return "MODERATE: Could affect performance or user experience"
        else:
            return "LOW: Minor impact, but should be addressed for best practices"


class ErrorPreventionRAG:
    """
    Main RAG-based error prevention system.

    Combines knowledge base retrieval with detection and prevention
    to proactively identify and prevent errors in workflows.
    """

    def __init__(self):
        self._knowledge_base = ErrorKnowledgeBase()
        self._detector = ErrorDetector(self._knowledge_base)
        self._prevention_engine = PreventionEngine(self._knowledge_base)
        self._analysis_history: List[Dict[str, Any]] = []

    def analyze(
        self,
        code: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        workflow_definition: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze code/config/workflow for potential errors.

        Args:
            code: Source code to analyze
            config: Configuration dictionary to analyze
            description: Text description for semantic search
            workflow_definition: Workflow definition to analyze

        Returns:
            Analysis results with detections and recommendations
        """
        context = {
            "code": code or "",
            "config": config or {},
            "description": description or "",
            "workflow": workflow_definition or {}
        }

        # Run detection
        detections = self._detector.detect(context)

        # Generate recommendations
        recommendations = self._prevention_engine.generate_recommendations(detections)

        # Build result
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_issues": len(detections),
                "critical_issues": len([d for d in detections if d.pattern.severity == ErrorSeverity.CRITICAL]),
                "high_issues": len([d for d in detections if d.pattern.severity == ErrorSeverity.HIGH]),
                "medium_issues": len([d for d in detections if d.pattern.severity == ErrorSeverity.MEDIUM]),
                "low_issues": len([d for d in detections if d.pattern.severity == ErrorSeverity.LOW])
            },
            "detections": [d.to_dict() for d in detections],
            "recommendations": [r.to_dict() for r in recommendations],
            "risk_score": self._calculate_risk_score(detections)
        }

        # Store in history
        self._analysis_history.append(result)

        return result

    def _calculate_risk_score(self, detections: List[DetectionResult]) -> float:
        """Calculate overall risk score (0-100)."""
        if not detections:
            return 0.0

        severity_weights = {
            ErrorSeverity.CRITICAL: 40,
            ErrorSeverity.HIGH: 25,
            ErrorSeverity.MEDIUM: 10,
            ErrorSeverity.LOW: 5
        }

        total_risk = 0.0
        for detection in detections:
            weight = severity_weights.get(detection.pattern.severity, 10)
            total_risk += weight * detection.confidence

        # Cap at 100
        return min(100.0, total_risk)

    def search_solutions(self, problem_description: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for solutions to a described problem.

        Args:
            problem_description: Description of the problem
            top_k: Number of results to return

        Returns:
            List of relevant patterns and solutions
        """
        results = self._knowledge_base.search_patterns(problem_description, top_k)
        return [
            {
                "pattern": pattern.to_dict(),
                "relevance_score": score,
                "solutions": pattern.resolution_steps,
                "prevention": pattern.prevention_strategies
            }
            for pattern, score in results
        ]

    def add_custom_pattern(self, pattern: ErrorPattern) -> None:
        """Add a custom error pattern to the knowledge base."""
        self._knowledge_base.add_pattern(pattern)

    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get history of analyses."""
        return self._analysis_history.copy()

    def clear_history(self) -> None:
        """Clear analysis history."""
        self._analysis_history.clear()

    @property
    def knowledge_base(self) -> ErrorKnowledgeBase:
        """Access the knowledge base."""
        return self._knowledge_base

    @property
    def pattern_count(self) -> int:
        """Get number of patterns in knowledge base."""
        return self._knowledge_base.pattern_count


# Singleton instance for global access
_default_instance: Optional[ErrorPreventionRAG] = None


def get_error_prevention_rag() -> ErrorPreventionRAG:
    """Get or create the default ErrorPreventionRAG instance."""
    global _default_instance
    if _default_instance is None:
        _default_instance = ErrorPreventionRAG()
    return _default_instance


# Convenience functions
def analyze_code(code: str) -> Dict[str, Any]:
    """Analyze code for potential errors."""
    return get_error_prevention_rag().analyze(code=code)


def analyze_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze workflow definition for potential errors."""
    return get_error_prevention_rag().analyze(workflow_definition=workflow)


def search_error_solutions(problem: str) -> List[Dict[str, Any]]:
    """Search for solutions to a problem."""
    return get_error_prevention_rag().search_solutions(problem)


__all__ = [
    "ErrorPreventionRAG",
    "ErrorKnowledgeBase",
    "ErrorDetector",
    "PreventionEngine",
    "ErrorPattern",
    "DetectionResult",
    "PreventionRecommendation",
    "ErrorSeverity",
    "ErrorCategory",
    "VectorStore",
    "get_error_prevention_rag",
    "analyze_code",
    "analyze_workflow",
    "search_error_solutions"
]
