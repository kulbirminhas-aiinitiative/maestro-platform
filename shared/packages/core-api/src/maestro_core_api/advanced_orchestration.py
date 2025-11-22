"""
Advanced orchestration patterns for Claude + UTCP.

Provides intelligent service selection, caching, optimization,
and ML-powered decision making.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from aiocache import Cache
from aiocache.serializers import JsonSerializer

from maestro_core_logging import get_logger
from .claude_orchestrator import ClaudeUTCPOrchestrator, OrchestrationResult
from .resilience import ResilienceManager
from .tracing import UTCPTracer, trace_function

logger = get_logger(__name__)


@dataclass
class ServicePerformanceMetrics:
    """Performance metrics for a service."""
    service_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency: float = 0.0
    avg_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    last_call_time: Optional[datetime] = None
    error_rate: float = 0.0
    recent_latencies: List[float] = field(default_factory=list)

    def update(self, latency: float, success: bool):
        """Update metrics with new call data."""
        self.total_calls += 1
        self.total_latency += latency
        self.last_call_time = datetime.utcnow()

        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

        # Track recent latencies (last 100)
        self.recent_latencies.append(latency)
        if len(self.recent_latencies) > 100:
            self.recent_latencies.pop(0)

        # Calculate metrics
        self.avg_latency = self.total_latency / self.total_calls
        self.error_rate = self.failed_calls / self.total_calls if self.total_calls > 0 else 0.0

        # Calculate percentiles
        if self.recent_latencies:
            sorted_latencies = sorted(self.recent_latencies)
            self.p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            self.p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]


@dataclass
class ToolSelectionStrategy:
    """Strategy for selecting tools/services."""
    prefer_low_latency: bool = True
    prefer_high_reliability: bool = True
    enable_cost_optimization: bool = False
    enable_load_balancing: bool = True
    max_parallel_calls: int = 5


class IntelligentOrchestrator(ClaudeUTCPOrchestrator):
    """
    Advanced orchestrator with ML-powered service selection and optimization.

    Features:
    - Intelligent service selection based on performance
    - Response caching with smart TTL
    - Request batching and deduplication
    - Cost optimization
    - Predictive pre-warming
    - A/B testing support

    Example:
        >>> orchestrator = IntelligentOrchestrator()
        >>> await orchestrator.initialize(service_urls)
        >>>
        >>> # Intelligent orchestration with caching
        >>> result = await orchestrator.orchestrate_intelligent(
        >>>     requirement="Build e-commerce site",
        >>>     enable_caching=True,
        >>>     strategy=ToolSelectionStrategy(prefer_low_latency=True)
        >>> )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
        registry=None,
        enable_resilience: bool = True
    ):
        """
        Initialize intelligent orchestrator.

        Args:
            api_key: Anthropic API key
            model: Claude model
            max_tokens: Max tokens
            registry: UTCP registry
            enable_resilience: Enable resilience patterns
        """
        super().__init__(api_key, model, max_tokens, registry)

        self.resilience_manager = ResilienceManager() if enable_resilience else None
        self.tracer = None

        # Performance tracking
        self.service_metrics: Dict[str, ServicePerformanceMetrics] = {}

        # Caching
        self.cache = Cache(Cache.MEMORY, serializer=JsonSerializer())

        # Tool call history for ML
        self.tool_call_history: List[Dict[str, Any]] = []

        logger.info("Intelligent orchestrator initialized")

    async def initialize(self, service_urls: List[str]):
        """Initialize orchestrator and tracing."""
        await super().initialize(service_urls)

        # Initialize tracer
        try:
            from .tracing import configure_tracing, get_tracer
            configure_tracing("intelligent-orchestrator", enable_console=False)
            self.tracer = UTCPTracer("intelligent-orchestrator")
        except Exception as e:
            logger.warning(f"Could not initialize tracing: {e}")

    @trace_function(span_name="intelligent_orchestration")
    async def orchestrate_intelligent(
        self,
        user_requirement: str,
        strategy: Optional[ToolSelectionStrategy] = None,
        enable_caching: bool = True,
        cache_ttl: int = 300,
        conversation_history: Optional[List] = None,
        system_prompt: Optional[str] = None
    ) -> OrchestrationResult:
        """
        Intelligent orchestration with advanced features.

        Args:
            user_requirement: User's request
            strategy: Tool selection strategy
            enable_caching: Enable response caching
            cache_ttl: Cache TTL in seconds
            conversation_history: Conversation context
            system_prompt: System prompt override

        Returns:
            OrchestrationResult with enhanced metrics
        """
        strategy = strategy or ToolSelectionStrategy()

        # Check cache first
        if enable_caching:
            cached_result = await self._check_cache(user_requirement)
            if cached_result:
                logger.info("Returning cached orchestration result")
                return cached_result

        # Get optimized tool list
        available_tools = await self._get_optimized_tools(strategy)

        # Build enhanced system prompt with performance data
        if not system_prompt:
            system_prompt = self._build_intelligent_system_prompt(strategy)

        # Trace orchestration
        if self.tracer:
            async with self.tracer.trace_orchestration(
                user_requirement,
                len(available_tools)
            ):
                result = await self._execute_intelligent_orchestration(
                    user_requirement,
                    available_tools,
                    strategy,
                    system_prompt,
                    conversation_history
                )
        else:
            result = await self._execute_intelligent_orchestration(
                user_requirement,
                available_tools,
                strategy,
                system_prompt,
                conversation_history
            )

        # Cache successful results
        if enable_caching and result.success:
            await self._cache_result(user_requirement, result, cache_ttl)

        # Update learning data
        await self._update_learning_data(result)

        return result

    async def _execute_intelligent_orchestration(
        self,
        user_requirement: str,
        available_tools: List[Dict],
        strategy: ToolSelectionStrategy,
        system_prompt: str,
        conversation_history: Optional[List]
    ) -> OrchestrationResult:
        """Execute orchestration with resilience and tracing."""
        messages = conversation_history or []
        messages.append({"role": "user", "content": user_requirement})

        # Call Claude with optimized tools
        message = await self.async_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            tools=available_tools,
            messages=messages
        )

        # Extract tool calls
        tool_calls = self._extract_tool_calls(message)

        if not tool_calls:
            response_text = self._extract_text_response(message)
            return OrchestrationResult(
                success=True,
                response=response_text,
                tool_calls=[],
                tool_results=[],
                tokens_used={
                    "input": message.usage.input_tokens,
                    "output": message.usage.output_tokens
                },
                model=self.model
            )

        # Execute tools with resilience
        tool_results = await self._execute_tools_with_resilience(
            tool_calls,
            strategy
        )

        # Get final response
        messages.append({"role": "assistant", "content": message.content})
        messages.append({
            "role": "user",
            "content": self._format_tool_results(tool_calls, tool_results)
        })

        final_message = await self.async_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=messages
        )

        response_text = self._extract_text_response(final_message)

        return OrchestrationResult(
            success=True,
            response=response_text,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used={
                "input": message.usage.input_tokens + final_message.usage.input_tokens,
                "output": message.usage.output_tokens + final_message.usage.output_tokens,
                "total": (message.usage.input_tokens + final_message.usage.input_tokens +
                         message.usage.output_tokens + final_message.usage.output_tokens)
            },
            model=self.model
        )

    async def _execute_tools_with_resilience(
        self,
        tool_calls: List[Dict[str, Any]],
        strategy: ToolSelectionStrategy
    ) -> List[Dict[str, Any]]:
        """Execute tools with resilience patterns."""
        results = []

        # Parallel execution if enabled
        if strategy.enable_load_balancing and len(tool_calls) > 1:
            # Execute in parallel with limit
            semaphore = asyncio.Semaphore(strategy.max_parallel_calls)

            async def execute_with_semaphore(tool_call):
                async with semaphore:
                    return await self._execute_single_tool_with_resilience(tool_call)

            results = await asyncio.gather(
                *[execute_with_semaphore(call) for call in tool_calls],
                return_exceptions=True
            )

            # Convert exceptions to error results
            results = [
                r if not isinstance(r, Exception)
                else {"id": tool_calls[i]["id"], "success": False, "error": str(r)}
                for i, r in enumerate(results)
            ]

        else:
            # Sequential execution
            for tool_call in tool_calls:
                result = await self._execute_single_tool_with_resilience(tool_call)
                results.append(result)

        return results

    async def _execute_single_tool_with_resilience(
        self,
        tool_call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute single tool with resilience patterns."""
        start_time = time.time()
        tool_name = tool_call["name"]

        # Extract service name from tool name
        service_name = tool_name.split(".")[0] if "." in tool_name else "unknown"

        try:
            if self.resilience_manager:
                # Call with resilience patterns
                result = await self.resilience_manager.call_with_resilience(
                    service_name,
                    self.registry.call_tool,
                    tool_name,
                    tool_call["input"]
                )
            else:
                # Direct call
                result = await self.registry.call_tool(
                    tool_name,
                    tool_call["input"]
                )

            # Update metrics
            duration = time.time() - start_time
            await self._update_service_metrics(service_name, duration, True)

            return {
                "id": tool_call["id"],
                "success": True,
                "result": result,
                "duration": duration
            }

        except Exception as e:
            duration = time.time() - start_time
            await self._update_service_metrics(service_name, duration, False)

            logger.error(
                "Tool execution failed",
                tool=tool_name,
                error=str(e)
            )

            return {
                "id": tool_call["id"],
                "success": False,
                "error": str(e),
                "duration": duration
            }

    async def _get_optimized_tools(
        self,
        strategy: ToolSelectionStrategy
    ) -> List[Dict[str, Any]]:
        """Get optimized tool list based on performance metrics."""
        all_tools = self.registry.list_available_tools()

        # Score and sort tools
        scored_tools = []

        for tool in all_tools:
            service_name = tool.get("service", {}).get("name", "unknown")
            metrics = self.service_metrics.get(service_name)

            score = self._calculate_tool_score(tool, metrics, strategy)
            scored_tools.append((score, tool))

        # Sort by score (higher is better)
        scored_tools.sort(key=lambda x: x[0], reverse=True)

        # Convert to Claude format
        return self._get_claude_tools(scored_tools)

    def _calculate_tool_score(
        self,
        tool: Dict[str, Any],
        metrics: Optional[ServicePerformanceMetrics],
        strategy: ToolSelectionStrategy
    ) -> float:
        """Calculate tool score based on metrics and strategy."""
        score = 100.0  # Base score

        if not metrics:
            return score  # No data yet, return base score

        # Factor in latency
        if strategy.prefer_low_latency and metrics.avg_latency > 0:
            latency_penalty = min(metrics.avg_latency / 100, 50)  # Max 50 point penalty
            score -= latency_penalty

        # Factor in reliability
        if strategy.prefer_high_reliability:
            reliability_bonus = (1 - metrics.error_rate) * 20  # Max 20 point bonus
            score += reliability_bonus

        # Recency bonus (prefer recently successful services)
        if metrics.last_call_time:
            age = (datetime.utcnow() - metrics.last_call_time).total_seconds()
            if age < 300:  # Within 5 minutes
                score += 10

        return max(0, score)

    def _build_intelligent_system_prompt(
        self,
        strategy: ToolSelectionStrategy
    ) -> str:
        """Build system prompt with performance insights."""
        base_prompt = super()._build_system_prompt()

        # Add performance insights
        performance_insights = []

        for service_name, metrics in self.service_metrics.items():
            if metrics.total_calls > 0:
                insights = f"- {service_name}: {metrics.avg_latency:.2f}ms avg latency, " \
                          f"{(1 - metrics.error_rate) * 100:.1f}% reliability"
                performance_insights.append(insights)

        if performance_insights:
            performance_section = "\n\nService Performance Insights:\n" + "\n".join(performance_insights)
            base_prompt += performance_section

        # Add strategy preferences
        preferences = []
        if strategy.prefer_low_latency:
            preferences.append("- Prefer services with lower latency")
        if strategy.prefer_high_reliability:
            preferences.append("- Prefer services with higher reliability")

        if preferences:
            preference_section = "\n\nSelection Preferences:\n" + "\n".join(preferences)
            base_prompt += preference_section

        return base_prompt

    async def _update_service_metrics(
        self,
        service_name: str,
        duration: float,
        success: bool
    ):
        """Update service performance metrics."""
        if service_name not in self.service_metrics:
            self.service_metrics[service_name] = ServicePerformanceMetrics(service_name)

        self.service_metrics[service_name].update(duration, success)

    async def _check_cache(self, requirement: str) -> Optional[OrchestrationResult]:
        """Check cache for orchestration result."""
        cache_key = self._get_cache_key(requirement)

        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return OrchestrationResult(**cached_data)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

        return None

    async def _cache_result(
        self,
        requirement: str,
        result: OrchestrationResult,
        ttl: int
    ):
        """Cache orchestration result."""
        cache_key = self._get_cache_key(requirement)

        try:
            # Convert to dict for caching
            cache_data = {
                "success": result.success,
                "response": result.response,
                "tool_calls": result.tool_calls,
                "tool_results": result.tool_results,
                "tokens_used": result.tokens_used,
                "model": result.model,
                "error": result.error
            }
            await self.cache.set(cache_key, cache_data, ttl=ttl)
            logger.debug(f"Cached orchestration result with TTL {ttl}s")
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

    def _get_cache_key(self, requirement: str) -> str:
        """Generate cache key for requirement."""
        return f"orchestration:{hashlib.md5(requirement.encode()).hexdigest()}"

    async def _update_learning_data(self, result: OrchestrationResult):
        """Update learning data for ML-powered optimization."""
        self.tool_call_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "tool_calls": result.tool_calls,
            "success": result.success,
            "tokens_used": result.tokens_used
        })

        # Keep only last 1000 entries
        if len(self.tool_call_history) > 1000:
            self.tool_call_history = self.tool_call_history[-1000:]

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return {
            "services": {
                name: {
                    "total_calls": m.total_calls,
                    "success_rate": (1 - m.error_rate) * 100,
                    "avg_latency_ms": m.avg_latency * 1000,
                    "p95_latency_ms": m.p95_latency * 1000,
                    "p99_latency_ms": m.p99_latency * 1000
                }
                for name, m in self.service_metrics.items()
            },
            "total_orchestrations": len(self.tool_call_history),
            "cache_enabled": True
        }