"""
Workflow Optimization & Standardization Module

EPIC MD-2961: Comprehensive workflow optimization including:
- Standard Library of reusable workflow patterns
- Best Practices Enforcer for validation
- Shared Toolkit for common utilities
- Error Prevention RAG for proactive error detection

This module provides enterprise-grade workflow components for
building resilient, compliant, and optimized workflows.
"""

from maestro_hive.workflow.standard_library import (
    StandardLibrary,
    WorkflowPattern,
    PatternCategory,
    PatternComplexity,
    RetryPattern,
    CircuitBreakerPattern,
    TimeoutPattern,
    BulkheadPattern,
    get_standard_library
)

from maestro_hive.workflow.best_practices_enforcer import (
    BestPracticesEnforcer,
    BestPracticeRule,
    ValidationResult,
    ValidationReport,
    Severity as RuleSeverity,
    RuleCategory,
    get_best_practices_enforcer as get_enforcer
)

from maestro_hive.workflow.shared_toolkit import (
    ToolkitRegistry,
    TokenBucketRateLimiter,
    Cache,
    ExecutionContext,
    Timer,
    rate_limited,
    cached,
    timed_decorator as timed,
    gather_with_concurrency,
    retry_async,
    deep_merge,
    get_toolkit_registry
)

from maestro_hive.workflow.error_prevention_rag import (
    ErrorPreventionRAG,
    ErrorKnowledgeBase,
    ErrorDetector,
    PreventionEngine,
    ErrorPattern,
    DetectionResult,
    PreventionRecommendation,
    ErrorSeverity,
    ErrorCategory,
    get_error_prevention_rag,
    analyze_code,
    analyze_workflow,
    search_error_solutions
)


__all__ = [
    # Standard Library
    "StandardLibrary",
    "WorkflowPattern",
    "PatternCategory",
    "PatternComplexity",
    "RetryPattern",
    "CircuitBreakerPattern",
    "TimeoutPattern",
    "BulkheadPattern",
    "get_standard_library",

    # Best Practices Enforcer
    "BestPracticesEnforcer",
    "BestPracticeRule",
    "ValidationResult",
    "ValidationReport",
    "RuleSeverity",
    "RuleCategory",
    "get_enforcer",

    # Shared Toolkit
    "ToolkitRegistry",
    "TokenBucketRateLimiter",
    "Cache",
    "ExecutionContext",
    "Timer",
    "rate_limited",
    "cached",
    "timed",
    "gather_with_concurrency",
    "retry_async",
    "deep_merge",
    "get_toolkit_registry",

    # Error Prevention RAG
    "ErrorPreventionRAG",
    "ErrorKnowledgeBase",
    "ErrorDetector",
    "PreventionEngine",
    "ErrorPattern",
    "DetectionResult",
    "PreventionRecommendation",
    "ErrorSeverity",
    "ErrorCategory",
    "get_error_prevention_rag",
    "analyze_code",
    "analyze_workflow",
    "search_error_solutions"
]

__version__ = "1.0.0"
__epic__ = "MD-2961"
